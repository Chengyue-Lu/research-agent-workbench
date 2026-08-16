"""Fail-closed closeout view validation and live-drift verification."""

from __future__ import annotations

import fnmatch
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from research_workbench.adapters.models import ApiSessionResult
from research_workbench.artifacts.integrity import hash_directory, hash_file, resolve_within_root
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.context import ContextSnapshot, MainStatePacket, assess_handoff_transfer
from research_workbench.contracts import RiskLevel
from research_workbench.contracts.common import ContractError, require_relative_path
from research_workbench.observability import ExecutionReceipt, check_execution_receipt
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import HandoffPacket, TaskPacket
from research_workbench.validation import Severity, check_handoff_against_task, validate_agent_trace

from .documents import _load_mapping
from .errors import CloseoutContractSnapshot, CloseoutError, _RFC3339_TIMESTAMP
from .paths import _final_path, _stage_path

@dataclass(frozen=True, slots=True)
class _ViewCheck:
    """The invariant inputs of one closeout view, re-checked at any root.

    The commit-last protocol deliberately re-validates the same view at every
    world-state checkpoint (staged, outputs published, post-hash, and after the
    Main State publish with a fresh disk reload); only ``root`` and the Main
    State document under review differ between checkpoints.
    """

    protocol: ProjectProtocol
    task: TaskPacket
    assignment: ResolvedTask
    handoff_document: Mapping[str, Any]
    audit_document: Mapping[str, Any] | None
    receipt_document: Mapping[str, Any]
    receipt_ref: str
    main_state_ref: str
    main_state_document: Mapping[str, Any]
    protocol_ref: str
    allowed_blocking_codes: frozenset[str]

    def at(self, root: Path, *, reload_main_state: bool = False) -> list[str]:
        main_state_document = (
            _load_mapping(root, self.main_state_ref, "published Main State")
            if reload_main_state
            else self.main_state_document
        )
        warnings: list[str] = []
        handoff = HandoffPacket.from_mapping(self.handoff_document)
        handoff_risks = check_handoff_against_task(
            self.task,
            handoff,
            project_root=root,
            assignment=self.assignment,
        )
        _raise_blocking(handoff_risks, allowed=self.allowed_blocking_codes)
        warnings.extend(risk.code for risk in handoff_risks if risk.level == RiskLevel.WARNING)
        if self.audit_document is not None:
            assessment = assess_handoff_transfer(self.audit_document, root=root)
            _raise_blocking(assessment.risks)
            warnings.extend(risk.code for risk in assessment.risks if risk.level == RiskLevel.WARNING)
        receipt = ExecutionReceipt.from_mapping(self.receipt_document)
        receipt_risks = check_execution_receipt(
            receipt, self.protocol, root=root, receipt_ref=self.receipt_ref
        )
        _raise_blocking(receipt_risks)
        warnings.extend(risk.code for risk in receipt_risks if risk.level == RiskLevel.WARNING)
        state = MainStatePacket.from_mapping(main_state_document)
        if receipt.agent_trace_index_ref is not None:
            state_trace_keys = {
                (reference.path, reference.sha256)
                for reference in state.agent_trace_index_refs
            }
            receipt_trace_key = (
                receipt.agent_trace_index_ref.path,
                receipt.agent_trace_index_ref.sha256,
            )
            if state_trace_keys != {receipt_trace_key}:
                raise CloseoutError(
                    "STATE-AGENT-TRACE-MISMATCH",
                    "Main State and Execution Receipt must pin the same Agent Trace",
                )
            trace_path = resolve_within_root(root, receipt.agent_trace_index_ref.path)
            if trace_path is None or not trace_path.is_file():
                raise CloseoutError(
                    "STATE-AGENT-TRACE-MISSING",
                    receipt.agent_trace_index_ref.path,
                )
            trace_issues = validate_agent_trace(
                trace_path,
                root=root,
                attempt_path=receipt.attempt_ref,
                receipt_path=self.receipt_ref,
                state_path=(
                    self.main_state_ref
                    if (
                        (state_path := resolve_within_root(root, self.main_state_ref))
                        is not None
                        and state_path.is_file()
                    )
                    else None
                ),
            )
            blocking = [issue for issue in trace_issues if issue.severity == Severity.ERROR]
            if blocking:
                raise CloseoutError(blocking[0].code, blocking[0].message)
            warnings.extend(
                issue.code
                for issue in trace_issues
                if issue.severity == Severity.WARNING
            )
        elif state.agent_trace_index_refs:
            raise CloseoutError(
                "STATE-AGENT-TRACE-MISMATCH",
                "Main State declares an Agent Trace absent from the Receipt",
            )
        _validate_main_state_view(
            root=root,
            document=main_state_document,
            protocol=self.protocol,
            protocol_ref=self.protocol_ref,
        )
        return list(dict.fromkeys(warnings))


def _validate_main_state_view(
    *,
    root: Path,
    document: Mapping[str, Any],
    protocol: ProjectProtocol,
    protocol_ref: str,
) -> None:
    state = MainStatePacket.from_mapping(document)
    expected_protocol = f"{protocol_ref}@{protocol.revision}"
    if state.project_protocol_ref != expected_protocol:
        raise CloseoutError("STATE-PROTOCOL-DRIFT", "Main State does not pin the current protocol")
    if state.current_questions != protocol.question_refs:
        raise CloseoutError("STATE-QUESTION-DRIFT", "Main State questions differ from Project Protocol")
    if len(state.next_actions) != 1:
        raise CloseoutError("STATE-NEXT-ACTION-AMBIGUOUS", "recovery requires exactly one next action")
    for reference in state.machine_state_refs:
        resolved = resolve_within_root(root, reference.path)
        if resolved is None or not resolved.is_file():
            raise CloseoutError("STATE-MACHINE-REF-MISSING", reference.path)
        if hash_file(resolved) != reference.sha256:
            raise CloseoutError("STATE-MACHINE-REF-DRIFT", reference.path)
    machine_keys = {
        (reference.path, reference.sha256) for reference in state.machine_state_refs
    }
    for reference in state.agent_trace_index_refs:
        if (reference.path, reference.sha256) not in machine_keys:
            raise CloseoutError(
                "STATE-AGENT-TRACE-MISMATCH",
                "Agent Trace index is not also pinned as machine state",
            )
    if state.context_snapshot_ref is None:
        raise CloseoutError("STATE-CONTEXT-SNAPSHOT-MISSING", "Main State lacks Context Snapshot")
    snapshot_document = _load_mapping(root, state.context_snapshot_ref, "main Context Snapshot")
    snapshot = ContextSnapshot.from_mapping(snapshot_document)
    if snapshot.scope != "main":
        raise CloseoutError("STATE-CONTEXT-SCOPE", "Main State must reference scope=main")
    if snapshot.assessment.level == "block":
        raise CloseoutError("STATE-CONTEXT-BLOCKED", "main Context Snapshot contains a block")
    if snapshot.assessment.level in {"warn", "rollover"} and not state.rollover_reason:
        raise CloseoutError("STATE-ROLLOVER-REASON-MISSING", "checkpoint lacks rollover reason")
    if state.previous_checkpoint_ref:
        previous = MainStatePacket.from_mapping(
            _load_mapping(root, state.previous_checkpoint_ref, "previous Main State")
        )
        lost_constraints = set(previous.pinned_constraints) - set(state.pinned_constraints)
        lost_decisions = set(previous.accepted_decisions) - set(state.accepted_decisions)
        if lost_constraints:
            raise CloseoutError("STATE-CONSTRAINT-LOSS", "; ".join(sorted(lost_constraints)))
        if lost_decisions:
            raise CloseoutError("STATE-DECISION-LOSS", "; ".join(sorted(lost_decisions)))
def _normalize_terminal_status(
    *,
    terminal_status: str,
    session_result: ApiSessionResult | None,
    failure_code: str | None,
    failure_summary: str | None,
) -> tuple[str, dict[str, Any] | None]:
    status = terminal_status
    code = failure_code
    summary = failure_summary
    tool_failures: list[dict[str, Any]] = []
    if session_result is not None:
        session_status = session_result.status.value
        if terminal_status != session_status:
            is_contract_stage_completion = (
                session_status == "completed" and terminal_status == "stage-completed"
            )
            is_explicit_downgrade = (
                terminal_status != "completed"
                and failure_code is not None
                and failure_summary is not None
            )
            if not is_contract_stage_completion and not is_explicit_downgrade:
                raise CloseoutError(
                    "CLOSEOUT-SESSION-STATUS-MISMATCH",
                    "caller status differs from the isolated session without an explicit failure gate",
                )
        mismatch = sorted(set(session_result.observed_models) - {session_result.requested_model})
        if mismatch:
            status = "failed"
            code = "MODEL-IDENTITY-MISMATCH"
            summary = "Provider-reported model identity differs from the explicit slot binding."
        if session_result.tool_failures:
            status = "failed"
            code = "CLIENT-TOOL-FAILED"
            summary = "One or more bounded client tools failed; automatic replay is forbidden."
            tool_failures = [
                {
                    "tool_name": failure.tool_name,
                    "call_number": failure.call_number,
                    "error_type": failure.error_type,
                }
                for failure in session_result.tool_failures
            ]
    if status in {"completed", "stage-completed"} and (code or summary):
        status = "failed"
    if status in {"completed", "stage-completed"}:
        return status, None
    failure = {
        "code": code or f"API-SESSION-{status.upper().replace('-', '_')}",
        "summary": summary or f"API session ended with status {status}.",
    }
    if session_result is not None:
        failure["stop_reason"] = session_result.stop_reason
        if session_result.observed_models:
            failure["observed_models"] = list(session_result.observed_models)
    if tool_failures:
        failure["tool_failures"] = tool_failures
    return status, failure


def _validate_identities(task: TaskPacket, profile: AgentProfile, assignment: ResolvedTask) -> None:
    if (assignment.task_id, assignment.task_revision) != (task.task_id, task.revision):
        raise CloseoutError("ASSIGNMENT-TASK-MISMATCH", "Assignment and Task identities differ")
    if assignment.agent_profile != f"{profile.agent_profile_id}@{profile.version}":
        raise CloseoutError("ASSIGNMENT-PROFILE-MISMATCH", "Assignment and Profile identities differ")
    if task.agent_profile != profile.agent_profile_id:
        raise CloseoutError("TASK-PROFILE-MISMATCH", "Task and Profile identities differ")


def _validate_closeout_permission(assignment: ResolvedTask) -> None:
    if assignment.effective_permissions.filesystem not in {"worktree-write", "workspace-write"}:
        raise CloseoutError(
            "TASK-PERMISSION-ESCALATION",
            "K-API-2 closeout requires an effective worktree-write permission",
        )


def _validate_output_paths(
    project_root: Path,
    task: TaskPacket,
    assignment: ResolvedTask,
    paths: tuple[str, ...],
) -> None:
    for relative in paths:
        normalized = relative.replace("\\", "/")
        resolved = resolve_within_root(project_root, normalized)
        if resolved is None:
            raise CloseoutError("CLOSEOUT-WRITE-SCOPE", f"path escapes project root: {relative}")
        if not any(_path_scope_matches(normalized, scope) for scope in task.write_scope):
            raise CloseoutError("CLOSEOUT-WRITE-SCOPE", f"path is outside Task write_scope: {relative}")
        if assignment.effective_permissions.allowed_roots:
            allowed = False
            for allowed_root in assignment.effective_permissions.allowed_roots:
                allowed_path = resolve_within_root(project_root, allowed_root)
                if allowed_path is None:
                    raise CloseoutError(
                        "CLOSEOUT-PERMISSION",
                        f"effective allowed_root escapes project: {allowed_root}",
                    )
                try:
                    resolved.relative_to(allowed_path)
                    allowed = True
                    break
                except ValueError:
                    continue
            if not allowed:
                raise CloseoutError(
                    "CLOSEOUT-PERMISSION",
                    f"path is outside effective allowed_roots: {relative}",
                )


def _path_scope_matches(path: str, pattern: str) -> bool:
    """Match POSIX path segments; only ``**`` may cross directory boundaries."""

    path_parts = tuple(part for part in path.replace("\\", "/").split("/") if part)
    pattern_parts = tuple(part for part in pattern.replace("\\", "/").split("/") if part)
    if ".." in path_parts or ".." in pattern_parts:
        return False
    memo: dict[tuple[int, int], bool] = {}

    def match(path_index: int, pattern_index: int) -> bool:
        key = (path_index, pattern_index)
        if key in memo:
            return memo[key]
        if pattern_index == len(pattern_parts):
            result = path_index == len(path_parts)
        elif pattern_parts[pattern_index] == "**":
            result = match(path_index, pattern_index + 1) or (
                path_index < len(path_parts) and match(path_index + 1, pattern_index)
            )
        else:
            result = (
                path_index < len(path_parts)
                and fnmatch.fnmatchcase(path_parts[path_index], pattern_parts[pattern_index])
                and match(path_index + 1, pattern_index + 1)
            )
        memo[key] = result
        return result

    return match(0, 0)


def _verify_live_contract_snapshots(
    project_root: Path,
    snapshots: tuple[CloseoutContractSnapshot, ...],
) -> None:
    for snapshot in snapshots:
        resolved = resolve_within_root(project_root, snapshot.ref)
        if resolved is None or not resolved.is_file():
            raise CloseoutError(
                "EXECUTION-CONTRACT-DRIFT", f"contract is missing or outside root: {snapshot.ref}"
            )
        if resolved.read_bytes() != snapshot.payload:
            raise CloseoutError(
                "EXECUTION-CONTRACT-DRIFT", f"contract bytes changed during Attempt: {snapshot.ref}"
            )


def _require_canonical_contract_ref(ref: str) -> None:
    try:
        require_relative_path(ref, "contract_ref")
    except ContractError as exc:
        raise CloseoutError("CLOSEOUT-CONTRACT-REF", str(exc)) from exc
    canonical = PurePosixPath(ref).as_posix()
    if "\\" in ref or canonical != ref or ref in {"", "."}:
        raise CloseoutError(
            "CLOSEOUT-CONTRACT-REF",
            f"contract ref must use one canonical repository-relative POSIX path: {ref}",
        )


def _verify_live_staged_sources(
    *,
    project_root: Path,
    stage_root: Path,
    task: TaskPacket,
    main_state_document: Mapping[str, Any],
    attempt_root: str,
    main_state_ref: str,
    allow_stale_inputs: bool,
) -> None:
    state = MainStatePacket.from_mapping(main_state_document)
    input_paths = {reference.path for reference in task.input_refs}
    for reference in task.input_refs:
        if allow_stale_inputs:
            continue
        staged = _stage_path(stage_root, reference.path)
        live = resolve_within_root(project_root, reference.path)
        if live is None or not live.is_file() or not staged.is_file():
            raise CloseoutError("TASK-STALE-INPUT", f"Task input is unavailable: {reference.path}")
        live_payload = live.read_bytes()
        staged_payload = staged.read_bytes()
        expected_hash = reference.sha256.removeprefix("sha256:").lower()
        if live_payload != staged_payload or hashlib.sha256(live_payload).hexdigest() != expected_hash:
            raise CloseoutError("TASK-STALE-INPUT", f"Task input drifted: {reference.path}")
    for reference in state.machine_state_refs:
        relative = reference.path
        if (
            relative in input_paths
            or relative == main_state_ref
            or relative == attempt_root
            or relative.startswith(attempt_root + "/")
        ):
            continue
        staged = _stage_path(stage_root, relative)
        live = resolve_within_root(project_root, relative)
        if live is None or not live.is_file() or not staged.is_file():
            raise CloseoutError("EXECUTION-CONTRACT-DRIFT", f"closeout source is missing: {relative}")
        if live.read_bytes() != staged.read_bytes():
            raise CloseoutError("EXECUTION-CONTRACT-DRIFT", f"closeout source drifted: {relative}")


def _verify_live_skill_locks(project_root: Path, assignment: ResolvedTask) -> None:
    for lock in assignment.skill_lock:
        if not lock.source_locator:
            raise CloseoutError(
                "ASSIGNMENT-SKILL-DRIFT", f"Skill lock has no source locator: {lock.identifier}"
            )
        source = resolve_within_root(project_root, lock.source_locator)
        if source is None or not source.is_file():
            raise CloseoutError(
                "ASSIGNMENT-SKILL-DRIFT", f"Skill source is missing: {lock.identifier}"
            )
        expected_content = lock.content_hash.removeprefix("sha256:").lower()
        if hash_file(source) != expected_content:
            raise CloseoutError(
                "ASSIGNMENT-SKILL-DRIFT", f"Skill source drifted: {lock.identifier}"
            )
        if lock.package_hash is not None:
            expected_package = lock.package_hash.removeprefix("sha256:").lower()
            if hash_directory(source.parent) != expected_package:
                raise CloseoutError(
                    "ASSIGNMENT-SKILL-DRIFT", f"Skill package drifted: {lock.identifier}"
                )


def _verify_published_hashes(
    project_root: Path,
    published_refs: tuple[str, ...],
    expected_hashes: Mapping[str, str],
) -> None:
    for relative in published_refs:
        final = _final_path(project_root, relative)
        expected = expected_hashes.get(relative)
        if expected is None or not final.is_file() or hash_file(final) != expected:
            raise CloseoutError(
                "CLOSEOUT-PUBLISHED-DRIFT", f"published closeout file drifted: {relative}"
            )


def _verify_staged_hash(stage_root: Path, relative: str, expected_hash: str) -> None:
    staged = _stage_path(stage_root, relative)
    if not staged.is_file() or hash_file(staged) != expected_hash:
        raise CloseoutError("CLOSEOUT-STAGE-DRIFT", f"staged closeout file drifted: {relative}")


def _raise_blocking(risks: Any, *, allowed: frozenset[str] = frozenset()) -> None:
    blockers = [
        risk for risk in risks if risk.level == RiskLevel.BLOCK and risk.code not in allowed
    ]
    if blockers:
        first = blockers[0]
        raise CloseoutError(first.code, first.message)


def _expected_blockers(failure: Mapping[str, Any] | None) -> frozenset[str]:
    if failure and failure.get("code") in {
        "REF-MISSING",
        "REF-HASH-MISMATCH",
        "REF-OUTSIDE-ROOT",
        "TASK-STALE-INPUT",
    }:
        return frozenset({"TASK-STALE-INPUT"})
    return frozenset()


def _validate_timestamp_order(started_at: str, finished_at: str) -> None:
    if not all(
        isinstance(value, str) and _RFC3339_TIMESTAMP.fullmatch(value)
        for value in (started_at, finished_at)
    ):
        raise CloseoutError(
            "CLOSEOUT-TIMESTAMP",
            "timestamps must be timezone-aware RFC 3339 date-times",
        )
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
        if started.utcoffset() is None or finished.utcoffset() is None:
            raise ValueError("timezone offset is required")
    except (TypeError, ValueError) as exc:
        raise CloseoutError(
            "CLOSEOUT-TIMESTAMP",
            "timestamps must be timezone-aware RFC 3339 date-times",
        ) from exc
    if finished < started:
        raise CloseoutError("CLOSEOUT-TIMESTAMP", "finished_at precedes started_at")
