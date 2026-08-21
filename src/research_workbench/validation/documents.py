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

from research_workbench.io import load_document
from research_workbench.artifacts.integrity import hash_file
from research_workbench.contracts.common import ContractError, parse_skill_reference
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
# Required fields for schema-backed documents come only from their JSON
# schemas. This table covers registry documents that intentionally have no
# dedicated schema.
DOCUMENT_REQUIRED: dict[str, tuple[str, ...]] = {
    "skill_sources": ("registry_kind", "sources"),
    "skill_candidates": ("registry_kind", "candidates"),
    "skill_accepted": ("registry_kind", "entries", "policy"),
    "provider_baselines": ("registry_kind", "providers"),
    "provider_adapters": ("registry_kind", "adapters"),
    "model_pool": ("registry_kind", "pool_id", "selection_policy", "slots"),
}

# Schema files are the single source of truth for schema-backed kinds.
SCHEMA_KINDS = frozenset(SchemaCatalog().document_kinds)


def infer_document_kind(document: Mapping[str, Any]) -> str | None:
    registry_kind = document.get("registry_kind")
    if isinstance(registry_kind, str):
        return registry_kind
    if "attempt_id" in document and "task_id" in document:
        if "result" in document:
            return "handoff_packet"
        if "started_at" in document and "task_revision" in document:
            return "attempt"
    if "completion_id" in document and "transaction_semantics" in document:
        return "attempt_completion_manifest"
    if "goal" in document and "task_id" in document:
        return "task_packet"
    if "project_id" in document and "active_modes" in document:
        return "project_protocol"
    if "mode_id" in document and "claim_rules" in document:
        return "research_mode"
    if "action_id" in document and "allowed_mechanisms" in document:
        return "mode_action"
    if "resolution_id" in document and "mechanism_resolutions" in document:
        return "method_resolution"
    if "snapshot_id" in document and "method_resolution_ref" in document and "bindings" in document:
        return "resolved_capability_snapshot"
    if "matrix_id" in document and "rules" in document:
        return "decision_authority"
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


def _resolve_contract_reference(document_path: Path, relative_path: str) -> Path | None:
    normalized = Path(*PurePosixPath(relative_path.replace("\\", "/")).parts)
    for ancestor in (document_path.parent, *document_path.parents):
        candidate = ancestor / normalized
        if candidate.is_file():
            return candidate
    return None


def _validate_pinned_contract_references(
    path: Path, document: Mapping[str, Any], kind: str
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    references: list[Mapping[str, Any]] = []
    path_key = "path"
    if kind == "research_mode" and document.get("schema_version") == "0.2.0":
        references = [item for item in document.get("action_refs", []) if isinstance(item, Mapping)]
    elif kind == "method_resolution":
        references = [
            item
            for item in document.get("action_selections", [])
            if isinstance(item, Mapping) and item.get("status") == "selected"
        ]
        path_key = "source_path"

    for index, reference in enumerate(references):
        relative_path = reference.get(path_key)
        expected_hash = reference.get("sha256")
        if not isinstance(relative_path, str) or not isinstance(expected_hash, str):
            continue
        resolved = _resolve_contract_reference(path, relative_path)
        pointer = "action_refs" if kind == "research_mode" else "action_selections"
        if resolved is None:
            issues.append(
                ValidationIssue(
                    path,
                    "METHOD-ACTION-REF-MISSING",
                    f"{pointer}[{index}] cannot resolve {relative_path}",
                )
            )
            continue
        actual_hash = hash_file(resolved)
        if actual_hash != expected_hash.removeprefix("sha256:").lower():
            issues.append(
                ValidationIssue(
                    path,
                    "METHOD-ACTION-REF-DRIFT",
                    f"{pointer}[{index}] hash differs for {relative_path}",
                )
            )
            continue
        referenced = load_document(resolved)
        for field in ("action_id", "mode_id", "version"):
            expected = reference.get(field)
            if expected is not None and referenced.get(field) != expected:
                issues.append(
                    ValidationIssue(
                        path,
                        "METHOD-ACTION-REF-IDENTITY",
                        f"{pointer}[{index}] {field} differs from {relative_path}",
                    )
                )
    if kind == "resolved_capability_snapshot":
        snapshot_refs: list[tuple[str, Mapping[str, Any]]] = []
        for field in ("task_ref", "method_resolution_ref"):
            value = document.get(field)
            if isinstance(value, Mapping):
                snapshot_refs.append((field, value))
        for index, binding in enumerate(document.get("bindings", [])):
            if isinstance(binding, Mapping) and isinstance(binding.get("source_ref"), Mapping):
                snapshot_refs.append((f"bindings[{index}].source_ref", binding["source_ref"]))
        for pointer, reference in snapshot_refs:
            relative_path = reference.get("path")
            expected_hash = reference.get("sha256")
            if not isinstance(relative_path, str) or not isinstance(expected_hash, str):
                continue
            resolved = _resolve_contract_reference(path, relative_path)
            if resolved is None:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-SNAPSHOT-REF-MISSING",
                        f"{pointer} cannot resolve {relative_path}",
                    )
                )
            elif hash_file(resolved) != expected_hash.removeprefix("sha256:").lower():
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-SNAPSHOT-REF-DRIFT",
                        f"{pointer} hash differs for {relative_path}",
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
        issues.extend(_validate_pinned_contract_references(path, document, kind))
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
