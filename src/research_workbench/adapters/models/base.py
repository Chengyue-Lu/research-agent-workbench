"""Shared safety and validation helpers for concrete model providers."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from research_workbench.adapters.models.http import (
    CredentialProvider,
    CredentialUnavailable,
    HttpRequest,
    HttpResponse,
    HttpTransport,
    HttpTransportError,
    decode_json_object,
    json_body,
)
from research_workbench.adapters.models.port import (
    Capability,
    CapabilityGap,
    DataPolicyGap,
    FinishReason,
    ModelNotSupported,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCategory,
)


def validate_adapter_capabilities(
    supported: frozenset[Capability],
    implemented: frozenset[Capability],
    provider: str,
) -> None:
    impossible = sorted(set(supported) - set(implemented), key=str)
    if impossible:
        raise ValueError(
            f"{provider} adapter cannot claim unimplemented capabilities: "
            + ", ".join(str(item) for item in impossible)
        )
    if Capability.TEXT not in supported:
        raise ValueError(f"{provider} adapter must include text capability")


def preflight(request: ModelRequest, snapshot: ProviderCapabilities) -> None:
    if not snapshot.supports_model(request.model):
        raise ModelNotSupported(snapshot.provider, request.model, snapshot.models)
    gaps = snapshot.gaps_for(request)
    if gaps:
        raise CapabilityGap(snapshot.provider, gaps)
    data_gaps = snapshot.data_policy_gaps_for(request.data_policy)
    if data_gaps:
        raise DataPolicyGap(snapshot.provider, data_gaps)
    if not request.messages:
        raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, "messages must not be empty")
    if request.response_format.kind not in {"text", "json_schema"}:
        raise ProviderError(
            ProviderErrorCategory.UNSUPPORTED,
            f"unsupported response format: {request.response_format.kind}",
        )
    if request.response_format.kind == "json_schema":
        if not request.response_format.name or not isinstance(request.response_format.schema, Mapping):
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                "json_schema response format requires name and schema",
            )
        try:
            Draft202012Validator.check_schema(request.response_format.schema)
        except SchemaError as exc:
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                f"invalid response JSON Schema: {exc.message}",
            ) from exc
    if request.tool_choice.kind not in {"auto", "none", "required", "specific"}:
        raise ProviderError(
            ProviderErrorCategory.INVALID_REQUEST,
            f"unsupported tool choice: {request.tool_choice.kind}",
        )
    if request.tool_choice.kind == "specific":
        if not request.tool_choice.name:
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                "specific tool choice requires a tool name",
            )
        names = {tool.name for tool in request.tools}
        if request.tool_choice.name not in names:
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                f"specific tool choice names an unavailable tool: {request.tool_choice.name}",
            )
    elif request.tool_choice.name is not None:
        raise ProviderError(
            ProviderErrorCategory.INVALID_REQUEST,
            f"tool choice {request.tool_choice.kind} must not include a tool name",
        )
    if request.tool_choice.kind != "auto" and not request.tools:
        raise ProviderError(
            ProviderErrorCategory.INVALID_REQUEST,
            f"tool choice {request.tool_choice.kind} requires at least one tool definition",
        )
    if request.max_output_tokens is not None and request.max_output_tokens <= 0:
        raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, "max_output_tokens must be positive")
    if request.temperature is not None and not 0 <= request.temperature <= 2:
        raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, "temperature must be between 0 and 2")
    tool_names: set[str] = set()
    for tool in request.tools:
        if not tool.name.strip() or not tool.description.strip():
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                "tool name and description must be non-empty",
            )
        if tool.name in tool_names:
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                f"duplicate tool definition: {tool.name}",
            )
        tool_names.add(tool.name)
        try:
            Draft202012Validator.check_schema(tool.input_schema)
        except SchemaError as exc:
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                f"invalid input schema for tool {tool.name!r}: {exc.message}",
            ) from exc
    for message in request.messages:
        if message.role not in {"system", "developer", "user", "assistant", "tool"}:
            raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, f"unsupported message role: {message.role}")
        if not message.content:
            raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, "message content must not be empty")
        for block in message.content:
            if block.kind == "text" and block.text is None:
                raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, "text block lacks text")
            if block.kind in {"tool_call", "tool_result"} and not isinstance(block.data, Mapping):
                raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, f"{block.kind} block lacks data")
            if block.kind == "tool_call" and isinstance(block.data, Mapping):
                if not _has_text(block.data.get("call_id")) or not _has_text(block.data.get("name")):
                    raise ProviderError(
                        ProviderErrorCategory.INVALID_REQUEST,
                        "tool_call block requires non-empty call_id and name",
                    )
                if not isinstance(block.data.get("arguments"), Mapping):
                    raise ProviderError(
                        ProviderErrorCategory.INVALID_REQUEST,
                        "tool_call block requires object arguments",
                    )
            if block.kind == "tool_result" and isinstance(block.data, Mapping):
                if not _has_text(block.data.get("call_id")) or "output" not in block.data:
                    raise ProviderError(
                        ProviderErrorCategory.INVALID_REQUEST,
                        "tool_result block requires non-empty call_id and output",
                    )


def provider_extension(request: ModelRequest, provider: str) -> Mapping[str, Any]:
    foreign = sorted(set(request.extensions) - {provider})
    if foreign:
        raise ProviderError(
            ProviderErrorCategory.UNSUPPORTED,
            "request carries extensions for a different provider: " + ", ".join(foreign),
        )
    value = request.extensions.get(provider, {})
    if not isinstance(value, Mapping):
        raise ProviderError(ProviderErrorCategory.INVALID_REQUEST, f"extensions.{provider} must be an object")
    return value


def perform_json_request(
    *,
    provider: str,
    transport: HttpTransport,
    credential: CredentialProvider,
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, object],
    timeout_seconds: float,
) -> tuple[HttpResponse, Mapping[str, object]]:
    try:
        secret = credential.resolve()
    except CredentialUnavailable as exc:
        raise ProviderError(ProviderErrorCategory.AUTHENTICATION, str(exc)) from exc
    authenticated = {key: value.replace("{API_KEY}", secret) for key, value in headers.items()}
    try:
        response = transport.send(
            HttpRequest("POST", url, authenticated, json_body(payload), timeout_seconds)
        )
    except HttpTransportError as exc:
        category = ProviderErrorCategory.TRANSIENT if exc.retryable else ProviderErrorCategory.INVALID_REQUEST
        raise ProviderError(category, str(exc), retryable=exc.retryable) from exc
    try:
        document = decode_json_object(response.body, provider=provider)
    except ValueError as exc:
        if response.status_code >= 400:
            category, retryable = generic_error_category(response.status_code)
            raise ProviderError(
                category,
                f"{provider} API returned HTTP {response.status_code} with a non-JSON error body",
                retryable=retryable,
                status_code=response.status_code,
            ) from exc
        raise ProviderError(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            str(exc),
            status_code=response.status_code,
        ) from exc
    return response, document


def generic_error_category(status_code: int) -> tuple[ProviderErrorCategory, bool]:
    if status_code == 401:
        return ProviderErrorCategory.AUTHENTICATION, False
    if status_code == 403:
        return ProviderErrorCategory.PERMISSION, False
    if status_code == 429:
        return ProviderErrorCategory.RATE_LIMIT, True
    if status_code in {408, 409, 425}:
        return ProviderErrorCategory.TRANSIENT, True
    if status_code >= 500:
        return ProviderErrorCategory.TRANSIENT, True
    if 400 <= status_code < 500:
        return ProviderErrorCategory.INVALID_REQUEST, False
    return ProviderErrorCategory.UNKNOWN, False


def raise_provider_http_error(
    *,
    provider: str,
    status_code: int,
    message: str,
    provider_code: str | None,
    category_override: ProviderErrorCategory | None = None,
) -> None:
    category, retryable = generic_error_category(status_code)
    if category_override is not None:
        category = category_override
        retryable = category in {ProviderErrorCategory.RATE_LIMIT, ProviderErrorCategory.TRANSIENT}
    raise ProviderError(
        category,
        f"{provider} API request failed: {message}",
        retryable=retryable,
        status_code=status_code,
        provider_code=provider_code,
    )


_JSON_FENCE = re.compile(r"^```[^\S\n]*(?:json|JSON)?[^\S\n]*\n(?P<body>.*?)\n?[^\S\n]*```$", re.DOTALL)


def _structured_json_text(raw: str) -> str:
    """Tolerate one surrounding Markdown code fence around the JSON payload."""

    candidate = raw.strip()
    match = _JSON_FENCE.match(candidate)
    if match:
        return match.group("body").strip()
    return candidate


def validate_structured_response(request: ModelRequest, response: ModelResponse) -> ModelResponse:
    if request.response_format.kind != "json_schema" or response.finish_reason not in {
        FinishReason.COMPLETE,
        FinishReason.STOP,
    }:
        return response
    schema = request.response_format.schema
    assert isinstance(schema, Mapping)
    text = _structured_json_text(
        "".join(block.text or "" for block in response.output if block.kind == "text")
    )
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            f"{response.provider} returned invalid JSON for structured output "
            f"(first 80 chars: {text[:80]!r})",
        ) from exc
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        pointer = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in first.absolute_path
        )
        raise ProviderError(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            f"{response.provider} structured output failed local validation at {pointer}: {first.message}",
        )
    return response


def validate_response_contract(request: ModelRequest, response: ModelResponse) -> ModelResponse:
    """Apply provider-independent checks before output can reach a tool runner."""

    definitions = {tool.name: tool for tool in request.tools}
    seen_ids: set[str] = set()
    for call in response.tool_calls:
        if call.call_id in seen_ids:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"{response.provider} returned duplicate tool call id: {call.call_id}",
            )
        seen_ids.add(call.call_id)
        definition = definitions.get(call.name)
        if definition is None:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"{response.provider} called undeclared tool: {call.name}",
            )
        errors = sorted(
            Draft202012Validator(definition.input_schema).iter_errors(call.arguments),
            key=lambda item: list(item.absolute_path),
        )
        if errors:
            first = errors[0]
            pointer = "$" + "".join(
                f"[{part}]" if isinstance(part, int) else f".{part}" for part in first.absolute_path
            )
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"{response.provider} tool call {call.name!r} failed local validation at "
                f"{pointer}: {first.message}",
            )
    if response.tool_calls and request.tool_choice.kind == "none":
        raise ProviderError(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            f"{response.provider} returned tool calls when tool_choice was none",
        )
    if request.tool_choice.kind in {"required", "specific"} and not response.tool_calls:
        raise ProviderError(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            f"{response.provider} did not return a required tool call",
        )
    if request.tool_choice.kind == "specific" and any(
        call.name != request.tool_choice.name for call in response.tool_calls
    ):
        raise ProviderError(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            f"{response.provider} called a tool other than the specifically selected tool",
        )
    if response.finish_reason == FinishReason.TOOL_CALL and not response.tool_calls:
        raise ProviderError(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            f"{response.provider} reported tool_call without tool calls",
        )
    return validate_structured_response(request, response)


def text_from_output(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def reject_unknown_extension_keys(
    extension: Mapping[str, Any],
    *,
    provider: str,
    allowed: frozenset[str],
) -> None:
    unknown = sorted(set(extension) - set(allowed))
    if unknown:
        raise ProviderError(
            ProviderErrorCategory.UNSUPPORTED,
            f"unsupported {provider} extension keys: " + ", ".join(unknown),
        )


def require_object(value: object, *, provider: str, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderError(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            f"{provider} response field {field} must be an object",
        )
    return value


def require_list(value: object, *, provider: str, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProviderError(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            f"{provider} response field {field} must be an array",
        )
    return value


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _environment_name(value: object, field: str) -> str:
    name = _nonempty_string(value, field)
    if not name.replace("_", "").isalnum():
        raise ValueError(f"{field} must contain only letters, digits, and underscores")
    return name


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
