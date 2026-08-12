from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    mapping_value,
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
