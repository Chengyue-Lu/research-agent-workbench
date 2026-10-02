"""Pure, explicit wire mappings for validated, model-bound API profiles.

These functions never resolve credentials, choose a provider, or perform I/O.
Only the documented nonstream text/client-tool/basic-schema subset is encoded.
Profile validation, account capabilities and exact source binding belong to the
caller; an offline wire fixture is not a remote conformance result.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from research_workbench.adapters.models.base import preflight, validate_response_contract
from research_workbench.adapters.models.port import (
    Capability, ContentBlock, FinishReason, ModelRequest, ModelResponse,
    ProviderCapabilities, ProviderError, ProviderErrorCategory, ToolCall, Usage,
)

CODEC_VERSION = "1.0.0"
FAMILIES = frozenset({"responses", "chat-completions", "anthropic-messages", "gemini-generate-content"})
POLICY_IDS = MappingProxyType({family: MappingProxyType({
    f"{kind}_policy_id": f"{family}:{kind}:v1"
    for kind in ("role", "tool", "schema", "usage", "finish", "error")}) for family in FAMILIES})
PARAMETER_POLICY_IDS = MappingProxyType({family: f"{family}:parameters:v1" for family in FAMILIES})
GEMMA_TEXT_PROFILE_ID = "google-gemma4-text-minimal-v1"
GEMMA_TEXT_MODEL = "gemma-4-26b-a4b-it"
# Google documents minimal=off specifically for Gemma 4. Gemini 3 minimal is
# still thinking, so this policy must remain bound to the exact model tuple.
GEMMA_TEXT_PARAMETERS = MappingProxyType({
    ("google", "gemini-generate-content", GEMMA_TEXT_MODEL, "standard"): MappingProxyType({
        "thinkingConfig": MappingProxyType({"thinkingLevel": "minimal"}),
    }),
})
NATIVE_PARAMETER_REGISTRY = MappingProxyType({
    ("deepseek", "responses", "nonthinking"): MappingProxyType({"reasoning": MappingProxyType({"effort": "none"})}),
    ("deepseek", "chat-completions", "nonthinking"): MappingProxyType({"thinking": MappingProxyType({"type": "disabled"})}),
    ("alibaba-dashscope", "chat-completions", "nonthinking"): MappingProxyType({"enable_thinking": False}),
    ("zhipu", "chat-completions", "nonthinking"): MappingProxyType({"thinking": MappingProxyType({"type": "disabled"})}),
    ("moonshot", "chat-completions", "nonthinking"): MappingProxyType({"thinking": MappingProxyType({"type": "disabled"})}),
    ("minimax", "responses", "nonthinking"): MappingProxyType({"reasoning": MappingProxyType({"effort": "none"})}),
    ("bytedance-ark", "chat-completions", "nonthinking"): MappingProxyType({"thinking": MappingProxyType({"type": "disabled"})}),
})
NATIVE_MODEL_REGISTRY = MappingProxyType({
    ("deepseek", "responses", "nonthinking"): frozenset({"deepseek-flash"}),
    ("deepseek", "chat-completions", "nonthinking"): frozenset({"deepseek-flash"}),
    ("alibaba-dashscope", "chat-completions", "nonthinking"): frozenset({"qwen3.8-max"}),
    ("zhipu", "chat-completions", "nonthinking"): frozenset({"glm-5.2"}),
    ("moonshot", "chat-completions", "nonthinking"): frozenset({"kimi-k2.6"}),
    ("minimax", "responses", "nonthinking"): frozenset({"MiniMax-M3"}),
    ("bytedance-ark", "chat-completions", "nonthinking"): frozenset({"seed-2-0-lite-260228"}),
})
_CODEC_CAPABILITIES = frozenset({Capability.TEXT, Capability.TOOLS, Capability.PARALLEL_TOOLS, Capability.STRUCTURED_OUTPUT})
_SCHEMA_KEYS = frozenset({"type", "properties", "required", "additionalProperties", "items", "enum", "description"})
_SCHEMA_TYPES = frozenset({"object", "string", "number", "integer", "boolean", "array"})


def _error(message: str, *, request: bool = False, unsupported: bool = False) -> None:
    category = (ProviderErrorCategory.UNSUPPORTED if unsupported else
                ProviderErrorCategory.INVALID_REQUEST if request else
                ProviderErrorCategory.CONTRACT_VIOLATION)
    raise ProviderError(category, message)


def _object(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _error("wire value must be an object")
    return value


def _nullable_object(value: object) -> Mapping[str, Any]:
    return {} if value is None else _object(value)


def _terminal(value: object, policy: Mapping[str, FinishReason]) -> FinishReason:
    if not isinstance(value, str):
        _error("provider stop reason must be an explicit string")
    return policy.get(value, FinishReason.UNKNOWN)


def _array(value: object) -> Sequence[Any]:
    if not isinstance(value, (list, tuple)):
        _error("wire value must be an array")
    return value


def _string(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        _error("wire identity must be a non-empty string")
    return value


def _json_value(value: object) -> Any:
    """Detach deep-frozen mappings without accepting non-JSON values."""
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            _error("JSON object keys must be strings", request=True)
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    _error("wire value is not finite JSON", request=True)


def _json_text(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(_json_value(value), ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _parsed_json(value: object) -> Any:
    if not isinstance(value, str):
        _error("wire JSON value must be a string")
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError("duplicate JSON member")
            result[key] = item
        return result
    invalid_json = False
    parsed = None
    try:
        parsed = json.loads(value, object_pairs_hook=unique_pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, TypeError, RecursionError):
        invalid_json = True
    # Raising after the handler releases JSONDecodeError.doc and exception chains.
    if invalid_json:
        _error("wire text is not valid finite JSON with unique members")
    return parsed


def _arguments(value: object) -> Mapping[str, Any]:
    return _object(_parsed_json(value))


@dataclass(frozen=True)
class _Profile:
    provider: str
    family: str
    model: str
    mode: str
    role_policy: str
    tool_policy: str
    schema_policy: str
    beta: bool
    capabilities: frozenset[Capability]


def _profile(document: Mapping[str, object]) -> _Profile:
    identity = _object(document.get("identity"))
    protocol = _object(document.get("protocol"))
    model = _object(document.get("model"))
    generation = _object(document.get("generation"))
    mapping = _object(document.get("mapping"))
    implementation = _object(document.get("implementation"))
    endpoint = _object(document.get("endpoint"))
    provider, family = _string(identity.get("provider")), _string(protocol.get("family"))
    if family not in FAMILIES:
        _error("profile wire family is not implemented", unsupported=True)
    if dict(mapping) != dict(POLICY_IDS[family]):
        _error("profile mapping policy is not implemented", unsupported=True)
    if implementation.get("codec_version") != CODEC_VERSION:
        _error("profile codec version does not match this implementation", unsupported=True)
    mode, parameter = generation.get("mode"), generation.get("parameter_profile_id")
    if parameter != PARAMETER_POLICY_IDS[family]:
        _error("generation parameter policy is not implemented", unsupported=True)
    if generation.get("continuation_policy") != "local-messages-only":
        _error("provider continuation is not implemented", unsupported=True)
    if provider == "deepseek":
        if (provider, family, mode) not in NATIVE_PARAMETER_REGISTRY:
            _error("DeepSeek requires the explicit native nonthinking profile", unsupported=True)
    elif mode == "nonthinking" and (provider, family, mode) not in NATIVE_PARAMETER_REGISTRY:
        _error("this vendor/model nonthinking control is not verified in this codec slice", unsupported=True)
    elif mode not in {"standard", "nonthinking"}:
        _error("generation mode is not implemented", unsupported=True)
    requested_model = _string(model.get("requested_id"))
    if mode == "nonthinking" and requested_model not in NATIVE_MODEL_REGISTRY[(provider, family, mode)]:
        _error("native nonthinking is not implemented for this exact model", unsupported=True)
    if any(isinstance(gap, str) and gap.startswith("blocking:") for gap in implementation.get("known_gaps", ())):
        _error("profile has an explicit blocking implementation gap", unsupported=True)
    invalid_capability = False
    supported = frozenset()
    try:
        supported = frozenset(Capability(value) for value in _array(implementation.get("capabilities")))
    except (ValueError, TypeError):
        invalid_capability = True
    if invalid_capability:
        _error("profile capability is not implemented", unsupported=True)
    if not supported <= _CODEC_CAPABILITIES:
        _error("profile claims capabilities outside this codec slice", unsupported=True)
    if document.get("profile_id") == GEMMA_TEXT_PROFILE_ID or requested_model == GEMMA_TEXT_MODEL:
        if (document.get("profile_id") != GEMMA_TEXT_PROFILE_ID
                or (provider, family, requested_model, mode) not in GEMMA_TEXT_PARAMETERS
                or supported != frozenset({Capability.TEXT})):
            _error("Gemma Text policy requires its exact profile/model and Text-only capability", unsupported=True)
    return _Profile(provider, family, requested_model, str(mode),
                    str(mapping["role_policy_id"]), str(mapping["tool_policy_id"]),
                    str(mapping["schema_policy_id"]), endpoint.get("base_path") == "/beta", supported)


def _schema(schema: object) -> dict[str, object]:
    value = _object(schema)
    if not set(value) <= _SCHEMA_KEYS or value.get("type") not in _SCHEMA_TYPES:
        _error("JSON Schema keyword/type is outside the implemented wire dialect", unsupported=True)
    result = _json_value(value)
    if value["type"] == "object":
        properties = _object(value.get("properties"))
        required = _array(value.get("required"))
        if value.get("additionalProperties") is not False or set(required) != set(properties) or len(required) != len(properties):
            _error("wire object schema requires every property and forbids additional properties", request=True)
        result["properties"] = {name: _schema(child) for name, child in properties.items()}
    elif "properties" in value or "required" in value or "additionalProperties" in value:
        _error("object-only schema keywords require object type", request=True)
    if value["type"] == "array":
        result["items"] = _schema(value.get("items"))
    elif "items" in value:
        _error("items requires array type", request=True)
    if "enum" in value and not _array(value["enum"]):
        _error("wire schema enum must not be empty", request=True)
    return result


def _strict_flag(request: ModelRequest, profile: _Profile) -> bool:
    """Never silently discard a caller's remote strict-tool request."""
    native = (
        profile.provider == "openai" and profile.family in {"responses", "chat-completions"}
        or profile.provider == "anthropic" and profile.family == "anthropic-messages"
        or profile.provider == "deepseek" and profile.family == "chat-completions" and profile.beta
    )
    if any(tool.strict for tool in request.tools) and not native:
        _error("native strict client tools are not implemented for this exact profile", unsupported=True)
    if profile.provider == "deepseek" and native and any(not tool.strict for tool in request.tools):
        _error("DeepSeek Beta strict profile requires all functions strict", request=True)
    return native


def _validate_request(request: ModelRequest, profile: _Profile) -> None:
    if profile.provider == "openrouter":
        _error("OpenRouter requires an independently frozen upstream/routing policy not implemented by this slice", unsupported=True)
    if request.extensions or request.metadata or request.reasoning_effort is not None:
        _error("request extensions, metadata or public reasoning controls are outside this profile slice", unsupported=True)
    if request.max_output_tokens is not None and (isinstance(request.max_output_tokens, bool) or not isinstance(request.max_output_tokens, int)):
        _error("max_output_tokens must be a positive integer", request=True)
    if request.temperature is not None and (isinstance(request.temperature, bool) or not isinstance(request.temperature, (int, float))):
        _error("temperature must be a finite number", request=True)
    snapshot = ProviderCapabilities(provider=profile.provider, adapter_version=CODEC_VERSION,
                                    supported=profile.capabilities, models=(profile.model,))
    # Preserve hard constraints. This pure descriptor has no account evidence;
    # hard DataPolicy requests remain gaps until a separately evidenced interface exists.
    preflight_error = None
    try:
        preflight(request, snapshot)
    except ProviderError as error:
        preflight_error = error.category
    if preflight_error is not None:
        raise ProviderError(preflight_error, "request failed codec preflight")
    if profile.provider == "moonshot" and (request.temperature is not None or request.tool_choice.kind in {"required", "specific"}):
        _error("Moonshot parameter or tool-choice subset is not verified for this profile", unsupported=True)
    if profile.provider == "minimax" and request.tool_choice.kind in {"required", "specific"}:
        _error("MiniMax tool choice is limited to the documented auto/none subset", unsupported=True)
    if request.response_format.kind == "json_schema":
        if profile.provider == "deepseek" and profile.family == "chat-completions":
            _error("DeepSeek Chat JSON Object is not JSON Schema output", unsupported=True)
        _schema(request.response_format.schema)
    _strict_flag(request, profile)
    pending: dict[str, str] = {}
    seen_call_ids: set[str] = set()
    for message in request.messages:
        if pending and message.role != "tool":
            _error("history requires tool results before another conversation turn", request=True)
        if message.role not in {"system", "developer", "user", "assistant", "tool"} or message.name is not None:
            _error("message role/name is outside the implemented profile", unsupported=True)
        if message.role == "developer" and (profile.provider != "openai"
                                             or profile.family in {"anthropic-messages", "gemini-generate-content"}):
            _error("developer semantics are not native to this profile", unsupported=True)
        for block in message.content:
            if block.kind == "text":
                if message.role == "tool":
                    _error("tool messages require tool_result blocks", request=True)
            elif block.kind == "tool_call":
                data = _object(block.data)
                if message.role != "assistant" or set(data) - {"call_id", "name", "arguments"}:
                    _error("tool_call role/fields are invalid", request=True)
                call_id, name = _string(data.get("call_id")), _string(data.get("name"))
                if call_id in seen_call_ids or name not in {tool.name for tool in request.tools}:
                    _error("history tool call is duplicated or undeclared", request=True)
                _object(data.get("arguments"))
                pending[call_id] = name
                seen_call_ids.add(call_id)
            elif block.kind == "tool_result":
                data = _object(block.data)
                if message.role != "tool" or set(data) - {"call_id", "name", "output", "is_error"}:
                    _error("tool_result role/fields are invalid", request=True)
                call_id = _string(data.get("call_id"))
                if call_id not in pending or data.get("name", pending[call_id]) != pending[call_id] or "output" not in data:
                    _error("tool_result requires a matching prior call", request=True)
                if "is_error" in data and not isinstance(data["is_error"], bool):
                    _error("tool_result is_error must be boolean", request=True)
                del pending[call_id]
            else:
                _error("content block is outside the implemented nonstream subset", unsupported=True)
    if pending:
        _error("request history has unanswered tool calls", request=True)


def _result(data: Mapping[str, Any]) -> object:
    return {"error": data["output"]} if data.get("is_error") else data["output"]


def encode_profile_request(request: ModelRequest, profile: Mapping[str, object]) -> dict[str, object]:
    selected = _profile(profile)
    _validate_request(request, selected)
    if selected.family == "responses":
        return _encode_responses(request, selected)
    if selected.family == "chat-completions":
        return _encode_chat(request, selected)
    if selected.family == "anthropic-messages":
        return _encode_messages(request, selected)
    return _encode_gemini(request, selected)


def _encode_responses(request: ModelRequest, profile: _Profile) -> dict[str, object]:
    items: list[dict[str, object]] = []
    for message in request.messages:
        text: list[str] = []
        def flush() -> None:
            if text:
                items.append({"role": message.role, "content": "\n".join(text)})
                text.clear()
        for block in message.content:
            if block.kind == "text":
                text.append(block.text or "")
                continue
            flush()
            data = _object(block.data)
            if block.kind == "tool_call":
                items.append({"type": "function_call", "call_id": data["call_id"], "name": data["name"],
                              "arguments": _json_text(data["arguments"])})
            else:
                items.append({"type": "function_call_output", "call_id": data["call_id"], "output": _json_text(_result(data))})
        flush()
    payload: dict[str, object] = {"model": request.model, "input": items}
    if profile.provider == "openai":
        payload["store"] = False
    if request.tools:
        native = _strict_flag(request, profile)
        tools = []
        for tool in request.tools:
            value: dict[str, object] = {"type": "function", "name": tool.name, "description": tool.description,
                                        "parameters": _schema(tool.input_schema)}
            if native:
                value["strict"] = tool.strict
            tools.append(value)
        payload["tools"] = tools
        payload["tool_choice"] = ({"type": "function", "name": request.tool_choice.name}
                                   if request.tool_choice.kind == "specific" else request.tool_choice.kind)
    if request.response_format.kind == "json_schema":
        value = {"type": "json_schema", "name": request.response_format.name, "schema": _schema(request.response_format.schema)}
        if profile.provider == "openai":
            value["strict"] = True
        payload["text"] = {"format": value}
    if request.max_output_tokens is not None:
        payload["max_output_tokens"] = request.max_output_tokens
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    payload.update(_json_value(NATIVE_PARAMETER_REGISTRY.get((profile.provider, profile.family, profile.mode), {})))
    return payload


def _encode_chat(request: ModelRequest, profile: _Profile) -> dict[str, object]:
    messages: list[dict[str, object]] = []
    for message in request.messages:
        if message.role == "tool":
            for block in message.content:
                data = _object(block.data)
                messages.append({"role": "tool", "tool_call_id": data["call_id"], "content": _json_text(_result(data))})
            continue
        text = [block.text or "" for block in message.content if block.kind == "text"]
        calls = []
        for block in message.content:
            if block.kind == "tool_call":
                data = _object(block.data)
                calls.append({"id": data["call_id"], "type": "function", "function": {
                    "name": data["name"], "arguments": _json_text(data["arguments"])}})
        value: dict[str, object] = {"role": message.role, "content": "\n".join(text) if text else None}
        if calls:
            value["tool_calls"] = calls
        messages.append(value)
    payload: dict[str, object] = {"model": request.model, "messages": messages, "stream": False}
    if request.tools:
        native = _strict_flag(request, profile)
        tools = []
        for tool in request.tools:
            value = {"name": tool.name, "description": tool.description, "parameters": _schema(tool.input_schema)}
            if native:
                value["strict"] = tool.strict
            tools.append({"type": "function", "function": value})
        payload["tools"] = tools
        payload["tool_choice"] = ({"type": "function", "function": {"name": request.tool_choice.name}}
                                   if request.tool_choice.kind == "specific" else request.tool_choice.kind)
    if request.response_format.kind == "json_schema":
        schema_format = {"name": request.response_format.name, "schema": _schema(request.response_format.schema)}
        if profile.provider == "openai":
            schema_format["strict"] = True
        payload["response_format"] = {"type": "json_schema", "json_schema": schema_format}
    if request.max_output_tokens is not None:
        # The two APIs use different, documented budget parameter names.
        payload["max_tokens" if profile.provider != "openai" else "max_completion_tokens"] = request.max_output_tokens
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    payload.update(_json_value(NATIVE_PARAMETER_REGISTRY.get((profile.provider, profile.family, profile.mode), {})))
    return payload


def _encode_messages(request: ModelRequest, profile: _Profile) -> dict[str, object]:
    if request.max_output_tokens is None:
        _error("Messages requires an explicit max_output_tokens budget", request=True)
    system: list[dict[str, object]] = []
    messages: list[dict[str, object]] = []
    for message in request.messages:
        content = []
        for block in message.content:
            data = _object(block.data) if block.kind != "text" else {}
            if block.kind == "text":
                content.append({"type": "text", "text": block.text or ""})
            elif block.kind == "tool_call":
                content.append({"type": "tool_use", "id": data["call_id"], "name": data["name"],
                                "input": _json_value(data["arguments"])})
            else:
                content.append({"type": "tool_result", "tool_use_id": data["call_id"],
                                "content": _json_text(data["output"]), "is_error": data.get("is_error", False)})
        if message.role == "system":
            system.extend(content)
        else:
            messages.append({"role": "assistant" if message.role == "assistant" else "user", "content": content})
    if not messages:
        _error("Messages requires a non-system message", request=True)
    payload: dict[str, object] = {"model": request.model, "messages": messages, "max_tokens": request.max_output_tokens}
    if system:
        payload["system"] = system
    if request.tools:
        native = _strict_flag(request, profile)
        tools = []
        for tool in request.tools:
            value = {"name": tool.name, "description": tool.description, "input_schema": _schema(tool.input_schema)}
            if native:
                value["strict"] = tool.strict
            tools.append(value)
        payload["tools"] = tools
        payload["tool_choice"] = ({"type": "tool", "name": request.tool_choice.name}
                                   if request.tool_choice.kind == "specific" else
                                   {"type": "any" if request.tool_choice.kind == "required" else request.tool_choice.kind})
    if request.response_format.kind == "json_schema":
        payload["output_config"] = {"format": {"type": "json_schema", "schema": _schema(request.response_format.schema)}}
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    return payload


def _encode_gemini(request: ModelRequest, profile: _Profile) -> dict[str, object]:
    contents, system = [], []
    known_calls: dict[str, str] = {}
    for message in request.messages:
        parts = []
        for block in message.content:
            data = _object(block.data) if block.kind != "text" else {}
            if block.kind == "text":
                parts.append({"text": block.text or ""})
            elif block.kind == "tool_call":
                known_calls[str(data["call_id"])] = str(data["name"])
                parts.append({"functionCall": {"id": data["call_id"], "name": data["name"],
                                               "args": _json_value(data["arguments"])}})
            else:
                result = _result(data)
                parts.append({"functionResponse": {"id": data["call_id"], "name": known_calls[str(data["call_id"])],
                    "response": _json_value(result) if isinstance(result, Mapping) else {"result": _json_value(result)}}})
        if message.role == "system":
            system.extend(parts)
        else:
            contents.append({"role": "model" if message.role == "assistant" else "user", "parts": parts})
    if not contents:
        _error("generateContent requires a non-system message", request=True)
    payload: dict[str, object] = {"contents": contents}
    if system:
        payload["systemInstruction"] = {"parts": system}
    if request.tools:
        payload["tools"] = [{"functionDeclarations": [{"name": tool.name, "description": tool.description,
            "parametersJsonSchema": _schema(tool.input_schema)} for tool in request.tools]}]
        choice: dict[str, object] = {"mode": {"auto": "AUTO", "none": "NONE", "required": "ANY", "specific": "ANY"}[request.tool_choice.kind]}
        if request.tool_choice.kind == "specific":
            choice["allowedFunctionNames"] = [request.tool_choice.name]
        payload["toolConfig"] = {"functionCallingConfig": choice}
    generation: dict[str, object] = {}
    generation.update(_json_value(GEMMA_TEXT_PARAMETERS.get(
        (profile.provider, profile.family, profile.model, profile.mode), {})))
    if request.max_output_tokens is not None:
        generation["maxOutputTokens"] = request.max_output_tokens
    if request.temperature is not None:
        generation["temperature"] = request.temperature
    if request.response_format.kind == "json_schema":
        generation.update(responseMimeType="application/json", responseJsonSchema=_schema(request.response_format.schema))
    if generation:
        payload["generationConfig"] = generation
    return payload


def _count(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        _error("provider token counter must be a nonnegative integer or unavailable")
    return value


def _usage(document: Mapping[str, Any], profile: _Profile) -> tuple[Usage, dict[str, object]]:
    raw = document.get("usageMetadata" if profile.family == "gemini-generate-content" else "usage")
    if raw is None:
        return Usage(), {"usage_available": False}
    value = _object(raw)
    details: dict[str, object] = {"usage_available": True}
    cached = reasoning = None
    if profile.family == "responses":
        incoming, outgoing = _count(value.get("input_tokens")), _count(value.get("output_tokens"))
        cached = _count(_nullable_object(value.get("input_tokens_details")).get("cached_tokens"))
        reasoning = _count(_nullable_object(value.get("output_tokens_details")).get("reasoning_tokens"))
    elif profile.family == "chat-completions":
        incoming, outgoing = _count(value.get("prompt_tokens")), _count(value.get("completion_tokens"))
        cached = _count(_nullable_object(value.get("prompt_tokens_details")).get("cached_tokens"))
        legacy_cache = _count(value.get("prompt_cache_hit_tokens"))
        if cached is not None and legacy_cache is not None and cached != legacy_cache:
            _error("provider cache counters disagree")
        cached = cached if cached is not None else legacy_cache
        reasoning = _count(_nullable_object(value.get("completion_tokens_details")).get("reasoning_tokens"))
    elif profile.family == "anthropic-messages":
        uncached, cached, created = (_count(value.get(name)) for name in
                                     ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        incoming = uncached + cached + created if None not in (uncached, cached, created) else None
        outgoing = _count(value.get("output_tokens"))
        details.update(uncached_input_tokens=uncached, cache_creation_input_tokens=created)
    else:
        incoming = _count(value.get("promptTokenCount"))
        candidates, reasoning = _count(value.get("candidatesTokenCount")), _count(value.get("thoughtsTokenCount"))
        outgoing = candidates + reasoning if candidates is not None and reasoning is not None else None
        cached = _count(value.get("cachedContentTokenCount"))
        details["candidate_output_tokens"] = candidates
    if incoming is not None and cached is not None and cached > incoming:
        _error("cached input exceeds total input")
    if outgoing is not None and reasoning is not None and reasoning > outgoing:
        _error("reasoning output exceeds total output")
    reported_total = _count(value.get("totalTokenCount" if profile.family == "gemini-generate-content" else "total_tokens"))
    if reported_total is not None and incoming is not None and outgoing is not None and reported_total != incoming + outgoing:
        _error("provider total token count contradicts its components")
    details["reported_total_tokens"] = reported_total
    cost = value.get("cost")
    if cost is not None and (not isinstance(cost, (int, float)) or isinstance(cost, bool) or not math.isfinite(cost) or cost < 0):
        _error("provider cost must be a nonnegative finite number or unavailable")
    currency = value.get("currency")
    if currency is not None and (not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha() or not currency.isupper()):
        _error("provider currency must be an explicit currency code or unavailable")
    return Usage(incoming, outgoing, cached, reasoning, float(cost) if cost is not None else None, currency), details


def _call(identifier: object, name: object, arguments: object, *, string_arguments: bool = False) -> ToolCall:
    value = _arguments(arguments) if string_arguments else _object(arguments)
    return ToolCall(_string(identifier), _string(name), _json_value(value))


def decode_profile_response(request: ModelRequest, document: Mapping[str, object], profile: Mapping[str, object]) -> ModelResponse:
    selected, value = _profile(profile), _object(document)
    _validate_request(request, selected)
    if value.get("error") is not None:
        _error("provider returned an error envelope")
    if selected.family == "responses":
        result = _decode_responses(value, selected)
    elif selected.family == "chat-completions":
        result = _decode_chat(value, selected)
    elif selected.family == "anthropic-messages":
        result = _decode_messages(value, selected)
    else:
        result = _decode_gemini(value, selected)
    if len(result.tool_calls) > 1 and Capability.PARALLEL_TOOLS not in selected.capabilities:
        _error("parallel client tools were not declared")
    if result.tool_calls and result.finish_reason != FinishReason.TOOL_CALL:
        _error("non-tool terminal state cannot authorize client tools")
    if not result.tool_calls and result.finish_reason == FinishReason.TOOL_CALL:
        _error("tool finish lacks client calls")
    if request.response_format.kind == "json_schema" and result.finish_reason in {FinishReason.COMPLETE, FinishReason.STOP}:
        # Base local schema validation remains mandatory; reject non-JSON constants
        # and ambiguous duplicate members before its more permissive JSON parser.
        _parsed_json("".join(block.text or "" for block in result.output if block.kind == "text"))
    contract_error = None
    validated = result
    try:
        validated = validate_response_contract(request, result)
    except ProviderError as error:
        contract_error = error.category
    if contract_error is not None:
        raise ProviderError(contract_error, "response failed local contract validation")
    return validated


def _response(document: Mapping[str, Any], profile: _Profile, output: list[ContentBlock], calls: list[ToolCall],
              finish: FinishReason, *, gemini: bool = False, warnings: tuple[str, ...] = ()) -> ModelResponse:
    if finish == FinishReason.UNKNOWN:
        _error("provider stop reason is outside the implemented terminal states", unsupported=True)
    usage, details = _usage(document, profile)
    identity = _string(document.get("responseId" if gemini else "id"))
    model = _string(document.get("modelVersion" if gemini else "model"))
    # Keep only typed/safe metadata; never retain raw errors/reasoning/signatures.
    metadata = {"wire_family": profile.family, "usage_components": details}
    return ModelResponse(identity, profile.provider, model, tuple(output), finish, tuple(calls), usage, warnings, metadata)


def _decode_responses(document: Mapping[str, Any], profile: _Profile) -> ModelResponse:
    status = document.get("status")
    if status not in ("completed", "incomplete"):
        _error("Responses status is not a completed or recognized incomplete result")
    incomplete_finish = None
    if status == "incomplete":
        reason = _object(document.get("incomplete_details", {})).get("reason")
        incomplete_finish = _terminal(reason, {"max_output_tokens": FinishReason.LENGTH, "content_filter": FinishReason.REFUSAL,
                                      "safety": FinishReason.REFUSAL})
    output, calls = [], []
    refusal = False
    for raw in _array(document.get("output")):
        item = _object(raw)
        partial_text = (item.get("type") == "message" and item.get("status") == "incomplete"
                        and incomplete_finish == FinishReason.LENGTH)
        if item.get("status", "completed") != "completed" and not partial_text:
            _error("response item is not complete")
        if item.get("type") == "message":
            if item.get("role") != "assistant":
                _error("Responses output role must be assistant")
            for raw_part in _array(item.get("content")):
                part = _object(raw_part)
                if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    output.append(ContentBlock("text", text=part["text"]))
                elif not partial_text and part.get("type") == "refusal" and isinstance(part.get("refusal"), str):
                    refusal = True
                    output.append(ContentBlock("refusal", text=part["refusal"]))
                else:
                    _error("Responses content kind is outside the implemented subset", unsupported=True)
        elif item.get("type") == "function_call":
            calls.append(_call(item.get("call_id"), item.get("name"), item.get("arguments"), string_arguments=True))
        else:
            _error("Responses reasoning/server-tool/output kind is unsupported", unsupported=True)
    if status == "incomplete":
        finish = incomplete_finish
    else:
        finish = FinishReason.REFUSAL if refusal else FinishReason.TOOL_CALL if calls else FinishReason.COMPLETE
    if calls and (status != "completed" or refusal):
        _error("incomplete/refused Responses result cannot authorize client tools")
    return _response(document, profile, output, calls, finish)


def _decode_chat(document: Mapping[str, Any], profile: _Profile) -> ModelResponse:
    choices = _array(document.get("choices"))
    if len(choices) != 1:
        _error("Chat requires exactly one choice")
    choice = _object(choices[0])
    message = _object(choice.get("message"))
    if message.get("role") != "assistant":
        _error("Chat response role must be assistant")
    if message.get("reasoning_content") not in (None, "") or message.get("function_call") is not None:
        _error("Chat reasoning continuation/legacy function calling is unsupported", unsupported=True)
    output, calls = [], []
    content = message.get("content")
    if content is not None:
        if not isinstance(content, str):
            _error("Chat output content must be text or null")
        output.append(ContentBlock("text", text=content))
    refused = message.get("refusal")
    if refused is not None:
        if not isinstance(refused, str):
            _error("Chat refusal must be text")
        output.append(ContentBlock("refusal", text=refused))
    for raw in _array(message.get("tool_calls", [])):
        item = _object(raw)
        if item.get("type") != "function":
            _error("Chat server-tool kind is unsupported", unsupported=True)
        function = _object(item.get("function"))
        calls.append(_call(item.get("id"), function.get("name"), function.get("arguments"), string_arguments=True))
    finish = _terminal(choice.get("finish_reason"), {"stop": FinishReason.COMPLETE, "tool_calls": FinishReason.TOOL_CALL,
              "length": FinishReason.LENGTH, "content_filter": FinishReason.REFUSAL})
    if refused is not None:
        if calls:
            _error("refusal cannot authorize client tools")
        finish = FinishReason.REFUSAL
    return _response(document, profile, output, calls, finish)


def _decode_messages(document: Mapping[str, Any], profile: _Profile) -> ModelResponse:
    if document.get("type") != "message" or document.get("role") != "assistant":
        _error("Messages response type/role is invalid")
    output, calls = [], []
    for raw in _array(document.get("content")):
        block = _object(raw)
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            output.append(ContentBlock("text", text=block["text"]))
        elif block.get("type") == "tool_use":
            calls.append(_call(block.get("id"), block.get("name"), block.get("input")))
        else:
            _error("Messages thinking/signature/server-tool/content kind is unsupported", unsupported=True)
    finish = _terminal(document.get("stop_reason"), {"end_turn": FinishReason.COMPLETE, "stop_sequence": FinishReason.STOP,
              "max_tokens": FinishReason.LENGTH, "tool_use": FinishReason.TOOL_CALL,
              "pause_turn": FinishReason.PAUSED, "refusal": FinishReason.REFUSAL,
              "model_context_window_exceeded": FinishReason.CONTEXT_LIMIT})
    return _response(document, profile, output, calls, finish)


def _decode_gemini(document: Mapping[str, Any], profile: _Profile) -> ModelResponse:
    candidates = _array(document.get("candidates", []))
    if not candidates and _object(document.get("promptFeedback", {})).get("blockReason"):
        return _response(document, profile, [], [], FinishReason.REFUSAL, gemini=True)
    if len(candidates) != 1:
        _error("generateContent requires exactly one candidate")
    candidate = _object(candidates[0])
    if _object(candidate.get("content")).get("role") != "model":
        _error("generateContent output role must be model")
    output, calls, warnings = [], [], []
    for index, raw in enumerate(_array(_object(candidate.get("content")).get("parts"))):
        part = _object(raw)
        if "thoughtSignature" in part or part.get("thought"):
            _error("Gemini thought/signature continuation is unsupported", unsupported=True)
        if isinstance(part.get("text"), str) and set(part) <= {"text", "thought"}:
            output.append(ContentBlock("text", text=part["text"]))
        elif isinstance(part.get("functionCall"), Mapping) and set(part) == {"functionCall"}:
            function = _object(part["functionCall"])
            identifier = function.get("id")
            if identifier is None:
                identifier = f"local-gemini-{_string(document.get('responseId'))}-{index}"
                warnings.append("Gemini client call ID is local correlation, not a provider-reported ID")
            calls.append(_call(identifier, function.get("name"), function.get("args")))
        else:
            _error("Gemini content kind is outside the implemented subset", unsupported=True)
    reason = candidate.get("finishReason")
    finish = _terminal(reason, {"STOP": FinishReason.COMPLETE, "MAX_TOKENS": FinishReason.LENGTH,
              "MALFORMED_FUNCTION_CALL": FinishReason.ERROR, "UNEXPECTED_TOOL_CALL": FinishReason.ERROR,
              "SAFETY": FinishReason.REFUSAL, "RECITATION": FinishReason.REFUSAL,
              "BLOCKLIST": FinishReason.REFUSAL, "PROHIBITED_CONTENT": FinishReason.REFUSAL,
              "SPII": FinishReason.REFUSAL, "IMAGE_SAFETY": FinishReason.REFUSAL})
    if calls and finish == FinishReason.COMPLETE:
        finish = FinishReason.TOOL_CALL
    return _response(document, profile, output, calls, finish, gemini=True, warnings=tuple(warnings))
