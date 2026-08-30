"""Fail-closed SkillReleaseProjection index and derivation validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from research_workbench.capability.lifecycle import (
    SkillLifecycleEntry,
    SkillLifecycleRecord,
)
from research_workbench.capability.models import SkillManifest
from research_workbench.capability.release_projection import (
    SkillReleaseProjection,
    projection_from_verified_release,
)
from research_workbench.contracts.common import ContractError
from research_workbench.validation.document_core import (
    ValidationIssue,
    document_has_loaded_bytes,
    document_hash,
    loaded_document_at,
    matches_repository_path,
)
from research_workbench.validation.document_kinds import infer_document_kind


def _indices(
    documents: Mapping[Path, Any],
) -> list[tuple[Path, Mapping[str, Any]]]:
    return [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping)
        and document.get("registry_kind") == "skill_release_projection_index"
    ]


def _accepted_entries(documents: Mapping[Path, Any]) -> dict[str, Mapping[str, Any]]:
    entries: dict[str, Mapping[str, Any]] = {}
    for document in documents.values():
        if not isinstance(document, Mapping) or document.get("registry_kind") != "skill_accepted":
            continue
        for entry in document.get("entries", []):
            if not isinstance(entry, Mapping):
                continue
            skill_id = entry.get("skill_id")
            version = entry.get("version")
            if isinstance(skill_id, str) and isinstance(version, str):
                entries[f"{skill_id}@{version}"] = entry
    return entries


def _lifecycle_entries(
    documents: Mapping[Path, Any],
) -> dict[str, tuple[Mapping[str, Any], SkillLifecycleEntry]]:
    result: dict[str, tuple[Mapping[str, Any], SkillLifecycleEntry]] = {}
    for document in documents.values():
        if not isinstance(document, Mapping) or document.get("registry_kind") != "skill_lifecycle_index":
            continue
        for entry in document.get("entries", []):
            if not isinstance(entry, Mapping):
                continue
            lifecycle_ref = entry.get("lifecycle_ref")
            document_path = entry.get("document_path")
            content_hash = entry.get("content_hash")
            if not all(isinstance(value, str) for value in (lifecycle_ref, document_path, content_hash)):
                continue
            loaded = loaded_document_at(documents, document_path)
            if loaded is None:
                continue
            try:
                record = SkillLifecycleRecord.from_mapping(loaded[1])
            except ContractError:
                continue
            result[str(lifecycle_ref)] = (
                entry,
                SkillLifecycleEntry(
                    lifecycle_ref=str(lifecycle_ref),
                    lifecycle_id=str(entry.get("lifecycle_id")),
                    lifecycle_version=str(entry.get("lifecycle_version")),
                    document_path=str(document_path),
                    content_hash=str(content_hash).removeprefix("sha256:").lower(),
                    record=record,
                ),
            )
    return result


def validate_skill_release_projections(
    documents: Mapping[Path, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    indices = _indices(documents)
    projection_documents = [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping)
        and infer_document_kind(document) == "skill_release_projection"
    ]
    if not indices:
        if projection_documents:
            issues.append(
                ValidationIssue(
                    projection_documents[0][0],
                    "SKILL-RELEASE-PROJECTION-INDEX-MISSING",
                    "SkillReleaseProjection documents require one closed integrity index",
                )
            )
        return issues
    if len(indices) > 1:
        for path, _ in indices[1:]:
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-INDEX-DUPLICATE",
                    "only one SkillReleaseProjection integrity index may be loaded",
                )
            )
        return issues

    index_path, index = indices[0]
    indexed: dict[str, tuple[str, Mapping[str, Any]]] = {}
    seen_identities: set[tuple[str, str]] = set()
    seen_paths: set[str] = set()
    seen_releases: set[str] = set()
    for position, entry in enumerate(index.get("entries", [])):
        if not isinstance(entry, Mapping):
            continue
        values = (
            entry.get("projection_ref"),
            entry.get("projection_id"),
            entry.get("projection_version"),
            entry.get("release_ref"),
            entry.get("document_path"),
        )
        if not all(isinstance(value, str) for value in values):
            continue
        projection_ref, projection_id, projection_version, release_ref, document_path = (
            str(value) for value in values
        )
        identity = (projection_id, projection_version)
        if projection_ref in indexed or identity in seen_identities:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-RELEASE-PROJECTION-IDENTITY-DUPLICATE",
                    f"duplicate projection identity at entries[{position}]: {projection_ref}",
                )
            )
            continue
        if document_path in seen_paths:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-RELEASE-PROJECTION-PATH-DUPLICATE",
                    f"duplicate projection path at entries[{position}]: {document_path}",
                )
            )
            continue
        if release_ref in seen_releases:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-RELEASE-PROJECTION-RELEASE-DUPLICATE",
                    f"multiple current projections target one release: {release_ref}",
                )
            )
            continue
        indexed[projection_ref] = (document_path, entry)
        seen_identities.add(identity)
        seen_paths.add(document_path)
        seen_releases.add(release_ref)

        loaded = loaded_document_at(documents, document_path)
        if loaded is None:
            issues.append(
                ValidationIssue(
                    index_path,
                    "SKILL-RELEASE-PROJECTION-DOCUMENT-MISSING",
                    f"indexed projection is not loaded: {document_path}",
                )
            )
            continue
        loaded_path, projection = loaded
        if infer_document_kind(projection) != "skill_release_projection":
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-RELEASE-PROJECTION-DOCUMENT-KIND",
                    f"indexed document is not a SkillReleaseProjection: {document_path}",
                )
            )
            continue
        try:
            parsed = SkillReleaseProjection.from_mapping(projection)
        except ContractError as exc:
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-RELEASE-PROJECTION-CONTRACT",
                    str(exc),
                )
            )
            continue
        if (
            parsed.reference != projection_ref
            or parsed.projection_id != projection_id
            or parsed.projection_version != projection_version
            or parsed.release_ref != release_ref
        ):
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "SKILL-RELEASE-PROJECTION-IDENTITY-MISMATCH",
                    f"index and projection identities disagree: {projection_ref}",
                )
            )
        expected_hash = entry.get("content_hash")
        if isinstance(expected_hash, str) and document_has_loaded_bytes(documents, loaded_path):
            if document_hash(documents, loaded_path) != expected_hash.removeprefix("sha256:").lower():
                issues.append(
                    ValidationIssue(
                        index_path,
                        "SKILL-RELEASE-PROJECTION-HASH-MISMATCH",
                        f"content hash does not match projection: {projection_ref}",
                    )
                )

    for path, projection in projection_documents:
        try:
            parsed = SkillReleaseProjection.from_mapping(projection)
        except ContractError:
            continue
        indexed_entry = indexed.get(parsed.reference)
        if indexed_entry is None:
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-UNINDEXED",
                    f"projection is not in the integrity index: {parsed.reference}",
                )
            )
        elif not matches_repository_path(path, indexed_entry[0]):
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-PATH-MISMATCH",
                    f"projection path disagrees with the index: {parsed.reference}",
                )
            )

    accepted = _accepted_entries(documents)
    lifecycle = _lifecycle_entries(documents)
    for path, projection in projection_documents:
        release = projection.get("release")
        provenance = projection.get("admission_provenance")
        if not isinstance(release, Mapping) or not isinstance(provenance, Mapping):
            continue
        release_ref = release.get("release_ref")
        lifecycle_ref = provenance.get("lifecycle_ref")
        accepted_entry = accepted.get(str(release_ref))
        lifecycle_pair = lifecycle.get(str(lifecycle_ref))
        if accepted_entry is None or accepted_entry.get("lifecycle") != "active":
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-RELEASE-INELIGIBLE",
                    f"projection source is not one active accepted Release: {release_ref}",
                )
            )
            continue
        if lifecycle_pair is None:
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-LIFECYCLE-MISSING",
                    f"projection Lifecycle provenance is not indexed: {lifecycle_ref}",
                )
            )
            continue
        lifecycle_index_entry, lifecycle_entry = lifecycle_pair
        record = lifecycle_entry.record
        if not record.eligible_for_new_binding():
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-LIFECYCLE-INELIGIBLE",
                    "projection source Lifecycle is not structurally eligible for new binding",
                )
            )
            continue
        if (
            provenance.get("lifecycle_document_path") != lifecycle_entry.document_path
            or provenance.get("lifecycle_content_hash") != lifecycle_index_entry.get("content_hash")
            or provenance.get("decision_owner") != record.admission.decision_owner
            or provenance.get("decision_ref") != record.admission.decision_ref
        ):
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-PROVENANCE-DRIFT",
                    "projection admission provenance differs from the indexed Lifecycle",
                )
            )
            continue
        if (
            release.get("skill_id") != accepted_entry.get("skill_id")
            or release.get("skill_version") != accepted_entry.get("version")
            or release.get("manifest_path") != accepted_entry.get("manifest_path")
            or str(release.get("content_hash", "")).removeprefix("sha256:").lower()
            != str(accepted_entry.get("content_hash", "")).removeprefix("sha256:").lower()
            or str(release.get("package_hash", "")).removeprefix("sha256:").lower()
            != str(accepted_entry.get("package_hash", "")).removeprefix("sha256:").lower()
        ):
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-RELEASE-DRIFT",
                    "projection release facts differ from the accepted Registry",
                )
            )
            continue
        manifest_loaded = loaded_document_at(documents, release.get("manifest_path"))
        if manifest_loaded is None:
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-MANIFEST-MISSING",
                    "projection manifest is not loaded",
                )
            )
            continue
        manifest_path, manifest_document = manifest_loaded
        expected_manifest_hash = str(release.get("manifest_sha256", "")).removeprefix("sha256:").lower()
        if document_has_loaded_bytes(documents, manifest_path) and document_hash(documents, manifest_path) != expected_manifest_hash:
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-MANIFEST-HASH-MISMATCH",
                    "projection manifest_sha256 does not match the loaded Release manifest",
                )
            )
            continue
        try:
            manifest = SkillManifest.from_mapping(manifest_document)
            expected = projection_from_verified_release(
                lifecycle_entry=lifecycle_entry,
                manifest=manifest,
                manifest_sha256=expected_manifest_hash,
                projection_version=str(projection.get("projection_version")),
            )
        except (ContractError, ValueError) as exc:
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-DERIVATION-BLOCKED",
                    str(exc),
                )
            )
            continue
        if dict(projection) != expected:
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-DERIVATION-DRIFT",
                    "projection does not equal deterministic Release/Lifecycle derivation",
                )
            )
    return issues


__all__ = ["validate_skill_release_projections"]
