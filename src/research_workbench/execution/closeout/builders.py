"""Pure document constructors for the staged closeout bundle."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from research_workbench.adapters.models import ApiSessionLimits, ApiSessionResult
from research_workbench.artifacts.integrity import hash_file
from research_workbench.capability import ResolvedTask
from research_workbench.context import (
    CONTEXT_METRIC_NAMES,
    ContextBudgetEstimate,
    ContextPolicySnapshot,
    ContextSnapshot,
    MainStatePacket,
    checkpoint_digest,
)
from research_workbench.contracts import RiskLevel, is_path_safe_identifier
from research_workbench.observability import ExecutionReceipt
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import AttemptRecord, FileReference, HandoffPacket, TaskPacket
from research_workbench.validation import check_claim_ceiling

from .documents import _load_mapping, _snapshot_document, _unique, _validate_schema
from .errors import CloseoutContractSnapshot, CloseoutError
from .paths import _file_ref, _stage_path

def _prepare_artifacts(
    *,
    task: TaskPacket,
    protocol: ProjectProtocol,
    attempt_root: str,
    output: Mapping[str, Any] | None,
    status: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    if output is None:
        if status in {"completed", "stage-completed"}:
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
    if status in {"completed", "stage-completed"} and "evidence-record" in required and evidence_count == 0:
        raise CloseoutError("CLOSEOUT-EVIDENCE-MISSING", "Task requires an Evidence record")
    if status in {"completed", "stage-completed"} and not documents:
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
    validation_refs: tuple[str, ...],
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
        "validation_refs": list(validation_refs),
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
    agent_trace_index_ref: FileReference | None,
    model_assignment_ref: FileReference | None,
    provider_conformance_ref: FileReference | None,
    handoff_tier: str,
    handoff_tier_reasons: tuple[str, ...],
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
        "handoff_tier": handoff_tier,
        "handoff_tier_reasons": list(handoff_tier_reasons),
    }
    if operational_failure:
        document["failure"] = dict(operational_failure)
    if agent_trace_index_ref is not None:
        document["agent_trace_index_ref"] = _file_ref(
            agent_trace_index_ref.path,
            agent_trace_index_ref.sha256,
            agent_trace_index_ref.revision,
        )
    if model_assignment_ref is not None:
        document["model_assignment_ref"] = _file_ref(
            model_assignment_ref.path,
            model_assignment_ref.sha256,
            model_assignment_ref.revision,
        )
    if provider_conformance_ref is not None:
        document["provider_conformance_ref"] = _file_ref(
            provider_conformance_ref.path,
            provider_conformance_ref.sha256,
            provider_conformance_ref.revision,
        )
    _validate_schema("attempt", document)
    AttemptRecord.from_mapping(document)
    return document


def _build_receipt(
    *,
    task: TaskPacket,
    profile_ref: str,
    assignment_ref: str,
    model_assignment_ref: FileReference | None,
    provider_conformance_ref: FileReference | None,
    execution_contract: str | None,
    agent_trace_index_ref: FileReference | None,
    handoff_tier: str,
    handoff_tier_reasons: tuple[str, ...],
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
        "completion_claim": (
            "contract-satisfied"
            if status in {"completed", "stage-completed"}
            else "execution-only"
        ),
        "handoff_tier": handoff_tier,
        "handoff_tier_reasons": list(handoff_tier_reasons),
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
            "external": False,
            "sensitive_data_detected": False,
            "redactions_applied": 0,
        },
        "output_refs": list(output_refs),
        "validation_refs": list(validation_refs),
        "limitations": limitations,
    }
    if model_assignment_ref is not None:
        document["model_assignment_ref"] = _file_ref(
            model_assignment_ref.path,
            model_assignment_ref.sha256,
            model_assignment_ref.revision,
        )
    if provider_conformance_ref is not None:
        document["provider_conformance_ref"] = _file_ref(
            provider_conformance_ref.path,
            provider_conformance_ref.sha256,
            provider_conformance_ref.revision,
        )
    if execution_contract is not None:
        document["execution_contract"] = execution_contract
    if agent_trace_index_ref is not None:
        document["agent_trace_index_ref"] = _file_ref(
            agent_trace_index_ref.path,
            agent_trace_index_ref.sha256,
            agent_trace_index_ref.revision,
        )
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
    agent_trace_index_ref: FileReference | None,
    source_refs: tuple[str, ...] = (),
    created_at: str,
    operational_failure: Mapping[str, Any] | None,
    previous_main_state_ref: str | None,
    provider_conformance_ref: FileReference | None = None,
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
            "disposition": (
                "accepted-closeout"
                if status == "completed"
                else "accepted-stage-closeout"
                if status == "stage-completed"
                else f"{status}-recoverable"
            ),
        }
    )
    risks = list(previous.get("open_risks", []))
    if operational_failure and operational_failure["code"] not in risks:
        risks.append(str(operational_failure["code"]))
    if (
        status in {"completed", "stage-completed"}
        and provider_conformance_ref is None
        and "API-LIVE-CONFORMANCE-NOT-RUN" not in risks
    ):
        risks.append("API-LIVE-CONFORMANCE-NOT-RUN")
    candidate_ref_paths = _unique(
        [
            protocol_ref,
            task_ref,
            profile_ref,
            assignment_ref,
            *source_refs,
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
            "active"
            if status == "completed"
            else "stage-completed"
            if status == "stage-completed"
            else "safe-paused"
            if status == "safe-paused"
            else "blocked"
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
        "agent_trace_index_refs": (
            [
                _file_ref(
                    agent_trace_index_ref.path,
                    agent_trace_index_ref.sha256,
                    agent_trace_index_ref.revision,
                )
            ]
            if agent_trace_index_ref is not None
            else []
        ),
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
