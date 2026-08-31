"""Fail-closed work artifact promotion (M4-002).

Promotion proves only that exact, checker-validated bytes are structurally
eligible for exclusive-copy publication.  It never accepts a Claim, records a
Human Decision, publishes a deliverable, or deletes the source workspace.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from research_workbench.artifacts.integrity import check_file_reference, hash_file, resolve_within_root
from research_workbench.contracts.common import ContractError, require_relative_path, require_string
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.io import load_document
from research_workbench.tasks.models import FileReference
from research_workbench.validation.schemas import SchemaCatalog

ALLOWED_TARGET_ZONES = ("objects", "runs", "deliverables/candidates")


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
    validation_report: FileReference
    operator: str
    entries: tuple[PromotionEntry, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PromotionRecord":
        report_raw = data.get("validation_report")
        entries_raw = data.get("entries")
        if not isinstance(report_raw, Mapping):
            raise ContractError("validation_report", "must be an object")
        if not isinstance(entries_raw, list) or not entries_raw:
            raise ContractError("entries", "must be a non-empty array")
        if any(not isinstance(item, Mapping) for item in entries_raw):
            raise ContractError("entries", "must contain only objects")
        return cls(
            require_string(data, "promotion_id"),
            _normalized_path(require_string(data, "source_workspace"), "source_workspace"),
            _file_reference(report_raw, "validation_report"),
            require_string(data, "operator"),
            tuple(PromotionEntry.from_mapping(item) for item in entries_raw),
        )


def _risk(code: str, message: str) -> ContractRisk:
    return ContractRisk(code, RiskLevel.BLOCK, message)


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


def _parse_report(root: Path, reference: FileReference) -> tuple[Mapping[str, Any] | None, list[ContractRisk]]:
    risks = _reference_risks(root, reference, "validation report")
    if risks:
        return None, risks
    path = resolve_within_root(root, reference.path)
    assert path is not None
    try:
        report = load_document(path)
    except Exception as exc:
        return None, [_risk("ARTIFACT-PROMOTION-BYPASS", f"validation report cannot be parsed: {exc}")]
    if not isinstance(report, Mapping):
        return None, [_risk("ARTIFACT-PROMOTION-BYPASS", "validation report must be an object")]
    errors = _schema_catalog().validate("deterministic_check_report", report)
    if errors:
        detail = "; ".join(f"{item.pointer}: {item.message}" for item in errors[:4])
        return None, [_risk("ARTIFACT-PROMOTION-BYPASS", f"validation report is schema-invalid: {detail}")]
    return report, []


def check_promotion(root: str | Path, data: Mapping[str, Any]) -> list[ContractRisk]:
    """Validate one promotion record and every live byte it authorizes."""

    root_path = Path(root).resolve()
    schema_errors = _schema_catalog().validate("promotion_record", data)
    if schema_errors:
        detail = "; ".join(f"{item.pointer}: {item.message}" for item in schema_errors[:4])
        return [_risk("ARTIFACT-PROMOTION-BYPASS", f"promotion record is schema-invalid: {detail}")]
    record = PromotionRecord.from_mapping(data)

    risks: list[ContractRisk] = []
    workspace_parts = _parts(record.source_workspace)
    if len(workspace_parts) != 3 or workspace_parts[0] != "work":
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

    report, report_risks = _parse_report(root_path, record.validation_report)
    risks.extend(report_risks)

    entry_keys: list[tuple[str, str]] = []
    entry_paths: list[str] = []
    targets: list[str] = []
    for entry in record.entries:
        artifact_path = _normalized_path(entry.artifact.path, "entries.artifact.path")
        entry_paths.append(artifact_path)
        entry_keys.append((artifact_path, entry.artifact.sha256))
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

    if len(entry_paths) != len(set(entry_paths)):
        risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "duplicate promotion entry artifact path"))
    if len(targets) != len(set(targets)):
        risks.append(_risk("ARTIFACT-OVERWRITE", "duplicate promotion target path"))

    if report is not None:
        if report.get("status") != "pass":
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "validation report status must be pass"))
        checker = report["checker"]
        risks.extend(
            _reference_risks(
                root_path,
                _file_reference(checker["source_ref"], "checker.source_ref"),
                "validation checker source",
            )
        )
        report_keys: list[tuple[str, str]] = []
        for item in report.get("subject_refs", []):
            subject = _file_reference(item, "subject_refs")
            subject_path = _normalized_path(subject.path, "subject_refs.path")
            report_keys.append((subject_path, subject.sha256))
            risks.extend(_reference_risks(root_path, subject, "validation report subject"))
        if len(report_keys) != len(set(report_keys)):
            risks.append(_risk("ARTIFACT-PROMOTION-BYPASS", "duplicate validation report subject"))
        if set(report_keys) != set(entry_keys) or len(report_keys) != len(entry_keys):
            risks.append(
                _risk(
                    "ARTIFACT-NEGATIVE-DROPPED",
                    "promotion entries must equal validation subjects by exact (path, sha256) set",
                )
            )
    return risks


@dataclass(frozen=True, slots=True)
class _StagedArtifact:
    temporary: Path
    target: Path
    expected_sha256: str


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


def execute_promotion(root: str | Path, data: Mapping[str, Any]) -> tuple[str, ...]:
    """Stage, revalidate, and exclusively publish every promoted entry."""

    root_path = Path(root).resolve()
    initial_risks = check_promotion(root_path, data)
    if initial_risks:
        raise ContractError("promotion", "; ".join(risk.message for risk in initial_risks))
    record = PromotionRecord.from_mapping(data)
    staged = _stage_promotions(root_path, record)
    try:
        final_risks = check_promotion(root_path, data)
        if final_risks:
            raise ContractError("promotion", "; ".join(risk.message for risk in final_risks))
        for item in staged:
            if resolve_within_root(root_path, item.target.relative_to(root_path).as_posix()) != item.target:
                raise ContractError("promotion", f"target boundary changed: {item.target}")
            if item.target.exists():
                raise ContractError("promotion", f"target appeared before publication: {item.target}")
            if hash_file(item.temporary) != item.expected_sha256:
                raise ContractError("promotion", f"staged bytes drifted before publication: {item.target}")
        _publish_staged(staged)
    except Exception:
        for item in staged:
            _best_effort_unlink(item.temporary)
        raise
    return tuple(entry.target for entry in record.entries if entry.disposition == "promote" and entry.target)


__all__ = ["PromotionEntry", "PromotionRecord", "check_promotion", "execute_promotion"]
