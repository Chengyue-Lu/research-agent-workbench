from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.contracts.common import (
    ContractError,
    mapping_value,
    require_string,
    string_tuple,
)
from research_workbench.io import load_document


DEFAULT_CAPABILITY_REQUIREMENTS = Path("registry/capabilities/requirements.json")


@dataclass(frozen=True, slots=True)
class RequirementPermissionCeiling:
    filesystem: str
    network: str
    external_write: bool

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RequirementPermissionCeiling":
        external_write = data.get("external_write")
        if not isinstance(external_write, bool):
            raise ContractError("constraints.permission_ceiling.external_write", "must be boolean")
        return cls(
            filesystem=require_string(data, "filesystem"),
            network=require_string(data, "network"),
            external_write=external_write,
        )


@dataclass(frozen=True, slots=True)
class DataEgressConstraint:
    policy: str
    allowed_payloads: tuple[str, ...]
    forbidden_payloads: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DataEgressConstraint":
        return cls(
            policy=require_string(data, "policy"),
            allowed_payloads=string_tuple(data, "allowed_payloads", required=True),
            forbidden_payloads=string_tuple(data, "forbidden_payloads", required=True),
        )


@dataclass(frozen=True, slots=True)
class SideEffectConstraint:
    policy: str
    allowed_effects: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SideEffectConstraint":
        return cls(
            policy=require_string(data, "policy"),
            allowed_effects=string_tuple(data, "allowed_effects", required=True),
        )


@dataclass(frozen=True, slots=True)
class CapabilityConstraints:
    permission_ceiling: RequirementPermissionCeiling
    data_egress: DataEgressConstraint
    side_effects: SideEffectConstraint

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CapabilityConstraints":
        return cls(
            permission_ceiling=RequirementPermissionCeiling.from_mapping(
                mapping_value(data, "permission_ceiling", required=True)
            ),
            data_egress=DataEgressConstraint.from_mapping(
                mapping_value(data, "data_egress", required=True)
            ),
            side_effects=SideEffectConstraint.from_mapping(
                mapping_value(data, "side_effects", required=True)
            ),
        )


@dataclass(frozen=True, slots=True)
class VerificationExpectations:
    deterministic: tuple[str, ...]
    semantic: tuple[str, ...]
    human: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "VerificationExpectations":
        return cls(
            deterministic=string_tuple(data, "deterministic", required=True),
            semantic=string_tuple(data, "semantic", required=True),
            human=string_tuple(data, "human", required=True),
        )


@dataclass(frozen=True, slots=True)
class UnsatisfiedRequirementBoundary:
    method_contract: str
    supply_binding: str
    next_stage: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "UnsatisfiedRequirementBoundary":
        return cls(
            method_contract=require_string(data, "method_contract"),
            supply_binding=require_string(data, "supply_binding"),
            next_stage=require_string(data, "next_stage"),
        )


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    schema_version: str
    requirement_id: str
    objective: str
    applies_when: tuple[str, ...]
    not_applicable_when: tuple[str, ...]
    required_inputs: tuple[str, ...]
    required_outputs: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    constraints: CapabilityConstraints
    verification_expectations: VerificationExpectations
    unsatisfied_requirement: UnsatisfiedRequirementBoundary

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CapabilityRequirement":
        return cls(
            schema_version=require_string(data, "schema_version"),
            requirement_id=require_string(data, "requirement_id"),
            objective=require_string(data, "objective"),
            applies_when=string_tuple(data, "applies_when", required=True),
            not_applicable_when=string_tuple(data, "not_applicable_when", required=True),
            required_inputs=string_tuple(data, "required_inputs", required=True),
            required_outputs=string_tuple(data, "required_outputs", required=True),
            required_artifacts=string_tuple(data, "required_artifacts", required=True),
            constraints=CapabilityConstraints.from_mapping(
                mapping_value(data, "constraints", required=True)
            ),
            verification_expectations=VerificationExpectations.from_mapping(
                mapping_value(data, "verification_expectations", required=True)
            ),
            unsatisfied_requirement=UnsatisfiedRequirementBoundary.from_mapping(
                mapping_value(data, "unsatisfied_requirement", required=True)
            ),
        )


@dataclass(frozen=True, slots=True)
class CapabilityRequirementEntry:
    requirement_id: str
    document_path: str
    content_hash: str
    requirement: CapabilityRequirement


@dataclass(frozen=True, slots=True)
class CapabilityRequirementSet:
    index_path: Path
    project_root: Path
    entries: tuple[CapabilityRequirementEntry, ...]

    @classmethod
    def load(
        cls,
        path: str | Path = DEFAULT_CAPABILITY_REQUIREMENTS,
        *,
        project_root: str | Path = ".",
    ) -> "CapabilityRequirementSet":
        root = Path(project_root).resolve()
        index_path = Path(path)
        if not index_path.is_absolute():
            index_path = root / index_path
        index = load_document(index_path)
        if not isinstance(index, Mapping) or index.get("registry_kind") != "capability_requirement_index":
            raise ValueError(f"not a Capability Requirement integrity index: {index_path}")
        raw_entries = index.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError(f"Capability Requirement index has no entries list: {index_path}")

        entries: list[CapabilityRequirementEntry] = []
        seen_ids: set[str] = set()
        seen_paths: set[str] = set()
        for position, raw in enumerate(raw_entries):
            if not isinstance(raw, Mapping):
                raise ValueError(f"Capability Requirement entry {position} is not an object")
            requirement_id = require_string(raw, "requirement_id")
            document_path = require_string(raw, "document_path")
            content_hash = require_string(raw, "content_hash").removeprefix("sha256:").lower()
            if requirement_id in seen_ids:
                raise ValueError(f"duplicate Capability Requirement identity: {requirement_id}")
            if document_path in seen_paths:
                raise ValueError(f"duplicate Capability Requirement path: {document_path}")
            seen_ids.add(requirement_id)
            seen_paths.add(document_path)

            resolved = resolve_within_root(root, document_path)
            if resolved is None or not resolved.is_file():
                raise ValueError(f"Capability Requirement path is missing or escapes root: {document_path}")
            if hash_file(resolved) != content_hash:
                raise ValueError(f"Capability Requirement content drift: {requirement_id}")
            document = load_document(resolved)
            if not isinstance(document, Mapping):
                raise ValueError(f"Capability Requirement is not an object: {document_path}")
            requirement = CapabilityRequirement.from_mapping(document)
            if requirement.requirement_id != requirement_id:
                raise ValueError(f"Capability Requirement identity mismatch: {requirement_id}")
            entries.append(
                CapabilityRequirementEntry(
                    requirement_id=requirement_id,
                    document_path=document_path,
                    content_hash=content_hash,
                    requirement=requirement,
                )
            )
        return cls(index_path=index_path, project_root=root, entries=tuple(entries))

    def require(self, requirement_ids: Iterable[str]) -> tuple[CapabilityRequirement, ...]:
        requested = (requirement_ids,) if isinstance(requirement_ids, str) else tuple(requirement_ids)
        by_id = {entry.requirement_id: entry.requirement for entry in self.entries}
        selected: list[CapabilityRequirement] = []
        seen: set[str] = set()
        for requirement_id in requested:
            if requirement_id in seen:
                raise ValueError(f"Capability Requirement selected more than once: {requirement_id}")
            try:
                selected.append(by_id[requirement_id])
            except KeyError as exc:
                raise ValueError(f"Capability Requirement is not indexed: {requirement_id}") from exc
            seen.add(requirement_id)
        return tuple(selected)
