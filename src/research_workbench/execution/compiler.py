"""Pure compiler from frozen research contracts to one fresh API session.

By construction the compiler sees only the Task Packet, the Agent Profile,
the frozen Skill Assignment, and the explicit model-slot binding. It reads
task input files and selected skill bodies, verifies each hash, refuses
oversized content instead of truncating it, and never receives main-agent
history or unselected skill content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from research_workbench.adapters.models import (
    ApiSessionLimits,
    Capability,
    ClientTool,
    ContentBlock,
    Message,
    ModelBinding,
    ModelRequest,
    ResponseFormat,
)
from research_workbench.adapters.models.port import ToolDefinition
from research_workbench.artifacts.integrity import (
    ReferenceStatus,
    check_file_reference,
    hash_file,
    resolve_within_root,
)
from research_workbench.capability.models import AgentProfile
from research_workbench.capability.resolver import ResolvedTask
from research_workbench.contracts.common import to_plain
from research_workbench.execution.errors import CompileError
from research_workbench.execution.options import ExecutionPolicy
from research_workbench.execution.tools import SessionToolLog, build_client_tools
from research_workbench.tasks import TaskPacket


EVIDENCE_OUTPUT_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "properties": {
        "statement": {"type": "string"},
        "source_locator": {"type": "string"},
        "quality_flags": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
        "facts": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "inferences": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "unresolved": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "statement",
        "source_locator",
        "quality_flags",
        "summary",
        "facts",
        "inferences",
        "recommendations",
        "limitations",
        "unresolved",
    ],
    "additionalProperties": False,
}

OUTPUT_CONTRACT_SCHEMAS: Mapping[str, Mapping[str, Any]] = {
    "evidence-record": EVIDENCE_OUTPUT_SCHEMA,
}


@dataclass(frozen=True, slots=True)
class CompileReport:
    input_chars: int
    skill_instruction_chars: int
    limit_sources: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class CompiledSession:
    request: ModelRequest
    limits: ApiSessionLimits
    tools: tuple[ClientTool, ...]
    tool_log: SessionToolLog
    attempt_id: str
    provider_name: str
    output_contract: str
    report: CompileReport


def compile_session(
    task: TaskPacket,
    profile: AgentProfile,
    assignment: ResolvedTask,
    binding: ModelBinding,
    *,
    root: Path,
    policy: ExecutionPolicy = ExecutionPolicy(),
) -> CompiledSession:
    """Compile one resolved Task into a fresh, bounded API session."""

    output_contract = _select_output_contract(task)
    _check_binding_capabilities(binding, require_tools=bool(assignment.resolved_tools))

    tool_log = SessionToolLog()
    tools = _resolve_tools(task, profile, assignment, root=root, policy=policy, log=tool_log)
    input_texts = _read_verified_inputs(task, root=root, policy=policy)
    skill_texts = _read_verified_skills(assignment, root=root, policy=policy)
    limits, limit_sources = _build_limits(task, policy)

    attempt_id = _attempt_identifier(assignment, binding, task)
    request = ModelRequest(
        model=binding.model,
        messages=(
            _system_message(task, assignment, skill_texts, output_contract),
            _user_message(task, input_texts),
        ),
        tools=tuple(tool.definition for tool in tools),
        response_format=ResponseFormat(
            kind="json_schema",
            name="evidence-extraction-result",
            schema=OUTPUT_CONTRACT_SCHEMAS[output_contract],
        ),
        capability_requirements=frozenset({Capability.STRUCTURED_OUTPUT}),
        metadata={
            "task_id": task.task_id,
            "assignment_id": assignment.assignment_id,
            "attempt_id": attempt_id,
            "slot_id": binding.slot_id,
        },
    )
    report = CompileReport(
        input_chars=sum(len(text) for text in input_texts.values()),
        skill_instruction_chars=sum(len(text) for text in skill_texts.values()),
        limit_sources=limit_sources,
    )
    return CompiledSession(
        request=request,
        limits=limits,
        tools=tools,
        tool_log=tool_log,
        attempt_id=attempt_id,
        provider_name=binding.provider_adapter,
        output_contract=output_contract,
        report=report,
    )


def _select_output_contract(task: TaskPacket) -> str:
    supported = tuple(
        item
        for item in task.required_outputs
        if isinstance(item, str) and item in OUTPUT_CONTRACT_SCHEMAS
    )
    if len(supported) != 1:
        raise CompileError(
            "COMPILE-OUTPUT-CONTRACT-UNSUPPORTED",
            "the task must require exactly one model-structured output contract from: "
            + ", ".join(sorted(OUTPUT_CONTRACT_SCHEMAS))
            + f" (found {list(supported)})",
        )
    contract = supported[0]
    if contract == "evidence-record" and not task.input_refs:
        raise CompileError(
            "COMPILE-INPUT-MISSING",
            "the evidence-record output contract requires at least one hash-pinned input",
        )
    return contract


def _check_binding_capabilities(binding: ModelBinding, *, require_tools: bool) -> None:
    required = {Capability.TEXT, Capability.STRUCTURED_OUTPUT}
    if require_tools:
        required.add(Capability.TOOLS)
    gaps = sorted(str(capability) for capability in required - set(binding.capabilities))
    if gaps:
        raise CompileError(
            "COMPILE-CAPABILITY-GAP",
            f"model slot {binding.slot_id!r} lacks required capabilities: " + ", ".join(gaps),
        )


def _resolve_tools(
    task: TaskPacket,
    profile: AgentProfile,
    assignment: ResolvedTask,
    *,
    root: Path,
    policy: ExecutionPolicy,
    log: SessionToolLog,
) -> tuple[ClientTool, ...]:
    allowed_by_profile = set(profile.allowed_tool_capabilities)
    not_allowed = sorted(set(assignment.resolved_tools) - allowed_by_profile)
    if not_allowed:
        raise CompileError(
            "COMPILE-TOOL-NOT-ALLOWED",
            "resolved tools are outside the profile tool allowlist: " + ", ".join(not_allowed),
        )
    return build_client_tools(
        tuple(sorted(set(assignment.resolved_tools))),
        root=root,
        readable_paths=tuple(reference.path for reference in task.input_refs),
        allowed_roots=assignment.effective_permissions.allowed_roots,
        max_read_chars=policy.max_document_read_chars,
        log=log,
    )


def _read_verified_inputs(
    task: TaskPacket, *, root: Path, policy: ExecutionPolicy
) -> dict[str, str]:
    texts: dict[str, str] = {}
    for reference in task.input_refs:
        check = check_file_reference(root, reference)
        if check.status == ReferenceStatus.HASH_MISMATCH:
            raise CompileError(
                "TASK-STALE-INPUT",
                f"input {reference.path!r} no longer matches its pinned sha256",
            )
        if check.status == ReferenceStatus.MISSING:
            raise CompileError(
                "COMPILE-INPUT-MISSING", f"input file is missing: {reference.path}"
            )
        if check.status == ReferenceStatus.OUTSIDE_ROOT:
            raise CompileError(
                "COMPILE-INPUT-OUTSIDE", f"input escapes the project root: {reference.path}"
            )
        assert check.resolved_path is not None
        size = check.resolved_path.stat().st_size
        if size > policy.max_input_chars:
            raise CompileError(
                "COMPILE-INPUT-TOO-LARGE",
                f"input {reference.path!r} exceeds the compile input cap "
                f"({size} > {policy.max_input_chars} chars)",
            )
        texts[reference.path] = check.resolved_path.read_text(encoding="utf-8")
    return texts


def _read_verified_skills(
    assignment: ResolvedTask, *, root: Path, policy: ExecutionPolicy
) -> dict[str, str]:
    texts: dict[str, str] = {}
    for lock in assignment.skill_lock:
        if not lock.source_locator:
            raise CompileError(
                "COMPILE-SKILL-LOCATOR-MISSING",
                f"skill {lock.skill_id!r} has no source locator to load",
            )
        resolved = resolve_within_root(root, lock.source_locator)
        if resolved is None or not resolved.is_file():
            raise CompileError(
                "COMPILE-SKILL-MISSING",
                f"skill body not found at {lock.source_locator!r}",
            )
        if hash_file(resolved) != lock.content_hash.removeprefix("sha256:").lower():
            raise CompileError(
                "COMPILE-SKILL-DRIFT",
                f"skill body {lock.source_locator!r} no longer matches its pinned hash",
            )
        text = resolved.read_text(encoding="utf-8")
        if len(text) > policy.max_skill_instruction_chars:
            raise CompileError(
                "COMPILE-SKILL-TOO-LARGE",
                f"skill {lock.skill_id!r} instructions exceed the compile cap "
                f"({len(text)} > {policy.max_skill_instruction_chars} chars)",
            )
        texts[lock.identifier] = text
    return texts


def _build_limits(task: TaskPacket, policy: ExecutionPolicy) -> tuple[ApiSessionLimits, dict[str, str]]:
    budget = task.budget
    max_model_turns = budget.max_turns or policy.default_max_model_turns
    max_output_tokens = budget.max_output_tokens or policy.default_max_output_tokens_per_turn
    max_seconds = float(budget.max_seconds or policy.default_max_seconds)
    limit_sources = {
        "max_model_turns": "task-budget" if budget.max_turns else "policy-default",
        "max_output_tokens_per_turn": (
            "task-budget" if budget.max_output_tokens else "policy-default"
        ),
        "max_seconds": "task-budget" if budget.max_seconds else "policy-default",
        "max_tool_calls": "policy-default",
        "max_parallel_tool_calls": "policy-default",
        "max_tool_result_chars": "policy-default",
    }
    limits = ApiSessionLimits(
        max_model_turns=max_model_turns,
        max_tool_calls=policy.max_tool_calls,
        max_parallel_tool_calls=policy.max_parallel_tool_calls,
        max_tool_result_chars=policy.max_tool_result_chars,
        max_output_tokens_per_turn=max_output_tokens,
        max_seconds=max_seconds,
        max_total_tokens=policy.max_total_tokens,
        max_provider_reported_cost=policy.max_provider_reported_cost,
        allowed_tool_side_effects=policy.allowed_tool_side_effects,
    )
    return limits, limit_sources


def _attempt_identifier(
    assignment: ResolvedTask, binding: ModelBinding, task: TaskPacket
) -> str:
    task_payload = json.dumps(
        to_plain(task), sort_keys=True, separators=(",", ":"), default=str
    )
    payload = {
        "assignment_id": assignment.assignment_id,
        "task_revision": task.revision,
        "task_payload_sha256": hashlib.sha256(task_payload.encode("utf-8")).hexdigest(),
        "slot_id": binding.slot_id,
        "provider_adapter": binding.provider_adapter,
        "model": binding.model,
        "input_lock": [
            {"path": reference.path, "sha256": reference.sha256}
            for reference in task.input_refs
        ],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return "A-" + digest[:12].upper()


def _system_message(
    task: TaskPacket,
    assignment: ResolvedTask,
    skill_texts: dict[str, str],
    output_contract: str,
) -> Message:
    sections: list[str] = [
        f"# Task Packet — {task.task_id} (revision {task.revision})",
        f"Goal: {task.goal}",
    ]
    if task.question_refs:
        sections.append("Questions: " + ", ".join(task.question_refs))
    sections.extend(
        [
            "",
            f"# Frozen Skill Assignment — {assignment.assignment_id}",
            "Selected skills: " + (", ".join(lock.identifier for lock in assignment.skill_lock) or "none"),
        ]
    )
    for identifier, text in skill_texts.items():
        sections.extend(["", f"# Skill instructions — {identifier}", text])
    sections.extend(
        [
            "",
            "# Output contract",
            f"Return exactly one structured {output_contract} result. The response format is "
            "a JSON schema; every required field must be present.",
            "",
            "# Stop conditions",
            *(f"- {condition}" for condition in task.stop_conditions),
            "",
            "# Safe pause conditions",
            *(f"- {condition}" for condition in task.safe_pause_conditions),
        ]
    )
    return Message("system", (ContentBlock(kind="text", text="\n".join(sections)),))


def _user_message(task: TaskPacket, input_texts: dict[str, str]) -> Message:
    sections: list[str] = ["# Task inputs (hash-verified)"]
    for reference in task.input_refs:
        sections.extend(
            [
                "",
                f"## Input — {reference.path} (sha256 {reference.sha256})",
                input_texts[reference.path],
            ]
        )
    return Message("user", (ContentBlock(kind="text", text="\n".join(sections)),))
