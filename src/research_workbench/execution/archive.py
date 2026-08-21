"""Marker-last closeout and file-only replay for one model-api Attempt.

This adapter consumes the legacy Skill-bound Attempt/Receipt contracts and the
M3-008 Trace Core. It does not resolve Method, Mode, Skill, Claim, or Human
Gate semantics.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.contracts import ContractError, ContractRisk, RiskLevel
from research_workbench.io import load_document
from research_workbench.observability.models import (
    ExecutionReceipt,
    check_execution_receipt,
)
from research_workbench.observability.trace import (
    TRACE_INDEX_FILENAME,
    derive_session_transcript,
    validate_attempt_trace,
)
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import AttemptRecord, FileReference
from research_workbench.validation.relationships import check_references
from research_workbench.validation.schemas import SchemaCatalog

ATTEMPT_FILENAME = "attempt.yaml"
RECEIPT_FILENAME = "execution-receipt.yaml"
TRANSCRIPT_FILENAME = "session-transcript.json"
COMPLETION_MANIFEST_FILENAME = "completion-manifest.yaml"


@dataclass(frozen=True, slots=True)
class ArchiveCloseoutResult:
    attempt_dir: Path
    completion_manifest: Path | None
    risks: tuple[ContractRisk, ...]

    @property
    def blocked(self) -> bool:
        return any(risk.level == RiskLevel.BLOCK for risk in self.risks)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _risk(code: str, message: str) -> ContractRisk:
    return ContractRisk(code, RiskLevel.BLOCK, message)


def _dedupe(risks: list[ContractRisk]) -> tuple[ContractRisk, ...]:
    seen: set[tuple[str, str, str]] = set()
    result: list[ContractRisk] = []
    for risk in risks:
        key = (risk.code, str(risk.level), risk.message)
        if key not in seen:
            seen.add(key)
            result.append(risk)
    return tuple(result)


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _publish_exclusive(path: Path, payload: bytes) -> None:
    """Publish one closeout artifact without overwriting an existing file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _yaml_payload(document: Mapping[str, Any]) -> bytes:
    return yaml.safe_dump(
        dict(document), sort_keys=False, allow_unicode=True
    ).encode("utf-8")


def _json_payload(document: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _schema_risks(kind: str, document: Mapping[str, Any]) -> list[ContractRisk]:
    return [
        _risk(
            "EXEC-ARCHIVE-INVALID",
            f"{kind}{error.pointer}: {error.message}",
        )
        for error in SchemaCatalog().validate(kind, document)
    ]


def _load_mapping(path: Path, label: str, risks: list[ContractRisk]) -> Mapping[str, Any] | None:
    try:
        document = load_document(path)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        risks.append(_risk("EXEC-ARCHIVE-INVALID", f"{label} cannot be read: {exc}"))
        return None
    if not isinstance(document, Mapping):
        risks.append(_risk("EXEC-ARCHIVE-INVALID", f"{label} is not an object"))
        return None
    return document


def _with_reference(
    document: Mapping[str, Any],
    *,
    field: str,
    reference: Mapping[str, str],
) -> dict[str, Any]:
    result = dict(document)
    result[field] = dict(reference)
    return result


def _with_unique_path(
    document: Mapping[str, Any],
    *,
    field: str,
    relative: str,
) -> dict[str, Any]:
    result = dict(document)
    values = list(result.get(field, []))
    if relative not in values:
        values.append(relative)
    result[field] = values
    return result


def finalize_execution_archive(
    *,
    root: str | Path,
    attempt_dir: str | Path,
    attempt_document: Mapping[str, Any],
    receipt_document: Mapping[str, Any],
    protocol: str | Path,
) -> ArchiveCloseoutResult:
    """Publish Attempt/Receipt/transcript, then commit with a last marker.

    If any deterministic validation blocks, the function leaves no completion
    marker. Already published closeout files are an uncommitted failed Attempt
    and must not be reused by a later process.
    """

    project_root = Path(root).resolve()
    raw_attempt = Path(attempt_dir)
    directory = raw_attempt if raw_attempt.is_absolute() else project_root / raw_attempt
    directory = directory.resolve()
    try:
        directory.relative_to(project_root)
    except ValueError as exc:
        raise ContractError("attempt_dir", "must stay within the project root") from exc

    marker_path = directory / COMPLETION_MANIFEST_FILENAME
    if marker_path.exists():
        raise FileExistsError("Attempt already has a completion marker; verify it instead")
    for filename in (ATTEMPT_FILENAME, RECEIPT_FILENAME, TRANSCRIPT_FILENAME):
        if (directory / filename).exists():
            raise FileExistsError(f"uncommitted closeout artifact already exists: {filename}")

    risks = list(validate_attempt_trace(project_root, directory).risks)
    if any(risk.level == RiskLevel.BLOCK for risk in risks):
        return ArchiveCloseoutResult(directory, None, _dedupe(risks))

    trace_index = directory / TRACE_INDEX_FILENAME
    trace_reference = {
        "path": _relative(project_root, trace_index),
        "sha256": hash_file(trace_index),
    }
    transcript_path = directory / TRANSCRIPT_FILENAME
    transcript_relative = _relative(project_root, transcript_path)
    transcript_document = {
        "schema_version": "0.1.0",
        "source": "agent-trace-derived-view",
        "attempt_id": str(attempt_document.get("attempt_id", "")),
        "turns": list(derive_session_transcript(directory)),
    }

    attempt_path = directory / ATTEMPT_FILENAME
    receipt_path = directory / RECEIPT_FILENAME
    attempt_relative = _relative(project_root, attempt_path)
    receipt_relative = _relative(project_root, receipt_path)

    attempt_mapping = _with_reference(
        attempt_document, field="trace_ref", reference=trace_reference
    )
    attempt_mapping["execution_receipt_ref"] = receipt_relative
    attempt_mapping = _with_unique_path(
        attempt_mapping, field="artifact_refs", relative=transcript_relative
    )

    receipt_mapping = _with_reference(
        receipt_document, field="trace_ref", reference=trace_reference
    )
    receipt_mapping["attempt_ref"] = attempt_relative
    receipt_mapping = _with_unique_path(
        receipt_mapping, field="output_refs", relative=transcript_relative
    )

    risks.extend(_schema_risks("attempt", attempt_mapping))
    risks.extend(_schema_risks("execution_receipt", receipt_mapping))
    try:
        AttemptRecord.from_mapping(attempt_mapping)
        receipt = ExecutionReceipt.from_mapping(receipt_mapping)
    except ContractError as exc:
        risks.append(_risk("EXEC-ARCHIVE-INVALID", str(exc)))
        return ArchiveCloseoutResult(directory, None, _dedupe(risks))
    if receipt.execution_kind != "model-api":
        risks.append(
            _risk(
                "EXEC-ARCHIVE-INVALID",
                "Trace Adapter closeout only accepts execution_kind=model-api",
            )
        )
    if any(risk.level == RiskLevel.BLOCK for risk in risks):
        return ArchiveCloseoutResult(directory, None, _dedupe(risks))

    _publish_exclusive(transcript_path, _json_payload(transcript_document))
    _publish_exclusive(attempt_path, _yaml_payload(attempt_mapping))
    _publish_exclusive(receipt_path, _yaml_payload(receipt_mapping))

    protocol_path = Path(protocol)
    if protocol_path.is_absolute():
        try:
            protocol_path = protocol_path.resolve()
            protocol_path.relative_to(project_root)
        except ValueError:
            protocol_path = Path()
    else:
        resolved_protocol = resolve_within_root(project_root, str(protocol_path))
        protocol_path = resolved_protocol if resolved_protocol is not None else Path()
    protocol_document = (
        _load_mapping(protocol_path, "Project Protocol", risks)
        if protocol_path.is_file()
        else None
    )
    if protocol_document is None and not protocol_path.is_file():
        risks.append(_risk("EXEC-ARCHIVE-INVALID", "Project Protocol is missing or outside root"))
    if protocol_document is not None:
        try:
            project_protocol = ProjectProtocol.from_mapping(protocol_document)
            risks.extend(
                check_execution_receipt(
                    receipt,
                    project_protocol,
                    root=project_root,
                    receipt_ref=receipt_relative,
                )
            )
        except ContractError as exc:
            risks.append(_risk("EXEC-ARCHIVE-INVALID", str(exc)))
    if any(risk.level == RiskLevel.BLOCK for risk in risks):
        return ArchiveCloseoutResult(directory, None, _dedupe(risks))

    committed_files = tuple(
        path
        for path in sorted(directory.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file()
        and path.name != COMPLETION_MANIFEST_FILENAME
        and not path.name.endswith(".tmp")
    )
    symlinks = [path for path in committed_files if path.is_symlink()]
    if symlinks:
        risks.append(
            _risk(
                "EXEC-ARCHIVE-INVALID",
                "Attempt archive contains symlinks: "
                + ", ".join(path.name for path in symlinks),
            )
        )
        return ArchiveCloseoutResult(directory, None, _dedupe(risks))
    manifest = {
        "schema_version": "0.1.0",
        "completion_id": f"CM-{attempt_mapping['attempt_id']}",
        "attempt_id": attempt_mapping["attempt_id"],
        "status": receipt_mapping["status"],
        "files": [
            {"path": _relative(project_root, path), "sha256": hash_file(path)}
            for path in committed_files
        ],
        "transaction_semantics": "marker-last",
        "committed_at": _now(),
    }
    manifest_risks = _schema_risks("attempt_completion_manifest", manifest)
    risks.extend(manifest_risks)
    if manifest_risks:
        return ArchiveCloseoutResult(directory, None, _dedupe(risks))
    _publish_exclusive(marker_path, _yaml_payload(manifest))
    return ArchiveCloseoutResult(directory, marker_path, _dedupe(risks))


def verify_execution_archive(
    attempt_dir: str | Path,
    *,
    root: str | Path,
    protocol: str | Path,
) -> tuple[ContractRisk, ...]:
    """Replay a committed closeout using only files and hashes."""

    project_root = Path(root).resolve()
    raw_attempt = Path(attempt_dir)
    directory = raw_attempt if raw_attempt.is_absolute() else project_root / raw_attempt
    directory = directory.resolve()
    try:
        directory.relative_to(project_root)
    except ValueError:
        return (_risk("EXEC-ARCHIVE-INVALID", "Attempt directory escapes project root"),)

    risks: list[ContractRisk] = []
    marker_path = directory / COMPLETION_MANIFEST_FILENAME
    if not marker_path.is_file():
        return (
            _risk(
                "EXEC-COMPLETION-MARKER-MISSING",
                "Attempt has no marker-last completion manifest",
            ),
        )
    marker = _load_mapping(marker_path, "completion marker", risks)
    if marker is None:
        return _dedupe(risks)
    marker_errors = SchemaCatalog().validate("attempt_completion_manifest", marker)
    risks.extend(
        _risk(
            "EXEC-COMPLETION-MARKER-INVALID",
            f"marker{error.pointer}: {error.message}",
        )
        for error in marker_errors
    )
    try:
        marker_refs = tuple(
            FileReference.from_mapping(item)
            for item in marker.get("files", [])
            if isinstance(item, Mapping)
        )
    except ContractError as exc:
        risks.append(_risk("EXEC-COMPLETION-MARKER-INVALID", str(exc)))
        marker_refs = ()
    risks.extend(check_references(project_root, marker_refs))
    recorded_paths = {reference.path for reference in marker_refs}
    actual_paths: set[str] = set()
    for path in directory.rglob("*"):
        if not path.is_file() or path.name == COMPLETION_MANIFEST_FILENAME:
            continue
        if path.is_symlink():
            risks.append(_risk("EXEC-ARCHIVE-INVALID", f"archive file is a symlink: {path.name}"))
            continue
        try:
            actual_paths.add(_relative(project_root, path))
        except ValueError:
            risks.append(_risk("EXEC-ARCHIVE-INVALID", f"archive file escapes root: {path.name}"))
    if recorded_paths != actual_paths:
        risks.append(
            _risk(
                "EXEC-COMPLETION-MARKER-INVALID",
                "completion marker file set differs from the Attempt directory",
            )
        )

    required = {
        ATTEMPT_FILENAME,
        RECEIPT_FILENAME,
        TRANSCRIPT_FILENAME,
        TRACE_INDEX_FILENAME,
    }
    missing = sorted(name for name in required if not (directory / name).is_file())
    if missing:
        risks.append(
            _risk("EXEC-ARCHIVE-INCOMPLETE", "missing closeout files: " + ", ".join(missing))
        )
        return _dedupe(risks)

    attempt_document = _load_mapping(directory / ATTEMPT_FILENAME, "Attempt", risks)
    receipt_document = _load_mapping(directory / RECEIPT_FILENAME, "Execution Receipt", risks)
    if attempt_document is None or receipt_document is None:
        return _dedupe(risks)
    risks.extend(_schema_risks("attempt", attempt_document))
    risks.extend(_schema_risks("execution_receipt", receipt_document))
    try:
        attempt = AttemptRecord.from_mapping(attempt_document)
        receipt = ExecutionReceipt.from_mapping(receipt_document)
    except ContractError as exc:
        risks.append(_risk("EXEC-ARCHIVE-INVALID", str(exc)))
        return _dedupe(risks)

    risks.extend(validate_attempt_trace(project_root, directory).risks)
    try:
        expected_turns = list(derive_session_transcript(directory))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        risks.append(_risk("EXEC-TRANSCRIPT-DRIFT", f"Trace-derived transcript failed: {exc}"))
        expected_turns = []
    expected_transcript = {
        "schema_version": "0.1.0",
        "source": "agent-trace-derived-view",
        "attempt_id": attempt.attempt_id,
        "turns": expected_turns,
    }
    try:
        actual_transcript = json.loads(
            (directory / TRANSCRIPT_FILENAME).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        risks.append(_risk("EXEC-TRANSCRIPT-DRIFT", f"transcript cannot be read: {exc}"))
    else:
        if actual_transcript != expected_transcript:
            risks.append(
                _risk(
                    "EXEC-TRANSCRIPT-DRIFT",
                    "session transcript is not the deterministic Trace-derived view",
                )
            )

    protocol_path = Path(protocol)
    if protocol_path.is_absolute():
        try:
            protocol_path = protocol_path.resolve()
            protocol_path.relative_to(project_root)
        except ValueError:
            protocol_path = Path()
    else:
        resolved_protocol = resolve_within_root(project_root, str(protocol_path))
        protocol_path = resolved_protocol if resolved_protocol is not None else Path()
    protocol_document = (
        _load_mapping(protocol_path, "Project Protocol", risks)
        if protocol_path.is_file()
        else None
    )
    if protocol_document is None and not protocol_path.is_file():
        risks.append(_risk("EXEC-ARCHIVE-INVALID", "Project Protocol is missing or outside root"))
    if protocol_document is not None:
        try:
            risks.extend(
                check_execution_receipt(
                    receipt,
                    ProjectProtocol.from_mapping(protocol_document),
                    root=project_root,
                    receipt_ref=_relative(project_root, directory / RECEIPT_FILENAME),
                )
            )
        except ContractError as exc:
            risks.append(_risk("EXEC-ARCHIVE-INVALID", str(exc)))
    if marker.get("attempt_id") != attempt.attempt_id or marker.get("status") != receipt.status:
        risks.append(
            _risk(
                "EXEC-COMPLETION-MARKER-INVALID",
                "completion marker identity or status differs from Attempt/Receipt",
            )
        )
    return _dedupe(risks)


__all__ = [
    "ATTEMPT_FILENAME",
    "ArchiveCloseoutResult",
    "COMPLETION_MANIFEST_FILENAME",
    "RECEIPT_FILENAME",
    "TRANSCRIPT_FILENAME",
    "finalize_execution_archive",
    "verify_execution_archive",
]
