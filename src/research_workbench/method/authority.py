from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    mapping_tuple,
    require_string,
)
from research_workbench.method.models import MethodResolution


@dataclass(frozen=True, slots=True)
class DecisionAuthorityRule:
    decision_type: str
    agent: str
    resolver: str
    human: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DecisionAuthorityRule":
        return cls(
            decision_type=require_string(data, "decision_type"),
            agent=require_string(data, "agent"),
            resolver=require_string(data, "resolver"),
            human=require_string(data, "human"),
        )


@dataclass(frozen=True, slots=True)
class DecisionAuthorityMatrix:
    schema_version: str
    matrix_id: str
    version: str
    rules: tuple[DecisionAuthorityRule, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DecisionAuthorityMatrix":
        rules = tuple(DecisionAuthorityRule.from_mapping(item) for item in mapping_tuple(data, "rules"))
        if not rules:
            raise ContractError("rules", "must not be empty")
        types = tuple(rule.decision_type for rule in rules)
        if len(types) != len(set(types)):
            raise ContractError("rules.decision_type", "must be unique")
        return cls(
            schema_version=require_string(data, "schema_version"),
            matrix_id=require_string(data, "matrix_id"),
            version=require_string(data, "version"),
            rules=rules,
        )

    def rule(self, decision_type: str) -> DecisionAuthorityRule:
        for rule in self.rules:
            if rule.decision_type == decision_type:
                return rule
        raise ContractError("decision_type", f"is not governed by {self.matrix_id}: {decision_type}")


@dataclass(frozen=True, slots=True)
class AuthorityAssessment:
    allowed: bool
    errors: tuple[str, ...]
    human_gates_required: tuple[str, ...]


def assess_method_resolution(
    resolution: MethodResolution,
    matrix: DecisionAuthorityMatrix,
) -> AuthorityAssessment:
    """Fail closed on ungoverned or over-authorized method decisions."""

    errors: list[str] = []
    human_gates: list[str] = []
    seen: set[str] = set()
    for index, record in enumerate(resolution.decision_records):
        decision_type = require_string(record, "decision_type")
        actor = require_string(record, "decided_by")
        outcome = require_string(record, "outcome")
        try:
            rule = matrix.rule(decision_type)
        except ContractError as exc:
            errors.append(str(exc))
            continue
        seen.add(decision_type)
        if actor == "agent" and rule.agent not in {"decide", "execute-approved"}:
            errors.append(f"decision_records[{index}] agent cannot decide {decision_type}")
        if actor == "resolver" and rule.resolver != "decide":
            errors.append(f"decision_records[{index}] resolver cannot decide {decision_type}")
        if rule.human == "required" and actor != "human":
            human_gates.append(decision_type)
            if outcome in {"approved", "promoted", "relaxed", "published"}:
                errors.append(f"decision_records[{index}] {decision_type} requires a human decision")

    for mandatory in ("mode_action_selection", "minimal_mechanism"):
        if mandatory not in seen:
            errors.append(f"required decision record missing: {mandatory}")

    if not resolution.provider_neutral:
        errors.append("Method Resolution contains Provider/Model/Host/Adapter-specific fields")

    if resolution.status == "resolved" and resolution.human_gates:
        pending = [gate for gate in resolution.human_gates if gate.get("status") != "approved"]
        if pending:
            errors.append("resolved Method Resolution retains an unapproved Human Gate")

    return AuthorityAssessment(
        allowed=not errors,
        errors=tuple(errors),
        human_gates_required=tuple(sorted(set(human_gates))),
    )
