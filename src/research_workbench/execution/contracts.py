"""Exact-match execution contracts for the portable API baseline.

An execution contract is selected by the Task's exact output/handoff/tool
signature.  The registry never ranks contracts, probes them in preference
order, or falls back after a selected contract rejects an input.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from research_workbench.adapters.models import (
    ApiSessionLimits,
    ClientTool,
    ModelResponse,
)
from research_workbench.adapters.models.base import decode_strict_json_value
from research_workbench.artifacts.integrity import hash_file
from research_workbench.capability import ResolvedTask
from research_workbench.execution.output import (
    API_TASK_OUTPUT_SCHEMA,
    ApiTaskOutputError,
    parse_api_task_output,
)
from research_workbench.execution.tools import (
    build_bounded_compute_tool,
    build_document_read_tool,
    build_frozen_text_read_tool,
)
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import TaskPacket
from research_workbench.validation import SchemaCatalog


@cache
def _schema_catalog() -> SchemaCatalog:
    return SchemaCatalog()


class ExecutionContractError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class ExecutionArtifact:
    """One trusted output location paired with model-controlled document data."""

    relative_name: str
    document_kind: str
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ExecutionValidation:
    relative_name: str
    document_kind: str
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ContractAdmission:
    success_status: str
    artifacts: tuple[ExecutionArtifact, ...]
    handoff: Mapping[str, Any]
    transfer_items: tuple[Mapping[str, Any], ...] = ()


def _string_array() -> dict[str, Any]:
    return {
        "type": "array",
        "items": {"type": "string", "minLength": 1},
        "uniqueItems": True,
    }


HANDOFF_BODY_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "required": [
        "result",
        "limitations",
        "conflicts",
        "unresolved",
        "human_decision_required",
        "recommended_next_actions",
    ],
    "properties": {
        "result": {
            "type": "object",
            "required": ["summary", "facts", "inferences", "recommendations"],
            "properties": {
                "summary": {"type": "string", "minLength": 1},
                "facts": _string_array(),
                "inferences": _string_array(),
                "recommendations": _string_array(),
            },
            "additionalProperties": False,
        },
        "limitations": _string_array(),
        "conflicts": {"type": "array", "items": {"type": "object", "minProperties": 1}},
        "unresolved": _string_array(),
        "human_decision_required": _string_array(),
        "recommended_next_actions": _string_array(),
    },
    "additionalProperties": False,
}


_FILE_REF_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "required": ["path", "sha256"],
    "properties": {
        "path": {"type": "string", "minLength": 1},
        "sha256": {"type": "string", "pattern": "^(?:sha256:)?[0-9a-fA-F]{64}$"},
        "revision": {"type": "integer", "minimum": 1},
    },
    "additionalProperties": False,
}


_SIMULATION_CHECK_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "required": ["status", "evidence_refs"],
    "properties": {
        "status": {"enum": ["pass", "fail", "not-run", "blocked"]},
        "evidence_refs": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "uniqueItems": True,
        },
    },
    "allOf": [
        {
            "if": {"properties": {"status": {"const": "pass"}}, "required": ["status"]},
            "then": {"properties": {"evidence_refs": {"minItems": 1}}},
        }
    ],
    "additionalProperties": False,
}


SIMULATION_VV_RESPONSE_REPORT_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "required": [
        "run_ref",
        "model_version",
        "input_lock",
        "parameter_boundary",
        "checks",
        "assumptions",
        "limitations",
        "claim_ceiling",
    ],
    "properties": {
        "run_ref": {"type": "string", "minLength": 1},
        "model_version": {"type": "string", "minLength": 1},
        "input_lock": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": _FILE_REF_SCHEMA,
        },
        "parameter_boundary": {"type": "string", "minLength": 1},
        "checks": {
            "type": "object",
            "required": ["convergence", "sensitivity", "benchmark_comparison"],
            "properties": {
                "convergence": _SIMULATION_CHECK_SCHEMA,
                "sensitivity": _SIMULATION_CHECK_SCHEMA,
                "benchmark_comparison": _SIMULATION_CHECK_SCHEMA,
            },
            "additionalProperties": False,
        },
        "assumptions": _string_array(),
        "limitations": _string_array(),
        "claim_ceiling": {"enum": ["exploratory", "simulation_supported", "unresolved"]},
    },
    "additionalProperties": False,
}


SIMULATION_API_OUTPUT_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "required": ["report", "handoff"],
    "properties": {
        "report": SIMULATION_VV_RESPONSE_REPORT_SCHEMA,
        "handoff": HANDOFF_BODY_SCHEMA,
    },
    "additionalProperties": False,
}


class ExecutionContract(ABC):
    contract_id: str
    version: str
    required_outputs: frozenset[str]
    require_transfer_manifest: bool
    tool_names: frozenset[str]
    response_format_name: str
    response_schema: Mapping[str, Any]
    success_status: str
    allowed_tool_side_effects: frozenset[str]
    supporting_refs: tuple[str, ...] = ()

    @property
    def identifier(self) -> str:
        return f"{self.contract_id}@{self.version}"

    def matches(self, task: TaskPacket, assignment: ResolvedTask) -> bool:
        return (
            _task_output_contracts(task) == self.required_outputs
            and task.handoff_policy.require_transfer_manifest
            == self.require_transfer_manifest
            and frozenset(assignment.resolved_tools) == self.tool_names
        )

    def validate_task_assignment(self, task: TaskPacket, assignment: ResolvedTask) -> None:
        if _task_output_contracts(task) != self.required_outputs:
            raise ExecutionContractError(
                "EXECUTION-CONTRACT-OUTPUT",
                "Task outputs differ from the exact ExecutionContract signature",
            )
        if frozenset(assignment.output_contracts) != self.required_outputs:
            raise ExecutionContractError(
                "ASSIGNMENT-OUTPUT-DRIFT",
                "Skill Assignment outputs differ from the exact ExecutionContract signature",
            )
        if frozenset(assignment.resolved_tools) != self.tool_names:
            raise ExecutionContractError(
                "EXECUTION-CONTRACT-TOOLS",
                "Skill Assignment tools differ from the exact ExecutionContract signature",
            )
        if task.handoff_policy.require_transfer_manifest != self.require_transfer_manifest:
            raise ExecutionContractError(
                "EXECUTION-CONTRACT-HANDOFF",
                "Task handoff tier differs from the selected ExecutionContract",
            )

    @abstractmethod
    def build_tools(
        self,
        root: str | Path,
        task: TaskPacket,
        limits: ApiSessionLimits,
    ) -> tuple[ClientTool, ...]:
        raise NotImplementedError

    @abstractmethod
    def admit_response(
        self,
        response: ModelResponse | None,
        *,
        task: TaskPacket,
        protocol: ProjectProtocol,
    ) -> ContractAdmission:
        raise NotImplementedError

    def build_validations(
        self,
        *,
        stage_root: Path,
        attempt_root: str,
        attempt_id: str,
        artifacts: tuple[ExecutionArtifact, ...],
    ) -> tuple[ExecutionValidation, ...]:
        return ()


class EvidenceH2ExecutionContract(ExecutionContract):
    contract_id = "evidence-h2"
    version = "0.1.0"
    required_outputs = frozenset(
        {"evidence-record", "handoff-transfer-manifest", "handoff-packet"}
    )
    require_transfer_manifest = True
    tool_names = frozenset({"document-read"})
    response_format_name = "api_task_output"
    response_schema = API_TASK_OUTPUT_SCHEMA
    success_status = "completed"
    allowed_tool_side_effects = frozenset({"read-only"})

    def validate_task_assignment(self, task: TaskPacket, assignment: ResolvedTask) -> None:
        super().validate_task_assignment(task, assignment)
        if task.handoff_policy.semantic_review == "required":
            raise ExecutionContractError(
                "OUTPUT-CONTRACT-UNSUPPORTED",
                "evidence/H2 cannot satisfy mandatory semantic review inside the API Attempt",
            )

    def build_tools(
        self,
        root: str | Path,
        task: TaskPacket,
        limits: ApiSessionLimits,
    ) -> tuple[ClientTool, ...]:
        return (build_document_read_tool(root, task),)

    def admit_response(
        self,
        response: ModelResponse | None,
        *,
        task: TaskPacket,
        protocol: ProjectProtocol,
    ) -> ContractAdmission:
        value = parse_api_task_output(response, task=task, protocol=protocol)
        artifacts = tuple(
            ExecutionArtifact(
                relative_name=f"artifacts/{wrapper['document']['object_id']}.yaml",
                document_kind="research_object",
                document=dict(wrapper["document"]),
            )
            for wrapper in value["artifacts"]
        )
        return ContractAdmission(
            success_status=self.success_status,
            artifacts=artifacts,
            handoff=dict(value["handoff"]),
            transfer_items=tuple(dict(item) for item in value["transfer_items"]),
        )


class SimulationH1ExecutionContract(ExecutionContract):
    contract_id = "simulation-h1"
    version = "0.1.0"
    required_outputs = frozenset({"simulation-vv-report", "handoff-packet"})
    require_transfer_manifest = False
    tool_names = frozenset({"file-read", "bounded-compute"})
    response_format_name = "simulation_vv_api_output"
    response_schema = SIMULATION_API_OUTPUT_SCHEMA
    success_status = "stage-completed"
    allowed_tool_side_effects = frozenset({"none", "read-only"})
    supporting_refs = (
        ".agents/skills/simulation-vv/scripts/check_vv_report.py",
    )

    def build_tools(
        self,
        root: str | Path,
        task: TaskPacket,
        limits: ApiSessionLimits,
    ) -> tuple[ClientTool, ...]:
        return (
            build_frozen_text_read_tool(
                "file-read",
                root,
                task,
                max_bytes=limits.max_tool_result_chars,
            ),
            build_bounded_compute_tool(
                max_values_per_call=limits.max_compute_values_per_call
            ),
        )

    def admit_response(
        self,
        response: ModelResponse | None,
        *,
        task: TaskPacket,
        protocol: ProjectProtocol,
    ) -> ContractAdmission:
        value = _decode_response(response)
        errors = sorted(
            Draft202012Validator(self.response_schema).iter_errors(value),
            key=lambda item: list(item.absolute_path),
        )
        if errors:
            first = errors[0]
            pointer = "$" + "".join(
                f"[{part}]" if isinstance(part, int) else f".{part}"
                for part in first.absolute_path
            )
            raise ApiTaskOutputError(
                "API-OUTPUT-CONTRACT", f"{pointer}: {first.message}"
            )
        if not isinstance(value, Mapping):
            raise ApiTaskOutputError("API-OUTPUT-CONTRACT", "top-level output must be an object")
        report = value.get("report")
        handoff = value.get("handoff")
        if not isinstance(report, Mapping) or not isinstance(handoff, Mapping):
            raise ApiTaskOutputError(
                "API-OUTPUT-CONTRACT", "simulation output lacks report or Handoff"
            )
        schema_errors = _schema_catalog().validate("simulation_vv_report", report)
        if schema_errors:
            first = schema_errors[0]
            raise ApiTaskOutputError(
                "API-OUTPUT-SIMULATION-CONTRACT", f"{first.pointer}: {first.message}"
            )
        expected_inputs = {
            (reference.path, reference.sha256) for reference in task.input_refs
        }
        actual_inputs = {
            (str(item.get("path", "")), str(item.get("sha256", "")).removeprefix("sha256:").lower())
            for item in report["input_lock"]
            if isinstance(item, Mapping)
        }
        if actual_inputs != expected_inputs:
            raise ApiTaskOutputError(
                "API-OUTPUT-SIMULATION-INPUT-LOCK",
                "simulation report input_lock must exactly equal the frozen Task inputs",
            )
        admitted_paths = {reference.path for reference in task.input_refs}
        has_nonpass = False
        for name in ("convergence", "sensitivity", "benchmark_comparison"):
            check = report["checks"][name]
            status = check["status"]
            refs = set(check["evidence_refs"])
            if not refs.issubset(admitted_paths):
                raise ApiTaskOutputError(
                    "API-OUTPUT-SIMULATION-EVIDENCE-BOUNDARY",
                    f"checks.{name} cites evidence outside frozen Task inputs",
                )
            if status != "pass":
                has_nonpass = True
        if report["claim_ceiling"] == "simulation_supported" and (
            "simulation_supported" not in protocol.claim_ceiling
        ):
            raise ApiTaskOutputError(
                "API-OUTPUT-CLAIM-CEILING",
                "simulation report exceeds the Project Protocol claim ceiling",
            )
        if has_nonpass and not (
            report["limitations"] or handoff["limitations"] or handoff["unresolved"]
        ):
            raise ApiTaskOutputError(
                "API-OUTPUT-SIMULATION-GAP-UNSTATED",
                "non-pass simulation checks require a persisted limitation or unresolved item",
            )
        admitted_handoff = dict(handoff)
        human_gate = (
            "Human review must decide whether the structurally admitted simulation V&V "
            "stage is scientifically acceptable before any claim promotion."
        )
        admitted_handoff["human_decision_required"] = list(
            dict.fromkeys(
                [
                    *admitted_handoff.get("human_decision_required", []),
                    human_gate,
                ]
            )
        )
        return ContractAdmission(
            success_status=self.success_status,
            artifacts=(
                ExecutionArtifact(
                    relative_name="simulation-vv-report.yaml",
                    document_kind="simulation_vv_report",
                    document=dict(report),
                ),
            ),
            handoff=admitted_handoff,
        )

    def build_validations(
        self,
        *,
        stage_root: Path,
        attempt_root: str,
        attempt_id: str,
        artifacts: tuple[ExecutionArtifact, ...],
    ) -> tuple[ExecutionValidation, ...]:
        if len(artifacts) != 1:
            raise ExecutionContractError(
                "EXECUTION-CONTRACT-ARTIFACT",
                "simulation/H1 requires exactly one report artifact",
            )
        report_ref = f"{attempt_root}/{artifacts[0].relative_name}"
        checker_ref = self.supporting_refs[0]
        report_path = stage_root / Path(report_ref)
        checker_path = stage_root / Path(checker_ref)
        document = {
            "schema_version": "0.1.0",
            "report_id": f"DCR-{attempt_id}-SIMULATION-VV",
            "checker": {
                "checker_id": "simulation-vv-structural-contract",
                "version": "0.1.0",
                "source_ref": {"path": checker_ref, "sha256": hash_file(checker_path)},
            },
            "subject_refs": [
                {"path": report_ref, "sha256": hash_file(report_path)}
            ],
            "status": "pass",
            "checks": [
                {
                    "code": "SIMULATION-VV-STRUCTURE",
                    "status": "pass",
                    "detail": "required V&V fields and check statuses are structurally valid",
                },
                {
                    "code": "SIMULATION-VV-INPUT-LOCK",
                    "status": "pass",
                    "detail": "report input lock and evidence references stay within frozen Task inputs",
                },
                {
                    "code": "SIMULATION-VV-CLAIM-CEILING",
                    "status": "pass",
                    "detail": "report claim ceiling does not exceed the active simulation boundary",
                },
            ],
            "scope": "structural, frozen-reference, and claim-boundary checks only",
            "limitations": [
                "A pass does not recompute numerical results or establish scientific correctness."
            ],
        }
        return (
            ExecutionValidation(
                relative_name="simulation-vv-check.yaml",
                document_kind="deterministic_check_report",
                document=document,
            ),
        )


class ExecutionContractRegistry:
    def __init__(self, contracts: tuple[ExecutionContract, ...]) -> None:
        self._contracts = contracts
        identifiers = [contract.identifier for contract in contracts]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("ExecutionContract identifiers must be unique")

    def require(self, task: TaskPacket, assignment: ResolvedTask) -> ExecutionContract:
        matches = [contract for contract in self._contracts if contract.matches(task, assignment)]
        if not matches:
            raise ExecutionContractError(
                "OUTPUT-CONTRACT-UNSUPPORTED",
                "no ExecutionContract exactly matches Task outputs, handoff tier, and tools",
            )
        if len(matches) != 1:
            raise ExecutionContractError(
                "EXECUTION-CONTRACT-AMBIGUOUS",
                "more than one ExecutionContract has the same exact signature",
            )
        selected = matches[0]
        selected.validate_task_assignment(task, assignment)
        return selected


def default_execution_contract_registry() -> ExecutionContractRegistry:
    return ExecutionContractRegistry(
        (EvidenceH2ExecutionContract(), SimulationH1ExecutionContract())
    )


def _task_output_contracts(task: TaskPacket) -> frozenset[str]:
    return frozenset(
        item if isinstance(item, str) else str(item.get("contract", ""))
        for item in task.required_outputs
    )


def _decode_response(response: ModelResponse | None) -> Any:
    if response is None:
        raise ApiTaskOutputError("API-OUTPUT-MISSING", "session has no final response")
    text = "".join(block.text or "" for block in response.output if block.kind == "text")
    if not text.strip():
        raise ApiTaskOutputError("API-OUTPUT-MISSING", "final response has no text output")
    try:
        return decode_strict_json_value(text)
    except ValueError as exc:
        position = getattr(exc, "pos", None)
        detail = f" at offset {position}" if isinstance(position, int) else ""
        raise ApiTaskOutputError("API-OUTPUT-JSON", f"invalid JSON{detail}") from exc
