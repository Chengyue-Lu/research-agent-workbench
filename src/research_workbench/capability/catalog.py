from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping

from research_workbench.artifacts.integrity import hash_directory, hash_file, resolve_within_root
from research_workbench.capability.models import SkillManifest
from research_workbench.contracts.common import ContractError, parse_skill_reference
from research_workbench.io import load_document


DEFAULT_CANDIDATES = Path("registry/skills/candidates.json")
DEFAULT_ACCEPTED = Path("registry/skills/accepted.json")


@dataclass(frozen=True, slots=True)
class AcceptedSkillEntry:
    skill_id: str
    version: str
    manifest_path: str
    source_path: str
    content_hash: str
    package_hash: str
    license_status: str
    lifecycle: str
    manifest: SkillManifest


class SkillRegistrySelectionError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


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
        active_ids: set[str] = set()
        canonical: list[dict[str, str]] = []
        for position, raw in enumerate(raw_entries):
            if not isinstance(raw, Mapping):
                raise ValueError(f"accepted registry entry {position} is not an object")
            required = (
                "skill_id",
                "version",
                "status",
                "manifest_path",
                "source_path",
                "content_hash",
                "package_hash",
                "license_status",
                "lifecycle",
            )
            missing = [field for field in required if not isinstance(raw.get(field), str) or not raw[field]]
            if missing:
                raise ValueError(f"accepted registry entry {position} lacks: {', '.join(missing)}")
            if raw["status"] != "accepted":
                raise ValueError(f"accepted registry entry {position} is not accepted")
            lifecycle = str(raw["lifecycle"])
            if lifecycle not in {"active", "legacy", "deprecated"}:
                raise ValueError(
                    f"accepted registry entry {position} has invalid lifecycle: {lifecycle}"
                )
            key = (str(raw["skill_id"]), str(raw["version"]))
            if key in seen:
                raise ValueError(f"duplicate accepted skill: {key[0]}@{key[1]}")
            seen.add(key)
            if lifecycle == "active":
                if key[0] in active_ids:
                    raise ValueError(f"multiple active accepted versions are forbidden: {key[0]}")
                active_ids.add(key[0])

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
                source_path=str(raw["source_path"]),
                content_hash=expected,
                package_hash=expected_package,
                license_status=str(raw["license_status"]),
                lifecycle=lifecycle,
                manifest=manifest,
            )
            entries.append(entry)
            canonical.append(
                {
                    "skill_id": entry.skill_id,
                    "version": entry.version,
                    "manifest_path": entry.manifest_path,
                    "source_path": entry.source_path,
                    "content_hash": entry.content_hash,
                    "package_hash": entry.package_hash,
                    "license_status": entry.license_status,
                    "lifecycle": entry.lifecycle,
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

    @property
    def active_manifests(self) -> tuple[SkillManifest, ...]:
        return tuple(entry.manifest for entry in self.entries if entry.lifecycle == "active")

    def require(
        self,
        skill_references: Iterable[str],
        *,
        purpose: Literal["new-assignment", "historical-replay"] = "new-assignment",
    ) -> tuple[SkillManifest, ...]:
        if purpose not in {"new-assignment", "historical-replay"}:
            raise ValueError(f"unsupported Skill resolution purpose: {purpose}")
        requested = (skill_references,) if isinstance(skill_references, str) else tuple(skill_references)
        by_id: dict[str, list[AcceptedSkillEntry]] = {}
        by_key: dict[tuple[str, str], AcceptedSkillEntry] = {}
        for entry in self.entries:
            by_id.setdefault(entry.skill_id, []).append(entry)
            by_key[(entry.skill_id, entry.version)] = entry

        selected: list[AcceptedSkillEntry] = []
        selected_keys: set[tuple[str, str]] = set()
        for index, raw_reference in enumerate(requested):
            try:
                reference = parse_skill_reference(raw_reference, f"required_skills[{index}]")
            except ContractError as exc:
                raise SkillRegistrySelectionError("SKILL-SELECTOR-INVALID", str(exc)) from exc

            if purpose == "historical-replay" and reference.version is None:
                raise SkillRegistrySelectionError(
                    "SKILL-VERSION-REQUIRED",
                    f"historical replay requires an exact version: {reference.skill_id}@<version>",
                )

            if reference.version is not None:
                entry = by_key.get((reference.skill_id, reference.version))
                if entry is None:
                    raise SkillRegistrySelectionError(
                        "SKILL-MISSING",
                        f"accepted Skill is not present: {reference.identifier}",
                    )
            else:
                active = [entry for entry in by_id.get(reference.skill_id, []) if entry.lifecycle == "active"]
                if not active:
                    if reference.skill_id in by_id:
                        lifecycles = ", ".join(
                            f"{entry.version}:{entry.lifecycle}" for entry in by_id[reference.skill_id]
                        )
                        raise SkillRegistrySelectionError(
                            "SKILL-INACTIVE",
                            f"Skill has no active version for new assignment: {reference.skill_id} ({lifecycles})",
                        )
                    raise SkillRegistrySelectionError(
                        "SKILL-MISSING",
                        f"accepted Skill is not present: {reference.skill_id}",
                    )
                if len(active) != 1:
                    raise SkillRegistrySelectionError(
                        "SKILL-VERSION-AMBIGUOUS",
                        f"multiple active versions require an exact selector: {reference.skill_id}",
                    )
                entry = active[0]

            if purpose == "new-assignment" and entry.lifecycle != "active":
                raise SkillRegistrySelectionError(
                    "SKILL-INACTIVE",
                    f"Skill is {entry.lifecycle} and cannot enter a new assignment: {entry.skill_id}@{entry.version}",
                )
            key = (entry.skill_id, entry.version)
            if key in selected_keys:
                raise SkillRegistrySelectionError(
                    "SKILL-DUPLICATE",
                    f"Skill is selected more than once: {entry.skill_id}@{entry.version}",
                )
            selected_keys.add(key)
            selected.append(entry)
        return tuple(entry.manifest for entry in selected)


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
