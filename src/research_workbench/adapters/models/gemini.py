"""Google Gemini generateContent adapter with explicit function-call mapping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from research_workbench.adapters.models.base import (
    perform_json_request,
    preflight,
    provider_extension,
    raise_provider_http_error,
    reject_unknown_extension_keys,
    require_list,
    require_object,
    validate_adapter_capabilities,
    validate_response_contract,
)
from research_workbench.adapters.models.http import CredentialProvider, HttpTransport, UrllibTransport
from research_workbench.adapters.models.port import (
    Capability,
    ContentBlock,
    FinishReason,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCategory,
    ToolCall,
    Usage,
)


class GeminiGenerateContentProvider:
    """One model-bound Gemini client-function adapter."""

    provider_name = "google"
    adapter_version = "0.1.0"
    implemented_capabilities = frozenset(
        {
            Capability.TEXT,
            Capability.TOOLS,
            Capability.PARALLEL_TOOLS,
            Capability.STRUCTURED_OUTPUT,
        }
    )

    def __init__(
        self,
        *,
        model: str,
        credential: CredentialProvider,
        transport: HttpTransport | None = None,
        supported: frozenset[Capability] = frozenset({Capability.TEXT}),
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: float = 60.0,
        regions: frozenset[str] = frozenset(),
        data_controls: frozenset[str] = frozenset(),
    ) -> None:
        normalized_model = model.removeprefix("models/")
        if not normalized_model.strip():
            raise ValueError("Gemini model must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        validate_adapter_capabilities(supported, self.implemented_capabilities, self.provider_name)
        self.model = normalized_model
        self.credential = credential
        self.transport = transport or UrllibTransport()
        self.supported = supported
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.regions = regions
        self.data_controls = data_controls

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.provider_name,
            adapter_version=self.adapter_version,
            supported=self.supported,
            models=(self.model,),
            deployment="remote",
            regions=self.regions,
            data_controls=self.data_controls,
            known_gaps=(
                "streaming, images, files, code execution, search, and thinking controls are not implemented",
                "generated function-call ids may be synthesized when the API omits them",
                "capability availability remains model/account specific and requires live conformance",
            ),
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        preflight(request, self.capabilities())
        extension = provider_extension(request, self.provider_name)
        reject_unknown_extension_keys(
            extension,
            provider=self.provider_name,
            allowed=frozenset({"safetySettings", "toolConfig"}),
        )
        if request.metadata:
            raise ProviderError(
                ProviderErrorCategory.UNSUPPORTED,
                "Gemini adapter does not transmit canonical request metadata",
            )
        payload = self._payload(request, extension)
        encoded_model = quote(self.model, safe="")
        http_response, document = perform_json_request(
            provider=self.provider_name,
            transport=self.transport,
            credential=self.credential,
            url=f"{self.base_url}/models/{encoded_model}:generateContent",
            headers={
                "x-goog-api-key": "{API_KEY}",
                "content-type": "application/json",
                "user-agent": "research-agent-workbench/0.1",
            },
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )
        if http_response.status_code >= 400:
            self._raise_api_error(http_response.status_code, document)
        return validate_response_contract(request, self._parse_response(request, document))

    def _payload(self, request: ModelRequest, extension: Mapping[str, Any]) -> dict[str, object]:
        system, contents = self._contents(request)
        payload: dict[str, object] = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if request.tools:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parametersJsonSchema": dict(tool.input_schema),
                        }
                        for tool in request.tools
                    ]
                }
            ]
            if request.tool_choice.kind != "auto":
                mode = "ANY" if request.tool_choice.kind in {"required", "specific"} else "NONE"
                function_config: dict[str, object] = {"mode": mode}
                if request.tool_choice.kind == "specific":
                    function_config["allowedFunctionNames"] = [request.tool_choice.name]
                payload["toolConfig"] = {"functionCallingConfig": function_config}
        generation: dict[str, object] = {}
        if request.max_output_tokens is not None:
            generation["maxOutputTokens"] = request.max_output_tokens
        if request.temperature is not None:
            generation["temperature"] = request.temperature
        if request.response_format.kind == "json_schema":
            generation["responseMimeType"] = "application/json"
            generation["responseJsonSchema"] = dict(request.response_format.schema or {})
        if generation:
            payload["generationConfig"] = generation
        for key in ("safetySettings", "toolConfig"):
            if key in extension:
                if key in payload:
                    raise ProviderError(
                        ProviderErrorCategory.INVALID_REQUEST,
                        f"Gemini {key} was supplied through both canonical and extension paths",
                    )
                payload[key] = extension[key]
        return payload

    def _contents(self, request: ModelRequest) -> tuple[str, list[dict[str, object]]]:
        system_parts: list[str] = []
        contents: list[dict[str, object]] = []
        known_calls: dict[str, str] = {}
        for message in request.messages:
            for block in message.content:
                if block.kind == "tool_call" and block.data:
                    known_calls[str(block.data["call_id"])] = str(block.data["name"])

        for message in request.messages:
            if message.role in {"system", "developer"}:
                for block in message.content:
                    if block.kind != "text":
                        raise ProviderError(
                            ProviderErrorCategory.UNSUPPORTED,
                            "Gemini system/developer messages only support text in this adapter",
                        )
                    system_parts.append(block.text or "")
                continue
            role = "model" if message.role == "assistant" else "user"
            parts: list[dict[str, object]] = []
            for block in message.content:
                data = block.data or {}
                if block.kind == "text":
                    if message.role == "tool":
                        raise ProviderError(
                            ProviderErrorCategory.INVALID_REQUEST,
                            "Gemini tool-role messages must contain tool_result blocks",
                        )
                    parts.append({"text": block.text or ""})
                elif block.kind == "tool_call":
                    parts.append(
                        {
                            "functionCall": {
                                "id": data["call_id"],
                                "name": data["name"],
                                "args": dict(data["arguments"]),
                            }
                        }
                    )
                elif block.kind == "tool_result":
                    call_id = str(data["call_id"])
                    name = data.get("name") or known_calls.get(call_id)
                    if not isinstance(name, str) or not name:
                        raise ProviderError(
                            ProviderErrorCategory.INVALID_REQUEST,
                            f"Gemini tool_result {call_id!r} requires name or a matching prior tool_call",
                        )
                    output = data["output"]
                    response = dict(output) if isinstance(output, Mapping) else {"result": output}
                    if data.get("is_error"):
                        response = {"error": response}
                    parts.append(
                        {
                            "functionResponse": {
                                "id": call_id,
                                "name": name,
                                "response": response,
                            }
                        }
                    )
                else:
                    raise ProviderError(
                        ProviderErrorCategory.UNSUPPORTED,
                        f"Gemini adapter cannot serialize content block: {block.kind}",
                    )
            contents.append({"role": role, "parts": parts})
        if not contents:
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                "Gemini request requires at least one non-system message",
            )
        return "\n\n".join(system_parts), contents

    def _parse_response(self, request: ModelRequest, document: Mapping[str, object]) -> ModelResponse:
        response_id = document.get("responseId")
        if not isinstance(response_id, str) or not response_id:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Gemini response lacks a non-empty responseId",
            )
        candidates = require_list(document.get("candidates"), provider=self.provider_name, field="candidates")
        warnings: list[str] = []
        if not candidates:
            prompt_feedback = document.get("promptFeedback")
            block_reason = prompt_feedback.get("blockReason") if isinstance(prompt_feedback, Mapping) else None
            if block_reason:
                return ModelResponse(
                    response_id=response_id,
                    provider=self.provider_name,
                    model=self._model(document, request),
                    output=(),
                    finish_reason=FinishReason.REFUSAL,
                    usage=self._usage(document.get("usageMetadata")),
                    provider_metadata={"prompt_feedback": prompt_feedback},
                )
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Gemini response has no candidates and no prompt block reason",
            )
        if len(candidates) > 1:
            warnings.append(f"Gemini returned {len(candidates)} candidates; adapter selected candidate 0")
        candidate = require_object(candidates[0], provider=self.provider_name, field="candidates[0]")
        content = require_object(candidate.get("content"), provider=self.provider_name, field="candidates[0].content")
        parts = require_list(content.get("parts"), provider=self.provider_name, field="candidates[0].content.parts")
        output: list[ContentBlock] = []
        calls: list[ToolCall] = []
        for index, raw_part in enumerate(parts):
            part = require_object(
                raw_part,
                provider=self.provider_name,
                field=f"candidates[0].content.parts[{index}]",
            )
            if isinstance(part.get("text"), str):
                output.append(ContentBlock(kind="text", text=str(part["text"])))
            elif isinstance(part.get("functionCall"), Mapping):
                calls.append(self._parse_tool_call(part["functionCall"], response_id, index, warnings))
            else:
                warnings.append(f"ignored Gemini part keys: {', '.join(sorted(map(str, part.keys())))}")
        if len(calls) > 1 and Capability.PARALLEL_TOOLS not in self.supported:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Gemini returned parallel function calls but adapter configuration does not claim parallel_tools",
            )
        raw_finish = candidate.get("finishReason")
        finish = FinishReason.TOOL_CALL if calls else _FINISH_REASONS.get(raw_finish, FinishReason.UNKNOWN)
        metadata: dict[str, object] = {"finish_reason": raw_finish}
        for key in ("finishMessage", "safetyRatings", "citationMetadata"):
            if key in candidate:
                metadata[key] = candidate[key]
        return ModelResponse(
            response_id=response_id,
            provider=self.provider_name,
            model=self._model(document, request),
            output=tuple(output),
            finish_reason=finish,
            tool_calls=tuple(calls),
            usage=self._usage(document.get("usageMetadata")),
            warnings=tuple(warnings),
            provider_metadata=metadata,
        )

    def _parse_tool_call(
        self,
        value: Mapping[str, Any],
        response_id: str,
        index: int,
        warnings: list[str],
    ) -> ToolCall:
        name = value.get("name")
        arguments = value.get("args")
        if not isinstance(name, str) or not name or not isinstance(arguments, Mapping):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"Gemini functionCall at part {index} lacks name or object args",
            )
        call_id = value.get("id")
        if not isinstance(call_id, str) or not call_id:
            call_id = f"gemini-{response_id}-{index}"
            warnings.append(f"Gemini functionCall {name!r} omitted id; synthesized {call_id!r}")
        return ToolCall(call_id=call_id, name=name, arguments=dict(arguments))

    def _model(self, document: Mapping[str, object], request: ModelRequest) -> str:
        value = document.get("modelVersion")
        return str(value) if isinstance(value, str) and value else request.model

    def _usage(self, value: object) -> Usage:
        if not isinstance(value, Mapping):
            return Usage()
        return Usage(
            input_tokens=_integer(value.get("promptTokenCount")),
            output_tokens=_integer(value.get("candidatesTokenCount")),
            cached_input_tokens=_integer(value.get("cachedContentTokenCount")),
        )

    def _raise_api_error(self, status_code: int, document: Mapping[str, object]) -> None:
        raw = document.get("error")
        error = raw if isinstance(raw, Mapping) else {}
        message = error.get("message") if isinstance(error.get("message"), str) else f"HTTP {status_code}"
        error_status = error.get("status")
        provider_code = str(error_status) if error_status is not None else None
        override = _ERROR_STATUSES.get(provider_code)
        raise_provider_http_error(
            provider=self.provider_name,
            status_code=status_code,
            message=message,
            provider_code=provider_code,
            category_override=override,
        )


_FINISH_REASONS: dict[object, FinishReason] = {
    "STOP": FinishReason.COMPLETE,
    "MAX_TOKENS": FinishReason.LENGTH,
    "MALFORMED_FUNCTION_CALL": FinishReason.ERROR,
    "UNEXPECTED_TOOL_CALL": FinishReason.ERROR,
    "SAFETY": FinishReason.REFUSAL,
    "RECITATION": FinishReason.REFUSAL,
    "BLOCKLIST": FinishReason.REFUSAL,
    "PROHIBITED_CONTENT": FinishReason.REFUSAL,
    "SPII": FinishReason.REFUSAL,
    "IMAGE_SAFETY": FinishReason.REFUSAL,
}

_ERROR_STATUSES: dict[str | None, ProviderErrorCategory] = {
    "UNAUTHENTICATED": ProviderErrorCategory.AUTHENTICATION,
    "PERMISSION_DENIED": ProviderErrorCategory.PERMISSION,
    "INVALID_ARGUMENT": ProviderErrorCategory.INVALID_REQUEST,
    "FAILED_PRECONDITION": ProviderErrorCategory.INVALID_REQUEST,
    "RESOURCE_EXHAUSTED": ProviderErrorCategory.RATE_LIMIT,
    "UNAVAILABLE": ProviderErrorCategory.TRANSIENT,
    "DEADLINE_EXCEEDED": ProviderErrorCategory.TRANSIENT,
}


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
