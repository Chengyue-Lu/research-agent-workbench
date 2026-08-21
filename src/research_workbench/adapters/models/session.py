"""Bounded, provider-neutral isolated API sessions.

Each ``run`` call starts from only the supplied request. The runner retains no
conversation state between calls, does not use provider response IDs as state,
and never changes provider or model automatically.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Protocol

from research_workbench.adapters.models.base import validate_response_contract
from research_workbench.adapters.models.port import (
    ContentBlock,
    FinishReason,
    Message,
    ModelRequest,
    ModelResponse,
    ProviderError,
    ProviderErrorCategory,
    ProviderRegistry,
    ToolCall,
    ToolDefinition,
    Usage,
)


class ApiSessionStatus(StrEnum):
    COMPLETED = "completed"
    SAFE_PAUSED = "safe-paused"
    BLOCKED = "blocked"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ApiSessionLimits:
    max_model_turns: int
    max_tool_calls: int
    max_parallel_tool_calls: int
    max_tool_result_chars: int
    max_output_tokens_per_turn: int
    max_seconds: float
    max_total_tokens: int | None = None
    max_provider_reported_cost: float | None = None
    allowed_tool_side_effects: frozenset[str] = frozenset({"read-only"})

    def __post_init__(self) -> None:
        positive = {
            "max_model_turns": self.max_model_turns,
            "max_tool_result_chars": self.max_tool_result_chars,
            "max_output_tokens_per_turn": self.max_output_tokens_per_turn,
            "max_seconds": self.max_seconds,
        }
        for field, value in positive.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"{field} must be positive")
        for field, value in {
            "max_tool_calls": self.max_tool_calls,
            "max_parallel_tool_calls": self.max_parallel_tool_calls,
        }.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")
        if self.max_tool_calls and not self.max_parallel_tool_calls:
            raise ValueError("max_parallel_tool_calls must be positive when tools are allowed")
        if self.max_total_tokens is not None and self.max_total_tokens <= 0:
            raise ValueError("max_total_tokens must be positive when supplied")
        if self.max_provider_reported_cost is not None and self.max_provider_reported_cost < 0:
            raise ValueError("max_provider_reported_cost must be non-negative when supplied")
        supported_side_effects = {"read-only", "local-write", "external-write"}
        unknown_side_effects = sorted(set(self.allowed_tool_side_effects) - supported_side_effects)
        if unknown_side_effects:
            raise ValueError("unknown allowed tool side effects: " + ", ".join(unknown_side_effects))


@dataclass(frozen=True, slots=True)
class ClientTool:
    definition: ToolDefinition
    execute: Callable[[Mapping[str, Any]], object]
    side_effect: str = "read-only"


class SessionEventSink(Protocol):
    """One provider-neutral durability boundary for session events."""

    def record(self, kind: str, payload: Mapping[str, Any]) -> None: ...


@dataclass(frozen=True, slots=True)
class AggregateUsage:
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None
    reasoning_tokens: int | None
    provider_reported_cost: float | None
    currency: str | None

    @property
    def total_tokens(self) -> int | None:
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class ApiSessionResult:
    status: ApiSessionStatus
    stop_reason: str
    provider: str
    requested_model: str
    observed_models: tuple[str, ...]
    model_turns: int
    tool_calls: int
    usage: AggregateUsage
    final_response: ModelResponse | None
    warnings: tuple[str, ...]


class IsolatedApiSessionRunner:
    """Execute one fresh API child session under hard local limits."""

    def __init__(
        self,
        providers: ProviderRegistry,
        *,
        tools: tuple[ClientTool, ...] = (),
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._providers = providers
        self._tools = {tool.definition.name: tool for tool in tools}
        if len(self._tools) != len(tools):
            raise ValueError("client tool names must be unique")
        self._clock = clock

    def run(
        self,
        *,
        provider_name: str,
        request: ModelRequest,
        limits: ApiSessionLimits,
        cancel_requested: Callable[[], bool] | None = None,
        event_sink: SessionEventSink | None = None,
    ) -> ApiSessionResult:
        declared = {tool.name for tool in request.tools}
        missing_handlers = sorted(declared - set(self._tools))
        unused_handlers = sorted(set(self._tools) - declared)
        if missing_handlers:
            raise ValueError("missing client tool handlers: " + ", ".join(missing_handlers))
        if unused_handlers:
            raise ValueError("undeclared client tool handlers: " + ", ".join(unused_handlers))
        if request.tools and limits.max_tool_calls == 0:
            raise ValueError("request declares tools but max_tool_calls is zero")
        disallowed_side_effects = sorted(
            {
                tool.side_effect
                for tool in self._tools.values()
                if tool.side_effect not in limits.allowed_tool_side_effects
            }
        )
        if disallowed_side_effects:
            raise ValueError(
                "client tools exceed allowed side-effect classes: "
                + ", ".join(disallowed_side_effects)
            )

        bounded_request = replace(
            request,
            max_output_tokens=min(
                request.max_output_tokens or limits.max_output_tokens_per_turn,
                limits.max_output_tokens_per_turn,
            ),
        )
        provider = self._providers.require(provider_name, bounded_request)
        started = self._clock()
        messages = list(bounded_request.messages)
        responses: list[ModelResponse] = []
        tool_call_count = 0
        warnings: list[str] = []
        cancelled = cancel_requested or (lambda: False)

        while True:
            if cancelled():
                return self._finish(
                    ApiSessionStatus.SAFE_PAUSED,
                    "cancellation-requested",
                    provider_name,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    event_sink,
                )
            if len(responses) >= limits.max_model_turns:
                return self._finish(
                    ApiSessionStatus.SAFE_PAUSED,
                    "model-turn-budget",
                    provider_name,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    event_sink,
                )
            if self._clock() - started >= limits.max_seconds:
                return self._finish(
                    ApiSessionStatus.SAFE_PAUSED,
                    "wall-time-budget",
                    provider_name,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    event_sink,
                )

            current = replace(bounded_request, messages=tuple(messages))
            if event_sink is not None:
                # This durability call is intentionally outside the provider
                # exception boundary: failure must block before network use.
                event_sink.record("provider-request", {"request": current})
            try:
                response = validate_response_contract(current, provider.generate(current))
            except ProviderError as exc:
                # A provider that misbehaves mid-loop ends the session honestly
                # instead of crashing it; partial turn state is preserved.
                warnings.append(f"provider error category: {exc.category}")
                return self._finish(
                    (
                        ApiSessionStatus.SAFE_PAUSED
                        if exc.category == ProviderErrorCategory.CANCELLED
                        else ApiSessionStatus.FAILED
                    ),
                    (
                        "provider-cancelled"
                        if exc.category == ProviderErrorCategory.CANCELLED
                        else f"provider-error:{exc.category}"
                    ),
                    provider_name,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    event_sink,
                )
            except Exception as exc:
                warnings.append(f"provider exception type: {type(exc).__name__}")
                return self._finish(
                    ApiSessionStatus.FAILED,
                    f"provider-exception:{type(exc).__name__}",
                    provider_name,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    event_sink,
                )
            if event_sink is not None:
                try:
                    event_sink.record("provider-response", {"response": response})
                except Exception as exc:
                    event_sink.record(
                        "capture-gap",
                        {
                            "stream": "messages",
                            "reason": (
                                "post-provider response capture failed: "
                                f"{type(exc).__name__}"
                            ),
                        },
                    )
                    return self._finish(
                        ApiSessionStatus.SAFE_PAUSED,
                        "trace-capture-gap",
                        provider_name,
                        request.model,
                        responses,
                        tool_call_count,
                        warnings,
                        event_sink,
                    )
            responses.append(response)
            warnings.extend(response.warnings)

            if cancelled():
                return self._finish(
                    ApiSessionStatus.SAFE_PAUSED,
                    "cancellation-requested",
                    provider_name,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    event_sink,
                )

            budget_reason = _usage_budget_reason(responses, limits)
            if budget_reason is not None:
                return self._finish(
                    ApiSessionStatus.SAFE_PAUSED,
                    budget_reason,
                    provider_name,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    event_sink,
                )
            if self._clock() - started >= limits.max_seconds:
                return self._finish(
                    ApiSessionStatus.SAFE_PAUSED,
                    "wall-time-budget",
                    provider_name,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    event_sink,
                )

            if response.tool_calls:
                if len(response.tool_calls) > limits.max_parallel_tool_calls:
                    return self._finish(
                        ApiSessionStatus.SAFE_PAUSED,
                        "parallel-tool-budget",
                        provider_name,
                        request.model,
                        responses,
                        tool_call_count,
                        warnings,
                        event_sink,
                    )
                if tool_call_count + len(response.tool_calls) > limits.max_tool_calls:
                    return self._finish(
                        ApiSessionStatus.SAFE_PAUSED,
                        "tool-call-budget",
                        provider_name,
                        request.model,
                        responses,
                        tool_call_count,
                        warnings,
                        event_sink,
                    )
                assistant_blocks = [
                    *response.output,
                    *(_tool_call_block(call) for call in response.tool_calls),
                ]
                tool_blocks: list[ContentBlock] = []
                for call in response.tool_calls:
                    if cancelled():
                        return self._finish(
                            ApiSessionStatus.SAFE_PAUSED,
                            "cancellation-requested",
                            provider_name,
                            request.model,
                            responses,
                            tool_call_count,
                            warnings,
                            event_sink,
                        )
                    binding = self._tools[call.name]
                    # Invocation is the accounting boundary: failures and
                    # oversized results still consumed a call and may have
                    # produced an observable side effect.
                    tool_call_count += 1
                    if event_sink is not None:
                        event_sink.record(
                            "tool-attempted",
                            {"call_id": call.call_id, "name": call.name, "arguments": dict(call.arguments)},
                        )
                    try:
                        output = binding.execute(call.arguments)
                        is_error = False
                    except Exception as exc:  # Tool failures return only their exception type.
                        output = {"error": type(exc).__name__}
                        is_error = True
                    rendered = _render_tool_output(output)
                    if event_sink is not None:
                        try:
                            event_sink.record(
                                "tool-result",
                                {
                                    "call_id": call.call_id,
                                    "name": call.name,
                                    "arguments": dict(call.arguments),
                                    "status": "failed" if is_error else "succeeded",
                                    "result": output,
                                    "result_entered_context": (
                                        len(rendered) <= limits.max_tool_result_chars
                                    ),
                                },
                            )
                        except Exception as exc:
                            event_sink.record(
                                "capture-gap",
                                {"stream": "tool-results", "reason": f"post-tool result capture failed: {type(exc).__name__}"},
                            )
                            return self._finish(
                                ApiSessionStatus.SAFE_PAUSED,
                                "trace-capture-gap",
                                provider_name,
                                request.model,
                                responses,
                                tool_call_count,
                                warnings,
                                event_sink,
                            )
                    if len(rendered) > limits.max_tool_result_chars:
                        return self._finish(
                            ApiSessionStatus.SAFE_PAUSED,
                            "tool-result-size-budget",
                            provider_name,
                            request.model,
                            responses,
                            tool_call_count,
                            warnings,
                            event_sink,
                        )
                    tool_blocks.append(
                        ContentBlock(
                            kind="tool_result",
                            data={
                                "call_id": call.call_id,
                                "name": call.name,
                                "output": output,
                                "is_error": is_error,
                            },
                        )
                    )
                messages.append(Message("assistant", tuple(assistant_blocks)))
                messages.append(Message("tool", tuple(tool_blocks)))
                continue

            status, reason = _terminal_status(response.finish_reason)
            return self._finish(
                status,
                reason,
                provider_name,
                request.model,
                responses,
                tool_call_count,
                warnings,
                event_sink,
            )

    @classmethod
    def _finish(
        cls,
        status: ApiSessionStatus,
        stop_reason: str,
        provider: str,
        requested_model: str,
        responses: list[ModelResponse],
        tool_calls: int,
        warnings: list[str],
        event_sink: SessionEventSink | None,
    ) -> ApiSessionResult:
        if event_sink is not None:
            event_sink.record(
                "session-status",
                {"status": status.value, "reason": stop_reason},
            )
        return cls._result(status, stop_reason, provider, requested_model, responses, tool_calls, warnings)

    @staticmethod
    def _result(
        status: ApiSessionStatus,
        stop_reason: str,
        provider: str,
        requested_model: str,
        responses: list[ModelResponse],
        tool_calls: int,
        warnings: list[str],
    ) -> ApiSessionResult:
        observed = tuple(dict.fromkeys(response.model for response in responses))
        if observed and any(model != requested_model for model in observed):
            warnings.append("provider-reported-model-differs-from-request")
        return ApiSessionResult(
            status=status,
            stop_reason=stop_reason,
            provider=provider,
            requested_model=requested_model,
            observed_models=observed,
            model_turns=len(responses),
            tool_calls=tool_calls,
            usage=_aggregate_usage(response.usage for response in responses),
            final_response=responses[-1] if responses else None,
            warnings=tuple(dict.fromkeys(warnings)),
        )


def _tool_call_block(call: ToolCall) -> ContentBlock:
    return ContentBlock(
        kind="tool_call",
        data={"call_id": call.call_id, "name": call.name, "arguments": dict(call.arguments)},
    )


def _render_tool_output(output: object) -> str:
    if isinstance(output, str):
        return output
    return json.dumps(output, ensure_ascii=False, separators=(",", ":"), default=str)


def _terminal_status(reason: FinishReason) -> tuple[ApiSessionStatus, str]:
    if reason in {FinishReason.COMPLETE, FinishReason.STOP}:
        return ApiSessionStatus.COMPLETED, str(reason)
    if reason == FinishReason.REFUSAL:
        return ApiSessionStatus.BLOCKED, str(reason)
    if reason in {FinishReason.LENGTH, FinishReason.PAUSED, FinishReason.CONTEXT_LIMIT}:
        return ApiSessionStatus.INCOMPLETE, str(reason)
    return ApiSessionStatus.FAILED, str(reason)


def _aggregate_usage(records: Iterable[Usage]) -> AggregateUsage:
    values = tuple(records)

    def total(field: str) -> int | None:
        items = [getattr(item, field) for item in values]
        return sum(items) if items and all(item is not None for item in items) else None

    costs = [item.provider_reported_cost for item in values]
    currencies = {item.currency for item in values if item.currency is not None}
    cost = sum(costs) if costs and all(item is not None for item in costs) and len(currencies) <= 1 else None
    currency = next(iter(currencies)) if cost is not None and currencies else None
    return AggregateUsage(
        input_tokens=total("input_tokens"),
        output_tokens=total("output_tokens"),
        cached_input_tokens=total("cached_input_tokens"),
        reasoning_tokens=total("reasoning_tokens"),
        provider_reported_cost=cost,
        currency=currency,
    )


def _usage_budget_reason(
    responses: list[ModelResponse], limits: ApiSessionLimits
) -> str | None:
    usage = _aggregate_usage(response.usage for response in responses)
    if limits.max_total_tokens is not None:
        if usage.total_tokens is None:
            return "token-usage-unavailable"
        if usage.total_tokens > limits.max_total_tokens:
            return "total-token-budget"
    if limits.max_provider_reported_cost is not None:
        if usage.provider_reported_cost is None:
            return "cost-usage-unavailable"
        if usage.provider_reported_cost > limits.max_provider_reported_cost:
            return "provider-cost-budget"
    return None
