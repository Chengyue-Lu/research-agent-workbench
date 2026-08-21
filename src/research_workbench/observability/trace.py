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
from collections import Counter
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
_RISK_MESSAGE_MISSING = "TRACE-MESSAGE-MISSING"
_RISK_SEQUENCE_GAP = "TRACE-SEQUENCE-GAP"
_RISK_ACTOR_UNOWNED = "TRACE-ACTOR-UNOWNED"
_RISK_HASH_MISMATCH = "TRACE-HASH-MISMATCH"
_RISK_CAPTURE_DELAYED = "TRACE-CAPTURE-DELAYED"
_RISK_REDACTION_UNDECLARED = "TRACE-REDACTION-UNDECLARED"
_RISK_READ_OUTSIDE_SCOPE = "TRACE-READ-OUTSIDE-SCOPE"
_RISK_EVENT_MISSING = "TRACE-EVENT-MISSING"
_RISK_TRANSIENT_RESULT_MISSING = "TRACE-TRANSIENT-RESULT-MISSING"
_RISK_PROCESS_ARTIFACT_OVERWRITTEN = "TRACE-PROCESS-ARTIFACT-OVERWRITTEN"
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
        self._append_event(
            "attempt-status",
            {
                "from_status": "planned",
                "to_status": "running",
                "reason": "trace initialized before provider execution",
            },
        )
        _create_exclusive(self.attempt_dir / TRACE_INDEX_FILENAME, _yaml_bytes(self._index))

    @property
    def redaction_count(self) -> int:
        return self._redaction_count

    @property
    def index_path(self) -> Path:
        return self.attempt_dir / TRACE_INDEX_FILENAME

    def record_content_read(
        self,
        path: str,
        *,
        access: str,
        allowlist_basis: str,
        content_sha256: str | None = None,
    ) -> None:
        """Record a file read as a fact; boundary compliance is validated later."""

        payload: dict[str, Any] = {
            "path": path,
            "access": access,
            "allowlist_basis": allowlist_basis,
        }
        if content_sha256 is not None:
            payload["content_sha256"] = content_sha256
        self._append_event("content-read", payload)

    def record_tool_call(
        self,
        *,
        operation_id: str,
        tool_name: str,
        status: str,
        arguments: Mapping[str, Any],
        result: Any | None = None,
        result_entered_context: bool = False,
    ) -> None:
        """Record a bounded tool fact; shell commands use ``tool_name='shell'``."""

        if result_entered_context and result is None:
            raise ValueError("a tool result must be supplied before it can enter model context")
        payload: dict[str, Any] = {
            "operation_id": operation_id,
            "tool_name": tool_name,
            "arguments": arguments,
        }
        if result is not None:
            payload["result"] = result
        self._record_tool(
            payload,
            status=status,
            result_entered_context=result_entered_context,
        )

    def record_file_revision(
        self,
        path: str,
        *,
        action: str,
        old_sha256: str | None = None,
        new_sha256: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Record a created, modified, or deleted file without mutating it."""

        payload: dict[str, Any] = {"path": path, "action": action}
        for key, value in (
            ("old_sha256", old_sha256),
            ("new_sha256", new_sha256),
            ("reason", reason),
        ):
            if value is not None:
                payload[key] = value
        self._append_event("file-revision", payload)

    def record_external_action(
        self,
        *,
        action_id: str,
        target_category: str,
        authorization_basis: str,
        side_effect_status: str,
        receipt_ref: Mapping[str, str] | None = None,
    ) -> None:
        """Record an externally visible side effect and its authorization fact."""

        payload: dict[str, Any] = {
            "action_id": action_id,
            "target_category": target_category,
            "authorization_basis": authorization_basis,
            "side_effect_status": side_effect_status,
        }
        if receipt_ref is not None:
            payload["receipt_ref"] = dict(receipt_ref)
        self._append_event("external-action", payload)

    def record_attempt_status(
        self,
        to_status: str,
        *,
        reason: str,
        from_status: str | None = None,
    ) -> None:
        """Record an Attempt lifecycle fact without inferring completion quality."""

        payload = {
            "from_status": from_status or self._status,
            "to_status": to_status,
            "reason": reason,
        }
        self._append_event("attempt-status", payload)

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
            self._record_tool(
                payload,
                status=str(payload.get("status", "unknown")),
                result_entered_context=bool(payload.get("result_entered_context", False)),
            )
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
            raw_affected_ids = payload.get("affected_ids", ())
            affected_ids = (
                tuple(str(item) for item in raw_affected_ids)
                if isinstance(raw_affected_ids, (list, tuple))
                else ()
            )
            self.record_capture_gap(
                str(payload.get("stream", "events")),
                str(payload.get("reason", "capture failure")),
                reason_category=str(payload.get("reason_category", "capture-failure")),
                affected_ids=affected_ids,
            )
        else:
            raise ValueError(f"unsupported trace event kind: {kind}")

    def record_capture_gap(
        self,
        stream: str,
        reason: str,
        *,
        reason_category: str = "capture-failure",
        affected_ids: Sequence[str] = (),
    ) -> None:
        payload: dict[str, Any] = {
            "affected_stream": stream,
            "reason_category": reason_category,
            "reason": reason,
        }
        if affected_ids:
            payload["affected_ids"] = list(affected_ids)
        event = self._append_event(
            "capture-gap",
            payload,
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
        self._append_event("tool-call", event_payload, inherited_redactions=redactions)

    def _append_event(
        self,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        inherited_redactions: Sequence[Mapping[str, str]] = (),
    ) -> Mapping[str, Any]:
        if self._sealed:
            raise RuntimeError("trace is already sealed")
        cleaned_payload, local_redactions = sanitize_trace_value(payload)
        combined_redactions = [
            {key: str(value) for key, value in redaction.items() if key != "redaction_id"}
            for redaction in (*inherited_redactions, *local_redactions)
        ]
        event_redactions = [
            {"redaction_id": f"RED-{index:04d}", **redaction}
            for index, redaction in enumerate(combined_redactions, start=1)
        ]
        self._redaction_count += len(local_redactions)
        self._event_sequence += 1
        if event_type == "attempt-status":
            self._status = str(cleaned_payload["to_status"])
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
            "payload": dict(cleaned_payload),
            "redactions": event_redactions,
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


def _risk(code: str, level: RiskLevel, message: str, *, detail: str) -> ContractRisk:
    """Emit one canonical public code with a stable internal detail subcode."""

    return ContractRisk(code, level, f"[{detail}] {message}")


def _load_mapping(path: Path) -> Mapping[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"document is not a mapping: {path}")
    return value


def _matches(path: str, patterns: Sequence[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(
        isinstance(pattern, str)
        and (
            normalized == pattern.replace("\\", "/")
            or fnmatch.fnmatchcase(normalized, pattern.replace("\\", "/"))
        )
        for pattern in patterns
    )


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
        return TraceValidationResult(
            attempt_dir,
            (
                _risk(
                    _RISK_READ_OUTSIDE_SCOPE,
                    RiskLevel.BLOCK,
                    "attempt is outside the validation root",
                    detail="attempt-path-escape",
                ),
            ),
        )
    index_path = attempt_dir / TRACE_INDEX_FILENAME
    if not index_path.is_file():
        return TraceValidationResult(
            attempt_dir,
            (
                _risk(
                    _RISK_EVENT_MISSING,
                    RiskLevel.BLOCK,
                    f"missing {TRACE_INDEX_FILENAME}",
                    detail="index-missing",
                ),
            ),
        )
    try:
        index = _load_mapping(index_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return TraceValidationResult(
            attempt_dir,
            (
                _risk(
                    _RISK_EVENT_MISSING,
                    RiskLevel.BLOCK,
                    str(exc),
                    detail="index-invalid",
                ),
            ),
        )
    catalog = SchemaCatalog()
    for error in catalog.validate("agent_trace_index", index):
        risks.append(
            _risk(
                _RISK_EVENT_MISSING,
                RiskLevel.BLOCK,
                f"INDEX{error.pointer}: {error.message}",
                detail="index-schema-invalid",
            )
        )

    actors: Mapping[str, Any] = {}
    actors_ref = index.get("actors_ref", {})
    actors_path = _checked_ref(attempt_dir, actors_ref, "actors", risks, detail="actors-ref")
    if actors_path:
        try:
            actors = _load_mapping(actors_path)
            for error in catalog.validate("agent_trace_actors", actors):
                risks.append(
                    _risk(
                        _RISK_ACTOR_UNOWNED,
                        RiskLevel.BLOCK,
                        f"ACTORS{error.pointer}: {error.message}",
                        detail="actors-schema-invalid",
                    )
                )
        except (OSError, ValueError, yaml.YAMLError) as exc:
            risks.append(
                _risk(
                    _RISK_ACTOR_UNOWNED,
                    RiskLevel.BLOCK,
                    str(exc),
                    detail="actors-invalid",
                )
            )
    task_path = _checked_ref(attempt_dir, index.get("task_ref", {}), "task", risks, detail="task-ref")
    if task_path:
        try:
            task_snapshot = _load_mapping(task_path)
            if "task_id" in task_snapshot and task_snapshot.get("task_id") != index.get("task_id"):
                risks.append(
                    _risk(
                        _RISK_EVENT_MISSING,
                        RiskLevel.BLOCK,
                        "Task snapshot task_id differs from INDEX",
                        detail="task-identity-drift",
                    )
                )
            if "revision" in task_snapshot and task_snapshot.get("revision") != index.get("task_revision"):
                risks.append(
                    _risk(
                        _RISK_EVENT_MISSING,
                        RiskLevel.BLOCK,
                        "Task snapshot revision differs from INDEX",
                        detail="task-revision-drift",
                    )
                )
        except (OSError, ValueError, yaml.YAMLError) as exc:
            risks.append(
                _risk(
                    _RISK_EVENT_MISSING,
                    RiskLevel.BLOCK,
                    str(exc),
                    detail="task-invalid",
                )
            )
    actor_entries = actors.get("actors", [])
    if not isinstance(actor_entries, list):
        actor_entries = []
    declared_actor_ids = [
        str(actor.get("actor_id"))
        for actor in actor_entries
        if isinstance(actor, Mapping) and actor.get("actor_id") is not None
    ]
    actor_owners = {
        str(actor.get("actor_id")): str(actor.get("accountable_owner", ""))
        for actor in actor_entries
        if isinstance(actor, Mapping) and actor.get("actor_id") is not None
    }
    known_actors = set(actor_owners)
    if len(declared_actor_ids) != len(set(declared_actor_ids)):
        risks.append(
            _risk(
                _RISK_ACTOR_UNOWNED,
                RiskLevel.BLOCK,
                "ACTORS contains duplicate actor_id values",
                detail="duplicate-actor-id",
            )
        )
    identities = (index.get("task_id"), index.get("task_revision"), index.get("attempt_id"))
    actor_identities = (actors.get("task_id"), actors.get("task_revision"), actors.get("attempt_id"))
    if actors and actor_identities != identities:
        risks.append(
            _risk(
                _RISK_EVENT_MISSING,
                RiskLevel.BLOCK,
                "ACTORS identity differs from INDEX",
                detail="actors-identity-drift",
            )
        )
    owner_actor_id = index.get("owner_actor_id")
    if owner_actor_id not in known_actors:
        risks.append(
            _risk(
                _RISK_ACTOR_UNOWNED,
                RiskLevel.BLOCK,
                "INDEX owner_actor_id is not registered",
                detail="owner-actor-unregistered",
            )
        )
    elif actor_owners.get(str(owner_actor_id)) != index.get("owner"):
        risks.append(
            _risk(
                _RISK_ACTOR_UNOWNED,
                RiskLevel.BLOCK,
                "INDEX owner differs from owner_actor_id accountable_owner",
                detail="owner-drift",
            )
        )
    for actor_id, accountable_owner in actor_owners.items():
        if not accountable_owner.strip():
            risks.append(
                _risk(
                    _RISK_ACTOR_UNOWNED,
                    RiskLevel.BLOCK,
                    f"actor {actor_id} has no accountable_owner",
                    detail="actor-owner-missing",
                )
            )

    for collection_name in (
        "handoff_refs",
        "decision_refs",
        "output_refs",
        "check_refs",
    ):
        references = index.get(collection_name, [])
        if isinstance(references, list):
            for position, reference in enumerate(references, start=1):
                _checked_ref(
                    attempt_dir,
                    reference,
                    f"{collection_name}[{position}]",
                    risks,
                    detail=f"{collection_name}-ref",
                )

    ledger = index.get("event_ledger", {})
    event_path = _checked_ref(attempt_dir, ledger, "event ledger", risks, detail="event-ledger-ref")
    events: list[Mapping[str, Any]] = []
    if event_path:
        try:
            event_lines = event_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            risks.append(
                _risk(
                    _RISK_EVENT_MISSING,
                    RiskLevel.BLOCK,
                    f"cannot read event ledger: {exc}",
                    detail="event-ledger-unreadable",
                )
            )
            event_lines = []
        for line_number, line in enumerate(event_lines, start=1):
            if not line.strip():
                risks.append(
                    _risk(
                        _RISK_EVENT_MISSING,
                        RiskLevel.BLOCK,
                        f"blank event line {line_number}",
                        detail="event-blank",
                    )
                )
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                risks.append(
                    _risk(
                        _RISK_EVENT_MISSING,
                        RiskLevel.BLOCK,
                        f"line {line_number}: {exc}",
                        detail="event-json-invalid",
                    )
                )
                continue
            if not isinstance(event, Mapping):
                risks.append(
                    _risk(
                        _RISK_EVENT_MISSING,
                        RiskLevel.BLOCK,
                        f"line {line_number} is not an object",
                        detail="event-object-invalid",
                    )
                )
                continue
            events.append(event)
            for error in catalog.validate("agent_trace_event", event):
                risks.append(
                    _risk(
                        _RISK_EVENT_MISSING,
                        RiskLevel.BLOCK,
                        f"event {line_number}{error.pointer}: {error.message}",
                        detail="event-schema-invalid",
                    )
                )
    expected_event_sequences = list(range(1, len(events) + 1))
    actual_event_sequences = [event.get("sequence") for event in events]
    if actual_event_sequences != expected_event_sequences:
        risks.append(
            _risk(
                _RISK_SEQUENCE_GAP,
                RiskLevel.BLOCK,
                "event sequence has a gap, duplicate, or reorder",
                detail="event-sequence",
            )
        )
    event_ids = [event.get("event_id") for event in events if isinstance(event.get("event_id"), str)]
    if len(event_ids) != len(set(event_ids)):
        risks.append(
            _risk(
                _RISK_SEQUENCE_GAP,
                RiskLevel.BLOCK,
                "event_id values are not unique",
                detail="duplicate-event-id",
            )
        )
    if isinstance(ledger, Mapping) and ledger.get("event_count") != len(events):
        risks.append(
            _risk(
                _RISK_EVENT_MISSING,
                RiskLevel.BLOCK,
                "INDEX event_count does not match events.jsonl",
                detail="event-count-drift",
            )
        )
    for event in events:
        if event.get("actor_id") not in known_actors:
            risks.append(
                _risk(
                    _RISK_ACTOR_UNOWNED,
                    RiskLevel.BLOCK,
                    f"event {event.get('event_id')} uses an unregistered actor",
                    detail="event-actor-unregistered",
                )
            )
        if (event.get("task_id"), event.get("task_revision"), event.get("attempt_id")) != identities:
            risks.append(
                _risk(
                    _RISK_EVENT_MISSING,
                    RiskLevel.BLOCK,
                    f"event {event.get('event_id')} identity differs from INDEX",
                    detail="event-identity-drift",
                )
            )
        payload = event.get("payload", {})
        if isinstance(payload, Mapping):
            rendered_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            if any(marker in rendered_payload for marker in _REDACTION_MARKERS) and not event.get("redactions"):
                risks.append(
                    _risk(
                        _RISK_REDACTION_UNDECLARED,
                        RiskLevel.BLOCK,
                        f"event {event.get('event_id')} contains an undeclared redaction marker",
                        detail="event-redaction-metadata-missing",
                    )
                )
        _validate_event_boundary(attempt_dir, index, event, risks)

    _validate_tool_result_provenance(attempt_dir, index, events, risks)

    status_events = [event for event in events if event.get("event_type") == "attempt-status"]
    current_status = "planned"
    if not status_events:
        risks.append(
            _risk(
                _RISK_EVENT_MISSING,
                RiskLevel.BLOCK,
                "trace has no attempt-status event",
                detail="attempt-status-missing",
            )
        )
    for event in status_events:
        payload = event.get("payload", {})
        if not isinstance(payload, Mapping):
            continue
        if payload.get("from_status") != current_status:
            risks.append(
                _risk(
                    _RISK_EVENT_MISSING,
                    RiskLevel.BLOCK,
                    f"attempt status {event.get('event_id')} starts at "
                    f"{payload.get('from_status')!r}, expected {current_status!r}",
                    detail="attempt-status-chain-drift",
                )
            )
        if isinstance(payload.get("to_status"), str):
            current_status = str(payload["to_status"])
    if index.get("attempt_status") != current_status:
        risks.append(
            _risk(
                _RISK_EVENT_MISSING,
                RiskLevel.BLOCK,
                "INDEX attempt_status does not match the final attempt-status event",
                detail="attempt-status-index-drift",
            )
        )

    messages = index.get("messages", [])
    if not isinstance(messages, list):
        messages = []
    sequences = [item.get("sequence") for item in messages if isinstance(item, Mapping)]
    if sequences != list(range(1, len(messages) + 1)):
        risks.append(
            _risk(
                _RISK_SEQUENCE_GAP,
                RiskLevel.BLOCK,
                "message sequence has a gap, duplicate, or reorder",
                detail="message-sequence",
            )
        )
    indexed_message_ids = [
        entry.get("message_id")
        for entry in messages
        if isinstance(entry, Mapping) and isinstance(entry.get("message_id"), str)
    ]
    if len(indexed_message_ids) != len(set(indexed_message_ids)):
        risks.append(
            _risk(
                _RISK_SEQUENCE_GAP,
                RiskLevel.BLOCK,
                "INDEX message_id values are not unique",
                detail="duplicate-message-id",
            )
        )
    indexed_paths: set[str] = set()
    parsed_messages: list[tuple[Mapping[str, Any], Mapping[str, Any], Path]] = []
    envelope_message_ids: list[str] = []
    for entry in messages:
        if not isinstance(entry, Mapping):
            continue
        path = _checked_ref(
            attempt_dir,
            entry,
            f"message {entry.get('message_id')}",
            risks,
            missing_code=_RISK_MESSAGE_MISSING,
            detail="message-ref",
        )
        if not path:
            continue
        indexed_paths.add(path.relative_to(attempt_dir).as_posix())
        try:
            envelope, body = _parse_message(path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            risks.append(
                _risk(
                    _RISK_MESSAGE_MISSING,
                    RiskLevel.BLOCK,
                    f"{path.name}: {exc}",
                    detail="message-envelope-invalid",
                )
            )
            continue
        try:
            json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            risks.append(
                _risk(
                    _RISK_MESSAGE_MISSING,
                    RiskLevel.BLOCK,
                    f"{path.name} body: {exc}",
                    detail="message-body-invalid",
                )
            )
        for error in catalog.validate("agent_trace_envelope", envelope):
            risks.append(
                _risk(
                    _RISK_MESSAGE_MISSING,
                    RiskLevel.BLOCK,
                    f"{path.name}{error.pointer}: {error.message}",
                    detail="message-envelope-schema-invalid",
                )
            )
        parsed_messages.append((entry, envelope, path))
        if isinstance(envelope.get("message_id"), str):
            envelope_message_ids.append(str(envelope["message_id"]))
        if _sha256_bytes(body) != str(entry.get("content_sha256", "")).removeprefix("sha256:"):
            risks.append(
                _risk(
                    _RISK_HASH_MISMATCH,
                    RiskLevel.BLOCK,
                    f"message body hash drift: {path.name}",
                    detail="message-content-hash",
                )
            )
        if envelope.get("content_sha256") != entry.get("content_sha256"):
            risks.append(
                _risk(
                    _RISK_HASH_MISMATCH,
                    RiskLevel.BLOCK,
                    f"envelope/index content hash differs: {path.name}",
                    detail="message-index-content-hash",
                )
            )
        for field in (
            "message_id",
            "sequence",
            "kind",
            "sender_actor_id",
            "receiver_actor_ids",
            "created_at",
            "capture_status",
            "capture_gap_event_id",
        ):
            if envelope.get(field) != entry.get(field):
                risks.append(
                    _risk(
                        _RISK_MESSAGE_MISSING,
                        RiskLevel.BLOCK,
                        f"envelope/index {field} differs: {path.name}",
                        detail="message-index-envelope-drift",
                    )
                )
        if (envelope.get("task_id"), envelope.get("task_revision"), envelope.get("attempt_id")) != identities:
            risks.append(
                _risk(
                    _RISK_MESSAGE_MISSING,
                    RiskLevel.BLOCK,
                    f"message identity differs from INDEX: {path.name}",
                    detail="message-identity-drift",
                )
            )
        receiver_ids = envelope.get("receiver_actor_ids", [])
        if not isinstance(receiver_ids, list):
            receiver_ids = []
        actor_ids = {envelope.get("sender_actor_id"), *receiver_ids}
        if not actor_ids.issubset(known_actors):
            risks.append(
                _risk(
                    _RISK_ACTOR_UNOWNED,
                    RiskLevel.BLOCK,
                    f"message uses an unregistered actor: {path.name}",
                    detail="message-actor-unregistered",
                )
            )
        sender = envelope.get("sender_actor_id")
        if sender in actor_owners and envelope.get("accountable_owner") != actor_owners[str(sender)]:
            risks.append(
                _risk(
                    _RISK_ACTOR_UNOWNED,
                    RiskLevel.BLOCK,
                    f"message accountable_owner differs from sender actor owner: {path.name}",
                    detail="message-owner-drift",
                )
            )
        if any(marker.encode() in body for marker in _REDACTION_MARKERS) and not envelope.get("redactions"):
            risks.append(
                _risk(
                    _RISK_REDACTION_UNDECLARED,
                    RiskLevel.BLOCK,
                    f"message contains an undeclared redaction marker: {path.name}",
                    detail="message-redaction-metadata-missing",
                )
            )
    if len(envelope_message_ids) != len(set(envelope_message_ids)):
        risks.append(
            _risk(
                _RISK_SEQUENCE_GAP,
                RiskLevel.BLOCK,
                "hash-bound envelope message_id values are not unique",
                detail="duplicate-envelope-message-id",
            )
        )
    message_dir = attempt_dir / TRACE_MESSAGES_DIRNAME
    if message_dir.is_dir():
        extras = {
            path.relative_to(attempt_dir).as_posix()
            for path in message_dir.iterdir()
            if path.is_file()
        } - indexed_paths
        if extras:
            risks.append(
                _risk(
                    _RISK_MESSAGE_MISSING,
                    RiskLevel.BLOCK,
                    "unindexed message files: " + ", ".join(sorted(extras)),
                    detail="message-unindexed",
                )
            )

    _validate_message_capture_events(events, indexed_message_ids, risks)
    has_gap, has_delay = _validate_capture_consistency(index, events, parsed_messages, risks)
    if has_gap or has_delay:
        level = (
            RiskLevel.BLOCK
            if index.get("attempt_status") in {"completed", "stage-completed"}
            else RiskLevel.WARNING
        )
        detail = "capture-gap" if has_gap else "capture-delayed"
        risks.append(
            _risk(
                _RISK_CAPTURE_DELAYED,
                level,
                "trace declares incomplete or delayed capture",
                detail=detail,
            )
        )
    if index.get("attempt_status") in {"completed", "stage-completed"} and index.get("trace_status") != "frozen":
        risks.append(
            _risk(
                _RISK_EVENT_MISSING,
                RiskLevel.BLOCK,
                "completed attempt trace is not frozen",
                detail="completed-trace-not-frozen",
            )
        )
    return TraceValidationResult(attempt_dir, tuple(risks))


def _checked_ref(
    attempt_dir: Path,
    reference: Any,
    label: str,
    risks: list[ContractRisk],
    *,
    missing_code: str = _RISK_EVENT_MISSING,
    detail: str,
) -> Path | None:
    if not isinstance(reference, Mapping) or not isinstance(reference.get("path"), str):
        risks.append(
            _risk(
                missing_code,
                RiskLevel.BLOCK,
                f"{label} reference is missing or invalid",
                detail=f"{detail}-invalid",
            )
        )
        return None
    path = resolve_within_root(attempt_dir, str(reference["path"]))
    if path is None:
        risks.append(
            _risk(
                missing_code,
                RiskLevel.BLOCK,
                f"{label} reference escapes the attempt directory",
                detail=f"{detail}-path-escape",
            )
        )
        return None
    if not path.is_file():
        risks.append(
            _risk(
                missing_code,
                RiskLevel.BLOCK,
                f"{label} file is missing: {reference['path']}",
                detail=f"{detail}-missing",
            )
        )
        return None
    expected = str(reference.get("sha256", "")).lower().removeprefix("sha256:")
    if hash_file(path) != expected:
        risks.append(
            _risk(
                _RISK_HASH_MISMATCH,
                RiskLevel.BLOCK,
                f"{label} hash differs: {reference['path']}",
                detail=f"{detail}-hash",
            )
        )
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
    read_allowlist = index.get("read_allowlist", [])
    write_scope = index.get("write_scope", [])
    tool_allowlist = index.get("tool_allowlist", [])
    if not isinstance(read_allowlist, list):
        read_allowlist = []
    if not isinstance(write_scope, list):
        write_scope = []
    if not isinstance(tool_allowlist, list):
        tool_allowlist = []
    if event_type == "content-read" and not _matches(str(payload.get("path", "")), read_allowlist):
        risks.append(
            _risk(
                _RISK_READ_OUTSIDE_SCOPE,
                RiskLevel.BLOCK,
                f"read outside declared boundary: {payload.get('path')}",
                detail="content-read-outside-scope",
            )
        )
    if event_type == "tool-call":
        if str(payload.get("tool_name", "")) not in tool_allowlist:
            risks.append(
                _risk(
                    _RISK_READ_OUTSIDE_SCOPE,
                    RiskLevel.BLOCK,
                    f"tool outside declared boundary: {payload.get('tool_name')}",
                    detail="tool-outside-scope",
                )
            )
        result_entered_context = payload.get("result_entered_context") is True
        result_origin = payload.get("result_origin")
        has_result_ref = "result_ref" in payload
        if result_entered_context and result_origin != "transient":
            detail = "result-origin-missing" if result_origin is None else "result-origin-invalid"
            risks.append(
                _risk(
                    _RISK_TRANSIENT_RESULT_MISSING,
                    RiskLevel.BLOCK,
                    "tool result entered context without transient provenance",
                    detail=detail,
                )
            )
        if not result_entered_context and (result_origin is not None or has_result_ref):
            risks.append(
                _risk(
                    _RISK_TRANSIENT_RESULT_MISSING,
                    RiskLevel.BLOCK,
                    "tool result provenance is present although the result did not enter context",
                    detail="tool-result-provenance-unexpected",
                )
            )
        if result_origin == "transient":
            if not isinstance(payload.get("result_ref"), Mapping):
                risks.append(
                    _risk(
                        _RISK_TRANSIENT_RESULT_MISSING,
                        RiskLevel.BLOCK,
                        "transient tool result has no result_ref",
                        detail="transient-result-ref-missing",
                    )
                )
    if event_type == "file-revision":
        raw_path = str(payload.get("path", ""))
        normalized = raw_path.replace("\\", "/")
        if (
            normalized in _PROTECTED_TRACE_PATHS
            or normalized.startswith(f"{TRACE_MESSAGES_DIRNAME}/")
            or normalized.startswith(f"{TRACE_TOOL_EVENTS_DIRNAME}/")
        ):
            if payload.get("action") in {"modified", "deleted"}:
                risks.append(
                    _risk(
                        _RISK_PROCESS_ARTIFACT_OVERWRITTEN,
                        RiskLevel.BLOCK,
                        f"trace process artifact was overwritten: {raw_path}",
                        detail="protected-trace-artifact-overwrite",
                    )
                )
        elif not _matches(raw_path, write_scope):
            risks.append(
                _risk(
                    _RISK_READ_OUTSIDE_SCOPE,
                    RiskLevel.BLOCK,
                    f"file revision outside declared write scope: {raw_path}",
                    detail="write-outside-scope",
                )
            )
    if event_type == "external-action" and "receipt_ref" in payload:
        _checked_ref(
            attempt_dir,
            payload.get("receipt_ref"),
            "external action receipt",
            risks,
            detail="external-action-receipt",
        )


def _trace_ref_key(reference: Mapping[str, Any]) -> str:
    return json.dumps(_plain(reference), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _validate_tool_result_provenance(
    attempt_dir: Path,
    index: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    risks: list[ContractRisk],
) -> None:
    event_refs: list[Any] = []
    for event in events:
        if event.get("event_type") != "tool-call":
            continue
        payload = event.get("payload", {})
        if isinstance(payload, Mapping) and payload.get("result_origin") == "transient":
            event_refs.append(payload.get("result_ref"))

    raw_index_refs = index.get("tool_event_refs", [])
    index_refs = raw_index_refs if isinstance(raw_index_refs, list) else []
    event_mappings = [reference for reference in event_refs if isinstance(reference, Mapping)]
    index_mappings = [reference for reference in index_refs if isinstance(reference, Mapping)]
    event_counts = Counter(_trace_ref_key(reference) for reference in event_mappings)
    index_counts = Counter(_trace_ref_key(reference) for reference in index_mappings)
    event_by_key = {_trace_ref_key(reference): reference for reference in event_mappings}
    index_by_key = {_trace_ref_key(reference): reference for reference in index_mappings}

    for key, missing_count in (event_counts - index_counts).items():
        reference = event_by_key[key]
        risks.append(
            _risk(
                _RISK_TRANSIENT_RESULT_MISSING,
                RiskLevel.BLOCK,
                f"event result_ref is absent from INDEX.tool_event_refs "
                f"({missing_count} unmatched): {reference.get('path')}",
                detail="tool-result-index-missing",
            )
        )
    for key, extra_count in (index_counts - event_counts).items():
        reference = index_by_key[key]
        risks.append(
            _risk(
                _RISK_TRANSIENT_RESULT_MISSING,
                RiskLevel.BLOCK,
                f"INDEX.tool_event_refs has no matching transient event "
                f"({extra_count} unmatched): {reference.get('path')}",
                detail="tool-result-index-extra",
            )
        )

    referenced_paths: set[str] = set()
    checked_keys: set[str] = set()
    for source, references in (("event", event_refs), ("index", index_refs)):
        for position, reference in enumerate(references, start=1):
            if isinstance(reference, Mapping):
                key = _trace_ref_key(reference)
                raw_path = reference.get("path")
                if isinstance(raw_path, str):
                    normalized_path = raw_path.replace("\\", "/")
                    referenced_paths.add(normalized_path)
                    if not normalized_path.startswith(f"{TRACE_TOOL_EVENTS_DIRNAME}/"):
                        risks.append(
                            _risk(
                                _RISK_TRANSIENT_RESULT_MISSING,
                                RiskLevel.BLOCK,
                                f"{source} tool result ref is outside {TRACE_TOOL_EVENTS_DIRNAME}/: {raw_path}",
                                detail="tool-result-path-outside-tool-events",
                            )
                        )
                if key in checked_keys:
                    continue
                checked_keys.add(key)
            _checked_ref(
                attempt_dir,
                reference,
                f"{source} transient tool result[{position}]",
                risks,
                missing_code=_RISK_TRANSIENT_RESULT_MISSING,
                detail=f"tool-result-{source}-ref",
            )

    tool_events_dir = attempt_dir / TRACE_TOOL_EVENTS_DIRNAME
    if tool_events_dir.is_dir():
        stored_paths = {
            path.relative_to(attempt_dir).as_posix()
            for path in tool_events_dir.rglob("*")
            if path.is_file()
        }
        for orphan in sorted(stored_paths - referenced_paths):
            risks.append(
                _risk(
                    _RISK_TRANSIENT_RESULT_MISSING,
                    RiskLevel.BLOCK,
                    f"tool result file is not referenced by an event or INDEX: {orphan}",
                    detail="tool-result-unindexed",
                )
            )


def _validate_message_capture_events(
    events: Sequence[Mapping[str, Any]],
    indexed_message_ids: Sequence[str],
    risks: list[ContractRisk],
) -> None:
    indexed = set(indexed_message_ids)
    captured: set[str] = set()
    for event in events:
        if event.get("event_type") != "message-capture":
            continue
        payload = event.get("payload", {})
        if not isinstance(payload, Mapping) or not isinstance(payload.get("message_id"), str):
            continue
        message_id = str(payload["message_id"])
        captured.add(message_id)
        if message_id not in indexed:
            risks.append(
                _risk(
                    _RISK_MESSAGE_MISSING,
                    RiskLevel.BLOCK,
                    f"message-capture event references absent message {message_id}",
                    detail="message-capture-target-missing",
                )
            )
    for message_id in sorted(indexed - captured):
        risks.append(
            _risk(
                _RISK_EVENT_MISSING,
                RiskLevel.BLOCK,
                f"indexed message {message_id} has no message-capture event",
                detail="message-capture-event-missing",
            )
        )


def _validate_capture_consistency(
    index: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    parsed_messages: Sequence[tuple[Mapping[str, Any], Mapping[str, Any], Path]],
    risks: list[ContractRisk],
) -> tuple[bool, bool]:
    event_gaps = [event for event in events if event.get("event_type") == "capture-gap"]
    event_gap_by_id = {
        str(event.get("event_id")): event
        for event in event_gaps
        if isinstance(event.get("event_id"), str)
    }
    raw_index_gaps = index.get("capture_gaps", [])
    index_gaps = (
        [gap for gap in raw_index_gaps if isinstance(gap, Mapping)]
        if isinstance(raw_index_gaps, list)
        else []
    )
    index_gap_ids = [str(gap.get("event_id")) for gap in index_gaps if isinstance(gap.get("event_id"), str)]
    if len(index_gap_ids) != len(set(index_gap_ids)):
        risks.append(
            _risk(
                _RISK_CAPTURE_DELAYED,
                RiskLevel.BLOCK,
                "INDEX capture_gaps contains duplicate event_id values",
                detail="duplicate-index-capture-gap",
            )
        )
    index_gap_by_id = {
        str(gap.get("event_id")): gap
        for gap in index_gaps
        if isinstance(gap.get("event_id"), str)
    }
    for event_id, event in event_gap_by_id.items():
        payload = event.get("payload", {})
        stream = payload.get("affected_stream") if isinstance(payload, Mapping) else None
        gap = index_gap_by_id.get(event_id)
        if gap is None:
            risks.append(
                _risk(
                    _RISK_CAPTURE_DELAYED,
                    RiskLevel.BLOCK,
                    f"capture-gap event {event_id} is absent from INDEX.capture_gaps",
                    detail="capture-gap-event-unindexed",
                )
            )
        elif gap.get("affected_stream") != stream:
            risks.append(
                _risk(
                    _RISK_CAPTURE_DELAYED,
                    RiskLevel.BLOCK,
                    f"capture-gap stream differs for {event_id}",
                    detail="capture-gap-stream-drift",
                )
            )
    for event_id, gap in index_gap_by_id.items():
        event = event_gap_by_id.get(event_id)
        if event is None:
            risks.append(
                _risk(
                    _RISK_CAPTURE_DELAYED,
                    RiskLevel.BLOCK,
                    f"INDEX capture gap {event_id} has no ledger event",
                    detail="indexed-capture-gap-event-missing",
                )
            )
            continue
        payload = event.get("payload", {})
        if isinstance(payload, Mapping) and gap.get("affected_stream") != payload.get("affected_stream"):
            risks.append(
                _risk(
                    _RISK_CAPTURE_DELAYED,
                    RiskLevel.BLOCK,
                    f"INDEX capture gap stream differs for {event_id}",
                    detail="indexed-capture-gap-stream-drift",
                )
            )

    message_entries = {
        str(entry.get("message_id")): entry
        for entry, _envelope, _path in parsed_messages
        if isinstance(entry.get("message_id"), str)
    }
    capture_actions: dict[str, set[str]] = {}
    for event in events:
        if event.get("event_type") != "message-capture":
            continue
        payload = event.get("payload", {})
        if not isinstance(payload, Mapping) or not isinstance(payload.get("message_id"), str):
            continue
        capture_actions.setdefault(str(payload["message_id"]), set()).add(str(payload.get("action", "")))
    statuses = [entry.get("capture_status") for entry in message_entries.values()]
    for message_id, entry in message_entries.items():
        status = entry.get("capture_status")
        gap_event_id = entry.get("capture_gap_event_id")
        if status == "delayed" and "exported-delayed" not in capture_actions.get(message_id, set()):
            risks.append(
                _risk(
                    _RISK_CAPTURE_DELAYED,
                    RiskLevel.BLOCK,
                    f"delayed message {message_id} lacks an exported-delayed capture event",
                    detail="message-delay-event-missing",
                )
            )
        if status in {"partial", "unavailable"}:
            event = event_gap_by_id.get(str(gap_event_id)) if gap_event_id is not None else None
            if event is None:
                risks.append(
                    _risk(
                        _RISK_CAPTURE_DELAYED,
                        RiskLevel.BLOCK,
                        f"message {message_id} has no valid capture-gap event",
                        detail="message-capture-gap-event-missing",
                    )
                )
                continue
            payload = event.get("payload", {})
            if not isinstance(payload, Mapping) or payload.get("affected_stream") != "messages":
                risks.append(
                    _risk(
                        _RISK_CAPTURE_DELAYED,
                        RiskLevel.BLOCK,
                        f"message {message_id} points to a non-message capture gap",
                        detail="message-capture-gap-stream-drift",
                    )
                )
            affected_ids = payload.get("affected_ids", []) if isinstance(payload, Mapping) else []
            if not isinstance(affected_ids, list) or message_id not in affected_ids:
                risks.append(
                    _risk(
                        _RISK_CAPTURE_DELAYED,
                        RiskLevel.BLOCK,
                        f"capture gap {gap_event_id} does not name message {message_id}",
                        detail="message-capture-gap-id-drift",
                    )
                )
        elif gap_event_id is not None:
            risks.append(
                _risk(
                    _RISK_CAPTURE_DELAYED,
                    RiskLevel.BLOCK,
                    f"message {message_id} declares a gap while capture_status is {status!r}",
                    detail="message-capture-status-drift",
                )
            )
        if status != "delayed" and "exported-delayed" in capture_actions.get(message_id, set()):
            risks.append(
                _risk(
                    _RISK_CAPTURE_DELAYED,
                    RiskLevel.BLOCK,
                    f"message {message_id} has exported-delayed event but status {status!r}",
                    detail="message-delay-status-drift",
                )
            )

    for event_id, event in event_gap_by_id.items():
        payload = event.get("payload", {})
        if not isinstance(payload, Mapping) or payload.get("affected_stream") != "messages":
            continue
        affected_ids = payload.get("affected_ids", [])
        if not isinstance(affected_ids, list):
            continue
        for message_id in affected_ids:
            entry = message_entries.get(str(message_id))
            if entry is None:
                continue
            if (
                entry.get("capture_status") not in {"partial", "unavailable"}
                or entry.get("capture_gap_event_id") != event_id
            ):
                risks.append(
                    _risk(
                        _RISK_CAPTURE_DELAYED,
                        RiskLevel.BLOCK,
                        f"capture gap {event_id} and message {message_id} disagree",
                        detail="capture-gap-message-drift",
                    )
                )

    has_gap = bool(event_gaps or index_gaps or any(status in {"partial", "unavailable"} for status in statuses))
    has_delay = any(status == "delayed" for status in statuses)
    expected_completeness = "gapped" if has_gap else "delayed" if has_delay else "complete"
    if index.get("completeness") != expected_completeness:
        risks.append(
            _risk(
                _RISK_CAPTURE_DELAYED,
                RiskLevel.BLOCK,
                f"INDEX completeness is {index.get('completeness')!r}, expected {expected_completeness!r}",
                detail="capture-completeness-drift",
            )
        )
    return has_gap, has_delay
