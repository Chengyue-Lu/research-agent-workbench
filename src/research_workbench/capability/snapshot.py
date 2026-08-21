"""Frozen binding between provider-neutral requirements and executable capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    ensure_unique,
    mapping_tuple,
    mapping_value,
    require_string,
    string_tuple,
)
from research_workbench.tasks.models import FileReference


@dataclass(frozen=True, slots=True)
class CapabilityBinding:
    requirement_id: str
    capability_id: str
    origin: str
    implementation_kind: str
    implementation_id: str
    source_ref: FileReference | None
    permissions: Mapping[str, Any]
    binding_details: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CapabilityBinding":
        source = data.get("source_ref")
        return cls(
            requirement_id=require_string(data, "requirement_id"),
            capability_id=require_string(data, "capability_id"),
            origin=require_string(data, "origin"),
            implementation_kind=require_string(data, "implementation_kind"),
            implementation_id=require_string(data, "implementation_id"),
            source_ref=FileReference.from_mapping(source) if isinstance(source, Mapping) else None,
            permissions=dict(mapping_value(data, "permissions", required=True)),
            binding_details=dict(mapping_value(data, "binding_details", required=True)),
        )


@dataclass(frozen=True, slots=True)
class ResolvedCapabilitySnapshot:
    schema_version: str
    snapshot_id: str
    task_ref: FileReference
    method_resolution_ref: FileReference
    status: str
    bindings: tuple[CapabilityBinding, ...]
    unresolved_requirement_ids: tuple[str, ...]
    resolved_by: str
    resolved_at: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ResolvedCapabilitySnapshot":
        status = require_string(data, "status")
        bindings = tuple(
            CapabilityBinding.from_mapping(item) for item in mapping_tuple(data, "bindings")
        )
        requirement_ids = tuple(binding.requirement_id for binding in bindings)
        ensure_unique(requirement_ids, "bindings.requirement_id")
        unresolved = ensure_unique(
            string_tuple(data, "unresolved_requirement_ids"),
            "unresolved_requirement_ids",
        )
        if set(requirement_ids) & set(unresolved):
            raise ContractError(
                "unresolved_requirement_ids",
                "must not repeat a requirement that already has a binding",
            )
        if status == "resolved" and unresolved:
            raise ContractError(
                "unresolved_requirement_ids",
                "must be empty when the snapshot status is resolved",
            )
        if status == "blocked" and not unresolved:
            raise ContractError(
                "unresolved_requirement_ids",
                "must preserve at least one gap when the snapshot status is blocked",
            )
        return cls(
            schema_version=require_string(data, "schema_version"),
            snapshot_id=require_string(data, "snapshot_id"),
            task_ref=FileReference.from_mapping(mapping_value(data, "task_ref", required=True)),
            method_resolution_ref=FileReference.from_mapping(
                mapping_value(data, "method_resolution_ref", required=True)
            ),
            status=status,
            bindings=bindings,
            unresolved_requirement_ids=unresolved,
            resolved_by=require_string(data, "resolved_by"),
            resolved_at=require_string(data, "resolved_at"),
        )

    def binding(self, requirement_id: str) -> CapabilityBinding:
        for binding in self.bindings:
            if binding.requirement_id == requirement_id:
                return binding
        raise ContractError(
            "bindings.requirement_id", f"has no resolved binding for {requirement_id}"
        )
