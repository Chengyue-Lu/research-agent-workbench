"""Bounded, provider-neutral isolated API sessions.

Each ``run`` call starts from only the supplied request. The runner retains no
conversation state between calls, does not use provider response IDs as state,
and never changes provider or model automatically.
"""

from __future__ import annotations

import json
import math
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
    ProviderCapabilities,
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
    max_compute_values_per_call: int = 256

    def __post_init__(self) -> None:
        positive_integers = {
            "max_model_turns": self.max_model_turns,
            "max_tool_result_chars": self.max_tool_result_chars,
            "max_output_tokens_per_turn": self.max_output_tokens_per_turn,
        }
        for field, value in positive_integers.items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field} must be a positive integer")
        if (
            isinstance(self.max_compute_values_per_call, bool)
            or not isinstance(self.max_compute_values_per_call, int)
            or self.max_compute_values_per_call <= 0
        ):
            raise ValueError("max_compute_values_per_call must be a positive integer")
        for field, value in {
            "max_tool_calls": self.max_tool_calls,
            "max_parallel_tool_calls": self.max_parallel_tool_calls,
        }.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")
        if (
            isinstance(self.max_seconds, bool)
            or not isinstance(self.max_seconds, (int, float))
            or not math.isfinite(self.max_seconds)
            or self.max_seconds <= 0
        ):
            raise ValueError("max_seconds must be a positive finite number")
        if self.max_tool_calls and not self.max_parallel_tool_calls:
            raise ValueError("max_parallel_tool_calls must be positive when tools are allowed")
        if self.max_total_tokens is not None and (
            isinstance(self.max_total_tokens, bool)
            or not isinstance(self.max_total_tokens, int)
            or self.max_total_tokens <= 0
        ):
            raise ValueError("max_total_tokens must be a positive integer when supplied")
        if self.max_provider_reported_cost is not None and (
            isinstance(self.max_provider_reported_cost, bool)
            or not isinstance(self.max_provider_reported_cost, (int, float))
            or not math.isfinite(self.max_provider_reported_cost)
            or self.max_provider_reported_cost < 0
        ):
            raise ValueError(
                "max_provider_reported_cost must be a non-negative finite number when supplied"
            )
        supported_side_effects = {"none", "read-only", "local-write", "external-write"}
        unknown_side_effects = sorted(set(self.allowed_tool_side_effects) - supported_side_effects)
        if unknown_side_effects:
            raise ValueError("unknown allowed tool side effects: " + ", ".join(unknown_side_effects))


@dataclass(frozen=True, slots=True)
class ClientTool:
    definition: ToolDefinition
    execute: Callable[[Mapping[str, Any]], object]
    side_effect: str = "read-only"
    trace_result: bool = False


class ApiSessionObserver(Protocol):
    """Sanitized lifecycle observer for one isolated session.

    The runner exposes only boundary identities and counts.  It never passes
    prompts, response bodies, tool arguments/results, native call IDs,
    credentials, exception messages, or model reasoning to the observer.
    Observer failures propagate so execution fails closed.
    """

    def provider_call_started(
        self,
        *,
        call_number: int,
        provider_identity: str,
        model: str,
    ) -> None: ...

    def provider_call_finished(
        self,
        *,
        call_number: int,
        status: str,
    ) -> None: ...

    def tool_call_started(
        self,
        *,
        call_number: int,
        tool_name: str,
    ) -> None: ...

    def tool_call_finished(
        self,
        *,
        call_number: int,
        tool_name: str,
        status: str,
        result_char_count: int,
        result_entered_context: bool,
        frozen_read_path: str | None,
        frozen_read_sha256: str | None,
        captured_result: object | None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ToolFailureSummary:
    """Minimal failure metadata retained after the transient transcript is gone."""

    tool_name: str
    call_number: int
    error_type: str


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
    """Session result whose ``provider`` is the canonical provider identity."""

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
    model_request_counts: tuple[tuple[str, int], ...] = ()
    tool_failures: tuple[ToolFailureSummary, ...] = ()

    @property
    def tool_failure_count(self) -> int:
        return len(self.tool_failures)


class IsolatedApiSessionRunner:
    """Execute one fresh API child session with bounded call/response guards.

    The runner cannot cancel an in-flight Provider or tool call. Tool-call
    fan-out is capped per turn, while client handlers currently run serially.
    """

    def __init__(
        self,
        providers: ProviderRegistry,
        *,
        tools: tuple[ClientTool, ...] = (),
        clock: Callable[[], float] = time.monotonic,
        observer: ApiSessionObserver | None = None,
    ) -> None:
        self._providers = providers
        self._tools = {tool.definition.name: tool for tool in tools}
        if len(self._tools) != len(tools):
            raise ValueError("client tool names must be unique")
        self._clock = clock
        self._observer = observer

    def run(
        self,
        *,
        provider_name: str | None = None,
        request: ModelRequest,
        limits: ApiSessionLimits,
        expected_capabilities: ProviderCapabilities | None = None,
        adapter_id: str | None = None,
    ) -> ApiSessionResult:
        """Run one request through an explicit adapter registry key.

        ``adapter_id`` is the preferred lookup argument. ``provider_name`` is
        retained as a compatibility alias and must not be confused with the
        canonical provider identity in the capability snapshot and response.
        """

        selected_adapter_id = _resolve_adapter_id(adapter_id, provider_name)
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
        provider, active_capabilities = self._providers.require_with_capabilities(
            selected_adapter_id,
            bounded_request,
            expected_capabilities=expected_capabilities,
        )
        canonical_provider = active_capabilities.provider
        started = self._clock()
        messages = list(bounded_request.messages)
        responses: list[ModelResponse] = []
        tool_call_count = 0
        warnings: list[str] = []
        tool_failures: list[ToolFailureSummary] = []

        while True:
            if len(responses) >= limits.max_model_turns:
                return self._result(
                    ApiSessionStatus.SAFE_PAUSED,
                    "model-turn-budget",
                    canonical_provider,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    tool_failures,
                )
            if self._clock() - started >= limits.max_seconds:
                return self._result(
                    ApiSessionStatus.SAFE_PAUSED,
                    "wall-time-budget",
                    canonical_provider,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    tool_failures,
                )

            current = replace(bounded_request, messages=tuple(messages))
            provider_call_number = len(responses) + 1
            if self._observer is not None:
                self._observer.provider_call_started(
                    call_number=provider_call_number,
                    provider_identity=canonical_provider,
                    model=request.model,
                )
            try:
                response = validate_response_contract(current, provider.generate(current))
            except Exception:
                if self._observer is not None:
                    self._observer.provider_call_finished(
                        call_number=provider_call_number,
                        status="failed",
                    )
                raise
            if self._observer is not None:
                self._observer.provider_call_finished(
                    call_number=provider_call_number,
                    status="succeeded",
                )
            if response.provider != canonical_provider:
                raise ProviderError(
                    ProviderErrorCategory.CONTRACT_VIOLATION,
                    "Provider response identity differs from the approved capability snapshot",
                )
            if response.model != request.model:
                responses.append(response)
                warnings.extend(response.warnings)
                return self._result(
                    ApiSessionStatus.FAILED,
                    "model-identity-mismatch",
                    canonical_provider,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    tool_failures,
                )
            responses.append(response)
            warnings.extend(response.warnings)

            budget_reason = _usage_budget_reason(responses, limits)
            if budget_reason is not None:
                return self._result(
                    ApiSessionStatus.SAFE_PAUSED,
                    budget_reason,
                    canonical_provider,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    tool_failures,
                )
            if self._clock() - started >= limits.max_seconds:
                return self._result(
                    ApiSessionStatus.SAFE_PAUSED,
                    "wall-time-budget",
                    canonical_provider,
                    request.model,
                    responses,
                    tool_call_count,
                    warnings,
                    tool_failures,
                )

            if response.tool_calls:
                if len(response.tool_calls) > limits.max_parallel_tool_calls:
                    return self._result(
                        ApiSessionStatus.SAFE_PAUSED,
                        "parallel-tool-budget",
                        canonical_provider,
                        request.model,
                        responses,
                        tool_call_count,
                        warnings,
                        tool_failures,
                    )
                if tool_call_count + len(response.tool_calls) > limits.max_tool_calls:
                    return self._result(
                        ApiSessionStatus.SAFE_PAUSED,
                        "tool-call-budget",
                        canonical_provider,
                        request.model,
                        responses,
                        tool_call_count,
                        warnings,
                        tool_failures,
                    )
                assistant_blocks = [
                    *response.output,
                    *(_tool_call_block(call) for call in response.tool_calls),
                ]
                tool_blocks: list[ContentBlock] = []
                for call in response.tool_calls:
                    if self._clock() - started >= limits.max_seconds:
                        return self._result(
                            ApiSessionStatus.SAFE_PAUSED,
                            "wall-time-budget",
                            canonical_provider,
                            request.model,
                            responses,
                            tool_call_count,
                            warnings,
                            tool_failures,
                        )
                    binding = self._tools[call.name]
                    tool_call_count += 1
                    if self._observer is not None:
                        self._observer.tool_call_started(
                            call_number=tool_call_count,
                            tool_name=call.name,
                        )
                    try:
                        output = binding.execute(call.arguments)
                        is_error = False
                    except Exception as exc:  # Tool failures return only their exception type.
                        error_type = type(exc).__name__
                        output = {"error": error_type}
                        is_error = True
                        tool_failures.append(
                            ToolFailureSummary(
                                tool_name=call.name,
                                call_number=tool_call_count,
                                error_type=error_type,
                            )
                        )
                    rendered = _render_tool_output(output)
                    frozen_read_path: str | None = None
                    frozen_read_sha256: str | None = None
                    if (
                        binding.side_effect == "read-only"
                        and isinstance(output, Mapping)
                        and isinstance(output.get("path"), str)
                        and isinstance(output.get("sha256"), str)
                    ):
                        frozen_read_path = str(output["path"])
                        frozen_read_sha256 = str(output["sha256"])
                    if self._clock() - started >= limits.max_seconds:
                        if self._observer is not None:
                            self._observer.tool_call_finished(
                                call_number=tool_call_count,
                                tool_name=call.name,
                                status="failed" if is_error else "succeeded",
                                result_char_count=len(rendered),
                                result_entered_context=False,
                                frozen_read_path=frozen_read_path,
                                frozen_read_sha256=frozen_read_sha256,
                                captured_result=(output if is_error or binding.trace_result else None),
                            )
                        return self._result(
                            ApiSessionStatus.SAFE_PAUSED,
                            "wall-time-budget",
                            canonical_provider,
                            request.model,
                            responses,
                            tool_call_count,
                            warnings,
                            tool_failures,
                        )
                    if len(rendered) > limits.max_tool_result_chars:
                        if self._observer is not None:
                            self._observer.tool_call_finished(
                                call_number=tool_call_count,
                                tool_name=call.name,
                                status="failed" if is_error else "succeeded",
                                result_char_count=len(rendered),
                                result_entered_context=False,
                                frozen_read_path=frozen_read_path,
                                frozen_read_sha256=frozen_read_sha256,
                                captured_result=(output if is_error or binding.trace_result else None),
                            )
                        return self._result(
                            ApiSessionStatus.SAFE_PAUSED,
                            "tool-result-size-budget",
                            canonical_provider,
                            request.model,
                            responses,
                            tool_call_count,
                            warnings,
                            tool_failures,
                        )
                    if self._observer is not None:
                        self._observer.tool_call_finished(
                            call_number=tool_call_count,
                            tool_name=call.name,
                            status="failed" if is_error else "succeeded",
                            result_char_count=len(rendered),
                            result_entered_context=True,
                            frozen_read_path=frozen_read_path,
                            frozen_read_sha256=frozen_read_sha256,
                            captured_result=(output if is_error or binding.trace_result else None),
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
            return self._result(
                status,
                reason,
                canonical_provider,
                request.model,
                responses,
                tool_call_count,
                warnings,
                tool_failures,
            )

    @staticmethod
    def _result(
        status: ApiSessionStatus,
        stop_reason: str,
        provider: str,
        requested_model: str,
        responses: list[ModelResponse],
        tool_calls: int,
        warnings: list[str],
        tool_failures: list[ToolFailureSummary],
    ) -> ApiSessionResult:
        observed = tuple(dict.fromkeys(response.model for response in responses))
        request_counts: dict[str, int] = {}
        for response in responses:
            request_counts[response.model] = request_counts.get(response.model, 0) + 1
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
            model_request_counts=tuple(request_counts.items()),
            tool_failures=tuple(tool_failures),
        )


def _resolve_adapter_id(adapter_id: str | None, provider_name: str | None) -> str:
    if adapter_id is not None and provider_name is not None and adapter_id != provider_name:
        raise ValueError("adapter_id and legacy provider_name select different adapters")
    selected = adapter_id if adapter_id is not None else provider_name
    if (
        not isinstance(selected, str)
        or not selected.strip()
        or selected != selected.strip()
    ):
        raise ValueError("adapter_id must be a non-empty normalized registry lookup key")
    return selected


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
