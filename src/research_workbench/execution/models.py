"""Contracts for the K-API-2 Task-to-API file loop.

The execution package compiles one frozen Task Packet + Skill Assignment into
a bounded isolated API session and closes it into recoverable file artifacts.
It never selects Skills, never routes models automatically, and never stores
credentials. See docs/implementation/K_API_2_FILE_LOOP.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping

from research_workbench.adapters.models.port import ModelRequest
from research_workbench.adapters.models.session import ApiSessionLimits, ApiSessionResult
from research_workbench.contracts.common import ContractRisk
from research_workbench.tasks.models import FileReference, HandoffPolicy

ATTEMPT_DIRNAME_OUTPUTS = "outputs"
PLAN_FILENAME = "execution-plan.yaml"
TRANSCRIPT_FILENAME = "session-transcript.json"
ATTEMPT_FILENAME = "attempt.yaml"
RECEIPT_FILENAME = "execution-receipt.yaml"
HANDOFF_FILENAME = "handoff.yaml"
CHECK_REPORT_FILENAME = "check-report.yaml"

CLOSEOUT_STATUSES = frozenset({"completed", "safe-paused", "incomplete", "failed"})


@dataclass(frozen=True, slots=True)
class ModelBinding:
    """Explicit model identity resolved from one pool slot; never auto-routed."""

    slot_id: str
    provider_adapter: str
    provider: str
    model: str
    reasoning_effort: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Immutable compile output: one frozen Task ready for one bounded session."""

    attempt_id: str
    task_id: str
    task_revision: int
    root: str
    attempt_dir: str
    model_binding: ModelBinding
    request: ModelRequest
    limits: ApiSessionLimits
    input_lock: tuple[FileReference, ...]
    readable_inputs: tuple[str, ...]
    write_scope: tuple[str, ...]
    required_outputs: tuple[str, ...]
    skill_lock: tuple[str, ...]
    assignment_ref: str
    profile_ref: str
    handoff_policy: HandoffPolicy
    started_at: str

    @property
    def provider(self) -> str:
        return self.model_binding.provider

    def to_mapping(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True, slots=True)
class ToolEvent:
    """One observable client-tool call inside the bounded session."""

    name: str
    ok: bool
    path: str | None = None
    sha256: str | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ExecutionRunResult:
    session: ApiSessionResult
    tool_events: tuple[ToolEvent, ...]
    stale_inputs: tuple[str, ...]
    # Recorded (request, response) pairs from a recording provider proxy; the
    # closeout persists them as the session transcript. Never contains secrets.
    transcript: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class CloseoutResult:
    status: str
    attempt_path: str
    receipt_path: str
    handoff_path: str
    check_report_path: str
    risks: tuple[ContractRisk, ...]


class ExecutionPlanError(ValueError):
    """Compile-time blocking failure carrying deterministic risks."""

    def __init__(self, risks: tuple[ContractRisk, ...]):
        self.risks = risks
        super().__init__("; ".join(f"{risk.code}: {risk.message}" for risk in risks))


def _plain(value: Any) -> Any:
    """JSON/YAML-safe rendering; unlike to_plain it also flattens frozensets and enums."""

    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (frozenset, set)):
        return sorted(_plain(item) for item in value)
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value
