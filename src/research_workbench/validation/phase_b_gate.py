"""Fail-closed Phase B evolution and replacement Gate validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from research_workbench.validation.document_core import (
    ValidationIssue,
    document_hash as _document_hash,
    loaded_document_at as _loaded_document_at,
)
from research_workbench.validation.document_kinds import infer_document_kind


def _phase_b_gate_identity(kind: str, document: Mapping[str, Any]) -> str | None:
    fields: dict[str, tuple[str, str | None]] = {
        "task-packet": ("task_id", "revision"),
        "research-mode": ("mode_id", "version"),
        "mode-action": ("action_id", "version"),
        "method-resolution": ("resolution_id", "revision"),
        "capability-requirement": ("requirement_id", None),
    }
    identity = fields.get(kind)
    if identity is None:
        return None
    id_field, version_field = identity
    object_id = document.get(id_field)
    if not isinstance(object_id, str):
        return None
    if version_field is None:
        return object_id
    version = document.get(version_field)
    if kind in {"task-packet", "method-resolution"}:
        return f"{object_id}@r{version}" if isinstance(version, int) else None
    return f"{object_id}@{version}" if isinstance(version, str) else None


def validate_phase_b_evolution_gates(
    documents: Mapping[Path, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    expected_document_kinds = {
        "task-packet": "task_packet",
        "research-mode": "research_mode",
        "mode-action": "mode_action",
        "method-resolution": "method_resolution",
        "capability-requirement": "capability_requirement",
    }

    for gate_path, gate in documents.items():
        if not isinstance(gate, Mapping) or infer_document_kind(gate) != "phase_b_evolution_gate":
            continue

        stable_refs = gate.get("stable_contract_refs")
        loaded_contracts: dict[str, list[tuple[str, Path, Mapping[str, Any], Mapping[str, Any]]]] = {}
        if isinstance(stable_refs, list):
            for reference in stable_refs:
                if not isinstance(reference, Mapping):
                    continue
                kind = reference.get("kind")
                ref = reference.get("ref")
                loaded = _loaded_document_at(documents, reference.get("document_path"))
                if not isinstance(kind, str) or not isinstance(ref, str) or loaded is None:
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-CONTRACT-MISSING",
                            f"stable contract is not loaded: {reference.get('document_path')}",
                        )
                    )
                    continue
                document_path, document = loaded
                actual_kind = infer_document_kind(document)
                actual_identity = _phase_b_gate_identity(kind, document)
                if actual_kind != expected_document_kinds.get(kind) or actual_identity != ref:
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-CONTRACT-IDENTITY-DRIFT",
                            f"stable contract identity does not match {kind}:{ref}",
                        )
                    )
                expected_hash = str(reference.get("content_hash", "")).removeprefix("sha256:").lower()
                if _document_hash(documents, document_path) != expected_hash:
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-CONTRACT-HASH-DRIFT",
                            f"stable contract content drifted: {kind}:{ref}",
                        )
                    )
                loaded_contracts.setdefault(kind, []).append(
                    (ref, document_path, document, reference)
                )

        required_counts = {
            "task-packet": 1,
            "research-mode": 1,
            "method-resolution": 1,
            "capability-requirement": 1,
        }
        for kind, count in required_counts.items():
            if len(loaded_contracts.get(kind, [])) != count:
                issues.append(
                    ValidationIssue(
                        gate_path,
                        "PHASE-B-GATE-CONTRACT-SET-INCOMPLETE",
                        f"gate requires exactly {count} {kind} reference(s)",
                    )
                )
        if not loaded_contracts.get("mode-action"):
            issues.append(
                ValidationIssue(
                    gate_path,
                    "PHASE-B-GATE-CONTRACT-SET-INCOMPLETE",
                    "gate requires at least one Mode Action reference",
                )
            )

        task_entry = next(iter(loaded_contracts.get("task-packet", [])), None)
        mode_entry = next(iter(loaded_contracts.get("research-mode", [])), None)
        method_entry = next(iter(loaded_contracts.get("method-resolution", [])), None)
        requirement_entry = next(iter(loaded_contracts.get("capability-requirement", [])), None)
        if task_entry and mode_entry and method_entry and requirement_entry:
            task_ref, task_path, _task, _task_reference = task_entry
            mode_ref, _mode_path, _mode, _mode_reference = mode_entry
            method_ref, _method_path, method, _method_reference = method_entry
            requirement_ref, _requirement_path, _requirement, requirement_reference = requirement_entry
            method_task_ref = method.get("task_ref")
            if not isinstance(method_task_ref, Mapping) or (
                f"{method_task_ref.get('task_id')}@r{method_task_ref.get('revision')}" != task_ref
                or str(method_task_ref.get("sha256", "")).removeprefix("sha256:").lower()
                != _document_hash(documents, task_path)
            ):
                issues.append(
                    ValidationIssue(
                        gate_path,
                        "PHASE-B-GATE-TASK-LINEAGE-DRIFT",
                        "Method Resolution does not retain the pinned Task identity and hash",
                    )
                )
            mode_resolution = method.get("mode_resolution")
            selected_modes = (
                mode_resolution.get("selected_mode_refs", [])
                if isinstance(mode_resolution, Mapping)
                else []
            )
            if mode_ref not in selected_modes:
                issues.append(
                    ValidationIssue(
                        gate_path,
                        "PHASE-B-GATE-MODE-LINEAGE-DRIFT",
                        "pinned Research Mode is not selected by the Method Resolution",
                    )
                )
            expected_actions = {
                ref: _document_hash(documents, path)
                for ref, path, _document, _reference in loaded_contracts.get("mode-action", [])
            }
            actual_actions = {
                str(decision.get("action_ref")): str(
                    decision.get("action_content_hash", "")
                ).removeprefix("sha256:").lower()
                for decision in method.get("action_decisions", [])
                if isinstance(decision, Mapping) and isinstance(decision.get("action_ref"), str)
            }
            if actual_actions != expected_actions:
                issues.append(
                    ValidationIssue(
                        gate_path,
                        "PHASE-B-GATE-ACTION-SET-DRIFT",
                        "pinned Mode Action set/hash does not equal the Method Resolution action set",
                    )
                )
            capability_requirements = {
                value
                for decision in method.get("action_decisions", [])
                if isinstance(decision, Mapping)
                for value in decision.get("capability_requirements", [])
                if isinstance(value, str)
            }
            if requirement_ref not in capability_requirements:
                issues.append(
                    ValidationIssue(
                        gate_path,
                        "PHASE-B-GATE-REQUIREMENT-LINEAGE-DRIFT",
                        "pinned Capability Requirement is not required by the Method Resolution",
                    )
                )

            replacement = gate.get("replacement")
            snapshot_refs = (
                replacement.get("snapshot_refs", [])
                if isinstance(replacement, Mapping)
                else []
            )
            snapshots: list[Mapping[str, Any]] = []
            for snapshot_ref in snapshot_refs:
                if not isinstance(snapshot_ref, Mapping):
                    continue
                loaded = _loaded_document_at(documents, snapshot_ref.get("document_path"))
                if loaded is None:
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-SNAPSHOT-MISSING",
                            f"replacement Snapshot is not loaded: {snapshot_ref.get('document_path')}",
                        )
                    )
                    continue
                snapshot_path, snapshot = loaded
                actual_ref = f"{snapshot.get('snapshot_id')}@r{snapshot.get('revision')}"
                expected_hash = str(snapshot_ref.get("content_hash", "")).removeprefix("sha256:").lower()
                if (
                    infer_document_kind(snapshot) != "resolved_capability_snapshot"
                    or snapshot_ref.get("ref") != actual_ref
                ):
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-SNAPSHOT-IDENTITY-DRIFT",
                            f"replacement Snapshot identity drifted: {snapshot_ref.get('ref')}",
                        )
                    )
                if _document_hash(documents, snapshot_path) != expected_hash:
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-SNAPSHOT-HASH-DRIFT",
                            f"replacement Snapshot content drifted: {snapshot_ref.get('ref')}",
                        )
                    )
                snapshot_method = snapshot.get("method_resolution_ref")
                snapshot_requirement = snapshot.get("requirement_ref")
                if not isinstance(snapshot_method, Mapping) or snapshot_method.get("ref") != method_ref:
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-SNAPSHOT-METHOD-DRIFT",
                            "replacement Snapshot does not retain the pinned Method Resolution",
                        )
                    )
                if not isinstance(snapshot_requirement, Mapping) or any(
                    (
                        snapshot_requirement.get("requirement_id") != requirement_ref,
                        snapshot_requirement.get("document_path")
                        != requirement_reference.get("document_path"),
                        str(snapshot_requirement.get("content_hash", "")).removeprefix("sha256:").lower()
                        != str(requirement_reference.get("content_hash", "")).removeprefix("sha256:").lower(),
                    )
                ):
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-SNAPSHOT-REQUIREMENT-DRIFT",
                            "replacement Snapshot does not retain the pinned Capability Requirement",
                        )
                    )
                snapshots.append(snapshot)

            if len(snapshots) == 2:
                snapshot_a, snapshot_b = snapshots
                if (
                    snapshot_a.get("selected_supply_report_ref")
                    == snapshot_b.get("selected_supply_report_ref")
                    or snapshot_a.get("supply_identity") == snapshot_b.get("supply_identity")
                ):
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-SUPPLY-NOT-REPLACED",
                            "Snapshot A and B must bind different exact supplies",
                        )
                    )
                for field in (
                    "task_ref",
                    "supply_required_permissions",
                    "supply_data_egress",
                    "supply_side_effects",
                ):
                    if snapshot_a.get(field) != snapshot_b.get(field):
                        issues.append(
                            ValidationIssue(
                                gate_path,
                                "PHASE-B-GATE-SNAPSHOT-CONTROL-DRIFT",
                                f"supply replacement changed the structural Snapshot {field}",
                            )
                        )
                supply_documents: list[Mapping[str, Any]] = []
                for snapshot in snapshots:
                    supply_ref = snapshot.get("selected_supply_report_ref")
                    loaded_supply = (
                        _loaded_document_at(documents, supply_ref.get("document_path"))
                        if isinstance(supply_ref, Mapping)
                        else None
                    )
                    if loaded_supply is None or infer_document_kind(loaded_supply[1]) != "capability_supply_report":
                        issues.append(
                            ValidationIssue(
                                gate_path,
                                "PHASE-B-GATE-SUPPLY-MISSING",
                                "replacement Snapshot does not resolve to a Supply Report",
                            )
                        )
                        continue
                    supply_documents.append(loaded_supply[1])
                if len(supply_documents) == 2:
                    supply_a, supply_b = supply_documents
                    for field, code in (
                        ("required_permissions", "PHASE-B-GATE-PERMISSION-RELAXED"),
                        ("data_egress_behavior", "PHASE-B-GATE-DATA-EGRESS-RELAXED"),
                        ("side_effects", "PHASE-B-GATE-SIDE-EFFECT-RELAXED"),
                    ):
                        if supply_a.get(field) != supply_b.get(field):
                            issues.append(
                                ValidationIssue(
                                    gate_path,
                                    code,
                                    f"supply replacement changed the frozen {field} boundary fact",
                                )
                            )

        migration_kinds: set[str] = set()
        replay_refs = gate.get("replay_migration_refs")
        if isinstance(replay_refs, list):
            for reference in replay_refs:
                if not isinstance(reference, Mapping):
                    continue
                migration_kind = reference.get("migration_kind")
                loaded = _loaded_document_at(documents, reference.get("document_path"))
                if not isinstance(migration_kind, str) or loaded is None:
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-MIGRATION-MISSING",
                            f"replay migration is not loaded: {reference.get('document_path')}",
                        )
                    )
                    continue
                migration_path, migration = loaded
                actual_kind = infer_document_kind(migration)
                expected_kind = {
                    "research-mode-migration": "research_mode_migration",
                    "skill-lifecycle-migration": "skill_lifecycle_migration",
                }.get(migration_kind)
                actual_ref = f"{migration.get('migration_id')}@{migration.get('migration_version')}"
                if actual_kind != expected_kind or actual_ref != reference.get("ref"):
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-MIGRATION-IDENTITY-DRIFT",
                            f"replay migration identity drifted: {reference.get('ref')}",
                        )
                    )
                expected_hash = str(reference.get("content_hash", "")).removeprefix("sha256:").lower()
                if _document_hash(documents, migration_path) != expected_hash:
                    issues.append(
                        ValidationIssue(
                            gate_path,
                            "PHASE-B-GATE-MIGRATION-HASH-DRIFT",
                            f"replay migration content drifted: {reference.get('ref')}",
                        )
                    )
                migration_kinds.add(migration_kind)
        if migration_kinds != {"research-mode-migration", "skill-lifecycle-migration"}:
            issues.append(
                ValidationIssue(
                    gate_path,
                    "PHASE-B-GATE-MIGRATION-SET-INCOMPLETE",
                    "gate must pin both Research Mode and Skill Lifecycle replay migrations",
                )
            )
    return issues
