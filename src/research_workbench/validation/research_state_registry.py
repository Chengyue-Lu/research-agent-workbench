"""Repository-level closure validation for Phase C research documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from research_workbench.research_state.closure import (
    ClosureIndex,
    check_research_attempt_lineage,
    check_research_failure,
    check_research_state,
    check_method_trace,
)
from research_workbench.validation.document_core import ValidationIssue
from research_workbench.validation.document_kinds import infer_document_kind


def validate_research_state_set(
    documents: Mapping[Path, Any],
) -> list[ValidationIssue]:
    """Validate every Research State against one exact repository closure."""

    checkers = {
        "research_state": (check_research_state, "RESEARCH-STATE-CLOSURE-INVALID"),
        "research_attempt_lineage": (
            check_research_attempt_lineage,
            "RESEARCH-ATTEMPT-CLOSURE-INVALID",
        ),
        "research_failure": (
            check_research_failure,
            "RESEARCH-FAILURE-CLOSURE-INVALID",
        ),
        "method_trace": (check_method_trace, "METHOD-TRACE-CLOSURE-INVALID"),
    }
    if not any(
        isinstance(document, Mapping) and infer_document_kind(document) in checkers
        for document in documents.values()
    ):
        return []
    index = ClosureIndex.from_documents(documents)
    issues: list[ValidationIssue] = []
    for path, document in documents.items():
        if not isinstance(document, Mapping):
            continue
        kind = infer_document_kind(document)
        if kind not in checkers:
            continue
        checker, code = checkers[kind]
        for problem in checker(document, index):
            issues.append(ValidationIssue(path, code, problem))
    return issues
