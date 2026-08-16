"""Deterministic validation for one file-first Agent Trace archive.

The trace bundle contains formats that the generic document loader deliberately
does not consume: Markdown messages with YAML front matter and a JSONL event
ledger.  This module validates those formats and their relationships without
loading any hidden runtime transcript or making a scientific-correctness claim.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.io import load_document
from research_workbench.validation.documents import Severity, ValidationIssue
from research_workbench.validation.schemas import SchemaCatalog


_MESSAGE_FILE_RE = re.compile(r"^(?P<sequence>[0-9]{4,})-.+\.md$")
_REDACTION_TOKEN_RE = re.compile(r"\[\[REDACTED:([A-Za-z0-9][A-Za-z0-9._-]*)\]\]")
_OWNER_PLACEHOLDERS = {"unknown", "unassigned", "none", "n/a"}
_TERMINAL_ATTEMPT_STATUSES = {
    "completed",
    "stage-completed",
    "safe-paused",
    "waiting",
    "incomplete",
    "failed",
    "blocked",
    "cancelled",
}
_IMMUTABLE_ARCHIVE_NAMES = {"TASK.yaml", "ACTORS.yaml"}
_IMMUTABLE_ARCHIVE_DIRECTORIES = {
    "messages",
    "tool-events",
    "handoffs",
    "decisions",
    "checks",
    "outputs",
    "snapshots",
}
_INDEX_MESSAGE_FIELDS = (
    "message_id",
    "sequence",
    "kind",
    "sender_actor_id",
    "receiver_actor_ids",
    "created_at",
    "capture_status",
    "attachment_refs",
    "in_reply_to",
    "capture_gap_event_id",
)


class _FrontMatterLoader(yaml.SafeLoader):
    """SafeLoader variant that preserves RFC 3339 timestamps as strings."""


_FrontMatterLoader.yaml_implicit_resolvers = {
    key: [
        resolver
        for resolver in value
        if resolver[0] != "tag:yaml.org,2002:timestamp"
    ]
    for key, value in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def _add_issue(
    issues: list[ValidationIssue],
    path: Path,
    code: str,
    message: str,
    severity: Severity = Severity.ERROR,
) -> None:
    issues.append(ValidationIssue(path, code, message, severity))


def _schema_issues(
    catalog: SchemaCatalog,
    kind: str,
    document: Any,
    path: Path,
    issues: list[ValidationIssue],
    *,
    locator: str | None = None,
) -> bool:
    errors = catalog.validate(kind, document)
    for error in errors:
        prefix = f"{locator}: " if locator else ""
        _add_issue(
            issues,
            path,
            "SCHEMA-INVALID",
            f"{prefix}{error.pointer}: {error.message}",
        )
    return not errors


def _normalized_hash(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.removeprefix("sha256:").lower()


def _normalized_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value.replace("\\", "/").rstrip("/")


def _resolve_project_path(root: Path, relative: Any) -> Path | None:
    normalized = _normalized_path(relative)
    if normalized is None:
        return None
    return resolve_within_root(root, normalized)


def _check_file_ref(
    root: Path,
    reference: Any,
    issue_path: Path,
    issues: list[ValidationIssue],
    *,
    label: str,
    missing_code: str = "TRACE-HASH-MISMATCH",
    mismatch_code: str = "TRACE-HASH-MISMATCH",
) -> Path | None:
    if not isinstance(reference, Mapping):
        _add_issue(issues, issue_path, missing_code, f"{label} is not a file reference")
        return None
    relative = reference.get("path")
    resolved = _resolve_project_path(root, relative)
    if resolved is None:
        _add_issue(
            issues,
            issue_path,
            "TRACE-REF-OUTSIDE-ROOT",
            f"{label} escapes the project root: {relative}",
        )
        return None
    if not resolved.is_file():
        _add_issue(issues, issue_path, missing_code, f"{label} does not exist: {relative}")
        return resolved
    expected = _normalized_hash(reference.get("sha256"))
    actual = hash_file(resolved)
    if expected != actual:
        _add_issue(
            issues,
            issue_path,
            mismatch_code,
            f"{label} hash mismatch: expected={expected} actual={actual} path={relative}",
        )
    return resolved


def _load_mapping(path: Path, issues: list[ValidationIssue], *, label: str) -> Mapping[str, Any] | None:
    try:
        document = load_document(path)
    except Exception as exc:
        _add_issue(issues, path, "PARSE-ERROR", f"cannot parse {label}: {exc}")
        return None
    if not isinstance(document, Mapping):
        _add_issue(issues, path, "DOCUMENT-INVALID", f"{label} must be an object")
        return None
    return document


def _parse_message(
    path: Path,
    issues: list[ValidationIssue],
) -> tuple[Mapping[str, Any], bytes, str] | None:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _add_issue(issues, path, "TRACE-MESSAGE-MISSING", str(exc))
        return None
    if raw.startswith(b"\xef\xbb\xbf"):
        _add_issue(issues, path, "PARSE-ERROR", "message must be UTF-8 without a BOM")
        return None
    lines = raw.splitlines(keepends=True)
    if not lines or lines[0].rstrip(b"\r\n") != b"---":
        _add_issue(issues, path, "PARSE-ERROR", "message lacks opening YAML front matter delimiter")
        return None
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.rstrip(b"\r\n") == b"---"),
        None,
    )
    if closing_index is None:
        _add_issue(issues, path, "PARSE-ERROR", "message lacks closing YAML front matter delimiter")
        return None
    try:
        header_text = b"".join(lines[1:closing_index]).decode("utf-8")
        payload = b"".join(lines[closing_index + 1 :])
        payload_text = payload.decode("utf-8")
        header = yaml.load(header_text, Loader=_FrontMatterLoader)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        _add_issue(issues, path, "PARSE-ERROR", f"invalid message envelope or payload: {exc}")
        return None
    if not isinstance(header, Mapping):
        _add_issue(issues, path, "DOCUMENT-INVALID", "message envelope must be an object")
        return None
    return header, payload, payload_text


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _scope_matches(scope: Any, path: Any) -> bool:
    normalized_scope = _normalized_path(scope)
    normalized_path = _normalized_path(path)
    if normalized_scope is None or normalized_path is None:
        return False
    if normalized_scope.endswith("/**"):
        anchor = normalized_scope[:-3].rstrip("/")
        return normalized_path == anchor or normalized_path.startswith(anchor + "/")
    return normalized_path == normalized_scope


def _is_beneath(path: Any, directory: Any) -> bool:
    normalized_path = _normalized_path(path)
    normalized_directory = _normalized_path(directory)
    if normalized_path is None or normalized_directory is None:
        return False
    return normalized_path == normalized_directory or normalized_path.startswith(normalized_directory + "/")


def _message_id_for_sequence(sequence: int) -> str:
    return f"MSG-{sequence:04d}"


def _event_id_for_sequence(sequence: int) -> str:
    return f"EVT-{sequence:04d}"


def _iter_string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_string_values(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_string_values(nested)


def _validate_redactions(
    value: Any,
    redactions: Any,
    path: Path,
    issues: list[ValidationIssue],
) -> set[str]:
    token_ids: set[str] = set()
    for text in _iter_string_values(value):
        token_ids.update(_REDACTION_TOKEN_RE.findall(text))
    declared: set[str] = set()
    archive_copy: set[str] = set()
    if isinstance(redactions, list):
        for item in redactions:
            if not isinstance(item, Mapping) or not isinstance(item.get("redaction_id"), str):
                continue
            redaction_id = str(item["redaction_id"])
            if redaction_id in declared:
                _add_issue(
                    issues,
                    path,
                    "TRACE-REDACTION-UNDECLARED",
                    f"duplicate redaction declaration: {redaction_id}",
                )
            declared.add(redaction_id)
            if item.get("applied_to") == "archive-copy":
                archive_copy.add(redaction_id)
    undeclared = sorted(token_ids - declared)
    unused = sorted(declared - token_ids)
    if undeclared:
        _add_issue(
            issues,
            path,
            "TRACE-REDACTION-UNDECLARED",
            "payload contains undeclared redaction markers: " + ", ".join(undeclared),
        )
    if unused:
        _add_issue(
            issues,
            path,
            "TRACE-REDACTION-UNDECLARED",
            "redaction declarations have no payload marker: " + ", ".join(unused),
        )
    return archive_copy


def _missing_sequences(sequences: Iterable[int]) -> set[int]:
    values = set(sequences)
    if not values:
        return set()
    return set(range(1, max(values) + 1)) - values


def _gap_covers_sequence(gap: Mapping[str, Any], stream: str, sequence: int) -> bool:
    return (
        gap.get("affected_stream") == stream
        and isinstance(gap.get("sequence_start"), int)
        and isinstance(gap.get("sequence_end"), int)
        and int(gap["sequence_start"]) <= sequence <= int(gap["sequence_end"])
    )


def _basis_is_prior_scope_decision(
    basis: str,
    occurred_at: Any,
    messages: Mapping[str, Mapping[str, Any]],
) -> bool:
    if basis == "TASK":
        return True
    message = messages.get(basis)
    if message is None or message.get("kind") != "scope-decision":
        return False
    message_time = _parse_datetime(message.get("created_at"))
    event_time = _parse_datetime(occurred_at)
    return message_time is not None and event_time is not None and message_time <= event_time


def _is_immutable_archive_path(path: str, archive_root: str) -> bool:
    if not _is_beneath(path, archive_root):
        return False
    relative = path[len(archive_root) :].lstrip("/")
    if relative in _IMMUTABLE_ARCHIVE_NAMES:
        return True
    first = relative.split("/", 1)[0]
    return first in _IMMUTABLE_ARCHIVE_DIRECTORIES


def _load_events(
    index: Mapping[str, Any],
    index_path: Path,
    root: Path,
    catalog: SchemaCatalog,
    actors: Mapping[str, Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> tuple[list[Mapping[str, Any]], Mapping[str, Mapping[str, Any]]]:
    ledger_ref = index.get("event_ledger")
    ledger_path = _check_file_ref(
        root,
        ledger_ref,
        index_path,
        issues,
        label="event ledger",
        missing_code="TRACE-EVENT-MISSING",
    )
    if ledger_path is None or not ledger_path.is_file():
        return [], {}
    try:
        raw = ledger_path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _add_issue(issues, ledger_path, "PARSE-ERROR", f"cannot read event ledger: {exc}")
        return [], {}

    physical_lines = text.splitlines()
    records: list[Mapping[str, Any]] = []
    events_by_id: dict[str, Mapping[str, Any]] = {}
    sequence_owner: dict[int, str] = {}
    for line_number, line in enumerate(physical_lines, start=1):
        if not line.strip():
            _add_issue(
                issues,
                ledger_path,
                "TRACE-EVENT-MISSING",
                f"events.jsonl:{line_number}: blank records are forbidden",
            )
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as exc:
            _add_issue(
                issues,
                ledger_path,
                "PARSE-ERROR",
                f"events.jsonl:{line_number}: {exc}",
            )
            continue
        if not isinstance(document, Mapping):
            _add_issue(
                issues,
                ledger_path,
                "DOCUMENT-INVALID",
                f"events.jsonl:{line_number}: event must be an object",
            )
            continue
        valid = _schema_issues(
            catalog,
            "agent_trace_event",
            document,
            ledger_path,
            issues,
            locator=f"events.jsonl:{line_number}",
        )
        records.append(document)
        if not valid:
            continue
        event_id = str(document["event_id"])
        sequence = int(document["sequence"])
        if event_id in events_by_id:
            _add_issue(issues, ledger_path, "TRACE-SEQUENCE-GAP", f"duplicate event_id: {event_id}")
        else:
            events_by_id[event_id] = document
        if sequence in sequence_owner:
            _add_issue(
                issues,
                ledger_path,
                "TRACE-SEQUENCE-GAP",
                f"duplicate event sequence {sequence}: {sequence_owner[sequence]}, {event_id}",
            )
        else:
            sequence_owner[sequence] = event_id
        if event_id != _event_id_for_sequence(sequence):
            _add_issue(
                issues,
                ledger_path,
                "TRACE-SEQUENCE-GAP",
                f"event ID {event_id} does not match sequence {sequence}",
            )
        for field in ("task_id", "task_revision", "attempt_id"):
            if document.get(field) != index.get(field):
                _add_issue(
                    issues,
                    ledger_path,
                    "TRACE-EVENT-MISSING",
                    f"{event_id} {field} differs from INDEX.yaml",
                )
        if document.get("actor_id") not in actors:
            _add_issue(
                issues,
                ledger_path,
                "TRACE-ACTOR-UNOWNED",
                f"{event_id} references unknown actor {document.get('actor_id')!r}",
            )
    expected_count = ledger_ref.get("event_count") if isinstance(ledger_ref, Mapping) else None
    if expected_count != len([line for line in physical_lines if line.strip()]):
        _add_issue(
            issues,
            ledger_path,
            "TRACE-EVENT-MISSING",
            f"event_count={expected_count!r} but ledger contains "
            f"{len([line for line in physical_lines if line.strip()])} records",
        )
    return records, events_by_id


def _validate_capture_gaps(
    index: Mapping[str, Any],
    index_path: Path,
    events_by_id: Mapping[str, Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> tuple[list[Mapping[str, Any]], bool]:
    indexed_gaps: dict[str, Mapping[str, Any]] = {}
    for gap in index.get("capture_gaps", []):
        if not isinstance(gap, Mapping) or not isinstance(gap.get("event_id"), str):
            continue
        event_id = str(gap["event_id"])
        if event_id in indexed_gaps:
            _add_issue(issues, index_path, "TRACE-SEQUENCE-GAP", f"duplicate capture gap: {event_id}")
        indexed_gaps[event_id] = gap

    event_gaps: dict[str, Mapping[str, Any]] = {
        event_id: event
        for event_id, event in events_by_id.items()
        if event.get("event_type") == "capture-gap"
    }
    for event_id, gap in indexed_gaps.items():
        event = event_gaps.get(event_id)
        if event is None:
            _add_issue(
                issues,
                index_path,
                "TRACE-EVENT-MISSING",
                f"indexed capture gap has no ledger event: {event_id}",
            )
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        for field in ("affected_stream", "sequence_start", "sequence_end", "affected_ids"):
            if field in gap and gap.get(field) != payload.get(field):
                _add_issue(
                    issues,
                    index_path,
                    "TRACE-EVENT-MISSING",
                    f"capture gap {event_id} differs between INDEX.yaml and events.jsonl at {field}",
                )
    for event_id in sorted(set(event_gaps) - set(indexed_gaps)):
        _add_issue(
            issues,
            index_path,
            "TRACE-EVENT-MISSING",
            f"capture-gap ledger event is absent from INDEX.yaml: {event_id}",
        )

    payloads = [
        event["payload"]
        for event in event_gaps.values()
        if isinstance(event.get("payload"), Mapping)
    ]
    return payloads, bool(indexed_gaps or event_gaps)


def _validate_messages(
    index: Mapping[str, Any],
    index_path: Path,
    root: Path,
    archive_root: str,
    catalog: SchemaCatalog,
    actors: Mapping[str, Mapping[str, Any]],
    events_by_id: Mapping[str, Mapping[str, Any]],
    gap_payloads: list[Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> tuple[dict[str, Mapping[str, Any]], bool, bool, set[str]]:
    messages: dict[str, Mapping[str, Any]] = {}
    sequences: dict[int, str] = {}
    indexed_paths: set[str] = set()
    delayed = False
    gapped = False
    material_paths: set[str] = set()
    message_capture_ids = {
        event.get("payload", {}).get("message_id")
        for event in events_by_id.values()
        if event.get("event_type") == "message-capture" and isinstance(event.get("payload"), Mapping)
    }

    for entry in index.get("messages", []):
        if not isinstance(entry, Mapping):
            continue
        message_id = entry.get("message_id")
        sequence = entry.get("sequence")
        relative = _normalized_path(entry.get("path"))
        if not isinstance(message_id, str) or not isinstance(sequence, int) or relative is None:
            continue
        if message_id in messages:
            _add_issue(issues, index_path, "TRACE-SEQUENCE-GAP", f"duplicate message_id: {message_id}")
        else:
            messages[message_id] = entry
        if sequence in sequences:
            _add_issue(
                issues,
                index_path,
                "TRACE-SEQUENCE-GAP",
                f"duplicate message sequence {sequence}: {sequences[sequence]}, {message_id}",
            )
        else:
            sequences[sequence] = message_id
        if message_id != _message_id_for_sequence(sequence):
            _add_issue(
                issues,
                index_path,
                "TRACE-SEQUENCE-GAP",
                f"message ID {message_id} does not match sequence {sequence}",
            )
        if not _is_beneath(relative, f"{archive_root}/messages"):
            _add_issue(
                issues,
                index_path,
                "TRACE-REF-OUTSIDE-ROOT",
                f"message is outside the archive messages directory: {relative}",
            )
        indexed_paths.add(relative)
        material_paths.add(relative)
        message_path = _check_file_ref(
            root,
            {"path": relative, "sha256": entry.get("sha256")},
            index_path,
            issues,
            label=f"message {message_id}",
            missing_code="TRACE-MESSAGE-MISSING",
        )
        if message_path is None or not message_path.is_file():
            continue
        match = _MESSAGE_FILE_RE.fullmatch(message_path.name)
        if match is None or int(match.group("sequence")) != sequence:
            _add_issue(
                issues,
                message_path,
                "TRACE-SEQUENCE-GAP",
                f"message filename prefix does not match sequence {sequence}",
            )
        parsed = _parse_message(message_path, issues)
        if parsed is None:
            continue
        header, payload, payload_text = parsed
        if not _schema_issues(catalog, "agent_trace_envelope", header, message_path, issues):
            continue
        actual_content_hash = hashlib.sha256(payload).hexdigest()
        for source, expected in (
            ("envelope", header.get("content_sha256")),
            ("INDEX.yaml", entry.get("content_sha256")),
        ):
            if _normalized_hash(expected) != actual_content_hash:
                _add_issue(
                    issues,
                    message_path,
                    "TRACE-HASH-MISMATCH",
                    f"{source} content_sha256 does not match the raw message payload",
                )
        for field in _INDEX_MESSAGE_FIELDS:
            if header.get(field) != entry.get(field):
                _add_issue(
                    issues,
                    message_path,
                    "TRACE-HASH-MISMATCH",
                    f"message metadata differs from INDEX.yaml at {field}",
                )
        for field in ("task_id", "task_revision", "attempt_id"):
            if header.get(field) != index.get(field):
                _add_issue(
                    issues,
                    message_path,
                    "TRACE-MESSAGE-MISSING",
                    f"message {field} differs from INDEX.yaml",
                )
        sender = header.get("sender_actor_id")
        sender_record = actors.get(sender) if isinstance(sender, str) else None
        if sender_record is None:
            _add_issue(
                issues,
                message_path,
                "TRACE-ACTOR-UNOWNED",
                f"unknown sender actor: {sender!r}",
            )
        elif header.get("accountable_owner") != sender_record.get("accountable_owner"):
            _add_issue(
                issues,
                message_path,
                "TRACE-ACTOR-UNOWNED",
                f"message owner does not match actor registry for {sender}",
            )
        for receiver in header.get("receiver_actor_ids", []):
            if receiver not in actors:
                _add_issue(
                    issues,
                    message_path,
                    "TRACE-ACTOR-UNOWNED",
                    f"unknown receiver actor: {receiver!r}",
                )
        for attachment in header.get("attachment_refs", []):
            _check_file_ref(
                root,
                attachment,
                message_path,
                issues,
                label=f"message {message_id} attachment",
            )
        archive_copy = _validate_redactions(payload_text, header.get("redactions"), message_path, issues)
        capture_gap_event_id = header.get("capture_gap_event_id")
        if archive_copy and capture_gap_event_id not in events_by_id:
            _add_issue(
                issues,
                message_path,
                "TRACE-REDACTION-UNDECLARED",
                "archive-copy redaction lacks a capture-gap event",
            )
        capture_status = header.get("capture_status")
        if capture_status == "delayed":
            delayed = True
        if capture_status in {"partial", "unavailable"}:
            gapped = True
            gap_event = events_by_id.get(capture_gap_event_id)
            if gap_event is None or gap_event.get("event_type") != "capture-gap":
                _add_issue(
                    issues,
                    message_path,
                    "TRACE-MESSAGE-MISSING",
                    f"{capture_status} message lacks its indexed capture-gap event",
                )
        if message_id not in message_capture_ids:
            _add_issue(
                issues,
                message_path,
                "TRACE-EVENT-MISSING",
                f"message has no message-capture ledger event: {message_id}",
            )

    missing = _missing_sequences(sequences)
    uncovered = sorted(
        sequence
        for sequence in missing
        if not any(_gap_covers_sequence(gap, "messages", sequence) for gap in gap_payloads)
    )
    if uncovered:
        _add_issue(
            issues,
            index_path,
            "TRACE-SEQUENCE-GAP",
            "undeclared message sequence gaps: " + ", ".join(map(str, uncovered)),
        )
    if missing and not uncovered:
        gapped = True

    for message_id, entry in messages.items():
        reply = entry.get("in_reply_to")
        if not isinstance(reply, str):
            continue
        target = messages.get(reply)
        if target is None or not isinstance(target.get("sequence"), int) or target["sequence"] >= entry["sequence"]:
            _add_issue(
                issues,
                index_path,
                "TRACE-MESSAGE-MISSING",
                f"{message_id} has an unknown or non-prior in_reply_to: {reply}",
            )

    message_directory = _resolve_project_path(root, f"{archive_root}/messages")
    if message_directory is not None and message_directory.is_dir():
        for candidate in message_directory.glob("*.md"):
            relative = candidate.resolve().relative_to(root).as_posix()
            if relative not in indexed_paths:
                _add_issue(
                    issues,
                    candidate,
                    "TRACE-MESSAGE-MISSING",
                    "message file is not listed in INDEX.yaml",
                )
    return messages, delayed, gapped, material_paths


def _validate_authorized_events(
    index: Mapping[str, Any],
    index_path: Path,
    root: Path,
    archive_root: str,
    records: list[Mapping[str, Any]],
    messages: Mapping[str, Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> tuple[set[str], dict[str, tuple[str, int, bool]]]:
    material_paths: set[str] = set()
    revision_state: dict[str, tuple[str, int, bool]] = {}
    read_allowlist = [item for item in index.get("read_allowlist", []) if isinstance(item, Mapping)]
    tool_allowlist = [item for item in index.get("tool_allowlist", []) if isinstance(item, Mapping)]
    write_scope = list(index.get("write_scope", []))
    indexed_tool_refs = {
        (_normalized_path(item.get("path")), _normalized_hash(item.get("sha256")))
        for item in index.get("tool_event_refs", [])
        if isinstance(item, Mapping)
    }

    for event in sorted(records, key=lambda item: item.get("sequence", 0)):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        event_id = event.get("event_id")
        if event_type == "content-read":
            path = payload.get("path")
            if _resolve_project_path(root, path) is None:
                _add_issue(
                    issues,
                    index_path,
                    "TRACE-REF-OUTSIDE-ROOT",
                    f"{event_id} read path escapes project root: {path}",
                )
            if payload.get("access") != "content":
                continue
            basis = payload.get("allowlist_basis")
            allowed = any(
                item.get("authorized_by") == basis and _scope_matches(item.get("path"), path)
                for item in read_allowlist
            )
            if not allowed or not isinstance(basis, str) or not _basis_is_prior_scope_decision(
                basis, event.get("occurred_at"), messages
            ):
                _add_issue(
                    issues,
                    index_path,
                    "TRACE-READ-OUTSIDE-SCOPE",
                    f"{event_id} content read is outside its authorized scope: {path}",
                )
        elif event_type == "tool-call":
            tool_name = payload.get("tool_name")
            basis = payload.get("allowlist_basis")
            allowed = any(
                item.get("tool_name") == tool_name and item.get("authorized_by") == basis
                for item in tool_allowlist
            )
            if not allowed or not isinstance(basis, str) or not _basis_is_prior_scope_decision(
                basis, event.get("occurred_at"), messages
            ):
                _add_issue(
                    issues,
                    index_path,
                    "TRACE-TOOL-OUTSIDE-SCOPE",
                    f"{event_id} tool is outside its authorized scope: {tool_name}",
                )
            archive_copy = _validate_redactions(
                payload.get("arguments"), payload.get("redactions"), index_path, issues
            )
            gap_event_id = payload.get("capture_gap_event_id")
            if archive_copy and not isinstance(gap_event_id, str):
                _add_issue(
                    issues,
                    index_path,
                    "TRACE-REDACTION-UNDECLARED",
                    f"{event_id} archive-copy argument redaction lacks capture_gap_event_id",
                )
            if payload.get("result_entered_context"):
                result_ref = payload.get("result_ref")
                result_origin = payload.get("result_origin")
                if not isinstance(result_ref, Mapping) or result_origin not in {"stable-source", "transient"}:
                    _add_issue(
                        issues,
                        index_path,
                        "TRACE-TRANSIENT-RESULT-MISSING",
                        f"{event_id} result entered context without an origin and hash-bound result ref",
                    )
                else:
                    resolved = _check_file_ref(
                        root,
                        result_ref,
                        index_path,
                        issues,
                        label=f"{event_id} tool result",
                        missing_code="TRACE-TRANSIENT-RESULT-MISSING",
                        mismatch_code="TRACE-TRANSIENT-RESULT-MISSING",
                    )
                    result_key = (
                        _normalized_path(result_ref.get("path")),
                        _normalized_hash(result_ref.get("sha256")),
                    )
                    if result_origin == "transient":
                        if not _is_beneath(result_ref.get("path"), f"{archive_root}/tool-events"):
                            _add_issue(
                                issues,
                                index_path,
                                "TRACE-TRANSIENT-RESULT-MISSING",
                                f"{event_id} transient result is not stored under tool-events/",
                            )
                        if result_key not in indexed_tool_refs:
                            _add_issue(
                                issues,
                                index_path,
                                "TRACE-TRANSIENT-RESULT-MISSING",
                                f"{event_id} transient result is absent from INDEX.tool_event_refs",
                            )
                        if resolved is not None:
                            material_paths.add(str(result_ref["path"]).replace("\\", "/"))
            elif "result_ref" in payload or "result_origin" in payload:
                _add_issue(
                    issues,
                    index_path,
                    "TRACE-EVENT-MISSING",
                    f"{event_id} records a result ref while result_entered_context is false",
                )
        elif event_type == "file-revision":
            path = _normalized_path(payload.get("path"))
            if path is None:
                continue
            material_paths.add(path)
            if _resolve_project_path(root, path) is None:
                _add_issue(
                    issues,
                    index_path,
                    "TRACE-REF-OUTSIDE-ROOT",
                    f"{event_id} file revision escapes project root: {path}",
                )
                continue
            if not any(_scope_matches(scope, path) for scope in write_scope):
                _add_issue(
                    issues,
                    index_path,
                    "TRACE-WRITE-OUTSIDE-SCOPE",
                    f"{event_id} file revision is outside write_scope: {path}",
                )
            action = payload.get("action")
            current = revision_state.get(path)
            if action == "created":
                if current is not None:
                    _add_issue(
                        issues,
                        index_path,
                        "TRACE-PROCESS-ARTIFACT-OVERWRITTEN",
                        f"{event_id} creates an already-observed process path: {path}",
                    )
                revision_state[path] = (
                    _normalized_hash(payload.get("new_sha256")) or "",
                    int(payload.get("new_revision", 0)),
                    False,
                )
            elif action == "modified":
                old_hash = _normalized_hash(payload.get("old_sha256")) or ""
                old_revision = int(payload.get("old_revision", 0))
                new_revision = int(payload.get("new_revision", 0))
                if _is_immutable_archive_path(path, archive_root):
                    _add_issue(
                        issues,
                        index_path,
                        "TRACE-PROCESS-ARTIFACT-OVERWRITTEN",
                        f"{event_id} modifies immutable process material: {path}",
                    )
                if current is None or current[2] or current[:2] != (old_hash, old_revision):
                    _add_issue(
                        issues,
                        index_path,
                        "TRACE-EVENT-MISSING",
                        f"{event_id} old file revision does not match prior ledger state: {path}",
                    )
                if new_revision <= old_revision:
                    _add_issue(
                        issues,
                        index_path,
                        "TRACE-PROCESS-ARTIFACT-OVERWRITTEN",
                        f"{event_id} file revision does not increase: {path}",
                    )
                revision_state[path] = (
                    _normalized_hash(payload.get("new_sha256")) or "",
                    new_revision,
                    False,
                )
            elif action == "deleted":
                old_hash = _normalized_hash(payload.get("old_sha256")) or ""
                old_revision = int(payload.get("old_revision", 0))
                if current is None or current[2] or current[:2] != (old_hash, old_revision):
                    _add_issue(
                        issues,
                        index_path,
                        "TRACE-EVENT-MISSING",
                        f"{event_id} deletion does not match prior ledger state: {path}",
                    )
                revision_state[path] = (old_hash, old_revision, True)

    for path, (expected_hash, _revision, deleted) in revision_state.items():
        resolved = _resolve_project_path(root, path)
        if resolved is None:
            continue
        if deleted:
            if resolved.exists():
                _add_issue(
                    issues,
                    index_path,
                    "TRACE-HASH-MISMATCH",
                    f"ledger marks deleted path as present: {path}",
                )
        elif not resolved.is_file():
            _add_issue(
                issues,
                index_path,
                "TRACE-HASH-MISMATCH",
                f"ledger final file revision is missing: {path}",
            )
        elif hash_file(resolved) != expected_hash:
            _add_issue(
                issues,
                index_path,
                "TRACE-HASH-MISMATCH",
                f"ledger final file hash differs from live bytes: {path}",
            )
    return material_paths, revision_state


def _validate_indexed_refs(
    index: Mapping[str, Any],
    index_path: Path,
    root: Path,
    archive_root: str,
    issues: list[ValidationIssue],
) -> set[str]:
    material_paths: set[str] = set()
    for field in ("tool_event_refs", "handoff_refs", "decision_refs", "output_refs", "check_refs"):
        seen_paths: set[str] = set()
        for reference in index.get(field, []):
            if not isinstance(reference, Mapping):
                continue
            relative = _normalized_path(reference.get("path"))
            if relative is None:
                continue
            if relative in seen_paths:
                _add_issue(
                    issues,
                    index_path,
                    "TRACE-HASH-MISMATCH",
                    f"duplicate path in {field}: {relative}",
                )
            seen_paths.add(relative)
            if not _is_beneath(relative, archive_root):
                _add_issue(
                    issues,
                    index_path,
                    "TRACE-REF-OUTSIDE-ROOT",
                    f"{field} entry is outside archive_root: {relative}",
                )
            _check_file_ref(root, reference, index_path, issues, label=f"{field} entry")
            material_paths.add(relative)
    return material_paths


def _validate_link_document(
    document_path: str | Path,
    *,
    kind: str,
    index: Mapping[str, Any],
    index_path: Path,
    root: Path,
    issues: list[ValidationIssue],
) -> None:
    candidate = Path(document_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        _add_issue(
            issues,
            candidate,
            "TRACE-REF-OUTSIDE-ROOT",
            f"{kind} is outside the project root",
        )
        return
    document = _load_mapping(candidate, issues, label=kind)
    if document is None:
        return
    for field in ("task_id", "task_revision"):
        if field in document and document.get(field) != index.get(field):
            _add_issue(
                issues,
                candidate,
                "TRACE-LINK-MISMATCH",
                f"{kind} {field} differs from trace index",
            )
    if kind == "Attempt":
        for field in ("attempt_id", "status"):
            expected_field = "attempt_status" if field == "status" else field
            if document.get(field) != index.get(expected_field):
                _add_issue(
                    issues,
                    candidate,
                    "TRACE-LINK-MISMATCH",
                    f"Attempt {field} differs from trace index",
                )
        references = [document.get("agent_trace_index_ref")]
    elif kind == "Execution Receipt":
        if document.get("status") != index.get("attempt_status"):
            _add_issue(
                issues,
                candidate,
                "TRACE-LINK-MISMATCH",
                "Execution Receipt status differs from trace index",
            )
        references = [document.get("agent_trace_index_ref")]
    else:
        references = list(document.get("agent_trace_index_refs", []))

    index_relative = index_path.resolve().relative_to(root).as_posix()
    index_digest = hash_file(index_path)
    matching = False
    for reference in references:
        if not isinstance(reference, Mapping):
            continue
        if (
            _normalized_path(reference.get("path")) == index_relative
            and _normalized_hash(reference.get("sha256")) == index_digest
        ):
            matching = True
            break
    if not matching:
        _add_issue(
            issues,
            candidate,
            "TRACE-LINK-MISMATCH",
            f"{kind} does not contain the current hash-bound Agent Trace index reference",
        )


def validate_agent_trace(
    index_path: str | Path,
    *,
    root: str | Path,
    attempt_path: str | Path | None = None,
    receipt_path: str | Path | None = None,
    state_path: str | Path | None = None,
) -> list[ValidationIssue]:
    """Validate a complete Agent Trace bundle rooted at ``INDEX.yaml``.

    Declared delayed capture and declared irrecoverable gaps are warnings.  A
    missing declaration, false completeness claim, hash drift, boundary breach,
    or inconsistent relationship is an error.
    """

    issues: list[ValidationIssue] = []
    project_root = Path(root).resolve()
    candidate = Path(index_path)
    if not candidate.is_absolute():
        direct_candidate = candidate.resolve()
        rooted_candidate = (project_root / candidate).resolve()
        try:
            direct_candidate.relative_to(project_root)
        except ValueError:
            direct_is_within_root = False
        else:
            direct_is_within_root = True
        candidate = direct_candidate if direct_is_within_root and direct_candidate.is_file() else rooted_candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError:
        _add_issue(
            issues,
            candidate,
            "TRACE-REF-OUTSIDE-ROOT",
            "Agent Trace index is outside the project root",
        )
        return issues
    index = _load_mapping(candidate, issues, label="Agent Trace index")
    if index is None:
        return issues
    catalog = SchemaCatalog()
    if not _schema_issues(catalog, "agent_trace_index", index, candidate, issues):
        return issues

    archive_root = _normalized_path(index.get("archive_root")) or ""
    actual_archive_root = candidate.parent.relative_to(project_root).as_posix()
    if archive_root != actual_archive_root:
        _add_issue(
            issues,
            candidate,
            "TRACE-REF-OUTSIDE-ROOT",
            f"archive_root={archive_root!r} does not match index directory {actual_archive_root!r}",
        )

    task_path = _check_file_ref(
        project_root, index.get("task_ref"), candidate, issues, label="frozen Task"
    )
    if task_path is not None and task_path.is_file():
        task = _load_mapping(task_path, issues, label="frozen Task")
        if task is not None:
            if task.get("task_id") != index.get("task_id") or task.get("revision", 1) != index.get("task_revision"):
                _add_issue(
                    issues,
                    task_path,
                    "TRACE-LINK-MISMATCH",
                    "frozen Task identity or revision differs from trace index",
                )

    actors_path = _check_file_ref(
        project_root,
        index.get("actors_ref"),
        candidate,
        issues,
        label="actor registry",
        missing_code="TRACE-ACTOR-UNOWNED",
    )
    actors: dict[str, Mapping[str, Any]] = {}
    if actors_path is not None and actors_path.is_file():
        actor_document = _load_mapping(actors_path, issues, label="actor registry")
        if actor_document is not None and _schema_issues(
            catalog, "agent_trace_actors", actor_document, actors_path, issues
        ):
            for field in ("task_id", "task_revision", "attempt_id"):
                if actor_document.get(field) != index.get(field):
                    _add_issue(
                        issues,
                        actors_path,
                        "TRACE-ACTOR-UNOWNED",
                        f"actor registry {field} differs from trace index",
                    )
            for actor in actor_document.get("actors", []):
                if not isinstance(actor, Mapping) or not isinstance(actor.get("actor_id"), str):
                    continue
                actor_id = str(actor["actor_id"])
                if actor_id in actors:
                    _add_issue(
                        issues,
                        actors_path,
                        "TRACE-ACTOR-UNOWNED",
                        f"duplicate actor_id: {actor_id}",
                    )
                actors[actor_id] = actor
                owner = str(actor.get("accountable_owner", "")).strip()
                if not owner or owner.casefold() in _OWNER_PLACEHOLDERS:
                    _add_issue(
                        issues,
                        actors_path,
                        "TRACE-ACTOR-UNOWNED",
                        f"actor {actor_id} lacks a named accountable owner",
                    )
                if "runtime_snapshot_ref" in actor:
                    _check_file_ref(
                        project_root,
                        actor["runtime_snapshot_ref"],
                        actors_path,
                        issues,
                        label=f"actor {actor_id} runtime snapshot",
                    )

    owner_actor = actors.get(index.get("owner_actor_id"))
    if owner_actor is None or owner_actor.get("accountable_owner") != index.get("owner"):
        _add_issue(
            issues,
            candidate,
            "TRACE-ACTOR-UNOWNED",
            "index owner_actor_id and owner do not match the actor registry",
        )

    records, events_by_id = _load_events(
        index, candidate, project_root, catalog, actors, issues
    )
    gap_payloads, has_declared_gap = _validate_capture_gaps(
        index, candidate, events_by_id, issues
    )
    event_sequences = [
        int(event["sequence"])
        for event in records
        if isinstance(event.get("sequence"), int)
    ]
    missing_event_sequences = _missing_sequences(event_sequences)
    uncovered_event_sequences = sorted(
        sequence
        for sequence in missing_event_sequences
        if not any(_gap_covers_sequence(gap, "events", sequence) for gap in gap_payloads)
    )
    if uncovered_event_sequences:
        _add_issue(
            issues,
            candidate,
            "TRACE-SEQUENCE-GAP",
            "undeclared event sequence gaps: " + ", ".join(map(str, uncovered_event_sequences)),
        )

    messages, delayed, message_gapped, message_material_paths = _validate_messages(
        index,
        candidate,
        project_root,
        archive_root,
        catalog,
        actors,
        events_by_id,
        gap_payloads,
        issues,
    )
    event_material_paths, revision_state = _validate_authorized_events(
        index, candidate, project_root, archive_root, records, messages, issues
    )
    indexed_material_paths = _validate_indexed_refs(
        index, candidate, project_root, archive_root, issues
    )
    required_creation_paths = message_material_paths | indexed_material_paths
    created_paths = {
        path
        for path, (_digest, _revision, deleted) in revision_state.items()
        if not deleted or path in required_creation_paths
    }
    for relative in sorted(required_creation_paths - created_paths):
        _add_issue(
            issues,
            candidate,
            "TRACE-EVENT-MISSING",
            f"indexed process material has no file-revision event: {relative}",
        )
    del event_material_paths  # retained in the ledger-state checks above

    gapped = has_declared_gap or message_gapped or bool(missing_event_sequences)
    derived_completeness = "gapped" if gapped else "delayed" if delayed else "complete"
    if delayed:
        _add_issue(
            issues,
            candidate,
            "TRACE-CAPTURE-DELAYED",
            "one or more messages were captured after dispatch",
            Severity.WARNING,
        )
    if gapped:
        _add_issue(
            issues,
            candidate,
            "TRACE-CAPTURE-GAP",
            "the trace declares one or more irrecoverable capture gaps",
            Severity.WARNING,
        )
    if index.get("completeness") != derived_completeness:
        code = "TRACE-SEQUENCE-GAP" if gapped else "TRACE-CAPTURE-DELAYED"
        _add_issue(
            issues,
            candidate,
            code,
            f"INDEX completeness={index.get('completeness')!r}; derived={derived_completeness!r}",
        )
    if index.get("trace_status") == "frozen" and index.get("attempt_status") not in _TERMINAL_ATTEMPT_STATUSES:
        _add_issue(
            issues,
            candidate,
            "TRACE-LINK-MISMATCH",
            "a frozen trace cannot retain a non-terminal attempt_status",
        )

    if attempt_path is not None:
        _validate_link_document(
            attempt_path,
            kind="Attempt",
            index=index,
            index_path=candidate,
            root=project_root,
            issues=issues,
        )
    if receipt_path is not None:
        _validate_link_document(
            receipt_path,
            kind="Execution Receipt",
            index=index,
            index_path=candidate,
            root=project_root,
            issues=issues,
        )
    if state_path is not None:
        _validate_link_document(
            state_path,
            kind="Main State",
            index=index,
            index_path=candidate,
            root=project_root,
            issues=issues,
        )
    return issues


__all__ = ["validate_agent_trace"]
