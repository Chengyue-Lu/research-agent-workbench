"""Sanitized, commit-last Agent Trace bundle generation for API boundaries.

The public API deliberately accepts only trusted identity, lifecycle, actor,
timestamp, and capture-availability metadata.  There is no input slot for a
provider prompt or response, source/tool body, tool arguments/results, native
response identifier, credential, exception detail, or model reasoning.

All material files are published exclusively and ``INDEX.yaml`` is written
last.  A write or verification failure is propagated as ``TraceRecorderError``
without publishing an index for the failed bundle.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Any, Iterable, Mapping

import yaml

from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.io import load_document, write_text_exclusive
from research_workbench.validation.schemas import SchemaCatalog


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_TRACE_ID_RE = re.compile(r"^TRACE-[A-Za-z0-9._-]+$")
_RUNTIME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@:/+-]{0,159}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_SECRET_MARKER_RE = re.compile(
    r"(?:^|[^a-z0-9])(?:authorization|bearer|api[_-]?key|password|credential|secret|"
    r"private[_-]?key|access[_-]?token|refresh[_-]?token)(?:$|[^a-z0-9])",
    re.IGNORECASE,
)
_OWNER_PLACEHOLDERS = {"unknown", "unassigned", "none", "n/a"}
_TERMINAL_STATUSES = {
    "completed",
    "stage-completed",
    "safe-paused",
    "waiting",
    "incomplete",
    "failed",
    "blocked",
    "cancelled",
}


class TraceRecorderError(RuntimeError):
    """The sanitized Trace bundle could not be safely produced."""


class CaptureGapKind(StrEnum):
    """Fixed, non-payload-bearing reasons for an explicit capture gap."""

    PROVIDER_CONTENT = "provider-content-not-retained"
    TOOL_CONTENT = "tool-content-not-retained"
    RUNTIME_EXPORT = "runtime-export-unavailable"
    CAPTURE_FAILURE = "sanitized-capture-failure"


class BoundaryCallStatus(StrEnum):
    """Terminal runtime status with no exception or Provider payload detail."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


_GAP_POLICY: dict[CaptureGapKind, tuple[str, str, str]] = {
    CaptureGapKind.PROVIDER_CONTENT: (
        "messages",
        "policy-omission",
        "Provider boundary content is excluded by Trace policy.",
    ),
    CaptureGapKind.TOOL_CONTENT: (
        "tool-results",
        "policy-omission",
        "Tool argument and result content is excluded by Trace policy.",
    ),
    CaptureGapKind.RUNTIME_EXPORT: (
        "events",
        "platform-unavailable",
        "Sanitized runtime boundary export was unavailable.",
    ),
    CaptureGapKind.CAPTURE_FAILURE: (
        "events",
        "capture-failure",
        "Sanitized boundary capture did not complete.",
    ),
}


@dataclass(frozen=True, slots=True)
class TraceActorMetadata:
    actor_id: str
    actor_type: str
    role: str
    runtime_identity: str
    accountable_owner: str


@dataclass(frozen=True, slots=True)
class TraceCaptureGap:
    kind: CaptureGapKind
    observed_at: str


@dataclass(frozen=True, slots=True)
class FrozenReadMetadata:
    """The only source-specific data allowed on a read-tool boundary."""

    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class FrozenTraceReference:
    """One not-yet-published closeout file frozen by exact bytes and digest."""

    path: str
    sha256: str
    payload: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class ApiTraceMetadata:
    trace_id: str
    task_id: str
    task_revision: int
    attempt_id: str
    baseline: str
    task_path: str
    archive_root: str
    owner_actor_id: str
    coordinator_actor_id: str
    worker_actor_id: str
    actors: tuple[TraceActorMetadata, ...]
    read_allowlist: tuple[str, ...]
    write_scope: tuple[str, ...]
    tool_allowlist: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TraceTimeline:
    started_at: str
    assignment_at: str
    handoff_at: str
    finished_at: str


@dataclass(frozen=True, slots=True)
class TraceBundleResult:
    trace_id: str
    index_path: Path
    index_sha256: str
    message_count: int
    event_count: int
    completeness: str


@dataclass(frozen=True, slots=True)
class FrozenTraceBundle:
    """An ordered, immutable view of Trace-owned bytes ready for closeout staging."""

    trace_id: str
    index_path: str
    index_sha256: str
    payloads: Mapping[str, bytes] = field(repr=False)
    message_count: int
    event_count: int
    completeness: str

    @property
    def index_ref(self) -> FrozenTraceReference:
        """Return the hash-bound in-memory index reference."""

        return FrozenTraceReference(
            self.index_path,
            self.index_sha256,
            self.payloads[self.index_path],
        )


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _yaml_text(document: Mapping[str, Any]) -> str:
    return yaml.safe_dump(dict(document), sort_keys=False, allow_unicode=True)


def _jsonl_text(events: Iterable[Mapping[str, Any]]) -> str:
    return "".join(
        json.dumps(dict(event), ensure_ascii=False, separators=(",", ":")) + "\n"
        for event in events
    )


def _validate_id(label: str, value: str) -> None:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise TraceRecorderError(f"{label} must be a bounded portable identifier")
    _reject_secret_marker(label, value)


def _validate_runtime_identity(value: str) -> None:
    if not isinstance(value, str) or _RUNTIME_RE.fullmatch(value) is None:
        raise TraceRecorderError("runtime_identity must be bounded boundary metadata")
    _reject_secret_marker("runtime_identity", value)


def _validate_owner(value: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise TraceRecorderError("accountable_owner must be a bounded named owner")
    if any(ord(character) < 32 for character in value):
        raise TraceRecorderError("accountable_owner cannot contain control characters")
    if value.strip().casefold() in _OWNER_PLACEHOLDERS:
        raise TraceRecorderError("accountable_owner must identify a named owner")
    _reject_secret_marker("accountable_owner", value)


def _reject_secret_marker(label: str, value: str) -> None:
    if _SECRET_MARKER_RE.search(value):
        raise TraceRecorderError(f"{label} resembles prohibited credential metadata")


def _normalize_relative_path(label: str, value: str) -> str:
    if not isinstance(value, str) or not value:
        raise TraceRecorderError(f"{label} must be a non-empty project-relative path")
    windows_path = PureWindowsPath(value)
    normalized = value.replace("\\", "/")
    posix_path = PurePosixPath(normalized)
    if windows_path.drive or windows_path.root or posix_path.is_absolute():
        raise TraceRecorderError(f"{label} must be project-relative")
    if any(part == ".." for part in normalized.split("/")):
        raise TraceRecorderError(f"{label} cannot escape the project root")
    canonical = posix_path.as_posix().rstrip("/")
    if not canonical or canonical == ".":
        raise TraceRecorderError(f"{label} must resolve beneath the project root")
    return canonical


def _normalize_scope(label: str, value: str) -> str:
    """Accept only an exact path or one terminal ``/**`` descendant scope."""

    if isinstance(value, str) and value.endswith("/**"):
        anchor = _normalize_relative_path(label, value[:-3])
        return f"{anchor}/**"
    normalized = _normalize_relative_path(label, value)
    if "*" in normalized or "?" in normalized:
        raise TraceRecorderError(f"{label} only supports an exact path or terminal /**")
    return normalized


def _scope_allows(scope: str, path: str) -> bool:
    if scope.endswith("/**"):
        anchor = scope[:-3].rstrip("/")
        return path == anchor or path.startswith(anchor + "/")
    return path == scope


def _parse_timestamp(label: str, value: str) -> datetime:
    if not isinstance(value, str):
        raise TraceRecorderError(f"{label} must be an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TraceRecorderError(f"{label} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TraceRecorderError(f"{label} must include a timezone offset")
    return parsed


def _validated_captured_result(value: object) -> Mapping[str, Any]:
    """Return one bounded JSON object suitable for a transient result ref."""

    if not isinstance(value, Mapping):
        raise TraceRecorderError("captured tool result must be a JSON object")
    try:
        text = json.dumps(
            dict(value),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise TraceRecorderError(
            "captured tool result must contain finite JSON data"
        ) from exc
    if len(text.encode("utf-8")) > 65536:
        raise TraceRecorderError("captured tool result exceeds the Trace boundary")
    if _SECRET_MARKER_RE.search(text):
        raise TraceRecorderError(
            "captured tool result resembles prohibited credential metadata"
        )
    parsed = json.loads(text)
    if not isinstance(parsed, Mapping):
        raise TraceRecorderError("captured tool result must remain a JSON object")
    return parsed


def _assert_schema(
    catalog: SchemaCatalog, kind: str, document: Mapping[str, Any]
) -> None:
    errors = catalog.validate(kind, document)
    if errors:
        first = errors[0]
        raise TraceRecorderError(
            f"generated {kind} is invalid at {first.pointer}: {first.message}"
        )


def _actor_mapping(actor: TraceActorMetadata) -> dict[str, Any]:
    return {
        "actor_id": actor.actor_id,
        "actor_type": actor.actor_type,
        "role": actor.role,
        "runtime_identity": actor.runtime_identity,
        "accountable_owner": actor.accountable_owner,
    }


def _message_text(header: Mapping[str, Any], body: str) -> str:
    return "---\n" + _yaml_text(header) + "---\n" + body


class ApiTraceRecorder:
    """A two-phase, sanitized API boundary Trace recorder.

    ``begin`` publishes the assignment before the caller dispatches work.  It
    deliberately does not create ``INDEX.yaml``.  ``seal`` freezes all
    Trace-owned bytes in memory with the index last but publishes no terminal
    material.  ``finalize`` reuses that frozen bundle, writes the terminal
    handoff and ledger, and publishes the index last.  The class never accepts
    transcript or Provider payload data.
    """

    def __init__(self, root: str | Path, metadata: ApiTraceMetadata) -> None:
        self.root = Path(root).resolve()
        self.metadata = metadata
        self._start: dict[str, Any] | None = None
        self._completion_key: tuple[Any, ...] | None = None
        self._result: TraceBundleResult | None = None
        self._sealed_key: tuple[Any, ...] | None = None
        self._sealed_bundle: FrozenTraceBundle | None = None
        self._sealed_references: tuple[tuple[str, str], ...] = ()
        self._boundary_records: list[dict[str, Any]] = []
        self._last_boundary_time: datetime | None = None
        self._next_provider_call = 1
        self._open_provider_calls: dict[int, tuple[str, str]] = {}
        self._completed_provider_calls = 0
        self._next_tool_call = 1
        self._open_tool_calls: dict[int, str] = {}

    @classmethod
    def begin(
        cls,
        root: str | Path,
        metadata: ApiTraceMetadata,
        *,
        started_at: str,
        assignment_at: str,
    ) -> ApiTraceRecorder:
        """Persist a partial, policy-declared assignment before Provider dispatch."""

        recorder = cls(root, metadata)
        recorder._begin(
            started_at=started_at,
            assignment_at=assignment_at,
            capture_status="partial",
            capture_action="persisted-before-send",
        )
        return recorder

    def record_provider_call_started(
        self,
        *,
        occurred_at: str,
        provider_identity: str,
        model: str,
    ) -> int:
        """Persist a Provider-call start without request data or native IDs."""

        _validate_runtime_identity(provider_identity)
        _validate_runtime_identity(model)
        call_number = self._next_provider_call
        document = {
            "schema_version": "0.1.0",
            "boundary_sequence": len(self._boundary_records) + 1,
            "boundary_type": "provider-call-started",
            "occurred_at": occurred_at,
            "actor_id": self.metadata.worker_actor_id,
            "provider_call_number": call_number,
            "provider_identity": provider_identity,
            "model": model,
        }
        self._record_boundary(document)
        self._open_provider_calls[call_number] = (provider_identity, model)
        self._next_provider_call += 1
        return call_number

    def record_provider_call_finished(
        self,
        call_number: int,
        *,
        occurred_at: str,
        status: BoundaryCallStatus,
    ) -> None:
        """Persist a Provider-call end without response or exception details."""

        if call_number not in self._open_provider_calls:
            raise TraceRecorderError("provider call number is not open")
        if not isinstance(status, BoundaryCallStatus):
            raise TraceRecorderError("provider status is outside the fixed vocabulary")
        provider_identity, model = self._open_provider_calls[call_number]
        document = {
            "schema_version": "0.1.0",
            "boundary_sequence": len(self._boundary_records) + 1,
            "boundary_type": "provider-call-finished",
            "occurred_at": occurred_at,
            "actor_id": self.metadata.worker_actor_id,
            "provider_call_number": call_number,
            "provider_identity": provider_identity,
            "model": model,
            "status": status.value,
        }
        self._record_boundary(document)
        del self._open_provider_calls[call_number]
        self._completed_provider_calls += 1

    def record_tool_call_started(
        self,
        *,
        occurred_at: str,
        tool_name: str,
    ) -> int:
        """Persist a tool-call start without arguments or Provider call IDs."""

        _validate_id("tool_name", tool_name)
        if self._start is None or tool_name not in self._start["tool_allowlist"]:
            raise TraceRecorderError("tool call is outside the frozen Trace allowlist")
        call_number = self._next_tool_call
        document = {
            "schema_version": "0.1.0",
            "boundary_sequence": len(self._boundary_records) + 1,
            "boundary_type": "tool-call-started",
            "occurred_at": occurred_at,
            "actor_id": self.metadata.worker_actor_id,
            "tool_call_number": call_number,
            "tool_name": tool_name,
        }
        self._record_boundary(document)
        self._open_tool_calls[call_number] = tool_name
        self._next_tool_call += 1
        return call_number

    def record_tool_call_finished(
        self,
        call_number: int,
        *,
        occurred_at: str,
        status: BoundaryCallStatus,
        result_char_count: int,
        result_entered_context: bool = True,
        frozen_read: FrozenReadMetadata | None = None,
        captured_result: object | None = None,
    ) -> None:
        """Persist only terminal tool metadata and optional frozen read identity."""

        tool_name = self._open_tool_calls.get(call_number)
        if tool_name is None:
            raise TraceRecorderError("tool call number is not open")
        if not isinstance(status, BoundaryCallStatus):
            raise TraceRecorderError("tool status is outside the fixed vocabulary")
        if (
            not isinstance(result_char_count, int)
            or isinstance(result_char_count, bool)
            or result_char_count < 0
        ):
            raise TraceRecorderError("result_char_count must be a non-negative integer")
        if not isinstance(result_entered_context, bool):
            raise TraceRecorderError("result_entered_context must be boolean")
        if frozen_read is not None and captured_result is not None:
            raise TraceRecorderError("tool result cannot be both stable and transient")
        if result_entered_context and frozen_read is None and captured_result is None:
            raise TraceRecorderError(
                "a tool result entering context requires a stable or captured result"
            )
        document: dict[str, Any] = {
            "schema_version": "0.1.0",
            "boundary_sequence": len(self._boundary_records) + 1,
            "boundary_type": "tool-call-finished",
            "occurred_at": occurred_at,
            "actor_id": self.metadata.worker_actor_id,
            "tool_call_number": call_number,
            "tool_name": tool_name,
            "status": status.value,
            "result_char_count": result_char_count,
            "result_entered_context": result_entered_context,
        }
        if frozen_read is not None:
            document["frozen_read"] = self._validated_frozen_read(frozen_read)
        if captured_result is not None:
            document["captured_result"] = dict(
                _validated_captured_result(captured_result)
            )
        self._record_boundary(document)
        del self._open_tool_calls[call_number]

    def seal(
        self,
        *,
        attempt_status: str,
        handoff_at: str,
        finished_at: str,
        capture_gaps: Iterable[TraceCaptureGap] = (),
        handoff_refs: Iterable[FrozenTraceReference] = (),
        decision_refs: Iterable[FrozenTraceReference] = (),
        output_refs: Iterable[FrozenTraceReference] = (),
        check_refs: Iterable[FrozenTraceReference] = (),
    ) -> FrozenTraceBundle:
        """Freeze terminal Trace bytes without publishing terminal files or the index."""

        if self._start is None:
            raise TraceRecorderError("Trace assignment must be begun before sealing")
        if self._open_provider_calls or self._open_tool_calls:
            raise TraceRecorderError("runtime boundary call is still open")
        self._verify_started_boundary()
        gaps = self._terminal_gaps(tuple(capture_gaps), handoff_at)
        reference_groups, frozen_references = self._validated_closeout_references(
            handoff_refs=tuple(handoff_refs),
            decision_refs=tuple(decision_refs),
            output_refs=tuple(output_refs),
            check_refs=tuple(check_refs),
        )
        completion_key = self._completion_identity(
            attempt_status,
            handoff_at,
            finished_at,
            gaps,
            reference_groups,
        )
        if self._sealed_bundle is not None:
            if completion_key != self._sealed_key:
                raise TraceRecorderError(
                    "Trace was already sealed with different terminal metadata or references"
                )
            return self._sealed_bundle
        runtime_gap_declared = any(
            gap.kind in {CaptureGapKind.RUNTIME_EXPORT, CaptureGapKind.CAPTURE_FAILURE}
            for gap in gaps
        )
        if self._completed_provider_calls == 0 and not runtime_gap_declared:
            raise TraceRecorderError(
                "Provider boundaries are absent and no runtime capture gap is declared"
            )

        prepared = self._prepare_final(
            attempt_status=attempt_status,
            handoff_at=handoff_at,
            finished_at=finished_at,
            capture_gaps=gaps,
            closeout_refs=reference_groups,
        )
        payloads = self._frozen_trace_payloads(prepared)
        index_relative = f"{self._start['archive_root']}/INDEX.yaml"
        bundle = FrozenTraceBundle(
            trace_id=self.metadata.trace_id,
            index_path=index_relative,
            index_sha256=prepared["index_sha256"],
            payloads=MappingProxyType(payloads),
            message_count=2,
            event_count=len(prepared["events"]),
            completeness=prepared["index"]["completeness"],
        )
        self._sealed_key = completion_key
        self._sealed_bundle = bundle
        self._sealed_references = frozen_references
        return bundle

    def finalize(
        self,
        *,
        attempt_status: str,
        handoff_at: str,
        finished_at: str,
        capture_gaps: Iterable[TraceCaptureGap] = (),
        handoff_refs: Iterable[FrozenTraceReference] = (),
        decision_refs: Iterable[FrozenTraceReference] = (),
        output_refs: Iterable[FrozenTraceReference] = (),
        check_refs: Iterable[FrozenTraceReference] = (),
    ) -> TraceBundleResult:
        """Seal and publish the terminal files, with ``INDEX.yaml`` committed last."""

        bundle = self.seal(
            attempt_status=attempt_status,
            handoff_at=handoff_at,
            finished_at=finished_at,
            capture_gaps=capture_gaps,
            handoff_refs=handoff_refs,
            decision_refs=decision_refs,
            output_refs=output_refs,
            check_refs=check_refs,
        )
        if self._result is not None:
            if self._completion_key != self._sealed_key:
                raise TraceRecorderError(
                    "Trace was already finalized with different terminal identity"
                )
            try:
                intact = (
                    self._result.index_path.is_file()
                    and hash_file(self._result.index_path) == self._result.index_sha256
                )
            except OSError:
                intact = False
            if not intact:
                raise TraceRecorderError("finalized Trace index is missing or drifted")
            return self._result
        self._verify_live_closeout_references()
        ordered_paths = tuple(bundle.payloads)
        if not ordered_paths or ordered_paths[-1] != bundle.index_path:
            raise TraceRecorderError("frozen Trace payload order lacks a final index")
        for relative in ordered_paths[:-1]:
            self._publish_or_verify_bytes(relative, bundle.payloads[relative])
        self._verify_live_closeout_references()
        self._publish_index_bytes(
            bundle.index_path,
            bundle.payloads[bundle.index_path],
            bundle.index_sha256,
        )
        result = TraceBundleResult(
            trace_id=bundle.trace_id,
            index_path=self.root.joinpath(*PurePosixPath(bundle.index_path).parts),
            index_sha256=bundle.index_sha256,
            message_count=bundle.message_count,
            event_count=bundle.event_count,
            completeness=bundle.completeness,
        )
        self._completion_key = self._sealed_key
        self._result = result
        return result

    def _begin(
        self,
        *,
        started_at: str,
        assignment_at: str,
        capture_status: str,
        capture_action: str,
    ) -> None:
        if self._start is not None:
            raise TraceRecorderError("Trace assignment boundary was already begun")
        prepared = self._prepare_start(
            started_at=started_at,
            assignment_at=assignment_at,
            capture_status=capture_status,
            capture_action=capture_action,
        )
        archive_path: Path = prepared["archive_path"]
        actors_path: Path = prepared["actors_path"]
        assignment_path: Path = prepared["assignment_path"]
        messages_path = archive_path / "messages"
        runtime_path = archive_path / "tool-events"
        handoff_path = messages_path / self._message_filename(
            2,
            self.metadata.worker_actor_id,
            self.metadata.coordinator_actor_id,
            "handoff",
        )
        reserved = (
            actors_path,
            assignment_path,
            handoff_path,
            archive_path / "events.jsonl",
            archive_path / "INDEX.yaml",
        )
        if any(path.exists() for path in reserved):
            raise TraceRecorderError(
                "Trace target contains a reserved boundary artifact"
            )
        self._ensure_messages_directory(archive_path, messages_path)
        self._ensure_runtime_directory(archive_path, runtime_path)
        self._publish_verified(
            actors_path,
            prepared["actors_text"],
            prepared["actors_sha256"],
        )
        self._publish_verified(
            assignment_path,
            prepared["assignment"]["text"],
            prepared["assignment"]["sha256"],
        )
        self._start = prepared
        self._last_boundary_time = prepared["assignment_time"]

    @staticmethod
    def _ensure_messages_directory(archive_path: Path, messages_path: Path) -> None:
        if messages_path.exists():
            if not messages_path.is_dir():
                raise TraceRecorderError("Trace messages target is not a directory")
            if any(messages_path.iterdir()):
                raise TraceRecorderError("Trace messages directory is not empty")
        try:
            messages_path.mkdir(parents=True, exist_ok=True)
            resolved = messages_path.resolve()
            resolved.relative_to(archive_path)
        except (OSError, ValueError) as exc:
            raise TraceRecorderError(
                "Trace messages directory creation or confinement failed"
            ) from exc
        if resolved != messages_path.absolute():
            raise TraceRecorderError(
                "Trace messages directory cannot be a link or junction"
            )

    @staticmethod
    def _ensure_runtime_directory(archive_path: Path, runtime_path: Path) -> None:
        if runtime_path.exists():
            if not runtime_path.is_dir():
                raise TraceRecorderError("Trace runtime target is not a directory")
            if any(runtime_path.iterdir()):
                raise TraceRecorderError("Trace runtime directory is not empty")
        try:
            runtime_path.mkdir(parents=True, exist_ok=True)
            resolved = runtime_path.resolve()
            resolved.relative_to(archive_path)
        except (OSError, ValueError) as exc:
            raise TraceRecorderError(
                "Trace runtime directory creation or confinement failed"
            ) from exc
        if resolved != runtime_path.absolute():
            raise TraceRecorderError(
                "Trace runtime directory cannot be a link or junction"
            )

    def _record_boundary(self, document: dict[str, Any]) -> None:
        if self._start is None:
            raise TraceRecorderError(
                "Trace assignment must be begun before runtime capture"
            )
        self._verify_recorder_identity()
        if self._sealed_bundle is not None:
            raise TraceRecorderError("runtime capture cannot continue after sealing")
        occurred_at = document.get("occurred_at")
        observed = _parse_timestamp("runtime boundary occurred_at", occurred_at)
        if self._last_boundary_time is not None and observed < self._last_boundary_time:
            raise TraceRecorderError("runtime boundary timestamps must be monotonic")
        sequence = len(self._boundary_records) + 1
        if document.get("boundary_sequence") != sequence:
            raise TraceRecorderError("runtime boundary sequence is not contiguous")
        boundary_type = document.get("boundary_type")
        if not isinstance(boundary_type, str):
            raise TraceRecorderError("runtime boundary type is unavailable")
        filename = f"{sequence:04d}-{boundary_type}.json"
        relative = f"{self._start['archive_root']}/tool-events/{filename}"
        path = self._start["archive_path"] / "tool-events" / filename
        text = (
            json.dumps(
                document,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        )
        digest = _sha256_bytes(text.encode("utf-8"))
        self._publish_verified(path, text, digest)
        self._boundary_records.append(
            {
                "document": document,
                "path": relative,
                "file_path": path,
                "sha256": digest,
                "occurred_time": observed,
            }
        )
        self._last_boundary_time = observed

    def _validated_frozen_read(
        self,
        frozen_read: FrozenReadMetadata,
    ) -> dict[str, str]:
        if not isinstance(frozen_read, FrozenReadMetadata):
            raise TraceRecorderError("frozen_read must be FrozenReadMetadata")
        relative = _normalize_relative_path("frozen read path", frozen_read.path)
        normalized_hash = frozen_read.sha256.lower().removeprefix("sha256:")
        if _SHA256_RE.fullmatch(normalized_hash) is None:
            raise TraceRecorderError("frozen read sha256 must be a SHA-256 digest")
        path = resolve_within_root(self.root, relative)
        try:
            intact = (
                path is not None
                and path.is_file()
                and hash_file(path) == normalized_hash
            )
        except OSError:
            intact = False
        if not intact:
            raise TraceRecorderError(
                "frozen read path or hash does not match live bytes"
            )
        if self._start is None or not any(
            _scope_allows(scope, relative) for scope in self._start["read_allowlist"]
        ):
            raise TraceRecorderError(
                "frozen read is outside the pre-dispatch allowlist"
            )
        return {"path": relative, "sha256": normalized_hash}

    @staticmethod
    def _publish_verified(path: Path, content: str, expected_hash: str) -> None:
        try:
            created = write_text_exclusive(path, content)
        except Exception as exc:
            raise TraceRecorderError(
                "Trace boundary artifact publication failed"
            ) from exc
        try:
            verified = created and path.is_file() and hash_file(path) == expected_hash
        except OSError:
            verified = False
        if not verified:
            raise TraceRecorderError("Trace boundary artifact verification failed")

    @staticmethod
    def _publish_index(path: Path, content: str, expected_hash: str) -> None:
        """Publish the commit marker without a fallible post-commit return step."""

        try:
            created = write_text_exclusive(path, content)
        except Exception as exc:
            try:
                committed = path.is_file() and hash_file(path) == expected_hash
            except OSError:
                committed = False
            if committed:
                return
            raise TraceRecorderError("Trace index publication failed") from exc
        try:
            verified = created and path.is_file() and hash_file(path) == expected_hash
        except OSError:
            verified = False
        if verified:
            return
        if created:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise TraceRecorderError("Trace index publication failed")

    def _terminal_gaps(
        self,
        supplied_gaps: tuple[TraceCaptureGap, ...],
        handoff_at: str,
    ) -> tuple[TraceCaptureGap, ...]:
        if self._start is None:
            raise TraceRecorderError("Trace assignment must be begun before sealing")
        for gap in supplied_gaps:
            if not isinstance(gap, TraceCaptureGap):
                raise TraceRecorderError("capture gap must be TraceCaptureGap metadata")
        gaps = tuple(
            gap for gap in supplied_gaps if gap.kind != CaptureGapKind.PROVIDER_CONTENT
        ) + (
            TraceCaptureGap(
                CaptureGapKind.PROVIDER_CONTENT,
                self._start["assignment_at"],
            ),
        )
        if self._next_tool_call > 1 and not any(
            gap.kind == CaptureGapKind.TOOL_CONTENT for gap in gaps
        ):
            gaps += (TraceCaptureGap(CaptureGapKind.TOOL_CONTENT, handoff_at),)
        return gaps

    def _validated_closeout_references(
        self,
        *,
        handoff_refs: tuple[FrozenTraceReference, ...],
        decision_refs: tuple[FrozenTraceReference, ...],
        output_refs: tuple[FrozenTraceReference, ...],
        check_refs: tuple[FrozenTraceReference, ...],
    ) -> tuple[dict[str, tuple[dict[str, str], ...]], tuple[tuple[str, str], ...]]:
        if self._start is None:
            raise TraceRecorderError("Trace assignment must be begun before sealing")
        archive_root = self._start["archive_root"]
        trace_namespaces = (
            f"{archive_root}/messages/",
            f"{archive_root}/tool-events/",
        )
        trace_paths = {
            f"{archive_root}/ACTORS.yaml",
            f"{archive_root}/events.jsonl",
            f"{archive_root}/INDEX.yaml",
        }
        trace_path_keys = {path.casefold() for path in trace_paths}
        trace_namespace_keys = tuple(
            namespace.casefold() for namespace in trace_namespaces
        )
        seen_paths: dict[str, tuple[str, str]] = {}
        groups: dict[str, tuple[dict[str, str], ...]] = {}
        normalized_references: list[tuple[str, str]] = []
        for field_name, references in (
            ("handoff_refs", handoff_refs),
            ("decision_refs", decision_refs),
            ("output_refs", output_refs),
            ("check_refs", check_refs),
        ):
            entries: list[tuple[str, tuple[str, str], dict[str, str]]] = []
            for reference in references:
                if not isinstance(reference, FrozenTraceReference):
                    raise TraceRecorderError(
                        f"{field_name} must contain FrozenTraceReference values"
                    )
                relative = _normalize_relative_path(
                    f"{field_name} path",
                    reference.path,
                )
                if relative != reference.path:
                    raise TraceRecorderError(
                        f"{field_name} path must be canonical project-relative metadata"
                    )
                if not relative.startswith(archive_root.rstrip("/") + "/"):
                    raise TraceRecorderError(
                        f"{field_name} path must stay within the Attempt archive"
                    )
                portable_path = relative.casefold()
                if portable_path in trace_path_keys or any(
                    portable_path.startswith(namespace)
                    for namespace in trace_namespace_keys
                ):
                    raise TraceRecorderError(
                        f"{field_name} path collides with Trace-owned material"
                    )
                if portable_path in seen_paths:
                    prior_field, prior_path = seen_paths[portable_path]
                    raise TraceRecorderError(
                        f"duplicate closeout reference path in {prior_field} and "
                        f"{field_name}: {prior_path} / {relative}"
                    )
                if not isinstance(reference.sha256, str):
                    raise TraceRecorderError(
                        f"{field_name} reference sha256 must be a SHA-256 digest"
                    )
                digest = reference.sha256.lower().removeprefix("sha256:")
                if _SHA256_RE.fullmatch(digest) is None:
                    raise TraceRecorderError(
                        f"{field_name} reference sha256 must be a SHA-256 digest"
                    )
                if not isinstance(reference.payload, bytes):
                    raise TraceRecorderError(
                        f"{field_name} reference payload must be frozen bytes"
                    )
                if _sha256_bytes(reference.payload) != digest:
                    raise TraceRecorderError(
                        f"{field_name} reference payload differs from its sha256"
                    )
                if not any(
                    _scope_allows(scope, relative)
                    for scope in self._start["write_scope"]
                ):
                    raise TraceRecorderError(
                        f"{field_name} reference is outside the frozen write_scope"
                    )
                literal = self._confined_literal_path(field_name, relative)
                if literal.exists():
                    try:
                        intact = (
                            literal.is_file()
                            and not literal.is_symlink()
                            and literal.read_bytes() == reference.payload
                        )
                    except OSError:
                        intact = False
                    if not intact:
                        raise TraceRecorderError(
                            f"{field_name} reference differs from existing project bytes"
                        )
                normalized = (relative, digest)
                entry = {"path": relative, "sha256": digest}
                entries.append((relative, normalized, entry))
                seen_paths[portable_path] = (field_name, relative)
            entries.sort(key=lambda item: item[0])
            groups[field_name] = tuple(entry for _, _, entry in entries)
            normalized_references.extend(reference for _, reference, _ in entries)
        return groups, tuple(normalized_references)

    def _confined_literal_path(self, label: str, relative: str) -> Path:
        literal = self.root.joinpath(*PurePosixPath(relative).parts).absolute()
        resolved = resolve_within_root(self.root, relative)
        if resolved is None or resolved != literal:
            raise TraceRecorderError(f"{label} path escapes through a link or junction")
        return literal

    def _frozen_trace_payloads(self, prepared: Mapping[str, Any]) -> dict[str, bytes]:
        if self._start is None:
            raise TraceRecorderError("Trace assignment must be begun before sealing")
        payloads: dict[str, bytes] = {}

        def add(relative: str, payload: bytes, expected_hash: str) -> None:
            if relative in payloads:
                raise TraceRecorderError(
                    f"duplicate frozen Trace payload path: {relative}"
                )
            if _sha256_bytes(payload) != expected_hash:
                raise TraceRecorderError(
                    f"frozen Trace payload hash drifted: {relative}"
                )
            payloads[relative] = payload

        add(
            f"{self._start['archive_root']}/ACTORS.yaml",
            self._read_verified_bytes(
                self._start["actors_path"],
                self._start["actors_sha256"],
                "actor registry",
            ),
            self._start["actors_sha256"],
        )
        add(
            self._start["assignment"]["path"],
            self._read_verified_bytes(
                self._start["assignment_path"],
                self._start["assignment"]["sha256"],
                "assignment boundary",
            ),
            self._start["assignment"]["sha256"],
        )
        for record in self._boundary_records:
            add(
                record["path"],
                self._read_verified_bytes(
                    record["file_path"],
                    record["sha256"],
                    "runtime boundary record",
                ),
                record["sha256"],
            )
        add(
            prepared["handoff"]["path"],
            prepared["handoff"]["text"].encode("utf-8"),
            prepared["handoff"]["sha256"],
        )
        add(
            f"{self._start['archive_root']}/events.jsonl",
            prepared["events_text"].encode("utf-8"),
            prepared["events_sha256"],
        )
        add(
            f"{self._start['archive_root']}/INDEX.yaml",
            prepared["index_text"].encode("utf-8"),
            prepared["index_sha256"],
        )
        return payloads

    @staticmethod
    def _read_verified_bytes(path: Path, expected_hash: str, label: str) -> bytes:
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise TraceRecorderError(
                f"{label} is unavailable during Trace sealing"
            ) from exc
        if _sha256_bytes(payload) != expected_hash:
            raise TraceRecorderError(f"{label} changed during Trace sealing")
        return payload

    def _verify_live_closeout_references(self) -> None:
        for relative, expected_hash in self._sealed_references:
            literal = self._confined_literal_path("closeout reference", relative)
            try:
                intact = literal.is_file() and not literal.is_symlink()
                if intact:
                    intact = _sha256_bytes(literal.read_bytes()) == expected_hash
            except OSError:
                intact = False
            if not intact:
                raise TraceRecorderError(
                    f"closeout reference is not published at finalization: {relative}"
                )

    def _publish_or_verify_bytes(self, relative: str, payload: bytes) -> None:
        path = self._confined_literal_path("Trace payload", relative)
        expected_hash = _sha256_bytes(payload)
        if path.exists():
            try:
                intact = (
                    path.is_file()
                    and not path.is_symlink()
                    and path.read_bytes() == payload
                )
            except OSError:
                intact = False
            if intact:
                return
            raise TraceRecorderError(f"Trace terminal artifact drifted: {relative}")
        try:
            content = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TraceRecorderError("Trace payload is not UTF-8 text") from exc
        self._publish_verified(path, content, expected_hash)

    def _publish_index_bytes(
        self,
        relative: str,
        payload: bytes,
        expected_hash: str,
    ) -> None:
        path = self._confined_literal_path("Trace index", relative)
        if path.exists():
            try:
                intact = (
                    path.is_file()
                    and not path.is_symlink()
                    and path.read_bytes() == payload
                    and hash_file(path) == expected_hash
                )
            except OSError:
                intact = False
            if intact:
                return
            raise TraceRecorderError("Trace index already exists with different bytes")
        try:
            content = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TraceRecorderError("Trace index payload is not UTF-8 text") from exc
        self._publish_index(path, content, expected_hash)

    def _prepare_start(
        self,
        *,
        started_at: str,
        assignment_at: str,
        capture_status: str,
        capture_action: str,
    ) -> dict[str, Any]:
        metadata = self.metadata
        _validate_id("task_id", metadata.task_id)
        _validate_id("attempt_id", metadata.attempt_id)
        _validate_id("owner_actor_id", metadata.owner_actor_id)
        _validate_id("coordinator_actor_id", metadata.coordinator_actor_id)
        _validate_id("worker_actor_id", metadata.worker_actor_id)
        if _TRACE_ID_RE.fullmatch(metadata.trace_id) is None:
            raise TraceRecorderError("trace_id must begin with TRACE- and be portable")
        _reject_secret_marker("trace_id", metadata.trace_id)
        if not isinstance(metadata.task_revision, int) or metadata.task_revision < 1:
            raise TraceRecorderError("task_revision must be a positive integer")
        _validate_runtime_identity(metadata.baseline)
        task_relative = _normalize_relative_path("task_path", metadata.task_path)
        archive_root = _normalize_relative_path("archive_root", metadata.archive_root)
        read_allowlist = tuple(
            _normalize_scope(f"read_allowlist[{index}]", item)
            for index, item in enumerate(metadata.read_allowlist)
        )
        write_scope = tuple(
            _normalize_scope(f"write_scope[{index}]", item)
            for index, item in enumerate(metadata.write_scope)
        )
        tool_allowlist = tuple(metadata.tool_allowlist)
        if not read_allowlist or len(read_allowlist) != len(set(read_allowlist)):
            raise TraceRecorderError("read_allowlist must contain unique frozen scopes")
        if not write_scope or len(write_scope) != len(set(write_scope)):
            raise TraceRecorderError("write_scope must contain unique frozen scopes")
        if len(tool_allowlist) != len(set(tool_allowlist)):
            raise TraceRecorderError("tool_allowlist must not repeat a tool")
        for tool_name in tool_allowlist:
            _validate_id("tool_allowlist item", tool_name)
        if task_relative not in read_allowlist:
            raise TraceRecorderError("read_allowlist must include the frozen Task path")
        if not any(_scope_allows(scope, archive_root) for scope in write_scope):
            raise TraceRecorderError(
                "archive_root is outside the frozen Task write_scope"
            )
        archive_path = resolve_within_root(self.root, archive_root)
        task_path = resolve_within_root(self.root, task_relative)
        literal_archive = self.root.joinpath(
            *PurePosixPath(archive_root).parts
        ).absolute()
        if (
            archive_path is None
            or archive_path == self.root
            or literal_archive != archive_path
        ):
            raise TraceRecorderError(
                "archive_root must be a direct path beneath the project root"
            )
        if task_path is None or not task_path.is_file():
            raise TraceRecorderError(
                "trusted Task reference does not exist within the project root"
            )
        try:
            task_document = load_document(task_path)
        except Exception as exc:
            raise TraceRecorderError("trusted Task reference is not readable") from exc
        if not isinstance(task_document, Mapping):
            raise TraceRecorderError("trusted Task reference must contain an object")
        if (
            task_document.get("task_id") != metadata.task_id
            or task_document.get("revision", 1) != metadata.task_revision
        ):
            raise TraceRecorderError(
                "trusted Task identity or revision differs from Trace metadata"
            )

        start_time = _parse_timestamp("started_at", started_at)
        assignment_time = _parse_timestamp("assignment_at", assignment_at)
        if start_time > assignment_time:
            raise TraceRecorderError("Trace start must not follow assignment")
        if capture_status not in {"complete", "delayed", "partial", "unavailable"}:
            raise TraceRecorderError("boundary capture status is unsupported")
        if capture_action not in {"persisted-before-send", "exported-delayed"}:
            raise TraceRecorderError("boundary capture action is unsupported")

        actor_records = self._validate_actors()
        catalog = SchemaCatalog()
        actor_document: dict[str, Any] = {
            "schema_version": "0.1.0",
            "task_id": metadata.task_id,
            "task_revision": metadata.task_revision,
            "attempt_id": metadata.attempt_id,
            "actors": [
                _actor_mapping(actor)
                for actor in sorted(metadata.actors, key=lambda item: item.actor_id)
            ],
        }
        _assert_schema(catalog, "agent_trace_actors", actor_document)
        actors_text = _yaml_text(actor_document)
        actors_sha256 = _sha256_bytes(actors_text.encode("utf-8"))

        assignment_body = (
            f"Assignment boundary recorded for task {metadata.task_id}@"
            f"{metadata.task_revision}; attempt {metadata.attempt_id}.\n"
        )
        assignment = self._build_message(
            sequence=1,
            kind="assignment",
            sender=metadata.coordinator_actor_id,
            receiver=metadata.worker_actor_id,
            owner=actor_records[metadata.coordinator_actor_id]["accountable_owner"],
            created_at=assignment_at,
            body=assignment_body,
            archive_root=archive_root,
            catalog=catalog,
            capture_status=capture_status,
            capture_gap_event_id="EVT-0001",
        )
        return {
            "root": self.root,
            "metadata": metadata,
            "archive_root": archive_root,
            "archive_path": archive_path,
            "task_relative": task_relative,
            "task_path": task_path,
            "task_sha256": hash_file(task_path),
            "actor_records": actor_records,
            "owner": actor_records[metadata.owner_actor_id]["accountable_owner"],
            "actors_path": archive_path / "ACTORS.yaml",
            "actors_text": actors_text,
            "actors_sha256": actors_sha256,
            "assignment": assignment,
            "assignment_path": archive_path / "messages" / assignment["filename"],
            "started_at": started_at,
            "start_time": start_time,
            "assignment_at": assignment_at,
            "assignment_time": assignment_time,
            "capture_status": capture_status,
            "capture_action": capture_action,
            "read_allowlist": read_allowlist,
            "write_scope": write_scope,
            "tool_allowlist": tool_allowlist,
            "catalog": catalog,
        }

    def _prepare_final(
        self,
        *,
        attempt_status: str,
        handoff_at: str,
        finished_at: str,
        capture_gaps: tuple[TraceCaptureGap, ...],
        closeout_refs: Mapping[str, tuple[dict[str, str], ...]],
    ) -> dict[str, Any]:
        if self._start is None:
            raise TraceRecorderError(
                "Trace assignment must be begun before finalization"
            )
        start = self._start
        metadata = self.metadata
        if attempt_status not in _TERMINAL_STATUSES:
            raise TraceRecorderError(
                "a frozen API Trace requires a terminal attempt_status"
            )
        handoff_time = _parse_timestamp("handoff_at", handoff_at)
        finished_time = _parse_timestamp("finished_at", finished_at)
        if not start["assignment_time"] <= handoff_time <= finished_time:
            raise TraceRecorderError("Trace finalization timeline must be monotonic")
        if (
            self._last_boundary_time is not None
            and self._last_boundary_time > handoff_time
        ):
            raise TraceRecorderError("runtime boundaries cannot follow the handoff")
        timeline = {
            "assignment_at": start["assignment_time"],
            "handoff_at": handoff_time,
        }
        sorted_gaps = self._validated_gaps(capture_gaps, timeline)
        catalog: SchemaCatalog = start["catalog"]
        actor_records: dict[str, dict[str, Any]] = start["actor_records"]

        handoff_body = (
            f"Handoff boundary recorded for attempt {metadata.attempt_id}; "
            f"status {attempt_status}.\n"
        )
        handoff = self._build_message(
            sequence=2,
            kind="handoff",
            sender=metadata.worker_actor_id,
            receiver=metadata.coordinator_actor_id,
            owner=actor_records[metadata.worker_actor_id]["accountable_owner"],
            created_at=handoff_at,
            body=handoff_body,
            archive_root=start["archive_root"],
            catalog=catalog,
            capture_status=start["capture_status"],
            capture_gap_event_id="EVT-0001",
            in_reply_to="MSG-0001",
        )

        events: list[dict[str, Any]] = []

        def add_event(
            event_type: str,
            actor_id: str,
            occurred_at: str,
            payload: dict[str, Any],
        ) -> dict[str, Any]:
            sequence = len(events) + 1
            event = {
                "schema_version": "0.1.0",
                "event_id": f"EVT-{sequence:04d}",
                "task_id": metadata.task_id,
                "task_revision": metadata.task_revision,
                "attempt_id": metadata.attempt_id,
                "sequence": sequence,
                "event_type": event_type,
                "actor_id": actor_id,
                "occurred_at": occurred_at,
                "payload": payload,
            }
            _assert_schema(catalog, "agent_trace_event", event)
            events.append(event)
            return event

        capture_gap_entries: list[dict[str, Any]] = []
        provider_content_gaps = [
            gap for gap in sorted_gaps if gap.kind == CaptureGapKind.PROVIDER_CONTENT
        ]
        if len(provider_content_gaps) != 1:
            raise TraceRecorderError(
                "message capture requires one Provider-content gap"
            )
        provider_gap = provider_content_gaps[0]
        affected_stream, reason_category, reason = _GAP_POLICY[provider_gap.kind]
        provider_gap_event = add_event(
            "capture-gap",
            metadata.owner_actor_id,
            provider_gap.observed_at,
            {
                "affected_stream": affected_stream,
                "reason_category": reason_category,
                "reason": reason,
            },
        )
        capture_gap_entries.append(
            {
                "event_id": provider_gap_event["event_id"],
                "affected_stream": affected_stream,
            }
        )
        add_event(
            "attempt-status",
            metadata.coordinator_actor_id,
            start["started_at"],
            {
                "to_status": "running",
                "reason": "sanitized API boundary recording started",
            },
        )
        add_event(
            "file-revision",
            metadata.coordinator_actor_id,
            start["assignment_at"],
            {
                "path": start["assignment"]["path"],
                "action": "created",
                "new_sha256": start["assignment"]["sha256"],
                "new_revision": 1,
            },
        )
        add_event(
            "message-capture",
            metadata.coordinator_actor_id,
            start["assignment_at"],
            {"message_id": "MSG-0001", "action": start["capture_action"]},
        )
        provider_started_at: dict[int, str] = {}
        tool_started_at: dict[int, str] = {}
        runtime_items = [
            (
                record["occurred_time"],
                0,
                record["document"]["boundary_sequence"],
                "boundary",
                record,
            )
            for record in self._boundary_records
        ]
        gap_items = [
            (
                _parse_timestamp("capture gap observed_at", gap.observed_at),
                1,
                index,
                "gap",
                gap,
            )
            for index, gap in enumerate(
                (
                    gap
                    for gap in sorted_gaps
                    if gap.kind != CaptureGapKind.PROVIDER_CONTENT
                ),
                start=1,
            )
        ]
        for _time, _priority, _sequence, item_type, item in sorted(
            [*runtime_items, *gap_items],
            key=lambda entry: (entry[0], entry[1], entry[2]),
        ):
            if item_type == "boundary":
                record = item
                document = record["document"]
                add_event(
                    "file-revision",
                    document["actor_id"],
                    document["occurred_at"],
                    {
                        "path": record["path"],
                        "action": "created",
                        "new_sha256": record["sha256"],
                        "new_revision": 1,
                    },
                )
                boundary_type = document["boundary_type"]
                if boundary_type == "provider-call-started":
                    call_number = int(document["provider_call_number"])
                    provider_started_at[call_number] = str(document["occurred_at"])
                    add_event(
                        "external-action",
                        document["actor_id"],
                        document["occurred_at"],
                        {
                            "action_id": f"provider-call-{call_number}",
                            "target_category": "model-provider",
                            "authorization_basis": "MODEL-ASSIGNMENT",
                            "side_effect_status": "started",
                        },
                    )
                elif boundary_type == "provider-call-finished":
                    call_number = int(document["provider_call_number"])
                    if call_number not in provider_started_at:
                        raise TraceRecorderError(
                            "Provider finish lacks a prior start boundary"
                        )
                    add_event(
                        "external-action",
                        document["actor_id"],
                        document["occurred_at"],
                        {
                            "action_id": f"provider-call-{call_number}",
                            "target_category": "model-provider",
                            "authorization_basis": "MODEL-ASSIGNMENT",
                            "side_effect_status": document["status"],
                        },
                    )
                elif boundary_type == "tool-call-started":
                    call_number = int(document["tool_call_number"])
                    tool_started_at[call_number] = str(document["occurred_at"])
                    add_event(
                        "tool-call",
                        document["actor_id"],
                        document["occurred_at"],
                        {
                            "operation_id": f"tool-call-{call_number}",
                            "tool_name": document["tool_name"],
                            "allowlist_basis": "TASK",
                            "status": "started",
                            "started_at": document["occurred_at"],
                            "arguments": {},
                            "redactions": [],
                            "result_entered_context": False,
                        },
                    )
                elif boundary_type == "tool-call-finished":
                    call_number = int(document["tool_call_number"])
                    started_at = tool_started_at.get(call_number)
                    if started_at is None:
                        raise TraceRecorderError(
                            "Tool finish lacks a prior start boundary"
                        )
                    result_entered = bool(document["result_entered_context"])
                    tool_payload: dict[str, Any] = {
                        "operation_id": f"tool-call-{call_number}",
                        "tool_name": document["tool_name"],
                        "allowlist_basis": "TASK",
                        "status": document["status"],
                        "started_at": started_at,
                        "finished_at": document["occurred_at"],
                        "arguments": {},
                        "redactions": [],
                        "result_entered_context": result_entered,
                    }
                    if result_entered:
                        frozen_read = document.get("frozen_read")
                        if isinstance(frozen_read, Mapping):
                            tool_payload.update(
                                {
                                    "result_origin": "stable-source",
                                    "result_ref": {
                                        "path": frozen_read["path"],
                                        "sha256": frozen_read["sha256"],
                                    },
                                }
                            )
                        elif isinstance(document.get("captured_result"), Mapping):
                            tool_payload.update(
                                {
                                    "result_origin": "transient",
                                    "result_ref": {
                                        "path": record["path"],
                                        "sha256": record["sha256"],
                                    },
                                }
                            )
                        else:
                            raise TraceRecorderError(
                                "tool result entered context without persisted content"
                            )
                    add_event(
                        "tool-call",
                        document["actor_id"],
                        document["occurred_at"],
                        tool_payload,
                    )
                frozen_read = document.get("frozen_read")
                if isinstance(frozen_read, Mapping):
                    add_event(
                        "content-read",
                        document["actor_id"],
                        document["occurred_at"],
                        {
                            "path": frozen_read["path"],
                            "access": "content",
                            "read_range": "full-file",
                            "allowlist_basis": "TASK",
                            "content_sha256": frozen_read["sha256"],
                        },
                    )
                continue
            gap = item
            affected_stream, reason_category, reason = _GAP_POLICY[gap.kind]
            event = add_event(
                "capture-gap",
                metadata.owner_actor_id,
                gap.observed_at,
                {
                    "affected_stream": affected_stream,
                    "reason_category": reason_category,
                    "reason": reason,
                },
            )
            capture_gap_entries.append(
                {"event_id": event["event_id"], "affected_stream": affected_stream}
            )
        for field_name in (
            "handoff_refs",
            "decision_refs",
            "output_refs",
            "check_refs",
        ):
            for reference in closeout_refs[field_name]:
                add_event(
                    "file-revision",
                    metadata.coordinator_actor_id,
                    handoff_at,
                    {
                        "path": reference["path"],
                        "action": "created",
                        "new_sha256": reference["sha256"],
                        "new_revision": 1,
                    },
                )
        add_event(
            "file-revision",
            metadata.coordinator_actor_id,
            handoff_at,
            {
                "path": handoff["path"],
                "action": "created",
                "new_sha256": handoff["sha256"],
                "new_revision": 1,
            },
        )
        add_event(
            "message-capture",
            metadata.worker_actor_id,
            handoff_at,
            {
                "message_id": "MSG-0002",
                "action": (
                    "exported-delayed"
                    if start["capture_action"] == "exported-delayed"
                    else "persisted-before-use"
                ),
            },
        )
        add_event(
            "attempt-status",
            metadata.coordinator_actor_id,
            finished_at,
            {
                "from_status": "running",
                "to_status": attempt_status,
                "reason": "sanitized API boundary recording finished",
            },
        )
        events_text = _jsonl_text(events)
        events_sha256 = _sha256_bytes(events_text.encode("utf-8"))
        completeness = (
            "gapped"
            if capture_gap_entries
            else "delayed"
            if start["capture_status"] == "delayed"
            else "complete"
        )
        runtime_refs = [
            {"path": record["path"], "sha256": record["sha256"]}
            for record in self._boundary_records
        ]
        index_document: dict[str, Any] = {
            "schema_version": "0.1.0",
            "trace_id": metadata.trace_id,
            "task_id": metadata.task_id,
            "task_revision": metadata.task_revision,
            "attempt_id": metadata.attempt_id,
            "archive_root": start["archive_root"],
            "baseline": metadata.baseline,
            "owner_actor_id": metadata.owner_actor_id,
            "owner": start["owner"],
            "attempt_status": attempt_status,
            "trace_status": "frozen",
            "completeness": completeness,
            "task_ref": {
                "path": start["task_relative"],
                "sha256": start["task_sha256"],
            },
            "actors_ref": {
                "path": f"{start['archive_root']}/ACTORS.yaml",
                "sha256": start["actors_sha256"],
            },
            "read_allowlist": [
                {"path": path, "authorized_by": "TASK"}
                for path in start["read_allowlist"]
            ],
            "write_scope": list(start["write_scope"]),
            "tool_allowlist": [
                {"tool_name": tool_name, "authorized_by": "TASK"}
                for tool_name in start["tool_allowlist"]
            ],
            "messages": [start["assignment"]["index_entry"], handoff["index_entry"]],
            "event_ledger": {
                "path": f"{start['archive_root']}/events.jsonl",
                "sha256": events_sha256,
                "event_count": len(events),
            },
            "tool_event_refs": runtime_refs,
            "handoff_refs": [dict(item) for item in closeout_refs["handoff_refs"]],
            "decision_refs": [dict(item) for item in closeout_refs["decision_refs"]],
            "output_refs": [dict(item) for item in closeout_refs["output_refs"]],
            "check_refs": [dict(item) for item in closeout_refs["check_refs"]],
            "capture_gaps": capture_gap_entries,
        }
        _assert_schema(catalog, "agent_trace_index", index_document)
        index_text = _yaml_text(index_document)
        return {
            "handoff": handoff,
            "handoff_path": start["archive_path"] / "messages" / handoff["filename"],
            "events": events,
            "events_text": events_text,
            "events_sha256": events_sha256,
            "index": index_document,
            "index_text": index_text,
            "index_sha256": _sha256_bytes(index_text.encode("utf-8")),
        }

    def _verify_started_boundary(self) -> None:
        if self._start is None:
            raise TraceRecorderError("Trace assignment boundary is unavailable")
        self._verify_recorder_identity()
        references = (
            (
                self._start["task_path"],
                self._start["task_sha256"],
                "trusted Task",
            ),
            (
                self._start["actors_path"],
                self._start["actors_sha256"],
                "actor registry",
            ),
            (
                self._start["assignment_path"],
                self._start["assignment"]["sha256"],
                "assignment boundary",
            ),
        )
        for path, expected_hash, label in references:
            try:
                intact = path.is_file() and hash_file(path) == expected_hash
            except OSError:
                intact = False
            if not intact:
                raise TraceRecorderError(f"{label} changed before Trace finalization")
        for record in self._boundary_records:
            try:
                intact = (
                    record["file_path"].is_file()
                    and hash_file(record["file_path"]) == record["sha256"]
                )
            except OSError:
                intact = False
            if not intact:
                raise TraceRecorderError(
                    "runtime boundary record changed before Trace finalization"
                )

    def _verify_recorder_identity(self) -> None:
        if self._start is None:
            raise TraceRecorderError("Trace assignment boundary is unavailable")
        if self.root != self._start["root"]:
            raise TraceRecorderError("Trace project root changed after begin")
        if self.metadata != self._start["metadata"]:
            raise TraceRecorderError("Trace metadata identity changed after begin")

    @staticmethod
    def _completion_identity(
        attempt_status: str,
        handoff_at: str,
        finished_at: str,
        gaps: tuple[TraceCaptureGap, ...],
        closeout_refs: Mapping[str, tuple[dict[str, str], ...]],
    ) -> tuple[Any, ...]:
        gap_keys: list[tuple[str, str]] = []
        for gap in gaps:
            if not isinstance(gap, TraceCaptureGap):
                raise TraceRecorderError("capture gap must be TraceCaptureGap metadata")
            kind = gap.kind.value if isinstance(gap.kind, CaptureGapKind) else ""
            gap_keys.append((kind, gap.observed_at))
        reference_keys = tuple(
            (
                field_name,
                tuple(
                    (item["path"], item["sha256"]) for item in closeout_refs[field_name]
                ),
            )
            for field_name in (
                "handoff_refs",
                "decision_refs",
                "output_refs",
                "check_refs",
            )
        )
        return (
            attempt_status,
            handoff_at,
            finished_at,
            tuple(sorted(gap_keys)),
            reference_keys,
        )

    def _validate_actors(self) -> dict[str, dict[str, Any]]:
        metadata = self.metadata
        if len(metadata.actors) < 2:
            raise TraceRecorderError(
                "API Trace requires coordinator and worker actor metadata"
            )
        records: dict[str, dict[str, Any]] = {}
        allowed_actor_types = {"agent", "human", "runtime-adapter", "local-tool"}
        for actor in metadata.actors:
            _validate_id("actor_id", actor.actor_id)
            _validate_id("role", actor.role)
            _validate_runtime_identity(actor.runtime_identity)
            _validate_owner(actor.accountable_owner)
            if actor.actor_type not in allowed_actor_types:
                raise TraceRecorderError(
                    "actor_type is outside the Agent Trace vocabulary"
                )
            if actor.actor_id in records:
                raise TraceRecorderError("actor_id values must be unique")
            records[actor.actor_id] = _actor_mapping(actor)
        required = {
            metadata.owner_actor_id,
            metadata.coordinator_actor_id,
            metadata.worker_actor_id,
        }
        if not required.issubset(records):
            raise TraceRecorderError(
                "owner, coordinator, and worker actors must be registered"
            )
        if metadata.coordinator_actor_id == metadata.worker_actor_id:
            raise TraceRecorderError("coordinator and worker actors must be distinct")
        return records

    def _validated_gaps(
        self,
        gaps: tuple[TraceCaptureGap, ...],
        timeline: Mapping[str, datetime],
    ) -> tuple[TraceCaptureGap, ...]:
        values: list[tuple[datetime, TraceCaptureGap]] = []
        seen: set[tuple[CaptureGapKind, str]] = set()
        for gap in gaps:
            if not isinstance(gap, TraceCaptureGap):
                raise TraceRecorderError("capture gap must be TraceCaptureGap metadata")
            if not isinstance(gap.kind, CaptureGapKind):
                raise TraceRecorderError(
                    "capture gap kind is outside the fixed policy vocabulary"
                )
            observed = _parse_timestamp("capture gap observed_at", gap.observed_at)
            if not timeline["assignment_at"] <= observed <= timeline["handoff_at"]:
                raise TraceRecorderError(
                    "capture gaps must occur between assignment and handoff"
                )
            key = (gap.kind, gap.observed_at)
            if key in seen:
                raise TraceRecorderError("duplicate capture gap metadata")
            seen.add(key)
            values.append((observed, gap))
        return tuple(
            gap
            for _, gap in sorted(
                values,
                key=lambda item: (item[0], item[1].kind.value, item[1].observed_at),
            )
        )

    def _build_message(
        self,
        *,
        sequence: int,
        kind: str,
        sender: str,
        receiver: str,
        owner: str,
        created_at: str,
        body: str,
        archive_root: str,
        catalog: SchemaCatalog,
        capture_status: str,
        capture_gap_event_id: str | None = None,
        in_reply_to: str | None = None,
    ) -> dict[str, Any]:
        message_id = f"MSG-{sequence:04d}"
        filename = f"{sequence:04d}-{sender}-to-{receiver}-{kind}.md"
        body_sha256 = _sha256_bytes(body.encode("utf-8"))
        header: dict[str, Any] = {
            "schema_version": "0.1.0",
            "message_id": message_id,
            "task_id": self.metadata.task_id,
            "task_revision": self.metadata.task_revision,
            "attempt_id": self.metadata.attempt_id,
            "sequence": sequence,
            "kind": kind,
            "sender_actor_id": sender,
            "receiver_actor_ids": [receiver],
            "accountable_owner": owner,
            "created_at": created_at,
        }
        if in_reply_to is not None:
            header["in_reply_to"] = in_reply_to
        if capture_gap_event_id is not None:
            header["capture_gap_event_id"] = capture_gap_event_id
        header.update(
            {
                "content_sha256": body_sha256,
                "attachment_refs": [],
                "redactions": [],
                "capture_status": capture_status,
            }
        )
        _assert_schema(catalog, "agent_trace_envelope", header)
        text = _message_text(header, body)
        sha256 = _sha256_bytes(text.encode("utf-8"))
        index_entry = {
            "message_id": message_id,
            "sequence": sequence,
            "path": f"{archive_root}/messages/{filename}",
            "sha256": sha256,
            "content_sha256": body_sha256,
            "kind": kind,
            "sender_actor_id": sender,
            "receiver_actor_ids": [receiver],
            "created_at": created_at,
            "capture_status": capture_status,
            "attachment_refs": [],
        }
        if in_reply_to is not None:
            index_entry["in_reply_to"] = in_reply_to
        if capture_gap_event_id is not None:
            index_entry["capture_gap_event_id"] = capture_gap_event_id
        return {
            "filename": filename,
            "path": index_entry["path"],
            "text": text,
            "sha256": sha256,
            "index_entry": index_entry,
        }

    @staticmethod
    def _message_filename(
        sequence: int,
        sender: str,
        receiver: str,
        kind: str,
    ) -> str:
        return f"{sequence:04d}-{sender}-to-{receiver}-{kind}.md"


def begin_api_trace(
    root: str | Path,
    metadata: ApiTraceMetadata,
    *,
    started_at: str,
    assignment_at: str,
) -> ApiTraceRecorder:
    """Persist the assignment boundary and return its finalization handle."""

    return ApiTraceRecorder.begin(
        root,
        metadata,
        started_at=started_at,
        assignment_at=assignment_at,
    )


def build_api_trace_bundle(
    root: str | Path,
    metadata: ApiTraceMetadata,
    timeline: TraceTimeline,
    *,
    attempt_status: str,
    capture_gaps: Iterable[TraceCaptureGap] = (),
) -> TraceBundleResult:
    """Export a retrospective bundle with delayed and gapped runtime capture."""

    recorder = ApiTraceRecorder(root, metadata)
    recorder._begin(
        started_at=timeline.started_at,
        assignment_at=timeline.assignment_at,
        capture_status="partial",
        capture_action="exported-delayed",
    )
    gaps = tuple(capture_gaps)
    if not any(
        gap.kind in {CaptureGapKind.RUNTIME_EXPORT, CaptureGapKind.CAPTURE_FAILURE}
        for gap in gaps
        if isinstance(gap, TraceCaptureGap)
    ):
        gaps += (
            TraceCaptureGap(CaptureGapKind.RUNTIME_EXPORT, timeline.assignment_at),
        )
    return recorder.finalize(
        attempt_status=attempt_status,
        handoff_at=timeline.handoff_at,
        finished_at=timeline.finished_at,
        capture_gaps=gaps,
    )


__all__ = [
    "ApiTraceMetadata",
    "ApiTraceRecorder",
    "BoundaryCallStatus",
    "CaptureGapKind",
    "FrozenReadMetadata",
    "FrozenTraceBundle",
    "FrozenTraceReference",
    "TraceActorMetadata",
    "TraceBundleResult",
    "TraceCaptureGap",
    "TraceRecorderError",
    "TraceTimeline",
    "begin_api_trace",
    "build_api_trace_bundle",
]
