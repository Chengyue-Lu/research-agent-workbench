"""File-authoritative execution trace recorder and deterministic validator.

The trace is deliberately small: one attempt, one writer, append-only events,
hash-bound messages, and an atomically refreshed INDEX.yaml.  It is not a
distributed tracing backend and never treats provider credentials or hidden
reasoning as recordable evidence.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.contracts import ContractRisk, RiskLevel
from research_workbench.validation.schemas import SchemaCatalog

TRACE_TASK_FILENAME = "TASK.yaml"
TRACE_ACTORS_FILENAME = "ACTORS.yaml"
TRACE_INDEX_FILENAME = "INDEX.yaml"
TRACE_EVENTS_FILENAME = "events.jsonl"
TRACE_MESSAGES_DIRNAME = "messages"
TRACE_TOOL_EVENTS_DIRNAME = "tool-events"

_SECRET_KEY = re.compile(
    r"(?:authorization|proxy[-_]?authorization|cookie|set[-_]?cookie|api[-_]?key|"
    r"access[-_]?token|refresh[-_]?token|secret|password|credential)$",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(
    r"(?i)(?:bearer\s+[A-Za-z0-9._~+/=-]{12,}|sk-[A-Za-z0-9_-]{12,}|"
    r"AIza[0-9A-Za-z_-]{20,}|(?:api[_-]?key|token|secret)\s*[:=]\s*\S{8,})"
)
_HIDDEN_REASONING_KEY = re.compile(
    r"^(?:thinking|thinking_content|reasoning_content|chain_of_thought|cot)$",
    re.IGNORECASE,
)
_REDACTION_MARKERS = ("[REDACTED:credential]", "[OMITTED:hidden-reasoning]")
_PROTECTED_TRACE_PATHS = {
    TRACE_TASK_FILENAME,
    TRACE_ACTORS_FILENAME,
    TRACE_INDEX_FILENAME,
    TRACE_EVENTS_FILENAME,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _yaml_bytes(document: Mapping[str, Any]) -> bytes:
    return yaml.safe_dump(dict(document), sort_keys=False, allow_unicode=True).encode("utf-8")


def _create_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _replace_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _plain(asdict(value))
    if hasattr(value, "to_mapping"):
        return _plain(value.to_mapping())
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(item) for item in value]
    if hasattr(value, "value") and isinstance(getattr(value, "value"), (str, int, float, bool)):
        return value.value
    if hasattr(value, "__dict__"):
        return {str(key): _plain(item) for key, item in vars(value).items()}
    return value


def sanitize_trace_value(value: Any) -> tuple[Any, tuple[dict[str, str], ...]]:
    """Remove credentials and hidden reasoning without retaining derived hashes."""

    redactions: list[dict[str, str]] = []

    def redact(item: Any, field_path: str) -> Any:
        if isinstance(item, Mapping):
            block_kind = item.get("kind", item.get("type"))
            if isinstance(block_kind, str) and block_kind.lower() in {
                "thinking", "reasoning", "reasoning_content", "chain_of_thought"
            }:
                redactions.append(
                    {
                        "category": "hidden-reasoning",
                        "reason": "provider hidden reasoning block is not a trace artifact",
                        "field_path": field_path or "$",
                    }
                )
                discriminator = "kind" if "kind" in item else "type"
                return {discriminator: block_kind, "content": "[OMITTED:hidden-reasoning]"}
            result: dict[str, Any] = {}
            for key, child in item.items():
                name = str(key)
                child_path = f"{field_path}.{name}" if field_path else name
                if _HIDDEN_REASONING_KEY.fullmatch(name):
                    redactions.append(
                        {
                            "category": "hidden-reasoning",
                            "reason": "provider hidden reasoning is not a trace artifact",
                            "field_path": child_path,
                        }
                    )
                    result[name] = "[OMITTED:hidden-reasoning]"
                elif _SECRET_KEY.search(name):
                    redactions.append(
                        {
                            "category": "credential",
                            "reason": "credential-shaped field is forbidden in trace storage",
                            "field_path": child_path,
                        }
                    )
                    result[name] = "[REDACTED:credential]"
                else:
                    result[name] = redact(child, child_path)
            return result
        if isinstance(item, (list, tuple)):
            return [redact(child, f"{field_path}[{index}]") for index, child in enumerate(item)]
        if isinstance(item, str) and _SECRET_VALUE.search(item):
            redactions.append(
                {
                    "category": "credential",
                    "reason": "credential-shaped value is forbidden in trace storage",
                    "field_path": field_path or "$",
                }
            )
            return "[REDACTED:credential]"
        return _plain(item)

    cleaned = redact(value, "")
    numbered = tuple(
        {"redaction_id": f"RED-{index:04d}", **entry}
        for index, entry in enumerate(redactions, start=1)
    )
    return cleaned, numbered


@dataclass(frozen=True, slots=True)
class TraceValidationResult:
    attempt_dir: Path
    risks: tuple[ContractRisk, ...]

    @property
    def blocked(self) -> bool:
        return any(risk.level == RiskLevel.BLOCK for risk in self.risks)


class AgentTraceRecorder:
    """Single-attempt, single-writer recorder implementing write-before-use."""

    def __init__(
        self,
        attempt_dir: str | Path,
        *,
        task_id: str,
        task_revision: int,
        attempt_id: str,
        task_snapshot: Mapping[str, Any],
        accountable_owner: str,
        actor_id: str,
        runtime_identity: str,
        provider: str,
        read_allowlist: Sequence[str],
        write_scope: Sequence[str],
        tool_allowlist: Sequence[str],
        baseline: str = "rwb-agent-trace-v0.1",
        created_at: str | None = None,
    ) -> None:
        self.attempt_dir = Path(attempt_dir).resolve()
        self.attempt_dir.mkdir(parents=True, exist_ok=True)
        self.task_id = task_id
        self.task_revision = task_revision
        self.attempt_id = attempt_id
        self.owner = accountable_owner
        self.actor_id = actor_id
        self.provider_actor_id = f"provider-{_safe_id(provider)}"
        self._created_at = created_at or _now()
        self._event_sequence = 0
        self._message_sequence = 0
        self._messages: list[dict[str, Any]] = []
        self._tool_refs: list[dict[str, str]] = []
        self._capture_gaps: list[dict[str, str]] = []
        self._status = "planned"
        self._trace_status = "active"
        self._sealed = False
        self._redaction_count = 0

        for reserved in (
            TRACE_TASK_FILENAME,
            TRACE_ACTORS_FILENAME,
            TRACE_INDEX_FILENAME,
            TRACE_EVENTS_FILENAME,
            TRACE_MESSAGES_DIRNAME,
            TRACE_TOOL_EVENTS_DIRNAME,
        ):
            if (self.attempt_dir / reserved).exists():
                raise FileExistsError(f"trace artifact already exists: {self.attempt_dir / reserved}")
        (self.attempt_dir / TRACE_MESSAGES_DIRNAME).mkdir()
        (self.attempt_dir / TRACE_TOOL_EVENTS_DIRNAME).mkdir()

        _create_exclusive(self.attempt_dir / TRACE_TASK_FILENAME, _yaml_bytes(task_snapshot))
        actors = {
            "schema_version": "0.1.0",
            "task_id": task_id,
            "task_revision": task_revision,
            "attempt_id": attempt_id,
            "actors": [
                {
                    "actor_id": actor_id,
                    "actor_type": "runtime-adapter",
                    "role": "bounded API session runner",
                    "runtime_identity": runtime_identity,
                    "accountable_owner": accountable_owner,
                },
                {
                    "actor_id": self.provider_actor_id,
                    "actor_type": "model-provider",
                    "role": "bound model provider",
                    "runtime_identity": provider,
                    "accountable_owner": accountable_owner,
                },
            ],
        }
        _create_exclusive(self.attempt_dir / TRACE_ACTORS_FILENAME, _yaml_bytes(actors))
        _create_exclusive(self.attempt_dir / TRACE_EVENTS_FILENAME, b"")
        self._index: dict[str, Any] = {
            "schema_version": "0.1.0",
            "trace_id": f"TRACE-{_safe_id(attempt_id)}",
            "task_id": task_id,
            "task_revision": task_revision,
            "attempt_id": attempt_id,
            "archive_root": self.attempt_dir.name,
            "baseline": baseline,
            "owner_actor_id": actor_id,
            "owner": accountable_owner,
            "attempt_status": "planned",
            "trace_status": "active",
            "completeness": "complete",
            "task_ref": _ref(self.attempt_dir / TRACE_TASK_FILENAME, TRACE_TASK_FILENAME),
            "actors_ref": _ref(self.attempt_dir / TRACE_ACTORS_FILENAME, TRACE_ACTORS_FILENAME),
            "read_allowlist": sorted(set(read_allowlist)),
            "write_scope": sorted(set(write_scope)),
            "tool_allowlist": sorted(set(tool_allowlist)),
            "messages": self._messages,
            "event_ledger": {"path": TRACE_EVENTS_FILENAME, "sha256": "0" * 64, "event_count": 1},
            "tool_event_refs": self._tool_refs,
            "handoff_refs": [],
            "decision_refs": [],
            "output_refs": [],
            "check_refs": [],
            "capture_gaps": self._capture_gaps,
        }
        self._append_event("attempt-status", {"to_status": "running", "reason": "trace initialized before provider execution"})
        _create_exclusive(self.attempt_dir / TRACE_INDEX_FILENAME, _yaml_bytes(self._index))

    @property
    def redaction_count(self) -> int:
        return self._redaction_count

    @property
    def index_path(self) -> Path:
        return self.attempt_dir / TRACE_INDEX_FILENAME

    def record(self, kind: str, payload: Mapping[str, Any]) -> None:
        """SessionEventSink entrypoint used by the isolated API runner."""

        if self._sealed:
            raise RuntimeError("trace is already sealed")
        if kind == "provider-request":
            self._record_message("provider-request", self.actor_id, (self.provider_actor_id,), payload, "persisted-before-send")
        elif kind == "provider-response":
            self._record_message("provider-response", self.provider_actor_id, (self.actor_id,), payload, "received")
        elif kind == "tool-attempted":
            self._record_tool(payload, status="attempted", result_entered_context=False)
        elif kind == "tool-result":
            self._record_tool(payload, status=str(payload.get("status", "unknown")), result_entered_context=True)
        elif kind == "session-status":
            status = str(payload.get("status", "incomplete"))
            mapped = "safe-paused" if status == "safe_paused" else status.replace("_", "-")
            allowed = {"completed", "safe-paused", "incomplete", "failed", "cancelled", "blocked", "waiting"}
            self._append_event(
                "attempt-status",
                {
                    "from_status": self._status,
                    "to_status": mapped if mapped in allowed else "incomplete",
                    "reason": str(payload.get("reason") or f"session ended with {status}"),
                },
            )
        elif kind == "capture-gap":
            self.record_capture_gap(str(payload.get("stream", "events")), str(payload.get("reason", "capture failure")))
        else:
            raise ValueError(f"unsupported trace event kind: {kind}")

    def record_capture_gap(self, stream: str, reason: str) -> None:
        event = self._append_event(
            "capture-gap",
            {"affected_stream": stream, "reason_category": "capture-failure", "reason": reason},
        )
        self._capture_gaps.append({"event_id": event["event_id"], "affected_stream": stream})
        self._index["completeness"] = "gapped"
        self._refresh_index()

    def seal(self, status: str | None = None) -> Mapping[str, str]:
        if self._sealed:
            return _ref(self.index_path, TRACE_INDEX_FILENAME)
        if status and status != self._status:
            self._append_event(
                "attempt-status",
                {"from_status": self._status, "to_status": status, "reason": "execution trace sealed"},
            )
        self._trace_status = "frozen"
        self._index["trace_status"] = "frozen"
        self._refresh_index()
        self._sealed = True
        return _ref(self.index_path, TRACE_INDEX_FILENAME)

    def _record_message(
        self,
        kind: str,
        sender: str,
        receivers: Sequence[str],
        payload: Mapping[str, Any],
        action: str,
    ) -> None:
        cleaned, redactions = sanitize_trace_value(payload)
        self._redaction_count += len(redactions)
        self._message_sequence += 1
        message_id = f"MSG-{self._message_sequence:04d}"
        body = json.dumps(cleaned, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        envelope = {
            "schema_version": "0.1.0",
            "message_id": message_id,
            "task_id": self.task_id,
            "task_revision": self.task_revision,
            "attempt_id": self.attempt_id,
            "sequence": self._message_sequence,
            "kind": kind,
            "sender_actor_id": sender,
            "receiver_actor_ids": list(receivers),
            "accountable_owner": self.owner,
            "created_at": _now(),
            "content_sha256": _sha256_bytes(body),
            "attachment_refs": [],
            "redactions": list(redactions),
            "capture_status": "complete",
        }
        header = yaml.safe_dump(envelope, sort_keys=False, allow_unicode=True).encode("utf-8")
        content = b"---\n" + header + b"---\n" + body + b"\n"
        relative = f"{TRACE_MESSAGES_DIRNAME}/{self._message_sequence:04d}-{kind}.trace"
        path = self.attempt_dir / relative
        _create_exclusive(path, content)
        self._messages.append(
            {
                "message_id": message_id,
                "sequence": self._message_sequence,
                "path": relative,
                "sha256": hash_file(path),
                "content_sha256": envelope["content_sha256"],
                "kind": kind,
                "sender_actor_id": sender,
                "receiver_actor_ids": list(receivers),
                "created_at": envelope["created_at"],
                "capture_status": "complete",
            }
        )
        self._append_event("message-capture", {"message_id": message_id, "action": action})

    def _record_tool(self, payload: Mapping[str, Any], *, status: str, result_entered_context: bool) -> None:
        cleaned, redactions = sanitize_trace_value(payload)
        self._redaction_count += len(redactions)
        operation_id = str(cleaned.get("operation_id") or cleaned.get("call_id") or f"op-{self._event_sequence + 1}")
        tool_name = str(cleaned.get("tool_name") or cleaned.get("name") or "unknown")
        event_payload: dict[str, Any] = {
            "operation_id": operation_id,
            "tool_name": tool_name,
            "status": status if status in {"attempted", "succeeded", "failed", "cancelled", "delivered", "unknown"} else "unknown",
            "arguments": cleaned.get("arguments", {}) if isinstance(cleaned, Mapping) else {},
            "redactions": list(redactions),
            "result_entered_context": result_entered_context,
        }
        if result_entered_context:
            result_payload = cleaned.get("result", cleaned)
            result_bytes = json.dumps(result_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            relative = f"{TRACE_TOOL_EVENTS_DIRNAME}/{_safe_id(operation_id)}-{status}.json"
            result_path = self.attempt_dir / relative
            _create_exclusive(result_path, result_bytes + b"\n")
            result_ref = _ref(result_path, relative)
            self._tool_refs.append(result_ref)
            event_payload.update({"result_origin": "transient", "result_ref": result_ref})
        self._append_event("tool-call", event_payload)

    def _append_event(self, event_type: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self._event_sequence += 1
        if event_type == "attempt-status":
            self._status = str(payload["to_status"])
        event = {
            "schema_version": "0.1.0",
            "event_id": f"EVT-{self._event_sequence:04d}",
            "task_id": self.task_id,
            "task_revision": self.task_revision,
            "attempt_id": self.attempt_id,
            "sequence": self._event_sequence,
            "event_type": event_type,
            "actor_id": self.actor_id,
            "occurred_at": _now(),
            "payload": dict(payload),
        }
        line = json.dumps(event, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
        with (self.attempt_dir / TRACE_EVENTS_FILENAME).open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
        self._refresh_index()
        return event

    def _refresh_index(self) -> None:
        if not hasattr(self, "_index"):
            return
        event_path = self.attempt_dir / TRACE_EVENTS_FILENAME
        self._index["attempt_status"] = self._status
        self._index["trace_status"] = self._trace_status
        self._index["event_ledger"] = {
            "path": TRACE_EVENTS_FILENAME,
            "sha256": hash_file(event_path),
            "event_count": self._event_sequence,
        }
        index_path = self.attempt_dir / TRACE_INDEX_FILENAME
        if index_path.exists():
            _replace_atomic(index_path, _yaml_bytes(self._index))


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return cleaned or "unknown"


def _ref(path: Path, relative: str) -> dict[str, str]:
    return {"path": relative.replace("\\", "/"), "sha256": hash_file(path)}


def _parse_message(path: Path) -> tuple[Mapping[str, Any], bytes]:
    raw = path.read_bytes()
    if not raw.startswith(b"---\n"):
        raise ValueError("message lacks trace envelope delimiter")
    try:
        header, body = raw[4:].split(b"---\n", 1)
    except ValueError as exc:
        raise ValueError("message lacks body delimiter") from exc
    envelope = yaml.safe_load(header.decode("utf-8"))
    if not isinstance(envelope, Mapping):
        raise ValueError("message envelope is not a mapping")
    return envelope, body.rstrip(b"\n")


def derive_session_transcript(attempt_dir: str | Path) -> tuple[Mapping[str, Any], ...]:
    """Build the legacy request/response view only from hash-bound Trace messages."""

    directory = Path(attempt_dir)
    index = _load_mapping(directory / TRACE_INDEX_FILENAME)
    pending: list[Any] = []
    pairs: list[Mapping[str, Any]] = []
    for entry in index.get("messages", []):
        if not isinstance(entry, Mapping):
            continue
        path = resolve_within_root(directory, str(entry.get("path", "")))
        if path is None or not path.is_file() or hash_file(path) != str(entry.get("sha256", "")).removeprefix("sha256:"):
            raise ValueError("cannot derive transcript from an invalid message reference")
        envelope, body = _parse_message(path)
        payload = json.loads(body.decode("utf-8"))
        if envelope.get("kind") == "provider-request":
            pending.append(payload.get("request", payload) if isinstance(payload, Mapping) else payload)
        elif envelope.get("kind") == "provider-response":
            if not pending:
                raise ValueError("provider response has no preceding request")
            response = payload.get("response", payload) if isinstance(payload, Mapping) else payload
            pairs.append({"request": pending.pop(0), "response": response})
    if pending:
        # A request followed by a provider/capture failure remains visible but
        # is not fabricated into a response pair.
        pairs.extend({"request": request, "response": None} for request in pending)
    return tuple(pairs)


def _risk(code: str, level: RiskLevel, message: str) -> ContractRisk:
    return ContractRisk(code, level, message)


def _load_mapping(path: Path) -> Mapping[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"document is not a mapping: {path}")
    return value


def _matches(path: str, patterns: Sequence[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized == pattern.replace("\\", "/") or fnmatch.fnmatchcase(normalized, pattern.replace("\\", "/")) for pattern in patterns)


def validate_attempt_trace(root: str | Path, attempt: str | Path) -> TraceValidationResult:
    """Validate one Attempt directory or INDEX.yaml and return structured risks."""

    project_root = Path(root).resolve()
    raw_attempt = Path(attempt)
    candidate = raw_attempt if raw_attempt.is_absolute() else project_root / raw_attempt
    candidate = candidate.resolve()
    attempt_dir = candidate.parent if candidate.name == TRACE_INDEX_FILENAME else candidate
    risks: list[ContractRisk] = []
    try:
        attempt_dir.relative_to(project_root)
    except ValueError:
        return TraceValidationResult(attempt_dir, (_risk("TRACE-PATH-ESCAPE", RiskLevel.BLOCK, "attempt is outside the validation root"),))
    index_path = attempt_dir / TRACE_INDEX_FILENAME
    if not index_path.is_file():
        return TraceValidationResult(attempt_dir, (_risk("TRACE-INDEX-MISSING", RiskLevel.BLOCK, f"missing {TRACE_INDEX_FILENAME}"),))
    try:
        index = _load_mapping(index_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return TraceValidationResult(attempt_dir, (_risk("TRACE-INDEX-INVALID", RiskLevel.BLOCK, str(exc)),))
    catalog = SchemaCatalog()
    for error in catalog.validate("agent_trace_index", index):
        risks.append(_risk("TRACE-SCHEMA-INVALID", RiskLevel.BLOCK, f"INDEX{error.pointer}: {error.message}"))

    actors: Mapping[str, Any] = {}
    actors_ref = index.get("actors_ref", {})
    actors_path = _checked_ref(attempt_dir, actors_ref, "actors", risks)
    if actors_path:
        try:
            actors = _load_mapping(actors_path)
            for error in catalog.validate("agent_trace_actors", actors):
                risks.append(_risk("TRACE-SCHEMA-INVALID", RiskLevel.BLOCK, f"ACTORS{error.pointer}: {error.message}"))
        except (OSError, ValueError, yaml.YAMLError) as exc:
            risks.append(_risk("TRACE-ACTORS-INVALID", RiskLevel.BLOCK, str(exc)))
    _checked_ref(attempt_dir, index.get("task_ref", {}), "task", risks)
    known_actors = {
        str(actor.get("actor_id"))
        for actor in actors.get("actors", [])
        if isinstance(actor, Mapping)
    }
    identities = (str(index.get("task_id")), int(index.get("task_revision", 0) or 0), str(index.get("attempt_id")))

    ledger = index.get("event_ledger", {})
    event_path = _checked_ref(attempt_dir, ledger, "event ledger", risks)
    events: list[Mapping[str, Any]] = []
    if event_path:
        for line_number, line in enumerate(event_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                risks.append(_risk("TRACE-EVENT-BLANK", RiskLevel.BLOCK, f"blank event line {line_number}"))
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                risks.append(_risk("TRACE-EVENT-INVALID", RiskLevel.BLOCK, f"line {line_number}: {exc}"))
                continue
            if not isinstance(event, Mapping):
                risks.append(_risk("TRACE-EVENT-INVALID", RiskLevel.BLOCK, f"line {line_number} is not an object"))
                continue
            events.append(event)
            for error in catalog.validate("agent_trace_event", event):
                risks.append(_risk("TRACE-SCHEMA-INVALID", RiskLevel.BLOCK, f"event {line_number}{error.pointer}: {error.message}"))
    expected_event_sequences = list(range(1, len(events) + 1))
    actual_event_sequences = [event.get("sequence") for event in events]
    if actual_event_sequences != expected_event_sequences:
        risks.append(_risk("TRACE-EVENT-SEQUENCE", RiskLevel.BLOCK, "event sequence has a gap, duplicate, or reorder"))
    if isinstance(ledger, Mapping) and ledger.get("event_count") != len(events):
        risks.append(_risk("TRACE-EVENT-COUNT", RiskLevel.BLOCK, "INDEX event_count does not match events.jsonl"))
    for event in events:
        if event.get("actor_id") not in known_actors:
            risks.append(_risk("TRACE-ACTOR-UNKNOWN", RiskLevel.BLOCK, f"event {event.get('event_id')} uses an unregistered actor"))
        if (event.get("task_id"), event.get("task_revision"), event.get("attempt_id")) != identities:
            risks.append(_risk("TRACE-IDENTITY-DRIFT", RiskLevel.BLOCK, f"event {event.get('event_id')} identity differs from INDEX"))
        _validate_event_boundary(attempt_dir, index, event, risks)

    messages = index.get("messages", [])
    if not isinstance(messages, list):
        messages = []
    sequences = [item.get("sequence") for item in messages if isinstance(item, Mapping)]
    if sequences != list(range(1, len(messages) + 1)):
        risks.append(_risk("TRACE-MESSAGE-SEQUENCE", RiskLevel.BLOCK, "message sequence has a gap, duplicate, or reorder"))
    indexed_paths: set[str] = set()
    for entry in messages:
        if not isinstance(entry, Mapping):
            continue
        path = _checked_ref(attempt_dir, entry, f"message {entry.get('message_id')}", risks)
        if not path:
            continue
        indexed_paths.add(path.relative_to(attempt_dir).as_posix())
        try:
            envelope, body = _parse_message(path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            risks.append(_risk("TRACE-MESSAGE-INVALID", RiskLevel.BLOCK, f"{path.name}: {exc}"))
            continue
        for error in catalog.validate("agent_trace_envelope", envelope):
            risks.append(_risk("TRACE-SCHEMA-INVALID", RiskLevel.BLOCK, f"{path.name}{error.pointer}: {error.message}"))
        if _sha256_bytes(body) != str(entry.get("content_sha256", "")).removeprefix("sha256:"):
            risks.append(_risk("TRACE-CONTENT-HASH", RiskLevel.BLOCK, f"message body hash drift: {path.name}"))
        if envelope.get("content_sha256") != entry.get("content_sha256"):
            risks.append(_risk("TRACE-ENVELOPE-DRIFT", RiskLevel.BLOCK, f"envelope/index content hash differs: {path.name}"))
        if (envelope.get("task_id"), envelope.get("task_revision"), envelope.get("attempt_id")) != identities:
            risks.append(_risk("TRACE-IDENTITY-DRIFT", RiskLevel.BLOCK, f"message identity differs from INDEX: {path.name}"))
        actor_ids = {envelope.get("sender_actor_id"), *envelope.get("receiver_actor_ids", [])}
        if not actor_ids.issubset(known_actors):
            risks.append(_risk("TRACE-ACTOR-UNKNOWN", RiskLevel.BLOCK, f"message uses an unregistered actor: {path.name}"))
        if any(marker.encode() in body for marker in _REDACTION_MARKERS) and not envelope.get("redactions"):
            risks.append(_risk("TRACE-REDACTION-UNDECLARED", RiskLevel.BLOCK, f"message contains an undeclared redaction marker: {path.name}"))
    message_dir = attempt_dir / TRACE_MESSAGES_DIRNAME
    if message_dir.is_dir():
        extras = {path.relative_to(attempt_dir).as_posix() for path in message_dir.iterdir() if path.is_file()} - indexed_paths
        if extras:
            risks.append(_risk("TRACE-MESSAGE-UNINDEXED", RiskLevel.BLOCK, "unindexed message files: " + ", ".join(sorted(extras))))

    gaps = index.get("capture_gaps", [])
    if gaps:
        level = RiskLevel.BLOCK if index.get("attempt_status") in {"completed", "stage-completed"} else RiskLevel.WARNING
        risks.append(_risk("TRACE-CAPTURE-GAP", level, f"trace declares {len(gaps)} capture gap(s)"))
    if index.get("completeness") == "complete" and gaps:
        risks.append(_risk("TRACE-FALSE-COMPLETE", RiskLevel.BLOCK, "complete trace cannot contain capture gaps"))
    if index.get("attempt_status") in {"completed", "stage-completed"} and index.get("trace_status") != "frozen":
        risks.append(_risk("TRACE-FALSE-COMPLETE", RiskLevel.BLOCK, "completed attempt trace is not frozen"))
    if not risks:
        risks.append(_risk("TRACE-VALID", RiskLevel.INFO, "trace schema, identities, hashes, sequences, and boundaries are valid"))
    return TraceValidationResult(attempt_dir, tuple(risks))


def _checked_ref(attempt_dir: Path, reference: Any, label: str, risks: list[ContractRisk]) -> Path | None:
    if not isinstance(reference, Mapping) or not isinstance(reference.get("path"), str):
        risks.append(_risk("TRACE-REF-INVALID", RiskLevel.BLOCK, f"{label} reference is missing or invalid"))
        return None
    path = resolve_within_root(attempt_dir, str(reference["path"]))
    if path is None:
        risks.append(_risk("TRACE-PATH-ESCAPE", RiskLevel.BLOCK, f"{label} reference escapes the attempt directory"))
        return None
    if not path.is_file():
        risks.append(_risk("TRACE-REF-MISSING", RiskLevel.BLOCK, f"{label} file is missing: {reference['path']}"))
        return None
    expected = str(reference.get("sha256", "")).lower().removeprefix("sha256:")
    if hash_file(path) != expected:
        risks.append(_risk("TRACE-HASH-DRIFT", RiskLevel.BLOCK, f"{label} hash differs: {reference['path']}"))
    return path


def _validate_event_boundary(
    attempt_dir: Path,
    index: Mapping[str, Any],
    event: Mapping[str, Any],
    risks: list[ContractRisk],
) -> None:
    event_type = event.get("event_type")
    payload = event.get("payload", {})
    if not isinstance(payload, Mapping):
        return
    if event_type == "content-read" and not _matches(str(payload.get("path", "")), index.get("read_allowlist", [])):
        risks.append(_risk("TRACE-READ-OUTSIDE-ALLOWLIST", RiskLevel.BLOCK, f"read outside declared boundary: {payload.get('path')}"))
    if event_type == "tool-call":
        if str(payload.get("tool_name", "")) not in index.get("tool_allowlist", []):
            risks.append(_risk("TRACE-TOOL-OUTSIDE-ALLOWLIST", RiskLevel.BLOCK, f"tool outside declared boundary: {payload.get('tool_name')}"))
        if payload.get("result_entered_context") and payload.get("result_origin") == "transient":
            _checked_ref(attempt_dir, payload.get("result_ref", {}), "transient tool result", risks)
    if event_type == "file-revision":
        raw_path = str(payload.get("path", ""))
        normalized = raw_path.replace("\\", "/")
        if normalized in _PROTECTED_TRACE_PATHS or normalized.startswith(f"{TRACE_MESSAGES_DIRNAME}/") or normalized.startswith(f"{TRACE_TOOL_EVENTS_DIRNAME}/"):
            if payload.get("action") in {"modified", "deleted"}:
                risks.append(_risk("TRACE-PROCESS-ARTIFACT-OVERWRITE", RiskLevel.BLOCK, f"trace process artifact was overwritten: {raw_path}"))
        elif not _matches(raw_path, index.get("write_scope", [])):
            risks.append(_risk("TRACE-WRITE-OUTSIDE-SCOPE", RiskLevel.BLOCK, f"file revision outside declared write scope: {raw_path}"))
