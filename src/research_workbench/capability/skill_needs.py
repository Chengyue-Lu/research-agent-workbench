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


DEFAULT_SKILL_NEEDS = Path("registry/skill-needs.json")


def _mapping_tuple(data: Mapping[str, Any], key: str) -> tuple[Mapping[str, Any], ...]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise ContractError(key, "must be a non-empty array")
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ContractError(f"{key}[{index}]", "must be an object")
        result.append(item)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class NeedActionReference:
    action_ref: str
    content_hash: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "NeedActionReference":
        return cls(
            action_ref=require_string(data, "action_ref"),
            content_hash=require_string(data, "content_hash"),
        )


@dataclass(frozen=True, slots=True)
class SkillNeedSemanticGap:
    missing_judgment: str
    failure_if_unaddressed: str
    why_not_mode_or_task: str
    why_not_direct_tool: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillNeedSemanticGap":
        return cls(
            missing_judgment=require_string(data, "missing_judgment"),
            failure_if_unaddressed=require_string(data, "failure_if_unaddressed"),
            why_not_mode_or_task=require_string(data, "why_not_mode_or_task"),
            why_not_direct_tool=require_string(data, "why_not_direct_tool"),
        )


@dataclass(frozen=True, slots=True)
class SkillNeedBaseline:
    route: str
    capability_requirement_refs: tuple[str, ...]
    procedure: tuple[str, ...]
    known_limitations: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillNeedBaseline":
        return cls(
            route=require_string(data, "route"),
            capability_requirement_refs=string_tuple(
                data, "capability_requirement_refs", required=True
            ),
            procedure=string_tuple(data, "procedure", required=True),
            known_limitations=string_tuple(data, "known_limitations", required=True),
        )


@dataclass(frozen=True, slots=True)
class SkillNeedExpectedIncrement:
    outcomes: tuple[str, ...]
    non_goals: tuple[str, ...]
    minimum_decision_rule: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillNeedExpectedIncrement":
        return cls(
            outcomes=string_tuple(data, "outcomes", required=True),
            non_goals=string_tuple(data, "non_goals", required=True),
            minimum_decision_rule=require_string(data, "minimum_decision_rule"),
        )


@dataclass(frozen=True, slots=True)
class RequiredEvidenceClass:
    evidence_class_id: str
    description: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RequiredEvidenceClass":
        return cls(
            evidence_class_id=require_string(data, "evidence_class_id"),
            description=require_string(data, "description"),
        )


@dataclass(frozen=True, slots=True)
class SkillNeedCriterion:
    criterion_id: str
    description: str
    assessment: str
    evidence_class_refs: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillNeedCriterion":
        return cls(
            criterion_id=require_string(data, "criterion_id"),
            description=require_string(data, "description"),
            assessment=require_string(data, "assessment"),
            evidence_class_refs=string_tuple(data, "evidence_class_refs", required=True),
        )


@dataclass(frozen=True, slots=True)
class SkillNeedEvaluationRequirements:
    comparison_arms: tuple[str, ...]
    required_evidence_classes: tuple[RequiredEvidenceClass, ...]
    criteria: tuple[SkillNeedCriterion, ...]
    coverage_requirements: tuple[str, ...]
    stop_conditions: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillNeedEvaluationRequirements":
        return cls(
            comparison_arms=string_tuple(data, "comparison_arms", required=True),
            required_evidence_classes=tuple(
                RequiredEvidenceClass.from_mapping(item)
                for item in _mapping_tuple(data, "required_evidence_classes")
            ),
            criteria=tuple(
                SkillNeedCriterion.from_mapping(item)
                for item in _mapping_tuple(data, "criteria")
            ),
            coverage_requirements=string_tuple(data, "coverage_requirements", required=True),
            stop_conditions=string_tuple(data, "stop_conditions", required=True),
        )


@dataclass(frozen=True, slots=True)
class SkillNeedDomainVariant:
    variant_id: str
    applies_when: str
    variation: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillNeedDomainVariant":
        return cls(
            variant_id=require_string(data, "variant_id"),
            applies_when=require_string(data, "applies_when"),
            variation=require_string(data, "variation"),
        )


@dataclass(frozen=True, slots=True)
class SkillNeedDomainScope:
    included: tuple[str, ...]
    excluded: tuple[str, ...]
    variants: tuple[SkillNeedDomainVariant, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillNeedDomainScope":
        return cls(
            included=string_tuple(data, "included", required=True),
            excluded=string_tuple(data, "excluded", required=True),
            variants=tuple(
                SkillNeedDomainVariant.from_mapping(item)
                for item in _mapping_tuple(data, "variants")
            ),
        )


@dataclass(frozen=True, slots=True)
class SkillNeedBoundaries:
    records_trial_results: bool
    records_evaluation_results: bool
    records_promotion_evidence: bool
    records_runtime_eligibility: bool
    is_candidate: bool
    is_assignment: bool
    promotion_owner: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillNeedBoundaries":
        booleans: dict[str, bool] = {}
        for key in (
            "records_trial_results",
            "records_evaluation_results",
            "records_promotion_evidence",
            "records_runtime_eligibility",
            "is_candidate",
            "is_assignment",
        ):
            value = data.get(key)
            if not isinstance(value, bool):
                raise ContractError(key, "must be boolean")
            booleans[key] = value
        return cls(
            **booleans,
            promotion_owner=require_string(data, "promotion_owner"),
        )


@dataclass(frozen=True, slots=True)
class SkillNeed:
    schema_version: str
    need_ref: str
    need_id: str
    version: str
    title: str
    mode_refs: tuple[str, ...]
    origin_actions: tuple[NeedActionReference, ...]
    triggers: tuple[str, ...]
    non_triggers: tuple[str, ...]
    semantic_gap: SkillNeedSemanticGap
    baseline: SkillNeedBaseline
    expected_increment: SkillNeedExpectedIncrement
    evaluation_requirements: SkillNeedEvaluationRequirements
    domain_scope: SkillNeedDomainScope
    boundaries: SkillNeedBoundaries

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillNeed":
        return cls(
            schema_version=require_string(data, "schema_version"),
            need_ref=require_string(data, "need_ref"),
            need_id=require_string(data, "need_id"),
            version=require_string(data, "version"),
            title=require_string(data, "title"),
            mode_refs=string_tuple(data, "mode_refs", required=True),
            origin_actions=tuple(
                NeedActionReference.from_mapping(item)
                for item in _mapping_tuple(data, "origin_actions")
            ),
            triggers=string_tuple(data, "triggers", required=True),
            non_triggers=string_tuple(data, "non_triggers", required=True),
            semantic_gap=SkillNeedSemanticGap.from_mapping(
                mapping_value(data, "semantic_gap", required=True)
            ),
            baseline=SkillNeedBaseline.from_mapping(
                mapping_value(data, "baseline", required=True)
            ),
            expected_increment=SkillNeedExpectedIncrement.from_mapping(
                mapping_value(data, "expected_increment", required=True)
            ),
            evaluation_requirements=SkillNeedEvaluationRequirements.from_mapping(
                mapping_value(data, "evaluation_requirements", required=True)
            ),
            domain_scope=SkillNeedDomainScope.from_mapping(
                mapping_value(data, "domain_scope", required=True)
            ),
            boundaries=SkillNeedBoundaries.from_mapping(
                mapping_value(data, "boundaries", required=True)
            ),
        )


@dataclass(frozen=True, slots=True)
class SkillNeedEntry:
    need_ref: str
    need_id: str
    version: str
    document_path: str
    content_hash: str
    need: SkillNeed


@dataclass(frozen=True, slots=True)
class SkillNeedSet:
    index_path: Path
    project_root: Path
    entries: tuple[SkillNeedEntry, ...]

    @classmethod
    def load(
        cls,
        path: str | Path = DEFAULT_SKILL_NEEDS,
        *,
        project_root: str | Path = ".",
    ) -> "SkillNeedSet":
        root = Path(project_root).resolve()
        index_path = Path(path)
        if not index_path.is_absolute():
            index_path = root / index_path
        index = load_document(index_path)
        if not isinstance(index, Mapping) or index.get("registry_kind") != "skill_need_index":
            raise ValueError(f"not a Skill Need integrity index: {index_path}")
        raw_entries = index.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError(f"Skill Need index has no entries list: {index_path}")

        entries: list[SkillNeedEntry] = []
        seen_refs: set[str] = set()
        seen_identities: set[tuple[str, str]] = set()
        seen_paths: set[str] = set()
        for position, raw in enumerate(raw_entries):
            if not isinstance(raw, Mapping):
                raise ValueError(f"Skill Need entry {position} is not an object")
            need_ref = require_string(raw, "need_ref")
            need_id = require_string(raw, "need_id")
            version = require_string(raw, "version")
            document_path = require_string(raw, "document_path")
            content_hash = require_string(raw, "content_hash").removeprefix("sha256:").lower()
            identity = (need_id, version)
            if need_ref in seen_refs:
                raise ValueError(f"duplicate Skill Need reference: {need_ref}")
            if identity in seen_identities:
                raise ValueError(f"duplicate Skill Need identity: {need_id}@{version}")
            if document_path in seen_paths:
                raise ValueError(f"duplicate Skill Need path: {document_path}")
            seen_refs.add(need_ref)
            seen_identities.add(identity)
            seen_paths.add(document_path)

            resolved = resolve_within_root(root, document_path)
            if resolved is None or not resolved.is_file():
                raise ValueError(f"Skill Need path is missing or escapes root: {document_path}")
            if hash_file(resolved) != content_hash:
                raise ValueError(f"Skill Need content drift: {need_ref}")
            document = load_document(resolved)
            if not isinstance(document, Mapping):
                raise ValueError(f"Skill Need is not an object: {document_path}")
            need = SkillNeed.from_mapping(document)
            if (need.need_ref, need.need_id, need.version) != (need_ref, need_id, version):
                raise ValueError(f"Skill Need identity mismatch: {need_ref}")
            entries.append(
                SkillNeedEntry(
                    need_ref=need_ref,
                    need_id=need_id,
                    version=version,
                    document_path=document_path,
                    content_hash=content_hash,
                    need=need,
                )
            )
        return cls(index_path=index_path, project_root=root, entries=tuple(entries))

    def require(self, need_refs: Iterable[str]) -> tuple[SkillNeed, ...]:
        requested = (need_refs,) if isinstance(need_refs, str) else tuple(need_refs)
        by_ref = {entry.need_ref: entry.need for entry in self.entries}
        selected: list[SkillNeed] = []
        seen: set[str] = set()
        for need_ref in requested:
            if need_ref in seen:
                raise ValueError(f"Skill Need selected more than once: {need_ref}")
            try:
                selected.append(by_ref[need_ref])
            except KeyError as exc:
                raise ValueError(f"Skill Need is not indexed: {need_ref}") from exc
            seen.add(need_ref)
        return tuple(selected)
