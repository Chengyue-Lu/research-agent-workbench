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


DEFAULT_SKILL_LIFECYCLE_INDEX = Path("registry/skills/lifecycle-v2.json")


@dataclass(frozen=True, slots=True)
class LifecycleSkillReference:
    skill_id: str
    version: str
    manifest_path: str
    content_hash: str
    package_hash: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "LifecycleSkillReference":
        return cls(
            skill_id=require_string(data, "skill_id"),
            version=require_string(data, "version"),
            manifest_path=require_string(data, "manifest_path"),
            content_hash=require_string(data, "content_hash"),
            package_hash=require_string(data, "package_hash"),
        )


@dataclass(frozen=True, slots=True)
class LifecycleIntake:
    state: str
    source_refs: tuple[str, ...]
    reason: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "LifecycleIntake":
        return cls(
            state=require_string(data, "state"),
            source_refs=string_tuple(data, "source_refs", required=True),
            reason=require_string(data, "reason"),
        )


@dataclass(frozen=True, slots=True)
class LifecycleEvaluation:
    state: str
    baseline_ref: str | None
    trial_ref: str | None
    evaluation_record_ref: str | None
    promotion_evidence_refs: tuple[str, ...]
    reason: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "LifecycleEvaluation":
        def optional(key: str) -> str | None:
            value = data.get(key)
            if value is not None and not isinstance(value, str):
                raise ContractError(f"evaluation.{key}", "must be a string")
            return value

        return cls(
            state=require_string(data, "state"),
            baseline_ref=optional("baseline_ref"),
            trial_ref=optional("trial_ref"),
            evaluation_record_ref=optional("evaluation_record_ref"),
            promotion_evidence_refs=string_tuple(data, "promotion_evidence_refs", required=True),
            reason=require_string(data, "reason"),
        )


@dataclass(frozen=True, slots=True)
class LifecycleAdmission:
    state: str
    decision_owner: str
    decision_ref: str | None
    reason: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "LifecycleAdmission":
        decision_ref = data.get("decision_ref")
        if decision_ref is not None and not isinstance(decision_ref, str):
            raise ContractError("admission.decision_ref", "must be a string")
        return cls(
            state=require_string(data, "state"),
            decision_owner=require_string(data, "decision_owner"),
            decision_ref=decision_ref,
            reason=require_string(data, "reason"),
        )


@dataclass(frozen=True, slots=True)
class RuntimeEligibility:
    state: str
    eligibility_ref: str
    scopes: tuple[str, ...]
    reason: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RuntimeEligibility":
        return cls(
            state=require_string(data, "state"),
            eligibility_ref=require_string(data, "eligibility_ref"),
            scopes=string_tuple(data, "scopes", required=True),
            reason=require_string(data, "reason"),
        )


@dataclass(frozen=True, slots=True)
class LifecycleDisposition:
    state: str
    superseded_by_refs: tuple[str, ...]
    reason: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "LifecycleDisposition":
        return cls(
            state=require_string(data, "state"),
            superseded_by_refs=string_tuple(data, "superseded_by_refs", required=True),
            reason=require_string(data, "reason"),
        )


@dataclass(frozen=True, slots=True)
class SkillLifecycleRecord:
    schema_version: str
    lifecycle_id: str
    lifecycle_version: str
    record_scope: str
    skill_ref: LifecycleSkillReference
    need_refs: tuple[str, ...]
    intake: LifecycleIntake
    evaluation: LifecycleEvaluation
    admission: LifecycleAdmission
    runtime_eligibility: RuntimeEligibility
    lifecycle: LifecycleDisposition

    @property
    def reference(self) -> str:
        return (
            f"{self.skill_ref.skill_id}@{self.skill_ref.version}"
            f"/lifecycle@{self.lifecycle_version}"
        )

    def eligible_for_new_binding(self) -> bool:
        return (
            self.record_scope == "current"
            and self.evaluation.state == "evidence-ready"
            and self.admission.state == "accepted"
            and self.admission.decision_owner == "human"
            and self.runtime_eligibility.state == "eligible"
            and self.lifecycle.state == "current"
        )

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SkillLifecycleRecord":
        return cls(
            schema_version=require_string(data, "schema_version"),
            lifecycle_id=require_string(data, "lifecycle_id"),
            lifecycle_version=require_string(data, "lifecycle_version"),
            record_scope=require_string(data, "record_scope"),
            skill_ref=LifecycleSkillReference.from_mapping(
                mapping_value(data, "skill_ref", required=True)
            ),
            need_refs=string_tuple(data, "need_refs", required=True),
            intake=LifecycleIntake.from_mapping(
                mapping_value(data, "intake", required=True)
            ),
            evaluation=LifecycleEvaluation.from_mapping(
                mapping_value(data, "evaluation", required=True)
            ),
            admission=LifecycleAdmission.from_mapping(
                mapping_value(data, "admission", required=True)
            ),
            runtime_eligibility=RuntimeEligibility.from_mapping(
                mapping_value(data, "runtime_eligibility", required=True)
            ),
            lifecycle=LifecycleDisposition.from_mapping(
                mapping_value(data, "lifecycle", required=True)
            ),
        )


@dataclass(frozen=True, slots=True)
class SkillLifecycleEntry:
    lifecycle_ref: str
    lifecycle_id: str
    lifecycle_version: str
    document_path: str
    content_hash: str
    record: SkillLifecycleRecord


@dataclass(frozen=True, slots=True)
class SkillLifecycleSet:
    index_path: Path
    project_root: Path
    entries: tuple[SkillLifecycleEntry, ...]

    @classmethod
    def load(
        cls,
        path: str | Path = DEFAULT_SKILL_LIFECYCLE_INDEX,
        *,
        project_root: str | Path = ".",
    ) -> "SkillLifecycleSet":
        root = Path(project_root).resolve()
        index_path = Path(path)
        if not index_path.is_absolute():
            index_path = root / index_path
        index = load_document(index_path)
        if not isinstance(index, Mapping) or index.get("registry_kind") != "skill_lifecycle_index":
            raise ValueError(f"not a Skill Lifecycle integrity index: {index_path}")
        raw_entries = index.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError(f"Skill Lifecycle index has no entries list: {index_path}")

        entries: list[SkillLifecycleEntry] = []
        seen_refs: set[str] = set()
        seen_identities: set[tuple[str, str]] = set()
        seen_paths: set[str] = set()
        for position, raw in enumerate(raw_entries):
            if not isinstance(raw, Mapping):
                raise ValueError(f"Skill Lifecycle entry {position} is not an object")
            lifecycle_ref = require_string(raw, "lifecycle_ref")
            lifecycle_id = require_string(raw, "lifecycle_id")
            lifecycle_version = require_string(raw, "lifecycle_version")
            document_path = require_string(raw, "document_path")
            content_hash = require_string(raw, "content_hash").removeprefix("sha256:").lower()
            identity = (lifecycle_id, lifecycle_version)
            if lifecycle_ref in seen_refs:
                raise ValueError(f"duplicate Skill Lifecycle reference: {lifecycle_ref}")
            if identity in seen_identities:
                raise ValueError(
                    f"duplicate Skill Lifecycle identity: {lifecycle_id}@{lifecycle_version}"
                )
            if document_path in seen_paths:
                raise ValueError(f"duplicate Skill Lifecycle path: {document_path}")
            seen_refs.add(lifecycle_ref)
            seen_identities.add(identity)
            seen_paths.add(document_path)

            resolved = resolve_within_root(root, document_path)
            if resolved is None or not resolved.is_file():
                raise ValueError(f"Skill Lifecycle path is missing or escapes root: {document_path}")
            if hash_file(resolved) != content_hash:
                raise ValueError(f"Skill Lifecycle content drift: {lifecycle_ref}")
            document = load_document(resolved)
            if not isinstance(document, Mapping):
                raise ValueError(f"Skill Lifecycle is not an object: {document_path}")
            record = SkillLifecycleRecord.from_mapping(document)
            if (
                record.reference != lifecycle_ref
                or record.lifecycle_id != lifecycle_id
                or record.lifecycle_version != lifecycle_version
            ):
                raise ValueError(f"Skill Lifecycle identity mismatch: {lifecycle_ref}")
            entries.append(
                SkillLifecycleEntry(
                    lifecycle_ref=lifecycle_ref,
                    lifecycle_id=lifecycle_id,
                    lifecycle_version=lifecycle_version,
                    document_path=document_path,
                    content_hash=content_hash,
                    record=record,
                )
            )
        return cls(index_path=index_path, project_root=root, entries=tuple(entries))

    def require(self, lifecycle_refs: Iterable[str]) -> tuple[SkillLifecycleRecord, ...]:
        requested = (lifecycle_refs,) if isinstance(lifecycle_refs, str) else tuple(lifecycle_refs)
        by_ref = {entry.lifecycle_ref: entry.record for entry in self.entries}
        selected: list[SkillLifecycleRecord] = []
        seen: set[str] = set()
        for lifecycle_ref in requested:
            if lifecycle_ref in seen:
                raise ValueError(f"Skill Lifecycle selected more than once: {lifecycle_ref}")
            try:
                selected.append(by_ref[lifecycle_ref])
            except KeyError as exc:
                raise ValueError(f"Skill Lifecycle is not indexed: {lifecycle_ref}") from exc
            seen.add(lifecycle_ref)
        return tuple(selected)

    def runtime_eligible(
        self,
        lifecycle_ref: str,
        eligibility_ref: str,
    ) -> bool:
        record = self.require((lifecycle_ref,))[0]
        return (
            record.runtime_eligibility.eligibility_ref == eligibility_ref
            and record.eligible_for_new_binding()
        )
