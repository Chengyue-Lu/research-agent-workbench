from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from research_workbench.artifacts.integrity import hash_directory, hash_file, resolve_within_root
from research_workbench.capability.models import SkillManifest
from research_workbench.io import load_document


DEFAULT_CANDIDATES = Path("registry/skills/candidates.json")
DEFAULT_ACCEPTED = Path("registry/skills/accepted.json")


@dataclass(frozen=True, slots=True)
class AcceptedSkillEntry:
    skill_id: str
    version: str
    manifest_path: str
    manifest_hash: str
    source_path: str
    content_hash: str
    package_hash: str
    license_status: str
    manifest: SkillManifest


@dataclass(frozen=True, slots=True)
class AcceptedSkillRegistry:
    index_path: Path
    project_root: Path
    entries: tuple[AcceptedSkillEntry, ...]
    digest: str

    @classmethod
    def load(
        cls,
        path: str | Path = DEFAULT_ACCEPTED,
        *,
        project_root: str | Path = ".",
    ) -> "AcceptedSkillRegistry":
        root = Path(project_root).resolve()
        index = Path(path)
        if not index.is_absolute():
            index = root / index
        document = load_document(index)
        if not isinstance(document, Mapping) or document.get("registry_kind") != "skill_accepted":
            raise ValueError(f"not an accepted skill registry: {index}")
        raw_entries = document.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError(f"accepted registry has no entries list: {index}")

        entries: list[AcceptedSkillEntry] = []
        seen: set[tuple[str, str]] = set()
        seen_ids: set[str] = set()
        canonical: list[dict[str, str]] = []
        for position, raw in enumerate(raw_entries):
            if not isinstance(raw, Mapping):
                raise ValueError(f"accepted registry entry {position} is not an object")
            required = (
                "skill_id",
                "version",
                "status",
                "manifest_path",
                "manifest_hash",
                "source_path",
                "content_hash",
                "package_hash",
                "license_status",
            )
            missing = [field for field in required if not isinstance(raw.get(field), str) or not raw[field]]
            if missing:
                raise ValueError(f"accepted registry entry {position} lacks: {', '.join(missing)}")
            if raw["status"] != "accepted":
                raise ValueError(f"accepted registry entry {position} is not accepted")
            key = (str(raw["skill_id"]), str(raw["version"]))
            if key in seen:
                raise ValueError(f"duplicate accepted skill: {key[0]}@{key[1]}")
            seen.add(key)
            if key[0] in seen_ids:
                raise ValueError(
                    f"multiple accepted versions require explicit Task version constraints: {key[0]}"
                )
            seen_ids.add(key[0])

            manifest_path = resolve_within_root(root, str(raw["manifest_path"]))
            source_path = resolve_within_root(root, str(raw["source_path"]))
            if manifest_path is None or source_path is None:
                raise ValueError(f"accepted skill path escapes project root: {key[0]}")
            if not manifest_path.is_file() or not source_path.is_file():
                raise ValueError(f"accepted skill files are missing: {key[0]}")
            manifest_document = load_document(manifest_path)
            if not isinstance(manifest_document, Mapping):
                raise ValueError(f"accepted manifest is not an object: {manifest_path}")
            manifest = SkillManifest.from_mapping(manifest_document)
            if (manifest.skill_id, manifest.version) != key:
                raise ValueError(f"accepted registry identity mismatch: {key[0]}@{key[1]}")
            if manifest.source_locator != str(raw["source_path"]):
                raise ValueError(f"accepted source locator mismatch: {key[0]}")
            expected_manifest = str(raw["manifest_hash"]).removeprefix("sha256:").lower()
            actual_manifest = hash_file(manifest_path)
            if actual_manifest != expected_manifest:
                raise ValueError(
                    f"accepted manifest drift: {key[0]} "
                    f"expected={expected_manifest} actual={actual_manifest}"
                )
            expected = str(raw["content_hash"]).removeprefix("sha256:").lower()
            expected_package = str(raw["package_hash"]).removeprefix("sha256:").lower()
            if manifest.source_content_hash.removeprefix("sha256:").lower() != expected:
                raise ValueError(f"accepted manifest hash mismatch: {key[0]}")
            if not manifest.source_package_hash or (
                manifest.source_package_hash.removeprefix("sha256:").lower() != expected_package
            ):
                raise ValueError(f"accepted manifest package hash mismatch: {key[0]}")
            actual = hash_file(source_path)
            if actual != expected:
                raise ValueError(f"accepted source content drift: {key[0]} expected={expected} actual={actual}")
            actual_package = hash_directory(source_path.parent)
            if actual_package != expected_package:
                raise ValueError(
                    f"accepted Skill package drift: {key[0]} expected={expected_package} actual={actual_package}"
                )
            entry = AcceptedSkillEntry(
                skill_id=key[0],
                version=key[1],
                manifest_path=str(raw["manifest_path"]),
                manifest_hash=expected_manifest,
                source_path=str(raw["source_path"]),
                content_hash=expected,
                package_hash=expected_package,
                license_status=str(raw["license_status"]),
                manifest=manifest,
            )
            entries.append(entry)
            canonical.append(
                {
                    "skill_id": entry.skill_id,
                    "version": entry.version,
                    "manifest_path": entry.manifest_path,
                    "manifest_hash": entry.manifest_hash,
                    "source_path": entry.source_path,
                    "content_hash": entry.content_hash,
                    "package_hash": entry.package_hash,
                    "license_status": entry.license_status,
                }
            )
        digest = hashlib.sha256(
            json.dumps(
                {"policy": document.get("policy", {}), "entries": canonical},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return cls(index, root, tuple(entries), digest)

    @property
    def manifests(self) -> tuple[SkillManifest, ...]:
        return tuple(entry.manifest for entry in self.entries)

    def require(self, skill_ids: Iterable[str]) -> tuple[SkillManifest, ...]:
        by_id = {entry.skill_id: entry.manifest for entry in self.entries}
        requested = tuple(skill_ids)
        missing = sorted(set(requested) - set(by_id))
        if missing:
            raise KeyError("accepted skills not found: " + ", ".join(missing))
        return tuple(by_id[skill_id] for skill_id in requested)


def load_candidates(path: str | Path = DEFAULT_CANDIDATES) -> list[dict[str, Any]]:
    document = load_document(path)
    if not isinstance(document, Mapping) or document.get("registry_kind") != "skill_candidates":
        raise ValueError(f"not a skill candidate registry: {path}")
    candidates = document.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError(f"candidate registry has no candidate list: {path}")
    return [dict(candidate) for candidate in candidates if isinstance(candidate, Mapping)]


def filter_candidates(
    candidates: Iterable[Mapping[str, Any]],
    *,
    status: str | None = None,
    mode: str | None = None,
    capability: str | None = None,
) -> list[Mapping[str, Any]]:
    return [
        candidate
        for candidate in candidates
        if (status is None or candidate.get("status") == status)
        and (mode is None or mode in candidate.get("applicable_modes", []))
        and (capability is None or capability in candidate.get("capabilities", []))
    ]
