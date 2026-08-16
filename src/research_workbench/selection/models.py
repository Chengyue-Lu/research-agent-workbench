from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    mapping_tuple,
    mapping_value,
    require_string,
    string_tuple,
)
from research_workbench.tasks import FileReference


EVIDENCE_BASES = frozenset(
    {
        "bounded-source-set",
        "computational-model-output",
        "mixed-bounded-and-computational",
        "other-empirical",
        "none",
        "unknown",
    }
)


@dataclass(frozen=True, slots=True)
class ModeDecisionCard:
    schema_version: str
    card_id: str
    mode_id: str
    mode_version: str
    mode_ref: FileReference
    research_output_required: bool
    applies_evidence_bases: tuple[str, ...]
    does_not_apply_evidence_bases: tuple[str, ...]
    ambiguous_evidence_bases: tuple[str, ...]
    trigger_codes: tuple[str, ...]
    non_trigger_codes: tuple[str, ...]
    boundary_codes: tuple[str, ...]
    combination_rules: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ModeDecisionCard":
        basis = mapping_value(data, "decision_basis", required=True)
        required = basis.get("research_output_required")
        if not isinstance(required, bool):
            raise ContractError("decision_basis.research_output_required", "must be boolean")
        applies = string_tuple(basis, "applies_evidence_bases", required=True)
        excludes = string_tuple(basis, "does_not_apply_evidence_bases", required=True)
        ambiguous = string_tuple(basis, "ambiguous_evidence_bases", required=True)
        groups = (set(applies), set(excludes), set(ambiguous))
        if any(group - EVIDENCE_BASES for group in groups):
            raise ContractError("decision_basis", "contains an unsupported evidence basis")
        if (groups[0] & groups[1]) or (groups[0] & groups[2]) or (groups[1] & groups[2]):
            raise ContractError("decision_basis", "evidence basis groups must be disjoint")
        if set().union(*groups) != EVIDENCE_BASES:
            raise ContractError("decision_basis", "must classify every evidence basis")
        rules = mapping_value(data, "rules", required=True)
        return cls(
            schema_version=require_string(data, "schema_version"),
            card_id=require_string(data, "card_id"),
            mode_id=require_string(data, "mode_id"),
            mode_version=require_string(data, "mode_version"),
            mode_ref=FileReference.from_mapping(mapping_value(data, "mode_ref", required=True)),
            research_output_required=required,
            applies_evidence_bases=applies,
            does_not_apply_evidence_bases=excludes,
            ambiguous_evidence_bases=ambiguous,
            trigger_codes=tuple(require_string(item, "code") for item in mapping_tuple(rules, "triggers")),
            non_trigger_codes=tuple(
                require_string(item, "code") for item in mapping_tuple(rules, "non_triggers")
            ),
            boundary_codes=tuple(
                require_string(item, "code") for item in mapping_tuple(rules, "boundaries")
            ),
            combination_rules=mapping_tuple(data, "combination_rules"),
        )

    def disposition(self, evidence_basis: str, produces_research_output: bool) -> str:
        if self.research_output_required and not produces_research_output:
            return "excluded"
        if evidence_basis in self.applies_evidence_bases:
            return "selected"
        if evidence_basis in self.ambiguous_evidence_bases:
            return "plausible"
        return "excluded"


@dataclass(frozen=True, slots=True)
class ModeSkillSelectionDecision:
    schema_version: str
    selection_id: str
    task_ref: FileReference
    task_revision: int
    decision_owner: str
    mode_registry_digest: str
    accepted_skill_registry_digest: str
    evidence_basis: str
    produces_research_output: bool
    requested_claim_strengths: tuple[str, ...]
    available_input_contracts: tuple[str, ...]
    mode_assessment: Mapping[str, Any]
    skill_assessment: Mapping[str, Any]
    execution: Mapping[str, Any]
    read_plan: Mapping[str, Any]
    handoff: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ModeSkillSelectionDecision":
        revision = data.get("task_revision")
        if not isinstance(revision, int) or revision < 1:
            raise ContractError("task_revision", "must be a positive integer")
        registry = mapping_value(data, "registry_lock", required=True)
        signals = mapping_value(data, "task_signals", required=True)
        basis = require_string(signals, "evidence_basis")
        if basis not in EVIDENCE_BASES:
            raise ContractError("task_signals.evidence_basis", "is unsupported")
        produces = signals.get("produces_research_evidence_or_claim")
        if not isinstance(produces, bool):
            raise ContractError(
                "task_signals.produces_research_evidence_or_claim", "must be boolean"
            )
        return cls(
            schema_version=require_string(data, "schema_version"),
            selection_id=require_string(data, "selection_id"),
            task_ref=FileReference.from_mapping(mapping_value(data, "task_ref", required=True)),
            task_revision=revision,
            decision_owner=require_string(data, "decision_owner"),
            mode_registry_digest=require_string(registry, "mode_registry_digest").removeprefix("sha256:"),
            accepted_skill_registry_digest=require_string(
                registry, "accepted_skill_registry_digest"
            ).removeprefix("sha256:"),
            evidence_basis=basis,
            produces_research_output=produces,
            requested_claim_strengths=string_tuple(signals, "requested_claim_strengths", required=True),
            available_input_contracts=string_tuple(signals, "available_input_contracts", required=True),
            mode_assessment=mapping_value(data, "mode_assessment", required=True),
            skill_assessment=mapping_value(data, "skill_assessment", required=True),
            execution=mapping_value(data, "execution", required=True),
            read_plan=mapping_value(data, "read_plan", required=True),
            handoff=mapping_value(data, "handoff", required=True),
        )
