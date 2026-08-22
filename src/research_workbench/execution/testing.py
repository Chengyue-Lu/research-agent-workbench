"""Offline scripted provider for tests and ``--scripted-session`` runs.

A scripted session file is JSON: ``{"responses": [...]}``; each entry carries
ModelResponse fields (output blocks, tool_calls, finish_reason, usage,
model). The provider declares text/tools/structured_output for any model, so
a compiled plan can bind it without a live adapter. The file is the evidence:
replaying the same script reproduces the same session.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

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
from research_workbench.contracts.common import ContractError, optional_string, require_string

SCRIPTED_PROVIDER_NAME = "scripted"
SCRIPTED_ADAPTER_VERSION = "0.1.0"


class ScriptedProvider:
    """Replay a fixed sequence of ModelResponse objects, in order."""

    def __init__(self, responses: Iterable[ModelResponse]) -> None:
        self._responses = list(responses)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=SCRIPTED_PROVIDER_NAME,
            adapter_version=SCRIPTED_ADAPTER_VERSION,
            supported=frozenset(
                {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
            ),
            models=(),  # any model name is accepted; the plan pins the identity
            deployment="local",
            known_gaps=("scripted replay never contacts a provider",),
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        if not self._responses:
            raise ProviderError(
                ProviderErrorCategory.UNKNOWN,
                "scripted session is exhausted",
            )
        return self._responses.pop(0)


def load_scripted_provider(path: str | Path) -> ScriptedProvider:
    """Load a scripted session JSON file into a ScriptedProvider."""

    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError("scripted_session", f"must be valid JSON: {exc.msg}") from exc
    if not isinstance(document, Mapping):
        raise ContractError("scripted_session", "must be an object")
    raw = document.get("responses")
    if not isinstance(raw, list) or any(not isinstance(item, Mapping) for item in raw):
        raise ContractError("responses", "must be an array of objects")
    return ScriptedProvider(
        [_response_from_mapping(item, index) for index, item in enumerate(raw)]
    )


def _response_from_mapping(data: Mapping[str, Any], index: int) -> ModelResponse:
    field = f"responses[{index}]"
    finish_raw = optional_string(data, "finish_reason") or FinishReason.COMPLETE.value
    try:
        finish_reason = FinishReason(finish_raw)
    except ValueError:
        raise ContractError(f"{field}.finish_reason", "has unsupported value") from None
    return ModelResponse(
        response_id=optional_string(data, "response_id") or f"scripted-{index}",
        provider=optional_string(data, "provider") or SCRIPTED_PROVIDER_NAME,
        model=optional_string(data, "model") or "scripted-model",
        output=tuple(
            _content_block(item, f"{field}.output[{item_index}]")
            for item_index, item in enumerate(_mapping_list(data, "output", f"{field}.output"))
        ),
        finish_reason=finish_reason,
        tool_calls=tuple(
            _tool_call(item, f"{field}.tool_calls[{item_index}]")
            for item_index, item in enumerate(
                _mapping_list(data, "tool_calls", f"{field}.tool_calls")
            )
        ),
        usage=_usage(data.get("usage"), f"{field}.usage"),
    )


def _mapping_list(data: Mapping[str, Any], key: str, field: str) -> tuple[Mapping[str, Any], ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise ContractError(field, "must be an array of objects")
    return tuple(value)


def _content_block(data: Mapping[str, Any], field: str) -> ContentBlock:
    text = data.get("text")
    if text is not None and not isinstance(text, str):
        raise ContractError(f"{field}.text", "must be a string")
    block_data = data.get("data")
    if block_data is not None and not isinstance(block_data, Mapping):
        raise ContractError(f"{field}.data", "must be an object")
    return ContentBlock(
        kind=require_string(data, "kind"),
        text=text,
        data=block_data,
        mime_type=optional_string(data, "mime_type"),
        reference=optional_string(data, "reference"),
    )


def _tool_call(data: Mapping[str, Any], field: str) -> ToolCall:
    arguments = data.get("arguments", {})
    if not isinstance(arguments, Mapping):
        raise ContractError(f"{field}.arguments", "must be an object")
    return ToolCall(
        call_id=require_string(data, "call_id"),
        name=require_string(data, "name"),
        arguments=dict(arguments),
    )


def _usage(raw: object, field: str) -> Usage:
    if raw is None:
        return Usage()
    if not isinstance(raw, Mapping):
        raise ContractError(field, "must be an object")

    def integer(key: str) -> int | None:
        value = raw.get(key)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise ContractError(f"{field}.{key}", "must be an integer")
        return value

    cost = raw.get("provider_reported_cost")
    if cost is not None and (isinstance(cost, bool) or not isinstance(cost, (int, float))):
        raise ContractError(f"{field}.provider_reported_cost", "must be a number")
    return Usage(
        input_tokens=integer("input_tokens"),
        output_tokens=integer("output_tokens"),
        cached_input_tokens=integer("cached_input_tokens"),
        reasoning_tokens=integer("reasoning_tokens"),
        provider_reported_cost=cost,
        currency=optional_string(raw, "currency"),
    )
