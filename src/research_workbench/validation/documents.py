"""Deterministic structural checks.

Passing these checks never implies scientific correctness. They only establish
that a document is legible, bounded, and internally referential enough for the
next stage of review.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Mapping

from research_workbench.artifacts.integrity import hash_bytes
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
from research_workbench.validation.authority_registry import validate_decision_authority
from research_workbench.validation.schemas import SchemaCatalog
from research_workbench.validation.capability_registry import (
    capability_requirement_entries as _capability_requirement_entries,
    validate_capability_requirement_set as _validate_capability_requirement_set,
)
from research_workbench.validation.capability_supply_registry import validate_capability_supply_chain
from research_workbench.validation.document_core import (
    LoadedDocuments,
    Severity,
    ValidationIssue,
    document_has_loaded_bytes as _document_has_loaded_bytes,
    document_hash as _document_hash,
    loaded_document_at as _loaded_document_at,
    matches_repository_path as _matches_repository_path,
)
from research_workbench.validation.document_kinds import infer_document_kind
from research_workbench.validation.method_resolution_registry import validate_method_resolutions
from research_workbench.validation.phase_b_gate import validate_phase_b_evolution_gates
from research_workbench.validation.research_state_registry import validate_research_state_set


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

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
    "phase_c_gate_manifest",
    "phase_c_gate_report",
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
    "runtime_bundle_manifest",
    "execution_binding",
    "execution_trace_fact",
    "execution_host_report",
    "execution_core_gate",
    "execution_policy",
    "generic_execution_receipt",
    "resolved_execution_view",
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
    "method_trace",
    "mode_action",
    "mode_action_registry",
    "context_snapshot",
    "execution_receipt",
    "research_object",
    "evaluation_manifest",
    "research_attempt_lineage",
    "research_failure",
    "research_state",
    "source_admission",
}


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


def _validate_evaluation_manifests(documents: Mapping[Path, Any]) -> list[ValidationIssue]:
    from research_workbench.evaluation.manifest import check_evaluation_manifest

    issues: list[ValidationIssue] = []
    for path, document in documents.items():
        if not isinstance(document, Mapping):
            continue
        if infer_document_kind(document) != "evaluation_manifest":
            continue
        for problem in check_evaluation_manifest(document):
            issues.append(ValidationIssue(path, "EVAL-MANIFEST-INVALID", problem))
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
    issues.extend(validate_method_resolutions(documents))
    issues.extend(_validate_skill_lifecycle_v2(documents))
    issues.extend(validate_capability_supply_chain(documents))
    issues.extend(validate_phase_b_evolution_gates(documents))
    issues.extend(_validate_research_mode_migrations(documents))
    issues.extend(validate_decision_authority(documents))
    issues.extend(validate_research_state_set(documents))
    issues.extend(_validate_evaluation_manifests(documents))
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
