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

EXECUTION_TRACE_RISK_CODE_REGISTRY = (
    RiskCodeEntry(
        "RECEIPT-TRACE-IDENTITY",
        "BLOCK",
        "Trace identity differs from its Execution Receipt or Attempt.",
    ),
    RiskCodeEntry(
        "RECEIPT-TRACE-MISMATCH",
        "BLOCK",
        "Attempt and Execution Receipt pin different Trace indexes.",
    ),
    RiskCodeEntry(
        "RECEIPT-TRACE-STATUS",
        "BLOCK",
        "Trace status differs from its Execution Receipt.",
    ),
)

EXECUTION_TRACE_RISK_CODES = frozenset(
    entry.code for entry in EXECUTION_TRACE_RISK_CODE_REGISTRY
)

EXECUTION_ARCHIVE_RISK_CODE_REGISTRY = (
    RiskCodeEntry(
        "EXEC-ARCHIVE-INCOMPLETE",
        "BLOCK",
        "A committed execution archive lacks a required file.",
    ),
    RiskCodeEntry(
        "EXEC-ARCHIVE-INVALID",
        "BLOCK",
        "An execution archive contract or project boundary is invalid.",
    ),
    RiskCodeEntry(
        "EXEC-COMPLETION-MARKER-INVALID",
        "BLOCK",
        "The marker-last manifest is invalid or does not match the archive.",
    ),
    RiskCodeEntry(
        "EXEC-COMPLETION-MARKER-MISSING",
        "BLOCK",
        "The Attempt has not published its marker-last manifest.",
    ),
    RiskCodeEntry(
        "EXEC-TRANSCRIPT-DRIFT",
        "BLOCK",
        "The compatibility transcript differs from its Trace-derived view.",
    ),
)

EXECUTION_ARCHIVE_RISK_CODES = frozenset(
    entry.code for entry in EXECUTION_ARCHIVE_RISK_CODE_REGISTRY
)

RECOVERY_RISK_CODE_REGISTRY = (
    RiskCodeEntry("RECOVERY-ATTEMPT-REUSE", "BLOCK", "Recovery would reuse an Attempt ID or directory."),
    RiskCodeEntry("RECOVERY-HANDOFF-MISMATCH", "BLOCK", "Handoff facts differ from the previous Attempt."),
    RiskCodeEntry("RECOVERY-HANDOFF-MISSING", "BLOCK", "The previous Attempt has no readable Handoff."),
    RiskCodeEntry("RECOVERY-PREVIOUS-INVALID", "BLOCK", "The previous execution archive fails replay."),
    RiskCodeEntry("RECOVERY-READY", "INFO", "Frozen files can seed a distinct new Attempt."),
    RiskCodeEntry("RECOVERY-SOURCE-INVALID", "BLOCK", "A recovery source file is structurally invalid."),
    RiskCodeEntry("RECOVERY-STATE-MISMATCH", "BLOCK", "Main State does not bind the paused Task and Handoff."),
    RiskCodeEntry("RECOVERY-STATE-MISSING", "BLOCK", "Main State is missing or outside the project root."),
    RiskCodeEntry("RECOVERY-STATUS-INVALID", "BLOCK", "The previous Attempt is not safe-paused."),
)

RECOVERY_RISK_CODES = frozenset(entry.code for entry in RECOVERY_RISK_CODE_REGISTRY)

ARTIFACT_RISK_CODE_REGISTRY = (
    RiskCodeEntry(
        "ARTIFACT-HASH-MISMATCH",
        "BLOCK",
        "Admitted or promoted artifact bytes differ from their declared hash.",
    ),
    RiskCodeEntry(
        "ARTIFACT-UNVERSIONED-REF",
        "WARNING_OR_BLOCK",
        "An artifact reference lacks the revision needed for exact replay.",
    ),
    RiskCodeEntry(
        "ARTIFACT-INBOX-CITED",
        "BLOCK",
        "A document cites mutable inbox content that was never admitted.",
    ),
    RiskCodeEntry(
        "ARTIFACT-OVERWRITE",
        "BLOCK",
        "Promotion would overwrite an existing accepted artifact.",
    ),
    RiskCodeEntry(
        "ARTIFACT-MISSING-PROVENANCE",
        "BLOCK",
        "An admitted source lacks the provenance facts required to re-locate it.",
    ),
    RiskCodeEntry(
        "ARTIFACT-NEGATIVE-DROPPED",
        "BLOCK",
        "A checked artifact, including negative results, is absent from the promotion decision.",
    ),
    RiskCodeEntry(
        "ARTIFACT-PROMOTION-BYPASS",
        "BLOCK",
        "Promotion was attempted without a passing validation report or from outside work/.",
    ),
    RiskCodeEntry(
        "REPRO-GAP",
        "WARNING_OR_BLOCK",
        "A run manifest or reproduction attempt lacks facts needed to rebuild the run.",
    ),
)

ARTIFACT_RISK_CODES = frozenset(entry.code for entry in ARTIFACT_RISK_CODE_REGISTRY)

__all__ = [
    "ARTIFACT_RISK_CODE_REGISTRY",
    "ARTIFACT_RISK_CODES",
    "EXECUTION_TRACE_RISK_CODE_REGISTRY",
    "EXECUTION_TRACE_RISK_CODES",
    "EXECUTION_ARCHIVE_RISK_CODE_REGISTRY",
    "EXECUTION_ARCHIVE_RISK_CODES",
    "RiskCodeEntry",
    "RECOVERY_RISK_CODE_REGISTRY",
    "RECOVERY_RISK_CODES",
    "TRACE_RISK_CODE_REGISTRY",
    "TRACE_RISK_CODES",
]
