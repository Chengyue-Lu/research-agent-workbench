"""Deterministic validation for one file-first Agent Trace Archive.

The validator checks observable records and declared omissions. It never asks
for, reconstructs, or scores hidden reasoning.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Mapping

import yaml

from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.contracts import ContractRisk, RiskLevel
from research_workbench.io import load_document
from research_workbench.validation.schemas import SchemaCatalog


@dataclass(frozen=True, slots=True)
class TraceValidationReport:
    trace_id: str
    event_count: int
    message_count: int
    capture_gap_count: int
    risks: tuple[ContractRisk, ...]

    @property
    def blocked(self) -> bool:
        return any(risk.level == RiskLevel.BLOCK for risk in self.risks)


def validate_trace_archive(
    envelope_path: str | Path, *, root: str | Path
) -> TraceValidationReport:
    project_root = Path(root).resolve()
    envelope_file = Path(envelope_path)
    if not envelope_file.is_absolute():
        envelope_file = project_root / envelope_file
    envelope_file = envelope_file.resolve()
    risks: list[ContractRisk] = []
    envelope = _load_mapping(envelope_file, "TRACE-ENVELOPE-INVALID", risks)
    if envelope is None:
        return TraceValidationReport("unknown", 0, 0, 0, tuple(risks))

    catalog = SchemaCatalog()
    _schema_risks(catalog, "agent_trace_envelope", envelope, envelope_file, risks)
    trace_id = str(envelope.get("trace_id", "unknown"))
    if any(risk.level == RiskLevel.BLOCK for risk in risks):
        return TraceValidationReport(trace_id, 0, 0, 0, tuple(risks))

    archive_root = resolve_within_root(project_root, str(envelope["archive_root"]))
    if archive_root is None or not archive_root.is_dir():
        _block(risks, "TRACE-ARCHIVE-ROOT", "archive_root is missing or outside the project root")
    else:
        try:
            envelope_file.relative_to(archive_root)
        except ValueError:
            _block(risks, "TRACE-ARCHIVE-ROOT", "Trace Envelope is not stored below archive_root")

    event_path = _check_ref(project_root, envelope["event_ledger_ref"], "event ledger", risks)
    index_path = _check_ref(project_root, envelope["index_ref"], "Trace Index", risks)
    if event_path is None or index_path is None:
        return TraceValidationReport(trace_id, 0, 0, 0, tuple(risks))

    index = _load_mapping(index_path, "TRACE-INDEX-INVALID", risks)
    if index is None:
        return TraceValidationReport(trace_id, 0, 0, 0, tuple(risks))
    index_schema_start = len(risks)
    _schema_risks(catalog, "agent_trace_index", index, index_path, risks)
    if any(risk.level == RiskLevel.BLOCK for risk in risks[index_schema_start:]):
        return TraceValidationReport(trace_id, 0, 0, 0, tuple(risks))

    if archive_root is not None:
        for label, path in (("event ledger", event_path), ("Trace Index", index_path)):
            try:
                path.relative_to(archive_root)
            except ValueError:
                _block(risks, "TRACE-ARCHIVE-ROOT", f"{label} is not stored below archive_root")

    identity = ("trace_id", "task_id", "attempt_id", "accountable_owner")
    for field in identity:
        if index.get(field) != envelope.get(field):
            _block(risks, "TRACE-INDEX-IDENTITY", f"Index {field} differs from the Envelope")
    if index.get("event_ledger_ref") != envelope.get("event_ledger_ref"):
        _block(risks, "TRACE-INDEX-LEDGER", "Index event_ledger_ref differs from the Envelope")

    actors = _actor_map(envelope.get("actors", []), risks)
    event_schema_start = len(risks)
    events = _load_events(event_path, catalog, risks)
    if any(risk.code == "TRACE-EVENT-INVALID" for risk in risks[event_schema_start:]):
        return TraceValidationReport(trace_id, len(events), 0, 0, tuple(risks))
    _validate_event_sequence(events, risks)
    _validate_event_identity(events, envelope, actors, risks)
    _validate_index_events(index.get("events", []), events, risks)
    _validate_event_scope(events, envelope, actors, project_root, risks)
    _validate_event_relations(events, project_root, risks)
    _validate_file_history(events, project_root, envelope, risks)

    messages = index.get("messages", [])
    if not isinstance(messages, list):
        messages = []
    _validate_messages(messages, events, envelope, actors, project_root, risks)
    _validate_capture(index, events, messages, envelope, risks)

    for key in ("handoff_refs", "decision_refs"):
        for reference in index.get(key, []):
            _check_ref(project_root, reference, key.removesuffix("_refs"), risks)

    gap_count = sum(event.get("event_type") == "capture-gap" for event in events)
    return TraceValidationReport(trace_id, len(events), len(messages), gap_count, tuple(risks))


def _load_mapping(
    path: Path, code: str, risks: list[ContractRisk]
) -> Mapping[str, Any] | None:
    try:
        value = load_document(path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        _block(risks, code, f"cannot load {path}: {exc}")
        return None
    if not isinstance(value, Mapping):
        _block(risks, code, f"{path} must contain an object")
        return None
    return value


def _schema_risks(
    catalog: SchemaCatalog,
    kind: str,
    value: Mapping[str, Any],
    path: Path,
    risks: list[ContractRisk],
) -> None:
    for error in catalog.validate(kind, value):
        _block(risks, "TRACE-SCHEMA-INVALID", f"{path}: {error.pointer}: {error.message}")


def _check_ref(
    root: Path, reference: Any, label: str, risks: list[ContractRisk]
) -> Path | None:
    if not isinstance(reference, Mapping):
        _block(risks, "TRACE-REF-INVALID", f"{label} reference is not an object")
        return None
    raw_path = reference.get("path")
    expected = str(reference.get("sha256", "")).removeprefix("sha256:").lower()
    if not isinstance(raw_path, str):
        _block(risks, "TRACE-REF-INVALID", f"{label} reference lacks a path")
        return None
    resolved = resolve_within_root(root, raw_path)
    if resolved is None:
        _block(risks, "TRACE-REF-OUTSIDE", f"{label} path escapes the project root: {raw_path}")
        return None
    if not resolved.is_file():
        _block(risks, "TRACE-REF-MISSING", f"{label} is missing: {raw_path}")
        return None
    actual = hash_file(resolved)
    if actual != expected:
        _block(risks, "TRACE-HASH-MISMATCH", f"{label} hash mismatch: {raw_path}")
        return None
    return resolved


def _load_events(
    path: Path, catalog: SchemaCatalog, risks: list[ContractRisk]
) -> list[Mapping[str, Any]]:
    events: list[Mapping[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _block(risks, "TRACE-EVENT-MISSING", f"cannot read event ledger: {exc}")
        return events
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            _block(risks, "TRACE-EVENT-INVALID", f"events.jsonl line {line_number}: {exc}")
            continue
        if not isinstance(event, Mapping):
            _block(risks, "TRACE-EVENT-INVALID", f"events.jsonl line {line_number} is not an object")
            continue
        for error in catalog.validate("agent_trace_event", event):
            _block(
                risks,
                "TRACE-EVENT-INVALID",
                f"events.jsonl line {line_number}: {error.pointer}: {error.message}",
            )
        events.append(event)
    if not events:
        _block(risks, "TRACE-EVENT-MISSING", "event ledger contains no events")
    return events


def _actor_map(raw: Any, risks: list[ContractRisk]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    if not isinstance(raw, list):
        return result
    for actor in raw:
        if not isinstance(actor, Mapping):
            continue
        actor_id = actor.get("actor_id")
        if not isinstance(actor_id, str):
            continue
        if actor_id in result:
            _block(risks, "TRACE-ACTOR-DUPLICATE", f"actor_id is repeated: {actor_id}")
        result[actor_id] = actor
        if not str(actor.get("accountable_owner", "")).strip():
            _block(risks, "TRACE-ACTOR-UNOWNED", f"actor has no accountable owner: {actor_id}")
    return result


def _validate_event_sequence(
    events: list[Mapping[str, Any]], risks: list[ContractRisk]
) -> None:
    sequences = [event.get("sequence") for event in events]
    expected = list(range(1, len(events) + 1))
    if sequences != expected:
        _block(risks, "TRACE-SEQUENCE-GAP", f"event sequence must be contiguous {expected}, got {sequences}")
    identifiers = [event.get("event_id") for event in events]
    if len(set(identifiers)) != len(identifiers):
        _block(risks, "TRACE-EVENT-DUPLICATE", "event_id values must be unique")
    timestamps: list[datetime] = []
    for event in events:
        try:
            timestamps.append(datetime.fromisoformat(str(event.get("occurred_at")).replace("Z", "+00:00")))
        except ValueError:
            return
    if timestamps != sorted(timestamps):
        _block(risks, "TRACE-TIME-REVERSAL", "event timestamps move backwards")


def _validate_event_identity(
    events: list[Mapping[str, Any]],
    envelope: Mapping[str, Any],
    actors: Mapping[str, Mapping[str, Any]],
    risks: list[ContractRisk],
) -> None:
    for event in events:
        event_id = event.get("event_id")
        for field in ("trace_id", "task_id", "attempt_id"):
            if event.get(field) != envelope.get(field):
                _block(risks, "TRACE-EVENT-IDENTITY", f"{event_id}: {field} differs from Envelope")
        if event.get("actor_id") not in actors:
            _block(risks, "TRACE-ACTOR-UNOWNED", f"{event_id}: unknown actor {event.get('actor_id')}")


def _validate_index_events(
    raw_index_events: Any,
    events: list[Mapping[str, Any]],
    risks: list[ContractRisk],
) -> None:
    if not isinstance(raw_index_events, list):
        return
    if len(raw_index_events) != len(events):
        _block(risks, "TRACE-INDEX-EVENT-MISMATCH", "Index does not cover every event")
        return
    fields = ("event_id", "sequence", "event_type", "actor_id", "occurred_at", "status")
    for indexed, event in zip(raw_index_events, events, strict=False):
        if not isinstance(indexed, Mapping) or any(indexed.get(field) != event.get(field) for field in fields):
            _block(risks, "TRACE-INDEX-EVENT-MISMATCH", f"Index event differs from ledger at sequence {event.get('sequence')}")


def _matches_scope(path: str, patterns: Any) -> bool:
    if not isinstance(patterns, list):
        return False
    normalized = path.replace("\\", "/").lstrip("./")
    for raw_pattern in patterns:
        if not isinstance(raw_pattern, str):
            continue
        pattern = raw_pattern.replace("\\", "/").lstrip("./")
        if any(marker in pattern for marker in "*?["):
            if fnmatchcase(normalized, pattern):
                return True
        elif normalized == pattern or normalized.startswith(pattern.rstrip("/") + "/"):
            return True
    return False


def _validate_event_scope(
    events: list[Mapping[str, Any]],
    envelope: Mapping[str, Any],
    actors: Mapping[str, Mapping[str, Any]],
    root: Path,
    risks: list[ContractRisk],
) -> None:
    allowed_tools = set(envelope.get("allowed_tools", []))
    for event in events:
        event_id = str(event.get("event_id"))
        event_type = event.get("event_type")
        target = event.get("target") if isinstance(event.get("target"), Mapping) else {}
        authorization = event.get("authorization") if isinstance(event.get("authorization"), Mapping) else {}
        if event_type == "file-read":
            path = target.get("path")
            if not isinstance(path, str) or not _matches_scope(path, envelope.get("read_allowlist")):
                _block(risks, "TRACE-READ-OUTSIDE-SCOPE", f"{event_id}: read is outside read_allowlist: {path}")
            if authorization.get("allowed") is not True:
                _block(risks, "TRACE-READ-OUTSIDE-SCOPE", f"{event_id}: read lacks positive authorization")
            if isinstance(path, str) and target.get("sha256"):
                _check_ref(root, {"path": path, "sha256": target["sha256"]}, "read target", risks)
        elif event_type == "tool-call":
            tool_name = target.get("id")
            if tool_name not in allowed_tools or authorization.get("allowed") is not True:
                _block(risks, "TRACE-TOOL-OUTSIDE-SCOPE", f"{event_id}: Tool is not allowed: {tool_name}")
        elif event_type == "external-action" and event.get("status") == "succeeded":
            if envelope.get("external_actions") == "forbidden":
                _block(risks, "TRACE-EXTERNAL-UNAUTHORIZED", f"{event_id}: external action succeeded while forbidden")
            else:
                approver = actors.get(str(authorization.get("approved_by_actor_id")))
                decision_ref = authorization.get("decision_ref")
                if (
                    authorization.get("allowed") is not True
                    or approver is None
                    or approver.get("actor_kind") != "human"
                    or decision_ref is None
                ):
                    _block(risks, "TRACE-EXTERNAL-UNAUTHORIZED", f"{event_id}: external action lacks auditable human authorization")
                else:
                    _check_ref(root, decision_ref, f"{event_id} authorization decision", risks)


def _validate_event_relations(
    events: list[Mapping[str, Any]], root: Path, risks: list[ContractRisk]
) -> None:
    by_id = {event.get("event_id"): event for event in events}
    results_by_call: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        event_id = str(event.get("event_id"))
        for key in ("request_ref", "result_ref", "tombstone_ref"):
            if key in event:
                _check_ref(root, event[key], f"{event_id} {key}", risks)
        if event.get("event_type") == "tool-result":
            related = str(event.get("related_event_id"))
            call = by_id.get(related)
            if call is None or call.get("event_type") != "tool-call":
                _block(risks, "TRACE-TOOL-RESULT-ORPHAN", f"{event_id}: related Tool call is missing")
            else:
                call_target = call.get("target", {})
                result_target = event.get("target", {})
                if call_target.get("id") != result_target.get("id"):
                    _block(risks, "TRACE-TOOL-RESULT-ORPHAN", f"{event_id}: Tool name differs from its call")
            results_by_call.setdefault(related, []).append(event)
            details = event.get("details", {})
            capture = event.get("capture", {})
            if details.get("transient") is True and "result_ref" not in event and capture.get("status") == "complete":
                _block(risks, "TRACE-TRANSIENT-RESULT-MISSING", f"{event_id}: transient result entered context without a retained result")
        if event.get("related_event_id") and event.get("related_event_id") not in by_id:
            _block(risks, "TRACE-EVENT-RELATION", f"{event_id}: related_event_id is unknown")
    for event in events:
        if event.get("event_type") == "tool-call" and event.get("status") == "succeeded":
            if not results_by_call.get(str(event.get("event_id"))):
                _block(risks, "TRACE-TRANSIENT-RESULT-MISSING", f"{event.get('event_id')}: successful Tool call lacks a result event")


def _validate_file_history(
    events: list[Mapping[str, Any]],
    root: Path,
    envelope: Mapping[str, Any],
    risks: list[ContractRisk],
) -> None:
    last_hash: dict[str, str] = {}
    for event in events:
        if event.get("event_type") != "file-write":
            continue
        event_id = str(event.get("event_id"))
        target = event.get("target", {})
        details = event.get("details", {})
        path = target.get("path")
        operation = details.get("operation")
        if not isinstance(path, str) or not _matches_scope(path, envelope.get("write_scope")):
            _block(risks, "TRACE-WRITE-OUTSIDE-SCOPE", f"{event_id}: write is outside write_scope: {path}")
            continue
        old_hash = str(details.get("old_sha256", "")).removeprefix("sha256:").lower()
        new_hash = str(details.get("new_sha256", "")).removeprefix("sha256:").lower()
        if operation == "create":
            if path in last_hash or not new_hash:
                _block(risks, "TRACE-PROCESS-ARTIFACT-OVERWRITTEN", f"{event_id}: create overwrites an existing process path")
            last_hash[path] = new_hash
        elif operation == "modify":
            if not old_hash or not new_hash or old_hash == new_hash:
                _block(risks, "TRACE-PROCESS-ARTIFACT-OVERWRITTEN", f"{event_id}: modify lacks distinct old/new hashes")
            if path in last_hash and last_hash[path] != old_hash:
                _block(risks, "TRACE-PROCESS-ARTIFACT-OVERWRITTEN", f"{event_id}: modification does not continue the recorded revision")
            last_hash[path] = new_hash
        elif operation == "delete":
            if not old_hash or "tombstone_ref" not in event:
                _block(risks, "TRACE-PROCESS-ARTIFACT-OVERWRITTEN", f"{event_id}: deletion lacks old hash or tombstone")
            last_hash.pop(path, None)
        else:
            _block(risks, "TRACE-PROCESS-ARTIFACT-OVERWRITTEN", f"{event_id}: file-write lacks an operation")
        target_hash = str(target.get("sha256", "")).removeprefix("sha256:").lower()
        if operation != "delete" and target_hash != new_hash:
            _block(risks, "TRACE-PROCESS-ARTIFACT-OVERWRITTEN", f"{event_id}: target hash differs from recorded revision")
        if operation != "delete" and target.get("sha256"):
            _check_ref(root, {"path": path, "sha256": target["sha256"]}, "written artifact", risks)


def _parse_message(path: Path, risks: list[ContractRisk]) -> tuple[Mapping[str, Any] | None, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _block(risks, "TRACE-MESSAGE-MISSING", f"cannot read message {path}: {exc}")
        return None, ""
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        _block(risks, "TRACE-MESSAGE-INVALID", f"message lacks YAML front matter: {path}")
        return None, ""
    header_text, payload = text[4:].split("\n---\n", 1)
    try:
        header = yaml.safe_load(header_text)
    except yaml.YAMLError as exc:
        _block(risks, "TRACE-MESSAGE-INVALID", f"cannot parse message header {path}: {exc}")
        return None, payload
    if not isinstance(header, Mapping):
        _block(risks, "TRACE-MESSAGE-INVALID", f"message header is not an object: {path}")
        return None, payload
    return header, payload


def _validate_messages(
    messages: list[Any],
    events: list[Mapping[str, Any]],
    envelope: Mapping[str, Any],
    actors: Mapping[str, Mapping[str, Any]],
    root: Path,
    risks: list[ContractRisk],
) -> None:
    if envelope.get("handoff_level") == "H0" and messages:
        _block(risks, "TRACE-H0-MESSAGE", "H0 Attempt cannot contain cross-Agent messages")
    sequences = [message.get("sequence") for message in messages if isinstance(message, Mapping)]
    if sequences != list(range(1, len(messages) + 1)):
        _block(risks, "TRACE-MESSAGE-SEQUENCE-GAP", f"message sequence is not contiguous: {sequences}")
    event_ids = {event.get("event_id"): event for event in events}
    seen: set[str] = set()
    for message in messages:
        if not isinstance(message, Mapping):
            continue
        message_id = str(message.get("message_id"))
        if message_id in seen:
            _block(risks, "TRACE-MESSAGE-DUPLICATE", f"message_id is repeated: {message_id}")
        seen.add(message_id)
        actor_ids = [message.get("sender_actor_id"), *message.get("receiver_actor_ids", [])]
        if any(actor_id not in actors for actor_id in actor_ids):
            _block(risks, "TRACE-ACTOR-UNOWNED", f"{message_id}: sender or receiver actor is unknown")
        sender = actors.get(str(message.get("sender_actor_id")))
        if sender is not None and message.get("accountable_owner") != sender.get("accountable_owner"):
            _block(risks, "TRACE-ACTOR-UNOWNED", f"{message_id}: accountable owner differs from sender owner")
        content_path = _check_ref(root, message.get("content_ref"), f"message {message_id}", risks)
        for attachment in message.get("attachment_refs", []):
            _check_ref(root, attachment, f"message {message_id} attachment", risks)
        sent = event_ids.get(message.get("sent_event_id"))
        if (
            sent is None
            or sent.get("event_type") != "message-sent"
            or sent.get("message_id") != message_id
            or sent.get("actor_id") != message.get("sender_actor_id")
        ):
            _block(risks, "TRACE-MESSAGE-MISSING", f"{message_id}: sent event is missing or mismatched")
        received_ids = message.get("received_event_ids", [])
        if len(received_ids) != len(message.get("receiver_actor_ids", [])):
            _block(risks, "TRACE-MESSAGE-MISSING", f"{message_id}: receive acknowledgements do not cover receivers")
        for event_id in received_ids:
            received = event_ids.get(event_id)
            if (
                received is None
                or received.get("event_type") != "message-received"
                or received.get("message_id") != message_id
                or received.get("actor_id") not in message.get("receiver_actor_ids", [])
                or received.get("related_event_id") != message.get("sent_event_id")
            ):
                _block(risks, "TRACE-MESSAGE-MISSING", f"{message_id}: received event is missing or mismatched")
        if content_path is None:
            continue
        header, payload = _parse_message(content_path, risks)
        if header is None:
            continue
        expected_fields = {
            "message_id": message_id,
            "task_id": envelope.get("task_id"),
            "attempt_id": envelope.get("attempt_id"),
            "sequence": message.get("sequence"),
            "kind": message.get("kind"),
            "sender_actor_id": message.get("sender_actor_id"),
            "receiver_actor_ids": message.get("receiver_actor_ids"),
            "accountable_owner": message.get("accountable_owner"),
            "created_at": message.get("created_at"),
            "capture_status": message.get("capture_status"),
            "attachment_refs": message.get("attachment_refs"),
        }
        for field, expected in expected_fields.items():
            if header.get(field) != expected:
                _block(risks, "TRACE-MESSAGE-INDEX-MISMATCH", f"{message_id}: header {field} differs from Index")
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if str(header.get("content_sha256", "")).removeprefix("sha256:").lower() != payload_hash:
            _block(risks, "TRACE-HASH-MISMATCH", f"{message_id}: visible payload hash mismatch")

    indexed_message_ids = {str(message.get("message_id")) for message in messages if isinstance(message, Mapping)}
    for event in events:
        if event.get("event_type") in {"message-sent", "message-received"}:
            if str(event.get("message_id")) not in indexed_message_ids:
                _block(risks, "TRACE-MESSAGE-MISSING", f"{event.get('event_id')}: message event is absent from Index")


def _validate_capture(
    index: Mapping[str, Any],
    events: list[Mapping[str, Any]],
    messages: list[Any],
    envelope: Mapping[str, Any],
    risks: list[ContractRisk],
) -> None:
    by_id = {event.get("event_id"): event for event in events}
    declared_gap_ids = set(index.get("capture_gap_event_ids", []))
    actual_gap_ids = {event.get("event_id") for event in events if event.get("event_type") == "capture-gap"}
    if declared_gap_ids != actual_gap_ids:
        _block(risks, "TRACE-CAPTURE-GAP-INDEX", "Index capture gaps differ from the event ledger")
    if actual_gap_ids and envelope.get("capture_status") != "gap-declared":
        _block(risks, "TRACE-CAPTURE-STATUS-MISMATCH", "Envelope reports complete despite capture-gap events")
    if not actual_gap_ids and envelope.get("capture_status") == "gap-declared":
        _block(risks, "TRACE-CAPTURE-STATUS-MISMATCH", "Envelope declares a gap but no capture-gap event exists")
    for event_id in sorted(str(item) for item in actual_gap_ids):
        _warn(risks, "TRACE-CAPTURE-GAP", f"declared capture gap: {event_id}")
        capture = by_id[event_id].get("capture", {})
        if not str(capture.get("reason", "")).strip() or not capture.get("affected_ids"):
            _block(risks, "TRACE-OMISSION-UNDECLARED", f"{event_id}: capture gap lacks reason or affected ids")

    declaration_by_message: dict[str, set[str]] = {}
    for event in events:
        if event.get("event_type") not in {"redaction", "omission", "capture-gap"}:
            continue
        capture = event.get("capture", {})
        for affected in capture.get("affected_ids", []):
            declaration_by_message.setdefault(str(affected), set()).add(str(event.get("event_type")))
        if event.get("event_type") in {"redaction", "omission"}:
            _warn(risks, "TRACE-REDACTION-DECLARED", f"declared {event.get('event_type')}: {event.get('event_id')}")

    for event in events:
        capture = event.get("capture")
        if not isinstance(capture, Mapping) or capture.get("status") == "complete":
            continue
        event_id = str(event.get("event_id"))
        if event.get("event_type") in {"capture-gap", "redaction", "omission"}:
            continue
        required = {
            "gap": "capture-gap",
            "redacted": "redaction",
            "omitted": "omission",
        }.get(str(capture.get("status")))
        if required and required not in declaration_by_message.get(event_id, set()):
            _block(risks, "TRACE-OMISSION-UNDECLARED", f"{event_id}: non-complete event capture lacks a declaration")

    for message in messages:
        if not isinstance(message, Mapping):
            continue
        message_id = str(message.get("message_id"))
        status = message.get("capture_status")
        declarations = declaration_by_message.get(message_id, set())
        if status == "delayed":
            _warn(risks, "TRACE-CAPTURE-DELAYED", f"message capture was delayed: {message_id}")
        elif status == "redacted" and "redaction" not in declarations:
            _block(risks, "TRACE-REDACTION-UNDECLARED", f"redacted message lacks a redaction event: {message_id}")
        elif status == "omitted" and "omission" not in declarations:
            _block(risks, "TRACE-OMISSION-UNDECLARED", f"omitted message lacks an omission event: {message_id}")
        elif status == "gap" and "capture-gap" not in declarations:
            _block(risks, "TRACE-OMISSION-UNDECLARED", f"gapped message lacks a capture-gap event: {message_id}")


def _block(risks: list[ContractRisk], code: str, message: str) -> None:
    risks.append(ContractRisk(code, RiskLevel.BLOCK, message))


def _warn(risks: list[ContractRisk], code: str, message: str) -> None:
    risks.append(ContractRisk(code, RiskLevel.WARNING, message))
