from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from research_workbench.artifacts.integrity import hash_bytes, resolve_within_root
from research_workbench.contracts.common import (
    ContractError,
    mapping_value,
    require_string,
    string_tuple,
)
from research_workbench.io import load_document, load_document_bytes


DEFAULT_PROTOCOL_PROFILES = Path("registry/protocol-profiles.json")


def _mapping_tuple(data: Mapping[str, Any], key: str) -> tuple[Mapping[str, Any], ...]:
    value = data.get(key)
    if not isinstance(value, list):
        raise ContractError(key, "must be an array")
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ContractError(f"{key}[{index}]", "must be an object")
        result.append(item)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class ProtocolMethodStandard:
    family: str
    edition: str
    profile_scope: str
    compliance_claim: str
    notes: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProtocolMethodStandard":
        return cls(
            family=require_string(data, "family"),
            edition=require_string(data, "edition"),
            profile_scope=require_string(data, "profile_scope"),
            compliance_claim=require_string(data, "compliance_claim"),
            notes=string_tuple(data, "notes", required=True),
        )


@dataclass(frozen=True, slots=True)
class ProtocolApplicability:
    applicable_when: tuple[str, ...]
    not_applicable_when: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProtocolApplicability":
        return cls(
            applicable_when=string_tuple(data, "applicable_when", required=True),
            not_applicable_when=string_tuple(data, "not_applicable_when", required=True),
        )


@dataclass(frozen=True, slots=True)
class ProtocolActionReference:
    action_ref: str
    content_hash: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProtocolActionReference":
        return cls(
            action_ref=require_string(data, "action_ref"),
            content_hash=require_string(data, "content_hash"),
        )


@dataclass(frozen=True, slots=True)
class ProtocolMethodObligation:
    obligation_id: str
    statement: str
    applies_to_action_refs: tuple[str, ...]
    evidence_expectation_refs: tuple[str, ...]
    gate_expectation_refs: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProtocolMethodObligation":
        return cls(
            obligation_id=require_string(data, "obligation_id"),
            statement=require_string(data, "statement"),
            applies_to_action_refs=string_tuple(
                data, "applies_to_action_refs", required=True
            ),
            evidence_expectation_refs=string_tuple(
                data, "evidence_expectation_refs", required=True
            ),
            gate_expectation_refs=string_tuple(data, "gate_expectation_refs"),
        )


@dataclass(frozen=True, slots=True)
class ProtocolEvidenceExpectation:
    expectation_id: str
    statement: str
    evidence_classes: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProtocolEvidenceExpectation":
        return cls(
            expectation_id=require_string(data, "expectation_id"),
            statement=require_string(data, "statement"),
            evidence_classes=string_tuple(data, "evidence_classes", required=True),
        )


@dataclass(frozen=True, slots=True)
class ProtocolGateExpectation:
    gate_ref: str
    effect: str
    rationale: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProtocolGateExpectation":
        return cls(
            gate_ref=require_string(data, "gate_ref"),
            effect=require_string(data, "effect"),
            rationale=require_string(data, "rationale"),
        )


@dataclass(frozen=True, slots=True)
class ProtocolProfileBoundaries:
    defines_global_dag: bool
    copies_mode_action_contract: bool
    binds_skill: bool
    binds_tool: bool
    binds_provider: bool
    binds_runtime: bool
    owns_routing: bool
    grants_claim_effect: bool
    grants_human_decision: bool

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProtocolProfileBoundaries":
        values: dict[str, bool] = {}
        for key in (
            "defines_global_dag",
            "copies_mode_action_contract",
            "binds_skill",
            "binds_tool",
            "binds_provider",
            "binds_runtime",
            "owns_routing",
            "grants_claim_effect",
            "grants_human_decision",
        ):
            value = data.get(key)
            if not isinstance(value, bool):
                raise ContractError(f"boundaries.{key}", "must be boolean")
            values[key] = value
        return cls(**values)


@dataclass(frozen=True, slots=True)
class ProtocolProfile:
    schema_version: str
    profile_id: str
    version: str
    title: str
    method_standard: ProtocolMethodStandard
    applicability: ProtocolApplicability
    compatible_mode_refs: tuple[str, ...]
    scoped_actions: tuple[ProtocolActionReference, ...]
    method_obligations: tuple[ProtocolMethodObligation, ...]
    evidence_expectations: tuple[ProtocolEvidenceExpectation, ...]
    gate_expectations: tuple[ProtocolGateExpectation, ...]
    boundaries: ProtocolProfileBoundaries

    @property
    def reference(self) -> str:
        return f"{self.profile_id}@{self.version}"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ProtocolProfile":
        return cls(
            schema_version=require_string(data, "schema_version"),
            profile_id=require_string(data, "profile_id"),
            version=require_string(data, "version"),
            title=require_string(data, "title"),
            method_standard=ProtocolMethodStandard.from_mapping(
                mapping_value(data, "method_standard", required=True)
            ),
            applicability=ProtocolApplicability.from_mapping(
                mapping_value(data, "applicability", required=True)
            ),
            compatible_mode_refs=string_tuple(
                data, "compatible_mode_refs", required=True
            ),
            scoped_actions=tuple(
                ProtocolActionReference.from_mapping(item)
                for item in _mapping_tuple(data, "scoped_actions")
            ),
            method_obligations=tuple(
                ProtocolMethodObligation.from_mapping(item)
                for item in _mapping_tuple(data, "method_obligations")
            ),
            evidence_expectations=tuple(
                ProtocolEvidenceExpectation.from_mapping(item)
                for item in _mapping_tuple(data, "evidence_expectations")
            ),
            gate_expectations=tuple(
                ProtocolGateExpectation.from_mapping(item)
                for item in _mapping_tuple(data, "gate_expectations")
            ),
            boundaries=ProtocolProfileBoundaries.from_mapping(
                mapping_value(data, "boundaries", required=True)
            ),
        )


@dataclass(frozen=True, slots=True)
class ProtocolProfileEntry:
    profile_ref: str
    profile_id: str
    version: str
    document_path: str
    content_hash: str
    profile: ProtocolProfile


@dataclass(frozen=True, slots=True)
class ProtocolProfileSet:
    index_path: Path
    project_root: Path
    entries: tuple[ProtocolProfileEntry, ...]

    @classmethod
    def load(
        cls,
        path: str | Path = DEFAULT_PROTOCOL_PROFILES,
        *,
        project_root: str | Path = ".",
    ) -> "ProtocolProfileSet":
        root = Path(project_root).resolve()
        index_path = Path(path)
        if not index_path.is_absolute():
            index_path = root / index_path
        index = load_document(index_path)
        if not isinstance(index, Mapping) or index.get("registry_kind") != "protocol_profile_index":
            raise ValueError(f"not a Protocol Profile integrity index: {index_path}")
        raw_entries = index.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError(f"Protocol Profile index has no entries list: {index_path}")

        entries: list[ProtocolProfileEntry] = []
        seen_refs: set[str] = set()
        seen_identities: set[tuple[str, str]] = set()
        seen_paths: set[str] = set()
        for position, raw in enumerate(raw_entries):
            if not isinstance(raw, Mapping):
                raise ValueError(f"Protocol Profile entry {position} is not an object")
            profile_ref = require_string(raw, "profile_ref")
            profile_id = require_string(raw, "profile_id")
            version = require_string(raw, "version")
            document_path = require_string(raw, "document_path")
            content_hash = require_string(raw, "content_hash").removeprefix("sha256:").lower()
            identity = (profile_id, version)
            if profile_ref in seen_refs:
                raise ValueError(f"duplicate Protocol Profile reference: {profile_ref}")
            if identity in seen_identities:
                raise ValueError(f"duplicate Protocol Profile identity: {profile_id}@{version}")
            if document_path in seen_paths:
                raise ValueError(f"duplicate Protocol Profile path: {document_path}")
            seen_refs.add(profile_ref)
            seen_identities.add(identity)
            seen_paths.add(document_path)

            resolved = resolve_within_root(root, document_path)
            if resolved is None or not resolved.is_file():
                raise ValueError(f"Protocol Profile path is missing or escapes root: {document_path}")
            content = resolved.read_bytes()
            if hash_bytes(content) != content_hash:
                raise ValueError(f"Protocol Profile content drift: {profile_ref}")
            document = load_document_bytes(resolved, content)
            if not isinstance(document, Mapping):
                raise ValueError(f"Protocol Profile is not an object: {document_path}")
            profile = ProtocolProfile.from_mapping(document)
            if profile.reference != profile_ref or (profile.profile_id, profile.version) != identity:
                raise ValueError(f"Protocol Profile identity mismatch: {profile_ref}")
            entries.append(
                ProtocolProfileEntry(
                    profile_ref=profile_ref,
                    profile_id=profile_id,
                    version=version,
                    document_path=document_path,
                    content_hash=content_hash,
                    profile=profile,
                )
            )
        return cls(index_path=index_path, project_root=root, entries=tuple(entries))

    def require(self, profile_refs: Iterable[str]) -> tuple[ProtocolProfile, ...]:
        requested = (profile_refs,) if isinstance(profile_refs, str) else tuple(profile_refs)
        by_ref = {entry.profile_ref: entry.profile for entry in self.entries}
        selected: list[ProtocolProfile] = []
        seen: set[str] = set()
        for profile_ref in requested:
            if profile_ref in seen:
                raise ValueError(f"Protocol Profile selected more than once: {profile_ref}")
            try:
                selected.append(by_ref[profile_ref])
            except KeyError as exc:
                raise ValueError(f"Protocol Profile is not indexed: {profile_ref}") from exc
            seen.add(profile_ref)
        return tuple(selected)
