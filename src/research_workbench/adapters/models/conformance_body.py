"""Opt-in pure admission for three fixed, synthetic DeepSeek Flash Responses bodies.

Only nonsecret ModelRequest fields and encoded body bytes are inspected. Headers,
credentials and remote billing are outside this helper. The byte limit constrains
local request size; it is not a tokenizer or billable-input proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from types import MappingProxyType

from research_workbench.adapters.models.port import (
    ContentBlock, DataPolicy, FinishReason, Message, ModelRequest, ModelResponse, ResponseFormat, ToolCall, ToolChoice, ToolDefinition,
)
from research_workbench.adapters.models.session_policy import _FrozenArray, _FrozenObject

PHASES = ("specific-tool", "result-text", "structured")
TOOL_PROMPT = "Call add_ints once with a=3 and b=4. After its result, return only 7."
SCHEMA_PROMPT = "Return an object with sum equal to 7."


class ConformanceBodyError(ValueError):
    """One fixed redacted error; never caller content or exception chains."""

    def __init__(self):
        super().__init__("conformance body admission failed")


def _fail():
    error = ConformanceBodyError()
    try:
        raise error from None
    finally:
        error.__cause__ = None
        error.__context__ = None
        error.__suppress_context__ = True


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _plain(value, depth=0):
    # Closed finite containers avoid walking arbitrary user objects or an
    # unbounded nested schema before admission. MappingProxyType is used by
    # the existing Session's immutable prepared history.
    if depth > 8:
        _fail()
    if value is None or type(value) in {bool, int}:
        if type(value) is int and not -(2**63) <= value <= 2**63 - 1:
            _fail()
        return value
    if type(value) is str:
        if len(value) > 256:
            _fail()
        return value
    if type(value) in {dict, MappingProxyType, _FrozenObject}:
        if len(value) > 16 or any(type(key) is not str or len(key) > 64 for key in value):
            _fail()
        return {key: _plain(item, depth + 1) for key, item in value.items()}
    if type(value) in {tuple, list, _FrozenArray}:
        if len(value) > 8:
            _fail()
        return [_plain(item, depth + 1) for item in value]
    _fail()


def tool_schema():
    return {"type": "object", "properties": {"a": {"type": "integer", "enum": [3]},
        "b": {"type": "integer", "enum": [4]}}, "required": ["a", "b"], "additionalProperties": False}


def result_schema():
    return {"type": "object", "properties": {"sum": {"type": "integer", "enum": [7]}},
        "required": ["sum"], "additionalProperties": False}


@dataclass(frozen=True, slots=True)
class ConformanceBodyPolicy:
    """Explicit immutable selection; no automatic profile or live authority."""

    max_output_tokens: int = 256
    max_body_bytes: int = 4096
    provider: str = "deepseek"
    protocol_family: str = "responses"
    model: str = "deepseek-flash"
    mode: str = "nonthinking"
    policy_version: str = "1.0.0"

    def __post_init__(self):
        policy_pin(self)


def policy_pin(policy):
    if (type(policy) is not ConformanceBodyPolicy or type(policy.max_output_tokens) is not int
            or not 16 <= policy.max_output_tokens <= 256 or type(policy.max_body_bytes) is not int
            or not 1024 <= policy.max_body_bytes <= 4096
            or any(type(value) is not str for value in (policy.provider, policy.protocol_family, policy.model,
                                                       policy.mode, policy.policy_version))
            or policy.provider != "deepseek" or policy.protocol_family != "responses"
            or policy.model != "deepseek-flash" or policy.mode != "nonthinking" or policy.policy_version != "1.0.0"):
        _fail()
    return (policy.max_output_tokens, policy.max_body_bytes, policy.provider,
            policy.protocol_family, policy.model, policy.mode, policy.policy_version)


@dataclass(frozen=True, slots=True, repr=False)
class PreparedBodyAdmission:
    """Private bounded memory-only expectation; never emitted into a report."""

    phase: str
    policy_state: tuple
    model_request: ModelRequest = field(repr=False)
    request_state: bytes = field(repr=False)
    expected_body: bytes = field(repr=False)
    expected_call_id: str | None = field(repr=False)
    expected_assistant_text: tuple[str, ...] = field(repr=False)

    def __repr__(self):
        return "<prepared synthetic body admission>"


def _text(message, prompt):
    return (type(message) is Message and type(message.role) is str and message.role == "user" and message.name is None
        and type(message.content) is tuple and len(message.content) == 1
        and type(message.content[0]) is ContentBlock and type(message.content[0].kind) is str
        and message.content[0].kind == "text" and type(message.content[0].text) is str
        and message.content[0].text == prompt and message.content[0].data is None
        and message.content[0].mime_type is None and message.content[0].reference is None)


def _history_block(message, role, kind):
    if (type(message) is not Message or type(message.role) is not str or message.role != role or message.name is not None
            or type(message.content) is not tuple or len(message.content) != 1
            or type(message.content[0]) is not ContentBlock):
        _fail()
    block = message.content[0]
    if type(block.kind) is not str or block.kind != kind or block.text is not None or block.mime_type is not None or block.reference is not None:
        _fail()
    return _plain(block.data)


def validated_response_context(response):
    """Private context from the same validated successful first Tool response."""
    if (type(response) is not ModelResponse or type(response.provider) is not str or response.provider != "deepseek"
            or type(response.model) is not str or response.model != "deepseek-flash" or response.finish_reason != FinishReason.TOOL_CALL
            or type(response.tool_calls) is not tuple or len(response.tool_calls) != 1
            or type(response.tool_calls[0]) is not ToolCall or type(response.tool_calls[0].name) is not str
            or response.tool_calls[0].name != "add_ints" or type(response.tool_calls[0].executed_by) is not str
            or response.tool_calls[0].executed_by != "client"
            or _json(_plain(response.tool_calls[0].arguments)) != _json({"a": 3, "b": 4})
            or type(response.output) is not tuple or len(response.output) > 4):
        _fail()
    call_id = response.tool_calls[0].call_id
    if type(call_id) is not str or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", call_id) is None:
        _fail()
    texts = []
    for block in response.output:
        if (type(block) is not ContentBlock or type(block.kind) is not str or block.kind != "text" or type(block.text) is not str
                or len(block.text) > 128 or block.data is not None or block.mime_type is not None or block.reference is not None):
            _fail()
        texts.append(block.text)
    if sum(map(len, texts)) > 256:
        _fail()
    return call_id, tuple(texts)


def prepare_body_admission(policy, phase, request, *, expected_call_id=None, expected_assistant_text=()):
    """Pure ModelRequest check, required before the credential boundary."""
    pin = policy_pin(policy)
    if type(phase) is not str or phase not in PHASES or type(request) is not ModelRequest:
        _fail()
    if (type(request.model) is not str or request.model != policy.model or type(request.max_output_tokens) is not int
            or request.max_output_tokens != policy.max_output_tokens or request.temperature is not None
            or request.reasoning_effort is not None or request.capability_requirements != frozenset()
            or type(request.capability_requirements) is not frozenset
            or type(request.data_policy) is not DataPolicy or request.data_policy != DataPolicy()
            or any(value is not False for value in (request.data_policy.local_only, request.data_policy.zero_data_retention_required,
                request.data_policy.training_opt_out_required, request.data_policy.allow_provider_server_tools))
            or type(request.data_policy.allowed_regions) is not tuple
            or _plain(request.metadata) != {} or _plain(request.extensions) != {}
            or type(request.messages) is not tuple or type(request.tools) is not tuple
            or type(request.tool_choice) is not ToolChoice or type(request.tool_choice.kind) is not str
            or request.tool_choice.name is not None and type(request.tool_choice.name) is not str
            or type(request.response_format) is not ResponseFormat or type(request.response_format.kind) is not str
            or request.response_format.name is not None and type(request.response_format.name) is not str):
        _fail()
    if (type(expected_assistant_text) is not tuple or len(expected_assistant_text) > 4
            or any(type(item) is not str or len(item) > 128 for item in expected_assistant_text)
            or sum(map(len, expected_assistant_text)) > 256):
        _fail()
    if phase != "result-text" and (expected_call_id is not None or expected_assistant_text):
        _fail()
    body = {"model": policy.model, "max_output_tokens": policy.max_output_tokens, "reasoning": {"effort": "none"}}
    if phase in {"specific-tool", "result-text"}:
        if (len(request.tools) != 1 or type(request.tools[0]) is not ToolDefinition
                or type(request.tools[0].name) is not str or type(request.tools[0].description) is not str
                or request.tools[0].name != "add_ints" or request.tools[0].description != "Add two synthetic integers."
                or request.tools[0].strict is not False or _json(_plain(request.tools[0].input_schema)) != _json(tool_schema())
                or request.response_format != ResponseFormat()):
            _fail()
        if not request.messages or not _text(request.messages[0], TOOL_PROMPT):
            _fail()
        body["tools"] = [{"type": "function", "name": "add_ints", "description": "Add two synthetic integers.", "parameters": tool_schema()}]
        body["input"] = [{"role": "user", "content": TOOL_PROMPT}]
        if phase == "specific-tool":
            if len(request.messages) != 1 or request.tool_choice != ToolChoice("specific", "add_ints"):
                _fail()
            body["tool_choice"] = {"type": "function", "name": "add_ints"}
        else:
            if (type(expected_call_id) is not str or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", expected_call_id) is None
                    or len(request.messages) != 3 or request.tool_choice != ToolChoice("none")):
                _fail()
            assistant = request.messages[1]
            if (type(assistant) is not Message or type(assistant.role) is not str or assistant.role != "assistant" or assistant.name is not None
                    or type(assistant.content) is not tuple or len(assistant.content) != len(expected_assistant_text) + 1):
                _fail()
            for block, text in zip(assistant.content[:-1], expected_assistant_text):
                if (type(block) is not ContentBlock or type(block.kind) is not str or block.kind != "text"
                        or type(block.text) is not str or block.text != text
                        or block.data is not None or block.mime_type is not None or block.reference is not None):
                    _fail()
            call = _history_block(Message("assistant", (assistant.content[-1],)), "assistant", "tool_call")
            result = _history_block(request.messages[2], "tool", "tool_result")
            if (_json(call) != _json({"call_id": expected_call_id, "name": "add_ints", "arguments": {"a": 3, "b": 4}})
                    or _json(result) != _json({"call_id": expected_call_id, "name": "add_ints", "output": 7, "is_error": False})):
                _fail()
            if expected_assistant_text:
                body["input"].append({"role": "assistant", "content": "\n".join(expected_assistant_text)})
            body["input"].extend([
                {"type": "function_call", "call_id": expected_call_id, "name": "add_ints",
                 "arguments": json.dumps(call["arguments"], ensure_ascii=False, separators=(",", ":"), allow_nan=False)},
                {"type": "function_call_output", "call_id": expected_call_id, "output": "7"}])
            body["tool_choice"] = "none"
    else:
        if (len(request.messages) != 1 or not _text(request.messages[0], SCHEMA_PROMPT) or request.tools
                or request.tool_choice != ToolChoice() or request.response_format.kind != "json_schema"
                or request.response_format.name != "sum" or _json(_plain(request.response_format.schema)) != _json(result_schema())):
            _fail()
        body["input"] = [{"role": "user", "content": SCHEMA_PROMPT}]
        body["text"] = {"format": {"type": "json_schema", "name": "sum", "schema": result_schema()}}
    expected = _json(body)
    if len(expected) > policy.max_body_bytes:
        _fail()
    # The accepted fields have one exact semantic representation. Store its
    # private canonical expectation rather than any header/auth material.
    return PreparedBodyAdmission(phase, pin, request, expected, expected, expected_call_id, expected_assistant_text)


def revalidate_body_admission(policy, admission, frozen_state):
    if type(admission) is not PreparedBodyAdmission:
        _fail()
    current = prepare_body_admission(policy, admission.phase, admission.model_request,
                                    expected_call_id=admission.expected_call_id,
                                    expected_assistant_text=admission.expected_assistant_text)
    state = (admission.phase, admission.policy_state, admission.model_request,
             admission.request_state, admission.expected_body, admission.expected_call_id, admission.expected_assistant_text)
    if (len(frozen_state) != 7 or state[2] is not frozen_state[2]
            or state[:2] != frozen_state[:2] or state[3:] != frozen_state[3:]
            or current.policy_state != admission.policy_state or current.request_state != admission.request_state
            or current.expected_body != admission.expected_body):
        _fail()


def validate_encoded_body(policy, admission, frozen_state, body):
    """Read only body bytes, after callbacks and before durable send intent."""
    revalidate_body_admission(policy, admission, frozen_state)
    if type(body) is not bytes or len(body) > policy.max_body_bytes:
        _fail()
    document = None
    try:
        def unique(pairs):
            result = {}
            for key, item in pairs:
                if key in result:
                    raise ValueError("duplicate")
                result[key] = item
            return result
        def constant(_):
            raise ValueError("nonfinite")
        document = json.loads(body, object_pairs_hook=unique, parse_constant=constant)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        pass
    if type(document) is not dict:
        _fail()
    try:
        actual = _json(_plain(document))
    except (ValueError, TypeError, UnicodeError):
        actual = None
    if actual != admission.expected_body:
        _fail()
