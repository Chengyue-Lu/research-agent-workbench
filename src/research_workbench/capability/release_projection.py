"""Deterministic Maintainer-to-Runtime Skill release publication.

The publisher consumes accepted immutable release bytes plus a Lifecycle record,
but its output deliberately excludes Need, evaluation, and lifecycle history.
Runtime consumers may load the projection/index without importing Lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from research_workbench.artifacts.integrity import hash_bytes, resolve_within_root
from research_workbench.capability.catalog import AcceptedSkillRegistry, DEFAULT_ACCEPTED
from research_workbench.capability.lifecycle import (
    DEFAULT_SKILL_LIFECYCLE_INDEX,
    SkillLifecycleEntry,
    SkillLifecycleRecord,
    SkillLifecycleSet,
)
from research_workbench.capability.models import SkillManifest
from research_workbench.contracts.common import (
    ContractError,
    mapping_value,
    require_string,
    string_tuple,
    to_plain,
)
from research_workbench.io import load_document, load_document_bytes


DEFAULT_SKILL_RELEASE_PROJECTION_INDEX = Path("registry/skills/release-projections.json")


def _normalized_hash(value: str) -> str:
    normalized = value.removeprefix("sha256:").lower()
    if len(normalized) != 64:
        raise ValueError("expected a SHA-256 digest")
    try:
        int(normalized, 16)
    except ValueError as exc:
        raise ValueError("expected a SHA-256 digest") from exc
    return normalized


@dataclass(frozen=True, slots=True)
class SkillReleaseProjection:
    schema_version: str
    projection_id: str
    projection_version: str
    release: Mapping[str, Any]
    runtime_contract: Mapping[str, Any]
    eligibility: Mapping[str, Any]
    admission_provenance: Mapping[str, Any]
    boundaries: Mapping[str, Any]

    @property
    def reference(self) -> str:
        return f"{self.projection_id}@{self.projection_version}"

    @property
    def release_ref(self) -> str:
        return str(self.release["release_ref"])

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillReleaseProjection":
        return cls(
            schema_version=require_string(data, "schema_version"),
            projection_id=require_string(data, "projection_id"),
            projection_version=require_string(data, "projection_version"),
            release=dict(mapping_value(data, "release", required=True)),
            runtime_contract=dict(mapping_value(data, "runtime_contract", required=True)),
            eligibility=dict(mapping_value(data, "eligibility", required=True)),
            admission_provenance=dict(
                mapping_value(data, "admission_provenance", required=True)
            ),
            boundaries=dict(mapping_value(data, "boundaries", required=True)),
        )


@dataclass(frozen=True, slots=True)
class SkillReleaseProjectionEntry:
    projection_ref: str
    projection_id: str
    projection_version: str
    release_ref: str
    document_path: str
    content_hash: str
    projection: SkillReleaseProjection


@dataclass(frozen=True, slots=True)
class SkillReleaseProjectionSet:
    index_path: Path
    project_root: Path
    entries: tuple[SkillReleaseProjectionEntry, ...]

    @classmethod
    def load(
        cls,
        path: str | Path = DEFAULT_SKILL_RELEASE_PROJECTION_INDEX,
        *,
        project_root: str | Path = ".",
    ) -> "SkillReleaseProjectionSet":
        root = Path(project_root).resolve()
        index_path = Path(path)
        if not index_path.is_absolute():
            index_path = root / index_path
        index = load_document(index_path)
        if not isinstance(index, Mapping) or index.get("registry_kind") != "skill_release_projection_index":
            raise ValueError(f"not a Skill Release Projection integrity index: {index_path}")
        # Import lazily: validation.documents imports the projection registry,
        # which imports this module while the validation package is initialising.
        from research_workbench.validation.schemas import SchemaCatalog

        catalog = SchemaCatalog()
        index_schema_errors = catalog.validate("skill_release_projection_index", index)
        if index_schema_errors:
            first = index_schema_errors[0]
            raise ValueError(
                "Skill Release Projection index schema invalid: "
                f"{first.pointer}: {first.message}"
            )
        raw_entries = index["entries"]

        entries: list[SkillReleaseProjectionEntry] = []
        seen_refs: set[str] = set()
        seen_identities: set[tuple[str, str]] = set()
        seen_paths: set[str] = set()
        seen_releases: set[str] = set()
        for raw in raw_entries:
            projection_ref = require_string(raw, "projection_ref")
            projection_id = require_string(raw, "projection_id")
            projection_version = require_string(raw, "projection_version")
            release_ref = require_string(raw, "release_ref")
            document_path = require_string(raw, "document_path")
            content_hash = _normalized_hash(require_string(raw, "content_hash"))
            identity = (projection_id, projection_version)
            if projection_ref in seen_refs or identity in seen_identities:
                raise ValueError(f"duplicate Skill Release Projection identity: {projection_ref}")
            if document_path in seen_paths:
                raise ValueError(f"duplicate Skill Release Projection path: {document_path}")
            if release_ref in seen_releases:
                raise ValueError(f"multiple current projections for one Skill Release: {release_ref}")
            seen_refs.add(projection_ref)
            seen_identities.add(identity)
            seen_paths.add(document_path)
            seen_releases.add(release_ref)

            resolved = resolve_within_root(root, document_path)
            if resolved is None or not resolved.is_file():
                raise ValueError(f"Skill Release Projection path is missing or escapes root: {document_path}")
            content = resolved.read_bytes()
            if hash_bytes(content) != content_hash:
                raise ValueError(f"Skill Release Projection content drift: {projection_ref}")
            document = load_document_bytes(resolved, content)
            if not isinstance(document, Mapping):
                raise ValueError(f"Skill Release Projection is not an object: {document_path}")
            projection_schema_errors = catalog.validate(
                "skill_release_projection", document
            )
            if projection_schema_errors:
                first = projection_schema_errors[0]
                raise ValueError(
                    "Skill Release Projection schema invalid: "
                    f"{first.pointer}: {first.message}"
                )
            projection = SkillReleaseProjection.from_mapping(document)
            if (
                projection.reference != projection_ref
                or projection.projection_id != projection_id
                or projection.projection_version != projection_version
                or projection.release_ref != release_ref
            ):
                raise ValueError(f"Skill Release Projection identity mismatch: {projection_ref}")
            entries.append(
                SkillReleaseProjectionEntry(
                    projection_ref,
                    projection_id,
                    projection_version,
                    release_ref,
                    document_path,
                    content_hash,
                    projection,
                )
            )
        return cls(index_path, root, tuple(entries))

    def require(self, projection_refs: Iterable[str]) -> tuple[SkillReleaseProjection, ...]:
        requested = (
            (projection_refs,)
            if isinstance(projection_refs, str)
            else tuple(projection_refs)
        )
        by_ref = {entry.projection_ref: entry.projection for entry in self.entries}
        selected: list[SkillReleaseProjection] = []
        seen: set[str] = set()
        for projection_ref in requested:
            if projection_ref in seen:
                raise ValueError(f"Skill Release Projection selected more than once: {projection_ref}")
            try:
                selected.append(by_ref[projection_ref])
            except KeyError as exc:
                raise ValueError(
                    f"Skill Release Projection is not indexed: {projection_ref}"
                ) from exc
            seen.add(projection_ref)
        return tuple(selected)


def _runtime_contract(manifest: SkillManifest) -> dict[str, Any]:
    if (
        manifest.runtime_data_egress_ceiling is None
        or manifest.runtime_side_effect_ceiling is None
    ):
        raise ValueError(
            "Skill Release lacks runtime_boundaries; legacy manifests cannot be projected"
        )
    return {
        "provided_capabilities": list(manifest.capabilities),
        "supported_inputs": list(manifest.input_contracts),
        "supported_outputs": list(manifest.output_contracts),
        "dependencies": {
            "required_tools": list(manifest.required_tools),
            "optional_tools": list(manifest.optional_tools),
        },
        "compatibility": {
            "applies_to_modes": list(manifest.applies_to_modes),
            "excludes": list(manifest.excludes),
            "incompatible_with": list(manifest.incompatible_with),
        },
        "permission_ceiling": to_plain(manifest.permission_ceiling),
        "data_egress_ceiling": dict(manifest.runtime_data_egress_ceiling),
        "side_effect_ceiling": dict(manifest.runtime_side_effect_ceiling),
    }


def projection_from_verified_release(
    *,
    lifecycle_entry: SkillLifecycleEntry,
    manifest: SkillManifest,
    manifest_sha256: str,
    projection_version: str,
) -> dict[str, Any]:
    """Create only the deterministic narrow mapping after eligibility is verified."""

    record = lifecycle_entry.record
    decision_ref = record.admission.decision_ref
    if decision_ref is None:
        raise ValueError("Skill Release has no Human admission decision reference")
    release_ref = f"{record.skill_ref.skill_id}@{record.skill_ref.version}"
    return {
        "schema_version": "0.1.0",
        "projection_id": f"{record.skill_ref.skill_id}-{record.skill_ref.version}",
        "projection_version": projection_version,
        "release": {
            "skill_id": record.skill_ref.skill_id,
            "skill_version": record.skill_ref.version,
            "release_ref": release_ref,
            "manifest_path": record.skill_ref.manifest_path,
            "manifest_sha256": f"sha256:{_normalized_hash(manifest_sha256)}",
            "content_hash": f"sha256:{_normalized_hash(record.skill_ref.content_hash)}",
            "package_hash": f"sha256:{_normalized_hash(record.skill_ref.package_hash)}",
        },
        "runtime_contract": _runtime_contract(manifest),
        "eligibility": {
            "state": "eligible",
            "eligibility_ref": record.runtime_eligibility.eligibility_ref,
            "scopes": list(record.runtime_eligibility.scopes),
        },
        "admission_provenance": {
            "lifecycle_ref": lifecycle_entry.lifecycle_ref,
            "lifecycle_document_path": lifecycle_entry.document_path,
            "lifecycle_content_hash": f"sha256:{lifecycle_entry.content_hash}",
            "decision_owner": "human",
            "decision_ref": decision_ref,
        },
        "boundaries": {
            "stores_need": False,
            "stores_candidate": False,
            "stores_trial_or_evaluation_results": False,
            "stores_metrics_or_deliberation": False,
            "stores_lifecycle_history": False,
            "selects_supply": False,
            "grants_execution": False,
            "grants_permission": False,
            "owns_fallback": False,
            "promotes_claim": False,
            "satisfies_human_gate": False,
        },
    }


def build_skill_release_projection(
    lifecycle_ref: str,
    *,
    projection_version: str,
    evidence_resolver: Callable[[str], bool],
    decision_resolver: Callable[[str], bool],
    project_root: str | Path = ".",
    accepted_registry_path: str | Path = DEFAULT_ACCEPTED,
    lifecycle_index_path: str | Path = DEFAULT_SKILL_LIFECYCLE_INDEX,
) -> dict[str, Any]:
    """Verify an accepted Release and emit its deterministic Runtime projection.

    The resolvers are mandatory because Lifecycle state strings alone cannot
    prove evaluation evidence or a Human decision.
    """

    root = Path(project_root).resolve()
    accepted = AcceptedSkillRegistry.load(accepted_registry_path, project_root=root)
    lifecycle = SkillLifecycleSet.load(lifecycle_index_path, project_root=root)
    lifecycle_entries = {
        entry.lifecycle_ref: entry for entry in lifecycle.entries
    }
    try:
        lifecycle_entry = lifecycle_entries[lifecycle_ref]
    except KeyError as exc:
        raise ValueError(f"Skill Lifecycle is not indexed: {lifecycle_ref}") from exc
    record: SkillLifecycleRecord = lifecycle_entry.record
    if not record.externally_verified_for_new_binding(
        evidence_resolver=evidence_resolver,
        decision_resolver=decision_resolver,
    ):
        raise ValueError(
            "Skill Lifecycle evidence or Human admission is not verified for new binding"
        )

    matching = [
        entry
        for entry in accepted.entries
        if (entry.skill_id, entry.version)
        == (record.skill_ref.skill_id, record.skill_ref.version)
    ]
    if len(matching) != 1 or matching[0].lifecycle != "active":
        raise ValueError(
            "Skill Release must be one exact active accepted Registry entry"
        )
    release = matching[0]
    if (
        record.skill_ref.manifest_path != release.manifest_path
        or _normalized_hash(record.skill_ref.content_hash) != release.content_hash
        or _normalized_hash(record.skill_ref.package_hash) != release.package_hash
    ):
        raise ValueError("Skill Lifecycle and accepted Release identity/hash disagree")

    manifest_path = resolve_within_root(root, release.manifest_path)
    if manifest_path is None or not manifest_path.is_file():
        raise ValueError("accepted Skill manifest is missing or escapes project root")
    manifest_content = manifest_path.read_bytes()
    manifest_document = load_document_bytes(manifest_path, manifest_content)
    if not isinstance(manifest_document, Mapping):
        raise ContractError("manifest", "must be an object")
    manifest = SkillManifest.from_mapping(manifest_document)
    if (manifest.skill_id, manifest.version) != (release.skill_id, release.version):
        raise ValueError("Skill manifest identity disagrees with accepted Release")
    # Force complete runtime boundary presence before any projection mapping.
    _runtime_contract(manifest)
    return projection_from_verified_release(
        lifecycle_entry=lifecycle_entry,
        manifest=manifest,
        manifest_sha256=hash_bytes(manifest_content),
        projection_version=projection_version,
    )


__all__ = [
    "DEFAULT_SKILL_RELEASE_PROJECTION_INDEX",
    "SkillReleaseProjection",
    "SkillReleaseProjectionEntry",
    "SkillReleaseProjectionSet",
    "build_skill_release_projection",
    "projection_from_verified_release",
]
