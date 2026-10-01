"""Shared byte-bound document validation primitives."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from research_workbench.artifacts.integrity import hash_file


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


def document_hash(documents: Mapping[Path, Any], path: Path) -> str:
    """Return the digest of the bytes that produced the loaded mapping."""

    if isinstance(documents, LoadedDocuments):
        return documents.sha256_for(path) or ""
    return hash_file(path)


def document_has_loaded_bytes(documents: Mapping[Path, Any], path: Path) -> bool:
    if isinstance(documents, LoadedDocuments):
        return documents.sha256_for(path) is not None
    return path.is_file()


def matches_repository_path(path: Path, repository_relative: str) -> bool:
    normalized_path = path.as_posix()
    normalized_relative = PurePosixPath(repository_relative).as_posix()
    return normalized_path == normalized_relative or normalized_path.endswith(
        f"/{normalized_relative}"
    )


def loaded_document_at(
    documents: Mapping[Path, Any], repository_relative: object
) -> tuple[Path, Mapping[str, Any]] | None:
    if not isinstance(repository_relative, str):
        return None
    for path, document in documents.items():
        if isinstance(document, Mapping) and matches_repository_path(
            path, repository_relative
        ):
            return path, document
    return None
