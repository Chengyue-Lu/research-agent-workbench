from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    mapping_tuple,
    mapping_value,
    optional_string,
    require_string,
    string_tuple,
)


@dataclass(frozen=True, slots=True)
class ProjectBudget:
    max_parallel_subagents: int = 1
    max_delegation_depth: int = 1
    coordination_cost_ratio_warn: float = 0.33

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProjectBudget":
        parallel = data.get("max_parallel_subagents", 1)
        depth = data.get("max_delegation_depth", 1)
        ratio = data.get("coordination_cost_ratio_warn", 0.33)
        if not isinstance(parallel, int) or parallel < 0:
            raise ContractError("budgets.max_parallel_subagents", "must be a non-negative integer")
        if not isinstance(depth, int) or depth < 0:
            raise ContractError("budgets.max_delegation_depth", "must be a non-negative integer")
        if not isinstance(ratio, (int, float)) or not 0 <= ratio <= 1:
            raise ContractError("budgets.coordination_cost_ratio_warn", "must be between 0 and 1")
        return cls(parallel, depth, float(ratio))


@dataclass(frozen=True, slots=True)
class ProjectProtocol:
    schema_version: str
    project_id: str
    question_refs: tuple[str, ...]
    active_modes: tuple[str, ...]
    claim_ceiling: tuple[str, ...]
    required_human_gates: tuple[str, ...]
    budgets: ProjectBudget
    context_policy: Mapping[str, Any]
    data_boundary: Mapping[str, Any]
    revision: int = 1

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProjectProtocol":
        revision = data.get("revision", 1)
        if not isinstance(revision, int) or revision < 1:
            raise ContractError("revision", "must be a positive integer")
        return cls(
            schema_version=require_string(data, "schema_version"),
            project_id=require_string(data, "project_id"),
            question_refs=string_tuple(data, "question_refs", required=True),
            active_modes=string_tuple(data, "active_modes", required=True),
            claim_ceiling=string_tuple(data, "claim_ceiling", required=True),
            required_human_gates=string_tuple(data, "required_human_gates", required=True),
            budgets=ProjectBudget.from_mapping(mapping_value(data, "budgets", required=True)),
            context_policy=dict(mapping_value(data, "context_policy", required=True)),
            data_boundary=dict(mapping_value(data, "data_boundary", required=True)),
            revision=revision,
        )


@dataclass(frozen=True, slots=True)
class ResearchMode:
    schema_version: str
    mode_id: str
    version: str
    applies_when: tuple[str, ...]
    required_artifact_types: tuple[str, ...]
    recommended_skill_capabilities: tuple[str, ...]
    claim_allows: tuple[str, ...]
    claim_forbids_without_other_mode: tuple[str, ...]
    human_decisions: tuple[str, ...]
    risk_rules: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ResearchMode":
        claim_rules = mapping_value(data, "claim_rules", required=True)
        return cls(
            schema_version=require_string(data, "schema_version"),
            mode_id=require_string(data, "mode_id"),
            version=require_string(data, "version"),
            applies_when=string_tuple(data, "applies_when", required=True),
            required_artifact_types=string_tuple(data, "required_artifact_types", required=True),
            recommended_skill_capabilities=string_tuple(data, "recommended_skill_capabilities", required=True),
            claim_allows=string_tuple(claim_rules, "allows", required=True),
            claim_forbids_without_other_mode=string_tuple(claim_rules, "forbids_without_other_mode"),
            human_decisions=string_tuple(data, "human_decisions", required=True),
            risk_rules=string_tuple(data, "risk_rules", required=True),
            metadata=dict(mapping_value(data, "metadata")),
        )


@dataclass(frozen=True, slots=True)
class ModeActionClaimEffects:
    may_support: tuple[str, ...]
    cannot_alone_support: tuple[str, ...]
    notes: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ModeActionClaimEffects":
        return cls(
            may_support=string_tuple(data, "may_support", required=True),
            cannot_alone_support=string_tuple(data, "cannot_alone_support", required=True),
            notes=string_tuple(data, "notes", required=True),
        )


@dataclass(frozen=True, slots=True)
class ModeAction:
    schema_version: str
    action_id: str
    version: str
    mode_ref: str
    title: str
    intent: str
    triggers: tuple[str, ...]
    non_triggers: tuple[str, ...]
    failure_modes: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    claim_effects: ModeActionClaimEffects
    human_gates: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    blocked_conditions: tuple[str, ...]
    risk_rules: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def reference(self) -> str:
        return f"{self.action_id}@{self.version}"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ModeAction":
        return cls(
            schema_version=require_string(data, "schema_version"),
            action_id=require_string(data, "action_id"),
            version=require_string(data, "version"),
            mode_ref=require_string(data, "mode_ref"),
            title=require_string(data, "title"),
            intent=require_string(data, "intent"),
            triggers=string_tuple(data, "triggers", required=True),
            non_triggers=string_tuple(data, "non_triggers", required=True),
            failure_modes=string_tuple(data, "failure_modes", required=True),
            required_artifacts=string_tuple(data, "required_artifacts", required=True),
            claim_effects=ModeActionClaimEffects.from_mapping(
                mapping_value(data, "claim_effects", required=True)
            ),
            human_gates=string_tuple(data, "human_gates", required=True),
            stop_conditions=string_tuple(data, "stop_conditions", required=True),
            blocked_conditions=string_tuple(data, "blocked_conditions", required=True),
            risk_rules=string_tuple(data, "risk_rules"),
            metadata=dict(mapping_value(data, "metadata")),
        )


@dataclass(frozen=True, slots=True)
class MethodTaskRef:
    task_id: str
    revision: int
    sha256: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MethodTaskRef":
        revision = data.get("revision")
        if not isinstance(revision, int) or revision < 1:
            raise ContractError("task_ref.revision", "must be a positive integer")
        return cls(
            task_id=require_string(data, "task_id"),
            revision=revision,
            sha256=optional_string(data, "sha256"),
        )


@dataclass(frozen=True, slots=True)
class MethodModeResolution:
    status: str
    selected_mode_refs: tuple[str, ...]
    unresolved_mode_ids: tuple[str, ...]
    reason: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MethodModeResolution":
        return cls(
            status=require_string(data, "status"),
            selected_mode_refs=string_tuple(data, "selected_mode_refs", required=True),
            unresolved_mode_ids=string_tuple(data, "unresolved_mode_ids", required=True),
            reason=require_string(data, "reason"),
        )


@dataclass(frozen=True, slots=True)
class MethodObligation:
    obligation_id: str
    statement: str
    assessment: str
    required_evidence: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MethodObligation":
        return cls(
            obligation_id=require_string(data, "obligation_id"),
            statement=require_string(data, "statement"),
            assessment=require_string(data, "assessment"),
            required_evidence=string_tuple(data, "required_evidence", required=True),
        )


@dataclass(frozen=True, slots=True)
class MethodActionDecision:
    decision_id: str
    action_ref: str | None
    action_content_hash: str | None
    planning_action_id: str | None
    obligations: tuple[MethodObligation, ...]
    mechanisms: tuple[str, ...]
    capability_requirements: tuple[str, ...]
    skill_need_refs: tuple[str, ...]
    human_gate_refs: tuple[str, ...]
    blocked_conditions: tuple[str, ...]
    rationale: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MethodActionDecision":
        return cls(
            decision_id=require_string(data, "decision_id"),
            action_ref=optional_string(data, "action_ref"),
            action_content_hash=optional_string(data, "action_content_hash"),
            planning_action_id=optional_string(data, "planning_action_id"),
            obligations=tuple(
                MethodObligation.from_mapping(item)
                for item in mapping_tuple(data, "obligations")
            ),
            mechanisms=string_tuple(data, "mechanisms", required=True),
            capability_requirements=string_tuple(
                data, "capability_requirements", required=True
            ),
            skill_need_refs=string_tuple(data, "skill_need_refs", required=True),
            human_gate_refs=string_tuple(data, "human_gate_refs", required=True),
            blocked_conditions=string_tuple(data, "blocked_conditions", required=True),
            rationale=require_string(data, "rationale"),
        )


@dataclass(frozen=True, slots=True)
class MethodSkillDisposition:
    status: str
    need_refs: tuple[str, ...]
    reason: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MethodSkillDisposition":
        return cls(
            status=require_string(data, "status"),
            need_refs=string_tuple(data, "need_refs", required=True),
            reason=require_string(data, "reason"),
        )


@dataclass(frozen=True, slots=True)
class RejectedMethodAlternative:
    alternative_id: str
    disposition: str
    reason: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RejectedMethodAlternative":
        return cls(
            alternative_id=require_string(data, "alternative_id"),
            disposition=require_string(data, "disposition"),
            reason=require_string(data, "reason"),
        )


@dataclass(frozen=True, slots=True)
class MethodResolution:
    schema_version: str
    resolution_id: str
    revision: int
    task_ref: MethodTaskRef
    source_case_id: str
    mode_resolution: MethodModeResolution
    action_decisions: tuple[MethodActionDecision, ...]
    skill_disposition: MethodSkillDisposition
    human_gate_refs: tuple[str, ...]
    blocked_conditions: tuple[str, ...]
    rejected_alternatives: tuple[RejectedMethodAlternative, ...]
    resolution_status: str
    limitations: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MethodResolution":
        revision = data.get("revision")
        if not isinstance(revision, int) or revision < 1:
            raise ContractError("revision", "must be a positive integer")
        return cls(
            schema_version=require_string(data, "schema_version"),
            resolution_id=require_string(data, "resolution_id"),
            revision=revision,
            task_ref=MethodTaskRef.from_mapping(
                mapping_value(data, "task_ref", required=True)
            ),
            source_case_id=require_string(data, "source_case_id"),
            mode_resolution=MethodModeResolution.from_mapping(
                mapping_value(data, "mode_resolution", required=True)
            ),
            action_decisions=tuple(
                MethodActionDecision.from_mapping(item)
                for item in mapping_tuple(data, "action_decisions")
            ),
            skill_disposition=MethodSkillDisposition.from_mapping(
                mapping_value(data, "skill_disposition", required=True)
            ),
            human_gate_refs=string_tuple(data, "human_gate_refs", required=True),
            blocked_conditions=string_tuple(data, "blocked_conditions", required=True),
            rejected_alternatives=tuple(
                RejectedMethodAlternative.from_mapping(item)
                for item in mapping_tuple(data, "rejected_alternatives")
            ),
            resolution_status=require_string(data, "resolution_status"),
            limitations=string_tuple(data, "limitations", required=True),
        )
