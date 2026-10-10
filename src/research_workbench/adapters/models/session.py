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
    ProviderError,
    ProviderErrorCategory,
    ProviderRegistry,
    ToolCall,
    ToolDefinition,
    Usage,
)
from research_workbench.adapters.models.session_policy import (
    ConformanceSessionPolicy, ConformanceSessionSummarySink,
    freeze_json, freeze_request, freeze_response,
    json_content_sha256, request_content_sha256, response_content_sha256,
    validate_summary_event,
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
        self._provider_invocations = 0
        self._tool_dispatches: list[tuple[str, str]] = []

    @property
    def dispatch_facts(self) -> Mapping[str, Any]:
        """Detached actual invocation facts for the current/most recent run.

        A caller owns this Runner for one run at a time. Durable intent capture
        and an admission callback do not count as an actual dispatch. Facts also
        remain available if capture or a Provider raises before run returns.
        """
        return {"provider_invocations": self._provider_invocations,
                "tool_invocations": len(self._tool_dispatches),
                "tool_calls": tuple(self._tool_dispatches)}

    def run(
        self,
        *,
        provider_name: str,
        request: ModelRequest,
        limits: ApiSessionLimits,
        cancel_requested: Callable[[], bool] | None = None,
        event_sink: SessionEventSink | ConformanceSessionSummarySink | None = None,
        tool_choice_transition: ConformanceSessionPolicy | None = None,
        deadline_monotonic: float | None = None,
        dispatch_guard: Callable[[str, Mapping[str, Any]], bool] | None = None,
    ) -> ApiSessionResult:
        self._provider_invocations = 0
        self._tool_dispatches = []
        if deadline_monotonic is not None and (
            isinstance(deadline_monotonic, bool)
            or not isinstance(deadline_monotonic, (int, float))
            or not math.isfinite(deadline_monotonic)
        ):
            raise ValueError("absolute Session deadline must be finite")
        if tool_choice_transition is not None:
            return self._run_conformance_session(
                provider_name=provider_name, request=request, limits=limits,
                cancel_requested=cancel_requested, event_sink=event_sink,
                policy=tool_choice_transition,
                deadline_monotonic=deadline_monotonic, dispatch_guard=dispatch_guard,
            )
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
        deadline = min(started + limits.max_seconds, deadline_monotonic) if deadline_monotonic is not None else started + limits.max_seconds
        guarded_dispatch = deadline_monotonic is not None or dispatch_guard is not None

        def expired() -> bool:
            observed = self._clock()
            return (isinstance(observed, bool) or not isinstance(observed, (int, float))
                    or not math.isfinite(observed) or observed < started or observed >= deadline)

        def paused(reason: str) -> ApiSessionResult:
            return self._finish(ApiSessionStatus.SAFE_PAUSED, reason, provider_name,
                request.model, responses, tool_call_count, warnings, event_sink)

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
            if expired():
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
            # Durable capture and boundary validation can be slow. The final
            # admission occurs after them, immediately before the real send.
            if guarded_dispatch and expired():
                return paused("wall-time-budget")
            if dispatch_guard is not None and dispatch_guard("provider", {"request": current}) is not True:
                return paused("dispatch-blocked")
            if guarded_dispatch and expired():
                return paused("wall-time-budget")
            try:
                self._provider_invocations += 1
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
            if expired():
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
                    if guarded_dispatch and expired():
                        return paused("wall-time-budget")
                    binding = self._tools[call.name]
                    # Invocation is the accounting boundary: failures and
                    # oversized results still consumed a call and may have
                    # produced an observable side effect.
                    if event_sink is not None:
                        event_sink.record(
                            "tool-attempted",
                            {"call_id": call.call_id, "name": call.name, "arguments": dict(call.arguments)},
                        )
                    if guarded_dispatch and expired():
                        return paused("wall-time-budget")
                    if dispatch_guard is not None and dispatch_guard("tool", {
                        "call_id": call.call_id, "name": call.name, "arguments": dict(call.arguments),
                    }) is not True:
                        return paused("dispatch-blocked")
                    if guarded_dispatch and expired():
                        return paused("wall-time-budget")
                    tool_call_count += 1
                    self._tool_dispatches.append((call.call_id, call.name))
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

    def _run_conformance_session(
        self,
        *,
        provider_name: str,
        request: ModelRequest,
        limits: ApiSessionLimits,
        cancel_requested: Callable[[], bool] | None,
        event_sink: SessionEventSink | ConformanceSessionSummarySink | None,
        policy: ConformanceSessionPolicy,
        deadline_monotonic: float | None,
        dispatch_guard: Callable[[str, Mapping[str, Any]], bool] | None,
    ) -> ApiSessionResult:
        """Opt-in, two-attempt specific -> successful Tool result -> none path.

        The default loop above is deliberately unchanged. Policy does not score
        probe business success: the caller must validate the final synthetic
        assertion independently. A versioned privacy summary sink receives only
        detached primitives; generic Agent Trace is not compatible with this
        policy. Callers own their cross-probe actual-send invocation ledger.
        """
        if type(policy) is not ConformanceSessionPolicy:
            raise ValueError("tool_choice_transition requires an immutable conformance Session policy")
        if event_sink is not None and getattr(event_sink, "conformance_summary_version", None) != "1.0.0":
            raise ValueError("explicit conformance policy requires a versioned privacy summary sink")
        frozen_policy = ConformanceSessionPolicy.from_mapping(policy.to_mapping())
        policy_hash = frozen_policy.sha256
        # Capture a private ceiling snapshot: even reflective mutations of the
        # caller's frozen dataclass cannot enlarge this invocation's budget.
        limits = replace(limits, allowed_tool_side_effects=frozenset(limits.allowed_tool_side_effects))
        if (
            any(type(value) is not int for value in (
                limits.max_model_turns, limits.max_tool_calls, limits.max_parallel_tool_calls,
                limits.max_tool_result_chars, limits.max_output_tokens_per_turn,
            ))
            or not math.isfinite(limits.max_seconds)
            or (limits.max_total_tokens is not None and type(limits.max_total_tokens) is not int)
            or (limits.max_provider_reported_cost is not None and (
                type(limits.max_provider_reported_cost) not in {int, float}
                or not math.isfinite(limits.max_provider_reported_cost)
            ))
            or limits.max_model_turns != frozen_policy.max_model_turns
            or limits.max_tool_calls != frozen_policy.max_tool_calls
            or limits.max_parallel_tool_calls != 1
            or limits.allowed_tool_side_effects != frozenset({"read-only"})
        ):
            raise ValueError("conformance Session limits must match the frozen policy ceilings")
        bounded_request = freeze_request(replace(
            request,
            max_output_tokens=min(
                request.max_output_tokens or limits.max_output_tokens_per_turn,
                limits.max_output_tokens_per_turn,
            ),
        ))
        if (
            len(bounded_request.tools) != 1
            or bounded_request.tools[0].name != frozen_policy.expected_tool_name
            or bounded_request.tool_choice != frozen_policy.initial_choice
            or bounded_request.response_format.kind != "text"
            or bounded_request.response_format.schema is not None
            or bool(bounded_request.metadata)
            or bool(bounded_request.extensions)
            or any(block.kind in {"tool_call", "tool_result"}
                   for message in bounded_request.messages for block in message.content)
        ):
            raise ValueError("conformance Session request must select its one fresh client Tool with empty metadata/extensions")
        if set(self._tools) != {frozen_policy.expected_tool_name}:
            raise ValueError("conformance Session must bind exactly its declared client Tool")
        tool = self._tools[frozen_policy.expected_tool_name]
        if tool.side_effect != "read-only" or tool.definition != bounded_request.tools[0]:
            raise ValueError("conformance Session handler definition or read-only ceiling differs")
        execute_tool = tool.execute
        request_hash = request_content_sha256(bounded_request)
        provider = self._providers.require(provider_name, bounded_request)
        identity = provider.capabilities()
        if not identity.models or bounded_request.model not in identity.models:
            raise ValueError("conformance Session requires an explicitly configured model identity")
        started = self._clock()
        cancelled = cancel_requested or (lambda: False)
        messages = list(bounded_request.messages)
        responses: list[ModelResponse] = []
        warnings: list[str] = []
        tool_call_count = 0
        model_attempts = 0
        local_history_assembled = False
        tool_context_submission_attempts = 0
        current: ModelRequest | None = None
        current_hash: str | None = None
        response: ModelResponse | None = None
        response_hash: str | None = None

        def emit(kind: str, payload: Mapping[str, object]) -> None:
            if event_sink is not None:
                # Only detached JSON primitives leave this boundary. Content
                # hashes used for private drift guards are never exposed: those
                # values could contain accidentally supplied credentials.
                detached = json.loads(json.dumps({
                    "summary_version": "1.0.0", "policy_id": frozen_policy.policy_id,
                    "policy_version": frozen_policy.version, "policy_sha256": policy_hash,
                    **payload,
                }, ensure_ascii=False, allow_nan=False))
                validate_summary_event(kind, detached)
                event_sink.record(kind, detached)

        def finish(status: ApiSessionStatus, reason: str) -> ApiSessionResult:
            payload = {
                "status": status.value, "stop_reason": reason,
                "model_attempts": model_attempts, "successful_responses": len(responses),
                "tool_invocations": tool_call_count,
                "local_tool_history_assembled": local_history_assembled,
                "tool_context_submission_attempts": tool_context_submission_attempts,
            }
            try:
                emit("session-summary", payload)
            except Exception:
                warnings.append("conformance-stop-summary-capture-failed")
                if reason != "trace-capture-gap":
                    # This terminal summary was already attempted. Reporting
                    # its capture gap must not recursively retry that summary.
                    return capture_gap(
                        "session-terminal", "session-summary-capture-failed",
                        terminal_summary_attempted=True,
                    )
            return self._result(status, reason, provider_name, request.model, responses, tool_call_count, warnings)

        def capture_gap(
            phase: str, failure_code: str, *, terminal_summary_attempted: bool = False,
        ) -> ApiSessionResult:
            # Stopping capture is bounded best effort. A broken sink must not
            # erase already received/validated responses or export its error.
            warnings.append("trace-capture-gap")
            try:
                emit("capture-gap-summary", {"phase": phase, "failure_code": failure_code})
            except Exception:
                warnings.append("conformance-gap-summary-capture-failed")
            if terminal_summary_attempted:
                return self._result(
                    ApiSessionStatus.SAFE_PAUSED, "trace-capture-gap", provider_name,
                    request.model, responses, tool_call_count, warnings,
                )
            return finish(ApiSessionStatus.SAFE_PAUSED, "trace-capture-gap")

        def boundary_reason() -> str | None:
            try:
                if policy.sha256 != policy_hash or frozen_policy.sha256 != policy_hash:
                    return "conformance-session-policy-drift"
                if request_content_sha256(bounded_request) != request_hash:
                    return "conformance-session-request-drift"
                if current is not None and request_content_sha256(current) != current_hash:
                    return "conformance-session-request-drift"
                if response is not None and response_content_sha256(response) != response_hash:
                    return "conformance-session-response-drift"
            except (ValueError, TypeError, AttributeError):
                return "conformance-session-content-drift"
            if cancelled():
                return "cancellation-requested"
            observed_time = self._clock()
            if not math.isfinite(started) or not math.isfinite(observed_time) or observed_time < started:
                return "wall-time-clock-invalid"
            if (observed_time - started >= limits.max_seconds
                    or deadline_monotonic is not None and observed_time >= deadline_monotonic):
                return "wall-time-budget"
            return None

        for turn in range(frozen_policy.max_model_turns):
            reason = boundary_reason()
            if reason is not None:
                return finish(ApiSessionStatus.SAFE_PAUSED, reason)
            current = replace(
                bounded_request, messages=tuple(messages),
                tool_choice=(frozen_policy.initial_choice if turn == 0
                             else frozen_policy.after_successful_tool_result),
            )
            current_hash = request_content_sha256(current)
            try:
                emit("request-summary", {
                    "phase": "specific-tool" if turn == 0 else "result-text",
                    "provider": identity.provider, "requested_model": bounded_request.model,
                    "tool_choice_kind": current.tool_choice.kind,
                    "tool_choice_name": current.tool_choice.name,
                    "model_attempt": turn + 1, "history_message_count": len(current.messages),
                    "tool_result_in_local_history": local_history_assembled,
                })
            except Exception:
                return capture_gap("provider-request", "request-summary-capture-failed")
            reason = boundary_reason()
            if reason is not None:
                return finish(ApiSessionStatus.SAFE_PAUSED, reason)
            if dispatch_guard is not None and dispatch_guard("provider", {"request": current}) is not True:
                return finish(ApiSessionStatus.SAFE_PAUSED, "dispatch-blocked")
            reason = boundary_reason()
            if reason is not None:
                return finish(ApiSessionStatus.SAFE_PAUSED, reason)
            try:
                model_attempts += 1
                if turn == 1:
                    tool_context_submission_attempts += 1
                self._provider_invocations += 1
                response = validate_response_contract(current, freeze_response(provider.generate(current)))
                response_hash = response_content_sha256(response)
            except ProviderError as exc:
                category = exc.category if isinstance(exc.category, ProviderErrorCategory) else ProviderErrorCategory.UNKNOWN
                warnings.append(f"provider error category: {category}")
                return finish(
                    ApiSessionStatus.SAFE_PAUSED if category == ProviderErrorCategory.CANCELLED else ApiSessionStatus.FAILED,
                    "provider-cancelled" if category == ProviderErrorCategory.CANCELLED else f"provider-error:{category}",
                )
            except Exception:
                warnings.append("provider exception category: unexpected")
                return finish(ApiSessionStatus.FAILED, "provider-exception:unexpected")
            # Provider facts are recorded after freezing/contract validation,
            # before optional summary capture can fail and stop execution.
            responses.append(response)
            if event_sink is not None:
                try:
                    def token_value(value: object) -> int | None:
                        return value if type(value) is int and value >= 0 else None

                    reported_cost = response.usage.provider_reported_cost
                    cost_value = reported_cost if (
                        type(reported_cost) in {int, float} and math.isfinite(reported_cost) and reported_cost >= 0
                    ) else None
                    emit("response-summary", {
                        "model_attempt": model_attempts, "tool_call_count": len(response.tool_calls),
                        "output_kinds": sorted({"text" if block.kind == "text" else "unsupported" for block in response.output}),
                        "finish_reason": response.finish_reason.value if isinstance(response.finish_reason, FinishReason) else FinishReason.UNKNOWN.value,
                        "input_tokens": token_value(response.usage.input_tokens),
                        "output_tokens": token_value(response.usage.output_tokens),
                        "cached_input_tokens": token_value(response.usage.cached_input_tokens),
                        "reasoning_tokens": token_value(response.usage.reasoning_tokens),
                        "provider_reported_cost": cost_value,
                        "cost_currency": response.usage.currency if response.usage.currency in {"USD", "CNY"} else None,
                    })
                except Exception:
                    return capture_gap("provider-response", "response-summary-capture-failed")
            warnings.extend(response.warnings)
            reason = boundary_reason()
            if reason is not None:
                return finish(ApiSessionStatus.SAFE_PAUSED, reason)
            if any(type(value) is not int or value < 0 for value in (
                response.usage.input_tokens, response.usage.output_tokens
            )):
                return finish(ApiSessionStatus.SAFE_PAUSED, "token-usage-unavailable")
            cost = response.usage.provider_reported_cost
            if cost is not None and (
                type(cost) not in {int, float} or not math.isfinite(cost) or cost < 0
            ):
                return finish(ApiSessionStatus.SAFE_PAUSED, "cost-usage-unavailable")
            reason = _usage_budget_reason(responses, limits)
            if reason is not None:
                return finish(ApiSessionStatus.SAFE_PAUSED, reason)
            if any(block.kind != "text" for block in response.output):
                return finish(ApiSessionStatus.FAILED, "conformance-output-kind-unsupported")
            if turn == 1:
                status, terminal_reason = _terminal_status(response.finish_reason)
                if status != ApiSessionStatus.COMPLETED:
                    return finish(status, terminal_reason)
                if not any(block.kind == "text" and (block.text or "").strip() for block in response.output):
                    return finish(ApiSessionStatus.FAILED, "conformance-result-text-empty")
                return finish(status, terminal_reason)
            if (
                response.finish_reason != FinishReason.TOOL_CALL
                or len(response.tool_calls) != frozen_policy.expected_tool_calls
                or any(call.name != frozen_policy.expected_tool_name
                       or call.executed_by != "client"
                       or not isinstance(call.call_id, str) or not call.call_id.strip()
                       for call in response.tool_calls)
            ):
                return finish(ApiSessionStatus.FAILED, "conformance-expected-one-tool")
            call = response.tool_calls[0]
            arguments_hash = json_content_sha256(call.arguments)
            reason = boundary_reason()
            if reason is not None:
                return finish(ApiSessionStatus.SAFE_PAUSED, reason)
            try:
                emit("tool-attempt-summary", {
                    "tool_ordinal": 1, "tool_name": frozen_policy.expected_tool_name,
                    "handler_invoked": False,
                })
            except Exception:
                return capture_gap("tool-attempt", "tool-attempt-summary-capture-failed")
            reason = ("conformance-tool-arguments-drift"
                if json_content_sha256(call.arguments) != arguments_hash else boundary_reason())
            if reason is not None:
                # The attempt was durably announced, but no handler ran.
                # No Tool result or transition is fabricated.
                return finish(ApiSessionStatus.SAFE_PAUSED, reason)
            # Revalidate after the capture boundary before the one invocation.
            validate_response_contract(current, response)
            if dispatch_guard is not None and dispatch_guard("tool", {
                "call_id": call.call_id, "name": call.name, "arguments": dict(call.arguments),
            }) is not True:
                return finish(ApiSessionStatus.SAFE_PAUSED, "dispatch-blocked")
            reason = ("conformance-tool-arguments-drift"
                if json_content_sha256(call.arguments) != arguments_hash else boundary_reason())
            if reason is not None:
                return finish(ApiSessionStatus.SAFE_PAUSED, reason)
            tool_call_count += 1  # Failed handlers consume the one Tool budget.
            self._tool_dispatches.append((call.call_id, call.name))
            try:
                output = freeze_json(execute_tool(call.arguments))
                rendered = output if isinstance(output, str) else json.dumps(
                    output, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
                )
                is_error = False
                output_hash = json_content_sha256(output)
            except Exception as exc:
                output = {"error": type(exc).__name__}
                rendered = ""
                is_error = True
                output_hash = None
            reason = boundary_reason()
            if json_content_sha256(call.arguments) != arguments_hash:
                reason = "conformance-tool-arguments-drift"
            if not is_error and len(rendered) > limits.max_tool_result_chars:
                reason = "tool-result-size-budget"
            deliverable = not is_error and reason is None
            if event_sink is not None:
                try:
                    emit("tool-result-summary", {
                        "tool_ordinal": 1, "tool_name": frozen_policy.expected_tool_name,
                        "status": "failed" if is_error else "succeeded",
                        "handler_invoked": True,
                        "result_eligible_for_local_history": deliverable,
                    })
                except Exception:
                    return capture_gap("tool-result", "tool-summary-capture-failed")
            if is_error:
                return finish(ApiSessionStatus.FAILED, "conformance-tool-handler-failed")
            # Capture may be slow, cancel execution, or reflectively mutate
            # another runtime reference. Recheck content and budgets afterwards.
            reason = boundary_reason() or reason
            if json_content_sha256(call.arguments) != arguments_hash:
                reason = "conformance-tool-arguments-drift"
            if json_content_sha256(output) != output_hash:
                reason = "conformance-tool-result-drift"
            rendered_after_capture = output if isinstance(output, str) else json.dumps(
                output, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
            )
            if len(rendered_after_capture) > limits.max_tool_result_chars:
                reason = "tool-result-size-budget"
            if reason is not None:
                return finish(ApiSessionStatus.SAFE_PAUSED, reason)
            messages.append(Message("assistant", tuple([
                *response.output, _tool_call_block(call),
            ])))
            messages.append(Message("tool", (ContentBlock(
                kind="tool_result", data=freeze_json({
                    "call_id": call.call_id, "name": call.name, "output": output, "is_error": False,
                }),
            ),)))
            local_history_assembled = True
            try:
                emit("tool-context-summary", {
                    "tool_ordinal": 1, "tool_name": frozen_policy.expected_tool_name,
                    "local_history_assembled": True, "result_entered_context": True,
                    "context_scope": "local-history",
                })
            except Exception:
                return capture_gap("tool-context", "tool-context-summary-capture-failed")
        return finish(ApiSessionStatus.FAILED, "conformance-session-terminal-missing")

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
