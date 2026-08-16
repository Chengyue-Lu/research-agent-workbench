from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from research_workbench.artifacts.integrity import hash_file
from research_workbench.io import load_document
from research_workbench.protocol.models import ResearchMode


DEFAULT_MODE_DIRECTORY = Path("registry/modes")


@dataclass(frozen=True, slots=True)
class ResearchModeEntry:
    mode_id: str
    version: str
    path: str
    content_hash: str
    mode: ResearchMode


@dataclass(frozen=True, slots=True)
class ResearchModeRegistry:
    directory: Path
    project_root: Path
    entries: tuple[ResearchModeEntry, ...]
    digest: str

    @classmethod
    def load(
        cls,
        directory: str | Path = DEFAULT_MODE_DIRECTORY,
        *,
        project_root: str | Path = ".",
    ) -> "ResearchModeRegistry":
        root = Path(project_root).resolve()
        mode_directory = Path(directory)
        if not mode_directory.is_absolute():
            mode_directory = root / mode_directory
        mode_directory = mode_directory.resolve()
        try:
            mode_directory.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Mode registry escapes project root: {mode_directory}") from exc
        if not mode_directory.is_dir():
            raise FileNotFoundError(f"Mode registry directory not found: {mode_directory}")

        entries: list[ResearchModeEntry] = []
        seen_ids: set[str] = set()
        canonical: list[dict[str, str]] = []
        for path in sorted((*mode_directory.glob("*.yaml"), *mode_directory.glob("*.yml"))):
            document = load_document(path)
            if not isinstance(document, Mapping):
                raise ValueError(f"Mode manifest is not an object: {path}")
            mode = ResearchMode.from_mapping(document)
            if mode.mode_id in seen_ids:
                raise ValueError(f"duplicate registered Mode id: {mode.mode_id}")
            seen_ids.add(mode.mode_id)
            relative = path.relative_to(root).as_posix()
            content_hash = hash_file(path)
            entry = ResearchModeEntry(mode.mode_id, mode.version, relative, content_hash, mode)
            entries.append(entry)
            canonical.append(
                {
                    "mode_id": entry.mode_id,
                    "version": entry.version,
                    "path": entry.path,
                    "content_hash": entry.content_hash,
                }
            )
        if not entries:
            raise ValueError(f"Mode registry contains no manifests: {mode_directory}")
        digest = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(mode_directory, root, tuple(entries), digest)

    @property
    def modes(self) -> tuple[ResearchMode, ...]:
        return tuple(entry.mode for entry in self.entries)

    def require(self, mode_ids: Iterable[str]) -> tuple[ResearchMode, ...]:
        by_id = {entry.mode_id: entry.mode for entry in self.entries}
        requested = tuple(mode_ids)
        missing = sorted(set(requested) - set(by_id))
        if missing:
            raise KeyError("registered Modes not found: " + ", ".join(missing))
        return tuple(by_id[mode_id] for mode_id in requested)
