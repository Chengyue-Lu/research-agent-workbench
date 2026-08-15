"""Builders that turn one session outcome into the closeout file chain.

Builders run in hash-dependency order (handoff content first, the main
state last) because audits, manifests, check reports, and machine-state
references pin the content hashes of documents built before them. All
document paths are deterministic functions of the attempt identity, which
makes re-running the same plan resumable instead of divergent.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from research_workbench.adapters.models import AggregateUsage, ApiSessionResult, ModelBinding
from research_workbench.artifacts.integrity import hash_file
from research_workbench.capability.resolver import ResolvedTask
from research_workbench.contracts.common import to_plain
from research_workbench.context.models import (
    ContextBudgetEstimate,
    ContextPolicySnapshot,
    ContextSnapshot,
    checkpoint_digest,
)
from research_workbench.execution.checks import (
    CHECKER_ID,
    CHECKER_REPO_PATH,
    CHECKER_VERSION,
    CheckOutcome,
    evaluate_evidence_checks,
    session_checks,
)
from research_workbench.execution.closeout import (
    CloseoutDocument,
    CloseoutPlan,
    PUBLISH_ORDER,
    input_lock_entries,
    serialize_document,
)
from research_workbench.execution.compiler import CompiledSession
from research_workbench.execution.errors import CloseoutError
from research_workbench.execution.status import map_outcome
from research_workbench.adapters.models import ApiSessionStatus
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import TaskPacket


MODEL_DRIFT_WARNING = "provider-reported-model-differs-from-request"
DRIFT_LIMITATION = "Provider reported a model different from the requested slot; the completion claim is withheld."
STRUCTURAL_LIMITATION = (
    "Offline K-API-2 execution record; structural evidence only, not a scientific correctness claim."
)


@dataclass(frozen=True, slots=True)
class SessionOutcome:
    status: str
    stop_reason: str
    provider: str
    requested_model: str
    observed_models: tuple[str, ...]
    model_turns: int
    tool_calls: int
    usage: AggregateUsage
    warnings: tuple[str, ...]
    structured_output: Mapping[str, Any] | None = None
    failure: Mapping[str, Any] | None = None
    tool_failures: tuple[Mapping[str, Any], ...] = ()


def outcome_from_result(
    result: ApiSessionResult,
    *,
    structured_output: Mapping[str, Any] | None = None,
    failure: Mapping[str, Any] | None = None,
) -> SessionOutcome:
    """Normalize one runner result (plus its parsed structured payload)."""

    return SessionOutcome(
        status=str(result.status.value),
        stop_reason=result.stop_reason,
        provider=result.provider,
        requested_model=result.requested_model,
        observed_models=tuple(result.observed_models),
        model_turns=result.model_turns,
        tool_calls=result.tool_calls,
        usage=result.usage,
        warnings=tuple(result.warnings),
        structured_output=structured_output,
        failure=failure,
    )


def build_closeout_documents(
    task: TaskPacket,
    assignment: ResolvedTask,
    binding: ModelBinding,
    compiled: CompiledSession,
    outcome: SessionOutcome,
    *,
    root: Path,
    protocol: ProjectProtocol,
    protocol_path: str,
    profile_path: str,
    task_path: str,
    started_at: str,
    finished_at: str,
    base_state: Any | None = None,
    batch_prefix: str = "",
    checkpoint_prefix: str = "",
) -> CloseoutPlan:
    """Build every closeout document for one attempt in publish order.

    ``batch_prefix``/``checkpoint_prefix`` relocate the batch and checkpoint
    directories (used to regenerate the static example fixtures); runtime
    execution keeps the defaults under the task write scope.
    """

    paths = _batch_paths(task.task_id, compiled.attempt_id, batch_prefix, checkpoint_prefix)
    completed = outcome.structured_output is not None and outcome.status == "completed"
    model_drift = MODEL_DRIFT_WARNING in outcome.warnings
    checks = (
        evaluate_evidence_checks(outcome.structured_output or {}, task)
        if completed
        else session_checks(
            stop_reason=outcome.stop_reason,
            tool_failures=_tool_failures(compiled),
        )
    )
    statuses = map_outcome(
        ApiSessionStatus(outcome.status),
        outcome.stop_reason,
        # A completed session without a structured payload can never gate a
        # contract-satisfied claim, whatever the session checks recorded.
        check_passed=all(check.passed for check in checks) and completed,
        model_drift=model_drift,
    )

    handoff = _handoff_document(
        task, assignment, outcome, statuses, compiled.attempt_id, paths,
        completed, model_drift, _tool_failures(compiled),
    )
    handoff_bytes = serialize_document(handoff)
    evidence = (
        _evidence_document(task, assignment, compiled.attempt_id, outcome, handoff)
        if completed
        else None
    )
    evidence_bytes = serialize_document(evidence) if evidence is not None else None

    mirror, mirror_index = _negative_mirror(handoff)
    check = _check_document(
        task, compiled.attempt_id, checks, finished_at, completed,
        subjects=(
            [{"path": paths["evidence"], "sha256": _hash(evidence_bytes)}]
            if completed
            else [{"path": paths["handoff"], "sha256": _hash(handoff_bytes)}]
        ),
        mirror=mirror if not completed else None,
        checker_sha256=_checker_hash(root),
    )
    check_bytes = serialize_document(check)

    source_path = paths["evidence"] if completed else paths["check"]
    source_sha = _hash(evidence_bytes) if completed else _hash(check_bytes)
    manifest, mappings = _manifest_document(
        task, compiled.attempt_id, handoff, finished_at, source_path, source_sha,
        completed, mirror_index,
    )

    audit = _audit_document(
        compiled.attempt_id, finished_at, paths, mappings, task_path,
        task_sha256=_file_hash(root, task_path),
        handoff_sha256=_hash(handoff_bytes),
        manifest_sha256=_hash(serialize_document(manifest)),
    )

    policy = ContextPolicySnapshot.from_project_policy(protocol.context_policy)
    tool_cap = compiled.limits.max_tool_result_chars
    task_snapshot = _snapshot(
        snapshot_id=f"CTX-{compiled.attempt_id}-TASK",
        captured_at=finished_at,
        scope="task",
        owner=task.task_id,
        source="runtime",
        policy=policy,
        metrics={
            "loaded_chars": compiled.report.input_chars + compiled.report.skill_instruction_chars,
            "skill_instruction_chars": compiled.report.skill_instruction_chars,
            "raw_material_chars": compiled.report.input_chars,
            "turns": outcome.model_turns,
            "long_tool_outputs": sum(
                1
                for record in compiled.tool_log.records
                if record.result_chars >= tool_cap // 2
            ),
            "open_items": len(handoff["unresolved"]) + len(handoff["limitations"]),
        },
        unknown=("pinned_chars", "recent_handoffs", "compaction_events", "hidden_decisions"),
        handoff_ready=True,
    )
    main_snapshot = _snapshot(
        snapshot_id=f"CTX-{compiled.attempt_id}-MAIN",
        captured_at=finished_at,
        scope="main",
        owner=None,
        source="file-estimate",
        policy=policy,
        metrics={
            "loaded_chars": len(str(handoff["result"]["summary"]))
            + sum(len(action) for action in handoff["recommended_next_actions"]),
            "raw_material_chars": 0,
            "recent_handoffs": 1,
            "turns": 0,
            "open_items": len(handoff["unresolved"]),
        },
        unknown=(
            "pinned_chars",
            "skill_instruction_chars",
            "long_tool_outputs",
            "compaction_events",
            "hidden_decisions",
        ),
        handoff_ready=None,
    )

    assignment_document = to_plain(assignment)
    attempt = _attempt_document(
        task, assignment, binding, outcome, statuses, compiled.attempt_id, paths,
        started_at, finished_at, completed,
    )
    receipt = _receipt_document(
        task, binding, outcome, statuses, compiled.attempt_id, paths,
        started_at, finished_at, completed, model_drift, profile_path,
    )
    role_documents = {
        "check": check,
        "manifest": manifest,
        "audit": audit,
        "task-snapshot": task_snapshot,
        "main-snapshot": main_snapshot,
        "assignment": assignment_document,
        "handoff": handoff,
        "attempt": attempt,
        "receipt": receipt,
    }
    if evidence is not None:
        role_documents["evidence"] = evidence
    main_state = _main_state_document(
        task, statuses, compiled.attempt_id, paths, protocol, protocol_path, finished_at,
        artifact_ref=paths["evidence"] if completed else paths["check"],
        handoff=handoff,
        main_snapshot=main_snapshot,
        role_documents=role_documents,
        base_state=base_state,
    )
    role_documents["main-state"] = main_state

    documents = tuple(
        CloseoutDocument(role, paths[role], role_documents[role])
        for role in PUBLISH_ORDER
        if role in role_documents
    )
    return CloseoutPlan(batch_dir=paths["batch"], documents=documents, main_state_path=paths["main-state"])


def _batch_paths(
    task_id: str, attempt_id: str, batch_prefix: str = "", checkpoint_prefix: str = ""
) -> dict[str, str]:
    batch = f"{batch_prefix}work/{task_id}/{attempt_id}".lstrip("/")
    checkpoint_dir = f"{checkpoint_prefix}checkpoints".rstrip("/")
    return {
        "batch": batch,
        "evidence": f"{batch}/evidence.yaml",
        "check": f"{batch}/check-report.yaml",
        "manifest": f"{batch}/transfer-manifest.yaml",
        "audit": f"{batch}/transfer-audit.yaml",
        "task-snapshot": f"{batch}/context-snapshot-task.yaml",
        "main-snapshot": f"{batch}/context-snapshot-main.yaml",
        "assignment": f"{batch}/skill-assignment.yaml",
        "handoff": f"{batch}/handoff.yaml",
        "attempt": f"{batch}/attempt.yaml",
        "receipt": f"{batch}/execution-receipt.yaml",
        "main-state": f"{checkpoint_dir}/MS-{attempt_id.removeprefix('A-')}.yaml",
    }


def _tool_failures(compiled: CompiledSession) -> tuple[dict[str, str], ...]:
    return tuple(
        {"name": record.name, "error": record.error or "unknown"}
        for record in compiled.tool_log.failures
    )


def _dedupe(values) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _hash(content: bytes | None) -> str:
    if content is None:
        raise CloseoutError("EXEC-CLOSEOUT-INVALID", "expected staged content is absent")
    return hashlib.sha256(content).hexdigest()


def _file_hash(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise CloseoutError("EXEC-CLOSEOUT-INVALID", f"referenced file is absent: {relative}")
    return hash_file(path)


def _checker_hash(root: Path) -> str:
    return _file_hash(root, CHECKER_REPO_PATH)


def _negative_mirror(handoff: Mapping[str, Any]) -> tuple[list[str], dict[str, int]]:
    """Ordered mirror of negative sections for manifest source locators."""

    mirror: list[str] = []
    index: dict[str, int] = {}
    for value in [*handoff["limitations"], *handoff["unresolved"]]:
        if value not in index:
            index[value] = len(mirror)
            mirror.append(value)
    return mirror, index


def _handoff_document(
    task: TaskPacket,
    assignment: ResolvedTask,
    outcome: SessionOutcome,
    statuses,
    attempt_id: str,
    paths: Mapping[str, str],
    completed: bool,
    model_drift: bool,
    tool_failures: tuple[Mapping[str, Any], ...],
) -> dict[str, Any]:
    structured = outcome.structured_output or {}
    tool_lines = [
        f"client tool {entry['name']} failed with {entry['error']}" for entry in tool_failures
    ]
    if completed:
        summary = str(structured.get("summary", ""))
        facts = [str(value) for value in structured.get("facts", [])]
        inferences = [str(value) for value in structured.get("inferences", [])]
        recommendations = [str(value) for value in structured.get("recommendations", [])]
        limitations = [*(str(value) for value in structured.get("limitations", [])), STRUCTURAL_LIMITATION]
        unresolved = [str(value) for value in structured.get("unresolved", [])]
        next_actions = [
            f"Verify the evidence record and transfer audit of attempt {attempt_id}, "
            "then admit or reject the evidence at the human gate."
        ]
    else:
        summary = f"Session {statuses.record_status}: {outcome.stop_reason}."
        facts, inferences, recommendations = [], [], []
        limitations = [
            f"Session ended {statuses.record_status}: {outcome.stop_reason}.",
            *tool_lines,
            STRUCTURAL_LIMITATION,
        ]
        unresolved = [f"Session stopped before completion: {outcome.stop_reason}.", *tool_lines]
        next_actions = [
            f"Resume task {task.task_id} from the {statuses.record_status} files of attempt "
            f"{attempt_id} without re-executing recorded side effects."
            if statuses.record_status == "safe-paused"
            else f"Review the {statuses.record_status} outcome of attempt {attempt_id} and decide "
            "whether to dispatch a fresh attempt."
        ]
    if model_drift:
        limitations.append(DRIFT_LIMITATION)
        unresolved.append(DRIFT_LIMITATION)

    document: dict[str, Any] = {
        "schema_version": "0.1.0",
        "task_id": task.task_id,
        "attempt_id": attempt_id,
        "status": statuses.record_status,
        "input_lock": input_lock_entries(task),
        "skill_lock": [lock.identifier for lock in assignment.skill_lock],
        "skill_assignment_ref": paths["assignment"],
        "result": {
            "summary": summary,
            "facts": _dedupe(facts),
            "inferences": _dedupe(inferences),
            "recommendations": _dedupe(recommendations),
        },
        "artifact_refs": [paths["evidence"] if completed else paths["check"]],
        "validation_refs": [paths["audit"]],
        "limitations": _dedupe(limitations),
        "conflicts": [],
        "unresolved": _dedupe(unresolved),
        "human_decision_required": (
            ["Decide whether to continue the incomplete session or close the attempt."]
            if statuses.record_status == "incomplete"
            else []
        ),
        "recommended_next_actions": next_actions,
        "execution_receipt_ref": paths["receipt"],
        "transfer_manifest_ref": paths["manifest"],
    }
    return document


def _evidence_document(
    task: TaskPacket,
    assignment: ResolvedTask,
    attempt_id: str,
    outcome: SessionOutcome,
    handoff: Mapping[str, Any],
) -> dict[str, Any]:
    structured = outcome.structured_output or {}
    source = task.input_refs[0]
    return {
        "schema_version": "0.1.0",
        "object_type": "evidence",
        "object_id": f"EVIDENCE-{task.task_id}-{attempt_id}",
        "revision": 1,
        "status": "proposed",
        "content_hash": source.sha256,
        "kind": "model-extracted-statement",
        "source_ref": {
            "object_id": source.path,
            "revision": source.revision or 1,
            "sha256": source.sha256,
        },
        "locator": str(structured.get("source_locator", "")),
        "statement": str(structured.get("statement", "")),
        "quality_flags": _dedupe(structured.get("quality_flags", [])),
        "metadata": {
            "attempt_id": attempt_id,
            "assignment_id": assignment.assignment_id,
            "transfer_facts": list(handoff["result"]["facts"]),
            "transfer_inferences": list(handoff["result"]["inferences"]),
            "transfer_recommendations": list(handoff["result"]["recommendations"]),
            "transfer_limitations": list(handoff["limitations"]),
            "transfer_unresolved": list(handoff["unresolved"]),
        },
    }


def _check_document(
    task: TaskPacket,
    attempt_id: str,
    checks: tuple[CheckOutcome, ...],
    finished_at: str,
    completed: bool,
    *,
    subjects: list[dict[str, str]],
    mirror: list[str] | None,
    checker_sha256: str,
) -> dict[str, Any]:
    limitations = (
        [STRUCTURAL_LIMITATION, "Offline fixture execution; no live provider was contacted."]
        if completed
        else list(mirror or [])
    )
    return {
        "schema_version": "0.1.0",
        "report_id": f"DCR-{attempt_id}",
        "checker": {
            "checker_id": CHECKER_ID,
            "version": CHECKER_VERSION,
            "source_ref": {"path": CHECKER_REPO_PATH, "sha256": checker_sha256},
        },
        "subject_refs": subjects,
        "status": "pass" if all(check.passed for check in checks) else "fail",
        "checks": [
            {"code": check.code, "status": check.status, "detail": check.detail}
            for check in checks
        ],
        "scope": f"k-api-2 offline closeout for task {task.task_id} attempt {attempt_id}",
        "limitations": _dedupe(limitations),
    }


def _manifest_document(
    task: TaskPacket,
    attempt_id: str,
    handoff: Mapping[str, Any],
    finished_at: str,
    source_path: str,
    source_sha256: str,
    completed: bool,
    mirror_index: Mapping[str, int],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    suffix = attempt_id.removeprefix("A-")
    items: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []

    def add(kind: str, index: int, statement: str, source_locator: str, handoff_locator: str) -> None:
        item_id = f"HTI-{suffix}-{kind.upper()}-{index:03d}"
        items.append(
            {
                "item_id": item_id,
                "kind": kind,
                "criticality": "material",
                "required_for_handoff": True,
                "statement": statement,
                "source_ref": {"path": source_path, "sha256": source_sha256},
                "source_locator": source_locator,
            }
        )
        mappings.append(
            {"item_id": item_id, "status": "carried", "handoff_locator": handoff_locator}
        )

    if completed:
        sections = (
            ("fact", handoff["result"]["facts"], "/metadata/transfer_facts", "/result/facts"),
            ("inference", handoff["result"]["inferences"], "/metadata/transfer_inferences", "/result/inferences"),
            ("recommendation", handoff["result"]["recommendations"], "/metadata/transfer_recommendations", "/result/recommendations"),
            ("limitation", handoff["limitations"], "/metadata/transfer_limitations", "/limitations"),
            ("unresolved", handoff["unresolved"], "/metadata/transfer_unresolved", "/unresolved"),
        )
        for kind, values, source_prefix, handoff_prefix in sections:
            for index, statement in enumerate(values):
                add(kind, index, statement, f"{source_prefix}/{index}", f"{handoff_prefix}/{index}")
    else:
        for kind, values, handoff_prefix in (
            ("limitation", handoff["limitations"], "/limitations"),
            ("unresolved", handoff["unresolved"], "/unresolved"),
        ):
            for index, statement in enumerate(values):
                add(
                    kind,
                    index,
                    statement,
                    f"/limitations/{mirror_index[statement]}",
                    f"{handoff_prefix}/{index}",
                )

    manifest = {
        "schema_version": "0.1.0",
        "manifest_id": f"HTM-{attempt_id}",
        "task_id": task.task_id,
        "task_revision": task.revision,
        "attempt_id": attempt_id,
        "generated_at": finished_at,
        "declared_by": "task-agent",
        "source_artifact_refs": [{"path": source_path, "sha256": source_sha256}],
        "items": items,
        "limitations": [
            "The task agent declares transfer obligations; this manifest does not prove "
            "that it found every scientifically important item."
        ],
    }
    return manifest, mappings


def _audit_document(
    attempt_id: str,
    finished_at: str,
    paths: Mapping[str, str],
    mappings: list[dict[str, Any]],
    task_path: str,
    *,
    task_sha256: str,
    handoff_sha256: str,
    manifest_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "audit_id": f"HTA-{attempt_id}",
        "task_ref": {"path": task_path, "sha256": task_sha256},
        "handoff_ref": {"path": paths["handoff"], "sha256": handoff_sha256},
        "manifest_ref": {"path": paths["manifest"], "sha256": manifest_sha256},
        "generated_at": finished_at,
        "mappings": mappings,
        "review": {
            "status": "pending",
            "reviewer_kind": "none",
            "reviewer_independent": False,
            "sampled_item_ids": [],
            "findings": [],
        },
        "limitations": [
            "Structural coverage is a machine result; semantic equivalence has not been reviewed."
        ],
    }


def _snapshot(
    *,
    snapshot_id: str,
    captured_at: str,
    scope: str,
    owner: str | None,
    source: str,
    policy: ContextPolicySnapshot,
    metrics: dict[str, int],
    unknown: tuple[str, ...],
    handoff_ready: bool | None,
) -> dict[str, Any]:
    snapshot = ContextSnapshot.create(
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        scope=scope,
        measurement_source=source,
        metrics=metrics,
        unknown_metrics=unknown,
        handoff_ready=handoff_ready,
        policy=policy,
        context_budget=ContextBudgetEstimate("unavailable"),
        owner_ref=owner,
    )
    return snapshot.to_mapping()


def _attempt_document(
    task: TaskPacket,
    assignment: ResolvedTask,
    binding: ModelBinding,
    outcome: SessionOutcome,
    statuses,
    attempt_id: str,
    paths: Mapping[str, str],
    started_at: str,
    finished_at: str,
    completed: bool,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "0.1.0",
        "task_id": task.task_id,
        "task_revision": task.revision,
        "attempt_id": attempt_id,
        "status": statuses.record_status,
        "started_at": started_at,
        "finished_at": finished_at,
        "trigger_reason": (
            f"task-to-api execution of assignment {assignment.assignment_id} "
            f"via slot {binding.slot_id}"
        ),
        "input_lock": input_lock_entries(task),
        "skill_lock": [lock.identifier for lock in assignment.skill_lock],
        "skill_assignment_ref": paths["assignment"],
        "execution_receipt_ref": paths["receipt"],
        "artifact_refs": [paths["evidence"] if completed else paths["check"]],
        "handoff_ref": paths["handoff"],
    }
    if outcome.failure is not None:
        document["failure"] = dict(outcome.failure)
    return document


def _receipt_document(
    task: TaskPacket,
    binding: ModelBinding,
    outcome: SessionOutcome,
    statuses,
    attempt_id: str,
    paths: Mapping[str, str],
    started_at: str,
    finished_at: str,
    completed: bool,
    model_drift: bool,
    profile_path: str,
) -> dict[str, Any]:
    usage_status, usage_records = _usage_records(outcome)
    document: dict[str, Any] = {
        "schema_version": "0.1.0",
        "receipt_id": f"XR-{attempt_id}",
        "execution_kind": "model-api",
        "attempt_ref": paths["attempt"],
        "task_id": task.task_id,
        "task_revision": task.revision,
        "agent_profile_ref": profile_path,
        "skill_assignment_ref": paths["assignment"],
        "context_snapshot_ref": paths["task-snapshot"],
        "started_at": started_at,
        "finished_at": finished_at,
        "status": statuses.record_status,
        "runtime": {
            "name": "isolated-api-session",
            "version": "0.1.0",
            "adapter_version": binding.provider_adapter,
        },
        "model_usage_status": usage_status,
        "model_usage": usage_records,
        "coordination": {
            "delegated_attempts": 0,
            "handoff_count": 1,
            "review_rounds": 0,
            "max_parallel_observed": 0,
        },
        "trace": {
            "mode": "minimal",
            "external": False,
            "sensitive_data_detected": False,
            "redactions_applied": 0,
        },
        "output_refs": _dedupe(
            [
                paths["evidence"] if completed else paths["check"],
                paths["manifest"],
                paths["handoff"],
            ]
        ),
        "validation_refs": [paths["check"], paths["audit"]],
        "limitations": _dedupe(
            [STRUCTURAL_LIMITATION, DRIFT_LIMITATION] if model_drift else [STRUCTURAL_LIMITATION]
        ),
    }
    if statuses.completion_claim is not None:
        document["completion_claim"] = statuses.completion_claim
    return document


def _usage_records(outcome: SessionOutcome) -> tuple[str, list[dict[str, Any]]]:
    usage = outcome.usage
    if usage.input_tokens is not None and usage.output_tokens is not None:
        record: dict[str, Any] = {
            "provider": outcome.provider,
            "model": outcome.observed_models[0] if outcome.observed_models else outcome.requested_model,
            "requests": outcome.model_turns,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
        }
        if usage.cached_input_tokens is not None:
            record["cached_input_tokens"] = usage.cached_input_tokens
        if usage.reasoning_tokens is not None:
            record["reasoning_tokens"] = usage.reasoning_tokens
        if usage.provider_reported_cost is not None and usage.currency is not None:
            record["provider_reported_cost"] = usage.provider_reported_cost
            record["currency"] = usage.currency
        return "measured", [record]
    if outcome.model_turns == 0:
        return "not-applicable", []
    return "unavailable", []


def _main_state_document(
    task: TaskPacket,
    statuses,
    attempt_id: str,
    paths: Mapping[str, str],
    protocol: ProjectProtocol,
    protocol_path: str,
    finished_at: str,
    *,
    artifact_ref: str,
    handoff: Mapping[str, Any],
    main_snapshot: Mapping[str, Any],
    role_documents: Mapping[str, Mapping[str, Any]],
    base_state: Any | None,
) -> dict[str, Any]:
    constraints = (
        list(base_state.pinned_constraints)
        if base_state is not None
        else ["claim ceiling: " + ", ".join(protocol.claim_ceiling)]
        + (["local data must not be uploaded"] if protocol.data_boundary.get("local_only") else [])
    )
    decisions = list(base_state.accepted_decisions) if base_state is not None else []
    machine_refs = [
        {"path": paths[role], "sha256": _hash(serialize_document(document))}
        for role, document in sorted(role_documents.items())
        if role != "main-state"
    ]
    document: dict[str, Any] = {
        "schema_version": "0.1.0",
        "checkpoint_id": f"MS-{attempt_id.removeprefix('A-')}",
        "continuity_status": statuses.continuity_status,
        "project_protocol_ref": f"{protocol_path}@{protocol.revision}",
        "current_questions": list(protocol.question_refs),
        "pinned_constraints": _dedupe(constraints),
        "accepted_decisions": _dedupe(decisions),
        "active_tasks": [
            {
                "task_id": task.task_id,
                "status": statuses.record_status,
                "expected_handoff": paths["handoff"],
            }
        ],
        "recent_handoffs": [
            {"ref": paths["handoff"], "disposition": f"machine-recorded-{statuses.record_status}"}
        ],
        "open_conflicts": [],
        "open_risks": list(main_snapshot["assessment"]["triggered_rules"]),
        "next_actions": list(handoff["recommended_next_actions"]),
        "artifact_index_refs": [artifact_ref],
        "machine_state_refs": machine_refs,
        "rollover_reason": statuses.rollover_reason,
        "created_at": finished_at,
        "context_snapshot_ref": paths["main-snapshot"],
    }
    if base_state is not None and base_state.previous_checkpoint_ref:
        document["previous_checkpoint_ref"] = base_state.previous_checkpoint_ref
    document["checkpoint_digest"] = checkpoint_digest(document)
    return document
