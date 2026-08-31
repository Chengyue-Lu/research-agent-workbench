"""Fail-closed SkillReleaseProjection index and derivation validation."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping

from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.capability.catalog import DEFAULT_ACCEPTED
from research_workbench.capability.lifecycle import (
    DEFAULT_SKILL_LIFECYCLE_INDEX,
    SkillLifecycleEntry,
    SkillLifecycleRecord,
)
from research_workbench.capability.models import SkillManifest
from research_workbench.capability.release_projection import (
    DEFAULT_SKILL_RELEASE_PROJECTION_INDEX,
    SkillReleaseProjection,
    projection_from_verified_release,
)
from research_workbench.contracts.common import ContractError
from research_workbench.validation.document_core import (
    ValidationIssue,
    document_has_loaded_bytes,
    document_hash,
)
from research_workbench.validation.document_kinds import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog


def _indices(
    documents: Mapping[Path, Any],
) -> list[tuple[Path, Mapping[str, Any]]]:
    return [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping)
        and document.get("registry_kind") == "skill_release_projection_index"
    ]


def _loaded_document_at_root(
    documents: Mapping[Path, Any], root: Path, repository_relative: str
) -> tuple[Path, Mapping[str, Any]] | None:
    """Return one exact, portable repository-relative document or fail closed."""

    posix = PurePosixPath(repository_relative)
    windows = PureWindowsPath(repository_relative)
    if (
        not posix.parts
        or posix.as_posix() != repository_relative
        or "\\" in repository_relative
        or posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or any(part in {"", ".", ".."} for part in (*posix.parts, *windows.parts))
    ):
        return None
    try:
        root_path = root.resolve()
        canonical = root_path.joinpath(*posix.parts)
        target = resolve_within_root(root, repository_relative)
        if target is None or target != canonical:
            return None
        matches = [
            (path, document)
            for path, document in documents.items()
            if isinstance(document, Mapping)
            and not any(part in {".", ".."} for part in path.parts)
            and (path if path.is_absolute() else Path.cwd() / path) == canonical
            and path.resolve() == target
        ]
    except (OSError, RuntimeError):
        return None
    return matches[0] if len(matches) == 1 else None


def _accepted_entries(
    documents: Mapping[Path, Any], *, root: Path
) -> dict[str, Mapping[str, Any]]:
    entries: dict[str, Mapping[str, Any]] = {}
    loaded = _loaded_document_at_root(documents, root, DEFAULT_ACCEPTED.as_posix())
    if loaded is None or loaded[1].get("registry_kind") != "skill_accepted":
        return entries
    for entry in loaded[1].get("entries", []):
        if not isinstance(entry, Mapping):
            continue
        skill_id = entry.get("skill_id")
        version = entry.get("version")
        if isinstance(skill_id, str) and isinstance(version, str):
            entries[f"{skill_id}@{version}"] = entry
    return entries


def _lifecycle_entries(
    documents: Mapping[Path, Any], *, root: Path
) -> dict[str, tuple[Mapping[str, Any], SkillLifecycleEntry]]:
    result: dict[str, tuple[Mapping[str, Any], SkillLifecycleEntry]] = {}
    loaded_index = _loaded_document_at_root(
        documents, root, DEFAULT_SKILL_LIFECYCLE_INDEX.as_posix()
    )
    if (
        loaded_index is None
        or loaded_index[1].get("registry_kind") != "skill_lifecycle_index"
    ):
        return result
    for entry in loaded_index[1].get("entries", []):
        if not isinstance(entry, Mapping):
            continue
        lifecycle_ref = entry.get("lifecycle_ref")
        document_path = entry.get("document_path")
        content_hash = entry.get("content_hash")
        if not all(
            isinstance(value, str)
            for value in (lifecycle_ref, document_path, content_hash)
        ):
            continue
        loaded = _loaded_document_at_root(documents, root, str(document_path))
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


def _repository_root_for(path: Path, repository_relative: str) -> Path | None:
    """Recover the project root without accepting absolute or parent paths."""

    relative = PurePosixPath(repository_relative)
    if (
        relative.is_absolute()
        or not relative.parts
        or relative.as_posix() != repository_relative
        or "\\" in repository_relative
        or any(part in {"", ".", ".."} for part in relative.parts)
        or any(part in {".", ".."} for part in path.parts)
    ):
        return None
    absolute_path = path if path.is_absolute() else Path.cwd() / path
    root = absolute_path
    for _part in relative.parts:
        root = root.parent
    if root.joinpath(*relative.parts) != absolute_path:
        return None
    try:
        resolved_root = root.resolve()
        resolved_path = path.resolve()
    except (OSError, RuntimeError):
        return None
    expected = resolved_root.joinpath(*relative.parts)
    return resolved_root if expected == resolved_path else None


def _arm_evidence_paths(
    evaluation: Mapping[str, Any], arm_name: str
) -> set[str]:
    paths: set[str] = set()
    for case in evaluation.get("cases", []):
        if not isinstance(case, Mapping):
            continue
        arms = case.get("arms")
        arm = arms.get(arm_name) if isinstance(arms, Mapping) else None
        if not isinstance(arm, Mapping):
            continue
        for key in ("output_ref", "validation_ref"):
            reference = arm.get(key)
            path = reference.get("path") if isinstance(reference, Mapping) else None
            if isinstance(path, str):
                paths.add(path)
        receipt_ref = arm.get("execution_receipt_ref")
        if isinstance(receipt_ref, str):
            paths.add(receipt_ref)
    return paths


def _loaded_evidence(
    documents: Mapping[Path, Any], reference: str, *, root: Path
) -> tuple[Path, Mapping[str, Any]] | None:
    """Load one repository-root-anchored evidence document exactly.

    Publication authority must never inherit the legacy suffix matching used by
    general document discovery. A Lifecycle reference names one exact path in
    the repository anchored by the canonical Projection index. Missing,
    escaping, or aliased/multiply-loaded targets therefore fail closed.
    """

    loaded = _loaded_document_at_root(documents, root, reference)
    if loaded is None or not document_has_loaded_bytes(documents, loaded[0]):
        return None
    return loaded


def _publication_authority_verified(
    documents: Mapping[Path, Any], record: SkillLifecycleRecord, *, root: Path
) -> bool:
    """Revalidate the external Evaluation closure and its named Human Decision."""

    evaluation_ref = record.evaluation.evaluation_record_ref
    decision_ref = record.admission.decision_ref
    if evaluation_ref is None or decision_ref is None:
        return False
    loaded_evaluation = _loaded_evidence(documents, evaluation_ref, root=root)
    if loaded_evaluation is None:
        return False
    _, evaluation = loaded_evaluation
    if SchemaCatalog().validate("skill_evaluation", evaluation):
        return False
    if (
        evaluation.get("skill_id") != record.skill_ref.skill_id
        or evaluation.get("skill_version") != record.skill_ref.version
    ):
        return False
    admission = evaluation.get("admission")
    if (
        not isinstance(admission, Mapping)
        or admission.get("status") != "human-decided"
        or admission.get("outcome") != "accept"
        or admission.get("decision_ref") != decision_ref
    ):
        return False
    loaded_decision = _loaded_evidence(documents, decision_ref, root=root)
    if loaded_decision is None:
        return False
    decision = loaded_decision[1]
    if (
        decision.get("object_type") != "decision"
        or SchemaCatalog().validate("research_object", decision)
    ):
        return False

    # Import lazily because skill_evaluation imports the public validation
    # package; importing it while validation.documents is initialising cycles.
    from research_workbench.evaluation.skill_evaluation import assess_skill_evaluation

    assessment = assess_skill_evaluation(evaluation, root=root)
    if assessment.verdict != "human-decision-recorded":
        return False

    baseline_paths = _arm_evidence_paths(evaluation, "baseline")
    trial_paths = _arm_evidence_paths(evaluation, "with_skill")
    baseline_ref = record.evaluation.baseline_ref
    trial_ref = record.evaluation.trial_ref
    promotion_refs = record.evaluation.promotion_evidence_refs
    if (
        baseline_ref not in baseline_paths
        or trial_ref not in trial_paths
        or not promotion_refs
        or any(reference not in baseline_paths | trial_paths for reference in promotion_refs)
    ):
        return False
    verified_evidence = {
        reference
        for reference in (
            baseline_ref,
            trial_ref,
            evaluation_ref,
            *promotion_refs,
        )
        if reference is not None
        and _loaded_evidence(documents, reference, root=root) is not None
    }
    return record.externally_verified_for_new_binding(
        evidence_resolver=lambda reference: reference in verified_evidence,
        decision_resolver=lambda reference: reference == decision_ref,
    )


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
    repository_root = _repository_root_for(
        index_path, DEFAULT_SKILL_RELEASE_PROJECTION_INDEX.as_posix()
    )
    if repository_root is None:
        issues.append(
            ValidationIssue(
                index_path,
                "SKILL-RELEASE-PROJECTION-INDEX-PATH",
                "SkillReleaseProjection index is not at its canonical repository path",
            )
        )
        return issues
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

        loaded = _loaded_document_at_root(
            documents, repository_root, document_path
        )
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
        else:
            indexed_projection = _loaded_document_at_root(
                documents, repository_root, indexed_entry[0]
            )
            if indexed_projection is not None and indexed_projection[0] == path:
                continue
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-PATH-MISMATCH",
                    f"projection path disagrees with the index: {parsed.reference}",
                )
            )

    accepted = _accepted_entries(documents, root=repository_root)
    lifecycle = _lifecycle_entries(documents, root=repository_root)
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
        if not _publication_authority_verified(
            documents, record, root=repository_root
        ):
            issues.append(
                ValidationIssue(
                    path,
                    "SKILL-RELEASE-PROJECTION-AUTHORITY-UNVERIFIED",
                    "projection source external Evaluation evidence or named Human Decision is not verified",
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
        manifest_ref = release.get("manifest_path")
        manifest_loaded = (
            _loaded_document_at_root(documents, repository_root, manifest_ref)
            if isinstance(manifest_ref, str)
            else None
        )
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
