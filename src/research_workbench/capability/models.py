from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    PermissionPolicy,
    mapping_value,
    optional_string,
    require_string,
    string_tuple,
)


@dataclass(frozen=True, slots=True)
class AgentProfile:
    schema_version: str
    agent_profile_id: str
    version: str
    purpose: str
    model_policy: Mapping[str, Any]
    permission_ceiling: PermissionPolicy
    allowed_tool_capabilities: tuple[str, ...]
    default_context_policy: str
    delegation_allowed: bool
    output_contracts: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "AgentProfile":
        delegation = mapping_value(data, "delegation", required=True)
        allowed = delegation.get("allowed")
        if not isinstance(allowed, bool):
            raise ContractError("delegation.allowed", "must be boolean")
        return cls(
            schema_version=require_string(data, "schema_version"),
            agent_profile_id=require_string(data, "agent_profile_id"),
            version=require_string(data, "version"),
            purpose=require_string(data, "purpose"),
            model_policy=dict(mapping_value(data, "model_policy", required=True)),
            permission_ceiling=PermissionPolicy.from_mapping(
                mapping_value(data, "permission_ceiling", required=True)
            ),
            allowed_tool_capabilities=string_tuple(data, "allowed_tool_capabilities", required=True),
            default_context_policy=require_string(data, "default_context_policy"),
            delegation_allowed=allowed,
            output_contracts=string_tuple(data, "output_contracts", required=True),
        )


@dataclass(frozen=True, slots=True)
class SkillManifest:
    schema_version: str
    skill_id: str
    version: str
    kind: str
    description: str
    capabilities: tuple[str, ...]
    applies_to_modes: tuple[str, ...]
    excludes: tuple[str, ...]
    required_tools: tuple[str, ...]
    optional_tools: tuple[str, ...]
    permission_ceiling: PermissionPolicy
    input_contracts: tuple[str, ...]
    output_contracts: tuple[str, ...]
    context_cost: Mapping[str, str]
    incompatible_with: tuple[str, ...]
    deterministic_verification: tuple[str, ...]
    source_origin: str
    source_content_hash: str
    source_locator: str | None = None
    source_package_hash: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillManifest":
        verification = mapping_value(data, "verification", required=True)
        source = mapping_value(data, "source", required=True)
        context_cost = mapping_value(data, "context_cost", required=True)
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in context_cost.items()):
            raise ContractError("context_cost", "keys and values must be strings")
        return cls(
            schema_version=require_string(data, "schema_version"),
            skill_id=require_string(data, "skill_id"),
            version=require_string(data, "version"),
            kind=require_string(data, "kind"),
            description=require_string(data, "description"),
            capabilities=string_tuple(data, "capabilities", required=True),
            applies_to_modes=string_tuple(data, "applies_to_modes", required=True),
            excludes=string_tuple(data, "excludes"),
            required_tools=string_tuple(data, "required_tools"),
            optional_tools=string_tuple(data, "optional_tools"),
            permission_ceiling=PermissionPolicy.from_mapping(
                mapping_value(data, "permission_ceiling", required=True)
            ),
            input_contracts=string_tuple(data, "input_contracts", required=True),
            output_contracts=string_tuple(data, "output_contracts", required=True),
            context_cost=dict(context_cost),
            incompatible_with=string_tuple(data, "incompatible_with"),
            deterministic_verification=string_tuple(verification, "deterministic"),
            source_origin=require_string(source, "origin"),
            source_content_hash=require_string(source, "content_hash"),
            source_locator=optional_string(source, "locator"),
            source_package_hash=optional_string(source, "package_hash"),
        )


@dataclass(frozen=True, slots=True)
class SkillLock:
    skill_id: str
    version: str
    content_hash: str
    source_locator: str | None = None
    package_hash: str | None = None

    @property
    def identifier(self) -> str:
        return f"{self.skill_id}@{self.version}"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillLock":
        return cls(
            skill_id=require_string(data, "skill_id"),
            version=require_string(data, "version"),
            content_hash=require_string(data, "content_hash"),
            source_locator=optional_string(data, "source_locator"),
            package_hash=optional_string(data, "package_hash"),
        )
