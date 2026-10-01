"""Fail-closed work artifact promotion (M4-002).

Promotion proves only that exact, checker-validated bytes are structurally
eligible for exclusive-copy publication.  It never accepts a Claim, records a
Human Decision, publishes a deliverable, or deletes the source workspace.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from research_workbench.artifacts.integrity import (
    check_file_reference,
    hash_bytes,
    hash_file,
    resolve_within_root,
)
from research_workbench.contracts.common import ContractError, require_relative_path, require_string
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.io import load_document, load_document_bytes
from research_workbench.tasks.models import FileReference
from research_workbench.validation.schemas import SchemaCatalog

ALLOWED_TARGET_ZONES = ("objects", "runs", "deliverables/candidates")
VALIDATION_POLICY_ZONE = "registry/validation-policies"
VALIDATION_AUTHORITY_REGISTRY_PATH = "registry/validation-policies/accepted.yaml"
VALIDATION_EXECUTION_ZONE = "runs/validation"
TASK_AUTHORITY_ZONE = "objects/tasks"
TRUSTED_VALIDATION_SOURCE_ZONES = ("src", "checks", ".github/scripts", "registry/validation-tools")


@lru_cache(maxsize=1)
def _schema_catalog() -> SchemaCatalog:
    return SchemaCatalog()


def _normalized_path(value: str, field: str) -> str:
    normalized = require_relative_path(value, field).replace("\\", "/")
    return PurePosixPath(normalized).as_posix()


def _parts(value: str) -> tuple[str, ...]:
    return tuple(PurePosixPath(value).parts)


def _strictly_within(path: str, parent: str) -> bool:
    path_parts = _parts(path)
    parent_parts = _parts(parent)
    return len(path_parts) > len(parent_parts) and path_parts[: len(parent_parts)] == parent_parts


def _within_zone(path: str, zone: str) -> bool:
    path_parts = _parts(path)
    zone_parts = _parts(zone)
    return len(path_parts) > len(zone_parts) and path_parts[: len(zone_parts)] == zone_parts


def _in_target_zone(path: str) -> bool:
    parts = _parts(path)
    return any(
        len(parts) > len(_parts(zone)) and parts[: len(_parts(zone))] == _parts(zone)
        for zone in ALLOWED_TARGET_ZONES
    )


def _file_reference(data: Mapping[str, Any], field: str) -> FileReference:
    reference = FileReference.from_mapping(data)
    return FileReference(
        _normalized_path(reference.path, f"{field}.path"),
        reference.sha256,
        reference.revision,
    )


@dataclass(frozen=True, slots=True)
class PromotionEntry:
    artifact: FileReference
    disposition: str
    negative_result: bool
    target: str | None
    reason: str | None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PromotionEntry":
        artifact_raw = data.get("artifact")
        if not isinstance(artifact_raw, Mapping):
            raise ContractError("entries.artifact", "must be an object")
        disposition = require_string(data, "disposition")
        negative_result = data.get("negative_result")
        if not isinstance(negative_result, bool):
            raise ContractError("entries.negative_result", "must be boolean")
        target_raw = data.get("target")
        target = (
            _normalized_path(target_raw, "entries.target")
            if isinstance(target_raw, str)
            else None
        )
        reason_raw = data.get("reason")
        reason = reason_raw if isinstance(reason_raw, str) and reason_raw.strip() else None
        return cls(
            _file_reference(artifact_raw, "entries.artifact"),
            disposition,
            negative_result,
            target,
            reason,
        )


@dataclass(frozen=True, slots=True)
class PromotionRecord:
    promotion_id: str
    source_workspace: str
    task_ref: FileReference
    validation_authority_registry: FileReference
    validation_report: FileReference
    validation_policy: FileReference
    validation_execution: FileReference
    operator: str
    recorded_at: datetime
    entries: tuple[PromotionEntry, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PromotionRecord":
        task_raw = data.get("task_ref")
        registry_raw = data.get("validation_authority_registry")
        report_raw = data.get("validation_report")
        policy_raw = data.get("validation_policy")
        execution_raw = data.get("validation_execution")
        entries_raw = data.get("entries")
        if not isinstance(task_raw, Mapping):
            raise ContractError("task_ref", "must be an object")
        if not isinstance(registry_raw, Mapping):
            raise ContractError("validation_authority_registry", "must be an object")
        if not isinstance(report_raw, Mapping):
            raise ContractError("validation_report", "must be an object")
        if not isinstance(policy_raw, Mapping):
            raise ContractError("validation_policy", "must be an object")
        if not isinstance(execution_raw, Mapping):
            raise ContractError("validation_execution", "must be an object")
        if not isinstance(entries_raw, list) or not entries_raw:
            raise ContractError("entries", "must be a non-empty array")
        if any(not isinstance(item, Mapping) for item in entries_raw):
            raise ContractError("entries", "must contain only objects")
        return cls(
            require_string(data, "promotion_id"),
            _normalized_path(require_string(data, "source_workspace"), "source_workspace"),
            _file_reference(task_raw, "task_ref"),
            _file_reference(registry_raw, "validation_authority_registry"),
            _file_reference(report_raw, "validation_report"),
            _file_reference(policy_raw, "validation_policy"),
            _file_reference(execution_raw, "validation_execution"),
            require_string(data, "operator"),
            _timestamp(require_string(data, "recorded_at"), "recorded_at"),
            tuple(PromotionEntry.from_mapping(item) for item in entries_raw),
        )


def _risk(code: str, message: str) -> ContractRisk:
    return ContractRisk(code, RiskLevel.BLOCK, message)


def _timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(field, "must be an ISO-8601 date-time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(field, "must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def _reference_risks(root: Path, reference: FileReference, label: str) -> list[ContractRisk]:
    check = check_file_reference(root, reference)
    if check.status.value == "ok":
        lexical = root.joinpath(*_parts(_normalized_path(reference.path, f"{label}.path")))
        if check.resolved_path != lexical:
            return [
                _risk(
                    "ARTIFACT-PROMOTION-BYPASS",
                    f"{label} traverses a symbolic-link boundary: {reference.path}",
                )
            ]
        return []
    if check.status.value == "missing":
        return [_risk("REF-MISSING", f"{label} is missing: {reference.path}")]
    if check.status.value == "outside_root":
        return [_risk("ARTIFACT-PROMOTION-BYPASS", f"{label} escapes project root: {reference.path}")]
    return [
        _risk(
            "ARTIFACT-HASH-MISMATCH",
            f"{label} bytes differ from declared sha256: {reference.path}",
        )
    ]


def _parse_referenced_document(
    root: Path,
    reference: FileReference,
    kind: str,
    label: str,
) -> tuple[Mapping[str, Any] | None, list[ContractRisk]]:
    risks = _reference_risks(root, reference, label)
    if risks:
        return None, risks
    path = resolve_within_root(root, reference.path)
    assert path is not None
    try:
        document = load_document(path)
    except Exception as exc:
        return None, [_risk("ARTIFACT-PROMOTION-BYPASS", f"{label} cannot be parsed: {exc}")]
    if not isinstance(document, Mapping):
        return None, [_risk("ARTIFACT-PROMOTION-BYPASS", f"{label} must be an object")]
    errors = _schema_catalog().validate(kind, document)
    if errors:
        detail = "; ".join(f"{item.pointer}: {item.message}" for item in errors[:4])
        return None, [_risk("ARTIFACT-PROMOTION-BYPASS", f"{label} is schema-invalid: {detail}")]
    return document, []


def _reference_key(reference: FileReference) -> tuple[str, str, int | None]:
    return reference.path, reference.sha256, reference.revision


def _reference_keys(items: Any, field: str) -> list[tuple[str, str, int | None]]:
    if not isinstance(items, list):
        raise ContractError(field, "must be an array")
    return [_reference_key(_file_reference(item, field)) for item in items]


def _component_binding(data: Any, kind: str) -> tuple[str, str, FileReference]:
    if not isinstance(data, Mapping):
        raise ContractError(kind, "must be an object")
    identity_field = {"checker": "checker_id", "runner": "runner_id", "host": "host_id"}[kind]
    source_raw = data.get("source_ref")
    if not isinstance(source_raw, Mapping):
        raise ContractError(f"{kind}.source_ref", "must be an object")
    return (
        require_string(data, identity_field),
        require_string(data, "version"),
        _file_reference(source_raw, f"{kind}.source_ref"),
    )


def _trusted_validation_source(path: str) -> bool:
    return any(_within_zone(path, zone) for zone in TRUSTED_VALIDATION_SOURCE_ZONES)


def _receipt_path(record: PromotionRecord) -> str:
    return f"runs/promotions/{record.promotion_id}/receipt.json"


def check_promotion(
    root: str | Path,
    data: Mapping[str, Any],
    *,
    record_reference: FileReference | None = None,
) -> list[ContractRisk]:
    """Validate promotion authority, execution evidence, and every live byte."""

    root_path = Path(root).resolve()
    schema_errors = _schema_catalog().validate("promotion_record", data)
    if schema_errors:
        detail = "; ".join(f"{item.pointer}: {item.message}" for item in schema_errors[:4])
        return [_risk("ARTIFACT-PROMOTION-BYPASS", f"promotion record is schema-invalid: {detail}")]
    record = PromotionRecord.from_mapping(data)

    risks: list[ContractRisk] = []
    workspace_parts = _parts(record.source_workspace)
    valid_workspace_shape = len(workspace_parts) == 3 and workspace_parts[0] == "work"
    if not valid_workspace_shape:
        risks.append(
            _risk(
                "ARTIFACT-PROMOTION-BYPASS",
                "source_workspace must be the exact work/<task>/<attempt> root",
            )
        )
    workspace = resolve_within_root(root_path, record.source_workspace)
    lexical_workspace = root_path.joinpath(*workspace_parts)
    if workspace is None or workspace != lexical_workspace or not workspace.is_dir():
        risks.append(
            _risk(
                "ARTIFACT-PROMOTION-BYPASS",
                f"source_workspace is missing or escapes root: {record.source_workspace}",
            )
        )

    if record_reference is not None:
        risks.extend(_reference_risks(root_path, record_reference, "promotion record"))
        if not _strictly_within(record_reference.path, record.source_workspace):
            risks.append(
                _risk(
                    "ARTIFACT-PROMOTION-BYPASS",
                    "executable promotion record must be an exact file inside source_workspace",
                )
            )

    task, task_risks = _parse_referenced_document(
        root_path,
        record.task_ref,
        "task_packet",
        "authoritative Task Packet",
    )
    authority_registry, registry_risks = _parse_referenced_document(
        root_path,
        record.validation_authority_registry,
        "promotion_validation_authority_registry",
        "accepted validation authority registry",
    )
    report, report_risks = _parse_referenced_document(
        root_path,
        record.validation_report,
        "deterministic_check_report",
        "validation report",
    )
    policy, policy_risks = _parse_referenced_document(
        root_path,
        record.validation_policy,
        "promotion_validation_policy",
        "accepted validation policy",
    )
    execution, execution_risks = _parse_referenced_document(
        root_path,
        record.validation_execution,
        "promotion_validation_execution",
        "validation execution record",
    )
    risks.extend(task_risks)
    risks.extend(registry_risks)
    risks.extend(report_risks)
    risks.extend(policy_risks)
    risks.extend(execution_risks)

    if not _strictly_within(record.validation_report.path, record.source_workspace):
        risks.append(
            _risk(
                "ARTIFACT-PROMOTION-BYPASS",
                "validation report must be an exact file inside source_workspace",
            )
        )
    if record.validation_authority_registry.path != VALIDATION_AUTHORITY_REGISTRY_PATH:
        risks.append(
            _risk(
                "ARTIFACT-PROMOTION-BYPASS",
                f"validation authority registry must be {VALIDATION_AUTHORITY_REGISTRY_PATH}",
            )
        )
    if not _within_zone(record.validation_policy.path, VALIDATION_POLICY_ZONE):
        risks.append(
            _risk(
                "ARTIFACT-PROMOTION-BYPASS",
                f"validation policy must be under {VALIDATION_POLICY_ZONE}/",
            )
        )
    if not _within_zone(record.validation_execution.path, VALIDATION_EXECUTION_ZONE):
        risks.append(
            _risk(
                "ARTIFACT-PROMOTION-BYPASS",
                f"validation execution must be under {VALIDATION_EXECUTION_ZONE}/",
            )
        )

    entry_keys: list[tuple[str, str, int | None]] = []
    entry_paths: list[str] = []
    targets: list[str] = []
    for entry in record.entries:
        artifact_path = _normalized_path(entry.artifact.path, "entries.artifact.path")
        entry_paths.append(artifact_path)
        entry_keys.append(_reference_key(entry.artifact))
        if not _strictly_within(artifact_path, record.source_workspace):
            risks.append(
                _risk(
                    "ARTIFACT-PROMOTION-BYPASS",
                    f"entry is outside its exact source workspace: {artifact_path}",
                )
            )
        risks.extend(_reference_risks(root_path, entry.artifact, "promotion entry"))
        if entry.disposition == "promote":
            if entry.target is None or not _in_target_zone(entry.target):
                risks.append(
                    _risk(
                        "ARTIFACT-PROMOTION-BYPASS",
                        f"target must be under objects/, runs/, or deliverables/candidates/: {entry.target}",
                    )
                )
                continue
            targets.append(entry.target)
            resolved_target = resolve_within_root(root_path, entry.target)
            lexical_target = root_path.joinpath(*_parts(entry.target))
            if resolved_target is None or resolved_target != lexical_target:
                risks.append(
                    _risk("ARTIFACT-PROMOTION-BYPASS", f"target escapes project root: {entry.target}")
                )
            elif resolved_target.exists():
                risks.append(_risk("ARTIFACT-OVERWRITE", f"target already exists: {entry.target}"))

    receipt_path = _receipt_path(record)
    receipt_target = resolve_within_root(root_path, receipt_path)
    lexical_receipt = root_path.joinpath(*_parts(receipt_path))
    if receipt_target is None or receipt_target != lexical_receipt:
        risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", f"receipt target escapes root: {receipt_path}"))
    elif receipt_target.exists():
        risks.append(_risk("ARTIFACT-OVERWRITE", f"receipt already exists: {receipt_path}"))
    if receipt_path in targets:
        risks.append(_risk("ARTIFACT-OVERWRITE", "promotion target collides with its receipt"))
    if len(entry_paths) != len(set(entry_paths)):
        risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "duplicate promotion entry artifact path"))
    if len(targets) != len(set(targets)):
        risks.append(_risk("ARTIFACT-OVERWRITE", "duplicate promotion target path"))

    report_keys: list[tuple[str, str, int | None]] = []
    report_checker: tuple[str, str, FileReference] | None = None
    if report is not None:
        if report.get("status") != "pass":
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "validation report status must be pass"))
        report_checker = _component_binding(report["checker"], "checker")
        risks.extend(_reference_risks(root_path, report_checker[2], "validation checker source"))
        report_keys = _reference_keys(report.get("subject_refs"), "subject_refs")
        for item in report.get("subject_refs", []):
            risks.extend(
                _reference_risks(
                    root_path,
                    _file_reference(item, "subject_refs"),
                    "validation report subject",
                )
            )
        if len(report_keys) != len(set(report_keys)):
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "duplicate validation report subject"))
        if set(report_keys) != set(entry_keys) or len(report_keys) != len(entry_keys):
            risks.append(
                _risk(
                    "ARTIFACT-NEGATIVE-DROPPED",
                    "promotion entries must equal validation subjects by exact file-reference set",
                )
            )

    policy_checker: tuple[str, str, FileReference] | None = None
    policy_runner: tuple[str, str, FileReference] | None = None
    registry_checker: tuple[str, str, FileReference] | None = None
    registry_runner: tuple[str, str, FileReference] | None = None
    registry_host: tuple[str, str, FileReference] | None = None

    task_revision: int | None = None
    if task is not None:
        revision = task.get("revision")
        task_revision = revision if isinstance(revision, int) else None
        if not valid_workspace_shape or task.get("task_id") != workspace_parts[1]:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "Task Packet is for another Task"))
        expected_task_path = (
            f"{TASK_AUTHORITY_ZONE}/{task.get('task_id')}/r{task_revision}/TASK.yaml"
            if task_revision is not None
            else ""
        )
        if record.task_ref.revision != task_revision or record.task_ref.path != expected_task_path:
            risks.append(
                _risk(
                    "ARTIFACT-PROMOTION-BYPASS",
                    "Task Packet must be revision-pinned at its canonical pre-Attempt authority path",
                )
            )
        input_keys = _reference_keys(task.get("input_refs"), "task.input_refs")
        if len(input_keys) != len(set(input_keys)):
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "Task Packet has duplicate input refs"))
        required_inputs = {
            _reference_key(record.validation_authority_registry),
            _reference_key(record.validation_policy),
        }
        if not required_inputs.issubset(set(input_keys)):
            risks.append(
                _risk(
                    "ARTIFACT-PROMOTION-BYPASS",
                    "Task Packet does not exact-pin the authority registry and accepted policy",
                )
            )
        write_scope = task.get("write_scope")
        if not isinstance(write_scope, list) or record.source_workspace not in write_scope:
            risks.append(
                _risk("ARTIFACT-PROMOTION-BYPASS", "Task Packet does not bind the source workspace")
            )
        elif any(
            not isinstance(scope, str)
            or not (scope == record.source_workspace or _strictly_within(scope, record.source_workspace))
            for scope in write_scope
        ):
            risks.append(
                _risk(
                    "ARTIFACT-PROMOTION-BYPASS",
                    "Task write_scope reaches outside the exact source workspace",
                )
            )

    registry_entry: Mapping[str, Any] | None = None
    if authority_registry is not None and valid_workspace_shape and task_revision is not None:
        matching_entries = [
            entry
            for entry in authority_registry.get("accepted_policies", [])
            if isinstance(entry, Mapping)
            and entry.get("task_id") == workspace_parts[1]
            and entry.get("task_revision") == task_revision
        ]
        if len(matching_entries) != 1:
            risks.append(
                _risk(
                    "ARTIFACT-PROMOTION-BYPASS",
                    "authority registry must contain exactly one accepted policy for the Task revision",
                )
            )
        else:
            registry_entry = matching_entries[0]
            registry_policy_ref = _file_reference(registry_entry["policy_ref"], "policy_ref")
            if registry_policy_ref != record.validation_policy:
                risks.append(
                    _risk("ARTIFACT-PROMOTION-BYPASS", "authority registry accepts another policy")
                )
            registry_checker = _component_binding(registry_entry["checker"], "checker")
            registry_runner = _component_binding(registry_entry["runner"], "runner")
            registry_host = _component_binding(registry_entry["host"], "host")
            for binding, label in (
                (registry_checker, "registry checker"),
                (registry_runner, "registry runner"),
                (registry_host, "registry validation host"),
            ):
                risks.extend(_reference_risks(root_path, binding[2], label))
                if not _trusted_validation_source(binding[2].path):
                    risks.append(
                        _risk(
                            "ARTIFACT-PROMOTION-BYPASS",
                            f"{label} must be exact-pinned from a repository-governed source zone",
                        )
                    )

    if policy is not None:
        policy_checker = _component_binding(policy["checker"], "checker")
        policy_runner = _component_binding(policy["runner"], "runner")
        for binding, label in ((policy_checker, "policy checker"), (policy_runner, "policy runner")):
            risks.extend(_reference_risks(root_path, binding[2], label))
            if not _trusted_validation_source(binding[2].path):
                risks.append(
                    _risk(
                        "ARTIFACT-PROMOTION-BYPASS",
                        f"{label} must be exact-pinned from a repository-governed source zone",
                    )
                )
        if valid_workspace_shape and policy.get("task_id") != workspace_parts[1]:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "validation policy is for another Task"))
        if report_checker is not None and policy_checker != report_checker:
            risks.append(
                _risk(
                    "ARTIFACT-PROMOTION-BYPASS",
                    "report checker identity/version/source pin differs from accepted policy",
                )
            )
        if registry_checker is not None and policy_checker != registry_checker:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "policy checker differs from registry"))
        if registry_runner is not None and policy_runner != registry_runner:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "policy runner differs from registry"))

    if execution is not None:
        execution_checker = _component_binding(execution["checker"], "checker")
        execution_runner = _component_binding(execution["runner"], "runner")
        execution_host = _component_binding(execution["host"], "host")
        for binding, label in (
            (execution_checker, "execution checker"),
            (execution_runner, "execution runner"),
            (execution_host, "execution validation host"),
        ):
            risks.extend(_reference_risks(root_path, binding[2], label))
            if not _trusted_validation_source(binding[2].path):
                risks.append(
                    _risk(
                        "ARTIFACT-PROMOTION-BYPASS",
                        f"{label} must be exact-pinned from a repository-governed source zone",
                    )
                )
        if execution.get("outcome") != "pass":
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "validation execution outcome must be pass"))
        if valid_workspace_shape:
            if execution.get("task_id") != workspace_parts[1]:
                risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "validation execution is for another Task"))
            if execution.get("attempt_id") != workspace_parts[2]:
                risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "validation execution is for another Attempt"))
        execution_task_ref = _file_reference(execution["task_ref"], "task_ref")
        execution_registry_ref = _file_reference(
            execution["authority_registry_ref"], "authority_registry_ref"
        )
        execution_policy_ref = _file_reference(execution["policy_ref"], "policy_ref")
        execution_report_ref = _file_reference(execution["report_ref"], "report_ref")
        if execution_task_ref != record.task_ref:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "execution does not exact-pin the Task"))
        if execution_registry_ref != record.validation_authority_registry:
            risks.append(
                _risk("ARTIFACT-PROMOTION-BYPASS", "execution does not exact-pin the authority registry")
            )
        if execution_policy_ref != record.validation_policy:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "execution does not exact-pin the accepted policy"))
        if execution_report_ref != record.validation_report:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "execution does not exact-pin the PASS report"))
        execution_keys = _reference_keys(execution.get("subject_refs"), "subject_refs")
        if len(execution_keys) != len(set(execution_keys)):
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "duplicate validation execution subject"))
        if set(execution_keys) != set(entry_keys) or len(execution_keys) != len(entry_keys):
            risks.append(
                _risk(
                    "ARTIFACT-PROMOTION-BYPASS",
                    "validation execution subjects differ from promotion entries",
                )
            )
        for item in execution.get("subject_refs", []):
            risks.extend(
                _reference_risks(
                    root_path,
                    _file_reference(item, "subject_refs"),
                    "validation execution subject",
                )
            )
        if policy_checker is not None and execution_checker != policy_checker:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "execution checker differs from policy"))
        if policy_runner is not None and execution_runner != policy_runner:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "execution runner differs from policy"))
        if registry_checker is not None and execution_checker != registry_checker:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "execution checker differs from registry"))
        if registry_runner is not None and execution_runner != registry_runner:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "execution runner differs from registry"))
        if registry_host is not None and execution_host != registry_host:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "execution host differs from registry"))
        if execution.get("executor") != execution_host[0]:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "executor differs from validation host"))
        if report_checker is not None and execution_checker != report_checker:
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "execution checker differs from report"))
        started_at = _timestamp(str(execution["started_at"]), "validation_execution.started_at")
        finished_at = _timestamp(str(execution["finished_at"]), "validation_execution.finished_at")
        if finished_at < started_at:
            risks.append(
                _risk("ARTIFACT-PROMOTION-BYPASS", "validation execution finishes before it starts")
            )
        if registry_entry is not None:
            accepted_at = _timestamp(str(registry_entry["accepted_at"]), "accepted_at")
            if accepted_at > started_at:
                risks.append(
                    _risk(
                        "ARTIFACT-PROMOTION-BYPASS",
                        "validation authority was not accepted before execution started",
                    )
                )
        if finished_at > record.recorded_at:
            risks.append(
                _risk(
                    "ARTIFACT-PROMOTION-BYPASS",
                    "promotion record predates completion of its validation execution",
                )
            )

    host_receipt: Mapping[str, Any] | None = None
    if execution is not None:
        host_receipt_ref = _file_reference(execution["host_receipt_ref"], "host_receipt_ref")
        host_receipt, host_receipt_risks = _parse_referenced_document(
            root_path,
            host_receipt_ref,
            "promotion_validation_host_receipt",
            "validation host receipt",
        )
        risks.extend(host_receipt_risks)
        if not _within_zone(host_receipt_ref.path, VALIDATION_EXECUTION_ZONE):
            risks.append(
                _risk(
                    "VALIDATION-EXECUTION-UNPROVEN",
                    f"validation host receipt must be under {VALIDATION_EXECUTION_ZONE}/",
                )
            )
        if host_receipt is not None and report is not None:
            from research_workbench.artifacts.validation_host import check_host_receipt_closure

            risks.extend(
                check_host_receipt_closure(root_path, record, report, execution, host_receipt)
            )
    if not risks and execution is not None and report is not None and host_receipt is not None:
        from research_workbench.artifacts.validation_host import reexecute_validation

        risks.extend(reexecute_validation(root_path, record, report, execution, host_receipt))
    return risks


@dataclass(frozen=True, slots=True)
class _StagedArtifact:
    temporary: Path
    target: Path
    expected_sha256: str


@dataclass(frozen=True, slots=True)
class PromotionExecutionResult:
    targets: tuple[str, ...]
    receipt: str


def _best_effort_unlink(path: Path) -> None:
    """Remove a staging file without masking the promotion outcome."""

    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _stage_promotions(root: Path, record: PromotionRecord) -> list[_StagedArtifact]:
    staged: list[_StagedArtifact] = []
    try:
        for entry in record.entries:
            if entry.disposition != "promote" or entry.target is None:
                continue
            source = resolve_within_root(root, entry.artifact.path)
            target = resolve_within_root(root, entry.target)
            if source is None or target is None:
                raise ContractError("promotion", "source or target escaped the project root")
            target.parent.mkdir(parents=True, exist_ok=True)
            target_after_mkdir = resolve_within_root(root, entry.target)
            if target_after_mkdir != target or target.exists():
                raise ContractError("promotion", f"target boundary changed or exists: {entry.target}")
            temporary_path: Path | None = None
            digest = hashlib.sha256()
            try:
                with source.open("rb") as input_stream, tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=target.parent,
                    prefix=f".{target.name}.promotion-",
                    suffix=".tmp",
                    delete=False,
                ) as output_stream:
                    temporary_path = Path(output_stream.name)
                    for block in iter(lambda: input_stream.read(1024 * 1024), b""):
                        digest.update(block)
                        output_stream.write(block)
                    output_stream.flush()
                    os.fsync(output_stream.fileno())
                if digest.hexdigest() != entry.artifact.sha256:
                    raise ContractError("promotion", f"source bytes drifted while staging: {entry.artifact.path}")
                staged.append(_StagedArtifact(temporary_path, target, entry.artifact.sha256))
            except Exception:
                if temporary_path is not None:
                    _best_effort_unlink(temporary_path)
                raise
        return staged
    except Exception:
        for item in staged:
            _best_effort_unlink(item.temporary)
        raise


def _stage_bytes(root: Path, target_path: str, content: bytes) -> _StagedArtifact:
    target = resolve_within_root(root, target_path)
    if target is None:
        raise ContractError("promotion", f"receipt target escaped root: {target_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if resolve_within_root(root, target_path) != target or target.exists():
        raise ContractError("promotion", f"receipt boundary changed or exists: {target_path}")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.promotion-",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return _StagedArtifact(temporary_path, target, hash_bytes(content))
    except Exception:
        if temporary_path is not None:
            _best_effort_unlink(temporary_path)
        raise


def _publish_staged(staged: list[_StagedArtifact]) -> None:
    published: list[_StagedArtifact] = []
    try:
        for item in staged:
            os.link(item.temporary, item.target)
            published.append(item)
    except Exception:
        for item in reversed(published):
            try:
                if item.target.exists() and os.path.samefile(item.target, item.temporary):
                    item.target.unlink()
            except OSError:
                pass
        raise
    finally:
        for item in staged:
            _best_effort_unlink(item.temporary)


def _reference_mapping(reference: FileReference) -> dict[str, Any]:
    mapping: dict[str, Any] = {"path": reference.path, "sha256": reference.sha256}
    if reference.revision is not None:
        mapping["revision"] = reference.revision
    return mapping


def load_promotion_record(
    root: Path,
    record_path: str | Path,
) -> tuple[Mapping[str, Any], FileReference]:
    """Read and hash one exact file-bound promotion record below ``root``."""

    if isinstance(record_path, Mapping):
        raise ContractError("promotion", "operation requires a file-bound promotion record")
    raw_path = Path(record_path)
    lexical = raw_path if raw_path.is_absolute() else root / raw_path
    lexical = Path(os.path.abspath(lexical))
    resolved = lexical.resolve()
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ContractError("promotion", "promotion record is outside the project root") from exc
    if os.path.normcase(str(lexical)) != os.path.normcase(str(resolved)):
        raise ContractError("promotion", "promotion record traverses a symbolic-link boundary")
    if not resolved.is_file():
        raise ContractError("promotion", f"promotion record is missing: {relative}")
    content = resolved.read_bytes()
    try:
        document = load_document_bytes(resolved, content)
    except Exception as exc:
        raise ContractError("promotion", f"promotion record cannot be parsed: {exc}") from exc
    if not isinstance(document, Mapping):
        raise ContractError("promotion", "promotion record must be an object")
    return document, FileReference(relative, hash_bytes(content))


def _build_receipt(
    record: PromotionRecord,
    record_reference: FileReference,
    report: Mapping[str, Any],
    execution: Mapping[str, Any],
    executed_at: str,
) -> Mapping[str, Any]:
    source_refs = [_reference_mapping(entry.artifact) for entry in record.entries]
    target_refs = [
        {
            "source_ref": _reference_mapping(entry.artifact),
            "target_ref": {
                "path": entry.target,
                "sha256": entry.artifact.sha256,
            },
        }
        for entry in record.entries
        if entry.disposition == "promote" and entry.target is not None
    ]
    checker_id, checker_version, checker_source = _component_binding(report["checker"], "checker")
    runner_id, runner_version, runner_source = _component_binding(execution["runner"], "runner")
    host_id, host_version, host_source = _component_binding(execution["host"], "host")
    return {
        "schema_version": "0.1.0",
        "receipt_id": f"{record.promotion_id}-RECEIPT",
        "promotion_id": record.promotion_id,
        "promotion_record_ref": _reference_mapping(record_reference),
        "task_ref": _reference_mapping(record.task_ref),
        "validation_authority_registry_ref": _reference_mapping(
            record.validation_authority_registry
        ),
        "validation_policy_ref": _reference_mapping(record.validation_policy),
        "validation_execution_ref": _reference_mapping(record.validation_execution),
        "validation_report_ref": _reference_mapping(record.validation_report),
        "checker": {
            "checker_id": checker_id,
            "version": checker_version,
            "source_ref": _reference_mapping(checker_source),
        },
        "runner": {
            "runner_id": runner_id,
            "version": runner_version,
            "source_ref": _reference_mapping(runner_source),
        },
        "host": {
            "host_id": host_id,
            "version": host_version,
            "source_ref": _reference_mapping(host_source),
        },
        "source_artifact_refs": source_refs,
        "target_artifact_refs": target_refs,
        "operator": record.operator,
        "executed_at": executed_at,
        "outcome": "succeeded",
        "authority_boundaries": {
            "structural_copy_fact_only": True,
            "claim_acceptance": False,
            "human_decision": False,
            "publication": False,
            "scientific_correctness": False,
            "source_deletion": False,
        },
    }


def execute_promotion(
    root: str | Path,
    record_path: str | Path,
    *,
    executed_at: str | None = None,
) -> PromotionExecutionResult:
    """Publish exact targets and one durable receipt from a file-bound record."""

    root_path = Path(root).resolve()
    data, record_reference = load_promotion_record(root_path, record_path)
    initial_risks = check_promotion(root_path, data, record_reference=record_reference)
    if initial_risks:
        raise ContractError("promotion", "; ".join(risk.message for risk in initial_risks))
    record = PromotionRecord.from_mapping(data)
    staged = _stage_promotions(root_path, record)
    try:
        final_risks = check_promotion(root_path, data, record_reference=record_reference)
        if final_risks:
            raise ContractError("promotion", "; ".join(risk.message for risk in final_risks))
        for item in staged:
            if resolve_within_root(root_path, item.target.relative_to(root_path).as_posix()) != item.target:
                raise ContractError("promotion", f"target boundary changed: {item.target}")
            if item.target.exists():
                raise ContractError("promotion", f"target appeared before publication: {item.target}")
            if hash_file(item.temporary) != item.expected_sha256:
                raise ContractError("promotion", f"staged bytes drifted before publication: {item.target}")
        report, report_risks = _parse_referenced_document(
            root_path,
            record.validation_report,
            "deterministic_check_report",
            "validation report",
        )
        if report is None or report_risks:
            raise ContractError("promotion", "validation report drifted before receipt creation")
        execution, execution_risks = _parse_referenced_document(
            root_path,
            record.validation_execution,
            "promotion_validation_execution",
            "validation execution record",
        )
        if execution is None or execution_risks:
            raise ContractError("promotion", "validation execution drifted before receipt creation")
        execution_time = executed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if _timestamp(execution_time, "executed_at") < record.recorded_at:
            raise ContractError("executed_at", "must not predate the promotion record")
        receipt = _build_receipt(record, record_reference, report, execution, execution_time)
        receipt_errors = _schema_catalog().validate("promotion_execution_receipt", receipt)
        if receipt_errors:
            detail = "; ".join(f"{item.pointer}: {item.message}" for item in receipt_errors[:4])
            raise ContractError("promotion", f"generated receipt is schema-invalid: {detail}")
        receipt_bytes = (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
        staged.append(_stage_bytes(root_path, _receipt_path(record), receipt_bytes))
        commit_risks = check_promotion(root_path, data, record_reference=record_reference)
        if commit_risks:
            raise ContractError("promotion", "; ".join(risk.message for risk in commit_risks))
        for item in staged:
            if hash_file(item.temporary) != item.expected_sha256:
                raise ContractError("promotion", f"staged bytes drifted before publication: {item.target}")
        _publish_staged(staged)
    except Exception:
        for item in staged:
            _best_effort_unlink(item.temporary)
        raise
    return PromotionExecutionResult(
        tuple(entry.target for entry in record.entries if entry.disposition == "promote" and entry.target),
        _receipt_path(record),
    )


__all__ = [
    "PromotionEntry",
    "PromotionExecutionResult",
    "PromotionRecord",
    "check_promotion",
    "execute_promotion",
    "load_promotion_record",
]
