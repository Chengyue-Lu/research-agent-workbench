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
    RiskCodeEntry("TRACE-ACTOR-UNKNOWN", "BLOCK", "An event or message names an unregistered actor."),
    RiskCodeEntry("TRACE-ACTORS-INVALID", "BLOCK", "The actor registry cannot be parsed."),
    RiskCodeEntry("TRACE-CAPTURE-GAP", "WARNING_OR_BLOCK", "The trace declares missing capture."),
    RiskCodeEntry("TRACE-CONTENT-HASH", "BLOCK", "A message body differs from its declared content hash."),
    RiskCodeEntry("TRACE-ENVELOPE-DRIFT", "BLOCK", "Message envelope and index facts disagree."),
    RiskCodeEntry("TRACE-EVENT-BLANK", "BLOCK", "The append-only event ledger contains a blank record."),
    RiskCodeEntry("TRACE-EVENT-COUNT", "BLOCK", "The indexed event count differs from the ledger."),
    RiskCodeEntry("TRACE-EVENT-INVALID", "BLOCK", "An event record is not valid JSON object data."),
    RiskCodeEntry("TRACE-EVENT-SEQUENCE", "BLOCK", "Event sequence is gapped, duplicated, or reordered."),
    RiskCodeEntry("TRACE-FALSE-COMPLETE", "BLOCK", "Completion is inconsistent with trace state or gaps."),
    RiskCodeEntry("TRACE-HASH-DRIFT", "BLOCK", "A referenced trace artifact differs from its hash."),
    RiskCodeEntry("TRACE-IDENTITY-DRIFT", "BLOCK", "Task or Attempt identity differs across trace artifacts."),
    RiskCodeEntry("TRACE-INDEX-INVALID", "BLOCK", "The trace index cannot be parsed."),
    RiskCodeEntry("TRACE-INDEX-MISSING", "BLOCK", "The Attempt has no trace index."),
    RiskCodeEntry("TRACE-MESSAGE-INVALID", "BLOCK", "A message artifact cannot be parsed."),
    RiskCodeEntry("TRACE-MESSAGE-SEQUENCE", "BLOCK", "Message sequence is gapped, duplicated, or reordered."),
    RiskCodeEntry("TRACE-MESSAGE-UNINDEXED", "BLOCK", "A message file is not declared in the index."),
    RiskCodeEntry("TRACE-PATH-ESCAPE", "BLOCK", "A path escapes the validated Attempt root."),
    RiskCodeEntry("TRACE-PROCESS-ARTIFACT-OVERWRITE", "BLOCK", "A protected trace artifact was overwritten."),
    RiskCodeEntry("TRACE-READ-OUTSIDE-ALLOWLIST", "BLOCK", "A recorded read is outside its declared boundary."),
    RiskCodeEntry("TRACE-REDACTION-UNDECLARED", "BLOCK", "Stored redaction markers lack declarations."),
    RiskCodeEntry("TRACE-REF-INVALID", "BLOCK", "A trace artifact reference has an invalid shape."),
    RiskCodeEntry("TRACE-REF-MISSING", "BLOCK", "A referenced trace artifact is missing."),
    RiskCodeEntry("TRACE-SCHEMA-INVALID", "BLOCK", "A trace artifact fails its JSON Schema."),
    RiskCodeEntry("TRACE-TASK-INVALID", "BLOCK", "The captured Task snapshot cannot be parsed."),
    RiskCodeEntry("TRACE-TOOL-OUTSIDE-ALLOWLIST", "BLOCK", "A recorded tool is outside its declared boundary."),
    RiskCodeEntry("TRACE-VALID", "INFO", "Trace facts, hashes, sequences, and boundaries are valid."),
    RiskCodeEntry("TRACE-WRITE-OUTSIDE-SCOPE", "BLOCK", "A recorded revision is outside its declared boundary."),
)

TRACE_RISK_CODES = frozenset(entry.code for entry in TRACE_RISK_CODE_REGISTRY)

__all__ = ["RiskCodeEntry", "TRACE_RISK_CODE_REGISTRY", "TRACE_RISK_CODES"]
