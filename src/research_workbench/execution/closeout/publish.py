"""Commit-last closeout entry points: capture, stage, publish, resume, inspect."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from research_workbench.adapters.models import ApiSessionLimits, ApiSessionResult
from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.context import ContextPolicySnapshot, MainStatePacket
from research_workbench.contracts import is_path_safe_identifier
from research_workbench.execution.output import validate_api_task_output
from research_workbench.io import publish_staged_file_exclusive, write_bytes_exclusive
from research_workbench.observability import ExecutionReceipt
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import AttemptRecord, HandoffPacket, TaskPacket

from .builders import (
    _build_attempt,
    _build_audit,
    _build_handoff,
    _build_main_state,
    _build_manifest,
    _build_receipt,
    _contract_specifications,
    _main_context_document,
    _prepare_artifacts,
    _task_context_document,
    _validated_snapshot_map,
)
from .documents import (
    _load_mapping,
    _resolve_existing,
    _snapshot_document,
    _stage_document,
    _unique,
)
from .errors import (
    CloseoutContractSnapshot,
    CloseoutError,
    CloseoutPublication,
    _TERMINAL_STATUSES,
)
from .paths import _CloseoutPaths, _final_path, _stage_locations, _stage_path
from .stage import (
    _load_stage_plan,
    _raise_if_execution_intent_is_incomplete,
    _remove_stage,
    _stage_task_inputs,
    _write_stage_plan,
)
from .verify import (
    _ViewCheck,
    _expected_blockers,
    _normalize_terminal_status,
    _require_canonical_contract_ref,
    _validate_closeout_permission,
    _validate_identities,
    _validate_main_state_view,
    _validate_output_paths,
    _validate_timestamp_order,
    _verify_live_contract_snapshots,
    _verify_live_skill_locks,
    _verify_live_staged_sources,
    _verify_published_hashes,
    _verify_staged_hash,
)

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
    view = _ViewCheck(
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=receipt_ref,
        main_state_ref=main_state_ref,
        main_state_document=main_state_document,
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed,
    )
    warnings = view.at(stage_root)
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
    warnings = view.at(project_root)
    fault("before-main-state-publish")
    _verify_published_hashes(project_root, output_refs, publication_hashes)
    warnings = view.at(project_root)
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
    view.at(project_root, reload_main_state=True)
    fault("after-final-validation")
    _remove_stage(project_root, stage_parent)
    return CloseoutPublication(
        status=attempt.status,
        main_state_ref=main_state_ref,
        published_refs=tuple(published),
        warnings=tuple(warnings),
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
    view = _ViewCheck(
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=receipt_ref,
        main_state_ref=paths.main_state,
        main_state_document=main_state_document,
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed,
    )
    warnings = view.at(project_root)
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

    view = _ViewCheck(
        protocol=protocol,
        task=task,
        assignment=assignment,
        handoff_document=handoff_document,
        audit_document=audit_document,
        receipt_document=receipt_document,
        receipt_ref=paths.receipt,
        main_state_ref=paths.main_state,
        main_state_document=main_state_document,
        protocol_ref=protocol_ref,
        allowed_blocking_codes=allowed_blocking_codes,
    )
    warnings = view.at(stage_root)
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
    warnings = view.at(project_root)
    fault("before-main-state-publish")
    _verify_published_hashes(project_root, non_main_refs, publication_hashes)
    warnings = view.at(project_root)
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

    view.at(project_root, reload_main_state=True)
    fault("after-final-validation")
    _remove_stage(project_root, stage_parent)
    return CloseoutPublication(
        status=normalized_status,
        main_state_ref=paths.main_state,
        published_refs=tuple(published),
        warnings=tuple(warnings),
    )
