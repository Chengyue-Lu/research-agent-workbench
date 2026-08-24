"""Deterministic structural checks.

Passing these checks never implies scientific correctness. They only establish
that a document is legible, bounded, and internally referential enough for the
next stage of review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Mapping

from research_workbench.artifacts.integrity import hash_bytes, hash_file
from research_workbench.capability.requirements import CapabilityRequirement
from research_workbench.capability.supply import (
    CapabilitySupplyReport,
    assess_supply,
    resolve_status,
)
from research_workbench.capability.lifecycle import SkillLifecycleRecord
from research_workbench.io import load_document_bytes
from research_workbench.contracts.common import (
    ContractError,
    parse_skill_reference,
)
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


class LoadedDocuments(dict[Path, Any]):
    """Parsed documents bound to SHA-256 digests from the same byte reads."""

    def __init__(self) -> None:
        super().__init__()
        self._sha256_by_path: dict[Path, str] = {}

    def add(self, path: Path, document: Any, *, sha256: str) -> None:
        self[path] = document
        self._sha256_by_path[path] = sha256

    def sha256_for(self, path: Path) -> str | None:
        return self._sha256_by_path.get(path)


def _document_hash(documents: Mapping[Path, Any], path: Path) -> str:
    """Return the digest of the bytes that produced the loaded mapping.

    ``load_and_validate`` always supplies ``LoadedDocuments`` so reference and
    identity checks cannot re-read a path after parsing. Plain mappings remain
    supported for in-memory unit tests and existing direct callers.
    """

    if isinstance(documents, LoadedDocuments):
        return documents.sha256_for(path) or ""
    return hash_file(path)


def _document_has_loaded_bytes(documents: Mapping[Path, Any], path: Path) -> bool:
    if isinstance(documents, LoadedDocuments):
        return documents.sha256_for(path) is not None
    return path.is_file()


def _aware_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


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
    "capability_conformance_evidence",
    "capability_resolution",
    "capability_supply_report",
    "phase_b_evolution_gate",
    "protocol_profile",
    "protocol_profile_index",
    "skill_need",
    "skill_need_index",
    "skill_lifecycle_index",
    "skill_lifecycle_migration",
    "skill_lifecycle_record",
    "deterministic_check_report",
    "decision_authority_matrix",
    "authority_rule_eligibility",
    "project_protocol",
    "provider_conformance_report",
    "research_mode",
    "research_mode_migration",
    "resolved_capability_snapshot",
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
    if document.get("evidence_kind") in {
        "deterministic-fixture",
        "local-conformance",
        "live-conformance",
    }:
        return "capability_conformance_evidence"
    if "need_id" in document and "semantic_gap" in document and "evaluation_requirements" in document:
        return "skill_need"
    if "lifecycle_id" in document and "skill_ref" in document and "runtime_eligibility" in document:
        return "skill_lifecycle_record"
    if "migration_id" in document and "source_registry_path" in document and "target_index_path" in document:
        return "skill_lifecycle_migration"
    if "profile_id" in document and "method_standard" in document and "method_obligations" in document:
        return "protocol_profile"
    if "report_id" in document and "supply_identity" in document and "availability" in document:
        return "capability_supply_report"
    if "snapshot_id" in document and "selected_supply_report_ref" in document:
        return "resolved_capability_snapshot"
    if "resolution_id" in document and "requirement_ref" in document and "comparisons" in document:
        return "capability_resolution"
    if document.get("scope") == "phase-b-evolution" and "gate_id" in document:
        return "phase_b_evolution_gate"
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
                if _document_hash(documents, document_path) != expected_hash:
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
        if isinstance(expected_hash, str) and _document_has_loaded_bytes(documents, loaded_path):
            if _document_hash(documents, loaded_path) != expected_hash.removeprefix("sha256:").lower():
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


def _skill_need_indices(
    documents: Mapping[Path, Any],
) -> list[tuple[Path, Mapping[str, Any]]]:
    return [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping) and document.get("registry_kind") == "skill_need_index"
    ]


def _skill_need_entries(documents: Mapping[Path, Any]) -> dict[str, Mapping[str, Any]]:
    indices = _skill_need_indices(documents)
    if len(indices) != 1:
        return {}
    entries: dict[str, Mapping[str, Any]] = {}
    for entry in indices[0][1].get("entries", []):
        if not isinstance(entry, Mapping) or not isinstance(entry.get("need_ref"), str):
            continue
        entries[str(entry["need_ref"])] = entry
    return entries


def _validate_skill_need_set(documents: Mapping[Path, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    indices = _skill_need_indices(documents)
    need_documents = [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping) and infer_document_kind(document) == "skill_need"
    ]
    method_references = [
        value
        for document in documents.values()
        if isinstance(document, Mapping) and infer_document_kind(document) == "method_resolution"
        for decision in document.get("action_decisions", [])
        if isinstance(decision, Mapping)
        for value in decision.get("skill_need_refs", [])
        if isinstance(value, str)
    ]
    if not indices:
        if need_documents or method_references:
            anchor = need_documents[0][0] if need_documents else Path("skill-needs")
            issues.append(
                ValidationIssue(
                    anchor,
                    "SKILL-NEED-INDEX-MISSING",
                    "Skill Need documents and Method references require one closed integrity index",
                )
            )
        return issues
    if len(indices) > 1:
        for path, _ in indices[1:]:
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-NEED-INDEX-DUPLICATE",
                    "only one Skill Need integrity index may be loaded",
                )
            )
        return issues

    index_path, index = indices[0]
    modes = {
        f"{document.get('mode_id')}@{document.get('version')}"
        for document in documents.values()
        if isinstance(document, Mapping) and "mode_id" in document and "claim_rules" in document
    }
    action_entries: dict[str, Mapping[str, Any]] = {}
    for document in documents.values():
        if not isinstance(document, Mapping) or document.get("registry_kind") != "mode_action_registry":
            continue
        for entry in document.get("entries", []):
            if isinstance(entry, Mapping):
                action_entries[f"{entry.get('action_id')}@{entry.get('version')}"] = entry
    capability_entries = _capability_requirement_entries(documents)

    indexed: dict[str, tuple[str, Mapping[str, Any]]] = {}
    seen_identities: set[tuple[str, str]] = set()
    seen_paths: set[str] = set()
    for position, entry in enumerate(index.get("entries", [])):
        if not isinstance(entry, Mapping):
            continue
        need_ref = entry.get("need_ref")
        need_id = entry.get("need_id")
        version = entry.get("version")
        document_path = entry.get("document_path")
        if not all(isinstance(value, str) for value in (need_ref, need_id, version, document_path)):
            continue
        identity = (str(need_id), str(version))
        if need_ref in indexed:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-NEED-REFERENCE-DUPLICATE",
                    f"duplicate Need reference at entries[{position}]: {need_ref}",
                )
            )
            continue
        if identity in seen_identities:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-NEED-IDENTITY-DUPLICATE",
                    f"duplicate Need identity at entries[{position}]: {need_id}@{version}",
                )
            )
            continue
        if document_path in seen_paths:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-NEED-PATH-DUPLICATE",
                    f"duplicate Need document path at entries[{position}]: {document_path}",
                )
            )
            continue
        indexed[str(need_ref)] = (str(document_path), entry)
        seen_identities.add(identity)
        seen_paths.add(str(document_path))

        loaded = _loaded_document_at(documents, document_path)
        if loaded is None:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-NEED-DOCUMENT-MISSING",
                    f"indexed Skill Need document is not loaded: {document_path}",
                )
            )
            continue
        loaded_path, need = loaded
        if infer_document_kind(need) != "skill_need":
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-NEED-DOCUMENT-KIND",
                    f"indexed document is not a Skill Need: {document_path}",
                )
            )
            continue
        if (
            need.get("need_ref"),
            need.get("need_id"),
            need.get("version"),
        ) != (need_ref, need_id, version):
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-NEED-IDENTITY-MISMATCH",
                    f"index and document identities disagree: {need_ref}",
                )
            )
        expected_hash = entry.get("content_hash")
        if isinstance(expected_hash, str) and _document_has_loaded_bytes(documents, loaded_path):
            if _document_hash(documents, loaded_path) != expected_hash.removeprefix("sha256:").lower():
                issues.append(
                    ValidationIssue(
                        index_path,
                        "SKILL-NEED-HASH-MISMATCH",
                        f"content hash does not match Skill Need document: {need_ref}",
                    )
                )

        for mode_ref in need.get("mode_refs", []):
            if isinstance(mode_ref, str) and modes and mode_ref not in modes:
                issues.append(
                    ValidationIssue(
                        loaded_path,
                        "SKILL-NEED-MODE-MISSING",
                        f"Skill Need references an unknown Research Mode: {mode_ref}",
                    )
                )
        seen_action_refs: set[str] = set()
        for action in need.get("origin_actions", []):
            if not isinstance(action, Mapping):
                continue
            action_ref = action.get("action_ref")
            if isinstance(action_ref, str):
                if action_ref in seen_action_refs:
                    issues.append(
                        ValidationIssue(
                            loaded_path,
                            "SKILL-NEED-ACTION-DUPLICATE",
                            f"duplicate origin Action reference: {action_ref}",
                        )
                    )
                seen_action_refs.add(action_ref)
            registered = action_entries.get(str(action_ref))
            if action_entries and registered is None:
                issues.append(
                    ValidationIssue(
                        loaded_path,
                        "SKILL-NEED-ACTION-MISSING",
                        f"Skill Need references an unknown Mode Action: {action_ref}",
                    )
                )
            elif registered is not None:
                if action.get("content_hash") != registered.get("content_hash"):
                    issues.append(
                        ValidationIssue(
                            loaded_path,
                            "SKILL-NEED-ACTION-HASH-MISMATCH",
                            f"Skill Need Action hash does not match Registry: {action_ref}",
                        )
                    )
                if registered.get("mode_ref") not in set(need.get("mode_refs", [])):
                    issues.append(
                        ValidationIssue(
                            loaded_path,
                            "SKILL-NEED-ACTION-MODE-MISMATCH",
                            f"Skill Need Action mode is outside mode_refs: {action_ref}",
                        )
                    )
        baseline = need.get("baseline", {})
        if isinstance(baseline, Mapping):
            for requirement_ref in baseline.get("capability_requirement_refs", []):
                if (
                    isinstance(requirement_ref, str)
                    and capability_entries
                    and requirement_ref not in capability_entries
                ):
                    issues.append(
                        ValidationIssue(
                            loaded_path,
                            "SKILL-NEED-CAPABILITY-REQUIREMENT-MISSING",
                            f"baseline references an unknown Capability Requirement: {requirement_ref}",
                        )
                    )
        evaluation = need.get("evaluation_requirements", {})
        if isinstance(evaluation, Mapping):
            evidence_classes: set[str] = set()
            for item in evaluation.get("required_evidence_classes", []):
                if not isinstance(item, Mapping) or not isinstance(item.get("evidence_class_id"), str):
                    continue
                evidence_class_id = str(item["evidence_class_id"])
                if evidence_class_id in evidence_classes:
                    issues.append(
                        ValidationIssue(
                            loaded_path,
                            "SKILL-NEED-EVIDENCE-CLASS-DUPLICATE",
                            f"duplicate required evidence class: {evidence_class_id}",
                        )
                    )
                evidence_classes.add(evidence_class_id)
            criterion_ids: set[str] = set()
            for criterion in evaluation.get("criteria", []):
                if not isinstance(criterion, Mapping):
                    continue
                criterion_id = criterion.get("criterion_id")
                if isinstance(criterion_id, str):
                    if criterion_id in criterion_ids:
                        issues.append(
                            ValidationIssue(
                                loaded_path,
                                "SKILL-NEED-CRITERION-DUPLICATE",
                                f"duplicate evaluation criterion: {criterion_id}",
                            )
                        )
                    criterion_ids.add(criterion_id)
                unknown = sorted(
                    value
                    for value in criterion.get("evidence_class_refs", [])
                    if isinstance(value, str) and value not in evidence_classes
                )
                if unknown:
                    issues.append(
                        ValidationIssue(
                            loaded_path,
                            "SKILL-NEED-EVIDENCE-CLASS-MISSING",
                            f"criterion references unknown evidence classes: {unknown}",
                        )
                    )
        domain_scope = need.get("domain_scope", {})
        if isinstance(domain_scope, Mapping):
            variant_ids: set[str] = set()
            for variant in domain_scope.get("variants", []):
                if not isinstance(variant, Mapping) or not isinstance(variant.get("variant_id"), str):
                    continue
                variant_id = str(variant["variant_id"])
                if variant_id in variant_ids:
                    issues.append(
                        ValidationIssue(
                            loaded_path,
                            "SKILL-NEED-DOMAIN-VARIANT-DUPLICATE",
                            f"duplicate domain variant: {variant_id}",
                        )
                    )
                variant_ids.add(variant_id)

    for path, need in need_documents:
        need_ref = need.get("need_ref")
        indexed_entry = indexed.get(str(need_ref))
        if indexed_entry is None:
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-NEED-UNINDEXED",
                    f"Skill Need document is not in the integrity index: {need_ref}",
                )
            )
        elif not _matches_repository_path(path, indexed_entry[0]):
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-NEED-PATH-MISMATCH",
                    f"Skill Need document path disagrees with the index: {need_ref}",
                )
            )

    for need_ref in method_references:
        if need_ref not in indexed:
            issues.append(
                ValidationIssue(
                    index_path,
                    "METHOD-RESOLUTION-SKILL-NEED-MISSING",
                    f"Method Resolution references an unknown Skill Need: {need_ref}",
                )
            )
    return issues


def _protocol_profile_indices(
    documents: Mapping[Path, Any],
) -> list[tuple[Path, Mapping[str, Any]]]:
    return [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping)
        and document.get("registry_kind") == "protocol_profile_index"
    ]


def _validate_protocol_profile_set(
    documents: Mapping[Path, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    indices = _protocol_profile_indices(documents)
    profile_documents = [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping) and infer_document_kind(document) == "protocol_profile"
    ]
    if not indices:
        if profile_documents:
            issues.append(
                ValidationIssue(
                    profile_documents[0][0],
                    "PROTOCOL-PROFILE-INDEX-MISSING",
                    "Protocol Profile documents require one closed integrity index",
                )
            )
        return issues
    if len(indices) > 1:
        for path, _ in indices[1:]:
            issues.append(
                ValidationIssue(
                    path,
                    "PROTOCOL-PROFILE-INDEX-DUPLICATE",
                    "only one Protocol Profile integrity index may be loaded",
                )
            )
        return issues

    index_path, index = indices[0]
    modes = {
        f"{document.get('mode_id')}@{document.get('version')}"
        for document in documents.values()
        if isinstance(document, Mapping) and "mode_id" in document and "claim_rules" in document
    }
    action_entries: dict[str, Mapping[str, Any]] = {}
    for document in documents.values():
        if not isinstance(document, Mapping) or document.get("registry_kind") != "mode_action_registry":
            continue
        for entry in document.get("entries", []):
            if isinstance(entry, Mapping):
                action_entries[f"{entry.get('action_id')}@{entry.get('version')}"] = entry

    indexed: dict[str, tuple[str, Mapping[str, Any]]] = {}
    seen_identities: set[tuple[str, str]] = set()
    seen_paths: set[str] = set()
    for position, entry in enumerate(index.get("entries", [])):
        if not isinstance(entry, Mapping):
            continue
        profile_ref = entry.get("profile_ref")
        profile_id = entry.get("profile_id")
        version = entry.get("version")
        document_path = entry.get("document_path")
        if not all(
            isinstance(value, str)
            for value in (profile_ref, profile_id, version, document_path)
        ):
            continue
        identity = (str(profile_id), str(version))
        if profile_ref in indexed:
            issues.append(
                ValidationIssue(
                    index_path,
                    "PROTOCOL-PROFILE-REFERENCE-DUPLICATE",
                    f"duplicate Profile reference at entries[{position}]: {profile_ref}",
                )
            )
            continue
        if identity in seen_identities:
            issues.append(
                ValidationIssue(
                    index_path,
                    "PROTOCOL-PROFILE-IDENTITY-DUPLICATE",
                    f"duplicate Profile identity at entries[{position}]: {profile_id}@{version}",
                )
            )
            continue
        if document_path in seen_paths:
            issues.append(
                ValidationIssue(
                    index_path,
                    "PROTOCOL-PROFILE-PATH-DUPLICATE",
                    f"duplicate Profile document path at entries[{position}]: {document_path}",
                )
            )
            continue
        indexed[str(profile_ref)] = (str(document_path), entry)
        seen_identities.add(identity)
        seen_paths.add(str(document_path))

        loaded = _loaded_document_at(documents, document_path)
        if loaded is None:
            issues.append(
                ValidationIssue(
                    index_path,
                    "PROTOCOL-PROFILE-DOCUMENT-MISSING",
                    f"indexed Protocol Profile document is not loaded: {document_path}",
                )
            )
            continue
        loaded_path, profile = loaded
        if infer_document_kind(profile) != "protocol_profile":
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "PROTOCOL-PROFILE-DOCUMENT-KIND",
                    f"indexed document is not a Protocol Profile: {document_path}",
                )
            )
            continue
        if (
            f"{profile.get('profile_id')}@{profile.get('version')}",
            profile.get("profile_id"),
            profile.get("version"),
        ) != (profile_ref, profile_id, version):
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "PROTOCOL-PROFILE-IDENTITY-MISMATCH",
                    f"index and document identities disagree: {profile_ref}",
                )
            )
        expected_hash = entry.get("content_hash")
        if isinstance(expected_hash, str) and _document_has_loaded_bytes(documents, loaded_path):
            if _document_hash(documents, loaded_path) != expected_hash.removeprefix("sha256:").lower():
                issues.append(
                    ValidationIssue(
                        index_path,
                        "PROTOCOL-PROFILE-HASH-MISMATCH",
                        f"content hash does not match Protocol Profile document: {profile_ref}",
                    )
                )

        compatible_modes = {
            value for value in profile.get("compatible_mode_refs", []) if isinstance(value, str)
        }
        for mode_ref in compatible_modes:
            if modes and mode_ref not in modes:
                issues.append(
                    ValidationIssue(
                        loaded_path,
                        "PROTOCOL-PROFILE-MODE-MISSING",
                        f"Profile references an unknown Research Mode: {mode_ref}",
                    )
                )

        scoped_action_refs: set[str] = set()
        for action in profile.get("scoped_actions", []):
            if not isinstance(action, Mapping):
                continue
            action_ref = action.get("action_ref")
            if not isinstance(action_ref, str):
                continue
            if action_ref in scoped_action_refs:
                issues.append(
                    ValidationIssue(
                        loaded_path,
                        "PROTOCOL-PROFILE-ACTION-DUPLICATE",
                        f"duplicate scoped Action reference: {action_ref}",
                    )
                )
            scoped_action_refs.add(action_ref)
            registered = action_entries.get(action_ref)
            if action_entries and registered is None:
                issues.append(
                    ValidationIssue(
                        loaded_path,
                        "PROTOCOL-PROFILE-ACTION-MISSING",
                        f"Profile references an unknown Mode Action: {action_ref}",
                    )
                )
            elif registered is not None:
                if action.get("content_hash") != registered.get("content_hash"):
                    issues.append(
                        ValidationIssue(
                            loaded_path,
                            "PROTOCOL-PROFILE-ACTION-HASH-MISMATCH",
                            f"Profile Action hash does not match Registry: {action_ref}",
                        )
                    )
                if registered.get("mode_ref") not in compatible_modes:
                    issues.append(
                        ValidationIssue(
                            loaded_path,
                            "PROTOCOL-PROFILE-ACTION-MODE-MISMATCH",
                            f"Profile Action mode is outside compatible_mode_refs: {action_ref}",
                        )
                    )

        evidence_refs: set[str] = set()
        for evidence in profile.get("evidence_expectations", []):
            if not isinstance(evidence, Mapping) or not isinstance(evidence.get("expectation_id"), str):
                continue
            expectation_id = str(evidence["expectation_id"])
            if expectation_id in evidence_refs:
                issues.append(
                    ValidationIssue(
                        loaded_path,
                        "PROTOCOL-PROFILE-EVIDENCE-DUPLICATE",
                        f"duplicate evidence expectation: {expectation_id}",
                    )
                )
            evidence_refs.add(expectation_id)

        gate_refs: set[str] = set()
        for gate in profile.get("gate_expectations", []):
            if not isinstance(gate, Mapping) or not isinstance(gate.get("gate_ref"), str):
                continue
            gate_ref = str(gate["gate_ref"])
            if gate_ref in gate_refs:
                issues.append(
                    ValidationIssue(
                        loaded_path,
                        "PROTOCOL-PROFILE-GATE-DUPLICATE",
                        f"duplicate Gate expectation: {gate_ref}",
                    )
                )
            gate_refs.add(gate_ref)

        obligation_ids: set[str] = set()
        covered_action_refs: set[str] = set()
        for obligation in profile.get("method_obligations", []):
            if not isinstance(obligation, Mapping):
                continue
            obligation_id = obligation.get("obligation_id")
            if isinstance(obligation_id, str):
                if obligation_id in obligation_ids:
                    issues.append(
                        ValidationIssue(
                            loaded_path,
                            "PROTOCOL-PROFILE-OBLIGATION-DUPLICATE",
                            f"duplicate method obligation: {obligation_id}",
                        )
                    )
                obligation_ids.add(obligation_id)
            action_refs = {
                value
                for value in obligation.get("applies_to_action_refs", [])
                if isinstance(value, str)
            }
            covered_action_refs.update(action_refs)
            unknown_actions = sorted(action_refs - scoped_action_refs)
            unknown_evidence = sorted(
                {
                    value
                    for value in obligation.get("evidence_expectation_refs", [])
                    if isinstance(value, str)
                }
                - evidence_refs
            )
            unknown_gates = sorted(
                {
                    value
                    for value in obligation.get("gate_expectation_refs", [])
                    if isinstance(value, str)
                }
                - gate_refs
            )
            if unknown_actions:
                issues.append(
                    ValidationIssue(
                        loaded_path,
                        "PROTOCOL-PROFILE-OBLIGATION-ACTION-MISSING",
                        f"obligation references Actions outside Profile scope: {unknown_actions}",
                    )
                )
            if unknown_evidence:
                issues.append(
                    ValidationIssue(
                        loaded_path,
                        "PROTOCOL-PROFILE-OBLIGATION-EVIDENCE-MISSING",
                        f"obligation references unknown evidence expectations: {unknown_evidence}",
                    )
                )
            if unknown_gates:
                issues.append(
                    ValidationIssue(
                        loaded_path,
                        "PROTOCOL-PROFILE-OBLIGATION-GATE-MISSING",
                        f"obligation references unknown Gate expectations: {unknown_gates}",
                    )
                )
        uncovered = sorted(scoped_action_refs - covered_action_refs)
        if uncovered:
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "PROTOCOL-PROFILE-ACTION-UNCOVERED",
                    f"scoped Actions are not covered by a method obligation: {uncovered}",
                )
            )

    for path, profile in profile_documents:
        profile_ref = f"{profile.get('profile_id')}@{profile.get('version')}"
        indexed_entry = indexed.get(profile_ref)
        if indexed_entry is None:
            issues.append(
                ValidationIssue(
                    path,
                    "PROTOCOL-PROFILE-UNINDEXED",
                    f"Protocol Profile document is not in the integrity index: {profile_ref}",
                )
            )
        elif not _matches_repository_path(path, indexed_entry[0]):
            issues.append(
                ValidationIssue(
                    path,
                    "PROTOCOL-PROFILE-PATH-MISMATCH",
                    f"Protocol Profile document path disagrees with the index: {profile_ref}",
                )
            )
    return issues


def _validate_skill_lifecycle_v2(
    documents: Mapping[Path, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    indices = [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping)
        and document.get("registry_kind") == "skill_lifecycle_index"
    ]
    records = [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping)
        and infer_document_kind(document) == "skill_lifecycle_record"
    ]
    migrations = [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping)
        and infer_document_kind(document) == "skill_lifecycle_migration"
    ]
    if not indices:
        if records or migrations:
            anchor = records[0][0] if records else migrations[0][0]
            issues.append(
                ValidationIssue(
                    anchor,
                    "SKILL-LIFECYCLE-INDEX-MISSING",
                    "Skill Lifecycle records and migrations require one closed integrity index",
                )
            )
        return issues
    if len(indices) > 1:
        for path, _ in indices[1:]:
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-LIFECYCLE-INDEX-DUPLICATE",
                    "only one Skill Lifecycle v2 integrity index may be loaded",
                )
            )
        return issues

    index_path, index = indices[0]
    accepted_documents = [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping) and document.get("registry_kind") == "skill_accepted"
    ]
    accepted_entries: dict[tuple[str, str], Mapping[str, Any]] = {}
    if len(accepted_documents) == 1:
        for entry in accepted_documents[0][1].get("entries", []):
            if isinstance(entry, Mapping):
                accepted_entries[(str(entry.get("skill_id")), str(entry.get("version")))] = entry
    need_refs = set(_skill_need_entries(documents))

    indexed: dict[str, tuple[str, Mapping[str, Any], SkillLifecycleRecord]] = {}
    seen_identities: set[tuple[str, str]] = set()
    seen_paths: set[str] = set()
    for position, entry in enumerate(index.get("entries", [])):
        if not isinstance(entry, Mapping):
            continue
        lifecycle_ref = entry.get("lifecycle_ref")
        lifecycle_id = entry.get("lifecycle_id")
        lifecycle_version = entry.get("lifecycle_version")
        document_path = entry.get("document_path")
        if not all(
            isinstance(value, str)
            for value in (lifecycle_ref, lifecycle_id, lifecycle_version, document_path)
        ):
            continue
        identity = (str(lifecycle_id), str(lifecycle_version))
        if lifecycle_ref in indexed:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-LIFECYCLE-REFERENCE-DUPLICATE",
                    f"duplicate lifecycle reference at entries[{position}]: {lifecycle_ref}",
                )
            )
            continue
        if identity in seen_identities:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-LIFECYCLE-IDENTITY-DUPLICATE",
                    f"duplicate lifecycle identity at entries[{position}]: {lifecycle_id}@{lifecycle_version}",
                )
            )
            continue
        if document_path in seen_paths:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-LIFECYCLE-PATH-DUPLICATE",
                    f"duplicate lifecycle path at entries[{position}]: {document_path}",
                )
            )
            continue
        seen_identities.add(identity)
        seen_paths.add(str(document_path))
        loaded = _loaded_document_at(documents, str(document_path))
        if loaded is None:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-LIFECYCLE-DOCUMENT-MISSING",
                    f"indexed lifecycle document is not loaded: {document_path}",
                )
            )
            continue
        loaded_path, document = loaded
        try:
            record = SkillLifecycleRecord.from_mapping(document)
        except ContractError as exc:
            issues.append(
                ValidationIssue(loaded_path, "SKILL-LIFECYCLE-CONTRACT", str(exc))
            )
            continue
        if (
            record.reference,
            record.lifecycle_id,
            record.lifecycle_version,
        ) != (lifecycle_ref, lifecycle_id, lifecycle_version):
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-LIFECYCLE-IDENTITY-MISMATCH",
                    f"index and lifecycle identities disagree: {lifecycle_ref}",
                )
            )
        expected_hash = entry.get("content_hash")
        if isinstance(expected_hash, str) and _document_has_loaded_bytes(documents, loaded_path):
            if _document_hash(documents, loaded_path) != expected_hash.removeprefix("sha256:").lower():
                issues.append(
                    ValidationIssue(
                        index_path,
                        "SKILL-LIFECYCLE-HASH-MISMATCH",
                        f"lifecycle content hash does not match: {lifecycle_ref}",
                    )
                )
        indexed[str(lifecycle_ref)] = (str(document_path), entry, record)

        if record.lifecycle_id != record.skill_ref.skill_id:
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-LIFECYCLE-SKILL-IDENTITY-MISMATCH",
                    "lifecycle_id must equal the governed skill_id",
                )
            )
        unknown_needs = sorted(set(record.need_refs) - need_refs) if need_refs else []
        if unknown_needs:
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-LIFECYCLE-NEED-MISSING",
                    f"lifecycle references unknown Skill Needs: {unknown_needs}",
                )
            )
        if record.record_scope == "migrated-legacy":
            accepted = accepted_entries.get((record.skill_ref.skill_id, record.skill_ref.version))
            if accepted_entries and accepted is None:
                issues.append(
                    ValidationIssue(
                        loaded_path,
                        "SKILL-LIFECYCLE-LEGACY-SOURCE-MISSING",
                        "migrated legacy lifecycle has no matching accepted Registry entry",
                    )
                )
            elif accepted is not None:
                expected = {
                    "manifest_path": record.skill_ref.manifest_path,
                    "content_hash": record.skill_ref.content_hash,
                    "package_hash": record.skill_ref.package_hash,
                }
                if any(accepted.get(key) != value for key, value in expected.items()):
                    issues.append(
                        ValidationIssue(
                            loaded_path,
                            "SKILL-LIFECYCLE-LEGACY-SOURCE-DRIFT",
                            "migrated lifecycle no longer matches the accepted Registry source entry",
                        )
                    )

        admission_state = record.admission.state
        runtime_state = record.runtime_eligibility.state
        lifecycle_state = record.lifecycle.state
        if admission_state == "trial" and (
            record.evaluation.trial_ref is None or runtime_state != "trial-only"
        ):
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-LIFECYCLE-TRIAL-INCONSISTENT",
                    "trial admission requires a trial_ref and trial-only runtime eligibility",
                )
            )
        if runtime_state == "trial-only" and (
            admission_state != "trial" or lifecycle_state != "current"
        ):
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-LIFECYCLE-TRIAL-ELIGIBILITY-INCONSISTENT",
                    "trial-only runtime eligibility requires trial admission and current lifecycle",
                )
            )
        if runtime_state == "historical-replay-only" and (
            record.record_scope != "migrated-legacy"
            or admission_state != "legacy-imported"
            or lifecycle_state not in {"legacy-preserved", "retired", "superseded"}
        ):
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-LIFECYCLE-HISTORICAL-ELIGIBILITY-INCONSISTENT",
                    "historical replay eligibility is reserved for migrated legacy records",
                )
            )
        if lifecycle_state in {"retired", "superseded"} and runtime_state in {
            "eligible",
            "trial-only",
        }:
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-LIFECYCLE-ENDED-BUT-ELIGIBLE",
                    f"{lifecycle_state} lifecycle cannot remain eligible for current runtime binding",
                )
            )

    for path, document in records:
        lifecycle_ref = (
            f"{document.get('skill_ref', {}).get('skill_id')}@"
            f"{document.get('skill_ref', {}).get('version')}/lifecycle@"
            f"{document.get('lifecycle_version')}"
        )
        indexed_entry = indexed.get(lifecycle_ref)
        if indexed_entry is None:
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-LIFECYCLE-UNINDEXED",
                    f"lifecycle document is not in the integrity index: {lifecycle_ref}",
                )
            )
        elif not _matches_repository_path(path, indexed_entry[0]):
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-LIFECYCLE-PATH-MISMATCH",
                    f"lifecycle document path disagrees with the index: {lifecycle_ref}",
                )
            )

    for migration_path, migration in migrations:
        source_registry_path = migration.get("source_registry_path")
        target_index_path = migration.get("target_index_path")
        source_loaded = (
            _loaded_document_at(documents, source_registry_path)
            if isinstance(source_registry_path, str)
            else None
        )
        target_loaded = (
            _loaded_document_at(documents, target_index_path)
            if isinstance(target_index_path, str)
            else None
        )
        if source_loaded is None:
            issues.append(
                ValidationIssue(
                    migration_path,
                    "SKILL-LIFECYCLE-MIGRATION-SOURCE-MISSING",
                    f"migration source Registry is not loaded: {source_registry_path}",
                )
            )
            continue
        if target_loaded is None or target_loaded[0] != index_path:
            issues.append(
                ValidationIssue(
                    migration_path,
                    "SKILL-LIFECYCLE-MIGRATION-TARGET-MISSING",
                    f"migration target is not the loaded lifecycle index: {target_index_path}",
                )
            )
        current_entries = {
            (str(item.get("skill_id")), str(item.get("version"))): item
            for item in source_loaded[1].get("entries", [])
            if isinstance(item, Mapping)
        }
        seen_sources: set[tuple[str, str]] = set()
        seen_targets: set[str] = set()
        for item in migration.get("entries", []):
            if not isinstance(item, Mapping):
                continue
            source = item.get("source", {})
            target = item.get("target", {})
            if not isinstance(source, Mapping) or not isinstance(target, Mapping):
                continue
            source_identity = (str(source.get("skill_id")), str(source.get("version")))
            target_ref = str(target.get("lifecycle_ref"))
            if source_identity in seen_sources:
                issues.append(
                    ValidationIssue(
                        migration_path,
                        "SKILL-LIFECYCLE-MIGRATION-SOURCE-DUPLICATE",
                        f"migration source identity is duplicated: {source_identity}",
                    )
                )
            if target_ref in seen_targets:
                issues.append(
                    ValidationIssue(
                        migration_path,
                        "SKILL-LIFECYCLE-MIGRATION-TARGET-DUPLICATE",
                        f"migration target is duplicated: {target_ref}",
                    )
                )
            seen_sources.add(source_identity)
            seen_targets.add(target_ref)
            current = current_entries.get(source_identity)
            source_fields = (
                "manifest_path",
                "content_hash",
                "package_hash",
                "lifecycle",
            )
            source_values = (
                source.get("manifest_path"),
                source.get("content_hash"),
                source.get("package_hash"),
                source.get("legacy_lifecycle"),
            )
            if current is None or tuple(current.get(key) for key in source_fields) != source_values:
                issues.append(
                    ValidationIssue(
                        migration_path,
                        "SKILL-LIFECYCLE-MIGRATION-SOURCE-DRIFT",
                        f"pinned source entry does not match accepted Registry: {source_identity}",
                    )
                )
            indexed_target = indexed.get(target_ref)
            if indexed_target is None:
                issues.append(
                    ValidationIssue(
                        migration_path,
                        "SKILL-LIFECYCLE-MIGRATION-TARGET-UNKNOWN",
                        f"migration target is not indexed: {target_ref}",
                    )
                )
                continue
            if (
                target.get("document_path") != indexed_target[0]
                or target.get("content_hash") != indexed_target[1].get("content_hash")
            ):
                issues.append(
                    ValidationIssue(
                        migration_path,
                        "SKILL-LIFECYCLE-MIGRATION-TARGET-DRIFT",
                        f"migration target path/hash does not match index: {target_ref}",
                    )
                )
            if item.get("disposition") != indexed_target[2].lifecycle.state:
                issues.append(
                    ValidationIssue(
                        migration_path,
                        "SKILL-LIFECYCLE-MIGRATION-DISPOSITION-DRIFT",
                        f"migration disposition does not match lifecycle record: {target_ref}",
                    )
                )
    return issues


def _validate_capability_supply_chain(
    documents: Mapping[Path, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    reports: dict[str, tuple[Path, Mapping[str, Any], CapabilitySupplyReport]] = {}
    resolutions: dict[str, tuple[Path, Mapping[str, Any]]] = {}
    lifecycle_records: dict[str, SkillLifecycleRecord] = {}
    for document in documents.values():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "skill_lifecycle_record":
            continue
        try:
            record = SkillLifecycleRecord.from_mapping(document)
        except ContractError:
            continue
        lifecycle_records[record.reference] = record

    def runtime_eligibility_check(lifecycle_ref: str, eligibility_ref: str) -> bool:
        record = lifecycle_records.get(lifecycle_ref)
        return bool(
            record
            and record.runtime_eligibility.eligibility_ref == eligibility_ref
            and record.externally_verified_for_new_binding(
                # Phase B has no authoritative Phase D evidence or Human
                # Decision document resolver.  Lifecycle state and reference
                # strings therefore remain structural facts and must fail
                # closed for a new Runtime binding.
                evidence_resolver=lambda _reference: False,
                decision_resolver=lambda _reference: False,
            )
        )

    def loaded_ref(
        owner_path: Path,
        reference: Any,
        *,
        missing_code: str,
        hash_code: str,
    ) -> tuple[Path, Mapping[str, Any]] | None:
        if not isinstance(reference, Mapping):
            issues.append(
                ValidationIssue(owner_path, missing_code, "reference must be an object")
            )
            return None
        document_path = reference.get("document_path")
        expected_hash = reference.get("content_hash")
        if not isinstance(document_path, str):
            issues.append(
                ValidationIssue(
                    owner_path,
                    missing_code,
                    "reference has no repository-relative document_path",
                )
            )
            return None
        loaded = _loaded_document_at(documents, document_path)
        if loaded is None:
            issues.append(
                ValidationIssue(
                    owner_path,
                    missing_code,
                    f"referenced document is not loaded: {document_path}",
                )
            )
            return None
        loaded_path, document = loaded
        if isinstance(expected_hash, str) and _document_has_loaded_bytes(documents, loaded_path):
            if _document_hash(documents, loaded_path) != expected_hash.removeprefix("sha256:").lower():
                issues.append(
                    ValidationIssue(
                        owner_path,
                        hash_code,
                        f"referenced document hash does not match: {document_path}",
                    )
                )
        return loaded_path, document

    def validate_evidence(
        identity: Any,
        evidence: Mapping[str, Any],
        required_capability: str | None,
        *,
        owner_path: Path | None = None,
    ) -> str:
        """Validate evidence semantics and return pass/fail/unknown.

        Provider conformance checks prove only low-level adapter behavior.  They
        therefore remain ``unknown`` for a high-level M9 Requirement even when
        the provider report itself passed.
        """

        artifact_ref = evidence.get("artifact_ref")
        if not isinstance(artifact_ref, Mapping):
            return "fail"
        artifact_path = artifact_ref.get("path")
        artifact_hash = artifact_ref.get("sha256")
        if not isinstance(artifact_path, str):
            return "fail"
        loaded = _loaded_document_at(documents, artifact_path)
        if loaded is None:
            return "fail"
        loaded_path, artifact = loaded
        if not isinstance(artifact_hash, str) or (
            _document_has_loaded_bytes(documents, loaded_path)
            and _document_hash(documents, loaded_path) != artifact_hash.removeprefix("sha256:").lower()
        ):
            return "fail"

        declared_kind = evidence.get("artifact_kind")
        expected_kind = {
            "capability-conformance-evidence": "capability_conformance_evidence",
            "provider-conformance-report": "provider_conformance_report",
        }.get(str(declared_kind))
        actual_kind = infer_document_kind(artifact)
        if expected_kind is None or actual_kind != expected_kind:
            if owner_path is not None:
                issues.append(
                    ValidationIssue(
                        owner_path,
                        "CAPABILITY-SUPPLY-EVIDENCE-KIND-MISMATCH",
                        f"declared artifact kind {declared_kind!r} does not match {actual_kind!r}",
                    )
                )
            return "fail"

        evidence_id = evidence.get("evidence_id")
        if expected_kind == "capability_conformance_evidence":
            valid = True
            checks: tuple[tuple[bool, str, str], ...] = (
                (
                    evidence_id == artifact.get("evidence_id"),
                    "CAPABILITY-SUPPLY-EVIDENCE-IDENTITY-MISMATCH",
                    "evidence_id does not match the capability evidence identity",
                ),
                (
                    artifact.get("implementation_ref") == identity.implementation_ref,
                    "CAPABILITY-SUPPLY-EVIDENCE-IMPLEMENTATION-MISMATCH",
                    "capability evidence implementation does not match Supply identity",
                ),
                (
                    artifact.get("implementation_version") == identity.implementation_version,
                    "CAPABILITY-SUPPLY-EVIDENCE-VERSION-MISMATCH",
                    "capability evidence version does not match Supply identity",
                ),
            )
            for passed, code, message in checks:
                if not passed:
                    valid = False
                    if owner_path is not None:
                        issues.append(ValidationIssue(owner_path, code, message))
            capabilities = artifact.get("capability_ids")
            if required_capability is not None and (
                not isinstance(capabilities, list)
                or required_capability not in capabilities
            ):
                valid = False
                if owner_path is not None:
                    issues.append(
                        ValidationIssue(
                            owner_path,
                            "CAPABILITY-SUPPLY-EVIDENCE-CAPABILITY-MISMATCH",
                            f"capability evidence does not prove {required_capability!r}",
                        )
                    )
            evidence_kind = artifact.get("evidence_kind")
            evidence_class = evidence.get("evidence_class")
            if (
                (evidence_class == "deterministic" and evidence_kind != "deterministic-fixture")
                or (
                    evidence_class == "live"
                    and evidence_kind not in {"local-conformance", "live-conformance"}
                )
            ):
                valid = False
                if owner_path is not None:
                    issues.append(
                        ValidationIssue(
                            owner_path,
                            "CAPABILITY-SUPPLY-EVIDENCE-CLASS-MISMATCH",
                            "Supply evidence_class does not match the typed evidence_kind",
                        )
                    )
            if not valid or artifact.get("result") == "fail":
                if owner_path is not None and artifact.get("result") == "fail":
                    issues.append(
                        ValidationIssue(
                            owner_path,
                            "CAPABILITY-SUPPLY-EVIDENCE-RESULT-FAILED",
                            "referenced capability evidence records a failed result",
                        )
                    )
                return "fail"
            return "pass" if artifact.get("result") == "pass" else "unknown"

        adapter_components = [
            component
            for component in identity.components
            if component.component_kind == "adapter"
        ]
        adapter_matches = any(
            component.component_ref == artifact.get("adapter_id")
            and component.version == artifact.get("adapter_version")
            for component in adapter_components
        )
        provider_components = [
            component
            for component in identity.components
            if component.component_kind == "provider"
        ]
        provider_matches = any(
            component.component_ref == artifact.get("provider")
            for component in provider_components
        )
        valid = True
        provider_checks: tuple[tuple[bool, str, str], ...] = (
            (
                evidence_id == artifact.get("report_id"),
                "CAPABILITY-SUPPLY-EVIDENCE-IDENTITY-MISMATCH",
                "evidence_id does not match ProviderConformanceReport.report_id",
            ),
            (
                evidence.get("evidence_class") == "live",
                "CAPABILITY-SUPPLY-EVIDENCE-CLASS-MISMATCH",
                "ProviderConformanceReport must be referenced as live evidence",
            ),
            (
                adapter_matches,
                "CAPABILITY-SUPPLY-EVIDENCE-IMPLEMENTATION-MISMATCH",
                "ProviderConformanceReport adapter identity/version does not match a Supply component",
            ),
            (
                provider_matches,
                "CAPABILITY-SUPPLY-EVIDENCE-IMPLEMENTATION-MISMATCH",
                "ProviderConformanceReport provider identity does not match a Supply component",
            ),
        )
        for passed, code, message in provider_checks:
            if not passed:
                valid = False
                if owner_path is not None:
                    issues.append(ValidationIssue(owner_path, code, message))
        if not valid or artifact.get("status") == "failed":
            if owner_path is not None and artifact.get("status") == "failed":
                issues.append(
                    ValidationIssue(
                        owner_path,
                        "CAPABILITY-SUPPLY-EVIDENCE-RESULT-FAILED",
                        "referenced ProviderConformanceReport records a failed result",
                    )
                )
            return "fail"
        # text/structured/tools checks are intentionally not a proof of a
        # scientific or method-level Capability Requirement.
        return "unknown"

    def evidence_check(identity: Any, evidence: Mapping[str, Any], requirement_id: str) -> str:
        return validate_evidence(identity, evidence, requirement_id)

    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "capability_supply_report":
            continue
        try:
            parsed = CapabilitySupplyReport.from_mapping(document)
        except ContractError as exc:
            issues.append(
                ValidationIssue(path, "CAPABILITY-SUPPLY-CONTRACT", str(exc))
            )
            continue
        if parsed.reference in reports:
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-SUPPLY-IDENTITY-DUPLICATE",
                    f"duplicate Supply Report identity: {parsed.reference}",
                )
            )
            continue
        reports[parsed.reference] = (path, document, parsed)

        component_kinds = {component.component_kind for component in parsed.supply_identity.components}
        required_kinds = {
            "procedure": {"procedure"},
            "tool": {"tool"},
            "adapter-provider": {"adapter", "provider"},
            "skill": {"skill"},
        }.get(parsed.supply_identity.supply_kind, set())
        if not required_kinds <= component_kinds:
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-SUPPLY-COMPONENT-INCOMPLETE",
                    f"{parsed.supply_identity.supply_kind} supply requires component kinds {sorted(required_kinds)}",
                )
            )
        # A Report only states supply facts.  Skill lifecycle and external
        # admission evidence are evaluated by Resolution for a requested
        # qualification; they do not make the Report itself invalid.
        component_keys = [
            (component.component_kind, component.component_ref, component.version)
            for component in parsed.supply_identity.components
        ]
        if len(component_keys) != len(set(component_keys)):
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-SUPPLY-COMPONENT-DUPLICATE",
                    "Supply Report component identities must be unique",
                )
            )
        availability_scope = parsed.availability.get("scope")
        expected_scope_kind = {
            "synthetic-bounded-fixture": "fixture-only",
            "deterministic-local": "local-environment",
            "live-observation": "provider-observation",
        }.get(parsed.observation_scope)
        if (
            not isinstance(availability_scope, Mapping)
            or availability_scope.get("scope_kind") != expected_scope_kind
        ):
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-SUPPLY-OBSERVATION-SCOPE-MISMATCH",
                    "Report observation_scope does not match its provider-neutral availability scope",
                )
            )
        observed_at = _aware_datetime(parsed.availability.get("observed_at"))
        valid_until_value = parsed.availability.get("valid_until")
        valid_until = (
            _aware_datetime(valid_until_value)
            if valid_until_value is not None
            else None
        )
        if observed_at is None or (
            valid_until_value is not None
            and (valid_until is None or observed_at > valid_until)
        ):
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-SUPPLY-AVAILABILITY-TIME-INVALID",
                    "availability timestamps must be timezone-aware and valid_until cannot precede observed_at",
                )
            )
        evidence_ids: set[str] = set()
        for evidence in parsed.conformance_evidence:
            evidence_id = evidence.get("evidence_id")
            if isinstance(evidence_id, str):
                if evidence_id in evidence_ids:
                    issues.append(
                        ValidationIssue(
                            path,
                            "CAPABILITY-SUPPLY-EVIDENCE-DUPLICATE",
                            f"duplicate conformance evidence identity: {evidence_id}",
                        )
                    )
                evidence_ids.add(evidence_id)
            artifact_ref = evidence.get("artifact_ref")
            if not isinstance(artifact_ref, Mapping):
                continue
            artifact_path = artifact_ref.get("path")
            artifact_hash = artifact_ref.get("sha256")
            if not isinstance(artifact_path, str):
                continue
            loaded = _loaded_document_at(documents, artifact_path)
            if loaded is None:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-SUPPLY-EVIDENCE-MISSING",
                        f"conformance evidence artifact is not loaded: {artifact_path}",
                    )
                )
            elif isinstance(artifact_hash, str) and _document_has_loaded_bytes(documents, loaded[0]):
                if _document_hash(documents, loaded[0]) != artifact_hash.removeprefix("sha256:").lower():
                    issues.append(
                        ValidationIssue(
                            path,
                            "CAPABILITY-SUPPLY-EVIDENCE-HASH-MISMATCH",
                            f"conformance evidence hash does not match: {artifact_path}",
                        )
                    )
            # Check typed identity and result independently of the status text
            # carried by the Supply Report.  Report fields never override the
            # referenced artifact.
            validate_evidence(parsed.supply_identity, evidence, None, owner_path=path)
            loaded_artifact = _loaded_document_at(documents, artifact_path)
            if loaded_artifact is not None and evidence.get("artifact_kind") == "capability-conformance-evidence":
                capabilities = loaded_artifact[1].get("capability_ids")
                if isinstance(capabilities, list) and not set(capabilities) <= set(parsed.provided_capabilities):
                    issues.append(
                        ValidationIssue(
                            path,
                            "CAPABILITY-SUPPLY-EVIDENCE-CAPABILITY-DRIFT",
                            "capability evidence claims capabilities absent from the Supply Report",
                        )
                    )
                artifact_scope = loaded_artifact[1].get("scope")
                availability_scope = parsed.availability.get("scope")
                scope_matches = False
                if isinstance(artifact_scope, Mapping) and isinstance(
                    availability_scope, Mapping
                ):
                    if evidence.get("evidence_class") == "deterministic":
                        scope_matches = (
                            artifact_scope.get("scope_kind")
                            == "synthetic-bounded-fixture"
                            and availability_scope.get("scope_kind") == "fixture-only"
                            and artifact_scope.get("fixture_id")
                            == availability_scope.get("fixture_id")
                        )
                    else:
                        scope_matches = (
                            artifact_scope.get("scope_kind")
                            == availability_scope.get("scope_kind")
                            and artifact_scope.get("scope_kind")
                            in {"local-environment", "provider-observation"}
                            and artifact_scope.get("scope_ref")
                            == availability_scope.get("scope_ref")
                        )
                if not scope_matches:
                    issues.append(
                        ValidationIssue(
                            path,
                            "CAPABILITY-SUPPLY-EVIDENCE-SCOPE-MISMATCH",
                            "typed evidence observation scope does not match the Supply availability scope",
                        )
                    )

    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "capability_resolution":
            continue
        resolution_id = document.get("resolution_id")
        revision = document.get("revision")
        if not isinstance(resolution_id, str) or not isinstance(revision, int):
            continue
        resolution_ref = f"{resolution_id}@r{revision}"
        if resolution_ref in resolutions:
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-RESOLUTION-IDENTITY-DUPLICATE",
                    f"duplicate Capability Resolution identity: {resolution_ref}",
                )
            )
            continue
        resolutions[resolution_ref] = (path, document)

        method_loaded = loaded_ref(
            path,
            document.get("method_resolution_ref"),
            missing_code="CAPABILITY-RESOLUTION-METHOD-MISSING",
            hash_code="CAPABILITY-RESOLUTION-METHOD-HASH-MISMATCH",
        )
        method_document: Mapping[str, Any] | None = None
        if method_loaded is not None:
            _, method_document = method_loaded
            expected_method_ref = f"{method_document.get('resolution_id')}@r{method_document.get('revision')}"
            if document.get("method_resolution_ref", {}).get("ref") != expected_method_ref:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-METHOD-IDENTITY-MISMATCH",
                        f"Method Resolution identity does not match referenced document: {expected_method_ref}",
                    )
                )

        requirement_loaded = loaded_ref(
            path,
            document.get("requirement_ref"),
            missing_code="CAPABILITY-RESOLUTION-REQUIREMENT-MISSING",
            hash_code="CAPABILITY-RESOLUTION-REQUIREMENT-HASH-MISMATCH",
        )
        requirement: CapabilityRequirement | None = None
        requirement_id = None
        if requirement_loaded is not None:
            requirement_path, requirement_document = requirement_loaded
            requirement_id = requirement_document.get("requirement_id")
            if document.get("requirement_ref", {}).get("requirement_id") != requirement_id:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-REQUIREMENT-IDENTITY-MISMATCH",
                        f"Requirement identity does not match referenced document: {requirement_id}",
                    )
                )
            try:
                requirement = CapabilityRequirement.from_mapping(requirement_document)
            except ContractError as exc:
                issues.append(
                    ValidationIssue(requirement_path, "CAPABILITY-REQUIREMENT-CONTRACT", str(exc))
                )
        if method_document is not None and isinstance(requirement_id, str):
            method_requirements = {
                value
                for decision in method_document.get("action_decisions", [])
                if isinstance(decision, Mapping)
                for value in decision.get("capability_requirements", [])
                if isinstance(value, str)
            }
            if requirement_id not in method_requirements:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-METHOD-REQUIREMENT-MISSING",
                        f"Method Resolution does not require capability: {requirement_id}",
                    )
                )

        candidate_refs = document.get("candidate_supply_report_refs", [])
        candidate_ids: list[str] = []
        candidate_reports: list[CapabilitySupplyReport] = []
        method_is_no_skill = (
            method_document is not None
            and isinstance(method_document.get("skill_disposition"), Mapping)
            and method_document["skill_disposition"].get("status") == "no-skill"
        )
        for candidate in candidate_refs:
            if not isinstance(candidate, Mapping) or not isinstance(candidate.get("ref"), str):
                continue
            candidate_ref = str(candidate["ref"])
            candidate_ids.append(candidate_ref)
            loaded = loaded_ref(
                path,
                candidate,
                missing_code="CAPABILITY-RESOLUTION-SUPPLY-MISSING",
                hash_code="CAPABILITY-RESOLUTION-SUPPLY-HASH-MISMATCH",
            )
            registered = reports.get(candidate_ref)
            if registered is None:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-SUPPLY-IDENTITY-MISSING",
                        f"candidate Supply Report identity is not loaded: {candidate_ref}",
                    )
                )
                continue
            if loaded is not None and loaded[0] != registered[0]:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-SUPPLY-PATH-MISMATCH",
                        f"candidate path does not identify Supply Report: {candidate_ref}",
                    )
                )
            candidate_report = registered[2]
            candidate_identity = candidate_report.supply_identity
            if method_is_no_skill and (
                candidate_identity.supply_kind == "skill"
                or any(
                    component.component_kind == "skill"
                    for component in candidate_identity.components
                )
                or candidate_identity.skill_lifecycle_ref is not None
                or candidate_identity.runtime_eligibility_ref is not None
            ):
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-NO-SKILL-SUPPLY",
                        "a Method with no-skill disposition cannot resolve through a Skill Supply, Skill component, or Skill lifecycle binding",
                    )
                )
            candidate_reports.append(candidate_report)
        if len(candidate_ids) != len(set(candidate_ids)):
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-RESOLUTION-SUPPLY-DUPLICATE",
                    "candidate Supply Report references must be unique",
                )
            )

        if requirement is not None and len(candidate_reports) == len(candidate_ids):
            assessments = [
                assess_supply(
                    requirement,
                    report,
                    evaluated_at=document.get("evaluated_at"),
                    qualification=str(document.get("qualification")),
                    evidence_check=evidence_check,
                    runtime_eligibility_check=runtime_eligibility_check,
                )
                for report in candidate_reports
            ]
            expected_comparisons = [assessment.to_mapping() for assessment in assessments]
            if document.get("comparisons") != expected_comparisons:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-COMPARISON-DRIFT",
                        "recorded supply comparisons do not match deterministic recomputation",
                    )
                )
            expected_status, expected_selected = resolve_status(assessments)
            if document.get("resolution_status") != expected_status:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-STATUS-DRIFT",
                        f"recorded status does not match deterministic result: {expected_status}",
                    )
                )
            if document.get("selected_supply_report_ref") != expected_selected:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-SELECTION-DRIFT",
                        f"recorded selection does not match deterministic result: {expected_selected}",
                    )
                )

    snapshot_ids: set[str] = set()
    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "resolved_capability_snapshot":
            continue
        snapshot_ref = f"{document.get('snapshot_id')}@r{document.get('revision')}"
        if snapshot_ref in snapshot_ids:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-IDENTITY-DUPLICATE",
                    f"duplicate Resolved Capability Snapshot identity: {snapshot_ref}",
                )
            )
            continue
        snapshot_ids.add(snapshot_ref)
        resolution_loaded = loaded_ref(
            path,
            document.get("resolution_ref"),
            missing_code="RESOLVED-CAPABILITY-SNAPSHOT-RESOLUTION-MISSING",
            hash_code="RESOLVED-CAPABILITY-SNAPSHOT-RESOLUTION-HASH-MISMATCH",
        )
        if resolution_loaded is None:
            continue
        resolution_path, resolution = resolution_loaded
        resolution_ref = f"{resolution.get('resolution_id')}@r{resolution.get('revision')}"
        if document.get("resolution_ref", {}).get("ref") != resolution_ref:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-RESOLUTION-IDENTITY-MISMATCH",
                    f"Resolution identity does not match referenced document: {resolution_ref}",
                )
            )
        if resolution.get("resolution_status") != "satisfied":
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-UNSATISFIED",
                    "Snapshot requires a satisfied Capability Resolution",
                )
            )
        qualification = document.get("qualification")
        if qualification != resolution.get("qualification"):
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-QUALIFICATION-DRIFT",
                    "Snapshot qualification does not match Capability Resolution",
                )
            )
        for field in ("method_resolution_ref", "requirement_ref"):
            if document.get(field) != resolution.get(field):
                issues.append(
                    ValidationIssue(
                        path,
                        "RESOLVED-CAPABILITY-SNAPSHOT-LINEAGE-DRIFT",
                        f"Snapshot {field} does not match Capability Resolution",
                    )
                )

        method_loaded = loaded_ref(
            path,
            document.get("method_resolution_ref"),
            missing_code="RESOLVED-CAPABILITY-SNAPSHOT-METHOD-MISSING",
            hash_code="RESOLVED-CAPABILITY-SNAPSHOT-METHOD-HASH-MISMATCH",
        )
        task_loaded = loaded_ref(
            path,
            document.get("task_ref"),
            missing_code="RESOLVED-CAPABILITY-SNAPSHOT-TASK-MISSING",
            hash_code="RESOLVED-CAPABILITY-SNAPSHOT-TASK-HASH-MISMATCH",
        )
        task_document: Mapping[str, Any] | None = None
        if method_loaded is not None:
            expected_method_ref = f"{method_loaded[1].get('resolution_id')}@r{method_loaded[1].get('revision')}"
            if document.get("method_resolution_ref", {}).get("ref") != expected_method_ref:
                issues.append(
                    ValidationIssue(
                        path,
                        "RESOLVED-CAPABILITY-SNAPSHOT-METHOD-IDENTITY-MISMATCH",
                        f"Snapshot Method identity does not match {expected_method_ref}",
                    )
                )
        if task_loaded is not None:
            task_path, task_document = task_loaded
            task_revision = task_document.get("revision", 1)
            expected_task_ref = f"{task_document.get('task_id')}@r{task_revision}"
            if document.get("task_ref", {}).get("ref") != expected_task_ref:
                issues.append(
                    ValidationIssue(
                        path,
                        "RESOLVED-CAPABILITY-SNAPSHOT-TASK-IDENTITY-MISMATCH",
                        f"Snapshot Task identity does not match {expected_task_ref}",
                    )
                )
            if method_loaded is not None:
                method_task_ref = method_loaded[1].get("task_ref")
                expected_hash = (
                    _document_hash(documents, task_path)
                    if _document_has_loaded_bytes(documents, task_path)
                    else None
                )
                if not isinstance(method_task_ref, Mapping) or (
                    method_task_ref.get("task_id") != task_document.get("task_id")
                    or method_task_ref.get("revision") != task_revision
                    or (
                        expected_hash is not None
                        and str(method_task_ref.get("sha256", "")).removeprefix("sha256:").lower()
                        != expected_hash
                    )
                ):
                    issues.append(
                        ValidationIssue(
                            path,
                            "RESOLVED-CAPABILITY-SNAPSHOT-TASK-METHOD-LINEAGE-DRIFT",
                            "Snapshot Task does not match the Task frozen by Method Resolution",
                        )
                    )

        selected = document.get("selected_supply_report_ref")
        selected_ref = selected.get("ref") if isinstance(selected, Mapping) else None
        if selected_ref != resolution.get("selected_supply_report_ref"):
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-SELECTION-DRIFT",
                    "Snapshot supply selection does not match Capability Resolution",
                )
            )
        loaded_supply = loaded_ref(
            path,
            selected,
            missing_code="RESOLVED-CAPABILITY-SNAPSHOT-SUPPLY-MISSING",
            hash_code="RESOLVED-CAPABILITY-SNAPSHOT-SUPPLY-HASH-MISMATCH",
        )
        supply_entry = reports.get(str(selected_ref))
        if loaded_supply is None or supply_entry is None:
            continue
        if loaded_supply[0] != supply_entry[0]:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-SUPPLY-PATH-MISMATCH",
                    f"Snapshot path does not identify Supply Report: {selected_ref}",
                )
            )
        supply_document = supply_entry[1]
        copied_supply_fields = {
            "supply_identity": "supply_identity",
            "supply_required_permissions": "required_permissions",
            "supply_data_egress": "data_egress_behavior",
            "supply_side_effects": "side_effects",
        }
        for snapshot_field, report_field in copied_supply_fields.items():
            if document.get(snapshot_field) != supply_document.get(report_field):
                issues.append(
                    ValidationIssue(
                        path,
                        "RESOLVED-CAPABILITY-SNAPSHOT-SUPPLY-FACT-DRIFT",
                        f"Snapshot {snapshot_field} does not match selected Supply Report",
                    )
                )
        expected_evidence_refs = [
            item.get("artifact_ref")
            for item in supply_document.get("conformance_evidence", [])
            if isinstance(item, Mapping)
        ]
        if document.get("conformance_evidence_refs") != expected_evidence_refs:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-EVIDENCE-DRIFT",
                    "Snapshot conformance evidence refs do not match selected Supply Report",
                )
            )
        if resolution_path != resolutions.get(resolution_ref, (None, None))[0]:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-RESOLUTION-PATH-MISMATCH",
                    f"Snapshot path does not identify Capability Resolution: {resolution_ref}",
                )
            )

        if qualification == "structural-replay":
            if document.get("boundaries", {}).get("execution_input") is not False:
                issues.append(
                    ValidationIssue(
                        path,
                        "RESOLVED-CAPABILITY-SNAPSHOT-STRUCTURAL-EXECUTION-FORBIDDEN",
                        "structural-replay Snapshot cannot be an execution input",
                    )
                )
            continue

        if qualification != "runtime-execution":
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-QUALIFICATION-UNKNOWN",
                    f"unsupported Snapshot qualification: {qualification!r}",
                )
            )
            continue

        if document.get("boundaries", {}).get("execution_input") is not True:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-RUNTIME-EXECUTION-REQUIRED",
                    "runtime-execution Snapshot must be marked as an execution input",
                )
            )
        parsed_report = supply_entry[2]
        required_capability = document.get("requirement_ref", {}).get("requirement_id")
        live_typed_evidence = False
        for evidence in parsed_report.conformance_evidence:
            if evidence.get("evidence_class") != "live":
                continue
            artifact_ref = evidence.get("artifact_ref")
            artifact_loaded = (
                _loaded_document_at(documents, artifact_ref.get("path"))
                if isinstance(artifact_ref, Mapping)
                else None
            )
            if (
                artifact_loaded is not None
                and isinstance(required_capability, str)
                and validate_evidence(
                    parsed_report.supply_identity,
                    evidence,
                    required_capability,
                )
                == "pass"
            ):
                live_typed_evidence = True
        availability_scope = parsed_report.availability.get("scope")
        fixture_only = (
            parsed_report.observation_scope == "synthetic-bounded-fixture"
            or (
                isinstance(availability_scope, Mapping)
                and availability_scope.get("scope_kind") == "fixture-only"
            )
        )
        if (
            fixture_only
            or not live_typed_evidence
        ):
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-RUNTIME-EVIDENCE-INELIGIBLE",
                    "runtime Snapshot requires non-fixture live typed capability evidence",
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


def _loaded_document_at(
    documents: Mapping[Path, Any], repository_relative: object
) -> tuple[Path, Mapping[str, Any]] | None:
    if not isinstance(repository_relative, str):
        return None
    for path, document in documents.items():
        if isinstance(document, Mapping) and _matches_repository_path(path, repository_relative):
            return path, document
    return None


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


def _validate_phase_b_evolution_gates(
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
            if isinstance(expected_hash, str) and _document_hash(documents, document_path) != expected_hash.removeprefix("sha256:").lower():
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
                matrix_content_hash=_document_hash(documents, matrix_path),
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
    issues.extend(_validate_skill_need_set(documents))
    issues.extend(_validate_protocol_profile_set(documents))
    issues.extend(_validate_method_resolutions(documents))
    issues.extend(_validate_skill_lifecycle_v2(documents))
    issues.extend(_validate_capability_supply_chain(documents))
    issues.extend(_validate_phase_b_evolution_gates(documents))
    issues.extend(_validate_research_mode_migrations(documents))
    issues.extend(_validate_decision_authority(documents))
    return issues


def load_and_validate(paths: Iterable[Path]) -> tuple[LoadedDocuments, list[ValidationIssue]]:
    documents = LoadedDocuments()
    issues: list[ValidationIssue] = []
    for path in paths:
        try:
            content = path.read_bytes()
            documents.add(
                path,
                load_document_bytes(path, content),
                sha256=hash_bytes(content),
            )
        except Exception as exc:  # parse errors are validation results at the CLI boundary
            issues.append(ValidationIssue(path, "PARSE-ERROR", str(exc)))
    issues.extend(validate_documents(documents))
    return documents, issues
