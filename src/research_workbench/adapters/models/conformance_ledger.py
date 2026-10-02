"""Pure, process-local token accounting for bounded conformance attempts.

The caller attests input upper bounds, actual send markers and independently
verified receipts. This helper does not tokenize, call a Provider, authenticate
those assertions, persist state or enforce a budget across processes/restarts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, NoReturn

from research_workbench.adapters.models.port import Usage

_MAX_COUNT = 2**63 - 1


class ConformanceLedgerError(ValueError):
    """Content-free failure code; no caller values or chained exception."""

    def __init__(self, code: str):
        self.code = code
        super().__init__("conformance usage ledger: " + code)


def _fail(code: str) -> NoReturn:
    # Caller may be handling a raw Provider exception. Clear the interpreter's
    # implicit context in finally after raise attaches it, before propagation.
    error = ConformanceLedgerError(code)
    try:
        raise error from None
    finally:
        error.__cause__ = None
        error.__context__ = None
        error.__suppress_context__ = True


def _positive(value: object, *, maximum: int | None = None) -> bool:
    return type(value) is int and value > 0 and (maximum is None or value <= maximum)


@dataclass(frozen=True, slots=True)
class ConformanceUsageLimits:
    total_token_limit: int
    max_attempts: int = 3
    max_invocations_per_attempt: int = 3
    max_output_tokens_per_invocation: int = 256

    def __post_init__(self) -> None:
        if not (
            _positive(self.total_token_limit, maximum=_MAX_COUNT)
            and _positive(self.max_attempts, maximum=3)
            and _positive(self.max_invocations_per_attempt, maximum=3)
            and _positive(self.max_output_tokens_per_invocation, maximum=256)
        ):
            _fail("invalid-limits")


@dataclass(frozen=True, slots=True)
class ConformanceReservation:
    reservation_ordinal: int
    attempt_ordinal: int
    input_upper_tokens: int
    output_upper_tokens: int


@dataclass(frozen=True, slots=True)
class VerifiedUsageAccountingReceipt:
    """Caller-verified numeric reconciliation, not authentication by this helper.

    No raw source, provider ID, secret, content hash or arbitrary message is
    accepted. Source/persistence/authority pins belong to the calling protocol.
    """

    reservation_ordinal: int
    attempt_ordinal: int
    usage: Usage
    verified: bool
    version: str = "1.0.0"
    verification_basis: str = "independent-accounting-reconciliation"


@dataclass(slots=True)
class _Attempt:
    ordinal: int
    repair_refreeze_asserted: bool
    status: str = "open"
    invocations: int = 0


@dataclass(slots=True)
class _Call:
    ordinal: int
    attempt: int
    input_upper: int
    output_upper: int
    handle: ConformanceReservation = field(repr=False)
    send_attempted: bool = False
    settled: bool = False
    response_received: bool = False
    successful_reported: bool = False
    outcome: str = "reserved"
    accounting_status: str = "reserved"
    reported_usage: dict[str, object] | None = None
    verified_usage: dict[str, object] | None = None

    @property
    def reserved_tokens(self) -> int:
        return self.input_upper + self.output_upper

    @property
    def effective_usage(self) -> dict[str, object] | None:
        return self.verified_usage if self.verified_usage is not None else self.reported_usage


# Explicit supported ISO4217 codes for reported costs. Unknown codes fail
# closed; this is not a promise to support every currency or infer exchange rates.
_COST_CURRENCIES = frozenset({"USD", "CNY", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "HKD", "SGD"})


def _normalized_usage(value: Usage | None) -> tuple[dict[str, object] | None, str | None]:
    if type(value) is not Usage:
        return None, "usage-unavailable"
    # Detach each field before validation: later reflective mutation of a caller's
    # frozen dataclass must not change the values we accept/store.
    input_tokens, output_tokens = value.input_tokens, value.output_tokens
    cached_input_tokens, reasoning_tokens = value.cached_input_tokens, value.reasoning_tokens
    cost, currency = value.provider_reported_cost, value.currency
    if any(type(item) is not int or not 0 <= item <= _MAX_COUNT for item in (input_tokens, output_tokens)):
        return None, "invalid-token-usage"
    for subset, total in ((cached_input_tokens, input_tokens), (reasoning_tokens, output_tokens)):
        if subset is not None and (type(subset) is not int or subset < 0 or subset > total):
            return None, "invalid-token-subset"
    if cost is not None and (
        type(cost) not in {int, float} or cost < 0 or cost > 1.7976931348623157e308 or not math.isfinite(cost)
    ):
        return None, "invalid-reported-cost"
    if currency is not None and (type(currency) is not str or currency not in _COST_CURRENCIES):
        return None, "unsupported-cost-currency"
    if cost is not None and currency is None:
        return None, "reported-cost-currency-unavailable"
    return {
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "cached_input_tokens": cached_input_tokens, "reasoning_tokens": reasoning_tokens,
        "provider_reported_cost": cost, "currency": currency,
        "cost_status": "provider-reported" if cost is not None else "unknown",
    }, None


class ConformanceUsageLedger:
    """One bounded plan: serial reservations, honest failures, no automatic retry."""

    def __init__(
        self, *, total_token_limit: int, max_attempts: int = 3,
        max_invocations_per_attempt: int = 3, max_output_tokens_per_invocation: int = 256,
    ) -> None:
        self._limits = ConformanceUsageLimits(
            total_token_limit, max_attempts, max_invocations_per_attempt,
            max_output_tokens_per_invocation,
        )
        self._lock = RLock()
        self._attempts: list[_Attempt] = []
        self._calls: list[_Call] = []
        self._handles: dict[int, _Call] = {}
        self._active: _Call | None = None

    @property
    def limits(self) -> ConformanceUsageLimits:
        # A fresh frozen value prevents reflective mutation of exposed limits
        # from changing the private limits used for accounting.
        item = self._limits
        return ConformanceUsageLimits(
            item.total_token_limit, item.max_attempts,
            item.max_invocations_per_attempt, item.max_output_tokens_per_invocation,
        )

    def start_attempt(self, *, repair_refreeze_confirmed: bool = False) -> int:
        with self._lock:
            if type(repair_refreeze_confirmed) is not bool:
                _fail("invalid-refreeze-assertion")
            if self._active is not None or (self._attempts and self._attempts[-1].status == "open"):
                _fail("attempt-still-active")
            if self._blocked_reason() is not None:
                _fail("accounting-blocked")
            if len(self._attempts) >= self._limits.max_attempts:
                _fail("attempt-budget-exhausted")
            if self._attempts and not repair_refreeze_confirmed:
                _fail("fresh-refreeze-assertion-required")
            ordinal = len(self._attempts) + 1
            self._attempts.append(_Attempt(ordinal, repair_refreeze_confirmed))
            return ordinal

    def reserve(self, *, input_upper_tokens: int, output_upper_tokens: int) -> ConformanceReservation:
        """Reserve explicit caller bounds before invoking a Provider/send.

        No context-window or tokenizer assumption is supplied here. Successful
        reservation consumes a Provider invocation slot even if later rejected
        without an HTTP send. Only one active reservation is allowed.
        """
        with self._lock:
            attempt = self._open_attempt()
            if self._active is not None:
                _fail("reservation-still-active")
            if self._blocked_reason() is not None:
                attempt.status = "failed"
                _fail("accounting-blocked")
            if not _positive(input_upper_tokens) or not _positive(
                output_upper_tokens, maximum=self._limits.max_output_tokens_per_invocation
            ):
                attempt.status = "failed"
                _fail("invalid-explicit-token-bound")
            if attempt.invocations >= self._limits.max_invocations_per_attempt:
                attempt.status = "failed"
                _fail("invocation-budget-exhausted")
            known, held = self._token_exposure()
            if input_upper_tokens + output_upper_tokens > self._limits.total_token_limit - known - held:
                attempt.status = "failed"
                _fail("token-budget-exhausted")
            ordinal = len(self._calls) + 1
            handle = ConformanceReservation(ordinal, attempt.ordinal, input_upper_tokens, output_upper_tokens)
            call = _Call(ordinal, attempt.ordinal, input_upper_tokens, output_upper_tokens, handle)
            self._calls.append(call)
            self._handles[id(handle)] = call
            self._active = call
            attempt.invocations += 1
            return handle

    def mark_send_attempt(self, reservation: ConformanceReservation) -> None:
        """Record the caller's actual HTTP send marker, at most once."""
        with self._lock:
            call = self._require_active(reservation)
            if call.send_attempted:
                _fail("send-already-marked")
            call.send_attempted = True

    def reject_before_send(self, reservation: ConformanceReservation) -> None:
        """Release a caller-confirmed unsent refusal/cancellation; retain failure."""
        with self._lock:
            call = self._require_active(reservation)
            if call.send_attempted:
                _fail("cannot-release-started-send")
            call.settled = True
            call.outcome = "failed-before-send"
            call.accounting_status = "released-before-send"
            self._attempts[call.attempt - 1].status = "failed"
            self._active = None

    def settle(
        self, reservation: ConformanceReservation, *, usage: Usage | None,
        successful: bool, response_received: bool,
    ) -> None:
        """Account success or failure; any failure closes this Attempt immediately.

        Incomplete/invalid usage retains conservative exposure and halts new
        requests. Complete valid usage is counted even on a failed invocation.
        Unknown monetary cost does not discard otherwise valid token counts.
        """
        with self._lock:
            call = self._require_active(reservation)
            if not call.send_attempted:
                _fail("send-marker-required")
            if type(successful) is not bool or type(response_received) is not bool or (successful and not response_received):
                _fail("invalid-response-outcome")
            normalized, issue = _normalized_usage(usage)
            call.settled = True
            call.response_received = response_received
            call.successful_reported = successful
            call.outcome = "succeeded" if successful else "failed"
            call.reported_usage = normalized
            call.accounting_status = "unresolved" if issue is not None else "known"
            self._active = None
            if normalized is not None and (
                normalized["input_tokens"] > call.input_upper
                or normalized["output_tokens"] > call.output_upper
            ):
                call.accounting_status = "reservation-exceeded"
                issue = "reservation-exceeded"
            known, _ = self._token_exposure()
            if known > self._limits.total_token_limit:
                call.accounting_status = "total-limit-exceeded"
                issue = "total-token-limit-exceeded"
            if not successful or issue is not None:
                self._attempts[call.attempt - 1].status = "failed"
            if issue is not None:
                _fail(issue)

    def reconcile(
        self, reservation: ConformanceReservation, *, receipt: VerifiedUsageAccountingReceipt,
    ) -> None:
        """Apply an explicit caller-verified receipt without removing original facts.

        The helper verifies shape/numerics/local call identity, not external
        receipt authenticity, authority, billing settlement or source pins.
        """
        with self._lock:
            call = self._lookup(reservation)
            if call.accounting_status not in {"unresolved", "reservation-exceeded"} or not call.settled:
                _fail("reconciliation-not-eligible")
            if (
                type(receipt) is not VerifiedUsageAccountingReceipt
                or type(receipt.verified) is not bool or not receipt.verified
                or type(receipt.version) is not str
                or receipt.version != "1.0.0"
                or type(receipt.verification_basis) is not str
                or receipt.verification_basis != "independent-accounting-reconciliation"
                or type(receipt.reservation_ordinal) is not int
                or type(receipt.attempt_ordinal) is not int
                or receipt.reservation_ordinal != call.ordinal or receipt.attempt_ordinal != call.attempt
            ):
                _fail("unverified-accounting-receipt")
            normalized, issue = _normalized_usage(receipt.usage)
            if issue is not None:
                _fail("invalid-accounting-receipt-usage")
            assert normalized is not None
            if normalized["input_tokens"] > call.input_upper or normalized["output_tokens"] > call.output_upper:
                _fail("receipt-exceeds-reservation")
            previous = call.verified_usage
            call.verified_usage = normalized
            known, _ = self._token_exposure()
            if known > self._limits.total_token_limit:
                call.verified_usage = previous
                _fail("receipt-exceeds-total-limit")
            call.accounting_status = "verified-reconciled"
            # Failed Attempt remains failed; no retry or next Attempt starts.

    def finish_attempt(self) -> None:
        with self._lock:
            attempt = self._open_attempt()
            if self._active is not None:
                _fail("reservation-still-active")
            if self._blocked_reason() is not None:
                attempt.status = "failed"
                _fail("accounting-blocked")
            attempt.status = "completed"

    def snapshot(self) -> dict[str, Any]:
        """Return a fresh closed primitive snapshot; no mutable state escapes."""
        with self._lock:
            known, held = self._token_exposure()
            usage_records = [call.effective_usage for call in self._calls if call.effective_usage is not None]
            costs: dict[str, float | int | None] = {}
            for item in usage_records:
                if item["provider_reported_cost"] is not None:
                    currency = item["currency"]
                    if currency in costs and costs[currency] is None:
                        continue
                    total = costs.get(currency, 0) + item["provider_reported_cost"]
                    costs[currency] = total if total <= 1.7976931348623157e308 and math.isfinite(total) else None
            return {
                "ledger_version": "1.0.0", "scope": "process-local-caller-attested",
                "limits": {
                    "total_token_limit": self._limits.total_token_limit,
                    "max_attempts": self._limits.max_attempts,
                    "max_invocations_per_attempt": self._limits.max_invocations_per_attempt,
                    "max_output_tokens_per_invocation": self._limits.max_output_tokens_per_invocation,
                },
                "blocked": self._blocked_reason() is not None,
                "blocked_reason": self._blocked_reason(),
                "provider_invocations": len(self._calls),
                "http_send_attempts": sum(call.send_attempted for call in self._calls),
                "responses_received": sum(call.response_received for call in self._calls),
                "successful_responses": sum(call.successful_reported and call.response_received for call in self._calls),
                "failed_invocations": sum(call.outcome in {"failed", "failed-before-send"} for call in self._calls),
                "known_input_tokens": sum(item["input_tokens"] for item in usage_records),
                "known_output_tokens": sum(item["output_tokens"] for item in usage_records),
                "known_total_tokens": known, "unresolved_reserved_tokens": held,
                "remaining_token_capacity": max(0, self._limits.total_token_limit - known - held),
                "cost": {
                    "basis": "provider-reported-only", "amounts_by_currency": dict(costs),
                    "unknown_call_count": sum(call.send_attempted and (
                        call.effective_usage is None or call.effective_usage["provider_reported_cost"] is None
                    ) for call in self._calls),
                    "estimated_cost_computed": False, "billing_settlement_verified": False,
                    "aggregation_status": "nonfinite-unavailable" if any(value is None for value in costs.values()) else "finite",
                },
                "attempts": [{
                    "ordinal": attempt.ordinal, "status": attempt.status,
                    "provider_invocations": attempt.invocations,
                    "repair_refreeze_asserted": attempt.repair_refreeze_asserted,
                } for attempt in self._attempts],
                "calls": [{
                    "ordinal": call.ordinal, "attempt_ordinal": call.attempt,
                    "input_upper_tokens": call.input_upper, "output_upper_tokens": call.output_upper,
                    "send_attempted": call.send_attempted, "settled": call.settled,
                    "response_received": call.response_received, "successful_reported": call.successful_reported,
                    "outcome": call.outcome, "accounting_status": call.accounting_status,
                    "reported_usage": dict(call.reported_usage) if call.reported_usage is not None else None,
                    "verified_usage": dict(call.verified_usage) if call.verified_usage is not None else None,
                } for call in self._calls],
            }

    def _lookup(self, reservation: ConformanceReservation) -> _Call:
        if type(reservation) is not ConformanceReservation:
            _fail("invalid-reservation")
        call = self._handles.get(id(reservation))
        if call is None or call.handle is not reservation:
            _fail("foreign-reservation")
        if (
            any(type(value) is not int for value in (
                reservation.reservation_ordinal, reservation.attempt_ordinal,
                reservation.input_upper_tokens, reservation.output_upper_tokens,
            ))
            or reservation.reservation_ordinal != call.ordinal or reservation.attempt_ordinal != call.attempt
            or reservation.input_upper_tokens != call.input_upper or reservation.output_upper_tokens != call.output_upper
        ):
            _fail("reservation-integrity-failed")
        return call

    def _require_active(self, reservation: ConformanceReservation) -> _Call:
        call = self._lookup(reservation)
        if call is not self._active or call.settled:
            _fail("reservation-already-settled-or-inactive")
        return call

    def _open_attempt(self) -> _Attempt:
        if not self._attempts or self._attempts[-1].status != "open":
            _fail("open-attempt-required")
        return self._attempts[-1]

    def _token_exposure(self) -> tuple[int, int]:
        known = 0
        held = 0
        for call in self._calls:
            usage = call.effective_usage
            used = usage["input_tokens"] + usage["output_tokens"] if usage is not None else 0
            known += used
            if call.accounting_status in {"reserved", "unresolved", "reservation-exceeded", "total-limit-exceeded"}:
                held += max(0, call.reserved_tokens - used)
        return known, held

    def _blocked_reason(self) -> str | None:
        if any(call.accounting_status == "total-limit-exceeded" for call in self._calls):
            return "total-token-limit-exceeded"
        if any(call.accounting_status == "reservation-exceeded" for call in self._calls):
            return "reservation-exceeded"
        if any(call.accounting_status == "unresolved" for call in self._calls):
            return "unresolved-accounting"
        return None
