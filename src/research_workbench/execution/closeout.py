"""Crash-consistent file closeout for one bounded API Attempt.

This module deliberately implements a commit-last protocol, not a multi-file
transaction: immutable documents are staged and validated, published by
exclusive hard link, and only then made resumable by publishing Main State.
An unpublished or partially published bundle is therefore unreachable from a
new authoritative checkpoint. A fully validated stage has an exact publication
plan and can resume without re-running the model; an incomplete build fails
closed for explicit recovery.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from research_workbench.adapters.models import ApiSessionLimits, ApiSessionResult
from research_workbench.artifacts.integrity import hash_directory, hash_file, resolve_within_root
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.context import (
    CONTEXT_METRIC_NAMES,
    ContextBudgetEstimate,
    ContextPolicySnapshot,
    ContextSnapshot,
    MainStatePacket,
    assess_handoff_transfer,
    checkpoint_digest,
)
from research_workbench.contracts import RiskLevel, is_path_safe_identifier
from research_workbench.contracts.common import ContractError, require_relative_path
from research_workbench.execution.output import validate_api_task_output
from research_workbench.io import (
    load_document,
    publish_staged_file_exclusive,
    write_bytes_exclusive,
    write_yaml_exclusive,
)
from research_workbench.observability import ExecutionReceipt, check_execution_receipt
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import AttemptRecord, HandoffPacket, TaskPacket
from research_workbench.validation import SchemaCatalog, check_claim_ceiling, check_handoff_against_task


_TERMINAL_STATUSES = {"completed", "safe-paused", "blocked", "incomplete", "failed"}
_RFC3339_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class CloseoutError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class CloseoutPublication:
    status: str
    main_state_ref: str
    published_refs: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CloseoutContractSnapshot:
    """Exact pre-execution bytes for one trusted closeout contract."""

    ref: str
    kind: str
    sha256: str
    payload: bytes = field(repr=False)


def capture_closeout_contracts(
    root: str | Path,
    specifications: tuple[tuple[str, str], ...],
) -> tuple[CloseoutContractSnapshot, ...]:
    """Capture and schema-check trusted contract bytes exactly once."""

    project_root = Path(root).resolve()
    snapshots: list[CloseoutContractSnapshot] = []
    seen: set[str] = set()
    for ref, kind in specifications:
        _require_canonical_contract_ref(ref)
        if ref in seen:
            raise CloseoutError("CLOSEOUT-CONTRACT-REF", f"duplicate contract ref: {ref}")
        seen.add(ref)
        resolved = resolve_within_root(project_root, ref)
        if resolved is None:
            raise CloseoutError("CLOSEOUT-CONTRACT-REF", f"contract ref escapes root: {ref}")
        if not resolved.is_file():
            raise CloseoutError("CLOSEOUT-CONTRACT-MISSING", f"contract is missing: {ref}")
        payload = resolved.read_bytes()
        snapshot = CloseoutContractSnapshot(
            ref=ref,
            kind=kind,
            sha256=hashlib.sha256(payload).hexdigest(),
            payload=payload,
        )
        _snapshot_document(snapshot)
        snapshots.append(snapshot)
    return tuple(snapshots)


def contract_snapshot_document(
    snapshots: tuple[CloseoutContractSnapshot, ...],
    ref: str,
) -> Mapping[str, Any]:
    """Parse one already captured and validated contract snapshot."""

    matches = [snapshot for snapshot in snapshots if snapshot.ref == ref]
    if len(matches) != 1:
        raise CloseoutError("CLOSEOUT-CONTRACT-SNAPSHOT", f"expected one snapshot for {ref}")
    return _snapshot_document(matches[0])


def resume_staged_closeout(
    *,
    root: str | Path,
    attempt_id: str,
    expected_task_id: str,
    expected_protocol_ref: str,
    expected_task_ref: str,
    expected_profile_ref: str,
    expected_assignment_ref: str,
    expected_provider_adapter_id: str,
    expected_model: str,
    expected_previous_main_state_ref: str | None,
    fault_injector: Callable[[str], None] | None = None,
) -> CloseoutPublication:
    """Finish a fully staged closeout without invoking a Provider or tool."""

    project_root = Path(root).resolve()
    if not is_path_safe_identifier(attempt_id):
        raise CloseoutError("CLOSEOUT-ATTEMPT-ID", "attempt_id is not path-safe")
    stage_parent, stage_root = _stage_locations(project_root, attempt_id, create=False)
    if not stage_root.is_dir():
        _raise_if_execution_intent_is_incomplete(
            project_root,
            attempt_id=attempt_id,
            task_id=expected_task_id,
            protocol_ref=expected_protocol_ref,
            task_ref=expected_task_ref,
            profile_ref=expected_profile_ref,
            assignment_ref=expected_assignment_ref,
            provider_adapter_id=expected_provider_adapter_id,
            requested_model=expected_model,
            previous_main_state_ref=expected_previous_main_state_ref,
        )
        raise CloseoutError("CLOSEOUT-STAGE-MISSING", f"no staged closeout for {attempt_id}")
    try:
        plan = _load_stage_plan(stage_parent, stage_root, attempt_id)
    except CloseoutError as exc:
        if exc.code == "CLOSEOUT-STAGE-INCOMPLETE":
            _raise_if_execution_intent_is_incomplete(
                project_root,
                attempt_id=attempt_id,
                task_id=expected_task_id,
                protocol_ref=expected_protocol_ref,
                task_ref=expected_task_ref,
                profile_ref=expected_profile_ref,
                assignment_ref=expected_assignment_ref,
                provider_adapter_id=expected_provider_adapter_id,
                requested_model=expected_model,
                previous_main_state_ref=expected_previous_main_state_ref,
            )
        raise
    expected_plan = {
        "protocol_ref": expected_protocol_ref,
        "task_ref": expected_task_ref,
        "profile_ref": expected_profile_ref,
        "assignment_ref": expected_assignment_ref,
        "provider_adapter_id": expected_provider_adapter_id,
        "requested_model": expected_model,
        "previous_main_state_ref": expected_previous_main_state_ref,
    }
    if any(plan[key] != value for key, value in expected_plan.items()):
        raise CloseoutError(
            "CLOSEOUT-STAGE-IDENTITY",
            "staged closeout belongs to different contract references",
        )
    canonical_paths = _CloseoutPaths(f"work/{expected_task_id}/{attempt_id}")
    if (
        plan["attempt_ref"] != canonical_paths.attempt
        or plan["main_state_ref"] != canonical_paths.main_state
    ):
        raise CloseoutError(
            "CLOSEOUT-STAGE-IDENTITY",
            "staged closeout paths differ from the canonical Task/Attempt root",
        )
    main_state_ref = canonical_paths.main_state
    attempt_ref = canonical_paths.attempt
    attempt_root = canonical_paths.attempt_root
    main_state_document = _load_mapping(stage_root, main_state_ref, "staged Main State")
    state = MainStatePacket.from_mapping(main_state_document)
    if state.previous_checkpoint_ref != expected_previous_main_state_ref:
        raise CloseoutError(
            "CLOSEOUT-STAGE-IDENTITY",
            "staged Main State has a different previous checkpoint",
        )
    attempt_document = _load_mapping(stage_root, attempt_ref, "staged Attempt")
    attempt = AttemptRecord.from_mapping(attempt_document)
    if attempt.attempt_id != attempt_id:
        raise CloseoutError("CLOSEOUT-STAGE-IDENTITY", "staged Attempt ID differs from directory")
    if attempt.task_id != expected_task_id:
        raise CloseoutError("CLOSEOUT-STAGE-IDENTITY", "staged closeout belongs to another Task")
    protocol_ref, separator, revision = state.project_protocol_ref.rpartition("@")
    if not separator or not revision.isdigit():
        raise CloseoutError("STATE-PROTOCOL-DRIFT", "Main State protocol reference is invalid")
    if protocol_ref != plan["protocol_ref"]:
        raise CloseoutError("CLOSEOUT-STAGE-IDENTITY", "stage plan and Main State protocol differ")
    protocol = ProjectProtocol.from_mapping(
        _load_mapping(stage_root, protocol_ref, "staged Project Protocol")
    )
    task_ref = plan["task_ref"]
    task = TaskPacket.from_mapping(_load_mapping(stage_root, task_ref, "staged Task Packet"))
    if (task.task_id, task.revision) != (attempt.task_id, attempt.task_revision):
        raise CloseoutError("CLOSEOUT-STAGE-IDENTITY", "staged Task and Attempt differ")
    if attempt.execution_receipt_ref is None or attempt.handoff_ref is None:
        raise CloseoutError("CLOSEOUT-STAGE-INCOMPLETE", "Attempt lacks Receipt or Handoff back-reference")
    receipt_ref = attempt.execution_receipt_ref
    receipt_document = _load_mapping(stage_root, receipt_ref, "staged Execution Receipt")
    receipt = ExecutionReceipt.from_mapping(receipt_document)
    if receipt.agent_profile_ref != plan["profile_ref"]:
        raise CloseoutError("CLOSEOUT-STAGE-IDENTITY", "stage plan and Receipt Profile differ")
    if receipt.skill_assignment_ref != plan["assignment_ref"]:
        raise CloseoutError("CLOSEOUT-STAGE-IDENTITY", "stage plan and Receipt Assignment differ")
    assignment = ResolvedTask.from_mapping(
        _load_mapping(stage_root, receipt.skill_assignment_ref, "staged Skill Assignment")
    )
    handoff_document = _load_mapping(stage_root, attempt.handoff_ref, "staged Handoff")
    handoff = HandoffPacket.from_mapping(handoff_document)
    audit_document: Mapping[str, Any] | None = None
    if handoff.validation_refs:
        if len(handoff.validation_refs) != 1:
            raise CloseoutError("CLOSEOUT-STAGE-INCOMPLETE", "K-API-2 expects at most one Transfer Audit")
        audit_document = _load_mapping(stage_root, handoff.validation_refs[0], "staged Transfer Audit")
    failure = attempt.failure if isinstance(attempt.failure, Mapping) else None
    allowed = _expected_blockers(failure)
    warnings = _validate_closeout_view(
        root=stage_root,
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=receipt_ref,
        main_state_document=main_state_document,
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed,
    )
    planned_contract_refs = {
        plan["protocol_ref"],
        plan["task_ref"],
        plan["profile_ref"],
        plan["assignment_ref"],
    }
    state_refs = {reference.path for reference in state.machine_state_refs}
    if not planned_contract_refs.issubset(state_refs):
        raise CloseoutError("CLOSEOUT-STAGE-INCOMPLETE", "Main State omits planned contract files")
    output_refs = tuple(
        reference.path
        for reference in state.machine_state_refs
        if reference.path == attempt_root or reference.path.startswith(attempt_root + "/")
    )
    output_refs = tuple(relative for relative in output_refs if relative != main_state_ref)
    publication_hashes = plan["publication_hashes"]
    if set(publication_hashes) != {*output_refs, main_state_ref}:
        raise CloseoutError(
            "CLOSEOUT-STAGE-INCOMPLETE",
            "stage publication plan differs from Main State output references",
        )
    required = {attempt_ref, attempt.handoff_ref, receipt_ref, state.context_snapshot_ref}
    if None in required or not {str(value) for value in required}.issubset(set(output_refs)):
        raise CloseoutError("CLOSEOUT-STAGE-INCOMPLETE", "Main State omits required closeout files")
    _validate_closeout_permission(assignment)
    _validate_output_paths(project_root, task, assignment, (*output_refs, main_state_ref))
    _verify_live_staged_sources(
        project_root=project_root,
        stage_root=stage_root,
        task=task,
        main_state_document=main_state_document,
        attempt_root=attempt_root,
        main_state_ref=main_state_ref,
        allow_stale_inputs=bool(allowed),
    )
    if plan["execution_material_status"] == "locked":
        _verify_live_skill_locks(project_root, assignment)
    fault = fault_injector or (lambda _point: None)
    published: list[str] = []
    for relative in output_refs:
        fault(f"before-publish:{relative}")
        publish_staged_file_exclusive(
            _stage_path(stage_root, relative),
            _final_path(project_root, relative),
        )
        published.append(relative)
        fault(f"after-publish:{relative}")
    warnings = _validate_closeout_view(
        root=project_root,
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=receipt_ref,
        main_state_document=main_state_document,
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed,
    )
    fault("before-main-state-publish")
    _verify_published_hashes(project_root, output_refs, publication_hashes)
    warnings = _validate_closeout_view(
        root=project_root,
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=receipt_ref,
        main_state_document=main_state_document,
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed,
    )
    _verify_live_staged_sources(
        project_root=project_root,
        stage_root=stage_root,
        task=task,
        main_state_document=main_state_document,
        attempt_root=attempt_root,
        main_state_ref=main_state_ref,
        allow_stale_inputs=bool(allowed),
    )
    if plan["execution_material_status"] == "locked":
        _verify_live_skill_locks(project_root, assignment)
    _verify_staged_hash(stage_root, main_state_ref, publication_hashes[main_state_ref])
    publish_staged_file_exclusive(
        _stage_path(stage_root, main_state_ref),
        _final_path(project_root, main_state_ref),
    )
    published.append(main_state_ref)
    fault("after-main-state-publish")
    _validate_closeout_view(
        root=project_root,
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=receipt_ref,
        main_state_document=_load_mapping(project_root, main_state_ref, "published Main State"),
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed,
    )
    fault("after-final-validation")
    _remove_stage(project_root, stage_parent)
    return CloseoutPublication(
        status=attempt.status,
        main_state_ref=main_state_ref,
        published_refs=tuple(published),
        warnings=tuple(warnings),
    )


def staged_closeout_exists(*, root: str | Path, attempt_id: str) -> bool:
    """Return whether a path-safe Attempt has any fail-closed closeout stage."""

    project_root = Path(root).resolve()
    if not is_path_safe_identifier(attempt_id):
        raise CloseoutError("CLOSEOUT-ATTEMPT-ID", "attempt_id is not path-safe")
    stage_parent, _stage_root = _stage_locations(project_root, attempt_id, create=False)
    return stage_parent.exists()


def record_api_attempt_intent(
    *,
    root: str | Path,
    attempt_id: str,
    task_id: str,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    provider_adapter_id: str,
    requested_model: str,
    started_at: str,
    previous_main_state_ref: str | None,
) -> bool:
    """Exclusively record execution intent before the first Provider call.

    An intent without a validated closeout plan is deliberately indeterminate:
    a later invocation must never guess that Provider/tool execution was absent.
    """

    project_root = Path(root).resolve()
    if not is_path_safe_identifier(attempt_id):
        raise CloseoutError("CLOSEOUT-ATTEMPT-ID", "attempt_id is not path-safe")
    if not is_path_safe_identifier(task_id):
        raise CloseoutError("CLOSEOUT-TASK-ID", "task_id must be one path-safe segment")
    intent_path = _attempt_intent_path(project_root, attempt_id, create=True)
    return write_yaml_exclusive(
        intent_path,
        {
            "version": 2,
            "attempt_id": attempt_id,
            "task_id": task_id,
            "protocol_ref": protocol_ref,
            "task_ref": task_ref,
            "profile_ref": profile_ref,
            "assignment_ref": assignment_ref,
            "provider_adapter_id": provider_adapter_id,
            "requested_model": requested_model,
            "started_at": started_at,
            "previous_main_state_ref": previous_main_state_ref,
        },
    )


def fail_if_api_attempt_intent_exists(
    *,
    root: str | Path,
    attempt_id: str,
    task_id: str,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    provider_adapter_id: str,
    requested_model: str,
    previous_main_state_ref: str | None,
) -> None:
    """Reject an uncommitted retry after execution may already have started."""

    _raise_if_execution_intent_is_incomplete(
        Path(root).resolve(),
        attempt_id=attempt_id,
        task_id=task_id,
        protocol_ref=protocol_ref,
        task_ref=task_ref,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        provider_adapter_id=provider_adapter_id,
        requested_model=requested_model,
        previous_main_state_ref=previous_main_state_ref,
    )


def inspect_committed_closeout(
    *,
    root: str | Path,
    task_id: str,
    attempt_id: str,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    previous_main_state_ref: str | None,
    expected_provider_adapter_id: str,
    expected_model: str,
) -> CloseoutPublication | None:
    """Validate and return one already committed Attempt without replaying execution."""

    project_root = Path(root).resolve()
    if not is_path_safe_identifier(attempt_id):
        raise CloseoutError("CLOSEOUT-ATTEMPT-ID", "attempt_id is not path-safe")
    attempt_root = f"work/{task_id}/{attempt_id}"
    paths = _CloseoutPaths(attempt_root)
    main_path = _final_path(project_root, paths.main_state)
    if not main_path.is_file():
        return None
    main_state_document = _load_mapping(project_root, paths.main_state, "committed Main State")
    state = MainStatePacket.from_mapping(main_state_document)
    if state.previous_checkpoint_ref != previous_main_state_ref:
        raise CloseoutError(
            "CLOSEOUT-COMMITTED-IDENTITY",
            "committed Main State has a different previous checkpoint",
        )
    attempt_document = _load_mapping(project_root, paths.attempt, "committed Attempt")
    attempt = AttemptRecord.from_mapping(attempt_document)
    if (attempt.task_id, attempt.attempt_id) != (task_id, attempt_id):
        raise CloseoutError("CLOSEOUT-COMMITTED-IDENTITY", "committed Attempt identity differs")
    protocol = ProjectProtocol.from_mapping(
        _load_mapping(project_root, protocol_ref, "committed Project Protocol")
    )
    task = TaskPacket.from_mapping(_load_mapping(project_root, task_ref, "committed Task Packet"))
    if (task.task_id, task.revision) != (attempt.task_id, attempt.task_revision):
        raise CloseoutError("CLOSEOUT-COMMITTED-IDENTITY", "committed Task and Attempt differ")
    if attempt.execution_receipt_ref is None or attempt.handoff_ref is None:
        raise CloseoutError("CLOSEOUT-COMMITTED-INCOMPLETE", "Attempt lacks Receipt or Handoff")
    receipt_ref = attempt.execution_receipt_ref
    receipt_document = _load_mapping(project_root, receipt_ref, "committed Execution Receipt")
    receipt = ExecutionReceipt.from_mapping(receipt_document)
    if receipt.model_binding is None or (
        receipt.model_binding.provider_adapter_id,
        receipt.model_binding.requested_model,
    ) != (expected_provider_adapter_id, expected_model):
        raise CloseoutError(
            "CLOSEOUT-COMMITTED-IDENTITY",
            "committed Receipt has a different requested model binding",
        )
    if receipt.agent_profile_ref != profile_ref or receipt.skill_assignment_ref != assignment_ref:
        raise CloseoutError(
            "CLOSEOUT-COMMITTED-IDENTITY",
            "committed Receipt differs from the requested Profile or Assignment",
        )
    assignment = ResolvedTask.from_mapping(
        _load_mapping(project_root, assignment_ref, "committed Skill Assignment")
    )
    handoff_document = _load_mapping(project_root, attempt.handoff_ref, "committed Handoff")
    handoff = HandoffPacket.from_mapping(handoff_document)
    if (handoff.task_id, handoff.attempt_id, handoff.status) != (
        task_id,
        attempt_id,
        attempt.status,
    ):
        raise CloseoutError("CLOSEOUT-COMMITTED-IDENTITY", "committed Handoff differs")
    audit_document: Mapping[str, Any] | None = None
    if handoff.validation_refs:
        if len(handoff.validation_refs) != 1:
            raise CloseoutError("CLOSEOUT-COMMITTED-INCOMPLETE", "expected at most one Transfer Audit")
        audit_document = _load_mapping(
            project_root,
            handoff.validation_refs[0],
            "committed Transfer Audit",
        )
    required_refs = {
        protocol_ref,
        task_ref,
        profile_ref,
        assignment_ref,
        paths.attempt,
        attempt.handoff_ref,
        receipt_ref,
        state.context_snapshot_ref,
    }
    state_refs = {reference.path for reference in state.machine_state_refs}
    if None in required_refs or not {str(value) for value in required_refs}.issubset(state_refs):
        raise CloseoutError(
            "CLOSEOUT-COMMITTED-INCOMPLETE",
            "committed Main State omits required contract or closeout files",
        )
    allowed = _expected_blockers(attempt.failure if isinstance(attempt.failure, Mapping) else None)
    warnings = _validate_closeout_view(
        root=project_root,
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=receipt_ref,
        main_state_document=main_state_document,
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed,
    )
    task_states = [item for item in state.active_tasks if item.task_id == task_id]
    if len(task_states) != 1 or task_states[0].status != attempt.status:
        raise CloseoutError("CLOSEOUT-COMMITTED-IDENTITY", "Main State and Attempt status differ")
    published = tuple(
        [
            *(
                reference.path
                for reference in state.machine_state_refs
                if reference.path == attempt_root
                or reference.path.startswith(attempt_root + "/")
            ),
            paths.main_state,
        ]
    )
    return CloseoutPublication(attempt.status, paths.main_state, published, tuple(warnings))


def validate_closeout_preconditions(
    *,
    root: str | Path,
    protocol: ProjectProtocol,
    task: TaskPacket,
    profile: AgentProfile,
    assignment: ResolvedTask,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    attempt_id: str,
    started_at: str,
    finished_at: str,
    previous_main_state_ref: str | None = None,
    previous_main_state_document: Mapping[str, Any] | None = None,
) -> None:
    """Fail before execution when the trusted closeout destination is invalid."""

    project_root = Path(root).resolve()
    if not is_path_safe_identifier(attempt_id):
        raise CloseoutError("CLOSEOUT-ATTEMPT-ID", "attempt_id is not path-safe")
    for ref in (protocol_ref, task_ref, profile_ref, assignment_ref):
        _require_canonical_contract_ref(ref)
    if previous_main_state_ref is not None:
        _require_canonical_contract_ref(previous_main_state_ref)
    elif previous_main_state_document is not None:
        raise CloseoutError(
            "CLOSEOUT-CONTRACT-REF",
            "previous Main State document requires previous_main_state_ref",
        )
    _validate_timestamp_order(started_at, finished_at)
    _validate_identities(task, profile, assignment)
    _validate_closeout_permission(assignment)
    if not is_path_safe_identifier(task.task_id):
        raise CloseoutError("CLOSEOUT-TASK-ID", "task_id must be one path-safe segment")
    paths = _CloseoutPaths(f"work/{task.task_id}/{attempt_id}")
    _validate_output_paths(project_root, task, assignment, paths.static_final_paths)
    for relative in (protocol_ref, task_ref, profile_ref, assignment_ref):
        _resolve_existing(project_root, relative, "closeout contract")
    if previous_main_state_ref:
        previous_document = previous_main_state_document or _load_mapping(
            project_root, previous_main_state_ref, "previous Main State"
        )
        MainStatePacket.from_mapping(previous_document)
        _validate_main_state_view(
            root=project_root,
            document=previous_document,
            protocol=protocol,
            protocol_ref=protocol_ref,
        )


def closeout_api_attempt(
    *,
    root: str | Path,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    attempt_id: str,
    started_at: str,
    finished_at: str,
    terminal_status: str,
    next_action: str,
    provider_adapter_id: str,
    requested_model: str,
    provider_adapter_version: str,
    expected_provider_identity: str | None,
    limits: ApiSessionLimits,
    session_result: ApiSessionResult | None = None,
    output: Mapping[str, Any] | None = None,
    failure_code: str | None = None,
    failure_summary: str | None = None,
    previous_main_state_ref: str | None = None,
    external_provider: bool = False,
    extra_limitations: tuple[str, ...] = (),
    fault_injector: Callable[[str], None] | None = None,
    contract_snapshots: tuple[CloseoutContractSnapshot, ...] | None = None,
    frozen_input_payloads: Mapping[str, bytes] | None = None,
) -> CloseoutPublication:
    """Persist one terminal Attempt and publish Main State last.

    ``fault_injector`` is a narrow verification seam.  Raising from a named
    boundary simulates process loss; a retry with identical inputs resumes the
    immutable publication rather than re-running provider or tool calls.
    """

    project_root = Path(root).resolve()
    if not is_path_safe_identifier(attempt_id):
        raise CloseoutError("CLOSEOUT-ATTEMPT-ID", "attempt_id is not path-safe")
    if terminal_status not in _TERMINAL_STATUSES:
        raise CloseoutError("CLOSEOUT-STATUS", f"unsupported status: {terminal_status}")
    if not next_action.strip():
        raise CloseoutError("CLOSEOUT-NEXT-ACTION", "one bounded next action is required")
    _validate_timestamp_order(started_at, finished_at)

    specifications = _contract_specifications(
        protocol_ref=protocol_ref,
        task_ref=task_ref,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        previous_main_state_ref=previous_main_state_ref,
    )
    snapshots = contract_snapshots or capture_closeout_contracts(project_root, specifications)
    snapshot_map = _validated_snapshot_map(snapshots, specifications)
    _verify_live_contract_snapshots(project_root, snapshots)
    protocol_document = _snapshot_document(snapshot_map[protocol_ref])
    task_document = _snapshot_document(snapshot_map[task_ref])
    profile_document = _snapshot_document(snapshot_map[profile_ref])
    assignment_document = _snapshot_document(snapshot_map[assignment_ref])
    protocol = ProjectProtocol.from_mapping(protocol_document)
    task = TaskPacket.from_mapping(task_document)
    profile = AgentProfile.from_mapping(profile_document)
    assignment = ResolvedTask.from_mapping(assignment_document)
    _validate_identities(task, profile, assignment)
    _validate_closeout_permission(assignment)
    if not is_path_safe_identifier(task.task_id):
        raise CloseoutError("CLOSEOUT-TASK-ID", "task_id must be one path-safe segment")
    if terminal_status == "completed" and session_result is None:
        raise CloseoutError(
            "CLOSEOUT-SESSION-RESULT-MISSING",
            "a completed closeout requires the isolated API session result",
        )
    if session_result is not None:
        if (
            expected_provider_identity is None
            or session_result.provider != expected_provider_identity
        ):
            raise CloseoutError(
                "CLOSEOUT-PROVIDER-MISMATCH",
                "session canonical Provider differs from the approved Provider identity",
            )
        if session_result.requested_model != requested_model:
            raise CloseoutError(
                "CLOSEOUT-MODEL-MISMATCH",
                "session requested model differs from the closeout model",
            )

    normalized_status, operational_failure = _normalize_terminal_status(
        terminal_status=terminal_status,
        session_result=session_result,
        failure_code=failure_code,
        failure_summary=failure_summary,
    )
    if normalized_status != "completed":
        output = None
    elif output is None:
        raise CloseoutError("CLOSEOUT-OUTPUT-MISSING", "completed Attempt has no API output")
    else:
        validate_api_task_output(output, task=task, protocol=protocol)

    attempt_root = f"work/{task.task_id}/{attempt_id}"
    paths = _CloseoutPaths(attempt_root)
    _validate_output_paths(project_root, task, assignment, paths.static_final_paths)
    artifact_documents, artifact_refs_by_id = _prepare_artifacts(
        task=task,
        protocol=protocol,
        attempt_root=attempt_root,
        output=output,
        status=normalized_status,
    )
    # Artifact names are derived from untrusted model output and therefore
    # cannot be represented by a preflight placeholder.  Authorize the exact
    # resolved paths before creating even the temporary closeout tree.
    _validate_output_paths(project_root, task, assignment, tuple(artifact_documents))
    stage_parent, stage_root = _stage_locations(project_root, attempt_id, create=True)
    fault = fault_injector or (lambda _point: None)

    # Build a minimal overlay containing exact input/contract bytes plus the
    # candidate output tree.  Relationship checks can then run before anything
    # becomes reachable from the real project root.
    source_refs = [protocol_ref, task_ref, profile_ref, assignment_ref]
    if previous_main_state_ref:
        source_refs.append(previous_main_state_ref)
    for relative in _unique(source_refs):
        destination = _stage_path(stage_root, relative)
        snapshot = snapshot_map.get(relative)
        if snapshot is None:
            raise CloseoutError(
                "CLOSEOUT-CONTRACT-SNAPSHOT", f"no frozen closeout source for {relative}"
            )
        write_bytes_exclusive(destination, snapshot.payload)
    stale_failure = _expected_blockers(operational_failure)
    # A session result does not prove that Task inputs and selected Skills were
    # captured by the trusted compiler.  Only the explicit frozen-material
    # handoff from the pipeline authorizes live Skill-lock revalidation during
    # commit/resume.
    execution_material_locked = frozen_input_payloads is not None
    _stage_task_inputs(
        project_root=project_root,
        stage_root=stage_root,
        task=task,
        frozen_input_payloads=frozen_input_payloads,
        allow_stale=bool(stale_failure),
    )

    for relative, document in artifact_documents.items():
        _stage_document(stage_root, relative, document, "research_object")

    manifest_ref: str | None = None
    audit_ref: str | None = None
    manifest_document: dict[str, Any] | None = None
    if artifact_documents:
        if output is None or not output.get("transfer_items"):
            raise CloseoutError(
                "CLOSEOUT-TRANSFER-EMPTY",
                "persisted research artifacts require declared transfer items",
            )
        manifest_ref = paths.manifest
        manifest_document = _build_manifest(
            output=output,
            task=task,
            attempt_id=attempt_id,
            generated_at=finished_at,
            stage_root=stage_root,
            artifact_refs_by_id=artifact_refs_by_id,
        )
        _stage_document(stage_root, manifest_ref, manifest_document, "handoff_transfer_manifest")
        audit_ref = paths.audit

    handoff_document = _build_handoff(
        task=task,
        assignment=assignment,
        assignment_ref=assignment_ref,
        attempt_id=attempt_id,
        status=normalized_status,
        output=output,
        artifact_refs=tuple(artifact_documents),
        manifest_ref=manifest_ref,
        audit_ref=audit_ref,
        receipt_ref=paths.receipt,
        operational_failure=operational_failure,
        next_action=next_action,
    )
    _stage_document(stage_root, paths.handoff, handoff_document, "handoff_packet")

    audit_document: dict[str, Any] | None = None
    if manifest_document is not None and output is not None:
        audit_document = _build_audit(
            output=output,
            task_ref=task_ref,
            handoff_ref=paths.handoff,
            manifest_ref=paths.manifest,
            attempt_id=attempt_id,
            generated_at=finished_at,
            stage_root=stage_root,
        )
        _stage_document(stage_root, paths.audit, audit_document, "handoff_transfer_audit")

    unresolved_count = len(handoff_document["unresolved"])
    context_policy = ContextPolicySnapshot.from_project_policy(protocol.context_policy)
    task_context = _task_context_document(
        attempt_id=attempt_id,
        attempt_ref=paths.attempt,
        captured_at=finished_at,
        model_turns=session_result.model_turns if session_result else None,
        unresolved_count=unresolved_count,
        handoff_audit_ref=audit_ref,
        policy=context_policy,
    )
    _stage_document(stage_root, paths.task_context, task_context, "context_snapshot")

    attempt_document = _build_attempt(
        task=task,
        assignment=assignment,
        assignment_ref=assignment_ref,
        attempt_id=attempt_id,
        status=normalized_status,
        started_at=started_at,
        finished_at=finished_at,
        artifact_refs=tuple(artifact_documents) + ((manifest_ref,) if manifest_ref else ()),
        handoff_ref=paths.handoff,
        receipt_ref=paths.receipt,
        operational_failure=operational_failure,
    )
    _stage_document(stage_root, paths.attempt, attempt_document, "attempt")

    receipt_document = _build_receipt(
        task=task,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        attempt_ref=paths.attempt,
        context_ref=paths.task_context,
        status=normalized_status,
        started_at=started_at,
        finished_at=finished_at,
        receipt_id=f"XR-{attempt_id}",
        output_refs=tuple(artifact_documents)
        + ((manifest_ref,) if manifest_ref else ())
        + (paths.handoff,),
        validation_refs=((audit_ref,) if audit_ref else ()),
        provider_adapter_id=provider_adapter_id,
        requested_model=requested_model,
        provider_adapter_version=provider_adapter_version,
        session_result=session_result,
        limits=limits,
        operational_failure=operational_failure,
        external_provider=external_provider,
        extra_limitations=extra_limitations,
    )
    _stage_document(stage_root, paths.receipt, receipt_document, "execution_receipt")

    main_context = _main_context_document(
        attempt_id=attempt_id,
        project_id=protocol.project_id,
        captured_at=finished_at,
        unresolved_count=unresolved_count,
        policy=context_policy,
    )
    _stage_document(stage_root, paths.main_context, main_context, "context_snapshot")

    non_main_refs = tuple(artifact_documents) + tuple(
        relative
        for relative in (
            manifest_ref,
            paths.handoff,
            audit_ref,
            paths.task_context,
            paths.attempt,
            paths.receipt,
            paths.main_context,
        )
        if relative is not None
    )
    main_state_document = _build_main_state(
        stage_root=stage_root,
        protocol=protocol,
        protocol_ref=protocol_ref,
        task=task,
        task_ref=task_ref,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        attempt_id=attempt_id,
        status=normalized_status,
        next_action=next_action,
        handoff_ref=paths.handoff,
        main_context_ref=paths.main_context,
        artifact_refs=tuple(artifact_documents),
        machine_refs=non_main_refs,
        created_at=finished_at,
        operational_failure=operational_failure,
        previous_main_state_ref=previous_main_state_ref,
    )
    _stage_document(stage_root, paths.main_state, main_state_document, "main_state")

    allowed_blocking_codes = _expected_blockers(operational_failure)

    warnings = _validate_closeout_view(
        root=stage_root,
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=paths.receipt,
        main_state_document=main_state_document,
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed_blocking_codes,
    )
    publication_hashes = _write_stage_plan(
        stage_parent=stage_parent,
        stage_root=stage_root,
        attempt_id=attempt_id,
        protocol_ref=protocol_ref,
        task_ref=task_ref,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        provider_adapter_id=provider_adapter_id,
        requested_model=requested_model,
        attempt_ref=paths.attempt,
        main_state_ref=paths.main_state,
        publication_refs=(*non_main_refs, paths.main_state),
        execution_material_status="locked" if execution_material_locked else "unavailable",
        previous_main_state_ref=previous_main_state_ref,
    )
    _verify_live_contract_snapshots(project_root, snapshots)
    fault("after-stage-validation")

    published: list[str] = []
    for relative in non_main_refs:
        fault(f"before-publish:{relative}")
        publish_staged_file_exclusive(
            _stage_path(stage_root, relative),
            _final_path(project_root, relative),
        )
        published.append(relative)
        fault(f"after-publish:{relative}")

    # Re-run relationship checks in the real tree while Main State is still
    # absent.  Only a fully published and internally consistent immutable set
    # may become authoritative.
    warnings = _validate_closeout_view(
        root=project_root,
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=paths.receipt,
        main_state_document=main_state_document,
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed_blocking_codes,
    )
    fault("before-main-state-publish")
    _verify_published_hashes(project_root, non_main_refs, publication_hashes)
    warnings = _validate_closeout_view(
        root=project_root,
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=paths.receipt,
        main_state_document=main_state_document,
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed_blocking_codes,
    )
    _verify_live_staged_sources(
        project_root=project_root,
        stage_root=stage_root,
        task=task,
        main_state_document=main_state_document,
        attempt_root=attempt_root,
        main_state_ref=paths.main_state,
        allow_stale_inputs=bool(stale_failure),
    )
    if execution_material_locked:
        _verify_live_skill_locks(project_root, assignment)
    _verify_staged_hash(stage_root, paths.main_state, publication_hashes[paths.main_state])
    publish_staged_file_exclusive(
        _stage_path(stage_root, paths.main_state),
        _final_path(project_root, paths.main_state),
    )
    published.append(paths.main_state)
    fault("after-main-state-publish")

    _validate_closeout_view(
        root=project_root,
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=paths.receipt,
        main_state_document=_load_mapping(project_root, paths.main_state, "published Main State"),
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed_blocking_codes,
    )
    fault("after-final-validation")
    _remove_stage(project_root, stage_parent)
    return CloseoutPublication(
        status=normalized_status,
        main_state_ref=paths.main_state,
        published_refs=tuple(published),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True, slots=True)
class _CloseoutPaths:
    attempt_root: str

    @property
    def manifest(self) -> str:
        return f"{self.attempt_root}/transfer-manifest.yaml"

    @property
    def handoff(self) -> str:
        return f"{self.attempt_root}/handoff.yaml"

    @property
    def audit(self) -> str:
        return f"{self.attempt_root}/transfer-audit.yaml"

    @property
    def task_context(self) -> str:
        return f"{self.attempt_root}/context-task.yaml"

    @property
    def attempt(self) -> str:
        return f"{self.attempt_root}/attempt.yaml"

    @property
    def receipt(self) -> str:
        return f"{self.attempt_root}/execution-receipt.yaml"

    @property
    def main_context(self) -> str:
        return f"{self.attempt_root}/context-main.yaml"

    @property
    def main_state(self) -> str:
        return f"{self.attempt_root}/main-state.yaml"

    @property
    def static_final_paths(self) -> tuple[str, ...]:
        return (
            self.manifest,
            self.handoff,
            self.audit,
            self.task_context,
            self.attempt,
            self.receipt,
            self.main_context,
            self.main_state,
        )


def _prepare_artifacts(
    *,
    task: TaskPacket,
    protocol: ProjectProtocol,
    attempt_root: str,
    output: Mapping[str, Any] | None,
    status: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    if output is None:
        if status == "completed":
            raise CloseoutError("CLOSEOUT-OUTPUT-MISSING", "completed Attempt has no API output")
        return {}, {}
    raw_artifacts = output.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raise CloseoutError("CLOSEOUT-OUTPUT-CONTRACT", "artifacts must be an array")
    documents: dict[str, dict[str, Any]] = {}
    by_id: dict[str, str] = {}
    portable_object_ids: set[str] = set()
    evidence_count = 0
    for index, item in enumerate(raw_artifacts):
        if not isinstance(item, Mapping) or not isinstance(item.get("document"), Mapping):
            raise CloseoutError("CLOSEOUT-ARTIFACT", f"artifacts[{index}] lacks a document")
        document = dict(item["document"])
        _validate_schema("research_object", document)
        object_id = document.get("object_id")
        if not is_path_safe_identifier(object_id):
            raise CloseoutError("CLOSEOUT-OBJECT-ID", f"artifacts[{index}] object_id is not path-safe")
        portable_object_id = str(object_id).casefold()
        if portable_object_id in portable_object_ids:
            raise CloseoutError(
                "CLOSEOUT-OBJECT-DUPLICATE",
                f"object_id collides after portable path normalization: {object_id}",
            )
        portable_object_ids.add(portable_object_id)
        if document.get("object_type") == "claim":
            risks = check_claim_ceiling(protocol, str(document.get("strength", "")))
            blockers = [risk for risk in risks if risk.level == RiskLevel.BLOCK]
            if blockers:
                raise CloseoutError(blockers[0].code, blockers[0].message)
        if document.get("object_type") == "evidence":
            evidence_count += 1
        relative = f"{attempt_root}/artifacts/{object_id}.yaml"
        documents[relative] = document
        by_id[object_id] = relative
    required = {
        value if isinstance(value, str) else str(value.get("contract", ""))
        for value in task.required_outputs
    }
    if status == "completed" and "evidence-record" in required and evidence_count == 0:
        raise CloseoutError("CLOSEOUT-EVIDENCE-MISSING", "Task requires an Evidence record")
    if status == "completed" and not documents:
        raise CloseoutError("CLOSEOUT-ARTIFACT-MISSING", "completed Attempt has no research artifacts")
    return documents, by_id


def _build_manifest(
    *,
    output: Mapping[str, Any],
    task: TaskPacket,
    attempt_id: str,
    generated_at: str,
    stage_root: Path,
    artifact_refs_by_id: Mapping[str, str],
) -> dict[str, Any]:
    raw_items = output.get("transfer_items")
    if not isinstance(raw_items, list) or not raw_items:
        raise CloseoutError("CLOSEOUT-TRANSFER-EMPTY", "transfer_items must not be empty")
    item_ids: set[str] = set()
    source_paths: list[str] = []
    items: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, Mapping):
            raise CloseoutError("CLOSEOUT-TRANSFER-ITEM", f"transfer_items[{index}] is invalid")
        item_id = str(raw.get("item_id", ""))
        if not item_id or item_id in item_ids:
            raise CloseoutError("CLOSEOUT-TRANSFER-ITEM", f"duplicate or empty item_id: {item_id!r}")
        item_ids.add(item_id)
        object_id = str(raw.get("source_object_id", ""))
        try:
            source_path = artifact_refs_by_id[object_id]
        except KeyError as exc:
            raise CloseoutError(
                "CLOSEOUT-TRANSFER-SOURCE",
                f"{item_id} references unknown source_object_id {object_id!r}",
            ) from exc
        if source_path not in source_paths:
            source_paths.append(source_path)
        source_ref = {"path": source_path, "sha256": hash_file(_stage_path(stage_root, source_path))}
        items.append(
            {
                "item_id": item_id,
                "kind": raw.get("kind"),
                "criticality": raw.get("criticality"),
                "required_for_handoff": raw.get("required_for_handoff"),
                "statement": raw.get("statement"),
                "source_ref": source_ref,
                "source_locator": raw.get("source_locator"),
            }
        )
    document = {
        "schema_version": "0.1.0",
        "manifest_id": f"HTM-{attempt_id}",
        "task_id": task.task_id,
        "task_revision": task.revision,
        "attempt_id": attempt_id,
        "generated_at": generated_at,
        "declared_by": "task-agent",
        "source_artifact_refs": [
            {"path": path, "sha256": hash_file(_stage_path(stage_root, path))}
            for path in source_paths
        ],
        "items": items,
        "limitations": [
            "The Task agent declares transfer obligations; deterministic checks do not prove semantic completeness."
        ],
    }
    _validate_schema("handoff_transfer_manifest", document)
    return document


def _build_handoff(
    *,
    task: TaskPacket,
    assignment: ResolvedTask,
    assignment_ref: str,
    attempt_id: str,
    status: str,
    output: Mapping[str, Any] | None,
    artifact_refs: tuple[str, ...],
    manifest_ref: str | None,
    audit_ref: str | None,
    receipt_ref: str,
    operational_failure: Mapping[str, Any] | None,
    next_action: str,
) -> dict[str, Any]:
    if output is not None:
        raw_handoff = output.get("handoff")
        if not isinstance(raw_handoff, Mapping):
            raise CloseoutError("CLOSEOUT-HANDOFF", "API output lacks a Handoff body")
        result = dict(raw_handoff.get("result", {}))
        limitations = list(raw_handoff.get("limitations", []))
        conflicts = list(raw_handoff.get("conflicts", []))
        unresolved = list(raw_handoff.get("unresolved", []))
        human = list(raw_handoff.get("human_decision_required", []))
        actions = list(raw_handoff.get("recommended_next_actions", []))
    else:
        summary = (
            str(operational_failure.get("summary"))
            if operational_failure
            else f"Attempt ended with status {status} before admitting research artifacts."
        )
        result = {"summary": summary, "facts": [], "inferences": [], "recommendations": []}
        limitations = [summary]
        conflicts = []
        if status == "safe-paused":
            unresolved = ["The bounded Task has unfinished work and no admitted research artifact."]
        elif status == "incomplete":
            unresolved = [
                "The API result is incomplete; continue only with a new Attempt because the prior "
                "transcript is not resumable."
            ]
        else:
            unresolved = []
        human = []
        actions = [next_action]
    if status in {"safe-paused", "incomplete"} and not unresolved:
        unresolved.append(f"The bounded Task has unfinished work at the persisted {status} boundary.")
    if not actions:
        actions = [next_action]
    document: dict[str, Any] = {
        "schema_version": "0.1.0",
        "task_id": task.task_id,
        "attempt_id": attempt_id,
        "status": status,
        "input_lock": [_file_ref(reference.path, reference.sha256, reference.revision) for reference in task.input_refs],
        "skill_lock": [lock.identifier for lock in assignment.skill_lock],
        "skill_assignment_ref": assignment_ref,
        "result": result,
        "artifact_refs": list(artifact_refs),
        "validation_refs": [audit_ref] if audit_ref else [],
        "limitations": limitations,
        "conflicts": conflicts,
        "unresolved": unresolved,
        "human_decision_required": human,
        "recommended_next_actions": actions,
        "execution_receipt_ref": receipt_ref,
    }
    if manifest_ref:
        document["transfer_manifest_ref"] = manifest_ref
    _validate_schema("handoff_packet", document)
    HandoffPacket.from_mapping(document)
    return document


def _build_audit(
    *,
    output: Mapping[str, Any],
    task_ref: str,
    handoff_ref: str,
    manifest_ref: str,
    attempt_id: str,
    generated_at: str,
    stage_root: Path,
) -> dict[str, Any]:
    raw_items = output.get("transfer_items")
    assert isinstance(raw_items, list)
    document = {
        "schema_version": "0.1.0",
        "audit_id": f"HTA-{attempt_id}",
        "task_ref": {"path": task_ref, "sha256": hash_file(_stage_path(stage_root, task_ref))},
        "handoff_ref": {"path": handoff_ref, "sha256": hash_file(_stage_path(stage_root, handoff_ref))},
        "manifest_ref": {"path": manifest_ref, "sha256": hash_file(_stage_path(stage_root, manifest_ref))},
        "generated_at": generated_at,
        "mappings": [
            {
                "item_id": item["item_id"],
                "status": "carried",
                "handoff_locator": item["handoff_locator"],
            }
            for item in raw_items
        ],
        "review": {
            "status": "pending",
            "reviewer_kind": "none",
            "reviewer_independent": False,
            "sampled_item_ids": [],
            "findings": [],
        },
        "limitations": [
            "Structural transfer coverage was checked; semantic equivalence has not been independently reviewed."
        ],
    }
    _validate_schema("handoff_transfer_audit", document)
    return document


def _build_attempt(
    *,
    task: TaskPacket,
    assignment: ResolvedTask,
    assignment_ref: str,
    attempt_id: str,
    status: str,
    started_at: str,
    finished_at: str,
    artifact_refs: tuple[str, ...],
    handoff_ref: str,
    receipt_ref: str,
    operational_failure: Mapping[str, Any] | None,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "0.1.0",
        "task_id": task.task_id,
        "task_revision": task.revision,
        "attempt_id": attempt_id,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "trigger_reason": "bounded Task-to-API execution",
        "input_lock": [_file_ref(reference.path, reference.sha256, reference.revision) for reference in task.input_refs],
        "skill_lock": [lock.identifier for lock in assignment.skill_lock],
        "skill_assignment_ref": assignment_ref,
        "execution_receipt_ref": receipt_ref,
        "artifact_refs": list(artifact_refs),
        "handoff_ref": handoff_ref,
    }
    if operational_failure:
        document["failure"] = dict(operational_failure)
    _validate_schema("attempt", document)
    AttemptRecord.from_mapping(document)
    return document


def _build_receipt(
    *,
    task: TaskPacket,
    profile_ref: str,
    assignment_ref: str,
    attempt_ref: str,
    context_ref: str,
    status: str,
    started_at: str,
    finished_at: str,
    receipt_id: str,
    output_refs: tuple[str, ...],
    validation_refs: tuple[str, ...],
    provider_adapter_id: str,
    requested_model: str,
    provider_adapter_version: str,
    session_result: ApiSessionResult | None,
    limits: ApiSessionLimits,
    operational_failure: Mapping[str, Any] | None,
    external_provider: bool,
    extra_limitations: tuple[str, ...],
) -> dict[str, Any]:
    usage = session_result.usage if session_result else None
    usage_status = (
        "measured"
        if usage is not None and usage.input_tokens is not None and usage.output_tokens is not None
        else "unavailable"
    )
    model_usage: list[dict[str, Any]] = []
    if session_result is not None:
        model_counts = session_result.model_request_counts or tuple(
            (model, 1) for model in session_result.observed_models
        )
        if len(model_counts) <= 1:
            actual_model = model_counts[0][0] if model_counts else requested_model
            record: dict[str, Any] = {
                "provider": session_result.provider,
                "model": actual_model,
                "requests": session_result.model_turns,
            }
            for key in (
                "input_tokens",
                "output_tokens",
                "cached_input_tokens",
                "reasoning_tokens",
            ):
                value = getattr(usage, key)
                if value is not None:
                    record[key] = value
            if usage.provider_reported_cost is not None:
                record["provider_reported_cost"] = usage.provider_reported_cost
            if usage.currency is not None:
                record["currency"] = usage.currency
            model_usage.append(record)
        else:
            usage_status = "unavailable"
            model_usage.extend(
                {"provider": session_result.provider, "model": model, "requests": count}
                for model, count in model_counts
            )
    elapsed = max(
        0.0,
        (
            datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
            - datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        ).total_seconds(),
    )
    limitations = [
        "No transient provider transcript or provider response identifier was persisted.",
        (
            "Runtime limits are call-boundary and post-response guards; they do not cancel an in-flight "
            "provider or tool call. "
            f"Configured ceilings: turns={limits.max_model_turns}, tools={limits.max_tool_calls}, "
            f"per_turn_fanout={limits.max_parallel_tool_calls}, tool_result_chars={limits.max_tool_result_chars}, "
            f"output_tokens_per_turn={limits.max_output_tokens_per_turn}, seconds={limits.max_seconds}."
        ),
        *extra_limitations,
    ]
    if session_result is not None and len(session_result.model_request_counts) > 1:
        limitations.append(
            "Aggregate usage could not be attributed across multiple observed model identities."
        )
    if session_result is None:
        limitations.append(
            "Session aggregates are unavailable; zero Provider turns, token usage, or tool calls "
            "must not be inferred from this Receipt."
        )
    if operational_failure:
        limitations.append(
            f"Execution did not satisfy the Task contract: {operational_failure['code']}."
        )
    document = {
        "schema_version": "0.1.0",
        "receipt_id": receipt_id,
        "execution_kind": "model-api",
        "model_binding": {
            "provider_adapter_id": provider_adapter_id,
            "requested_model": requested_model,
        },
        "attempt_ref": attempt_ref,
        "task_id": task.task_id,
        "task_revision": task.revision,
        "agent_profile_ref": profile_ref,
        "skill_assignment_ref": assignment_ref,
        "context_snapshot_ref": context_ref,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "completion_claim": "contract-satisfied" if status == "completed" else "execution-only",
        "runtime": {
            "name": "isolated-api-session-runner",
            "version": "0.1.0",
            "adapter_version": provider_adapter_version or "unavailable",
        },
        "model_usage_status": usage_status,
        "model_usage": model_usage,
        "coordination": {
            "delegated_attempts": 0,
            "handoff_count": 1,
            "review_rounds": 0,
            "max_parallel_observed": 0,
            "execution_seconds": elapsed,
            **(
                {"execution_tokens": usage.total_tokens}
                if usage is not None and usage.total_tokens is not None
                else {}
            ),
        },
        "trace": {
            "mode": "minimal",
            "external": external_provider,
            "sensitive_data_detected": False,
            "redactions_applied": 0,
        },
        "output_refs": list(output_refs),
        "validation_refs": list(validation_refs),
        "limitations": limitations,
    }
    _validate_schema("execution_receipt", document)
    ExecutionReceipt.from_mapping(document)
    return document


def _task_context_document(
    *,
    attempt_id: str,
    attempt_ref: str,
    captured_at: str,
    model_turns: int | None,
    unresolved_count: int,
    handoff_audit_ref: str | None,
    policy: ContextPolicySnapshot,
) -> dict[str, Any]:
    metrics: dict[str, int] = {
        "open_items": unresolved_count,
        "compaction_events": 0,
        "hidden_decisions": 0,
    }
    if model_turns is not None:
        metrics["turns"] = model_turns
    unknown = tuple(sorted(set(CONTEXT_METRIC_NAMES) - set(metrics)))
    snapshot = ContextSnapshot.create(
        snapshot_id=f"CTX-TASK-{attempt_id}",
        captured_at=captured_at,
        scope="task",
        owner_ref=attempt_ref,
        measurement_source="mixed",
        metrics=metrics,
        unknown_metrics=unknown,
        handoff_ready=True,
        handoff_audit_ref=handoff_audit_ref,
        context_budget=ContextBudgetEstimate("unavailable"),
        policy=policy,
    )
    return snapshot.to_mapping()


def _main_context_document(
    *,
    attempt_id: str,
    project_id: str,
    captured_at: str,
    unresolved_count: int,
    policy: ContextPolicySnapshot,
) -> dict[str, Any]:
    metrics = {
        "raw_material_chars": 0,
        "recent_handoffs": 1,
        "open_items": unresolved_count,
        "turns": 0,
        "long_tool_outputs": 0,
        "compaction_events": 0,
        "hidden_decisions": 0,
    }
    unknown = tuple(sorted(set(CONTEXT_METRIC_NAMES) - set(metrics)))
    snapshot = ContextSnapshot.create(
        snapshot_id=f"CTX-MAIN-{attempt_id}",
        captured_at=captured_at,
        scope="main",
        owner_ref=project_id,
        measurement_source="file-estimate",
        metrics=metrics,
        unknown_metrics=unknown,
        handoff_ready=None,
        context_budget=ContextBudgetEstimate("unavailable"),
        policy=policy,
    )
    return snapshot.to_mapping()


def _build_main_state(
    *,
    stage_root: Path,
    protocol: ProjectProtocol,
    protocol_ref: str,
    task: TaskPacket,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    attempt_id: str,
    status: str,
    next_action: str,
    handoff_ref: str,
    main_context_ref: str,
    artifact_refs: tuple[str, ...],
    machine_refs: tuple[str, ...],
    created_at: str,
    operational_failure: Mapping[str, Any] | None,
    previous_main_state_ref: str | None,
) -> dict[str, Any]:
    previous: Mapping[str, Any] = {}
    if previous_main_state_ref:
        previous = _load_mapping(stage_root, previous_main_state_ref, "previous Main State")
        MainStatePacket.from_mapping(previous)
    constraints = list(previous.get("pinned_constraints", []))
    if protocol.data_boundary.get("local_only") and "local data must not be uploaded" not in constraints:
        constraints.append("local data must not be uploaded")
    claim_constraint = "claim ceiling: " + ", ".join(protocol.claim_ceiling)
    if claim_constraint not in constraints:
        constraints.append(claim_constraint)
    active_tasks = [
        item
        for item in previous.get("active_tasks", [])
        if isinstance(item, Mapping) and item.get("task_id") != task.task_id
    ]
    active_tasks.append({"task_id": task.task_id, "status": status, "expected_handoff": handoff_ref})
    recent = [item for item in previous.get("recent_handoffs", []) if isinstance(item, Mapping)]
    recent.append(
        {
            "ref": handoff_ref,
            "disposition": "accepted-closeout" if status == "completed" else f"{status}-recoverable",
        }
    )
    risks = list(previous.get("open_risks", []))
    if operational_failure and operational_failure["code"] not in risks:
        risks.append(str(operational_failure["code"]))
    if status == "completed" and "API-LIVE-CONFORMANCE-NOT-RUN" not in risks:
        risks.append("API-LIVE-CONFORMANCE-NOT-RUN")
    candidate_ref_paths = _unique(
        [
            protocol_ref,
            task_ref,
            profile_ref,
            assignment_ref,
            *(reference.path for reference in task.input_refs),
            *machine_refs,
            *( [previous_main_state_ref] if previous_main_state_ref else [] ),
        ]
    )
    ref_paths = [
        relative
        for relative in candidate_ref_paths
        if _stage_path(stage_root, relative).is_file()
    ]
    document: dict[str, Any] = {
        "schema_version": "0.1.0",
        "checkpoint_id": f"MS-{attempt_id}",
        "continuity_status": (
            "active" if status == "completed" else "safe-paused" if status == "safe-paused" else "blocked"
        ),
        "project_protocol_ref": f"{protocol_ref}@{protocol.revision}",
        "current_questions": list(protocol.question_refs),
        "pinned_constraints": constraints,
        "accepted_decisions": list(previous.get("accepted_decisions", [])),
        "active_tasks": active_tasks,
        "recent_handoffs": recent,
        "open_conflicts": list(previous.get("open_conflicts", [])),
        "open_risks": risks,
        "next_actions": [next_action],
        "artifact_index_refs": _unique(
            [*previous.get("artifact_index_refs", []), *artifact_refs]
        ),
        "machine_state_refs": [
            {"path": relative, "sha256": hash_file(_stage_path(stage_root, relative))}
            for relative in ref_paths
        ],
        "rollover_reason": "A fresh main session is required to prove file-only recovery after API closeout.",
        "created_at": created_at,
        "context_snapshot_ref": main_context_ref,
    }
    if previous_main_state_ref:
        document["previous_checkpoint_ref"] = previous_main_state_ref
    document["checkpoint_digest"] = checkpoint_digest(document)
    _validate_schema("main_state", document)
    MainStatePacket.from_mapping(document)
    return document


def _validate_closeout_view(
    *,
    root: Path,
    protocol: ProjectProtocol,
    task: TaskPacket,
    assignment: ResolvedTask,
    handoff_document: Mapping[str, Any],
    audit_document: Mapping[str, Any] | None,
    receipt_document: Mapping[str, Any],
    receipt_ref: str,
    main_state_document: Mapping[str, Any],
    protocol_ref: str,
    allowed_blocking_codes: frozenset[str],
) -> list[str]:
    warnings: list[str] = []
    handoff = HandoffPacket.from_mapping(handoff_document)
    handoff_risks = check_handoff_against_task(
        task,
        handoff,
        project_root=root,
        assignment=assignment,
    )
    _raise_blocking(handoff_risks, allowed=allowed_blocking_codes)
    warnings.extend(risk.code for risk in handoff_risks if risk.level == RiskLevel.WARNING)
    if audit_document is not None:
        assessment = assess_handoff_transfer(audit_document, root=root)
        _raise_blocking(assessment.risks)
        warnings.extend(risk.code for risk in assessment.risks if risk.level == RiskLevel.WARNING)
    receipt = ExecutionReceipt.from_mapping(receipt_document)
    receipt_risks = check_execution_receipt(receipt, protocol, root=root, receipt_ref=receipt_ref)
    _raise_blocking(receipt_risks)
    warnings.extend(risk.code for risk in receipt_risks if risk.level == RiskLevel.WARNING)
    _validate_main_state_view(
        root=root,
        document=main_state_document,
        protocol=protocol,
        protocol_ref=protocol_ref,
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
            is_explicit_downgrade = (
                terminal_status != "completed"
                and failure_code is not None
                and failure_summary is not None
            )
            if not is_explicit_downgrade:
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
    if status == "completed" and (code or summary):
        status = "failed"
    if status == "completed":
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


def _contract_specifications(
    *,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    previous_main_state_ref: str | None,
) -> tuple[tuple[str, str], ...]:
    specifications = [
        (protocol_ref, "project_protocol"),
        (task_ref, "task_packet"),
        (profile_ref, "agent_profile"),
        (assignment_ref, "skill_assignment"),
    ]
    if previous_main_state_ref is not None:
        specifications.append((previous_main_state_ref, "main_state"))
    return tuple(specifications)


def _validated_snapshot_map(
    snapshots: tuple[CloseoutContractSnapshot, ...],
    specifications: tuple[tuple[str, str], ...],
) -> dict[str, CloseoutContractSnapshot]:
    expected = dict(specifications)
    if len(expected) != len(specifications):
        raise CloseoutError("CLOSEOUT-CONTRACT-REF", "contract refs must be unique")
    actual: dict[str, CloseoutContractSnapshot] = {}
    for snapshot in snapshots:
        if snapshot.ref in actual:
            raise CloseoutError(
                "CLOSEOUT-CONTRACT-SNAPSHOT", f"duplicate snapshot for {snapshot.ref}"
            )
        if expected.get(snapshot.ref) != snapshot.kind:
            raise CloseoutError(
                "CLOSEOUT-CONTRACT-SNAPSHOT",
                f"snapshot identity or kind differs for {snapshot.ref}",
            )
        _snapshot_document(snapshot)
        actual[snapshot.ref] = snapshot
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise CloseoutError(
            "CLOSEOUT-CONTRACT-SNAPSHOT",
            f"snapshot set differs; missing={missing}, extra={extra}",
        )
    return actual


def _snapshot_document(snapshot: CloseoutContractSnapshot) -> Mapping[str, Any]:
    if hashlib.sha256(snapshot.payload).hexdigest() != snapshot.sha256:
        raise CloseoutError(
            "CLOSEOUT-CONTRACT-SNAPSHOT", f"snapshot digest differs for {snapshot.ref}"
        )
    try:
        text = snapshot.payload.decode("utf-8")
        suffix = PurePosixPath(snapshot.ref).suffix.lower()
        if suffix == ".json":
            value = json.loads(text)
        elif suffix in {".yaml", ".yml"}:
            value = yaml.safe_load(text)
        else:
            raise CloseoutError(
                "CLOSEOUT-CONTRACT-REF", f"unsupported contract suffix: {snapshot.ref}"
            )
    except (UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise CloseoutError(
            "CLOSEOUT-CONTRACT-PARSE",
            f"contract cannot be parsed as UTF-8 structured data: {snapshot.ref}",
        ) from exc
    if not isinstance(value, Mapping):
        raise CloseoutError(
            "CLOSEOUT-CONTRACT-PARSE", f"contract must be an object: {snapshot.ref}"
        )
    errors = SchemaCatalog().validate(snapshot.kind, value)
    if errors:
        first = errors[0]
        raise CloseoutError(
            "CLOSEOUT-CONTRACT-SCHEMA",
            f"{snapshot.ref}{first.pointer}: {first.message}",
        )
    return value


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


def _stage_document(root: Path, relative: str, document: Mapping[str, Any], kind: str) -> None:
    _validate_schema(kind, document)
    write_yaml_exclusive(_stage_path(root, relative), document)


def _validate_schema(kind: str, document: Mapping[str, Any]) -> None:
    errors = SchemaCatalog().validate(kind, document)
    if errors:
        first = errors[0]
        raise CloseoutError("CLOSEOUT-SCHEMA", f"{kind} {first.pointer}: {first.message}")


def _load_mapping(root: Path, relative: str, label: str) -> Mapping[str, Any]:
    resolved = resolve_within_root(root, relative)
    if resolved is None or not resolved.is_file():
        raise CloseoutError("REF-MISSING", f"{label} does not exist within project: {relative}")
    value = load_document(resolved)
    if not isinstance(value, Mapping):
        raise CloseoutError("DOCUMENT-INVALID", f"{label} must be an object: {relative}")
    return value


def _resolve_existing(root: Path, relative: str, label: str) -> Path:
    resolved = resolve_within_root(root, relative)
    if resolved is None or not resolved.is_file():
        raise CloseoutError("REF-MISSING", f"{label} does not exist: {relative}")
    return resolved


def _stage_path(root: Path, relative: str) -> Path:
    resolved = resolve_within_root(root, relative)
    if resolved is None:
        raise CloseoutError("REF-OUTSIDE-ROOT", relative)
    return resolved


def _stage_locations(
    project_root: Path,
    attempt_id: str,
    *,
    create: bool,
) -> tuple[Path, Path]:
    project = project_root.resolve()
    rw_root = project / ".rwb"
    closeout_root = rw_root / "closeout"
    stage_parent = closeout_root / attempt_id
    stage_root = stage_parent / "tree"
    for path in (rw_root, closeout_root, stage_parent, stage_root):
        if path.is_symlink():
            raise CloseoutError(
                "CLOSEOUT-STAGE-PATH",
                f"staging components must not be symlinks: {path}",
            )
    if create:
        stage_root.mkdir(parents=True, exist_ok=True)
    if stage_parent.exists() and not stage_parent.is_dir():
        raise CloseoutError("CLOSEOUT-STAGE-PATH", "attempt stage is not a directory")
    if stage_root.exists() and not stage_root.is_dir():
        raise CloseoutError("CLOSEOUT-STAGE-PATH", "stage tree is not a directory")
    resolved_closeout = closeout_root.resolve()
    resolved_parent = stage_parent.resolve()
    try:
        resolved_parent.relative_to(resolved_closeout)
        resolved_closeout.relative_to(project)
    except ValueError as exc:
        raise CloseoutError("CLOSEOUT-STAGE-PATH", "staging path escapes the project") from exc
    return stage_parent, stage_root


def _stage_task_inputs(
    *,
    project_root: Path,
    stage_root: Path,
    task: TaskPacket,
    frozen_input_payloads: Mapping[str, bytes] | None,
    allow_stale: bool,
) -> None:
    expected_paths = {reference.path for reference in task.input_refs}
    supplied = dict(frozen_input_payloads or {})
    if frozen_input_payloads is not None and set(supplied) != expected_paths:
        raise CloseoutError(
            "CLOSEOUT-INPUT-SNAPSHOT",
            "frozen Task input payloads do not exactly match Task input_refs",
        )
    for reference in task.input_refs:
        if reference.path in supplied:
            payload = supplied[reference.path]
            if not isinstance(payload, bytes):
                raise CloseoutError(
                    "CLOSEOUT-INPUT-SNAPSHOT", f"frozen input is not bytes: {reference.path}"
                )
        else:
            resolved = resolve_within_root(project_root, reference.path)
            if resolved is None or not resolved.is_file():
                if allow_stale:
                    continue
                raise CloseoutError("REF-MISSING", f"Task input does not exist: {reference.path}")
            payload = resolved.read_bytes()
        expected_hash = reference.sha256.removeprefix("sha256:").lower()
        if hashlib.sha256(payload).hexdigest() != expected_hash and not allow_stale:
            raise CloseoutError("TASK-STALE-INPUT", f"Task input hash differs: {reference.path}")
        write_bytes_exclusive(_stage_path(stage_root, reference.path), payload)


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


def _write_stage_plan(
    *,
    stage_parent: Path,
    stage_root: Path,
    attempt_id: str,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    provider_adapter_id: str,
    requested_model: str,
    attempt_ref: str,
    main_state_ref: str,
    publication_refs: tuple[str, ...],
    execution_material_status: str,
    previous_main_state_ref: str | None,
) -> dict[str, str]:
    attempt_path = _stage_path(stage_root, attempt_ref)
    main_state_path = _stage_path(stage_root, main_state_ref)
    publication_hashes = {
        relative: hash_file(_stage_path(stage_root, relative)) for relative in publication_refs
    }
    write_yaml_exclusive(
        stage_parent / "plan.yaml",
        {
            "version": 3,
            "attempt_id": attempt_id,
            "protocol_ref": protocol_ref,
            "task_ref": task_ref,
            "profile_ref": profile_ref,
            "assignment_ref": assignment_ref,
            "provider_adapter_id": provider_adapter_id,
            "requested_model": requested_model,
            "attempt_ref": attempt_ref,
            "attempt_sha256": hash_file(attempt_path),
            "main_state_ref": main_state_ref,
            "main_state_sha256": hash_file(main_state_path),
            "execution_material_status": execution_material_status,
            "previous_main_state_ref": previous_main_state_ref,
            "publication_hashes": publication_hashes,
        },
    )
    return publication_hashes


def _load_stage_plan(stage_parent: Path, stage_root: Path, attempt_id: str) -> dict[str, Any]:
    plan_path = stage_parent / "plan.yaml"
    if not plan_path.is_file():
        raise CloseoutError(
            "CLOSEOUT-STAGE-INCOMPLETE",
            "staged closeout has no validated publication plan",
        )
    value = load_document(plan_path)
    required_strings = (
        "attempt_id",
        "protocol_ref",
        "task_ref",
        "profile_ref",
        "assignment_ref",
        "provider_adapter_id",
        "requested_model",
        "attempt_ref",
        "attempt_sha256",
        "main_state_ref",
        "main_state_sha256",
        "execution_material_status",
    )
    if not isinstance(value, Mapping) or value.get("version") != 3:
        raise CloseoutError("CLOSEOUT-STAGE-INCOMPLETE", "stage plan version is invalid")
    if any(not isinstance(value.get(key), str) or not value[key] for key in required_strings):
        raise CloseoutError("CLOSEOUT-STAGE-INCOMPLETE", "stage plan fields are invalid")
    plan: dict[str, Any] = {key: str(value[key]) for key in required_strings}
    if "previous_main_state_ref" not in value:
        raise CloseoutError(
            "CLOSEOUT-STAGE-INCOMPLETE",
            "stage previous Main State identity is missing",
        )
    previous_main_state_ref = value.get("previous_main_state_ref")
    if previous_main_state_ref is not None and (
        not isinstance(previous_main_state_ref, str) or not previous_main_state_ref
    ):
        raise CloseoutError(
            "CLOSEOUT-STAGE-INCOMPLETE",
            "stage previous Main State reference is invalid",
        )
    plan["previous_main_state_ref"] = previous_main_state_ref
    if plan["execution_material_status"] not in {"locked", "unavailable"}:
        raise CloseoutError(
            "CLOSEOUT-STAGE-INCOMPLETE", "stage execution material status is invalid"
        )
    raw_hashes = value.get("publication_hashes")
    if not isinstance(raw_hashes, Mapping) or not raw_hashes:
        raise CloseoutError("CLOSEOUT-STAGE-INCOMPLETE", "stage publication hashes are missing")
    publication_hashes: dict[str, str] = {}
    for ref, digest in raw_hashes.items():
        if not isinstance(ref, str) or not ref or not isinstance(digest, str) or not digest:
            raise CloseoutError(
                "CLOSEOUT-STAGE-INCOMPLETE", "stage publication hashes are invalid"
            )
        publication_hashes[ref] = digest.removeprefix("sha256:").lower()
    plan["publication_hashes"] = publication_hashes
    if plan["attempt_id"] != attempt_id:
        raise CloseoutError("CLOSEOUT-STAGE-IDENTITY", "stage plan Attempt ID differs")
    for ref_key, hash_key in (
        ("attempt_ref", "attempt_sha256"),
        ("main_state_ref", "main_state_sha256"),
    ):
        path = _stage_path(stage_root, plan[ref_key])
        if not path.is_file() or hash_file(path) != plan[hash_key].removeprefix("sha256:").lower():
            raise CloseoutError("CLOSEOUT-STAGE-DRIFT", f"stage plan hash differs: {ref_key}")
    for relative, digest in publication_hashes.items():
        _verify_staged_hash(stage_root, relative, digest)
    return plan


def _raise_if_execution_intent_is_incomplete(
    project_root: Path,
    *,
    attempt_id: str,
    task_id: str,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    provider_adapter_id: str,
    requested_model: str,
    previous_main_state_ref: str | None,
) -> None:
    intent_path = _attempt_intent_path(project_root, attempt_id, create=False)
    if not intent_path.is_file():
        return
    value = load_document(intent_path)
    expected = {
        "version": 2,
        "attempt_id": attempt_id,
        "task_id": task_id,
        "protocol_ref": protocol_ref,
        "task_ref": task_ref,
        "profile_ref": profile_ref,
        "assignment_ref": assignment_ref,
        "provider_adapter_id": provider_adapter_id,
        "requested_model": requested_model,
        "previous_main_state_ref": previous_main_state_ref,
    }
    if not isinstance(value, Mapping) or any(value.get(key) != item for key, item in expected.items()):
        raise CloseoutError(
            "CLOSEOUT-STAGE-IDENTITY",
            "execution intent belongs to different Task or runtime contracts",
        )
    raise CloseoutError(
        "API-ATTEMPT-RESULT-UNKNOWN",
        "execution intent exists without a validated closeout plan; automatic replay is forbidden",
    )


def _attempt_intent_path(project_root: Path, attempt_id: str, *, create: bool) -> Path:
    if not is_path_safe_identifier(attempt_id):
        raise CloseoutError("CLOSEOUT-ATTEMPT-ID", "attempt_id is not path-safe")
    project = project_root.resolve()
    rw_root = project / ".rwb"
    intent_root = rw_root / "attempt-intents"
    intent_path = intent_root / f"{attempt_id}.yaml"
    for path in (rw_root, intent_root, intent_path):
        if path.is_symlink():
            raise CloseoutError(
                "API-ATTEMPT-INTENT-PATH",
                f"execution intent components must not be symlinks: {path}",
            )
    if create:
        intent_root.mkdir(parents=True, exist_ok=True)
    if intent_root.exists() and not intent_root.is_dir():
        raise CloseoutError("API-ATTEMPT-INTENT-PATH", "intent root is not a directory")
    resolved_root = intent_root.resolve()
    resolved_path = intent_path.resolve()
    try:
        resolved_root.relative_to(project)
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise CloseoutError("API-ATTEMPT-INTENT-PATH", "intent path escapes the project") from exc
    return intent_path


def _final_path(root: Path, relative: str) -> Path:
    resolved = resolve_within_root(root, relative)
    if resolved is None:
        raise CloseoutError("REF-OUTSIDE-ROOT", relative)
    return resolved


def _file_ref(path: str, sha256: str, revision: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"path": path, "sha256": sha256}
    if revision is not None:
        value["revision"] = revision
    return value


def _unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


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


def _remove_stage(project_root: Path, stage_parent: Path) -> None:
    resolved_project = project_root.resolve()
    resolved_stage = stage_parent.resolve()
    expected_parent = (resolved_project / ".rwb" / "closeout").resolve()
    try:
        resolved_stage.relative_to(expected_parent)
    except ValueError as exc:
        raise CloseoutError("CLOSEOUT-STAGE-PATH", "refusing to remove an unexpected stage path") from exc
    if resolved_stage == expected_parent:
        raise CloseoutError("CLOSEOUT-STAGE-PATH", "refusing to remove the closeout root")
    shutil.rmtree(resolved_stage, ignore_errors=False)
