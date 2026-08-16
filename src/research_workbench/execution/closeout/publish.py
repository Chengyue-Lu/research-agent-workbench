"""Commit-last closeout entry points: capture, stage, publish, resume, inspect."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from research_workbench.adapters.models import (
    ApiSessionLimits,
    ApiSessionResult,
    DataPolicy,
    ModelAssignment,
)
from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.context import ContextPolicySnapshot, MainStatePacket
from research_workbench.contracts import is_path_safe_identifier
from research_workbench.execution.output import validate_api_task_output
from research_workbench.execution.contracts import (
    ContractAdmission,
    EvidenceH2ExecutionContract,
    ExecutionArtifact,
    ExecutionContract,
    ExecutionContractError,
    default_execution_contract_registry,
)
from research_workbench.io import publish_staged_file_exclusive, write_bytes_exclusive
from research_workbench.observability import ExecutionReceipt
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import AttemptRecord, FileReference, HandoffPacket, TaskPacket
from research_workbench.validation import SchemaCatalog

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


class AgentTraceSealer(Protocol):
    """Trusted bridge that seals runtime Trace bytes against staged closeout files."""

    def __call__(
        self,
        *,
        stage_root: Path,
        handoff_refs: tuple[str, ...],
        decision_refs: tuple[str, ...],
        output_refs: tuple[str, ...],
        check_refs: tuple[str, ...],
    ) -> tuple[FileReference, Mapping[str, bytes]]: ...


def _protocol_data_policy(protocol: ProjectProtocol) -> DataPolicy:
    """Derive the protocol policy again at the closeout trust boundary."""

    boundary = protocol.data_boundary
    supported = {
        "local_only",
        "external_upload_requires_approval",
        "zero_data_retention_required",
        "training_opt_out_required",
        "allowed_regions",
        "allow_provider_server_tools",
    }
    if set(boundary) - supported:
        raise CloseoutError(
            "PROJECT-DATA-BOUNDARY", "Project Protocol has unsupported data-boundary fields"
        )
    boolean_fields = (
        "local_only",
        "external_upload_requires_approval",
        "zero_data_retention_required",
        "training_opt_out_required",
        "allow_provider_server_tools",
    )
    if any(not isinstance(boundary.get(field, False), bool) for field in boolean_fields):
        raise CloseoutError(
            "PROJECT-DATA-BOUNDARY", "Project Protocol data-boundary flags must be boolean"
        )
    regions = boundary.get("allowed_regions", [])
    if not isinstance(regions, list) or any(
        not isinstance(region, str) or not region for region in regions
    ):
        raise CloseoutError(
            "PROJECT-DATA-BOUNDARY", "Project Protocol allowed_regions must be strings"
        )
    return DataPolicy(
        local_only=boundary.get("local_only", False),
        zero_data_retention_required=boundary.get("zero_data_retention_required", False),
        training_opt_out_required=boundary.get("training_opt_out_required", False),
        allowed_regions=tuple(regions),
        allow_provider_server_tools=boundary.get("allow_provider_server_tools", False),
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


def _contract_output_ref(attempt_root: str, relative_name: str) -> str:
    if (
        not isinstance(relative_name, str)
        or not relative_name
        or "\\" in relative_name
        or PurePosixPath(relative_name).is_absolute()
        or ".." in PurePosixPath(relative_name).parts
        or PurePosixPath(relative_name).as_posix() != relative_name
    ):
        raise CloseoutError(
            "EXECUTION-CONTRACT-PATH", "ExecutionContract output name is not canonical"
        )
    return f"{attempt_root}/{relative_name}"


def _agent_trace_material_paths(
    index: Mapping[str, Any],
    index_path: str,
) -> set[str]:
    archive_root = index.get("archive_root")
    if not isinstance(archive_root, str) or not archive_root:
        raise CloseoutError("AGENT-TRACE-IDENTITY", "Trace archive_root is unavailable")
    paths = {index_path}

    def add_ref(value: object) -> None:
        if not isinstance(value, Mapping):
            return
        path = value.get("path")
        if isinstance(path, str) and (
            path == archive_root or path.startswith(archive_root.rstrip("/") + "/")
        ):
            paths.add(path)

    add_ref(index.get("actors_ref"))
    add_ref(index.get("event_ledger"))
    # Closeout refs are hash-bound dependencies of the index, not Trace-owned
    # payloads.  They are staged and published by the closeout transaction.
    for key in ("messages", "tool_event_refs"):
        values = index.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            add_ref(value)
            if isinstance(value, Mapping):
                attachments = value.get("attachment_refs", [])
                if isinstance(attachments, list):
                    for attachment in attachments:
                        add_ref(attachment)
    return paths


def _validate_frozen_agent_trace_bundle(
    *,
    content_root: Path,
    project_root: Path,
    attempt_root: str,
    task: TaskPacket,
    assignment: ResolvedTask,
    normalized_status: str,
    index_ref: FileReference,
    payloads: Mapping[str, bytes],
) -> Mapping[str, Any]:
    """Verify Trace-owned bytes without absorbing closeout-owned dependencies."""

    if index_ref.path != f"{attempt_root}/INDEX.yaml":
        raise CloseoutError(
            "AGENT-TRACE-IDENTITY",
            "Agent Trace index is outside the canonical Attempt root",
        )
    if index_ref.path not in payloads:
        raise CloseoutError(
            "AGENT-TRACE-BUNDLE-MISSING",
            "Agent Trace index is absent from its frozen bundle",
        )
    for relative, payload in payloads.items():
        if not (relative == attempt_root or relative.startswith(attempt_root + "/")):
            raise CloseoutError(
                "AGENT-TRACE-IDENTITY",
                f"Agent Trace material escapes the Attempt root: {relative}",
            )
        if not isinstance(payload, bytes):
            raise CloseoutError(
                "AGENT-TRACE-BUNDLE-DRIFT",
                f"Agent Trace payload is not frozen bytes: {relative}",
            )
        live = resolve_within_root(content_root, relative)
        if (
            live is None
            or not live.is_file()
            or live.is_symlink()
            or live.read_bytes() != payload
        ):
            raise CloseoutError(
                "AGENT-TRACE-BUNDLE-DRIFT",
                f"Agent Trace material drifted before closeout: {relative}",
            )
    if hashlib.sha256(payloads[index_ref.path]).hexdigest() != index_ref.sha256:
        raise CloseoutError(
            "AGENT-TRACE-BUNDLE-DRIFT",
            "Agent Trace index digest differs from its frozen reference",
        )
    trace_index = _load_mapping(
        content_root,
        index_ref.path,
        "sealed Agent Trace Index",
    )
    if set(payloads) != _agent_trace_material_paths(trace_index, index_ref.path):
        raise CloseoutError(
            "AGENT-TRACE-BUNDLE-DRIFT",
            "frozen Agent Trace payloads differ from Trace-owned indexed material",
        )
    if (
        trace_index.get("task_id"),
        trace_index.get("task_revision"),
        trace_index.get("attempt_id"),
        trace_index.get("attempt_status"),
        trace_index.get("trace_status"),
    ) != (
        task.task_id,
        task.revision,
        attempt_root.rsplit("/", 1)[-1],
        normalized_status,
        "frozen",
    ):
        raise CloseoutError(
            "AGENT-TRACE-IDENTITY",
            "Agent Trace identity or terminal status differs from closeout",
        )
    _validate_output_paths(
        project_root,
        task,
        assignment,
        tuple(sorted(payloads)),
    )
    return trace_index


def _prepare_admitted_artifacts(
    *,
    attempt_root: str,
    artifacts: tuple[ExecutionArtifact, ...],
) -> tuple[dict[str, dict[str, Any]], dict[str, str], dict[str, str]]:
    documents: dict[str, dict[str, Any]] = {}
    refs_by_id: dict[str, str] = {}
    kinds: dict[str, str] = {}
    for artifact in artifacts:
        relative = _contract_output_ref(attempt_root, artifact.relative_name)
        if relative in documents:
            raise CloseoutError(
                "EXECUTION-CONTRACT-PATH", f"duplicate contract artifact path: {relative}"
            )
        document = dict(artifact.document)
        documents[relative] = document
        kinds[relative] = artifact.document_kind
        object_id = document.get("object_id")
        if isinstance(object_id, str) and object_id:
            if object_id in refs_by_id:
                raise CloseoutError(
                    "EXECUTION-CONTRACT-ARTIFACT", f"duplicate artifact identity: {object_id}"
                )
            refs_by_id[object_id] = relative
    return documents, refs_by_id, kinds


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
    expected_model_assignment_id: str,
    expected_execution_contract: str,
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
            model_assignment_id=expected_model_assignment_id,
            execution_contract=expected_execution_contract,
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
                model_assignment_id=expected_model_assignment_id,
                execution_contract=expected_execution_contract,
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
        "model_assignment_id": expected_model_assignment_id,
        "execution_contract": expected_execution_contract,
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
    if receipt.execution_contract != expected_execution_contract:
        raise CloseoutError(
            "CLOSEOUT-STAGE-IDENTITY", "stage plan and Receipt ExecutionContract differ"
        )
    planned_model_ref = plan.get("model_assignment_ref")
    if (
        (planned_model_ref is None) != (receipt.model_assignment_ref is None)
        or (
            isinstance(planned_model_ref, FileReference)
            and receipt.model_assignment_ref is not None
            and (
                planned_model_ref.path,
                planned_model_ref.sha256,
            )
            != (
                receipt.model_assignment_ref.path,
                receipt.model_assignment_ref.sha256,
            )
        )
    ):
        raise CloseoutError(
            "CLOSEOUT-STAGE-IDENTITY",
            "stage plan and Receipt Model Assignment reference differ",
        )
    if expected_model_assignment_id != "unavailable":
        if receipt.model_assignment_ref is None:
            raise CloseoutError(
                "CLOSEOUT-STAGE-INCOMPLETE", "Receipt omits the Model Assignment"
            )
        staged_model_assignment = ModelAssignment.from_mapping(
            _load_mapping(
                stage_root,
                receipt.model_assignment_ref.path,
                "staged Model Assignment",
            )
        )
        if staged_model_assignment.model_assignment_id != expected_model_assignment_id:
            raise CloseoutError(
                "CLOSEOUT-STAGE-IDENTITY", "staged Model Assignment identity differs"
            )
    assignment = ResolvedTask.from_mapping(
        _load_mapping(stage_root, receipt.skill_assignment_ref, "staged Skill Assignment")
    )
    handoff_document = _load_mapping(stage_root, attempt.handoff_ref, "staged Handoff")
    handoff = HandoffPacket.from_mapping(handoff_document)
    audit_document: Mapping[str, Any] | None = None
    if handoff.transfer_manifest_ref:
        if canonical_paths.audit not in handoff.validation_refs:
            raise CloseoutError(
                "CLOSEOUT-STAGE-INCOMPLETE", "H2 Handoff omits its Transfer Audit"
            )
        audit_document = _load_mapping(
            stage_root, canonical_paths.audit, "staged Transfer Audit"
        )
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
    if receipt.model_assignment_ref is not None:
        required.add(receipt.model_assignment_ref.path)
    if receipt.agent_trace_index_ref is not None:
        required.add(receipt.agent_trace_index_ref.path)
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
    expected_model_assignment_id: str,
    expected_execution_contract: str,
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
    if receipt.execution_contract != expected_execution_contract:
        raise CloseoutError(
            "CLOSEOUT-COMMITTED-IDENTITY",
            "committed Receipt has a different ExecutionContract",
        )
    if expected_model_assignment_id != "unavailable":
        if receipt.model_assignment_ref is None:
            raise CloseoutError(
                "CLOSEOUT-COMMITTED-INCOMPLETE",
                "committed Receipt omits its Model Assignment",
            )
        committed_model_assignment = ModelAssignment.from_mapping(
            _load_mapping(
                project_root,
                receipt.model_assignment_ref.path,
                "committed Model Assignment",
            )
        )
        if committed_model_assignment.model_assignment_id != expected_model_assignment_id:
            raise CloseoutError(
                "CLOSEOUT-COMMITTED-IDENTITY",
                "committed Model Assignment identity differs",
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
    if handoff.transfer_manifest_ref:
        if paths.audit not in handoff.validation_refs:
            raise CloseoutError(
                "CLOSEOUT-COMMITTED-INCOMPLETE", "H2 Handoff omits its Transfer Audit"
            )
        audit_document = _load_mapping(
            project_root,
            paths.audit,
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
    if receipt.model_assignment_ref is not None:
        required_refs.add(receipt.model_assignment_ref.path)
    if receipt.agent_trace_index_ref is not None:
        required_refs.add(receipt.agent_trace_index_ref.path)
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
    provider_conformance_document: Mapping[str, Any] | None = None,
    provider_conformance_expected_sha256: str | None = None,
    extra_limitations: tuple[str, ...] = (),
    fault_injector: Callable[[str], None] | None = None,
    contract_snapshots: tuple[CloseoutContractSnapshot, ...] | None = None,
    frozen_input_payloads: Mapping[str, bytes] | None = None,
    frozen_contract_payloads: Mapping[str, bytes] | None = None,
    execution_contract: ExecutionContract | None = None,
    admission: ContractAdmission | None = None,
    model_assignment: ModelAssignment | None = None,
    agent_trace_index_ref: FileReference | None = None,
    frozen_agent_trace_payloads: Mapping[str, bytes] | None = None,
    agent_trace_sealer: AgentTraceSealer | None = None,
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
    try:
        selected_contract = execution_contract or default_execution_contract_registry().require(
            task, assignment
        )
        selected_contract.validate_task_assignment(task, assignment)
    except ExecutionContractError as exc:
        raise CloseoutError(exc.code, str(exc).split(": ", 1)[-1]) from exc
    contract_identifier = selected_contract.identifier
    handoff_tier = "H2" if selected_contract.require_transfer_manifest else "H1"
    handoff_tier_reasons = (
        "task-policy-requires-transfer-manifest"
        if selected_contract.require_transfer_manifest
        else "fresh-model-api-without-transfer-manifest",
    )
    model_assignment_id = "unavailable"
    model_assignment_ref: FileReference | None = None
    if model_assignment is not None:
        if model_assignment.attempt_id != attempt_id:
            raise CloseoutError(
                "MODEL-ASSIGNMENT-ATTEMPT-MISMATCH",
                "Model Assignment does not match the Attempt identity",
            )
        if (model_assignment.task_id, model_assignment.task_revision) != (
            task.task_id,
            task.revision,
        ):
            raise CloseoutError(
                "MODEL-ASSIGNMENT-TASK-MISMATCH",
                "Model Assignment does not match the Task identity/revision",
            )
        if (
            model_assignment.agent_profile_ref.path != profile_ref
            or model_assignment.agent_profile_ref.sha256
            != snapshot_map[profile_ref].sha256
        ):
            raise CloseoutError(
                "MODEL-ASSIGNMENT-PROFILE-MISMATCH",
                "Model Assignment does not hash-pin the selected Agent Profile",
            )
        if (
            model_assignment.provider_adapter_id,
            model_assignment.requested_model,
        ) != (provider_adapter_id, requested_model):
            raise CloseoutError(
                "MODEL-ASSIGNMENT-BINDING-MISMATCH",
                "Model Assignment differs from the requested adapter/model",
            )
        if model_assignment.selection_source == "profile-default" and (
            model_assignment.slot_id != profile.model_policy.get("default_slot")
        ):
            raise CloseoutError(
                "MODEL-SLOT-MISMATCH",
                "profile-default Model Assignment does not use the Profile default slot",
            )
        if model_assignment.execution_limits != limits:
            raise CloseoutError(
                "MODEL-ASSIGNMENT-EXECUTION-LIMITS",
                "Model Assignment execution limits differ from closeout limits",
            )
        if model_assignment.effective_data_policy != _protocol_data_policy(protocol):
            raise CloseoutError(
                "MODEL-ASSIGNMENT-DATA-POLICY",
                "Model Assignment data policy differs from the Project Protocol",
            )
        if model_assignment.automatic_fallback is not False:
            raise CloseoutError(
                "MODEL-ASSIGNMENT-FALLBACK",
                "Model Assignment must forbid automatic fallback",
            )
        model_assignment_id = model_assignment.model_assignment_id
    if not is_path_safe_identifier(task.task_id):
        raise CloseoutError("CLOSEOUT-TASK-ID", "task_id must be one path-safe segment")
    if terminal_status in {"completed", "stage-completed"} and session_result is None:
        raise CloseoutError(
            "CLOSEOUT-SESSION-RESULT-MISSING",
            "a successful closeout requires the isolated API session result",
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

    if (provider_conformance_document is None) != (
        provider_conformance_expected_sha256 is None
    ):
        raise CloseoutError(
            "PROVIDER-CONFORMANCE-EVIDENCE",
            "Provider conformance document and expected hash must be supplied together",
        )
    if provider_conformance_document is not None:
        schema_errors = SchemaCatalog().validate(
            "provider_conformance_report", provider_conformance_document
        )
        if schema_errors:
            raise CloseoutError(
                "PROVIDER-CONFORMANCE-EVIDENCE",
                "Provider conformance document is schema-invalid",
            )
        if provider_conformance_document.get("status") != "passed":
            raise CloseoutError(
                "PROVIDER-CONFORMANCE-FAILED",
                "Provider conformance evidence must have status passed",
            )
        if (
            provider_conformance_document.get("adapter_id"),
            provider_conformance_document.get("requested_model"),
        ) != (provider_adapter_id, requested_model):
            raise CloseoutError(
                "PROVIDER-CONFORMANCE-BINDING-MISMATCH",
                "Provider conformance evidence differs from the closeout adapter/model",
            )

    expected_frozen_contract_refs = set(selected_contract.supporting_refs)
    if model_assignment is not None and model_assignment.selection_ref is not None:
        expected_frozen_contract_refs.add(model_assignment.selection_ref.path)
    supplied_contract_payloads = dict(frozen_contract_payloads or {})
    if set(supplied_contract_payloads) != expected_frozen_contract_refs:
        raise CloseoutError(
            "EXECUTION-CONTRACT-SNAPSHOT",
            "frozen supporting and override references do not exactly match the execution identity",
        )
    for relative, payload in supplied_contract_payloads.items():
        if not isinstance(payload, bytes):
            raise CloseoutError(
                "EXECUTION-CONTRACT-SNAPSHOT", f"frozen contract payload is not bytes: {relative}"
            )
        live = resolve_within_root(project_root, relative)
        if live is None or not live.is_file() or live.read_bytes() != payload:
            raise CloseoutError(
                "EXECUTION-CONTRACT-DRIFT", f"execution support reference drifted: {relative}"
            )
    if model_assignment is not None and model_assignment.selection_ref is not None:
        selection_payload = supplied_contract_payloads[model_assignment.selection_ref.path]
        if hashlib.sha256(selection_payload).hexdigest() != model_assignment.selection_ref.sha256:
            raise CloseoutError(
                "MODEL-ASSIGNMENT-SELECTION-DRIFT",
                "Model Assignment override reference digest differs",
            )

    normalized_status, operational_failure = _normalize_terminal_status(
        terminal_status=terminal_status,
        session_result=session_result,
        failure_code=failure_code,
        failure_summary=failure_summary,
    )
    if normalized_status not in {"completed", "stage-completed"}:
        output = None
        admission = None
    elif admission is not None:
        if admission.success_status != selected_contract.success_status:
            raise CloseoutError(
                "EXECUTION-CONTRACT-STATUS",
                "admitted output success status differs from its ExecutionContract",
            )
        if normalized_status != admission.success_status:
            raise CloseoutError(
                "EXECUTION-CONTRACT-STATUS",
                "closeout success status differs from the admitted output contract",
            )
        output = {
            "artifacts": [
                {"document": dict(artifact.document)} for artifact in admission.artifacts
            ],
            "handoff": dict(admission.handoff),
            "transfer_items": [dict(item) for item in admission.transfer_items],
        }
    elif output is None:
        raise CloseoutError("CLOSEOUT-OUTPUT-MISSING", "successful Attempt has no API output")
    elif isinstance(selected_contract, EvidenceH2ExecutionContract):
        validate_api_task_output(output, task=task, protocol=protocol)
    else:
        raise CloseoutError(
            "CLOSEOUT-OUTPUT-ADMISSION",
            "non-evidence ExecutionContracts require trusted admission before closeout",
        )

    attempt_root = f"work/{task.task_id}/{attempt_id}"
    paths = _CloseoutPaths(attempt_root)
    trace_payloads = dict(frozen_agent_trace_payloads or {})
    if agent_trace_sealer is not None and (
        agent_trace_index_ref is not None or trace_payloads
    ):
        raise CloseoutError(
            "AGENT-TRACE-BUNDLE-AMBIGUOUS",
            "supply either a deferred Trace sealer or an already frozen Trace bundle",
        )
    if (agent_trace_index_ref is None) != (not trace_payloads):
        raise CloseoutError(
            "AGENT-TRACE-BUNDLE-MISSING",
            "Agent Trace index and frozen bundle must be supplied together",
        )
    if agent_trace_index_ref is not None:
        _validate_frozen_agent_trace_bundle(
            content_root=project_root,
            project_root=project_root,
            attempt_root=attempt_root,
            task=task,
            assignment=assignment,
            normalized_status=normalized_status,
            index_ref=agent_trace_index_ref,
            payloads=trace_payloads,
        )
    _validate_output_paths(project_root, task, assignment, paths.static_final_paths)
    if provider_conformance_document is not None:
        _validate_output_paths(
            project_root, task, assignment, (paths.provider_conformance,)
        )
    artifact_kinds: dict[str, str]
    if admission is not None and not isinstance(selected_contract, EvidenceH2ExecutionContract):
        artifact_documents, artifact_refs_by_id, artifact_kinds = _prepare_admitted_artifacts(
            attempt_root=attempt_root,
            artifacts=admission.artifacts,
        )
    else:
        artifact_documents, artifact_refs_by_id = _prepare_artifacts(
            task=task,
            protocol=protocol,
            attempt_root=attempt_root,
            output=output,
            status=normalized_status,
        )
        artifact_kinds = {relative: "research_object" for relative in artifact_documents}
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
    for relative, payload in supplied_contract_payloads.items():
        write_bytes_exclusive(_stage_path(stage_root, relative), payload)
    for relative, payload in sorted(trace_payloads.items()):
        write_bytes_exclusive(_stage_path(stage_root, relative), payload)
    if model_assignment is not None:
        model_assignment_path = paths.model_assignment
        _stage_document(
            stage_root,
            model_assignment_path,
            model_assignment.to_mapping(),
            "model_assignment",
        )
        model_assignment_ref = FileReference(
            model_assignment_path,
            hash_file(_stage_path(stage_root, model_assignment_path)),
        )
    provider_conformance_ref: FileReference | None = None
    if provider_conformance_document is not None:
        _stage_document(
            stage_root,
            paths.provider_conformance,
            provider_conformance_document,
            "provider_conformance_report",
        )
        actual_hash = hash_file(_stage_path(stage_root, paths.provider_conformance))
        if actual_hash != provider_conformance_expected_sha256:
            raise CloseoutError(
                "PROVIDER-CONFORMANCE-HASH-MISMATCH",
                "staged Provider conformance evidence differs from its approved hash",
            )
        provider_conformance_ref = FileReference(
            paths.provider_conformance,
            actual_hash,
        )
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
        _stage_document(stage_root, relative, document, artifact_kinds[relative])

    contract_validation_refs: tuple[str, ...] = ()
    if admission is not None:
        try:
            validations = selected_contract.build_validations(
                stage_root=stage_root,
                attempt_root=attempt_root,
                attempt_id=attempt_id,
                artifacts=admission.artifacts,
            )
        except ExecutionContractError as exc:
            raise CloseoutError(exc.code, str(exc).split(": ", 1)[-1]) from exc
        validation_refs: list[str] = []
        for validation in validations:
            relative = _contract_output_ref(attempt_root, validation.relative_name)
            if relative in artifact_documents or relative in validation_refs:
                raise CloseoutError(
                    "EXECUTION-CONTRACT-PATH", f"duplicate contract output path: {relative}"
                )
            _validate_output_paths(project_root, task, assignment, (relative,))
            _stage_document(
                stage_root,
                relative,
                validation.document,
                validation.document_kind,
            )
            validation_refs.append(relative)
        contract_validation_refs = tuple(validation_refs)

    manifest_ref: str | None = None
    audit_ref: str | None = None
    manifest_document: dict[str, Any] | None = None
    if selected_contract.require_transfer_manifest and artifact_documents:
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
        validation_refs=contract_validation_refs + ((audit_ref,) if audit_ref else ()),
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

    if agent_trace_sealer is not None:
        try:
            sealed_ref, sealed_payloads = agent_trace_sealer(
                stage_root=stage_root,
                handoff_refs=(paths.handoff,)
                + ((manifest_ref,) if manifest_ref is not None else ()),
                decision_refs=(),
                output_refs=tuple(artifact_documents),
                check_refs=contract_validation_refs
                + ((audit_ref,) if audit_ref is not None else ())
                + (
                    (provider_conformance_ref.path,)
                    if provider_conformance_ref is not None
                    else ()
                ),
            )
        except CloseoutError:
            raise
        except Exception as exc:
            raise CloseoutError(
                "AGENT-TRACE-CAPTURE-FAILED",
                "Agent Trace could not be sealed against the staged closeout",
            ) from exc
        if not isinstance(sealed_ref, FileReference) or not isinstance(
            sealed_payloads, Mapping
        ):
            raise CloseoutError(
                "AGENT-TRACE-CAPTURE-FAILED",
                "Agent Trace sealer returned an invalid frozen bundle",
            )
        agent_trace_index_ref = sealed_ref
        trace_payloads = dict(sealed_payloads)
        for relative, payload in trace_payloads.items():
            if not isinstance(relative, str) or not isinstance(payload, bytes):
                raise CloseoutError(
                    "AGENT-TRACE-CAPTURE-FAILED",
                    "Agent Trace sealer returned invalid path or payload metadata",
                )
            write_bytes_exclusive(_stage_path(stage_root, relative), payload)
        _validate_frozen_agent_trace_bundle(
            content_root=stage_root,
            project_root=project_root,
            attempt_root=attempt_root,
            task=task,
            assignment=assignment,
            normalized_status=normalized_status,
            index_ref=agent_trace_index_ref,
            payloads=trace_payloads,
        )

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
        agent_trace_index_ref=agent_trace_index_ref,
        model_assignment_ref=model_assignment_ref,
        provider_conformance_ref=provider_conformance_ref,
        handoff_tier=handoff_tier,
        handoff_tier_reasons=handoff_tier_reasons,
        operational_failure=operational_failure,
    )
    _stage_document(stage_root, paths.attempt, attempt_document, "attempt")

    receipt_document = _build_receipt(
        task=task,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        model_assignment_ref=model_assignment_ref,
        provider_conformance_ref=provider_conformance_ref,
        execution_contract=contract_identifier,
        agent_trace_index_ref=agent_trace_index_ref,
        handoff_tier=handoff_tier,
        handoff_tier_reasons=handoff_tier_reasons,
        attempt_ref=paths.attempt,
        context_ref=paths.task_context,
        status=normalized_status,
        started_at=started_at,
        finished_at=finished_at,
        receipt_id=f"XR-{attempt_id}",
        output_refs=tuple(artifact_documents)
        + ((manifest_ref,) if manifest_ref else ())
        + (paths.handoff,),
        validation_refs=contract_validation_refs
        + ((audit_ref,) if audit_ref else ())
        + (
            (provider_conformance_ref.path,)
            if provider_conformance_ref is not None
            else ()
        ),
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

    trace_index_path = (
        agent_trace_index_ref.path if agent_trace_index_ref is not None else None
    )
    trace_non_index_refs = tuple(
        relative for relative in trace_payloads if relative != trace_index_path
    )
    # Referenced closeout files must be published before the Trace INDEX commit
    # marker. Attempt/Receipt then publish after INDEX because both hash-pin it;
    # Main State remains the final authoritative commit.
    non_main_refs = tuple(
        _unique(
            [
                *artifact_documents,
                *(
                    relative
                    for relative in (
                        manifest_ref,
                        paths.handoff,
                        audit_ref,
                        *contract_validation_refs,
                        paths.task_context,
                        model_assignment_ref.path if model_assignment_ref is not None else None,
                        (
                            provider_conformance_ref.path
                            if provider_conformance_ref is not None
                            else None
                        ),
                    )
                    if relative is not None
                ),
                *trace_non_index_refs,
                *(
                    (trace_index_path,)
                    if trace_index_path is not None
                    else ()
                ),
                paths.attempt,
                paths.receipt,
                paths.main_context,
            ]
        )
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
        agent_trace_index_ref=agent_trace_index_ref,
        source_refs=tuple(supplied_contract_payloads),
        created_at=finished_at,
        operational_failure=operational_failure,
        previous_main_state_ref=previous_main_state_ref,
        provider_conformance_ref=provider_conformance_ref,
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
        model_assignment_id=model_assignment_id,
        model_assignment_ref=model_assignment_ref,
        execution_contract=contract_identifier,
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
