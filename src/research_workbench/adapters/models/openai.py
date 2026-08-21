"""OpenAI Responses API adapter with explicit, locally checked semantics."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from research_workbench.adapters.models.base import (
    _integer,
    perform_json_request,
    preflight,
    provider_extension,
    raise_provider_http_error,
    reject_unknown_extension_keys,
    require_list,
    require_object,
    text_from_output,
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


class OpenAIResponsesProvider:
    """One model-bound OpenAI adapter.

    Capabilities are configuration facts, not optimistic model-family guesses.
    Callers must explicitly enable capabilities they have verified for the
    configured model and account.
    """

    provider_name = "openai"
    adapter_version = "0.1.0"
    implemented_capabilities = frozenset(
        {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT, Capability.REASONING}
    )

    def __init__(
        self,
        *,
        model: str,
        credential: CredentialProvider,
        transport: HttpTransport | None = None,
        supported: frozenset[Capability] = frozenset({Capability.TEXT}),
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60.0,
        regions: frozenset[str] = frozenset(),
        data_controls: frozenset[str] = frozenset(),
    ) -> None:
        if not model.strip():
            raise ValueError("OpenAI model must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        validate_adapter_capabilities(supported, self.implemented_capabilities, self.provider_name)
        self.model = model
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
                "streaming, multimodal input, files, server tools, and provider state are not implemented",
                "capability availability remains model/account specific and requires live conformance",
            ),
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        snapshot = self.capabilities()
        preflight(request, snapshot)
        extension = provider_extension(request, self.provider_name)
        reject_unknown_extension_keys(
            extension,
            provider=self.provider_name,
            allowed=frozenset({"service_tier", "truncation", "safety_identifier"}),
        )
        payload = self._payload(request, extension)
        http_response, document = perform_json_request(
            provider=self.provider_name,
            transport=self.transport,
            credential=self.credential,
            url=f"{self.base_url}/responses",
            headers={
                "Authorization": "Bearer {API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "research-agent-workbench/0.1",
            },
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )
        if http_response.status_code >= 400:
            self._raise_api_error(http_response.status_code, document)
        return validate_response_contract(request, self._parse_response(request, document))

    def _payload(self, request: ModelRequest, extension: Mapping[str, Any]) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": request.model,
            "input": self._input_items(request),
            # Responses are stored by default. Research inputs should not become
            # provider state merely because an adapter omitted a field.
            "store": False,
        }
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": dict(tool.input_schema),
                    "strict": tool.strict,
                }
                for tool in request.tools
            ]
            if request.tool_choice.kind == "specific":
                payload["tool_choice"] = {
                    "type": "function",
                    "name": request.tool_choice.name,
                }
            elif request.tool_choice.kind != "auto":
                payload["tool_choice"] = request.tool_choice.kind
        if request.response_format.kind == "json_schema":
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": request.response_format.name,
                    "strict": True,
                    "schema": dict(request.response_format.schema or {}),
                }
            }
        if request.max_output_tokens is not None:
            payload["max_output_tokens"] = request.max_output_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.reasoning_effort is not None:
            payload["reasoning"] = {"effort": request.reasoning_effort}
        if request.metadata:
            payload["metadata"] = dict(request.metadata)
        for key in ("service_tier", "truncation", "safety_identifier"):
            if key in extension:
                payload[key] = extension[key]
        return payload

    def _input_items(self, request: ModelRequest) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for message in request.messages:
            pending_text: list[str] = []

            def flush_text() -> None:
                if not pending_text:
                    return
                if message.role == "tool":
                    raise ProviderError(
                        ProviderErrorCategory.INVALID_REQUEST,
                        "OpenAI tool-role messages must contain tool_result blocks",
                    )
                items.append({"role": message.role, "content": "\n".join(pending_text)})
                pending_text.clear()

            for block in message.content:
                if block.kind == "text":
                    pending_text.append(block.text or "")
                    continue
                flush_text()
                data = block.data or {}
                if block.kind == "tool_call":
                    items.append(
                        {
                            "type": "function_call",
                            "call_id": data["call_id"],
                            "name": data["name"],
                            "arguments": json.dumps(
                                data["arguments"], ensure_ascii=False, separators=(",", ":")
                            ),
                        }
                    )
                elif block.kind == "tool_result":
                    items.append(
                        {
                            "type": "function_call_output",
                            "call_id": data["call_id"],
                            "output": text_from_output(data["output"]),
                        }
                    )
                else:
                    raise ProviderError(
                        ProviderErrorCategory.UNSUPPORTED,
                        f"OpenAI adapter cannot serialize content block: {block.kind}",
                    )
            flush_text()
        return items

    def _parse_response(self, request: ModelRequest, document: Mapping[str, object]) -> ModelResponse:
        response_id = document.get("id")
        if not isinstance(response_id, str) or not response_id:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "OpenAI response lacks a non-empty id",
            )
        output_items = require_list(document.get("output"), provider=self.provider_name, field="output")
        output: list[ContentBlock] = []
        calls: list[ToolCall] = []
        warnings: list[str] = []
        refused = False
        for index, raw_item in enumerate(output_items):
            item = require_object(raw_item, provider=self.provider_name, field=f"output[{index}]")
            item_type = item.get("type")
            if item_type == "message":
                content = require_list(
                    item.get("content"), provider=self.provider_name, field=f"output[{index}].content"
                )
                for part_index, raw_part in enumerate(content):
                    part = require_object(
                        raw_part,
                        provider=self.provider_name,
                        field=f"output[{index}].content[{part_index}]",
                    )
                    if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                        output.append(ContentBlock(kind="text", text=str(part["text"])))
                    elif part.get("type") == "refusal" and isinstance(part.get("refusal"), str):
                        refused = True
                        output.append(ContentBlock(kind="refusal", text=str(part["refusal"])))
                    else:
                        warnings.append(f"ignored OpenAI message content type: {part.get('type')!r}")
            elif item_type == "function_call":
                calls.append(self._parse_tool_call(item, index))
            else:
                warnings.append(f"ignored OpenAI output item type: {item_type!r}")

        finish = self._finish_reason(document, has_calls=bool(calls), refused=refused)
        usage = self._usage(document.get("usage"))
        model = document.get("model") if isinstance(document.get("model"), str) else request.model
        metadata = {
            key: document[key]
            for key in ("status", "service_tier", "system_fingerprint")
            if key in document
        }
        return ModelResponse(
            response_id=response_id,
            provider=self.provider_name,
            model=str(model),
            output=tuple(output),
            finish_reason=finish,
            tool_calls=tuple(calls),
            usage=usage,
            warnings=tuple(warnings),
            provider_metadata=metadata,
        )

    def _parse_tool_call(self, item: Mapping[str, Any], index: int) -> ToolCall:
        call_id = item.get("call_id")
        name = item.get("name")
        arguments = item.get("arguments")
        if not isinstance(call_id, str) or not call_id or not isinstance(name, str) or not name:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"OpenAI function_call at output[{index}] lacks call_id or name",
            )
        try:
            decoded = json.loads(arguments) if isinstance(arguments, str) else arguments
        except json.JSONDecodeError as exc:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"OpenAI function_call {call_id!r} has invalid JSON arguments",
            ) from exc
        if not isinstance(decoded, Mapping):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"OpenAI function_call {call_id!r} arguments are not an object",
            )
        return ToolCall(call_id=call_id, name=name, arguments=dict(decoded))

    def _finish_reason(self, document: Mapping[str, object], *, has_calls: bool, refused: bool) -> FinishReason:
        if has_calls:
            return FinishReason.TOOL_CALL
        if refused:
            return FinishReason.REFUSAL
        status = document.get("status")
        if status == "completed":
            return FinishReason.COMPLETE
        if status == "cancelled":
            return FinishReason.ERROR
        if status == "incomplete":
            details = document.get("incomplete_details")
            reason = details.get("reason") if isinstance(details, Mapping) else None
            if reason == "max_output_tokens":
                return FinishReason.LENGTH
            if reason in {"content_filter", "safety"}:
                return FinishReason.REFUSAL
            return FinishReason.UNKNOWN
        return FinishReason.UNKNOWN

    def _usage(self, value: object) -> Usage:
        if not isinstance(value, Mapping):
            return Usage()
        input_details = value.get("input_tokens_details")
        output_details = value.get("output_tokens_details")
        return Usage(
            input_tokens=_integer(value.get("input_tokens")),
            output_tokens=_integer(value.get("output_tokens")),
            cached_input_tokens=_integer(input_details.get("cached_tokens"))
            if isinstance(input_details, Mapping)
            else None,
            reasoning_tokens=_integer(output_details.get("reasoning_tokens"))
            if isinstance(output_details, Mapping)
            else None,
        )

    def _raise_api_error(self, status_code: int, document: Mapping[str, object]) -> None:
        raw = document.get("error")
        error = raw if isinstance(raw, Mapping) else {}
        message = error.get("message") if isinstance(error.get("message"), str) else f"HTTP {status_code}"
        code_value = error.get("code") or error.get("type")
        provider_code = str(code_value) if code_value is not None else None
        override = None
        if provider_code in {"context_length_exceeded", "max_tokens"}:
            override = ProviderErrorCategory.CONTEXT_LIMIT
        elif provider_code in {"content_filter", "safety"}:
            override = ProviderErrorCategory.SAFETY_REFUSAL
        raise_provider_http_error(
            provider=self.provider_name,
            status_code=status_code,
            message=message,
            provider_code=provider_code,
            category_override=override,
        )
