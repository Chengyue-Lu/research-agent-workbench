"""Strict closeout and file-only replay for one executed ExecutionPlan.

``closeout`` maps the bounded session outcome onto the four terminal states,
publishes the Attempt/Receipt/Handoff/check-report chain with the same
tempfile+fsync+exclusive-link atomic publish as ``cli._write_yaml``, and merges
every deterministic check risk; any BLOCK risk forbids the ``completed`` state.
``verify_attempt`` replays the whole chain from files only and is read-only
and idempotent. See docs/implementation/K_API_2_FILE_LOOP.md §3/§4.

Two artifacts join the §4 layout when a Transfer Manifest is required:
``transfer-manifest.yaml`` and ``handoff-transfer-audit.yaml`` (both existing
schema kinds). The ExecutionPlan does not carry the Task Packet path, so the
frozen Task is located by scanning the project for a ``task_packet`` document
with the plan's task_id. When none is found, Handoff checks run against a
plan-derived surrogate and the Transfer Audit degrades to a blocking risk
instead of fabricating a task reference.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from research_workbench import __version__
from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.capability.models import AgentProfile
from research_workbench.capability.resolver import ResolvedTask
from research_workbench.context.handoff_transfer import assess_handoff_transfer
from research_workbench.contracts.common import ContractError, PermissionPolicy
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.execution.models import (
    ATTEMPT_DIRNAME_OUTPUTS,
    ATTEMPT_FILENAME,
    CHECK_REPORT_FILENAME,
    HANDOFF_FILENAME,
    PLAN_FILENAME,
    RECEIPT_FILENAME,
    TRANSCRIPT_FILENAME,
    CloseoutResult,
    ExecutionPlan,
    ExecutionRunResult,
)
from research_workbench.io import load_document
from research_workbench.observability.models import ExecutionReceipt, check_execution_receipt
from research_workbench.protocol.models import ProjectBudget, ProjectProtocol
from research_workbench.tasks.models import (
    DelegationPolicy,
    FileReference,
    HandoffPacket,
    HandoffPolicy,
    TaskBudget,
    TaskPacket,
)
from research_workbench.validation.documents import infer_document_kind
from research_workbench.validation.relationships import (
    check_handoff_against_task,
    check_references,
)
from research_workbench.validation.schemas import SchemaCatalog

MANIFEST_FILENAME = "transfer-manifest.yaml"
TRANSFER_AUDIT_FILENAME = "handoff-transfer-audit.yaml"

CONTRACT_HANDOFF_PACKET = "handoff-packet"
CONTRACT_TRANSFER_MANIFEST = "handoff-transfer-manifest"

PROTOCOL_FILENAME = "project-protocol.yaml"

__all__ = [
    "MANIFEST_FILENAME",
    "TRANSFER_AUDIT_FILENAME",
    "closeout",
    "verify_attempt",
]


def closeout(plan: ExecutionPlan, run: ExecutionRunResult, *, root: str | Path) -> CloseoutResult:
    """Validate one session outcome and publish the attempt file chain atomically."""

    root_path = Path(root).resolve()
    attempt_dir = resolve_within_root(root_path, plan.attempt_dir)
    if attempt_dir is None:
        raise ContractError("attempt_dir", "must stay within the project root")
    session = run.session
    notes: list[str] = []
    catalog = SchemaCatalog()

    final_message = _parse_final_message(run, notes)
    outputs = _scan_outputs(attempt_dir)
    output_refs = [_relative(root_path, path) for path in outputs]
    manifest_required = (
        plan.handoff_policy.require_transfer_manifest
        or CONTRACT_TRANSFER_MANIFEST in plan.required_outputs
    )
    missing_contracts = _missing_required_outputs(plan, outputs, catalog)
    if missing_contracts:
        notes.append("required outputs missing or schema-invalid: " + ", ".join(missing_contracts))
    if run.stale_inputs:
        notes.append("input lock drifted during the run: " + ", ".join(run.stale_inputs))
    notes.extend(f"session warning: {warning}" for warning in session.warnings)
    observed = set(session.observed_models)
    if observed and observed != {session.requested_model}:
        notes.append("provider observed models: " + ", ".join(session.observed_models))
    status = _initial_status(run, final_message, missing_contracts, outputs)

    task_path, task = _locate_task(root_path, plan.task_id)
    task_is_real = task is not None and task_path is not None
    assignment = _load_assignment(root_path, plan.assignment_ref)
    if task is None:
        task = _surrogate_task(plan.to_mapping(), _agent_profile_hint(plan, assignment), assignment)
        notes.append(
            "Task Packet was not found in the project; Handoff checks ran against "
            "the execution plan surrogate"
        )
    protocol = _load_protocol(root_path)
    now = _now()
    if _timestamp(now) < _timestamp(plan.started_at):
        # The compiler stamps microsecond precision while closeout truncates to
        # seconds; a sub-second run would otherwise invert the time interval.
        now = plan.started_at

    _publish_yaml(attempt_dir / PLAN_FILENAME, plan.to_mapping())
    transcript = _transcript_document(plan, run, final_message)
    transcript_hash = _publish_json(attempt_dir / TRANSCRIPT_FILENAME, transcript)
    transcript_rel = _relative(root_path, attempt_dir / TRANSCRIPT_FILENAME)

    # The Transfer Manifest pins the transcript hash, so it is published before
    # the Handoff that references it. Its items do not depend on the final
    # status whenever a final message exists, so the completed-to-incomplete
    # downgrade below never invalidates it.
    manifest_rel: str | None = None
    manifest_hash: str | None = None
    transfer_mappings: tuple[Mapping[str, Any], ...] = ()
    if manifest_required:
        manifest_mapping, transfer_mappings = _build_manifest(
            plan, run, final_message, status, now, transcript_rel, transcript_hash
        )
        manifest_hash = _publish_yaml(attempt_dir / MANIFEST_FILENAME, manifest_mapping)
        manifest_rel = _relative(root_path, attempt_dir / MANIFEST_FILENAME)

    handoff_rel = _relative(root_path, attempt_dir / HANDOFF_FILENAME)
    receipt_rel = _relative(root_path, attempt_dir / RECEIPT_FILENAME)
    audit_rel = _relative(root_path, attempt_dir / TRANSFER_AUDIT_FILENAME)
    audit_expected = manifest_required and task_is_real
    handoff_mapping = _build_handoff(
        plan, run, final_message, status, output_refs, transcript_rel, manifest_rel,
        audit_rel if audit_expected else None, receipt_rel,
    )
    handoff = HandoffPacket.from_mapping(handoff_mapping)
    risks: list[ContractRisk] = list(
        check_handoff_against_task(task, handoff, project_root=root_path, assignment=assignment)
    )
    predicted: list[ContractRisk] = []
    if manifest_required and not task_is_real:
        predicted.append(
            _block(
                "HANDOFF-AUDIT-REF-MISSING",
                f"Task Packet for {plan.task_id} was not found; the Transfer Audit cannot be built",
            )
        )
    # The semantic-review gate is evaluated here so the downgrade lands before
    # anything status-bearing is published; the real assess re-emits it below.
    review_gate = audit_expected and task.handoff_policy.semantic_review == "required"
    if status == "completed" and (_has_block(risks) or predicted or review_gate):
        # Never fabricate completion: a blocked closeout degrades before publish.
        status = "incomplete"
        handoff_mapping = _build_handoff(
            plan, run, final_message, status, output_refs, transcript_rel, manifest_rel,
            audit_rel if audit_expected else None, receipt_rel,
        )
        handoff = HandoffPacket.from_mapping(handoff_mapping)
    handoff_hash = _publish_yaml(attempt_dir / HANDOFF_FILENAME, handoff_mapping)

    if audit_expected:
        audit_mapping: Mapping[str, Any] | None = _build_audit(
            plan, root_path, task_path, handoff_rel, handoff_hash,
            manifest_rel, manifest_hash, transfer_mappings, now,
        )
        _publish_yaml(attempt_dir / TRANSFER_AUDIT_FILENAME, audit_mapping)
        risks.extend(assess_handoff_transfer(audit_mapping, root=root_path).risks)
    else:
        audit_mapping = None
        risks.extend(predicted)

    attempt_mapping = _build_attempt(
        plan, run, status, now, output_refs, manifest_rel, receipt_rel, handoff_rel
    )
    _publish_yaml(attempt_dir / ATTEMPT_FILENAME, attempt_mapping)
    attempt_rel = _relative(root_path, attempt_dir / ATTEMPT_FILENAME)

    receipt_mapping = _build_receipt(
        plan, run, status, now, attempt_rel, output_refs, manifest_rel, handoff_rel,
        audit_rel if audit_mapping is not None else None, notes,
    )
    receipt = ExecutionReceipt.from_mapping(receipt_mapping)
    receipt_risks = list(
        check_execution_receipt(receipt, protocol, root=root_path, receipt_ref=receipt_rel)
    )
    risks.extend(receipt_risks)
    if status == "completed" and _has_block(receipt_risks):
        # Defensive: blocking conditions are excluded by construction, so a
        # BLOCK here means the workspace changed under the closeout.
        status = "failed"
        risks.append(
            _block(
                "EXEC-CLOSEOUT-INVALID",
                "receipt check blocked a completed closeout; published Attempt may be stale",
            )
        )
        receipt_mapping = _build_receipt(
            plan, run, status, now, attempt_rel, output_refs, manifest_rel, handoff_rel,
            audit_rel if audit_mapping is not None else None, notes,
        )
    _publish_yaml(attempt_dir / RECEIPT_FILENAME, receipt_mapping)

    risks.extend(
        _schema_risks(
            catalog,
            (
                ("attempt", attempt_mapping),
                ("execution_receipt", receipt_mapping),
                ("handoff_packet", handoff_mapping),
                ("handoff_transfer_manifest", manifest_mapping if manifest_rel else None),
                ("handoff_transfer_audit", audit_mapping),
            ),
        )
    )
    if status == "completed" and _has_block(risks):
        status = "failed"

    report_mapping = _build_check_report(plan, status, risks, root_path, attempt_dir, outputs)
    report_errors = catalog.validate("deterministic_check_report", report_mapping)
    if report_errors:
        first = report_errors[0]
        risks.append(
            _block(
                "EXEC-CLOSEOUT-INVALID",
                f"check report failed schema validation at {first.pointer}: {first.message}",
            )
        )
        status = "failed"
    _publish_yaml(attempt_dir / CHECK_REPORT_FILENAME, report_mapping)

    return CloseoutResult(
        status=status,
        attempt_path=attempt_rel,
        receipt_path=receipt_rel,
        handoff_path=handoff_rel,
        check_report_path=_relative(root_path, attempt_dir / CHECK_REPORT_FILENAME),
        risks=_dedupe(risks),
    )


def verify_attempt(attempt_dir: str | Path, *, root: str | Path) -> tuple[ContractRisk, ...]:
    """Replay every deterministic closeout check from files only; read-only."""

    root_path = Path(root).resolve()
    attempt_path = Path(attempt_dir).resolve()
    try:
        attempt_path.relative_to(root_path)
    except ValueError:
        raise ContractError("attempt_dir", "must stay within the project root")
    risks: list[ContractRisk] = []
    catalog = SchemaCatalog()

    documents: dict[str, Mapping[str, Any]] = {}
    optional_present: set[str] = set()
    for filename, kind, optional in (
        (ATTEMPT_FILENAME, "attempt", False),
        (RECEIPT_FILENAME, "execution_receipt", False),
        (HANDOFF_FILENAME, "handoff_packet", False),
        (CHECK_REPORT_FILENAME, "deterministic_check_report", False),
        (MANIFEST_FILENAME, "handoff_transfer_manifest", True),
        (TRANSFER_AUDIT_FILENAME, "handoff_transfer_audit", True),
    ):
        path = attempt_path / filename
        if not path.is_file():
            if not optional:
                risks.append(_block("EXEC-CLOSEOUT-INVALID", f"closeout artifact is missing: {filename}"))
            continue
        optional_present.add(kind)
        document = _load_mapping_quiet(path)
        if document is None:
            risks.append(_block("EXEC-CLOSEOUT-INVALID", f"closeout artifact does not parse: {filename}"))
            continue
        errors = catalog.validate(kind, document)
        if errors:
            first = errors[0]
            risks.append(
                _block(
                    "EXEC-CLOSEOUT-INVALID",
                    f"{filename} failed schema validation at {first.pointer}: {first.message}",
                )
            )
        documents[kind] = document

    plan_document = _load_mapping_quiet(attempt_path / PLAN_FILENAME)
    if plan_document is None:
        risks.append(_block("EXEC-CLOSEOUT-INVALID", f"closeout artifact does not parse: {PLAN_FILENAME}"))

    report = documents.get("deterministic_check_report")
    if report is not None:
        subject_refs = [
            FileReference.from_mapping(item)
            for item in report.get("subject_refs", [])
            if isinstance(item, Mapping)
        ]
        risks.extend(check_references(root_path, subject_refs))
        pinned = {reference.path for reference in subject_refs}
        outputs_dir = attempt_path / ATTEMPT_DIRNAME_OUTPUTS
        if outputs_dir.is_dir():
            extras = sorted(
                _relative(root_path, path)
                for path in outputs_dir.iterdir()
                if path.is_file() and _relative(root_path, path) not in pinned
            )
            for extra in extras:
                risks.append(
                    _block(
                        "EXEC-CLOSEOUT-INVALID",
                        f"outputs file is not pinned by the check report: {extra}",
                    )
                )

    receipt_document = documents.get("execution_receipt")
    if receipt_document is not None:
        try:
            receipt = ExecutionReceipt.from_mapping(receipt_document)
        except ContractError as exc:
            risks.append(_block("EXEC-CLOSEOUT-INVALID", f"Execution Receipt is invalid: {exc}"))
        else:
            # A tampered workspace must not crash the replay; a failed check is
            # itself closeout evidence.
            try:
                risks.extend(
                    check_execution_receipt(
                        receipt,
                        _load_protocol(root_path),
                        root=root_path,
                        receipt_ref=_relative(root_path, attempt_path / RECEIPT_FILENAME),
                    )
                )
            except Exception as exc:
                risks.append(
                    _block("EXEC-CLOSEOUT-INVALID", f"receipt replay could not complete: {exc}")
                )

    handoff_document = documents.get("handoff_packet")
    if handoff_document is not None and plan_document is not None:
        try:
            handoff = HandoffPacket.from_mapping(handoff_document)
        except ContractError as exc:
            risks.append(_block("EXEC-CLOSEOUT-INVALID", f"Handoff Packet is invalid: {exc}"))
        else:
            task_id = str(plan_document.get("task_id", ""))
            _, task = _locate_task(root_path, task_id)
            assignment = _load_assignment(root_path, str(plan_document.get("assignment_ref", "")))
            if task is None:
                task = _surrogate_task(plan_document, _agent_profile_hint(None, assignment), assignment)
            try:
                risks.extend(
                    check_handoff_against_task(
                        task, handoff, project_root=root_path, assignment=assignment
                    )
                )
            except Exception as exc:
                risks.append(
                    _block("EXEC-CLOSEOUT-INVALID", f"handoff replay could not complete: {exc}")
                )
    if (
        "handoff_transfer_manifest" in optional_present
        and "handoff_transfer_audit" not in optional_present
    ):
        risks.append(
            _block(
                "HANDOFF-AUDIT-REF-MISSING",
                "Transfer Manifest exists but the Transfer Audit is missing",
            )
        )
    return _dedupe(risks)


# ---------------------------------------------------------------------------
# status mapping and required outputs


def _initial_status(
    run: ExecutionRunResult,
    final_message: Mapping[str, Any] | None,
    missing_contracts: tuple[str, ...],
    outputs: tuple[Path, ...],
) -> str:
    session_status = str(run.session.status)
    if session_status == "failed":
        return "failed"
    if session_status in {"blocked", "incomplete"}:
        return "incomplete"
    if session_status == "safe-paused" or run.stale_inputs:
        return "safe-paused"
    if final_message is None:
        return "incomplete"
    declared = final_message.get("status")
    if declared == "safe-paused":
        return "safe-paused"
    if declared != "completed":
        return "incomplete"
    if missing_contracts or not outputs:
        # A completed Handoff must reference at least one produced artifact.
        return "incomplete"
    return "completed"


def _parse_final_message(run: ExecutionRunResult, notes: list[str]) -> Mapping[str, Any] | None:
    response = run.session.final_response
    if response is None:
        notes.append("session ended without a final response; no closeout JSON was produced")
        return None
    texts = [
        block.text
        for block in response.output
        if block.kind == "text" and isinstance(block.text, str) and block.text.strip()
    ]
    for text in reversed(texts):
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping):
            return value
    if texts:
        notes.append("final response text is not a valid JSON closeout object")
    else:
        notes.append("final response carries no text block; no closeout JSON was produced")
    return None


def _scan_outputs(attempt_dir: Path) -> tuple[Path, ...]:
    outputs_dir = attempt_dir / ATTEMPT_DIRNAME_OUTPUTS
    if not outputs_dir.is_dir():
        return ()
    return tuple(
        path for path in sorted(outputs_dir.iterdir(), key=lambda item: item.name) if path.is_file()
    )


def _missing_required_outputs(
    plan: ExecutionPlan,
    outputs: tuple[Path, ...],
    catalog: SchemaCatalog,
) -> tuple[str, ...]:
    parsed: list[Mapping[str, Any]] = []
    for path in outputs:
        if path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            continue
        document = _load_mapping_quiet(path)
        if document is not None:
            parsed.append(document)
    missing: list[str] = []
    for contract in plan.required_outputs:
        if contract in {CONTRACT_HANDOFF_PACKET, CONTRACT_TRANSFER_MANIFEST}:
            continue  # closeout-produced handoff.yaml / transfer-manifest.yaml
        if not any(_satisfies_contract(catalog, document, contract) for document in parsed):
            missing.append(contract)
    return tuple(missing)


def _satisfies_contract(catalog: SchemaCatalog, document: Mapping[str, Any], contract: str) -> bool:
    kind = infer_document_kind(document)
    if kind is None:
        return False
    object_type = document.get("object_type")
    matches = kind in {contract, contract.replace("-", "_")} or (
        kind == "research_object"
        and isinstance(object_type, str)
        and contract in {object_type, f"{object_type}-record"}
    )
    if not matches:
        return False
    try:
        return not catalog.validate(kind, document)
    except KeyError:
        # Registry kinds without a schema file can only be matched structurally.
        return True


# ---------------------------------------------------------------------------
# document builders


def _build_handoff(
    plan: ExecutionPlan,
    run: ExecutionRunResult,
    final_message: Mapping[str, Any] | None,
    status: str,
    output_refs: list[str],
    transcript_rel: str,
    manifest_rel: str | None,
    audit_rel: str | None,
    receipt_rel: str,
) -> dict[str, Any]:
    session = run.session
    if final_message is not None:
        summary = str(final_message.get("summary") or f"attempt ended as {status}")
        limitations = [str(item) for item in final_message.get("limitations", [])]
        unresolved = [str(item) for item in final_message.get("unresolved", [])]
    else:
        summary = f"attempt {plan.attempt_id} ended as {status}: {session.stop_reason}"
        limitations = []
        unresolved = [f"session stopped before a final closeout message: {session.stop_reason}"]
    if status == "safe-paused" and not unresolved:
        unresolved.append(f"session stopped before completion: {session.stop_reason}")
    artifact_refs = list(output_refs)
    if manifest_rel is not None:
        # Manifest items source their statements from the transcript, so the
        # Handoff must index it (HANDOFF-AUDIT-SOURCE-NOT-INDEXED).
        artifact_refs.append(transcript_rel)
    recommended: list[str] = []
    if status == "safe-paused":
        recommended.append(
            f"resume {plan.task_id} with a fresh attempt under the unchanged input lock"
        )
        if run.stale_inputs:
            recommended.append("re-freeze the Task inputs that drifted before resuming")
    handoff: dict[str, Any] = {
        "schema_version": "0.1.0",
        "task_id": plan.task_id,
        "attempt_id": plan.attempt_id,
        "status": status,
        "input_lock": [_file_reference_mapping(reference) for reference in plan.input_lock],
        "skill_lock": list(plan.skill_lock),
        "skill_assignment_ref": plan.assignment_ref,
        "result": {
            "summary": summary,
            "facts": [summary],
            "inferences": [],
            "recommendations": [],
        },
        "artifact_refs": sorted(set(artifact_refs)),
        "validation_refs": [audit_rel] if audit_rel is not None else [],
        "limitations": limitations,
        "conflicts": [],
        "unresolved": unresolved,
        "human_decision_required": [],
        "recommended_next_actions": recommended,
        "execution_receipt_ref": receipt_rel,
    }
    if manifest_rel is not None:
        handoff["transfer_manifest_ref"] = manifest_rel
    return handoff


def _build_manifest(
    plan: ExecutionPlan,
    run: ExecutionRunResult,
    final_message: Mapping[str, Any] | None,
    status: str,
    now: str,
    transcript_rel: str,
    transcript_hash: str,
) -> tuple[dict[str, Any], tuple[Mapping[str, Any], ...]]:
    source_ref = {"path": transcript_rel, "sha256": transcript_hash}
    items: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []

    def add_item(kind: str, statement: str, source_locator: str, handoff_locator: str) -> None:
        item_id = f"HTI-{plan.attempt_id}-{len(items) + 1:03d}"
        items.append(
            {
                "item_id": item_id,
                "kind": kind,
                "criticality": "material",
                "required_for_handoff": True,
                "statement": statement,
                "source_ref": source_ref,
                "source_locator": source_locator,
            }
        )
        mappings.append({"item_id": item_id, "status": "carried", "handoff_locator": handoff_locator})

    if final_message is not None:
        summary = str(final_message.get("summary") or f"attempt ended as {status}")
        add_item("fact", summary, "/final_message/summary", "/result/facts/0")
        for index, limitation in enumerate(final_message.get("limitations", [])):
            add_item(
                "limitation",
                str(limitation),
                f"/final_message/limitations/{index}",
                f"/limitations/{index}",
            )
        for index, open_item in enumerate(final_message.get("unresolved", [])):
            add_item(
                "unresolved",
                str(open_item),
                f"/final_message/unresolved/{index}",
                f"/unresolved/{index}",
            )
        if status == "safe-paused" and not final_message.get("unresolved"):
            add_item(
                "unresolved",
                f"session stopped before completion: {run.session.stop_reason}",
                "/stop_reason",
                "/unresolved/0",
            )
    else:
        add_item(
            "fact",
            f"attempt {plan.attempt_id} ended as {status}: {run.session.stop_reason}",
            "/status",
            "/result/facts/0",
        )
        add_item(
            "unresolved",
            f"session stopped before a final closeout message: {run.session.stop_reason}",
            "/stop_reason",
            "/unresolved/0",
        )
    manifest = {
        "schema_version": "0.1.0",
        "manifest_id": f"HTM-{plan.attempt_id}",
        "task_id": plan.task_id,
        "task_revision": plan.task_revision,
        "attempt_id": plan.attempt_id,
        "generated_at": now,
        "declared_by": "task-agent",
        "source_artifact_refs": [source_ref],
        "items": items,
        "limitations": [
            "The manifest is generated at closeout from the session transcript; it "
            "declares transfer coverage and does not claim semantic review."
        ],
    }
    return manifest, tuple(mappings)


def _build_audit(
    plan: ExecutionPlan,
    root: Path,
    task_path: Path,
    handoff_rel: str,
    handoff_hash: str,
    manifest_rel: str | None,
    manifest_hash: str | None,
    mappings: tuple[Mapping[str, Any], ...],
    now: str,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "audit_id": f"HTA-{plan.attempt_id}",
        "task_ref": {
            "path": _relative(root, task_path),
            "sha256": hash_file(task_path),
        },
        "handoff_ref": {"path": handoff_rel, "sha256": handoff_hash},
        "manifest_ref": {"path": manifest_rel, "sha256": manifest_hash},
        "generated_at": now,
        "mappings": list(mappings),
        "review": {
            "status": "pending",
            "reviewer_kind": "none",
            "reviewer_independent": False,
            "sampled_item_ids": [],
            "findings": [],
        },
        "limitations": [
            "Structural coverage is generated at closeout; semantic equivalence "
            "still requires a bounded human review."
        ],
    }


def _build_attempt(
    plan: ExecutionPlan,
    run: ExecutionRunResult,
    status: str,
    now: str,
    output_refs: list[str],
    manifest_rel: str | None,
    receipt_rel: str,
    handoff_rel: str,
) -> dict[str, Any]:
    artifact_refs = list(output_refs)
    if manifest_rel is not None:
        artifact_refs.append(manifest_rel)
    attempt: dict[str, Any] = {
        "schema_version": "0.1.0",
        "task_id": plan.task_id,
        "task_revision": plan.task_revision,
        "attempt_id": plan.attempt_id,
        "status": status,
        "started_at": plan.started_at,
        "finished_at": now,
        "trigger_reason": "bounded API task execution",
        "input_lock": [_file_reference_mapping(reference) for reference in plan.input_lock],
        "skill_lock": list(plan.skill_lock),
        "skill_assignment_ref": plan.assignment_ref,
        "execution_receipt_ref": receipt_rel,
        "artifact_refs": sorted(set(artifact_refs)),
        "handoff_ref": handoff_rel,
    }
    if status == "failed":
        attempt["failure"] = {"reason": f"session {run.session.status}: {run.session.stop_reason}"}
    return attempt


def _build_receipt(
    plan: ExecutionPlan,
    run: ExecutionRunResult,
    status: str,
    now: str,
    attempt_rel: str,
    output_refs: list[str],
    manifest_rel: str | None,
    handoff_rel: str,
    audit_rel: str | None,
    limitations: list[str],
) -> dict[str, Any]:
    session = run.session
    usage = session.usage
    model_usage: list[dict[str, Any]] = []
    if session.model_turns:
        record: dict[str, Any] = {
            "provider": session.provider,
            "model": session.requested_model,
            "requests": session.model_turns,
        }
        for field in (
            "input_tokens",
            "output_tokens",
            "cached_input_tokens",
            "reasoning_tokens",
            "provider_reported_cost",
            "currency",
        ):
            value = getattr(usage, field)
            if value is not None:
                record[field] = value
        model_usage.append(record)
    usage_status = (
        "measured"
        if model_usage and usage.input_tokens is not None and usage.output_tokens is not None
        else "unavailable"
    )
    runtime: dict[str, Any] = {
        "name": session.provider,
        "version": __version__,
        "adapter_version": plan.model_binding.provider_adapter,
    }
    if session.final_response is not None and session.final_response.response_id:
        runtime["native_execution_id"] = session.final_response.response_id
    receipt_output_refs = list(output_refs)
    if manifest_rel is not None:
        receipt_output_refs.append(manifest_rel)
    receipt_output_refs.append(handoff_rel)
    return {
        "schema_version": "0.1.0",
        "receipt_id": f"XR-{plan.attempt_id}",
        "execution_kind": "model-api",
        "attempt_ref": attempt_rel,
        "task_id": plan.task_id,
        "task_revision": plan.task_revision,
        "agent_profile_ref": plan.profile_ref,
        "skill_assignment_ref": plan.assignment_ref,
        "started_at": plan.started_at,
        "finished_at": now,
        "status": status,
        "completion_claim": "execution-only",
        "runtime": runtime,
        "model_usage_status": usage_status,
        "model_usage": model_usage,
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
        "output_refs": sorted(set(receipt_output_refs)),
        "validation_refs": [audit_rel] if audit_rel is not None else [],
        "limitations": limitations,
    }


def _build_check_report(
    plan: ExecutionPlan,
    status: str,
    risks: list[ContractRisk],
    root: Path,
    attempt_dir: Path,
    outputs: tuple[Path, ...],
) -> dict[str, Any]:
    subjects: list[dict[str, str]] = []
    for name in (
        PLAN_FILENAME,
        TRANSCRIPT_FILENAME,
        MANIFEST_FILENAME,
        HANDOFF_FILENAME,
        TRANSFER_AUDIT_FILENAME,
        ATTEMPT_FILENAME,
        RECEIPT_FILENAME,
    ):
        path = attempt_dir / name
        if path.is_file():
            subjects.append({"path": _relative(root, path), "sha256": hash_file(path)})
    subjects.extend(
        {"path": _relative(root, path), "sha256": hash_file(path)} for path in outputs
    )
    unique_subjects = list({subject["path"]: subject for subject in subjects}.values())
    blockers = sum(1 for risk in risks if risk.level == RiskLevel.BLOCK)
    checks = [
        {
            "code": "EXEC-CLOSEOUT-SUMMARY",
            "status": "fail" if blockers else "pass",
            "detail": f"closeout status={status}; blocking risks={blockers}",
        }
    ]
    checks.extend(
        {
            "code": risk.code,
            "status": "fail" if risk.level == RiskLevel.BLOCK else "pass",
            "detail": f"{risk.level}: {risk.message}",
        }
        for risk in risks
    )
    return {
        "schema_version": "0.1.0",
        "report_id": f"DCR-{plan.attempt_id}",
        "checker": {
            "checker_id": "execution-closeout",
            "version": __version__,
            # The checker is this closeout module; the frozen execution plan is
            # the in-root artifact that pins the contract the checks enforced.
            "source_ref": subjects[0],
        },
        "subject_refs": unique_subjects,
        "status": "fail" if blockers else "pass",
        "checks": checks,
        "scope": f"closeout of attempt {plan.attempt_id} for task {plan.task_id}@{plan.task_revision}",
        "limitations": [
            "checker.source_ref pins the frozen execution plan, not the closeout "
            "module source, which lives outside the project root.",
            "A pass establishes structural closeout validity only, never scientific correctness.",
        ],
    }


def _transcript_document(
    plan: ExecutionPlan,
    run: ExecutionRunResult,
    final_message: Mapping[str, Any] | None,
) -> dict[str, Any]:
    session = run.session
    document: dict[str, Any] = {
        "schema_version": "0.1.0",
        "attempt_id": plan.attempt_id,
        "provider": session.provider,
        "requested_model": session.requested_model,
        "observed_models": list(session.observed_models),
        "status": str(session.status),
        "stop_reason": session.stop_reason,
        "model_turns": session.model_turns,
        "tool_calls": session.tool_calls,
        "warnings": list(session.warnings),
        "transcript": [dict(entry) for entry in run.transcript],
        "tool_events": [
            {
                "name": event.name,
                "ok": event.ok,
                "path": event.path,
                "sha256": event.sha256,
                "detail": event.detail,
            }
            for event in run.tool_events
        ],
    }
    if final_message is not None:
        document["final_message"] = dict(final_message)
    return document


# ---------------------------------------------------------------------------
# shared loading helpers


def _locate_task(root: Path, task_id: str) -> tuple[Path | None, TaskPacket | None]:
    if not task_id:
        return None, None
    candidates: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if name != "work" and not name.startswith(".")
        )
        for filename in sorted(filenames):
            if Path(filename).suffix.lower() in {".json", ".yaml", ".yml"}:
                candidates.append(Path(current) / filename)
    for path in sorted(candidates):
        document = _load_mapping_quiet(path)
        if (
            document is None
            or infer_document_kind(document) != "task_packet"
            or document.get("task_id") != task_id
        ):
            continue
        try:
            task = TaskPacket.from_mapping(document)
        except ContractError:
            return None, None
        if SchemaCatalog().validate("task_packet", document):
            return None, None
        return path, task
    return None, None


def _surrogate_task(
    plan_mapping: Mapping[str, Any],
    agent_profile: str,
    assignment: ResolvedTask | None,
) -> TaskPacket:
    """Reconstruct the check-relevant Task face frozen into the ExecutionPlan.

    required_skills falls back to the locked Skill set, so HANDOFF-SKILL-LOSS
    cannot fire from the surrogate; every other check uses accurate plan data.
    """

    if not agent_profile and assignment is not None:
        agent_profile = assignment.agent_profile.split("@", 1)[0]
    policy_mapping = plan_mapping.get("handoff_policy")
    policy = (
        HandoffPolicy.from_mapping(policy_mapping)
        if isinstance(policy_mapping, Mapping)
        else HandoffPolicy()
    )
    return TaskPacket(
        schema_version="0.1.0",
        task_id=str(plan_mapping.get("task_id", "")),
        goal="(reconstructed from the frozen execution plan)",
        question_refs=(),
        active_modes=(),
        required_capabilities=(),
        required_skills=tuple(str(item) for item in plan_mapping.get("skill_lock", ())),
        forbidden_skills=(),
        agent_profile=agent_profile or "unknown",
        input_refs=tuple(
            FileReference.from_mapping(item)
            for item in plan_mapping.get("input_lock", ())
            if isinstance(item, Mapping)
        ),
        write_scope=tuple(str(item) for item in plan_mapping.get("write_scope", ()) or ("work",)),
        required_outputs=tuple(
            str(item) for item in plan_mapping.get("required_outputs", ()) or ("handoff-packet",)
        ),
        permissions=PermissionPolicy(),
        delegation=DelegationPolicy(),
        budget=TaskBudget(),
        atomic_boundary="(reconstructed from the frozen execution plan)",
        completion_checks=("(reconstructed)",),
        safe_pause_conditions=("(reconstructed)",),
        stop_conditions=("(reconstructed)",),
        stale_if=(),
        handoff_policy=policy,
        revision=int(plan_mapping.get("task_revision", 1)),
    )


def _agent_profile_hint(plan: ExecutionPlan | None, assignment: ResolvedTask | None) -> str:
    if plan is not None:
        profile = _load_profile(Path(plan.root).resolve(), plan.profile_ref)
        if profile is not None:
            return profile.agent_profile_id
    if assignment is not None:
        return assignment.agent_profile.split("@", 1)[0]
    return ""


def _load_assignment(root: Path, reference: str) -> ResolvedTask | None:
    document = _load_referenced(root, reference)
    if document is None:
        return None
    try:
        return ResolvedTask.from_mapping(document)
    except ContractError:
        return None


def _load_profile(root: Path, reference: str) -> AgentProfile | None:
    document = _load_referenced(root, reference)
    if document is None:
        return None
    try:
        return AgentProfile.from_mapping(document)
    except ContractError:
        return None


def _load_referenced(root: Path, reference: str) -> Mapping[str, Any] | None:
    if not reference:
        return None
    path = Path(reference)
    resolved = path if path.is_absolute() else resolve_within_root(root, reference)
    if resolved is None or not resolved.is_file():
        return None
    return _load_mapping_quiet(resolved)


def _load_protocol(root: Path) -> ProjectProtocol:
    document = _load_mapping_quiet(root / PROTOCOL_FILENAME)
    if document is not None:
        try:
            return ProjectProtocol.from_mapping(document)
        except ContractError:
            pass
    # Default mirrors the `rwb init` template budgets with an open boundary;
    # the protocol-dependent receipt checks stay inert for closeout receipts.
    return ProjectProtocol(
        schema_version="0.1.0",
        project_id="default",
        question_refs=(),
        active_modes=(),
        claim_ceiling=(),
        required_human_gates=(),
        budgets=ProjectBudget(),
        context_policy={},
        data_boundary={},
    )


def _load_mapping_quiet(path: Path) -> Mapping[str, Any] | None:
    try:
        document = load_document(path)
    except Exception:
        return None
    return document if isinstance(document, Mapping) else None


def _schema_risks(
    catalog: SchemaCatalog,
    artifacts: tuple[tuple[str, Mapping[str, Any] | None], ...],
) -> list[ContractRisk]:
    risks: list[ContractRisk] = []
    for kind, document in artifacts:
        if document is None:
            continue
        errors = catalog.validate(kind, document)
        if errors:
            first = errors[0]
            risks.append(
                _block(
                    "EXEC-CLOSEOUT-INVALID",
                    f"published {kind} failed schema validation at {first.pointer}: {first.message}",
                )
            )
    return risks


# ---------------------------------------------------------------------------
# atomic publish and small utilities


def _publish_yaml(path: Path, document: Mapping[str, Any]) -> str:
    payload = yaml.safe_dump(dict(document), sort_keys=False, allow_unicode=True).encode("utf-8")
    return _publish_bytes(path, payload)


def _publish_json(path: Path, document: Mapping[str, Any]) -> str:
    payload = (json.dumps(document, ensure_ascii=False, indent=2, default=str) + "\n").encode("utf-8")
    return _publish_bytes(path, payload)


def _publish_bytes(path: Path, payload: bytes) -> str:
    """Publish via tempfile+fsync+exclusive link, mirroring cli._write_yaml."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return hashlib.sha256(payload).hexdigest()


def _file_reference_mapping(reference: FileReference) -> dict[str, Any]:
    mapping: dict[str, Any] = {"path": reference.path, "sha256": reference.sha256}
    if reference.revision is not None:
        mapping["revision"] = reference.revision
    return mapping


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _block(code: str, message: str) -> ContractRisk:
    return ContractRisk(code, RiskLevel.BLOCK, message)


def _has_block(risks: list[ContractRisk]) -> bool:
    return any(risk.level == RiskLevel.BLOCK for risk in risks)


def _dedupe(risks: list[ContractRisk]) -> tuple[ContractRisk, ...]:
    seen: set[tuple[str, str]] = set()
    result: list[ContractRisk] = []
    for risk in risks:
        key = (risk.code, risk.message)
        if key not in seen:
            seen.add(key)
            result.append(risk)
    return tuple(result)
