"""Deterministic structural checks.

Passing these checks never implies scientific correctness. They only establish
that a document is legible, bounded, and internally referential enough for the
next stage of review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Mapping

from research_workbench.artifacts.integrity import hash_file
from research_workbench.io import load_document
from research_workbench.contracts.common import ContractError, parse_skill_reference
from research_workbench.protocol.migrations import (
    RESEARCH_MODE_MIGRATION_ID,
    RESEARCH_MODE_MIGRATION_VERSION,
    migrate_research_mode_v01_to_v02,
)
from research_workbench.protocol.authority import (
    DecisionAuthorityMatrix,
    evaluate_authority_rule_eligibility,
)
from research_workbench.validation.schemas import SchemaCatalog


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    path: Path
    code: str
    message: str
    severity: Severity = Severity.ERROR


COMMON_REQUIRED = ("schema_version",)
DOCUMENT_REQUIRED: dict[str, tuple[str, ...]] = {
    "project_protocol": (
        "project_id",
        "question_refs",
        "active_modes",
        "claim_ceiling",
        "required_human_gates",
        "budgets",
        "context_policy",
        "data_boundary",
    ),
    "task_packet": (
        "task_id",
        "goal",
        "required_capabilities",
        "required_skills",
        "agent_profile",
        "input_refs",
        "write_scope",
        "required_outputs",
        "permissions",
        "delegation",
        "atomic_boundary",
        "completion_checks",
        "safe_pause_conditions",
        "stop_conditions",
    ),
    "handoff_packet": (
        "task_id",
        "attempt_id",
        "status",
        "skill_lock",
        "result",
        "artifact_refs",
        "limitations",
        "unresolved",
    ),
    "skill_sources": ("registry_kind", "sources"),
    "skill_candidates": ("registry_kind", "candidates"),
    "skill_accepted": ("registry_kind", "entries", "policy"),
    "provider_baselines": ("registry_kind", "providers"),
    "provider_adapters": ("registry_kind", "adapters"),
    "model_pool": ("registry_kind", "pool_id", "selection_policy", "slots"),
}

SCHEMA_KINDS = {
    "capability_requirement",
    "capability_requirement_index",
    "deterministic_check_report",
    "decision_authority_matrix",
    "authority_rule_eligibility",
    "project_protocol",
    "provider_conformance_report",
    "research_mode",
    "research_mode_migration",
    "agent_profile",
    "skill_manifest",
    "skill_assignment",
    "skill_archive_audit",
    "skill_evaluation",
    "task_packet",
    "attempt",
    "handoff_packet",
    "handoff_transfer_audit",
    "handoff_transfer_manifest",
    "main_state",
    "method_resolution",
    "mode_action",
    "mode_action_registry",
    "context_snapshot",
    "execution_receipt",
    "research_object",
}


def infer_document_kind(document: Mapping[str, Any]) -> str | None:
    registry_kind = document.get("registry_kind")
    if isinstance(registry_kind, str):
        return registry_kind
    if "attempt_id" in document and "task_id" in document:
        if "result" in document:
            return "handoff_packet"
        if "started_at" in document and "task_revision" in document:
            return "attempt"
    if "goal" in document and "task_id" in document:
        return "task_packet"
    if "project_id" in document and "active_modes" in document:
        return "project_protocol"
    if "mode_id" in document and "claim_rules" in document:
        return "research_mode"
    if (
        document.get("migration_kind") == "research_mode_migration"
        and "source_mode" in document
        and "target_mode" in document
    ):
        return "research_mode_migration"
    if "matrix_id" in document and "authority_classes" in document and "entries" in document:
        return "decision_authority_matrix"
    if "eligibility_id" in document and "matrix_ref" in document and "result" in document:
        return "authority_rule_eligibility"
    if "action_id" in document and "mode_ref" in document and "claim_effects" in document:
        return "mode_action"
    if "resolution_id" in document and "mode_resolution" in document and "action_decisions" in document:
        return "method_resolution"
    if "requirement_id" in document and "constraints" in document and "unsatisfied_requirement" in document:
        return "capability_requirement"
    if "agent_profile_id" in document and "permission_ceiling" in document:
        return "agent_profile"
    if "skill_id" in document and "capabilities" in document:
        return "skill_manifest"
    if "assignment_id" in document and "skill_lock" in document:
        return "skill_assignment"
    if "checkpoint_id" in document and "project_protocol_ref" in document:
        return "main_state"
    if "snapshot_id" in document and "assessment" in document and "metrics" in document:
        return "context_snapshot"
    if "receipt_id" in document and "execution_kind" in document and "attempt_ref" in document:
        return "execution_receipt"
    if "audit_id" in document and "manifest_ref" in document and "mappings" in document:
        return "handoff_transfer_audit"
    if "manifest_id" in document and "source_artifact_refs" in document and "items" in document:
        return "handoff_transfer_manifest"
    if "report_id" in document and "adapter_id" in document and "checks" in document:
        return "provider_conformance_report"
    if "report_id" in document and "checker" in document and "checks" in document:
        return "deterministic_check_report"
    if "report_id" in document and "source_id" in document and "archive_signals" in document:
        return "skill_archive_audit"
    if "evaluation_id" in document and "candidate_id" in document and "cases" in document:
        return "skill_evaluation"
    if "object_type" in document and "object_id" in document:
        return "research_object"
    return None


def _require_fields(
    path: Path, document: Mapping[str, Any], fields: Iterable[str]
) -> list[ValidationIssue]:
    return [
        ValidationIssue(path, "FIELD-MISSING", f"required field is missing: {field}")
        for field in fields
        if field not in document
    ]


def _validate_hashes(path: Path, value: Any, pointer: str = "$") -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            nested_pointer = f"{pointer}.{key}"
            if key in {"sha256", "content_hash"} and isinstance(nested, str):
                normalized = nested.removeprefix("sha256:")
                if "REPLACE_WITH" in nested:
                    issues.append(
                        ValidationIssue(
                            path,
                            "HASH-PLACEHOLDER",
                            f"placeholder hash at {nested_pointer}",
                            Severity.WARNING,
                        )
                    )
                elif not SHA256_RE.fullmatch(normalized):
                    issues.append(
                        ValidationIssue(
                            path,
                            "HASH-INVALID",
                            f"expected 64 hexadecimal characters at {nested_pointer}",
                        )
                    )
            issues.extend(_validate_hashes(path, nested, nested_pointer))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            issues.extend(_validate_hashes(path, nested, f"{pointer}[{index}]"))
    return issues


def _validate_registry(
    path: Path, document: Mapping[str, Any], kind: str, source_ids: set[str]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if kind == "skill_sources":
        seen: set[str] = set()
        for index, source in enumerate(document.get("sources", [])):
            if not isinstance(source, Mapping):
                issues.append(ValidationIssue(path, "SOURCE-INVALID", f"sources[{index}] is not an object"))
                continue
            issues.extend(_require_fields(path, source, ("source_id", "origin", "locator", "revision", "license_status", "trust")))
            source_id = source.get("source_id")
            if isinstance(source_id, str):
                if source_id in seen:
                    issues.append(ValidationIssue(path, "SOURCE-DUPLICATE", f"duplicate source_id: {source_id}"))
                seen.add(source_id)
    elif kind == "skill_candidates":
        allowed = {"discovered", "triage", "reference", "quarantine", "rejected", "trial", "accepted"}
        seen = set()
        for index, candidate in enumerate(document.get("candidates", [])):
            if not isinstance(candidate, Mapping):
                issues.append(ValidationIssue(path, "CANDIDATE-INVALID", f"candidates[{index}] is not an object"))
                continue
            issues.extend(
                _require_fields(
                    path,
                    candidate,
                    (
                        "candidate_id",
                        "source_id",
                        "source_path",
                        "status",
                        "kind",
                        "capabilities",
                        "applicable_modes",
                        "context_cost",
                        "risk_flags",
                        "decision",
                    ),
                )
            )
            if candidate.get("status") not in allowed:
                issues.append(ValidationIssue(path, "CANDIDATE-STATUS", f"invalid status at candidates[{index}]"))
            candidate_id = candidate.get("candidate_id")
            if isinstance(candidate_id, str):
                if candidate_id in seen:
                    issues.append(ValidationIssue(path, "CANDIDATE-DUPLICATE", f"duplicate candidate_id: {candidate_id}"))
                seen.add(candidate_id)
            source_id = candidate.get("source_id")
            if isinstance(source_id, str) and source_id not in source_ids:
                issues.append(ValidationIssue(path, "SOURCE-UNKNOWN", f"candidate references unknown source: {source_id}"))
            if candidate.get("status") == "accepted" and "content_hash" not in candidate:
                issues.append(ValidationIssue(path, "CANDIDATE-UNPINNED", f"accepted candidate lacks content_hash: {candidate_id}"))
    elif kind == "skill_accepted":
        active_ids: set[str] = set()
        seen = set()
        for index, entry in enumerate(document.get("entries", [])):
            if not isinstance(entry, Mapping):
                issues.append(ValidationIssue(path, "ACCEPTED-INVALID", f"entries[{index}] is not an object"))
                continue
            issues.extend(
                _require_fields(
                    path,
                    entry,
                    (
                        "skill_id", "version", "status", "manifest_path", "source_path",
                        "content_hash", "license_status", "admission",
                        "package_hash",
                        "lifecycle",
                    ),
                )
            )
            key = (entry.get("skill_id"), entry.get("version"))
            if key in seen:
                issues.append(ValidationIssue(path, "ACCEPTED-DUPLICATE", f"duplicate accepted Skill: {key}"))
            seen.add(key)
            if entry.get("status") != "accepted":
                issues.append(ValidationIssue(path, "ACCEPTED-STATUS", f"entries[{index}] is not accepted"))
            lifecycle = entry.get("lifecycle")
            if lifecycle not in {"active", "legacy", "deprecated"}:
                issues.append(
                    ValidationIssue(path, "ACCEPTED-LIFECYCLE", f"invalid lifecycle at entries[{index}]")
                )
            skill_id = entry.get("skill_id")
            if lifecycle == "active" and isinstance(skill_id, str):
                if skill_id in active_ids:
                    issues.append(
                        ValidationIssue(
                            path,
                            "ACCEPTED-ACTIVE-DUPLICATE",
                            f"multiple active versions for Skill: {skill_id}",
                        )
                    )
                active_ids.add(skill_id)
    elif kind == "provider_baselines":
        for provider in document.get("providers", []):
            if isinstance(provider, Mapping):
                issues.extend(
                    _require_fields(
                        path,
                        provider,
                        ("provider", "api_surface", "adapter_status", "capabilities", "semantic_notes", "sources"),
                    )
                )
    elif kind == "provider_adapters":
        seen = set()
        for index, adapter in enumerate(document.get("adapters", [])):
            if not isinstance(adapter, Mapping):
                issues.append(
                    ValidationIssue(path, "PROVIDER-ADAPTER-INVALID", f"adapters[{index}] is not an object")
                )
                continue
            issues.extend(
                _require_fields(
                    path,
                    adapter,
                    (
                        "adapter_id",
                        "provider",
                        "enabled",
                        "base_url",
                        "credential_env",
                        "model_env",
                        "capabilities",
                        "live_conformance",
                    ),
                )
            )
            adapter_id = adapter.get("adapter_id")
            if isinstance(adapter_id, str):
                if adapter_id in seen:
                    issues.append(
                        ValidationIssue(path, "PROVIDER-ADAPTER-DUPLICATE", f"duplicate adapter_id: {adapter_id}")
                    )
                seen.add(adapter_id)
    elif kind == "model_pool":
        # Import locally to keep the generic validation module independent of
        # adapter initialization at import time.
        from research_workbench.adapters.models.pool import ModelPool

        try:
            ModelPool.from_mapping(document)
        except ValueError as exc:
            issues.append(ValidationIssue(path, "MODEL-POOL-INVALID", str(exc)))
    return issues


def _validate_task(path: Path, document: Mapping[str, Any], kind: str) -> list[ValidationIssue]:
    if kind != "task_packet":
        return []
    issues: list[ValidationIssue] = []
    required = []
    forbidden = []
    for field, destination in (("required_skills", required), ("forbidden_skills", forbidden)):
        for index, raw_reference in enumerate(document.get(field, [])):
            if not isinstance(raw_reference, str):
                continue
            try:
                destination.append(parse_skill_reference(raw_reference, f"{field}[{index}]"))
            except ContractError as exc:
                issues.append(ValidationIssue(path, "SKILL-SELECTOR-INVALID", str(exc)))
    overlap = sorted(
        required_reference.identifier
        for required_reference in required
        for forbidden_reference in forbidden
        if required_reference.skill_id == forbidden_reference.skill_id
        and (
            required_reference.version is None
            or forbidden_reference.version is None
            or required_reference.version == forbidden_reference.version
        )
    )
    if overlap:
        issues.append(ValidationIssue(path, "SKILL-CONFLICT", f"skills are both required and forbidden: {', '.join(overlap)}"))
    for scope in document.get("write_scope", []):
        if isinstance(scope, str) and (PureWindowsPath(scope).is_absolute() or PurePosixPath(scope).is_absolute()):
            issues.append(ValidationIssue(path, "SCOPE-ABSOLUTE", f"write_scope must be repository-relative: {scope}"))
    return issues


def _matches_repository_path(path: Path, repository_relative: str) -> bool:
    normalized_path = path.as_posix()
    normalized_relative = PurePosixPath(repository_relative).as_posix()
    return normalized_path == normalized_relative or normalized_path.endswith(f"/{normalized_relative}")


def _validate_mode_action_registry(documents: Mapping[Path, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    registries = [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping) and document.get("registry_kind") == "mode_action_registry"
    ]
    if not registries:
        return issues

    modes = {
        f"{document.get('mode_id')}@{document.get('version')}": document
        for document in documents.values()
        if isinstance(document, Mapping)
        and "mode_id" in document
        and "claim_rules" in document
    }
    action_documents: dict[tuple[str, str], tuple[Path, Mapping[str, Any]]] = {}
    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "mode_action":
            continue
        key = (str(document.get("action_id")), str(document.get("version")))
        if key in action_documents:
            issues.append(
                ValidationIssue(path, "MODE-ACTION-DUPLICATE", f"duplicate Mode Action document: {key}")
            )
        action_documents[key] = (path, document)
        mode_ref = document.get("mode_ref")
        if isinstance(mode_ref, str) and mode_ref not in modes:
            issues.append(
                ValidationIssue(path, "MODE-ACTION-MODE-MISSING", f"unknown Research Mode: {mode_ref}")
            )
        claim_effects = document.get("claim_effects")
        if isinstance(claim_effects, Mapping):
            may_support = set(claim_effects.get("may_support", []))
            cannot_alone_support = set(claim_effects.get("cannot_alone_support", []))
            overlap = sorted(may_support & cannot_alone_support)
            if overlap:
                issues.append(
                    ValidationIssue(
                        path,
                        "MODE-ACTION-CLAIM-EFFECT-CONFLICT",
                        "claim strengths cannot be both may_support and cannot_alone_support: "
                        + ", ".join(overlap),
                    )
                )
            if isinstance(mode_ref, str) and mode_ref in modes:
                claim_rules = modes[mode_ref].get("claim_rules", {})
                allowed = set(claim_rules.get("allows", [])) if isinstance(claim_rules, Mapping) else set()
                outside_mode = sorted(may_support - allowed - {"unresolved", "withdrawn"})
                if outside_mode:
                    issues.append(
                        ValidationIssue(
                            path,
                            "MODE-ACTION-CLAIM-NOT-ALLOWED",
                            f"may_support exceeds {mode_ref} claim rules: {', '.join(outside_mode)}",
                        )
                    )

    indexed: set[tuple[str, str]] = set()
    for registry_path, registry in registries:
        for index, entry in enumerate(registry.get("entries", [])):
            if not isinstance(entry, Mapping):
                continue
            key = (str(entry.get("action_id")), str(entry.get("version")))
            if key in indexed:
                issues.append(
                    ValidationIssue(
                        registry_path,
                        "MODE-ACTION-REGISTRY-DUPLICATE",
                        f"duplicate registry entry at entries[{index}]: {key}",
                    )
                )
                continue
            indexed.add(key)
            registered = action_documents.get(key)
            if registered is None:
                issues.append(
                    ValidationIssue(
                        registry_path,
                        "MODE-ACTION-DOCUMENT-MISSING",
                        f"registry entry has no loaded Action document: {key}",
                    )
                )
                continue
            document_path, action = registered
            expected_path = entry.get("document_path")
            if not isinstance(expected_path, str) or not _matches_repository_path(document_path, expected_path):
                issues.append(
                    ValidationIssue(
                        registry_path,
                        "MODE-ACTION-PATH-MISMATCH",
                        f"registry path does not match Action document for {key}: {expected_path}",
                    )
                )
            if entry.get("mode_ref") != action.get("mode_ref"):
                issues.append(
                    ValidationIssue(
                        registry_path,
                        "MODE-ACTION-MODE-MISMATCH",
                        f"registry mode_ref disagrees with Action document for {key}",
                    )
                )
            expected_hash = entry.get("content_hash")
            if isinstance(expected_hash, str):
                expected_hash = expected_hash.removeprefix("sha256:").lower()
                if hash_file(document_path) != expected_hash:
                    issues.append(
                        ValidationIssue(
                            registry_path,
                            "MODE-ACTION-HASH-MISMATCH",
                            f"content hash does not match Action document for {key}",
                        )
                    )

    for key, (path, _) in action_documents.items():
        if key not in indexed:
            issues.append(
                ValidationIssue(path, "MODE-ACTION-UNINDEXED", f"Action document is not in the registry: {key}")
            )
    return issues


def _capability_requirement_indices(
    documents: Mapping[Path, Any],
) -> list[tuple[Path, Mapping[str, Any]]]:
    return [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping)
        and document.get("registry_kind") == "capability_requirement_index"
    ]


def _capability_requirement_entries(documents: Mapping[Path, Any]) -> dict[str, Mapping[str, Any]]:
    indices = _capability_requirement_indices(documents)
    if len(indices) != 1:
        return {}
    entries: dict[str, Mapping[str, Any]] = {}
    for entry in indices[0][1].get("entries", []):
        if not isinstance(entry, Mapping) or not isinstance(entry.get("requirement_id"), str):
            continue
        entries[str(entry["requirement_id"])] = entry
    return entries


def _validate_capability_requirement_set(
    documents: Mapping[Path, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    indices = _capability_requirement_indices(documents)
    requirement_documents = [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping) and infer_document_kind(document) == "capability_requirement"
    ]
    method_references = [
        value
        for document in documents.values()
        if isinstance(document, Mapping) and infer_document_kind(document) == "method_resolution"
        for decision in document.get("action_decisions", [])
        if isinstance(decision, Mapping)
        for value in decision.get("capability_requirements", [])
        if isinstance(value, str)
    ]
    if not indices:
        if requirement_documents or method_references:
            anchor = requirement_documents[0][0] if requirement_documents else Path("capability-requirements")
            issues.append(
                ValidationIssue(
                    anchor,
                    "CAPABILITY-REQUIREMENT-INDEX-MISSING",
                    "Capability Requirement documents and Method references require one closed integrity index",
                )
            )
        return issues
    if len(indices) > 1:
        for path, _ in indices[1:]:
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-REQUIREMENT-INDEX-DUPLICATE",
                    "only one Capability Requirement integrity index may be loaded",
                )
            )
        return issues

    index_path, index = indices[0]
    indexed: dict[str, tuple[str, Mapping[str, Any]]] = {}
    seen_paths: set[str] = set()
    for position, entry in enumerate(index.get("entries", [])):
        if not isinstance(entry, Mapping):
            continue
        requirement_id = entry.get("requirement_id")
        document_path = entry.get("document_path")
        if not isinstance(requirement_id, str) or not isinstance(document_path, str):
            continue
        if requirement_id in indexed:
            issues.append(
                ValidationIssue(
                    index_path,
                    "CAPABILITY-REQUIREMENT-IDENTITY-DUPLICATE",
                    f"duplicate Requirement identity at entries[{position}]: {requirement_id}",
                )
            )
            continue
        if document_path in seen_paths:
            issues.append(
                ValidationIssue(
                    index_path,
                    "CAPABILITY-REQUIREMENT-PATH-DUPLICATE",
                    f"duplicate Requirement document path at entries[{position}]: {document_path}",
                )
            )
            continue
        indexed[requirement_id] = (document_path, entry)
        seen_paths.add(document_path)

        loaded = _loaded_document_at(documents, document_path)
        if loaded is None:
            issues.append(
                ValidationIssue(
                    index_path,
                    "CAPABILITY-REQUIREMENT-DOCUMENT-MISSING",
                    f"indexed Requirement document is not loaded: {document_path}",
                )
            )
            continue
        loaded_path, requirement = loaded
        if infer_document_kind(requirement) != "capability_requirement":
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "CAPABILITY-REQUIREMENT-DOCUMENT-KIND",
                    f"indexed document is not a Capability Requirement: {document_path}",
                )
            )
            continue
        if requirement.get("requirement_id") != requirement_id:
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "CAPABILITY-REQUIREMENT-IDENTITY-MISMATCH",
                    f"index and document identities disagree: {requirement_id}",
                )
            )
        expected_hash = entry.get("content_hash")
        if isinstance(expected_hash, str) and loaded_path.is_file():
            if hash_file(loaded_path) != expected_hash.removeprefix("sha256:").lower():
                issues.append(
                    ValidationIssue(
                        index_path,
                        "CAPABILITY-REQUIREMENT-HASH-MISMATCH",
                        f"content hash does not match Requirement document: {requirement_id}",
                    )
                )

    for path, requirement in requirement_documents:
        requirement_id = requirement.get("requirement_id")
        indexed_entry = indexed.get(str(requirement_id))
        if indexed_entry is None:
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-REQUIREMENT-UNINDEXED",
                    f"Requirement document is not in the integrity index: {requirement_id}",
                )
            )
        elif not _matches_repository_path(path, indexed_entry[0]):
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-REQUIREMENT-PATH-MISMATCH",
                    f"Requirement document path disagrees with the index: {requirement_id}",
                )
            )
    return issues


def _validate_method_resolutions(documents: Mapping[Path, Any]) -> list[ValidationIssue]:
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
                if recorded_hash != hash_file(task_path):
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


def _loaded_document_at(
    documents: Mapping[Path, Any], repository_relative: object
) -> tuple[Path, Mapping[str, Any]] | None:
    if not isinstance(repository_relative, str):
        return None
    for path, document in documents.items():
        if isinstance(document, Mapping) and _matches_repository_path(path, repository_relative):
            return path, document
    return None


def _validate_research_mode_migrations(
    documents: Mapping[Path, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    action_entries: dict[str, Mapping[str, Any]] = {}
    action_registry: Mapping[str, Any] | None = None
    for document in documents.values():
        if not isinstance(document, Mapping) or document.get("registry_kind") != "mode_action_registry":
            continue
        action_registry = document
        for entry in document.get("entries", []):
            if isinstance(entry, Mapping):
                action_entries[f"{entry.get('action_id')}@{entry.get('version')}"] = entry

    seen_migrations: set[tuple[str, str]] = set()
    for path, migration in documents.items():
        if not isinstance(migration, Mapping) or infer_document_kind(migration) != "research_mode_migration":
            continue
        identity = (
            str(migration.get("migration_id")),
            str(migration.get("migration_version")),
        )
        if identity in seen_migrations:
            issues.append(
                ValidationIssue(path, "MODE-MIGRATION-DUPLICATE", f"duplicate migration identity: {identity}")
            )
        seen_migrations.add(identity)

        implementation = migration.get("implementation")
        if (
            not isinstance(implementation, Mapping)
            or implementation.get("id") != RESEARCH_MODE_MIGRATION_ID
            or implementation.get("version") != RESEARCH_MODE_MIGRATION_VERSION
            or migration.get("migration_version") != RESEARCH_MODE_MIGRATION_VERSION
        ):
            issues.append(
                ValidationIssue(
                    path,
                    "MODE-MIGRATION-IMPLEMENTATION-MISMATCH",
                    "migration and implementation versions must match the supported migration seam",
                )
            )

        loaded_modes: dict[str, tuple[Path, Mapping[str, Any]]] = {}
        for side in ("source_mode", "target_mode"):
            reference = migration.get(side)
            if not isinstance(reference, Mapping):
                continue
            loaded = _loaded_document_at(documents, reference.get("document_path"))
            if loaded is None:
                issues.append(
                    ValidationIssue(path, "MODE-MIGRATION-DOCUMENT-MISSING", f"{side} document is not loaded")
                )
                continue
            document_path, mode = loaded
            loaded_modes[side] = loaded
            actual_ref = f"{mode.get('mode_id')}@{mode.get('version')}"
            if reference.get("ref") != actual_ref:
                issues.append(
                    ValidationIssue(path, "MODE-MIGRATION-REF-MISMATCH", f"{side}.ref does not match its document")
                )
            expected_hash = reference.get("content_hash")
            if isinstance(expected_hash, str) and hash_file(document_path) != expected_hash.removeprefix("sha256:").lower():
                issues.append(
                    ValidationIssue(path, "MODE-MIGRATION-HASH-MISMATCH", f"{side}.content_hash does not match its document")
                )

        source_loaded = loaded_modes.get("source_mode")
        target_loaded = loaded_modes.get("target_mode")
        if source_loaded is None or target_loaded is None:
            continue
        _, source_mode = source_loaded
        _, target_mode = target_loaded
        if source_mode.get("mode_id") != target_mode.get("mode_id"):
            issues.append(
                ValidationIssue(path, "MODE-MIGRATION-ID-MISMATCH", "source and target must retain the same mode_id")
            )
        if source_mode.get("version") != "0.1.0" or target_mode.get("version") != "0.2.0":
            issues.append(
                ValidationIssue(path, "MODE-MIGRATION-VERSION-MISMATCH", "migration must be v0.1.0 to v0.2.0")
            )

        if action_registry is not None:
            try:
                recorded_target_refs = [
                    target.get("ref")
                    for item in migration.get("action_migrations", [])
                    if isinstance(item, Mapping)
                    for target in [item.get("target")]
                    if isinstance(target, Mapping) and isinstance(target.get("ref"), str)
                ]
                expected_target = migrate_research_mode_v01_to_v02(
                    source_mode, recorded_target_refs, action_registry
                )
            except ContractError as error:
                issues.append(
                    ValidationIssue(
                        path,
                        "MODE-MIGRATION-DETERMINISM-BLOCKED",
                        f"supported migration could not resolve: {error}",
                    )
                )
            else:
                if dict(target_mode) != expected_target:
                    issues.append(
                        ValidationIssue(
                            path,
                            "MODE-MIGRATION-TARGET-MISMATCH",
                            "target Mode does not match the supported deterministic migration",
                        )
                    )

        expected_preserved = set(source_mode) - {
            "version",
            "recommended_skill_capabilities",
        }
        if set(migration.get("preserved_fields", [])) != expected_preserved:
            issues.append(
                ValidationIssue(
                    path,
                    "MODE-MIGRATION-FIELD-DECLARATION-MISMATCH",
                    "preserved_fields must exactly declare the supported migration",
                )
            )
        if set(migration.get("removed_fields", [])) != {
            "recommended_skill_capabilities"
        } or set(migration.get("added_fields", [])) != {"action_refs"}:
            issues.append(
                ValidationIssue(
                    path,
                    "MODE-MIGRATION-FIELD-DECLARATION-MISMATCH",
                    "removed_fields and added_fields must exactly declare the supported migration",
                )
            )

        for field in migration.get("preserved_fields", []):
            if isinstance(field, str) and source_mode.get(field) != target_mode.get(field):
                issues.append(
                    ValidationIssue(path, "MODE-MIGRATION-PRESERVATION-MISMATCH", f"field was not preserved: {field}")
                )
        for field in migration.get("removed_fields", []):
            if isinstance(field, str) and (field not in source_mode or field in target_mode):
                issues.append(
                    ValidationIssue(path, "MODE-MIGRATION-REMOVAL-MISMATCH", f"field was not removed exactly: {field}")
                )
        for field in migration.get("added_fields", []):
            if isinstance(field, str) and (field in source_mode or field not in target_mode):
                issues.append(
                    ValidationIssue(path, "MODE-MIGRATION-ADDITION-MISMATCH", f"field was not added exactly: {field}")
                )

        source_mode_ref = f"{source_mode.get('mode_id')}@{source_mode.get('version')}"
        target_mode_ref = f"{target_mode.get('mode_id')}@{target_mode.get('version')}"
        source_action_refs: set[str] = set()
        target_action_refs: set[str] = set()
        for index, action_migration in enumerate(migration.get("action_migrations", [])):
            if not isinstance(action_migration, Mapping):
                continue
            side_values: dict[str, tuple[str, Mapping[str, Any]]] = {}
            for side, expected_mode_ref in (("source", source_mode_ref), ("target", target_mode_ref)):
                reference = action_migration.get(side)
                if not isinstance(reference, Mapping):
                    continue
                action_ref = reference.get("ref")
                entry = action_entries.get(action_ref) if isinstance(action_ref, str) else None
                if entry is None:
                    issues.append(
                        ValidationIssue(
                            path,
                            "MODE-MIGRATION-ACTION-MISSING",
                            f"action_migrations[{index}].{side} is not in the Action Registry",
                        )
                    )
                    continue
                side_values[side] = (action_ref, entry)
                if entry.get("mode_ref") != expected_mode_ref:
                    issues.append(
                        ValidationIssue(
                            path,
                            "MODE-MIGRATION-ACTION-MODE-MISMATCH",
                            f"action_migrations[{index}].{side} belongs to the wrong Mode revision",
                        )
                    )
                if reference.get("document_path") != entry.get("document_path") or reference.get("content_hash") != entry.get("content_hash"):
                    issues.append(
                        ValidationIssue(
                            path,
                            "MODE-MIGRATION-ACTION-PIN-MISMATCH",
                            f"action_migrations[{index}].{side} path/hash differs from the Registry",
                        )
                    )
            if "source" in side_values and "target" in side_values:
                source_ref, source_entry = side_values["source"]
                target_ref, target_entry = side_values["target"]
                if source_ref in source_action_refs or target_ref in target_action_refs:
                    issues.append(
                        ValidationIssue(
                            path,
                            "MODE-MIGRATION-ACTION-DUPLICATE",
                            f"action_migrations[{index}] repeats a source or target Action",
                        )
                    )
                source_action_refs.add(source_ref)
                target_action_refs.add(target_ref)
                if source_entry.get("action_id") != target_entry.get("action_id") or source_ref == target_ref:
                    issues.append(
                        ValidationIssue(
                            path,
                            "MODE-MIGRATION-ACTION-LINEAGE-MISMATCH",
                            f"action_migrations[{index}] must retain action_id and publish a new version",
                        )
                    )

        declared_target_refs = {
            value for value in target_mode.get("action_refs", []) if isinstance(value, str)
        }
        if declared_target_refs != target_action_refs:
            issues.append(
                ValidationIssue(
                    path,
                    "MODE-MIGRATION-ACTION-CLOSURE",
                    "target Mode action_refs must exactly match migration targets",
                )
            )
    return issues


def _validate_decision_authority(
    documents: Mapping[Path, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    matrices: dict[str, tuple[Path, Mapping[str, Any]]] = {}
    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "decision_authority_matrix":
            continue
        try:
            matrix = DecisionAuthorityMatrix.from_mapping(document)
        except ContractError as error:
            issues.append(
                ValidationIssue(
                    path,
                    "DECISION-AUTHORITY-MATRIX-INVALID",
                    str(error),
                )
            )
            continue
        if matrix.reference in matrices:
            issues.append(
                ValidationIssue(
                    path,
                    "DECISION-AUTHORITY-MATRIX-DUPLICATE",
                    f"duplicate Matrix identity: {matrix.reference}",
                )
            )
        matrices[matrix.reference] = (path, document)

    seen_eligibility_records: set[str] = set()
    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "authority_rule_eligibility":
            continue
        eligibility_id = str(document.get("eligibility_id"))
        if eligibility_id in seen_eligibility_records:
            issues.append(
                ValidationIssue(
                    path,
                    "AUTHORITY-RULE-ELIGIBILITY-DUPLICATE",
                    f"duplicate eligibility_id: {eligibility_id}",
                )
            )
        seen_eligibility_records.add(eligibility_id)
        matrix_ref = document.get("matrix_ref")
        if not isinstance(matrix_ref, Mapping):
            continue
        loaded = _loaded_document_at(documents, matrix_ref.get("document_path"))
        if loaded is None:
            issues.append(
                ValidationIssue(
                    path,
                    "DECISION-AUTHORITY-MATRIX-MISSING",
                    "eligibility Matrix document is not loaded",
                )
            )
            continue
        matrix_path, matrix_document = loaded
        if matrices.get(str(matrix_ref.get("ref"))) != (matrix_path, matrix_document):
            issues.append(
                ValidationIssue(
                    path,
                    "DECISION-AUTHORITY-MATRIX-REF-MISMATCH",
                    "eligibility Matrix ref does not match the loaded Matrix",
                )
            )
            continue
        try:
            expected = evaluate_authority_rule_eligibility(
                document,
                matrix_document,
                matrix_content_hash=hash_file(matrix_path),
            )
        except ContractError as error:
            issues.append(
                ValidationIssue(
                    path,
                    "AUTHORITY-RULE-ELIGIBILITY-INVALID",
                    str(error),
                )
            )
            continue
        if document.get("result") != expected:
            issues.append(
                ValidationIssue(
                    path,
                    "DECISION-AUTHORITY-RESULT-MISMATCH",
                    "recorded result does not match deterministic rule-eligibility evaluation",
                )
            )
    return issues


def validate_documents(documents: Mapping[Path, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    source_ids: set[str] = set()
    schema_catalog = SchemaCatalog()

    for path, document in documents.items():
        if isinstance(document, Mapping) and document.get("registry_kind") == "skill_sources":
            for source in document.get("sources", []):
                if isinstance(source, Mapping) and isinstance(source.get("source_id"), str):
                    source_ids.add(source["source_id"])

    for path, document in documents.items():
        if not isinstance(document, Mapping):
            issues.append(ValidationIssue(path, "DOCUMENT-INVALID", "top-level value must be an object"))
            continue
        kind = infer_document_kind(document)
        if kind is None or (kind not in DOCUMENT_REQUIRED and kind not in SCHEMA_KINDS):
            issues.append(ValidationIssue(path, "DOCUMENT-UNKNOWN", "document kind cannot be inferred"))
            continue
        if kind in SCHEMA_KINDS:
            for schema_error in schema_catalog.validate(kind, document):
                issues.append(
                    ValidationIssue(
                        path,
                        "SCHEMA-INVALID",
                        f"{schema_error.pointer}: {schema_error.message}",
                    )
                )
        if kind in DOCUMENT_REQUIRED:
            issues.extend(_require_fields(path, document, COMMON_REQUIRED + DOCUMENT_REQUIRED[kind]))
        issues.extend(_validate_hashes(path, document))
        issues.extend(_validate_registry(path, document, kind, source_ids))
        issues.extend(_validate_task(path, document, kind))
    issues.extend(_validate_mode_action_registry(documents))
    issues.extend(_validate_capability_requirement_set(documents))
    issues.extend(_validate_method_resolutions(documents))
    issues.extend(_validate_research_mode_migrations(documents))
    issues.extend(_validate_decision_authority(documents))
    return issues


def load_and_validate(paths: Iterable[Path]) -> tuple[dict[Path, Any], list[ValidationIssue]]:
    documents: dict[Path, Any] = {}
    issues: list[ValidationIssue] = []
    for path in paths:
        try:
            documents[path] = load_document(path)
        except Exception as exc:  # parse errors are validation results at the CLI boundary
            issues.append(ValidationIssue(path, "PARSE-ERROR", str(exc)))
    issues.extend(validate_documents(documents))
    return documents, issues
