"""Explicit, versioned conformance-only ToolChoice transition policy.

This policy narrows one isolated session to two attempts and one declared
read-only client Tool. It neither grants Tool permission nor proves an
arbitrary Python handler is pure, and does not perform probe business scoring.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, Protocol

from research_workbench.adapters.models.port import (
    ContentBlock, ModelRequest, ModelResponse, ToolChoice,
)


class ConformanceSessionSummarySink(Protocol):
    """Explicit opt-in privacy summary sink, separate from generic Agent Trace.

    Implementations advertise ``conformance_summary_version = '1.0.0'`` and
    accept only the closed primitive summaries emitted by the policy runner.
    They receive no runtime request, response, Tool argument or result object,
    and no digest derived from those potentially credential-bearing values.
    Local-history assembly and submission attempts are distinct facts; this
    interface does not attest generic raw-content Trace or replay validity.
    """

    conformance_summary_version: str

    def record(self, kind: str, payload: Mapping[str, object]) -> None: ...


def validate_summary_event(kind: str, payload: Mapping[str, object]) -> None:
    """Closed local summary contract; does not reuse the Agent Trace schema."""
    common = {"summary_version", "policy_id", "policy_version", "policy_sha256"}
    fields = {
        "request-summary": {
            "phase", "provider", "requested_model", "tool_choice_kind", "tool_choice_name",
            "model_attempt", "history_message_count", "tool_result_in_local_history",
        },
        "response-summary": {
            "model_attempt", "tool_call_count", "output_kinds", "finish_reason",
            "input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens",
            "provider_reported_cost", "cost_currency",
        },
        "tool-attempt-summary": {"tool_ordinal", "tool_name", "handler_invoked"},
        "tool-result-summary": {
            "tool_ordinal", "tool_name", "status", "handler_invoked", "result_eligible_for_local_history",
        },
        "tool-context-summary": {
            "tool_ordinal", "tool_name", "local_history_assembled", "result_entered_context", "context_scope",
        },
        "capture-gap-summary": {"phase", "failure_code"},
        "session-summary": {
            "status", "stop_reason", "model_attempts", "successful_responses", "tool_invocations",
            "local_tool_history_assembled", "tool_context_submission_attempts",
        },
    }
    if kind not in fields or set(payload) != common | fields[kind]:
        raise ValueError("conformance summary event fields are closed")
    if payload["summary_version"] != "1.0.0" or payload["policy_version"] != "1.0.0":
        raise ValueError("unsupported conformance summary version")
    if not isinstance(payload["policy_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", payload["policy_sha256"]):
        raise ValueError("invalid conformance summary policy hash")

    def primitive(value: object) -> bool:
        if type(value) in {str, int, bool, type(None)}:
            return True
        if type(value) is float:
            return math.isfinite(value)
        if type(value) is list:
            return all(primitive(item) for item in value)
        return False

    if not all(primitive(value) for value in payload.values()):
        raise ValueError("conformance summary must contain detached finite primitives")


@dataclass(frozen=True, slots=True)
class ConformanceSessionPolicy:
    policy_id: str
    version: str
    initial_choice: ToolChoice
    after_successful_tool_result: ToolChoice
    expected_tool_name: str
    expected_tool_calls: int
    max_model_turns: int
    max_tool_calls: int

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9._-]{0,127}", self.policy_id
        ):
            raise ValueError("invalid conformance Session policy identity")
        if self.version != "1.0.0":
            raise ValueError("unsupported conformance Session policy version")
        if not isinstance(self.expected_tool_name, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_-]{0,127}", self.expected_tool_name
        ):
            raise ValueError("invalid conformance Session Tool name")
        if type(self.initial_choice) is not ToolChoice or self.initial_choice != ToolChoice(
            "specific", self.expected_tool_name
        ):
            raise ValueError("conformance Session initial choice must select its Tool")
        if type(self.after_successful_tool_result) is not ToolChoice or (
            self.after_successful_tool_result != ToolChoice("none")
        ):
            raise ValueError("conformance Session result choice must be none")
        for name, required in (
            ("expected_tool_calls", 1), ("max_model_turns", 2), ("max_tool_calls", 1)
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) != required:
                raise ValueError("conformance Session policy ceilings must be one Tool and two turns")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> ConformanceSessionPolicy:
        keys = {
            "policy_id", "version", "initial_choice", "after_successful_tool_result",
            "expected_tool_name", "expected_tool_calls", "max_model_turns", "max_tool_calls",
        }
        if not isinstance(value, Mapping) or set(value) != keys:
            raise ValueError("conformance Session policy fields are closed")

        def choice(name: str) -> ToolChoice:
            item = value[name]
            if not isinstance(item, Mapping) or set(item) != {"kind", "name"}:
                raise ValueError("conformance Session choice fields are closed")
            return ToolChoice(kind=item["kind"], name=item["name"])

        return cls(
            policy_id=value["policy_id"], version=value["version"],
            initial_choice=choice("initial_choice"),
            after_successful_tool_result=choice("after_successful_tool_result"),
            expected_tool_name=value["expected_tool_name"],
            expected_tool_calls=value["expected_tool_calls"],
            max_model_turns=value["max_model_turns"], max_tool_calls=value["max_tool_calls"],
        )

    def to_mapping(self) -> dict[str, object]:
        # Revalidation detects deliberate object.__setattr__ tampering too.
        self.__post_init__()
        return {
            "policy_id": self.policy_id, "version": self.version,
            "initial_choice": {"kind": self.initial_choice.kind, "name": self.initial_choice.name},
            "after_successful_tool_result": {
                "kind": self.after_successful_tool_result.kind,
                "name": self.after_successful_tool_result.name,
            },
            "expected_tool_name": self.expected_tool_name,
            "expected_tool_calls": self.expected_tool_calls,
            "max_model_turns": self.max_model_turns, "max_tool_calls": self.max_tool_calls,
        }

    @property
    def sha256(self) -> str:
        """Canonical policy-content digest; distinct from a serialized FileRef hash."""
        document = json.dumps(
            self.to_mapping(), sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(document).hexdigest()


def _immutable(*args: object, **kwargs: object) -> None:
    raise TypeError("conformance Session JSON values are immutable")


class _FrozenObject(dict):
    """JSON-compatible defensive snapshot, including jsonschema's object type."""

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _immutable


class _FrozenArray(list):
    """JSON-compatible defensive snapshot, including jsonschema's array type."""

    __setitem__ = __delitem__ = append = clear = extend = insert = pop = remove = _immutable
    reverse = sort = __iadd__ = __imul__ = _immutable


def freeze_json(value: object) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("conformance Session JSON object keys must be strings")
        return _FrozenObject({key: freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return _FrozenArray(freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError("conformance Session values must be finite JSON")


def freeze_request(request: ModelRequest) -> ModelRequest:
    def block(item: ContentBlock) -> ContentBlock:
        return replace(item, data=freeze_json(item.data) if item.data is not None else None)

    return replace(
        request,
        capability_requirements=frozenset(request.capability_requirements),
        data_policy=replace(request.data_policy, allowed_regions=tuple(request.data_policy.allowed_regions)),
        messages=tuple(replace(message, content=tuple(block(item) for item in message.content)) for message in request.messages),
        tools=tuple(replace(tool, input_schema=freeze_json(tool.input_schema)) for tool in request.tools),
        response_format=replace(
            request.response_format,
            schema=freeze_json(request.response_format.schema) if request.response_format.schema is not None else None,
        ),
        metadata=freeze_json(request.metadata), extensions=freeze_json(request.extensions),
    )


def freeze_response(response: ModelResponse) -> ModelResponse:
    return replace(
        response,
        usage=replace(response.usage),
        warnings=tuple(response.warnings),
        output=tuple(replace(block, data=freeze_json(block.data) if block.data is not None else None) for block in response.output),
        tool_calls=tuple(replace(call, arguments=freeze_json(call.arguments)) for call in response.tool_calls),
        provider_metadata=freeze_json(response.provider_metadata),
    )


def request_control_sha256(request: ModelRequest) -> str:
    """Recheck the frozen request controls; history and choice are separate."""
    value = {
        "model": request.model,
        "tools": [{
            "name": tool.name, "description": tool.description,
            "input_schema": tool.input_schema, "strict": tool.strict,
        } for tool in request.tools],
        "response_format": {
            "kind": request.response_format.kind, "name": request.response_format.name,
            "schema": request.response_format.schema,
        },
        "max_output_tokens": request.max_output_tokens, "temperature": request.temperature,
        "reasoning_effort": request.reasoning_effort,
        "capability_requirements": sorted(str(item) for item in request.capability_requirements),
        "data_policy": {
            "local_only": request.data_policy.local_only,
            "zero_data_retention_required": request.data_policy.zero_data_retention_required,
            "training_opt_out_required": request.data_policy.training_opt_out_required,
            "allowed_regions": list(request.data_policy.allowed_regions),
            "allow_provider_server_tools": request.data_policy.allow_provider_server_tools,
        },
        "metadata": request.metadata, "extensions": request.extensions,
    }
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def json_content_sha256(value: object) -> str:
    """Private runtime drift guard, never an archived credential-derived digest."""
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def request_content_sha256(request: ModelRequest) -> str:
    """Private full request pin, including each round's planned history/choice."""
    return json_content_sha256({
        "control": request_control_sha256(request),
        "tool_choice": {"kind": request.tool_choice.kind, "name": request.tool_choice.name},
        "messages": [{
            "role": message.role, "name": message.name,
            "content": [{
                "kind": block.kind, "text": block.text, "data": block.data,
                "mime_type": block.mime_type, "reference": block.reference,
            } for block in message.content],
        } for message in request.messages],
    })


def response_content_sha256(response: ModelResponse) -> str:
    """Private response and Tool parameter guard; never forwarded to a sink."""
    def usage_value(value: object) -> object:
        # Invalid reported usage still needs a drift pin before its safe pause.
        return "nonfinite-number" if isinstance(value, float) and not math.isfinite(value) else value

    return json_content_sha256({
        "response_id": response.response_id, "provider": response.provider, "model": response.model,
        "output": [{
            "kind": block.kind, "text": block.text, "data": block.data,
            "mime_type": block.mime_type, "reference": block.reference,
        } for block in response.output],
        "finish_reason": response.finish_reason,
        "tool_calls": [{
            "call_id": call.call_id, "name": call.name,
            "arguments": call.arguments, "executed_by": call.executed_by,
        } for call in response.tool_calls],
        "usage": {
            "input_tokens": usage_value(response.usage.input_tokens), "output_tokens": usage_value(response.usage.output_tokens),
            "cached_input_tokens": usage_value(response.usage.cached_input_tokens),
            "reasoning_tokens": usage_value(response.usage.reasoning_tokens),
            "provider_reported_cost": usage_value(response.usage.provider_reported_cost),
            "currency": response.usage.currency,
        },
        "warnings": list(response.warnings), "provider_metadata": response.provider_metadata,
    })
