from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from research_workbench.tasks.models import FileReference


class ReferenceStatus(StrEnum):
    OK = "ok"
    MISSING = "missing"
    HASH_MISMATCH = "hash_mismatch"
    OUTSIDE_ROOT = "outside_root"


@dataclass(frozen=True, slots=True)
class ReferenceCheck:
    reference: FileReference
    status: ReferenceStatus
    resolved_path: Path | None = None
    actual_sha256: str | None = None

    @property
    def valid(self) -> bool:
        return self.status == ReferenceStatus.OK


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_within_root(root: str | Path, relative_path: str) -> Path | None:
    root_path = Path(root).resolve()
    candidate = (root_path / relative_path).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError:
        return None
    return candidate


def check_file_reference(root: str | Path, reference: FileReference) -> ReferenceCheck:
    resolved = resolve_within_root(root, reference.path)
    if resolved is None:
        return ReferenceCheck(reference, ReferenceStatus.OUTSIDE_ROOT)
    if not resolved.is_file():
        return ReferenceCheck(reference, ReferenceStatus.MISSING, resolved)
    actual = hash_file(resolved)
    if actual != reference.sha256.lower().removeprefix("sha256:"):
        return ReferenceCheck(reference, ReferenceStatus.HASH_MISMATCH, resolved, actual)
    return ReferenceCheck(reference, ReferenceStatus.OK, resolved, actual)
