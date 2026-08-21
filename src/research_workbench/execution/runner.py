"""Legacy-compatible traced wrapper for one isolated model API session."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import yaml

from research_workbench.adapters.models import (
    ApiSessionLimits,
    ApiSessionResult,
    IsolatedApiSessionRunner,
    ModelRequest,
)
from research_workbench.observability.trace import (
    AgentTraceRecorder,
    TRACE_INDEX_FILENAME,
)
from research_workbench.tasks import FileReference


@dataclass(frozen=True, slots=True)
class TracedSessionResult:
    session: ApiSessionResult
    attempt_dir: Path
    trace_ref: FileReference
    redactions_applied: int


def _actor_id(profile: str, attempt_id: str) -> str:
    value = f"{profile}-{attempt_id}"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return cleaned or f"runtime-{attempt_id}"


def _has_outbound_request(attempt_dir: Path) -> bool:
    index_path = attempt_dir / TRACE_INDEX_FILENAME
    try:
        loaded = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, yaml.YAMLError):
        return False
    index = loaded if isinstance(loaded, Mapping) else {}
    messages = index.get("messages", [])
    return isinstance(messages, list) and any(
        isinstance(item, Mapping) and item.get("kind") == "provider-request"
        for item in messages
    )


def run_traced_session(
    *,
    root: str | Path,
    attempt_dir: str | Path,
    task_id: str,
    task_revision: int,
    attempt_id: str,
    task_snapshot: Mapping[str, Any],
    accountable_owner: str,
    agent_profile_id: str,
    provider_name: str,
    request: ModelRequest,
    limits: ApiSessionLimits,
    session_runner: IsolatedApiSessionRunner,
    read_allowlist: Sequence[str],
    write_scope: Sequence[str],
    tool_allowlist: Sequence[str],
    actor_id: str | None = None,
    cancel_requested: Callable[[], bool] | None = None,
) -> TracedSessionResult:
    """Create Trace first, execute once, and seal without reusing an Attempt."""

    project_root = Path(root).resolve()
    raw_attempt = Path(attempt_dir)
    directory = (raw_attempt if raw_attempt.is_absolute() else project_root / raw_attempt).resolve()
    try:
        directory.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("attempt_dir must stay within the project root") from exc
    if not accountable_owner.strip():
        raise ValueError("accountable_owner is required")
    if not agent_profile_id.strip():
        raise ValueError("agent_profile_id is required")
    recorder = AgentTraceRecorder(
        directory,
        task_id=task_id,
        task_revision=task_revision,
        attempt_id=attempt_id,
        task_snapshot=task_snapshot,
        accountable_owner=accountable_owner,
        actor_id=actor_id or _actor_id(agent_profile_id, attempt_id),
        runtime_identity="isolated-api-session",
        provider=provider_name,
        read_allowlist=read_allowlist,
        write_scope=write_scope,
        tool_allowlist=tool_allowlist,
    )
    try:
        session = session_runner.run(
            provider_name=provider_name,
            request=request,
            limits=limits,
            cancel_requested=cancel_requested,
            event_sink=recorder,
        )
    except BaseException as exc:
        outbound_may_have_run = _has_outbound_request(recorder.attempt_dir)
        if outbound_may_have_run:
            try:
                recorder.record_capture_gap(
                    "events",
                    "session aborted after durable outbound request: "
                    f"{type(exc).__name__}",
                )
            except BaseException:
                # If even the capture-gap cannot be stored, the missing closeout
                # marker remains the fail-closed signal.
                pass
        try:
            recorder.record_attempt_status(
                "failed" if outbound_may_have_run else "blocked",
                reason=f"session raised {type(exc).__name__}",
            )
            recorder.seal("failed" if outbound_may_have_run else "blocked")
        except BaseException:
            pass
        raise

    trace_mapping = recorder.seal(session.status.value)
    project_trace_mapping = {
        "path": recorder.index_path.relative_to(project_root).as_posix(),
        "sha256": trace_mapping["sha256"],
    }
    return TracedSessionResult(
        session=session,
        attempt_dir=recorder.attempt_dir,
        trace_ref=FileReference.from_mapping(project_trace_mapping),
        redactions_applied=recorder.redaction_count,
    )


__all__ = ["TracedSessionResult", "run_traced_session"]
