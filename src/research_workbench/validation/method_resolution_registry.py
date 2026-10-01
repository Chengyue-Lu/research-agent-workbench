"""Fail-closed Method Resolution registry and Action-inheritance validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from research_workbench.validation.capability_registry import (
    capability_requirement_entries as _capability_requirement_entries,
    capability_requirement_indices as _capability_requirement_indices,
)
from research_workbench.validation.document_core import (
    ValidationIssue,
    document_hash as _document_hash,
)
from research_workbench.validation.document_kinds import infer_document_kind


def validate_method_resolutions(documents: Mapping[Path, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    capability_indices = _capability_requirement_indices(documents)
    capability_entries = _capability_requirement_entries(documents)
    modes = {
        f"{document.get('mode_id')}@{document.get('version')}"
        for document in documents.values()
        if isinstance(document, Mapping)
        and "mode_id" in document
        and "claim_rules" in document
    }
    action_entries: dict[str, Mapping[str, Any]] = {}
    action_documents: dict[str, tuple[Path, Mapping[str, Any]]] = {}
    task_documents: dict[tuple[str, int], tuple[Path, Mapping[str, Any]]] = {}
    for path, document in documents.items():
        if not isinstance(document, Mapping):
            continue
        kind = infer_document_kind(document)
        if kind == "mode_action":
            action_documents[
                f"{document.get('action_id')}@{document.get('version')}"
            ] = (path, document)
        elif kind == "task_packet" and isinstance(document.get("revision"), int):
            key = (str(document.get("task_id")), int(document["revision"]))
            if key in task_documents:
                issues.append(
                    ValidationIssue(
                        path,
                        "METHOD-RESOLUTION-TASK-DUPLICATE",
                        f"duplicate Task identity available to Method Resolution: {key}",
                    )
                )
            task_documents[key] = (path, document)
    for document in documents.values():
        if not isinstance(document, Mapping) or document.get("registry_kind") != "mode_action_registry":
            continue
        for entry in document.get("entries", []):
            if isinstance(entry, Mapping):
                action_entries[f"{entry.get('action_id')}@{entry.get('version')}"] = entry

    seen_resolutions: set[tuple[str, int]] = set()
    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "method_resolution":
            continue
        revision = document.get("revision")
        resolution_key = (
            str(document.get("resolution_id")),
            revision if isinstance(revision, int) else 0,
        )
        if resolution_key in seen_resolutions:
            issues.append(
                ValidationIssue(
                    path,
                    "METHOD-RESOLUTION-DUPLICATE",
                    f"duplicate Method Resolution identity: {resolution_key}",
                )
            )
        seen_resolutions.add(resolution_key)

        task_document: Mapping[str, Any] | None = None
        task_ref = document.get("task_ref")
        if isinstance(task_ref, Mapping):
            task_revision = task_ref.get("revision")
            task_key = (
                str(task_ref.get("task_id")),
                task_revision if isinstance(task_revision, int) else 0,
            )
            loaded_task = task_documents.get(task_key)
            if loaded_task is None:
                issues.append(
                    ValidationIssue(
                        path,
                        "METHOD-RESOLUTION-TASK-MISSING",
                        f"no loaded TaskPacket matches task_id and revision: {task_key}",
                    )
                )
            else:
                task_path, task_document = loaded_task
                recorded_hash = str(task_ref.get("sha256", "")).removeprefix("sha256:").lower()
                if recorded_hash != _document_hash(documents, task_path):
                    issues.append(
                        ValidationIssue(
                            path,
                            "METHOD-RESOLUTION-TASK-HASH-MISMATCH",
                            f"task_ref hash does not match TaskPacket bytes for {task_key}",
                        )
                    )

        mode_resolution = document.get("mode_resolution", {})
        selected_mode_refs = {
            value
            for value in mode_resolution.get("selected_mode_refs", [])
            if isinstance(value, str)
        } if isinstance(mode_resolution, Mapping) else set()
        if modes and isinstance(mode_resolution, Mapping):
            for mode_ref in mode_resolution.get("selected_mode_refs", []):
                if isinstance(mode_ref, str) and mode_ref not in modes:
                    issues.append(
                        ValidationIssue(
                            path,
                            "METHOD-RESOLUTION-MODE-MISSING",
                            f"unknown selected Research Mode: {mode_ref}",
                        )
                    )

        decision_ids: set[str] = set()
        obligation_ids: set[str] = set()
        skill_need_refs: set[str] = set()
        capability_requirement_refs: set[str] = set()
        human_gate_refs: set[str] = set()
        blocked_conditions: set[str] = set()
        for index, decision in enumerate(document.get("action_decisions", [])):
            if not isinstance(decision, Mapping):
                continue
            decision_id = decision.get("decision_id")
            if isinstance(decision_id, str):
                if decision_id in decision_ids:
                    issues.append(
                        ValidationIssue(
                            path,
                            "METHOD-RESOLUTION-DECISION-DUPLICATE",
                            f"duplicate action decision ID: {decision_id}",
                        )
                    )
                decision_ids.add(decision_id)
            action_ref = decision.get("action_ref")
            if "claim_effects" in decision:
                issues.append(
                    ValidationIssue(
                        path,
                        "METHOD-RESOLUTION-CLAIM-EFFECT-OVERRIDE",
                        f"action_decisions[{index}] cannot redefine Action claim effects",
                    )
                )
            if isinstance(action_ref, str) and action_entries:
                entry = action_entries.get(action_ref)
                if entry is None:
                    issues.append(
                        ValidationIssue(
                            path,
                            "METHOD-RESOLUTION-ACTION-MISSING",
                            f"action_decisions[{index}] references unknown Action: {action_ref}",
                        )
                    )
                elif decision.get("action_content_hash") != entry.get("content_hash"):
                    issues.append(
                        ValidationIssue(
                            path,
                            "METHOD-RESOLUTION-ACTION-HASH-MISMATCH",
                            f"action_decisions[{index}] hash does not match Registry for {action_ref}",
                        )
                    )
                else:
                    if entry.get("mode_ref") not in selected_mode_refs:
                        issues.append(
                            ValidationIssue(
                                path,
                                "METHOD-RESOLUTION-ACTION-MODE-MISMATCH",
                                f"action_decisions[{index}] Action mode_ref is not selected: {entry.get('mode_ref')}",
                            )
                        )
                    loaded_action = action_documents.get(action_ref)
                    if loaded_action is None:
                        issues.append(
                            ValidationIssue(
                                path,
                                "METHOD-RESOLUTION-ACTION-DOCUMENT-MISSING",
                                f"Action document is not loaded for {action_ref}",
                            )
                        )
                    else:
                        _, action_document = loaded_action
                        decision_gates = {
                            value for value in decision.get("human_gate_refs", []) if isinstance(value, str)
                        }
                        action_gates = {
                            value for value in action_document.get("human_gates", []) if isinstance(value, str)
                        }
                        missing_gates = sorted(action_gates - decision_gates)
                        if missing_gates:
                            issues.append(
                                ValidationIssue(
                                    path,
                                    "METHOD-RESOLUTION-ACTION-GATE-MISSING",
                                    f"action_decisions[{index}] drops or renames required Action gates: {missing_gates}",
                                )
                            )
                        evidence_plan = {
                            value
                            for obligation in decision.get("obligations", [])
                            if isinstance(obligation, Mapping)
                            for value in obligation.get("required_evidence", [])
                            if isinstance(value, str)
                        }
                        required_artifacts = {
                            value for value in action_document.get("required_artifacts", []) if isinstance(value, str)
                        }
                        missing_artifacts = sorted(required_artifacts - evidence_plan)
                        if missing_artifacts:
                            issues.append(
                                ValidationIssue(
                                    path,
                                    "METHOD-RESOLUTION-ACTION-ARTIFACT-MISSING",
                                    f"action_decisions[{index}] evidence plan omits Action artifacts: {missing_artifacts}",
                                )
                            )
                        for field, code in (
                            ("stop_conditions", "METHOD-RESOLUTION-ACTION-STOP-MISSING"),
                            ("blocked_conditions", "METHOD-RESOLUTION-ACTION-BLOCK-MISSING"),
                        ):
                            inherited = {
                                value for value in action_document.get(field, []) if isinstance(value, str)
                            }
                            resolved = {
                                value for value in decision.get(field, []) if isinstance(value, str)
                            }
                            missing = sorted(inherited - resolved)
                            if missing:
                                issues.append(
                                    ValidationIssue(
                                        path,
                                        code,
                                        f"action_decisions[{index}] drops Action {field}: {missing}",
                                    )
                                )
            for obligation in decision.get("obligations", []):
                if not isinstance(obligation, Mapping):
                    continue
                obligation_id = obligation.get("obligation_id")
                if isinstance(obligation_id, str):
                    if obligation_id in obligation_ids:
                        issues.append(
                            ValidationIssue(
                                path,
                                "METHOD-RESOLUTION-OBLIGATION-DUPLICATE",
                                f"duplicate obligation ID: {obligation_id}",
                            )
                        )
                    obligation_ids.add(obligation_id)
            skill_need_refs.update(
                value for value in decision.get("skill_need_refs", []) if isinstance(value, str)
            )
            for requirement_id in decision.get("capability_requirements", []):
                if not isinstance(requirement_id, str):
                    continue
                capability_requirement_refs.add(requirement_id)
                if capability_indices and requirement_id not in capability_entries:
                    issues.append(
                        ValidationIssue(
                            path,
                            "METHOD-RESOLUTION-CAPABILITY-REQUIREMENT-MISSING",
                            f"action_decisions[{index}] references an unknown Capability Requirement: {requirement_id}",
                        )
                    )
            human_gate_refs.update(
                value for value in decision.get("human_gate_refs", []) if isinstance(value, str)
            )
            blocked_conditions.update(
                value for value in decision.get("blocked_conditions", []) if isinstance(value, str)
            )

        skill_disposition = document.get("skill_disposition", {})
        declared_skill_needs = (
            {
                value
                for value in skill_disposition.get("need_refs", [])
                if isinstance(value, str)
            }
            if isinstance(skill_disposition, Mapping)
            else set()
        )
        closure_checks = (
            (
                declared_skill_needs,
                skill_need_refs,
                "METHOD-RESOLUTION-SKILL-NEED-CLOSURE",
                "skill_disposition.need_refs",
            ),
            (
                {value for value in document.get("human_gate_refs", []) if isinstance(value, str)},
                human_gate_refs,
                "METHOD-RESOLUTION-HUMAN-GATE-CLOSURE",
                "human_gate_refs",
            ),
            (
                {value for value in document.get("blocked_conditions", []) if isinstance(value, str)},
                blocked_conditions,
                "METHOD-RESOLUTION-BLOCK-CLOSURE",
                "blocked_conditions",
            ),
        )
        for declared, derived, code, field in closure_checks:
            if declared != derived:
                issues.append(
                    ValidationIssue(
                        path,
                        code,
                        f"{field} must exactly match action decision references: "
                        f"declared={sorted(declared)}, derived={sorted(derived)}",
                    )
                )

        if task_document is not None:
            task_requirements = {
                value
                for value in task_document.get("required_capabilities", [])
                if isinstance(value, str)
            }
            if task_requirements != capability_requirement_refs:
                issues.append(
                    ValidationIssue(
                        path,
                        "METHOD-RESOLUTION-CAPABILITY-REQUIREMENT-CLOSURE",
                        "Task required_capabilities must exactly match action decision Capability Requirements: "
                        f"task={sorted(task_requirements)}, method={sorted(capability_requirement_refs)}",
                    )
                )

        alternatives: set[str] = set()
        for alternative in document.get("rejected_alternatives", []):
            if not isinstance(alternative, Mapping):
                continue
            alternative_id = alternative.get("alternative_id")
            if isinstance(alternative_id, str):
                if alternative_id in alternatives:
                    issues.append(
                        ValidationIssue(
                            path,
                            "METHOD-RESOLUTION-ALTERNATIVE-DUPLICATE",
                            f"duplicate rejected alternative: {alternative_id}",
                        )
                    )
                alternatives.add(alternative_id)
    return issues
