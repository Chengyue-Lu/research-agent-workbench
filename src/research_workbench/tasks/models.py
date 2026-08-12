from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    PermissionPolicy,
    mapping_tuple,
    mapping_value,
    optional_string,
    require_relative_path,
    require_string,
    string_tuple,
)


SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")


@dataclass(frozen=True, slots=True)
class FileReference:
    path: str
    sha256: str
    revision: int | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "FileReference":
        path = require_relative_path(require_string(data, "path"), "path")
        sha256 = require_string(data, "sha256")
        if not SHA256_RE.fullmatch(sha256):
            raise ContractError("sha256", "must be a SHA-256 digest")
        revision = data.get("revision")
        if revision is not None and (not isinstance(revision, int) or revision < 1):
            raise ContractError("revision", "must be a positive integer")
        return cls(path, sha256.removeprefix("sha256:").lower(), revision)


@dataclass(frozen=True, slots=True)
class DelegationPolicy:
    allowed: bool = False
    max_depth: int = 0
    max_parallel: int = 0
    sub_budget: Mapping[str, int | float] | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DelegationPolicy":
        allowed = data.get("allowed")
        if not isinstance(allowed, bool):
            raise ContractError("delegation.allowed", "must be boolean")
        max_depth = data.get("max_depth", 0)
        max_parallel = data.get("max_parallel", 0)
        if not isinstance(max_depth, int) or max_depth < 0:
            raise ContractError("delegation.max_depth", "must be a non-negative integer")
        if not isinstance(max_parallel, int) or max_parallel < 0:
            raise ContractError("delegation.max_parallel", "must be a non-negative integer")
        if not allowed and (max_depth or max_parallel):
            raise ContractError("delegation", "limits must be zero when delegation is disabled")
        sub_budget = data.get("sub_budget")
        if sub_budget is not None and not isinstance(sub_budget, Mapping):
            raise ContractError("delegation.sub_budget", "must be an object")
        return cls(allowed, max_depth, max_parallel, dict(sub_budget) if sub_budget else None)


@dataclass(frozen=True, slots=True)
class TaskBudget:
    max_turns: int | None = None
    max_output_tokens: int | None = None
    max_seconds: int | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "TaskBudget":
        values: dict[str, int | None] = {}
        for field in ("max_turns", "max_output_tokens", "max_seconds"):
            value = data.get(field)
            if value is not None and (not isinstance(value, int) or value <= 0):
                raise ContractError(f"budget.{field}", "must be a positive integer")
            values[field] = value
        return cls(**values)


@dataclass(frozen=True, slots=True)
class HandoffPolicy:
    require_transfer_manifest: bool = False
    semantic_review: str = "risk-triggered"
    minimum_semantic_samples: int = 1

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "HandoffPolicy":
        required = data.get("require_transfer_manifest", False)
        if not isinstance(required, bool):
            raise ContractError("handoff_policy.require_transfer_manifest", "must be boolean")
        review = data.get("semantic_review", "risk-triggered")
        if review not in {"required", "risk-triggered"}:
            raise ContractError("handoff_policy.semantic_review", "has unsupported value")
        samples = data.get("minimum_semantic_samples", 1)
        if isinstance(samples, bool) or not isinstance(samples, int) or samples < 0:
            raise ContractError("handoff_policy.minimum_semantic_samples", "must be non-negative")
        return cls(required, str(review), samples)


@dataclass(frozen=True, slots=True)
class TaskPacket:
    schema_version: str
    task_id: str
    goal: str
    question_refs: tuple[str, ...]
    active_modes: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    required_skills: tuple[str, ...]
    forbidden_skills: tuple[str, ...]
    agent_profile: str
    input_refs: tuple[FileReference, ...]
    write_scope: tuple[str, ...]
    required_outputs: tuple[str | Mapping[str, Any], ...]
    permissions: PermissionPolicy
    delegation: DelegationPolicy
    budget: TaskBudget
    stop_conditions: tuple[str, ...]
    stale_if: tuple[str, ...]
    handoff_policy: HandoffPolicy = HandoffPolicy()
    revision: int = 1

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "TaskPacket":
        required_outputs = data.get("required_outputs")
        if not isinstance(required_outputs, list) or any(
            not isinstance(item, (str, Mapping)) for item in required_outputs
        ):
            raise ContractError("required_outputs", "must be an array of strings or objects")
        scopes = string_tuple(data, "write_scope", required=True)
        for index, scope in enumerate(scopes):
            require_relative_path(scope, f"write_scope[{index}]")
        revision = data.get("revision", 1)
        if not isinstance(revision, int) or revision < 1:
            raise ContractError("revision", "must be a positive integer")
        budget_data = mapping_value(data, "budget")
        return cls(
            schema_version=require_string(data, "schema_version"),
            task_id=require_string(data, "task_id"),
            goal=require_string(data, "goal"),
            question_refs=string_tuple(data, "question_refs"),
            active_modes=string_tuple(data, "active_modes"),
            required_capabilities=string_tuple(data, "required_capabilities", required=True),
            required_skills=string_tuple(data, "required_skills", required=True),
            forbidden_skills=string_tuple(data, "forbidden_skills"),
            agent_profile=require_string(data, "agent_profile"),
            input_refs=tuple(FileReference.from_mapping(item) for item in mapping_tuple(data, "input_refs")),
            write_scope=scopes,
            required_outputs=tuple(required_outputs),
            permissions=PermissionPolicy.from_mapping(mapping_value(data, "permissions", required=True)),
            delegation=DelegationPolicy.from_mapping(mapping_value(data, "delegation", required=True)),
            budget=TaskBudget.from_mapping(budget_data),
            stop_conditions=string_tuple(data, "stop_conditions", required=True),
            stale_if=string_tuple(data, "stale_if"),
            handoff_policy=HandoffPolicy.from_mapping(mapping_value(data, "handoff_policy")),
            revision=revision,
        )


@dataclass(frozen=True, slots=True)
class HandoffResult:
    summary: str
    facts: tuple[str, ...]
    inferences: tuple[str, ...]
    recommendations: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "HandoffResult":
        return cls(
            summary=require_string(data, "summary"),
            facts=string_tuple(data, "facts"),
            inferences=string_tuple(data, "inferences"),
            recommendations=string_tuple(data, "recommendations"),
        )


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    schema_version: str
    task_id: str
    task_revision: int
    attempt_id: str
    status: str
    started_at: str
    finished_at: str | None
    trigger_reason: str
    input_lock: tuple[FileReference, ...]
    skill_lock: tuple[str, ...]
    skill_assignment_ref: str | None
    runtime_snapshot_ref: str | None
    execution_receipt_ref: str | None
    artifact_refs: tuple[str, ...]
    handoff_ref: str | None
    failure: Mapping[str, Any] | None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "AttemptRecord":
        task_revision = data.get("task_revision")
        if not isinstance(task_revision, int) or task_revision < 1:
            raise ContractError("task_revision", "must be a positive integer")
        runtime_ref = optional_string(data, "runtime_snapshot_ref")
        receipt_ref = optional_string(data, "execution_receipt_ref")
        handoff_ref = optional_string(data, "handoff_ref")
        assignment_ref = optional_string(data, "skill_assignment_ref")
        for field, value in (
            ("skill_assignment_ref", assignment_ref),
            ("runtime_snapshot_ref", runtime_ref),
            ("execution_receipt_ref", receipt_ref),
            ("handoff_ref", handoff_ref),
        ):
            if value is not None:
                require_relative_path(value, field)
        artifact_refs = string_tuple(data, "artifact_refs", required=True)
        for index, ref in enumerate(artifact_refs):
            require_relative_path(ref, f"artifact_refs[{index}]")
        failure = data.get("failure")
        if failure is not None and not isinstance(failure, Mapping):
            raise ContractError("failure", "must be an object")
        return cls(
            schema_version=require_string(data, "schema_version"),
            task_id=require_string(data, "task_id"),
            task_revision=task_revision,
            attempt_id=require_string(data, "attempt_id"),
            status=require_string(data, "status"),
            started_at=require_string(data, "started_at"),
            finished_at=optional_string(data, "finished_at"),
            trigger_reason=require_string(data, "trigger_reason"),
            input_lock=tuple(FileReference.from_mapping(item) for item in mapping_tuple(data, "input_lock")),
            skill_lock=string_tuple(data, "skill_lock", required=True),
            skill_assignment_ref=assignment_ref,
            runtime_snapshot_ref=runtime_ref,
            execution_receipt_ref=receipt_ref,
            artifact_refs=artifact_refs,
            handoff_ref=handoff_ref,
            failure=dict(failure) if failure else None,
        )


@dataclass(frozen=True, slots=True)
class HandoffPacket:
    schema_version: str
    task_id: str
    attempt_id: str
    status: str
    input_lock: tuple[FileReference, ...]
    skill_lock: tuple[str, ...]
    skill_assignment_ref: str | None
    result: HandoffResult
    artifact_refs: tuple[str, ...]
    validation_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    conflicts: tuple[Mapping[str, Any], ...]
    unresolved: tuple[str, ...]
    human_decision_required: tuple[str, ...]
    recommended_next_actions: tuple[str, ...]
    runtime_metadata_ref: str | None = None
    execution_receipt_ref: str | None = None
    transfer_manifest_ref: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "HandoffPacket":
        status = require_string(data, "status")
        if status not in {"completed", "incomplete", "failed", "blocked", "cancelled"}:
            raise ContractError("status", "is not a supported handoff status")
        assignment_ref = optional_string(data, "skill_assignment_ref")
        if assignment_ref is not None:
            require_relative_path(assignment_ref, "skill_assignment_ref")
        receipt_ref = optional_string(data, "execution_receipt_ref")
        if receipt_ref is not None:
            require_relative_path(receipt_ref, "execution_receipt_ref")
        runtime_metadata_ref = optional_string(data, "runtime_metadata_ref")
        if runtime_metadata_ref is not None:
            require_relative_path(runtime_metadata_ref, "runtime_metadata_ref")
        transfer_manifest_ref = optional_string(data, "transfer_manifest_ref")
        if transfer_manifest_ref is not None:
            require_relative_path(transfer_manifest_ref, "transfer_manifest_ref")
        return cls(
            schema_version=require_string(data, "schema_version"),
            task_id=require_string(data, "task_id"),
            attempt_id=require_string(data, "attempt_id"),
            status=status,
            input_lock=tuple(FileReference.from_mapping(item) for item in mapping_tuple(data, "input_lock")),
            skill_lock=string_tuple(data, "skill_lock", required=True),
            skill_assignment_ref=assignment_ref,
            result=HandoffResult.from_mapping(mapping_value(data, "result", required=True)),
            artifact_refs=string_tuple(data, "artifact_refs", required=True),
            validation_refs=string_tuple(data, "validation_refs"),
            limitations=string_tuple(data, "limitations", required=True),
            conflicts=mapping_tuple(data, "conflicts"),
            unresolved=string_tuple(data, "unresolved", required=True),
            human_decision_required=string_tuple(data, "human_decision_required"),
            recommended_next_actions=string_tuple(data, "recommended_next_actions"),
            runtime_metadata_ref=runtime_metadata_ref,
            execution_receipt_ref=receipt_ref,
            transfer_manifest_ref=transfer_manifest_ref,
        )
