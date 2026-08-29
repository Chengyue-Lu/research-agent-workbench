"""Fail-closed Decision Authority registry and eligibility validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from research_workbench.contracts.common import ContractError
from research_workbench.protocol.authority import (
    DecisionAuthorityMatrix,
    evaluate_authority_rule_eligibility,
)
from research_workbench.validation.document_core import (
    ValidationIssue,
    document_hash as _document_hash,
    loaded_document_at as _loaded_document_at,
)
from research_workbench.validation.document_kinds import infer_document_kind


def validate_decision_authority(
    documents: Mapping[Path, Any]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    matrices: dict[str, tuple[Path, Mapping[str, Any]]] = {}
    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "decision_authority_matrix":
            continue
        try:
            matrix = DecisionAuthorityMatrix.from_mapping(document)
        except ContractError as error:
            issues.append(
                ValidationIssue(
                    path,
                    "DECISION-AUTHORITY-MATRIX-INVALID",
                    str(error),
                )
            )
            continue
        if matrix.reference in matrices:
            issues.append(
                ValidationIssue(
                    path,
                    "DECISION-AUTHORITY-MATRIX-DUPLICATE",
                    f"duplicate Matrix identity: {matrix.reference}",
                )
            )
        matrices[matrix.reference] = (path, document)

    seen_eligibility_records: set[str] = set()
    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "authority_rule_eligibility":
            continue
        eligibility_id = str(document.get("eligibility_id"))
        if eligibility_id in seen_eligibility_records:
            issues.append(
                ValidationIssue(
                    path,
                    "AUTHORITY-RULE-ELIGIBILITY-DUPLICATE",
                    f"duplicate eligibility_id: {eligibility_id}",
                )
            )
        seen_eligibility_records.add(eligibility_id)
        matrix_ref = document.get("matrix_ref")
        if not isinstance(matrix_ref, Mapping):
            continue
        loaded = _loaded_document_at(documents, matrix_ref.get("document_path"))
        if loaded is None:
            issues.append(
                ValidationIssue(
                    path,
                    "DECISION-AUTHORITY-MATRIX-MISSING",
                    "eligibility Matrix document is not loaded",
                )
            )
            continue
        matrix_path, matrix_document = loaded
        if matrices.get(str(matrix_ref.get("ref"))) != (matrix_path, matrix_document):
            issues.append(
                ValidationIssue(
                    path,
                    "DECISION-AUTHORITY-MATRIX-REF-MISMATCH",
                    "eligibility Matrix ref does not match the loaded Matrix",
                )
            )
            continue
        try:
            expected = evaluate_authority_rule_eligibility(
                document,
                matrix_document,
                matrix_content_hash=_document_hash(documents, matrix_path),
            )
        except ContractError as error:
            issues.append(
                ValidationIssue(
                    path,
                    "AUTHORITY-RULE-ELIGIBILITY-INVALID",
                    str(error),
                )
            )
            continue
        if document.get("result") != expected:
            issues.append(
                ValidationIssue(
                    path,
                    "DECISION-AUTHORITY-RESULT-MISMATCH",
                    "recorded result does not match deterministic rule-eligibility evaluation",
                )
            )
    return issues
