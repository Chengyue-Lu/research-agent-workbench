"""Repository-level closure validation for Phase C research documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from research_workbench.research_state import ClosureIndex, check_research_state
from research_workbench.validation.document_core import ValidationIssue
from research_workbench.validation.document_kinds import infer_document_kind


def validate_research_state_set(
    documents: Mapping[Path, Any],
) -> list[ValidationIssue]:
    """Validate every Research State against one exact repository closure."""

    if not any(
        isinstance(document, Mapping)
        and infer_document_kind(document) == "research_state"
        for document in documents.values()
    ):
        return []
    index = ClosureIndex.from_documents(documents)
    issues: list[ValidationIssue] = []
    for path, document in documents.items():
        if (
            not isinstance(document, Mapping)
            or infer_document_kind(document) != "research_state"
        ):
            continue
        for problem in check_research_state(document, index):
            issues.append(
                ValidationIssue(path, "RESEARCH-STATE-CLOSURE-INVALID", problem)
            )
    return issues
