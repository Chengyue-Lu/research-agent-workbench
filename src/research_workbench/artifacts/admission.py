"""Source admission and provenance checks (M4-001).

Inbox content is mutable quarantine: it must never be citable.  Admission to
``sources/raw`` records the provenance sidecar demanded by module 07 §4 so an
admitted byte set can be re-located, licensed, and re-parsed later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from research_workbench.artifacts.integrity import (
    check_file_reference,
    hash_bytes,
)
from research_workbench.contracts.common import ContractError, require_relative_path, require_string
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.tasks.models import FileReference

INBOX_PATH_MARKER = "sources/inbox/"
RAW_PATH_PREFIX = "sources/raw/"


def normalized_relative(path: str) -> str:
    return require_relative_path(path, "path").replace("\\", "/")


def _within_zone(path: str, zone: str) -> bool:
    """Zone check that accepts both project-relative and repository-relative paths."""

    normalized = normalized_relative(path)
    return normalized.startswith(zone) or f"/{zone}" in f"/{normalized}"


def path_cites_inbox(path: str) -> bool:
    """Return True when a repository-relative path points into the inbox."""

    return _within_zone(path, INBOX_PATH_MARKER)


def inbox_citation_risk(path: str, field: str = "path") -> ContractRisk:
    return ContractRisk(
        "ARTIFACT-INBOX-CITED",
        RiskLevel.BLOCK,
        f"{field} cites un-admitted inbox content: {path}",
    )


@dataclass(frozen=True, slots=True)
class SourceAdmission:
    admission_id: str
    original_filename: str
    admitted_path: str
    sha256: str
    acquisition_uri: str | None
    acquisition_doi: str | None
    acquisition_device: str | None
    acquired_at: str
    operator: str
    license_or_data_use: str
    parser_name: str
    parser_version: str
    sensitivity: str
    egress_restriction: str
    derivatives: tuple[FileReference, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SourceAdmission":
        try:
            origin = data["acquisition"]["origin"]
            derivatives_raw = data.get("derivatives") or []
            return cls(
                admission_id=require_string(data, "admission_id"),
                original_filename=require_string(data, "original_filename"),
                admitted_path=require_relative_path(
                    require_string(data, "admitted_path"), "admitted_path"
                ).replace("\\", "/"),
                sha256=require_string(data, "sha256").removeprefix("sha256:").lower(),
                acquisition_uri=origin.get("uri"),
                acquisition_doi=origin.get("doi"),
                acquisition_device=origin.get("device"),
                acquired_at=require_string(data["acquisition"], "acquired_at"),
                operator=require_string(data["acquisition"], "operator"),
                license_or_data_use=require_string(data, "license_or_data_use"),
                parser_name=require_string(data["parser"], "name"),
                parser_version=require_string(data["parser"], "version"),
                sensitivity=require_string(data, "sensitivity"),
                egress_restriction=require_string(data, "egress_restriction"),
                derivatives=tuple(
                    FileReference.from_mapping(item) for item in derivatives_raw
                ),
            )
        except KeyError as exc:
            raise ContractError(str(exc.args[0]), "is required") from exc


def check_source_admission(root: str | Path, data: Mapping[str, Any]) -> list[ContractRisk]:
    """Deterministically verify one admission sidecar against live bytes."""

    risks: list[ContractRisk] = []
    admission = SourceAdmission.from_mapping(data)

    if not _within_zone(admission.admitted_path, RAW_PATH_PREFIX):
        risks.append(
            ContractRisk(
                "ARTIFACT-MISSING-PROVENANCE",
                RiskLevel.BLOCK,
                f"admitted_path must live under {RAW_PATH_PREFIX}: {admission.admitted_path}",
            )
        )
    if path_cites_inbox(admission.admitted_path):
        risks.append(inbox_citation_risk(admission.admitted_path, "admitted_path"))

    reference = FileReference(admission.admitted_path, admission.sha256)
    check = check_file_reference(root, reference)
    if check.status.value == "missing":
        risks.append(
            ContractRisk(
                "REF-MISSING", RiskLevel.BLOCK, f"admitted file is missing: {admission.admitted_path}"
            )
        )
    elif check.status.value in {"hash_mismatch", "outside_root"}:
        risks.append(
            ContractRisk(
                "ARTIFACT-HASH-MISMATCH",
                RiskLevel.BLOCK,
                f"admitted bytes differ from declared sha256: {admission.admitted_path}",
            )
        )

    origin_facts = [
        admission.acquisition_uri,
        admission.acquisition_doi,
        admission.acquisition_device,
    ]
    if not any(origin_facts):
        risks.append(
            ContractRisk(
                "ARTIFACT-MISSING-PROVENANCE",
                RiskLevel.BLOCK,
                f"{admission.admission_id}: acquisition.origin needs a uri, doi, or device",
            )
        )
    if _parse_datetime(admission.acquired_at) is None:
        risks.append(
            ContractRisk(
                "ARTIFACT-MISSING-PROVENANCE",
                RiskLevel.BLOCK,
                f"{admission.admission_id}: acquired_at must be an ISO-8601 timestamp",
            )
        )

    for derivative in admission.derivatives:
        if path_cites_inbox(derivative.path):
            risks.append(inbox_citation_risk(derivative.path, "derivatives.path"))
        derivative_check = check_file_reference(root, derivative)
        if derivative_check.status.value == "missing":
            risks.append(
                ContractRisk(
                    "REF-MISSING", RiskLevel.BLOCK, f"derivative is missing: {derivative.path}"
                )
            )
        elif derivative_check.status.value in {"hash_mismatch", "outside_root"}:
            risks.append(
                ContractRisk(
                    "ARTIFACT-HASH-MISMATCH",
                    RiskLevel.BLOCK,
                    f"derivative bytes differ from declared sha256: {derivative.path}",
                )
            )
    return risks


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def build_admission_mapping(
    *,
    original_filename: str,
    admitted_path: str,
    content: bytes,
    origin: Mapping[str, str],
    acquired_at: str,
    operator: str,
    license_or_data_use: str,
    parser_name: str,
    parser_version: str,
    sensitivity: str,
    egress_restriction: str,
    admission_id: str | None = None,
    derivatives: tuple[Mapping[str, str], ...] = (),
) -> dict[str, Any]:
    """Build a deterministic admission sidecar; no implicit timestamps."""

    if _parse_datetime(acquired_at) is None:
        raise ValueError("acquired_at must be an explicit ISO-8601 timestamp")
    if not any(origin.get(key) for key in ("uri", "doi", "device")):
        raise ValueError("origin must carry at least one of uri, doi, device")
    normalized_path = require_relative_path(admitted_path, "admitted_path").replace("\\", "/")
    if path_cites_inbox(normalized_path):
        raise ValueError(f"admitted_path must not cite inbox content: {normalized_path}")
    if not _within_zone(normalized_path, RAW_PATH_PREFIX):
        raise ValueError(f"admitted_path must live under {RAW_PATH_PREFIX}: {normalized_path}")
    digest = hash_bytes(content)
    return {
        "schema_version": "0.1.0",
        "admission_id": admission_id or f"SADM-{digest[:12].upper()}",
        "original_filename": original_filename,
        "admitted_path": normalized_path,
        "sha256": digest,
        "acquisition": {
            "origin": {key: value for key, value in origin.items() if value},
            "acquired_at": acquired_at,
            "operator": operator,
        },
        "license_or_data_use": license_or_data_use,
        "parser": {"name": parser_name, "version": parser_version},
        "sensitivity": sensitivity,
        "egress_restriction": egress_restriction,
        "derivatives": [dict(item) for item in derivatives],
    }


def sidecar_path_for(admitted_path: str) -> str:
    return f"{admitted_path}.admission.yaml"
