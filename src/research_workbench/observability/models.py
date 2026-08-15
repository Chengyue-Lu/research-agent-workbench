"""Small, provider-neutral execution records.

Receipts intentionally retain aggregate control-plane facts, not full prompts,
chain-of-thought, provider SDK objects, or raw tool transcripts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.context import ContextSnapshot, assess_handoff_transfer
from research_workbench.contracts import ContractError, ContractRisk, RiskLevel
from research_workbench.contracts.common import (
    mapping_tuple,
    mapping_value,
    optional_string,
    require_relative_path,
    require_string,
    string_tuple,
)
from research_workbench.io import load_document
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import AttemptRecord, FileReference, HandoffPacket
from research_workbench.validation.documents import infer_document_kind
from research_workbench.validation.relationships import check_references
from research_workbench.validation.schemas import SchemaCatalog


def _optional_non_negative_int(data: Mapping[str, Any], field: str) -> int | None:
    value = data.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError(field, "must be a non-negative integer")
    return value


def _optional_non_negative_number(data: Mapping[str, Any], field: str) -> float | None:
    value = data.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ContractError(field, "must be a non-negative number")
    return float(value)


@dataclass(frozen=True, slots=True)
class ExecutionRuntime:
    name: str
    version: str
    adapter_version: str
    native_execution_id: str | None = None
    capability_snapshot_ref: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ExecutionRuntime":
        capability_ref = optional_string(data, "capability_snapshot_ref")
        if capability_ref is not None:
            require_relative_path(capability_ref, "runtime.capability_snapshot_ref")
        return cls(
            require_string(data, "name"),
            require_string(data, "version"),
            require_string(data, "adapter_version"),
            optional_string(data, "native_execution_id"),
            capability_ref,
        )


@dataclass(frozen=True, slots=True)
class ModelUsageRecord:
    provider: str
    model: str
    requests: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    provider_reported_cost: float | None = None
    currency: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ModelUsageRecord":
        requests = _optional_non_negative_int(data, "requests")
        if requests is None:
            raise ContractError("model_usage.requests", "is required")
        cost = _optional_non_negative_number(data, "provider_reported_cost")
        currency = optional_string(data, "currency")
        if (cost is None) != (currency is None):
            raise ContractError(
                "model_usage.provider_reported_cost",
                "cost and currency must be present together",
            )
        return cls(
            require_string(data, "provider"),
            require_string(data, "model"),
            requests,
            _optional_non_negative_int(data, "input_tokens"),
            _optional_non_negative_int(data, "output_tokens"),
            _optional_non_negative_int(data, "cached_input_tokens"),
            _optional_non_negative_int(data, "reasoning_tokens"),
            cost,
            currency,
        )


@dataclass(frozen=True, slots=True)
class RequestedModelBinding:
    """The explicit adapter lookup key and model requested for one API Attempt."""

    provider_adapter_id: str
    requested_model: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RequestedModelBinding":
        return cls(
            provider_adapter_id=require_string(data, "provider_adapter_id"),
            requested_model=require_string(data, "requested_model"),
        )


@dataclass(frozen=True, slots=True)
class CoordinationUsage:
    delegated_attempts: int
    handoff_count: int
    review_rounds: int
    max_parallel_observed: int
    coordination_tokens: int | None = None
    execution_tokens: int | None = None
    coordination_seconds: float | None = None
    execution_seconds: float | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CoordinationUsage":
        required: dict[str, int] = {}
        for field in ("delegated_attempts", "handoff_count", "review_rounds", "max_parallel_observed"):
            value = _optional_non_negative_int(data, field)
            if value is None:
                raise ContractError(f"coordination.{field}", "is required")
            required[field] = value
        return cls(
            **required,
            coordination_tokens=_optional_non_negative_int(data, "coordination_tokens"),
            execution_tokens=_optional_non_negative_int(data, "execution_tokens"),
            coordination_seconds=_optional_non_negative_number(data, "coordination_seconds"),
            execution_seconds=_optional_non_negative_number(data, "execution_seconds"),
        )

    @property
    def cost_ratio(self) -> tuple[float | None, str | None]:
        if self.coordination_tokens is not None and self.execution_tokens is not None:
            total = self.coordination_tokens + self.execution_tokens
            return ((self.coordination_tokens / total) if total else 0.0, "tokens")
        if self.coordination_seconds is not None and self.execution_seconds is not None:
            total = self.coordination_seconds + self.execution_seconds
            return ((self.coordination_seconds / total) if total else 0.0, "seconds")
        return None, None


@dataclass(frozen=True, slots=True)
class TracePolicyRecord:
    mode: str
    external: bool
    sensitive_data_detected: bool
    redactions_applied: int
    retained_until: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "TracePolicyRecord":
        mode = require_string(data, "mode")
        if mode not in {"disabled", "minimal", "redacted", "full"}:
            raise ContractError("trace.mode", "has unsupported value")
        external = data.get("external")
        sensitive = data.get("sensitive_data_detected")
        if not isinstance(external, bool) or not isinstance(sensitive, bool):
            raise ContractError("trace", "external and sensitive_data_detected must be boolean")
        redactions = _optional_non_negative_int(data, "redactions_applied")
        if redactions is None:
            raise ContractError("trace.redactions_applied", "is required")
        return cls(mode, external, sensitive, redactions, optional_string(data, "retained_until"))


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    schema_version: str
    receipt_id: str
    execution_kind: str
    attempt_ref: str
    task_id: str
    task_revision: int
    agent_profile_ref: str
    skill_assignment_ref: str
    context_snapshot_ref: str | None
    started_at: str
    finished_at: str
    status: str
    completion_claim: str | None
    model_binding: RequestedModelBinding | None
    runtime: ExecutionRuntime
    model_usage_status: str
    model_usage: tuple[ModelUsageRecord, ...]
    coordination: CoordinationUsage
    trace: TracePolicyRecord
    output_refs: tuple[str, ...]
    validation_refs: tuple[str, ...]
    limitations: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ExecutionReceipt":
        kind = require_string(data, "execution_kind")
        if kind not in {"contract-only", "native-agent", "model-api", "local-tool"}:
            raise ContractError("execution_kind", "has unsupported value")
        revision = data.get("task_revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ContractError("task_revision", "must be a positive integer")
        status = require_string(data, "status")
        if status not in {
            "completed",
            "stage-completed",
            "safe-paused",
            "waiting",
            "incomplete",
            "failed",
            "blocked",
            "cancelled",
        }:
            raise ContractError("status", "has unsupported value")
        completion_claim = optional_string(data, "completion_claim")
        if completion_claim not in {None, "execution-only", "contract-satisfied"}:
            raise ContractError("completion_claim", "has unsupported value")
        if completion_claim == "contract-satisfied" and status not in {
            "completed",
            "stage-completed",
        }:
            raise ContractError(
                "completion_claim",
                "contract-satisfied requires completed or stage-completed status",
            )
        raw_model_binding = data.get("model_binding")
        if raw_model_binding is None:
            if kind == "model-api":
                raise ContractError("model_binding", "is required for model-api execution")
            model_binding = None
        elif not isinstance(raw_model_binding, Mapping):
            raise ContractError("model_binding", "must be an object")
        else:
            model_binding = RequestedModelBinding.from_mapping(raw_model_binding)
        usage_status = require_string(data, "model_usage_status")
        if usage_status not in {"measured", "estimated", "unavailable", "not-applicable"}:
            raise ContractError("model_usage_status", "has unsupported value")
        usage = tuple(ModelUsageRecord.from_mapping(item) for item in mapping_tuple(data, "model_usage"))
        if usage_status == "not-applicable" and usage:
            raise ContractError("model_usage", "must be empty when status is not-applicable")
        if usage_status in {"measured", "estimated"} and not usage:
            raise ContractError("model_usage", f"must not be empty when status is {usage_status}")
        if usage_status == "measured" and any(
            item.input_tokens is None or item.output_tokens is None for item in usage
        ):
            raise ContractError("model_usage", "measured usage requires input_tokens and output_tokens")
        refs: dict[str, str | None] = {
            "attempt_ref": require_string(data, "attempt_ref"),
            "agent_profile_ref": require_string(data, "agent_profile_ref"),
            "skill_assignment_ref": require_string(data, "skill_assignment_ref"),
            "context_snapshot_ref": optional_string(data, "context_snapshot_ref"),
        }
        for field, value in refs.items():
            if value is not None:
                require_relative_path(value, field)
        output_refs = string_tuple(data, "output_refs", required=True)
        validation_refs = string_tuple(data, "validation_refs", required=True)
        for field, values in (("output_refs", output_refs), ("validation_refs", validation_refs)):
            for index, value in enumerate(values):
                require_relative_path(value, f"{field}[{index}]")
        if len(output_refs) != len(set(output_refs)) or len(validation_refs) != len(set(validation_refs)):
            raise ContractError("references", "output and validation references must be unique")
        started_at = require_string(data, "started_at")
        finished_at = require_string(data, "finished_at")
        if datetime.fromisoformat(finished_at.replace("Z", "+00:00")) < datetime.fromisoformat(
            started_at.replace("Z", "+00:00")
        ):
            raise ContractError("finished_at", "must not precede started_at")
        return cls(
            schema_version=require_string(data, "schema_version"),
            receipt_id=require_string(data, "receipt_id"),
            execution_kind=kind,
            attempt_ref=str(refs["attempt_ref"]),
            task_id=require_string(data, "task_id"),
            task_revision=revision,
            agent_profile_ref=str(refs["agent_profile_ref"]),
            skill_assignment_ref=str(refs["skill_assignment_ref"]),
            context_snapshot_ref=refs["context_snapshot_ref"],
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            completion_claim=completion_claim,
            model_binding=model_binding,
            runtime=ExecutionRuntime.from_mapping(mapping_value(data, "runtime", required=True)),
            model_usage_status=usage_status,
            model_usage=usage,
            coordination=CoordinationUsage.from_mapping(mapping_value(data, "coordination", required=True)),
            trace=TracePolicyRecord.from_mapping(mapping_value(data, "trace", required=True)),
            output_refs=output_refs,
            validation_refs=validation_refs,
            limitations=string_tuple(data, "limitations", required=True),
        )


def _load_reference(root: Path, relative: str) -> tuple[Path | None, Mapping[str, Any] | None]:
    path = resolve_within_root(root, relative)
    if path is None or not path.is_file():
        return path, None
    document = load_document(path)
    if not isinstance(document, Mapping):
        raise ContractError(relative, "referenced document must be an object")
    return path, document


def check_execution_receipt(
    receipt: ExecutionReceipt,
    protocol: ProjectProtocol,
    *,
    root: str | Path,
    receipt_ref: str | None = None,
) -> list[ContractRisk]:
    project_root = Path(root).resolve()
    risks: list[ContractRisk] = []

    def missing(field: str, relative: str) -> None:
        risks.append(
            ContractRisk("REF-MISSING", RiskLevel.BLOCK, f"{field} does not resolve within project: {relative}")
        )

    _, attempt_document = _load_reference(project_root, receipt.attempt_ref)
    if attempt_document is None:
        missing("attempt_ref", receipt.attempt_ref)
    else:
        attempt = AttemptRecord.from_mapping(attempt_document)
        if (attempt.task_id, attempt.task_revision) != (receipt.task_id, receipt.task_revision):
            risks.append(
                ContractRisk(
                    "RECEIPT-TASK-MISMATCH",
                    RiskLevel.BLOCK,
                    "execution receipt task identity does not match Attempt",
                )
            )
        if receipt_ref and attempt.execution_receipt_ref != receipt_ref:
            risks.append(
                ContractRisk(
                    "RECEIPT-ATTEMPT-BACKREF",
                    RiskLevel.BLOCK,
                    "Attempt does not point back to this Execution Receipt",
                )
            )
        if attempt.skill_assignment_ref != receipt.skill_assignment_ref:
            risks.append(
                ContractRisk(
                    "RECEIPT-ATTEMPT-ASSIGNMENT-MISMATCH",
                    RiskLevel.BLOCK,
                    "Attempt and Execution Receipt point to different Skill Assignments",
                )
            )
        expected_outputs = set(attempt.artifact_refs)
        if attempt.handoff_ref:
            expected_outputs.add(attempt.handoff_ref)
        missing_outputs = sorted(expected_outputs - set(receipt.output_refs))
        if missing_outputs:
            risks.append(
                ContractRisk(
                    "RECEIPT-ATTEMPT-OUTPUT-LOSS",
                    RiskLevel.BLOCK,
                    "Execution Receipt omits Attempt outputs: " + ", ".join(missing_outputs),
                )
            )
        if (
            attempt.runtime_snapshot_ref
            and receipt.runtime.capability_snapshot_ref != attempt.runtime_snapshot_ref
        ):
            risks.append(
                ContractRisk(
                    "RECEIPT-RUNTIME-SNAPSHOT-MISMATCH",
                    RiskLevel.BLOCK,
                    "Attempt and Execution Receipt point to different Runtime snapshots",
                )
            )
        if attempt.started_at != receipt.started_at or attempt.finished_at != receipt.finished_at:
            risks.append(
                ContractRisk(
                    "RECEIPT-TIME-MISMATCH",
                    RiskLevel.BLOCK,
                    "execution receipt timestamps do not match Attempt",
                )
            )
        if attempt.status != receipt.status:
            risks.append(
                ContractRisk(
                    "RECEIPT-STATUS-MISMATCH",
                    RiskLevel.BLOCK,
                    "execution receipt status does not match Attempt",
                )
            )

    _, assignment_document = _load_reference(project_root, receipt.skill_assignment_ref)
    if assignment_document is None:
        missing("skill_assignment_ref", receipt.skill_assignment_ref)
    else:
        assignment = ResolvedTask.from_mapping(assignment_document)
        if (assignment.task_id, assignment.task_revision) != (receipt.task_id, receipt.task_revision):
            risks.append(
                ContractRisk(
                    "RECEIPT-ASSIGNMENT-MISMATCH",
                    RiskLevel.BLOCK,
                    "execution receipt task identity does not match Skill Assignment",
                )
            )

    _, profile_document = _load_reference(project_root, receipt.agent_profile_ref)
    if profile_document is None:
        missing("agent_profile_ref", receipt.agent_profile_ref)
    else:
        profile = AgentProfile.from_mapping(profile_document)
        if assignment_document is not None:
            assignment = ResolvedTask.from_mapping(assignment_document)
            profile_identifier = f"{profile.agent_profile_id}@{profile.version}"
            if profile_identifier != assignment.agent_profile:
                risks.append(
                    ContractRisk(
                        "RECEIPT-PROFILE-MISMATCH",
                        RiskLevel.BLOCK,
                        "Agent Profile does not match Skill Assignment",
                    )
                )

    if receipt.context_snapshot_ref:
        _, snapshot_document = _load_reference(project_root, receipt.context_snapshot_ref)
        if snapshot_document is None:
            missing("context_snapshot_ref", receipt.context_snapshot_ref)
        else:
            snapshot = ContextSnapshot.from_mapping(snapshot_document)
            if snapshot.scope == "task" and snapshot.owner_ref not in {None, receipt.task_id, receipt.attempt_ref}:
                risks.append(
                    ContractRisk(
                        "RECEIPT-CONTEXT-OWNER-MISMATCH",
                        RiskLevel.BLOCK,
                        "task Context Snapshot belongs to a different owner",
                    )
                )
            if snapshot.assessment.level == "block":
                risks.append(
                    ContractRisk(
                        "RECEIPT-CONTEXT-BLOCKED",
                        RiskLevel.BLOCK,
                        "Context Snapshot contains an unresolved blocking condition",
                    )
                )
            if snapshot.handoff_audit_ref:
                _, audit_document = _load_reference(project_root, snapshot.handoff_audit_ref)
                if audit_document is None:
                    missing("handoff_audit_ref", snapshot.handoff_audit_ref)
                else:
                    assessment = assess_handoff_transfer(audit_document, root=project_root)
                    risks.extend(assessment.risks)

    for field, references in (("output_refs", receipt.output_refs), ("validation_refs", receipt.validation_refs)):
        for relative in references:
            path = resolve_within_root(project_root, relative)
            if path is None or not path.is_file():
                missing(field, relative)

    interpreted_validations = 0
    for relative in receipt.validation_refs:
        path = resolve_within_root(project_root, relative)
        if path is None or not path.is_file() or path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            continue
        validation_document = load_document(path)
        if not isinstance(validation_document, Mapping):
            continue
        kind = infer_document_kind(validation_document)
        if kind == "deterministic_check_report":
            interpreted_validations += 1
            schema_errors = SchemaCatalog().validate(kind, validation_document)
            if schema_errors:
                risks.append(
                    ContractRisk(
                        "RECEIPT-VALIDATION-INVALID",
                        RiskLevel.BLOCK,
                        f"validation report {relative} is schema-invalid",
                    )
                )
                continue
            subject_refs = [
                FileReference.from_mapping(item)
                for item in validation_document.get("subject_refs", [])
                if isinstance(item, Mapping)
            ]
            pinned_refs = list(subject_refs)
            checker = validation_document.get("checker")
            if isinstance(checker, Mapping) and isinstance(checker.get("source_ref"), Mapping):
                pinned_refs.append(FileReference.from_mapping(checker["source_ref"]))
            risks.extend(check_references(project_root, pinned_refs))
            subject_paths = {reference.path for reference in subject_refs}
            expected_subjects = set(receipt.output_refs) | {receipt.attempt_ref}
            if not subject_paths.intersection(expected_subjects):
                risks.append(
                    ContractRisk(
                        "RECEIPT-VALIDATION-SCOPE-MISMATCH",
                        RiskLevel.BLOCK,
                        f"validation report {relative} does not pin an Attempt or output from this receipt",
                    )
                )
            if (
                receipt.completion_claim == "contract-satisfied"
                and validation_document.get("status") != "pass"
            ):
                risks.append(
                    ContractRisk(
                        "RECEIPT-VALIDATION-FAILED",
                        RiskLevel.BLOCK,
                        f"machine validation failed: {relative}",
                    )
                )
        elif kind == "handoff_transfer_audit":
            interpreted_validations += 1
            assessment = assess_handoff_transfer(validation_document, root=project_root)
            risks.extend(assessment.risks)
        elif kind == "provider_conformance_report":
            interpreted_validations += 1
            if SchemaCatalog().validate(kind, validation_document):
                risks.append(
                    ContractRisk(
                        "RECEIPT-VALIDATION-INVALID",
                        RiskLevel.BLOCK,
                        f"provider conformance report {relative} is schema-invalid",
                    )
                )
            elif (
                receipt.completion_claim == "contract-satisfied"
                and validation_document.get("status") != "passed"
            ):
                risks.append(
                    ContractRisk(
                        "RECEIPT-VALIDATION-FAILED",
                        RiskLevel.BLOCK,
                        f"provider conformance failed: {relative}",
                    )
                )

    if receipt.completion_claim == "contract-satisfied" and interpreted_validations == 0:
        risks.append(
            ContractRisk(
                "RECEIPT-MACHINE-VALIDATION-MISSING",
                RiskLevel.BLOCK,
                "completion requires at least one understood machine validation artifact",
            )
        )

    for relative in receipt.output_refs:
        path = resolve_within_root(project_root, relative)
        if path is None or not path.is_file():
            continue
        document = load_document(path) if path.suffix.lower() in {".json", ".yaml", ".yml"} else None
        if isinstance(document, Mapping) and "result" in document and "attempt_id" in document:
            handoff = HandoffPacket.from_mapping(document)
            if handoff.task_id != receipt.task_id:
                risks.append(
                    ContractRisk(
                        "RECEIPT-HANDOFF-TASK-MISMATCH",
                        RiskLevel.BLOCK,
                        f"Handoff output {relative} belongs to a different Task",
                    )
                )
            if receipt_ref and handoff.execution_receipt_ref != receipt_ref:
                risks.append(
                    ContractRisk(
                        "RECEIPT-HANDOFF-BACKREF",
                        RiskLevel.BLOCK,
                        f"Handoff output {relative} does not point back to this Execution Receipt",
                    )
                )

    if receipt.status in {"completed", "stage-completed"} and not receipt.output_refs:
        risks.append(
            ContractRisk("RECEIPT-MISSING-OUTPUT", RiskLevel.BLOCK, "completed execution has no output references")
        )
    if receipt.status == "safe-paused":
        if receipt.context_snapshot_ref is None:
            risks.append(
                ContractRisk(
                    "RECEIPT-SAFE-PAUSE-CONTEXT-MISSING",
                    RiskLevel.BLOCK,
                    "safe-paused execution must pin the Context Snapshot that triggered closeout",
                )
            )
        if attempt_document is not None:
            attempt = AttemptRecord.from_mapping(attempt_document)
            if attempt.handoff_ref is None:
                risks.append(
                    ContractRisk(
                        "RECEIPT-SAFE-PAUSE-HANDOFF-MISSING",
                        RiskLevel.BLOCK,
                        "safe-paused execution must persist a recoverable Handoff",
                    )
                )
    if receipt.execution_kind in {"native-agent", "model-api"} and receipt.model_usage_status == "unavailable":
        risks.append(
            ContractRisk(
                "COST-USAGE-UNKNOWN",
                RiskLevel.WARNING,
                "model usage is unavailable; do not claim token or cost savings",
            )
        )
    ratio, basis = receipt.coordination.cost_ratio
    if ratio is None and receipt.execution_kind == "native-agent":
        risks.append(
            ContractRisk(
                "COORDINATION-COST-UNKNOWN",
                RiskLevel.WARNING,
                "native agent execution lacks token- or time-based coordination measurements",
            )
        )
    elif ratio is not None and ratio > protocol.budgets.coordination_cost_ratio_warn:
        risks.append(
            ContractRisk(
                "COORDINATION-COST-HIGH",
                RiskLevel.WARNING,
                f"coordination ratio {ratio:.3f} by {basis} exceeds {protocol.budgets.coordination_cost_ratio_warn:.3f}",
            )
        )
    if receipt.coordination.max_parallel_observed > protocol.budgets.max_parallel_subagents:
        risks.append(
            ContractRisk(
                "DELEGATION-FANOUT",
                RiskLevel.BLOCK,
                "observed parallel delegation exceeds Project Protocol budget",
            )
        )
    if receipt.coordination.review_rounds > 1:
        risks.append(
            ContractRisk(
                "REVIEW-LOOP",
                RiskLevel.WARNING,
                "more than one review round requires an explicit benefit justification",
            )
        )
    if receipt.trace.sensitive_data_detected:
        risks.append(
            ContractRisk(
                "TRACE-SENSITIVE",
                RiskLevel.BLOCK,
                "trace reports sensitive data; redact or delete it before retention",
            )
        )
    if receipt.trace.external and protocol.data_boundary.get("local_only"):
        risks.append(
            ContractRisk(
                "TRACE-DATA-BOUNDARY",
                RiskLevel.BLOCK,
                "external trace conflicts with the local-only Project Protocol",
            )
        )
    if receipt.trace.mode == "full":
        risks.append(
            ContractRisk(
                "TRACE-OVERRETENTION",
                RiskLevel.WARNING,
                "full trace retention should be reduced unless a current diagnostic consumer exists",
            )
        )
    return risks
