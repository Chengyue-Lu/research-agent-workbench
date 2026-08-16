"""Anthropic Messages API adapter with client-tool ownership preserved."""

from __future__ import annotations

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


class AnthropicMessagesProvider:
    """One model-bound Anthropic client-tools adapter."""

    provider_name = "anthropic"
    adapter_version = "0.1.0"
    implemented_capabilities = frozenset(
        {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
    )

    def __init__(
        self,
        *,
        model: str,
        credential: CredentialProvider,
        transport: HttpTransport | None = None,
        supported: frozenset[Capability] = frozenset({Capability.TEXT}),
        base_url: str = "https://api.anthropic.com/v1",
        timeout_seconds: float = 60.0,
        default_max_output_tokens: int = 1024,
        regions: frozenset[str] = frozenset(),
        data_controls: frozenset[str] = frozenset(),
    ) -> None:
        if not model.strip():
            raise ValueError("Anthropic model must not be empty")
        if timeout_seconds <= 0 or default_max_output_tokens <= 0:
            raise ValueError("timeouts and default_max_output_tokens must be positive")
        validate_adapter_capabilities(supported, self.implemented_capabilities, self.provider_name)
        self.model = model
        self.credential = credential
        self.transport = transport or UrllibTransport()
        self.supported = supported
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.default_max_output_tokens = default_max_output_tokens
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
                "streaming, images, files, prompt caching, thinking, and server tools are not implemented",
                "server tools are intentionally not normalized as client tool calls",
                "capability availability remains model/account specific and requires live conformance",
            ),
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        preflight(request, self.capabilities())
        if request.temperature is not None and request.temperature > 1:
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                "Anthropic temperature must be between 0 and 1",
            )
        extension = provider_extension(request, self.provider_name)
        reject_unknown_extension_keys(
            extension,
            provider=self.provider_name,
            allowed=frozenset({"stop_sequences", "metadata"}),
        )
        payload = self._payload(request, extension)
        http_response, document = perform_json_request(
            provider=self.provider_name,
            transport=self.transport,
            credential=self.credential,
            url=f"{self.base_url}/messages",
            headers={
                "x-api-key": "{API_KEY}",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "user-agent": "research-agent-workbench/0.1",
            },
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )
        if http_response.status_code >= 400:
            self._raise_api_error(http_response.status_code, document)
        response = self._parse_response(request, document)
        if request.max_output_tokens is None:
            response = ModelResponse(
                response_id=response.response_id,
                provider=response.provider,
                model=response.model,
                output=response.output,
                finish_reason=response.finish_reason,
                tool_calls=response.tool_calls,
                usage=response.usage,
                warnings=(
                    f"Anthropic requires max_tokens; adapter applied explicit default {self.default_max_output_tokens}",
                    *response.warnings,
                ),
                provider_metadata=response.provider_metadata,
            )
        return validate_response_contract(request, response)

    def _payload(self, request: ModelRequest, extension: Mapping[str, Any]) -> dict[str, object]:
        system, messages = self._messages(request)
        payload: dict[str, object] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_output_tokens or self.default_max_output_tokens,
        }
        if system:
            payload["system"] = system
        if request.tools:
            payload["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": dict(tool.input_schema),
                    "strict": tool.strict,
                }
                for tool in request.tools
            ]
            if request.tool_choice.kind == "specific":
                payload["tool_choice"] = {
                    "type": "tool",
                    "name": request.tool_choice.name,
                }
            elif request.tool_choice.kind == "required":
                payload["tool_choice"] = {"type": "any"}
            elif request.tool_choice.kind != "auto":
                payload["tool_choice"] = {"type": request.tool_choice.kind}
        if request.response_format.kind == "json_schema":
            payload["output_config"] = {
                "format": {
                    "type": "json_schema",
                    "schema": dict(request.response_format.schema or {}),
                }
            }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.metadata:
            unsupported = sorted(set(request.metadata) - {"user_id"})
            if unsupported:
                raise ProviderError(
                    ProviderErrorCategory.UNSUPPORTED,
                    "Anthropic metadata only supports user_id in this adapter: " + ", ".join(unsupported),
                )
            payload["metadata"] = dict(request.metadata)
        for key in ("stop_sequences", "metadata"):
            if key in extension:
                if key in payload:
                    raise ProviderError(
                        ProviderErrorCategory.INVALID_REQUEST,
                        f"Anthropic {key} was supplied through two request paths",
                    )
                payload[key] = extension[key]
        return payload

    def _messages(self, request: ModelRequest) -> tuple[str, list[dict[str, object]]]:
        system_parts: list[str] = []
        messages: list[dict[str, object]] = []
        for message in request.messages:
            if message.role in {"system", "developer"}:
                for block in message.content:
                    if block.kind != "text":
                        raise ProviderError(
                            ProviderErrorCategory.UNSUPPORTED,
                            "Anthropic system/developer messages only support text in this adapter",
                        )
                    system_parts.append(block.text or "")
                continue
            role = "assistant" if message.role == "assistant" else "user"
            content: list[dict[str, object]] = []
            for block in message.content:
                data = block.data or {}
                if block.kind == "text":
                    if message.role == "tool":
                        raise ProviderError(
                            ProviderErrorCategory.INVALID_REQUEST,
                            "Anthropic tool-role messages must contain tool_result blocks",
                        )
                    content.append({"type": "text", "text": block.text or ""})
                elif block.kind == "tool_call":
                    content.append(
                        {
                            "type": "tool_use",
                            "id": data["call_id"],
                            "name": data["name"],
                            "input": dict(data["arguments"]),
                        }
                    )
                elif block.kind == "tool_result":
                    result: dict[str, object] = {
                        "type": "tool_result",
                        "tool_use_id": data["call_id"],
                        "content": text_from_output(data["output"]),
                    }
                    if "is_error" in data:
                        result["is_error"] = bool(data["is_error"])
                    content.append(result)
                else:
                    raise ProviderError(
                        ProviderErrorCategory.UNSUPPORTED,
                        f"Anthropic adapter cannot serialize content block: {block.kind}",
                    )
            messages.append({"role": role, "content": content})
        if not messages:
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                "Anthropic request requires at least one non-system message",
            )
        return "\n\n".join(system_parts), messages

    def _parse_response(self, request: ModelRequest, document: Mapping[str, object]) -> ModelResponse:
        response_id = document.get("id")
        if not isinstance(response_id, str) or not response_id:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Anthropic response lacks a non-empty id",
            )
        content = require_list(document.get("content"), provider=self.provider_name, field="content")
        output: list[ContentBlock] = []
        calls: list[ToolCall] = []
        warnings: list[str] = []
        for index, raw_block in enumerate(content):
            block = require_object(raw_block, provider=self.provider_name, field=f"content[{index}]")
            block_type = block.get("type")
            if block_type == "text" and isinstance(block.get("text"), str):
                output.append(ContentBlock(kind="text", text=str(block["text"])))
            elif block_type == "tool_use":
                calls.append(self._parse_tool_call(block, index))
            else:
                warnings.append(f"ignored Anthropic content type: {block_type!r}")
        stop_reason = document.get("stop_reason")
        finish = FinishReason.TOOL_CALL if calls else _STOP_REASONS.get(stop_reason, FinishReason.UNKNOWN)
        usage_value = document.get("usage")
        usage = self._usage(usage_value)
        model = document.get("model") if isinstance(document.get("model"), str) else request.model
        metadata = {"stop_reason": stop_reason}
        if "stop_sequence" in document:
            metadata["stop_sequence"] = document["stop_sequence"]
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

    def _parse_tool_call(self, block: Mapping[str, Any], index: int) -> ToolCall:
        call_id = block.get("id")
        name = block.get("name")
        arguments = block.get("input")
        if (
            not isinstance(call_id, str)
            or not call_id
            or not isinstance(name, str)
            or not name
            or not isinstance(arguments, Mapping)
        ):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"Anthropic tool_use at content[{index}] lacks id, name, or object input",
            )
        return ToolCall(call_id=call_id, name=name, arguments=dict(arguments))

    def _usage(self, value: object) -> Usage:
        if not isinstance(value, Mapping):
            return Usage()
        return Usage(
            input_tokens=_integer(value.get("input_tokens")),
            output_tokens=_integer(value.get("output_tokens")),
            cached_input_tokens=_integer(value.get("cache_read_input_tokens")),
        )

    def _raise_api_error(self, status_code: int, document: Mapping[str, object]) -> None:
        raw = document.get("error")
        error = raw if isinstance(raw, Mapping) else {}
        message = error.get("message") if isinstance(error.get("message"), str) else f"HTTP {status_code}"
        error_type = error.get("type")
        provider_code = str(error_type) if error_type is not None else None
        override = _ERROR_TYPES.get(provider_code)
        raise_provider_http_error(
            provider=self.provider_name,
            status_code=status_code,
            message=message,
            provider_code=provider_code,
            category_override=override,
        )


_STOP_REASONS: dict[object, FinishReason] = {
    "end_turn": FinishReason.COMPLETE,
    "stop_sequence": FinishReason.STOP,
    "max_tokens": FinishReason.LENGTH,
    "tool_use": FinishReason.TOOL_CALL,
    "pause_turn": FinishReason.PAUSED,
    "refusal": FinishReason.REFUSAL,
    "model_context_window_exceeded": FinishReason.CONTEXT_LIMIT,
}

_ERROR_TYPES: dict[str | None, ProviderErrorCategory] = {
    "authentication_error": ProviderErrorCategory.AUTHENTICATION,
    "permission_error": ProviderErrorCategory.PERMISSION,
    "invalid_request_error": ProviderErrorCategory.INVALID_REQUEST,
    "request_too_large": ProviderErrorCategory.CONTEXT_LIMIT,
    "rate_limit_error": ProviderErrorCategory.RATE_LIMIT,
    "overloaded_error": ProviderErrorCategory.TRANSIENT,
}
