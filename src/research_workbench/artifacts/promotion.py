"""Work-to-object promotion checks and execution (M4-002).

Only validated work products may be promoted.  Accepted artifacts are never
overwritten in place, and negative results may not silently disappear from a
promotion decision.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from research_workbench.artifacts.admission import _within_zone
from research_workbench.artifacts.integrity import check_file_reference, resolve_within_root
from research_workbench.contracts.common import ContractError, require_relative_path, require_string
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.io import load_document
from research_workbench.tasks.models import FileReference

WORK_PATH_PREFIX = "work/"
PROMOTABLE_TARGET_PREFIXES = ("objects/", "runs/", "deliverables/")
PROMOTED = "promoted"
RETAINED = "retained-in-work"


@dataclass(frozen=True, slots=True)
class PromotionEntry:
    artifact: FileReference
    disposition: str
    negative_result: bool
    target: str | None
    reason: str | None


@dataclass(frozen=True, slots=True)
class PromotionRecord:
    promotion_id: str
    source_workspace: str
    validation_report: FileReference
    decided_by: str
    decided_at: str
    entries: tuple[PromotionEntry, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PromotionRecord":
        try:
            entries_raw = data["entries"]
            entries = tuple(
                PromotionEntry(
                    artifact=FileReference.from_mapping(item["artifact"]),
                    disposition=require_string(item, "disposition"),
                    negative_result=bool(item.get("negative_result", False)),
                    target=(
                        require_relative_path(item["target"], "target").replace("\\", "/")
                        if "target" in item
                        else None
                    ),
                    reason=item.get("reason"),
                )
                for item in entries_raw
            )
            return cls(
                promotion_id=require_string(data, "promotion_id"),
                source_workspace=require_relative_path(
                    require_string(data, "source_workspace"), "source_workspace"
                ).replace("\\", "/"),
                validation_report=FileReference.from_mapping(data["validation_report"]),
                decided_by=require_string(data, "decided_by"),
                decided_at=require_string(data, "decided_at"),
                entries=entries,
            )
        except KeyError as exc:
            raise ContractError(str(exc.args[0]), "is required") from exc


def _report_document(path: Path) -> Mapping[str, Any] | None:
    """Load and identify the validation report with lazily resolved validators."""

    from research_workbench.validation.documents import infer_document_kind
    from research_workbench.validation.schemas import SchemaCatalog

    try:
        report_document = load_document(path)
    except Exception as exc:
        raise ContractError("validation-report-unreadable", str(exc)) from exc
    if not isinstance(report_document, Mapping) or (
        infer_document_kind(report_document) != "deterministic_check_report"
    ):
        return None
    if SchemaCatalog().validate("deterministic_check_report", report_document):
        return None
    return report_document


def check_promotion(root: str | Path, data: Mapping[str, Any]) -> list[ContractRisk]:
    """Verify promotion eligibility without mutating anything."""

    risks: list[ContractRisk] = []
    record = PromotionRecord.from_mapping(data)

    if not _within_zone(record.source_workspace, WORK_PATH_PREFIX):
        risks.append(
            ContractRisk(
                "ARTIFACT-PROMOTION-BYPASS",
                RiskLevel.BLOCK,
                f"source_workspace must live under work/: {record.source_workspace}",
            )
        )

    report_path = resolve_within_root(root, record.validation_report.path)
    if report_path is None or not report_path.is_file():
        risks.append(
            ContractRisk(
                "REF-MISSING",
                RiskLevel.BLOCK,
                f"validation report is missing: {record.validation_report.path}",
            )
        )
        return risks
    try:
        report_document = _report_document(report_path)
    except ContractError as exc:
        risks.append(
            ContractRisk(
                "ARTIFACT-PROMOTION-BYPASS",
                RiskLevel.BLOCK,
                f"validation report is unreadable: {exc}",
            )
        )
        return risks
    if report_document is None:
        risks.append(
            ContractRisk(
                "ARTIFACT-PROMOTION-BYPASS",
                RiskLevel.BLOCK,
                "validation report must be a schema-valid deterministic_check_report document",
            )
        )
        return risks
    if report_document.get("status") != "pass":
        risks.append(
            ContractRisk(
                "ARTIFACT-PROMOTION-BYPASS",
                RiskLevel.BLOCK,
                f"validation report status is {report_document.get('status')!r}; "
                "only passing reports may promote",
            )
        )
        return risks

    subject_paths = {
        require_relative_path(subject["path"], "subject_refs.path").replace("\\", "/")
        for subject in report_document.get("subject_refs", [])
        if isinstance(subject, Mapping) and isinstance(subject.get("path"), str)
    }
    entry_paths = {entry.artifact.path for entry in record.entries}
    for uncovered in sorted(subject_paths - entry_paths):
        risks.append(
            ContractRisk(
                "ARTIFACT-NEGATIVE-DROPPED",
                RiskLevel.BLOCK,
                f"checked artifact absent from the promotion decision: {uncovered}",
            )
        )

    seen_targets: set[str] = set()
    for entry in record.entries:
        if not entry.artifact.path.startswith(record.source_workspace):
            risks.append(
                ContractRisk(
                    "ARTIFACT-PROMOTION-BYPASS",
                    RiskLevel.BLOCK,
                    f"entry artifact escapes source_workspace: {entry.artifact.path}",
                )
            )
        artifact_check = check_file_reference(root, entry.artifact)
        if artifact_check.status.value == "missing":
            risks.append(
                ContractRisk("REF-MISSING", RiskLevel.BLOCK, f"entry artifact is missing: {entry.artifact.path}")
            )
        elif artifact_check.status.value in {"hash_mismatch", "outside_root"}:
            risks.append(
                ContractRisk(
                    "ARTIFACT-HASH-MISMATCH",
                    RiskLevel.BLOCK,
                    f"entry artifact bytes differ from declared sha256: {entry.artifact.path}",
                )
            )
        if entry.disposition == PROMOTED:
            if entry.target is None:
                risks.append(
                    ContractRisk(
                        "ARTIFACT-PROMOTION-BYPASS",
                        RiskLevel.BLOCK,
                        f"promoted entry lacks target: {entry.artifact.path}",
                    )
                )
                continue
            if not any(
                _within_zone(entry.target, prefix) for prefix in PROMOTABLE_TARGET_PREFIXES
            ):
                risks.append(
                    ContractRisk(
                        "ARTIFACT-PROMOTION-BYPASS",
                        RiskLevel.BLOCK,
                        f"target must live under objects/, runs/, or deliverables/: {entry.target}",
                    )
                )
            if entry.target in seen_targets:
                risks.append(
                    ContractRisk(
                        "ARTIFACT-OVERWRITE",
                        RiskLevel.BLOCK,
                        f"two entries promote to the same target: {entry.target}",
                    )
                )
            seen_targets.add(entry.target)
            target_path = resolve_within_root(root, entry.target)
            if target_path is not None and target_path.exists():
                risks.append(
                    ContractRisk(
                        "ARTIFACT-OVERWRITE",
                        RiskLevel.BLOCK,
                        f"target already exists: {entry.target}",
                    )
                )
    return risks


def execute_promotion(root: str | Path, data: Mapping[str, Any]) -> list[str]:
    """Copy promoted artifacts into their targets after a fail-closed check."""

    risks = check_promotion(root, data)
    blocking = [risk for risk in risks if risk.level == RiskLevel.BLOCK]
    if blocking:
        raise ContractError(
            "promotion-blocked",
            "; ".join(f"{risk.code}: {risk.message}" for risk in blocking),
        )
    record = PromotionRecord.from_mapping(data)
    copied: list[str] = []
    for entry in record.entries:
        if entry.disposition != PROMOTED or entry.target is None:
            continue
        source_path = resolve_within_root(root, entry.artifact.path)
        target_path = resolve_within_root(root, entry.target)
        if source_path is None or target_path is None:
            raise ContractError("promotion-blocked", f"unresolvable paths for {entry.artifact.path}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target_path)
        copied.append(entry.target)
    return copied
