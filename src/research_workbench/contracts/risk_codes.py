"""Deterministic risk codes owned by the file-authoritative Trace Core.

This registry is intentionally limited to M3-008.  It does not assign meaning
to Method, Mode, Skill, Claim, or Human-Gate decisions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskCodeEntry:
    code: str
    severity: str
    summary: str


TRACE_RISK_CODE_REGISTRY = (
    RiskCodeEntry(
        "TRACE-MESSAGE-MISSING",
        "BLOCK",
        "A required message fact or artifact is missing or inconsistent.",
    ),
    RiskCodeEntry(
        "TRACE-SEQUENCE-GAP",
        "BLOCK",
        "An event/message sequence or stable identifier is gapped or duplicated.",
    ),
    RiskCodeEntry(
        "TRACE-ACTOR-UNOWNED",
        "BLOCK",
        "An actor is unregistered, unowned, or inconsistent with its accountable owner.",
    ),
    RiskCodeEntry(
        "TRACE-HASH-MISMATCH",
        "BLOCK",
        "A hash-bound Trace artifact or message body differs from its declared hash.",
    ),
    RiskCodeEntry(
        "TRACE-CAPTURE-DELAYED",
        "WARNING_OR_BLOCK",
        "Capture is delayed, gapped, or inconsistent with completeness metadata.",
    ),
    RiskCodeEntry("TRACE-REDACTION-UNDECLARED", "BLOCK", "Stored redaction markers lack declarations."),
    RiskCodeEntry(
        "TRACE-READ-OUTSIDE-SCOPE",
        "BLOCK",
        "A recorded read, tool, write, or validation path is outside its declared scope.",
    ),
    RiskCodeEntry(
        "TRACE-EVENT-MISSING",
        "BLOCK",
        "A required Trace event, reference, identity, or lifecycle fact is missing or inconsistent.",
    ),
    RiskCodeEntry(
        "TRACE-TRANSIENT-RESULT-MISSING",
        "BLOCK",
        "A transient result that entered context lacks its origin, reference, or artifact.",
    ),
    RiskCodeEntry(
        "TRACE-PROCESS-ARTIFACT-OVERWRITTEN",
        "BLOCK",
        "A protected process artifact was overwritten or deleted.",
    ),
)

TRACE_RISK_CODES = frozenset(entry.code for entry in TRACE_RISK_CODE_REGISTRY)

__all__ = ["RiskCodeEntry", "TRACE_RISK_CODE_REGISTRY", "TRACE_RISK_CODES"]
