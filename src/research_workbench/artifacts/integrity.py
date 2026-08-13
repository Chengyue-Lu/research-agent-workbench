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


def hash_directory(path: str | Path) -> str:
    """Hash stable package sources, excluding generated interpreter/OS caches."""

    root = Path(path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    digest = hashlib.sha256()
    excluded_names = {".DS_Store"}
    files = (
        candidate
        for candidate in root.rglob("*")
        if candidate.is_file()
        and "__pycache__" not in candidate.parts
        and candidate.suffix.lower() not in {".pyc", ".pyo"}
        and candidate.name not in excluded_names
    )
    # Path ordering is host-dependent: WindowsPath compares case-insensitively,
    # while PosixPath compares case-sensitively. Package locks instead use one
    # repository-relative ordering on every host.
    for file_path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        if file_path.is_symlink():
            raise ValueError(f"refusing to hash symlinked package file: {file_path}")
        relative = file_path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(hash_file(file_path)))
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
