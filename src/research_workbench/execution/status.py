"""Single source of truth for session-outcome to closeout-status mapping.

Every closeout document (Attempt, Handoff, Execution Receipt, Main State)
derives its status from this table so the file chain can never disagree
about what happened.
"""

from __future__ import annotations

from dataclasses import dataclass

from research_workbench.adapters.models import ApiSessionStatus


CONTINUITY_FOR_RECORD_STATUS = {
    "completed": "stage-completed",
    "stage-completed": "stage-completed",
    "safe-paused": "safe-paused",
    "blocked": "blocked",
    "incomplete": "waiting",
    "waiting": "waiting",
    "failed": "blocked",
    "cancelled": "blocked",
}


@dataclass(frozen=True, slots=True)
class CloseoutStatuses:
    record_status: str
    continuity_status: str
    rollover_reason: str
    completion_claim: str | None


def map_outcome(
    status: ApiSessionStatus,
    stop_reason: str,
    *,
    check_passed: bool = False,
    model_drift: bool = False,
) -> CloseoutStatuses:
    """Map one API session outcome onto the statuses of the whole file chain."""

    if status == ApiSessionStatus.COMPLETED:
        record = "completed"
        reason = "task closed at its atomic boundary"
        claim = "execution-only" if not check_passed else "contract-satisfied"
        if model_drift:
            claim = None
            reason = (
                "provider-reported model differs from the requested slot; "
                "completion claim withheld"
            )
        return CloseoutStatuses(record, CONTINUITY_FOR_RECORD_STATUS[record], reason, claim)
    if status == ApiSessionStatus.SAFE_PAUSED:
        record = "safe-paused"
        reason = f"api-session safe pause: {stop_reason}"
    elif status == ApiSessionStatus.BLOCKED:
        record = "blocked"
        reason = f"provider refusal: {stop_reason}"
    elif status == ApiSessionStatus.INCOMPLETE:
        record = "incomplete"
        reason = f"session ended incomplete: {stop_reason}"
    else:
        record = "failed"
        reason = f"session failed: {stop_reason}"
    return CloseoutStatuses(record, CONTINUITY_FOR_RECORD_STATUS[record], reason, None)
