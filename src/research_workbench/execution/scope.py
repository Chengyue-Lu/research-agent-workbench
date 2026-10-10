"""Exact Method-local selectors for the two execution-slice identities."""

from __future__ import annotations

from typing import Any, Mapping


def execution_selector(scope: Mapping[str, Any]) -> tuple[str, str]:
    """Reject ambiguous selectors; a planning ID is scoped by the pinned Method."""
    fields = {
        "action-capability-slice": "action_ref",
        "planning-capability-slice": "planning_action_id",
    }
    kind = scope.get("kind")
    field = fields.get(kind) if isinstance(kind, str) else None
    if field is None:
        raise ValueError("Unknown execution slice kind")
    other = "planning_action_id" if field == "action_ref" else "action_ref"
    value = scope.get(field)
    if other in scope or not isinstance(value, str) or not value:
        raise ValueError("Execution slice requires exactly its kind's selector")
    return field, value


def selected_method_decision(
    scope: Mapping[str, Any], method: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Resolve only within the caller's already exact-pinned Method document."""
    field, value = execution_selector(scope)
    other = "planning_action_id" if field == "action_ref" else "action_ref"
    matches = [
        decision for decision in method.get("action_decisions", ())
        if isinstance(decision, Mapping)
        and decision.get(field) == value and other not in decision
    ]
    if len(matches) != 1 or method.get("resolution_status") != "proceed":
        raise ValueError("Execution slice requires one exact proceed Method decision")
    return matches[0]


def slice_completion_claim(scope: Mapping[str, Any]) -> str:
    execution_selector(scope)
    return str(scope["kind"]) + "-only"
