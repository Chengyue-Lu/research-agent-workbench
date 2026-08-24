"""Fail-closed consumer boundary for Capability Snapshots.

Parsing a mapping is intentionally not enough to make it executable.  This
module reuses the repository SchemaCatalog and document-closure validator and
returns a Snapshot only after every loaded schema, identity, hash, and
cross-document invariant has passed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.validation.documents import (
    LoadedDocuments,
    ValidationIssue,
    infer_document_kind,
    load_and_validate,
)


DOCUMENT_SUFFIXES = {".json", ".yaml", ".yml"}


class CapabilitySnapshotValidationError(ValueError):
    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(issues)
        detail = "; ".join(
            f"{issue.path}:{issue.code}:{issue.message}" for issue in self.issues
        )
        super().__init__("Capability Snapshot validation failed: " + detail)


@dataclass(frozen=True, slots=True)
class ValidatedCapabilitySnapshot:
    path: Path
    document: Mapping[str, Any]
    documents: Mapping[Path, Any]

    @property
    def qualification(self) -> str:
        return str(self.document["qualification"])

    @property
    def runtime_execution_input(self) -> bool:
        return (
            self.qualification == "runtime-execution"
            and self.document.get("boundaries", {}).get("execution_input") is True
        )


def _consumer_error(path: Path, code: str, message: str) -> CapabilitySnapshotValidationError:
    return CapabilitySnapshotValidationError((ValidationIssue(path, code, message),))


def _normalized_sha256(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.removeprefix("sha256:").lower()
    if len(normalized) != 64:
        return None
    try:
        int(normalized, 16)
    except ValueError:
        return None
    return normalized


def _deep_read_only(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _deep_read_only(nested) for key, nested in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_deep_read_only(nested) for nested in value)
    return value


def load_validated_capability_snapshot(
    path: str | Path,
    *,
    project_root: str | Path = ".",
    document_roots: Iterable[str | Path] = ("registry", "examples"),
    require_runtime_execution: bool = False,
    expected_sha256: str | None = None,
    execution_at: object | None = None,
) -> ValidatedCapabilitySnapshot:
    """Load one Snapshot only through the existing repository validator.

    ``document_roots`` is explicit so a Runtime can provide the exact frozen
    repository view it intends to consume. No reference is silently upgraded
    or fetched from a Provider. ``expected_sha256`` is an optional caller pin;
    when supplied, it is checked against the exact bytes parsed by validation.
    ``execution_at`` remains an accepted compatibility argument but is not a
    Phase B availability clock or Runtime-admission fact.
    """

    root = Path(project_root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        relative_candidate = candidate.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"Capability Snapshot path escapes project root: {path}") from exc
    if resolve_within_root(root, relative_candidate) != candidate:
        raise ValueError(f"Capability Snapshot path escapes project root: {path}")
    if not candidate.is_file():
        raise ValueError(f"Capability Snapshot is missing: {candidate}")

    normalized_expected: str | None = None
    if expected_sha256 is not None:
        normalized_expected = _normalized_sha256(expected_sha256)
        if normalized_expected is None:
            raise _consumer_error(
                candidate,
                "CAPABILITY-SNAPSHOT-CONSUMER-HASH-INVALID",
                "expected_sha256 must be a 64-character SHA-256 value",
            )
    _ = execution_at

    paths: set[Path] = {candidate}
    for relative in document_roots:
        location = Path(relative)
        if not location.is_absolute():
            location = root / location
        location = location.resolve()
        try:
            location.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"document root escapes project root: {relative}") from exc
        if not location.exists():
            continue
        if location.is_file():
            if location.suffix.lower() in DOCUMENT_SUFFIXES:
                paths.add(location)
            continue
        paths.update(
            item
            for item in location.rglob("*")
            if item.is_file() and item.suffix.lower() in DOCUMENT_SUFFIXES
        )

    documents, issues = load_and_validate(sorted(paths))
    if normalized_expected is not None:
        if not isinstance(documents, LoadedDocuments):
            raise _consumer_error(
                candidate,
                "CAPABILITY-SNAPSHOT-CONSUMER-HASH-UNAVAILABLE",
                "Validation did not retain the digest of the bytes used to parse the Snapshot",
            )
        actual_snapshot_hash = documents.sha256_for(candidate)
        if actual_snapshot_hash is None:
            if issues:
                raise CapabilitySnapshotValidationError(issues)
            raise _consumer_error(
                candidate,
                "CAPABILITY-SNAPSHOT-CONSUMER-HASH-UNAVAILABLE",
                "Validation did not load the externally pinned Snapshot bytes",
            )
        if actual_snapshot_hash != normalized_expected:
            raise _consumer_error(
                candidate,
                "CAPABILITY-SNAPSHOT-CONSUMER-HASH-MISMATCH",
                "Snapshot bytes parsed by the validator do not match the externally pinned SHA-256",
            )
    if issues:
        raise CapabilitySnapshotValidationError(issues)
    document = documents.get(candidate)
    if not isinstance(document, Mapping) or infer_document_kind(document) != "resolved_capability_snapshot":
        raise CapabilitySnapshotValidationError(
            (
                ValidationIssue(
                    candidate,
                    "CAPABILITY-SNAPSHOT-CONSUMER-KIND",
                    "requested document is not a Resolved Capability Snapshot",
                ),
            )
        )
    validated = ValidatedCapabilitySnapshot(candidate, document, documents)
    if require_runtime_execution and not validated.runtime_execution_input:
        raise CapabilitySnapshotValidationError(
            (
                ValidationIssue(
                    candidate,
                    "CAPABILITY-SNAPSHOT-CONSUMER-NOT-RUNTIME-ELIGIBLE",
                    "Runtime accepts only a validated runtime-execution Snapshot",
                ),
            )
        )
    frozen_documents = MappingProxyType(
        {document_path: _deep_read_only(value) for document_path, value in documents.items()}
    )
    frozen_document = frozen_documents[candidate]
    assert isinstance(frozen_document, Mapping)
    return ValidatedCapabilitySnapshot(candidate, frozen_document, frozen_documents)
