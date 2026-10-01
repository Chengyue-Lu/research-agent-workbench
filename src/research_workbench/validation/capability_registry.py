"""Fail-closed Capability Requirement registry closure validation.

This module owns the authority-relevant closed-set seam previously embedded in
the broad document dispatcher.  It neither parses arbitrary document kinds nor
performs orchestration; it only proves that Requirement identities, paths,
hashes, and Method references belong to one exact index.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from research_workbench.validation.document_core import (
    ValidationIssue,
    document_has_loaded_bytes,
    document_hash,
    loaded_document_at,
    matches_repository_path,
)
from research_workbench.validation.document_kinds import infer_document_kind


def capability_requirement_indices(
    documents: Mapping[Path, Any],
) -> list[tuple[Path, Mapping[str, Any]]]:
    return [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping)
        and document.get("registry_kind") == "capability_requirement_index"
    ]


def capability_requirement_entries(
    documents: Mapping[Path, Any],
) -> dict[str, Mapping[str, Any]]:
    indices = capability_requirement_indices(documents)
    if len(indices) != 1:
        return {}
    entries: dict[str, Mapping[str, Any]] = {}
    for entry in indices[0][1].get("entries", []):
        if not isinstance(entry, Mapping) or not isinstance(
            entry.get("requirement_id"), str
        ):
            continue
        entries[str(entry["requirement_id"])] = entry
    return entries


def validate_capability_requirement_set(
    documents: Mapping[Path, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    indices = capability_requirement_indices(documents)
    requirement_documents = [
        (path, document)
        for path, document in documents.items()
        if isinstance(document, Mapping)
        and infer_document_kind(document) == "capability_requirement"
    ]
    method_references = [
        value
        for document in documents.values()
        if isinstance(document, Mapping)
        and infer_document_kind(document) == "method_resolution"
        for decision in document.get("action_decisions", [])
        if isinstance(decision, Mapping)
        for value in decision.get("capability_requirements", [])
        if isinstance(value, str)
    ]
    if not indices:
        if requirement_documents or method_references:
            anchor = (
                requirement_documents[0][0]
                if requirement_documents
                else Path("capability-requirements")
            )
            issues.append(
                ValidationIssue(
                    anchor,
                    "CAPABILITY-REQUIREMENT-INDEX-MISSING",
                    "Capability Requirement documents and Method references require one closed integrity index",
                )
            )
        return issues
    if len(indices) > 1:
        for path, _ in indices[1:]:
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-REQUIREMENT-INDEX-DUPLICATE",
                    "only one Capability Requirement integrity index may be loaded",
                )
            )
        return issues

    index_path, index = indices[0]
    indexed: dict[str, tuple[str, Mapping[str, Any]]] = {}
    seen_paths: set[str] = set()
    for position, entry in enumerate(index.get("entries", [])):
        if not isinstance(entry, Mapping):
            continue
        requirement_id = entry.get("requirement_id")
        document_path = entry.get("document_path")
        if not isinstance(requirement_id, str) or not isinstance(document_path, str):
            continue
        if requirement_id in indexed:
            issues.append(
                ValidationIssue(
                    index_path,
                    "CAPABILITY-REQUIREMENT-IDENTITY-DUPLICATE",
                    f"duplicate Requirement identity at entries[{position}]: {requirement_id}",
                )
            )
            continue
        if document_path in seen_paths:
            issues.append(
                ValidationIssue(
                    index_path,
                    "CAPABILITY-REQUIREMENT-PATH-DUPLICATE",
                    f"duplicate Requirement document path at entries[{position}]: {document_path}",
                )
            )
            continue
        indexed[requirement_id] = (document_path, entry)
        seen_paths.add(document_path)

        loaded = loaded_document_at(documents, document_path)
        if loaded is None:
            issues.append(
                ValidationIssue(
                    index_path,
                    "CAPABILITY-REQUIREMENT-DOCUMENT-MISSING",
                    f"indexed Requirement document is not loaded: {document_path}",
                )
            )
            continue
        loaded_path, requirement = loaded
        if infer_document_kind(requirement) != "capability_requirement":
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "CAPABILITY-REQUIREMENT-DOCUMENT-KIND",
                    f"indexed document is not a Capability Requirement: {document_path}",
                )
            )
            continue
        if requirement.get("requirement_id") != requirement_id:
            issues.append(
                ValidationIssue(
                    loaded_path,
                    "CAPABILITY-REQUIREMENT-IDENTITY-MISMATCH",
                    f"index and document identities disagree: {requirement_id}",
                )
            )
        expected_hash = entry.get("content_hash")
        if isinstance(expected_hash, str) and document_has_loaded_bytes(
            documents, loaded_path
        ):
            if document_hash(documents, loaded_path) != expected_hash.removeprefix(
                "sha256:"
            ).lower():
                issues.append(
                    ValidationIssue(
                        index_path,
                        "CAPABILITY-REQUIREMENT-HASH-MISMATCH",
                        f"content hash does not match Requirement document: {requirement_id}",
                    )
                )

    for path, requirement in requirement_documents:
        requirement_id = requirement.get("requirement_id")
        indexed_entry = indexed.get(str(requirement_id))
        if indexed_entry is None:
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-REQUIREMENT-UNINDEXED",
                    f"Requirement document is not in the integrity index: {requirement_id}",
                )
            )
        elif not matches_repository_path(path, indexed_entry[0]):
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-REQUIREMENT-PATH-MISMATCH",
                    f"Requirement document path disagrees with the index: {requirement_id}",
                )
            )
    return issues
