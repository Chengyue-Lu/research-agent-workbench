"""Compile one frozen Task Packet + Skill Assignment into an ExecutionPlan.

The compiler is a pure function: it runs every compile-time blocking check
from docs/implementation/K_API_2_FILE_LOOP.md §3 and either returns an
immutable ExecutionPlan or raises ExecutionPlanError carrying BLOCK risks.
Malformed input documents keep the ContractError (CLI exit-2) channel; a
well-formed document that fails a compile-time check raises
ExecutionPlanError. The compiler never starts a session, never mutates the
workspace, and never reads credentials: only the model identifier string is
pulled from the injected environment mapping.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from research_workbench.adapters.models.configuration import load_provider_adapter_configs
from research_workbench.adapters.models.pool import load_model_pool, validate_pool_adapters
from research_workbench.adapters.models.port import (
    ContentBlock,
    Message,
    ModelRequest,
    ResponseFormat,
    ToolDefinition,
)
from research_workbench.adapters.models.session import ApiSessionLimits
from research_workbench.artifacts.integrity import (
    check_file_reference,
    hash_file,
    resolve_within_root,
)
from research_workbench.capability.catalog import AcceptedSkillRegistry, SkillRegistrySelectionError
from research_workbench.capability.models import AgentProfile, SkillManifest
from research_workbench.capability.resolver import ResolvedTask
from research_workbench.contracts.common import ContractError, require_relative_path
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.execution.models import ExecutionPlan, ExecutionPlanError, ModelBinding
from research_workbench.io import load_document
from research_workbench.tasks.models import FileReference, TaskPacket
from research_workbench.validation.schemas import SchemaCatalog

# Budget fields the Task Packet does not pin fall back to these defaults;
# the tool-call ceilings are fixed by the K-API-2 contract.
DEFAULT_MAX_MODEL_TURNS = 8
DEFAULT_MAX_OUTPUT_TOKENS_PER_TURN = 4096
DEFAULT_MAX_SECONDS = 900.0
DEFAULT_MAX_TOOL_CALLS = 12
DEFAULT_MAX_PARALLEL_TOOL_CALLS = 8
DEFAULT_MAX_TOOL_RESULT_CHARS = 8000
MAX_SKILL_SOURCE_CHARS = 20000

CLOSEOUT_RESPONSE_FORMAT = ResponseFormat(
    kind="json_schema",
    name="execution_closeout",
    schema={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["completed", "safe-paused"]},
            "summary": {"type": "string"},
            "limitations": {"type": "array", "items": {"type": "string"}},
            "unresolved": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["status", "summary", "limitations", "unresolved"],
        "additionalProperties": False,
    },
)

# The runner attaches handlers under these exact names; the plan must declare
# them or IsolatedApiSessionRunner rejects the request.
EXECUTION_TOOL_DEFINITIONS = (
    ToolDefinition(
        name="read_file",
        description=(
            "Read one declared Task input or one file inside the attempt "
            "outputs directory; returns its path, sha256, and content."
        ),
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    ),
    ToolDefinition(
        name="write_artifact",
        description=(
            "Write one formal output artifact under a bare file name into the "
            "attempt outputs directory."
        ),
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}, "content": {"type": "string"}},
            "required": ["name", "content"],
            "additionalProperties": False,
        },
    ),
    ToolDefinition(
        name="list_outputs",
        description="List the file names and sha256 digests currently in the attempt outputs directory.",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
)


def compile_execution(
    task_path: str | Path,
    assignment_path: str | Path,
    *,
    slot: str,
    pool_path: str | Path,
    adapters_path: str | Path,
    root: str | Path,
    attempt_id: str | None = None,
    environment: Mapping[str, str] | None = None,
    started_at: str | None = None,
    model_override: str | None = None,
    base_state_path: str | Path | None = None,
) -> ExecutionPlan:
    """Compile frozen inputs into one bounded plan or raise ExecutionPlanError."""

    root_path = Path(root).resolve()
    environment_map: Mapping[str, str] = os.environ if environment is None else environment
    task = TaskPacket.from_mapping(_load_mapping(task_path))
    assignment = ResolvedTask.from_mapping(_load_mapping(assignment_path))
    risks: list[ContractRisk] = []

    if assignment.task_id != task.task_id or assignment.task_revision != task.revision:
        risks.append(
            _block(
                "EXEC-TASK-ASSIGNMENT-MISMATCH",
                f"assignment binds {assignment.task_id}@{assignment.task_revision}, "
                f"task is {task.task_id}@{task.revision}",
            )
        )

    profile = _check_profile(task, assignment, root_path, risks)

    for reference in task.input_refs:
        check = check_file_reference(root_path, reference)
        if not check.valid:
            detail = f"input {reference.path}: {check.status}"
            if check.actual_sha256:
                detail += f" (actual sha256:{check.actual_sha256})"
            risks.append(_block("EXEC-INPUT-STALE", detail))

    manifests = _check_skill_lock(assignment, root_path, risks)

    # A supplied Main State is a validated execution input: it is resolved,
    # schema-checked, and hashed here at compile time, strictly before any
    # provider call, so a missing or malformed state can never spend tokens
    # or leave a claimed-but-unseeded attempt behind.
    base_state: FileReference | None = None
    if base_state_path is not None:
        resolved_state = resolve_within_root(root_path, str(base_state_path))
        if resolved_state is None or not resolved_state.is_file():
            risks.append(
                _block(
                    "EXEC-BASE-STATE-INVALID",
                    f"base state {base_state_path} is missing or outside the project root",
                )
            )
        else:
            state_errors = SchemaCatalog().validate("main_state", _load_mapping(resolved_state))
            if state_errors:
                first = state_errors[0]
                risks.append(
                    _block(
                        "EXEC-BASE-STATE-INVALID",
                        f"base state fails main_state schema at {first.pointer}: {first.message}",
                    )
                )
            else:
                base_state = FileReference(
                    path=resolved_state.resolve().relative_to(root_path).as_posix(),
                    sha256=hash_file(resolved_state),
                )

    slot_config = None
    pool = load_model_pool(pool_path)
    try:
        slot_config = pool.get(slot)
    except KeyError:
        risks.append(_block("EXEC-MODEL-UNBOUND", f"model slot is not present in the pool: {slot}"))
    else:
        if not slot_config.enabled:
            risks.append(_block("EXEC-MODEL-UNBOUND", f"model slot is disabled: {slot}"))
        elif model_override is not None:
            if not isinstance(model_override, str) or not model_override.strip():
                risks.append(
                    _block("EXEC-MODEL-UNBOUND", "model_override must be a non-empty string when supplied")
                )
        else:
            configured = environment_map.get(slot_config.model_env, "")
            bound = configured.strip() if isinstance(configured, str) else ""
            if not bound:
                risks.append(
                    _block(
                        "EXEC-MODEL-UNBOUND",
                        f"model slot {slot!r} requires a non-empty {slot_config.model_env} value",
                    )
                )

    adapters = load_provider_adapter_configs(adapters_path)
    try:
        validate_pool_adapters(pool, adapters)
    except ValueError as exc:
        risks.append(_block("EXEC-ADAPTER-MISMATCH", str(exc)))
    adapter_by_id = {adapter.adapter_id: adapter for adapter in adapters}

    if not task.write_scope:
        risks.append(_block("EXEC-WRITESCOPE-INVALID", "task write_scope is empty"))
    else:
        for scope in task.write_scope:
            try:
                require_relative_path(scope, "write_scope")
            except ContractError as exc:
                risks.append(_block("EXEC-WRITESCOPE-INVALID", str(exc)))

    if risks:
        raise ExecutionPlanError(tuple(risks))
    assert profile is not None and slot_config is not None

    if model_override is not None:
        bound_model = model_override.strip()
    else:
        bound_model = environment_map.get(slot_config.model_env, "").strip()
    adapter = adapter_by_id[slot_config.provider_adapter]
    binding = ModelBinding(
        slot_id=slot_config.slot_id,
        provider_adapter=slot_config.provider_adapter,
        provider=adapter.provider,
        model=bound_model,
        reasoning_effort=slot_config.reasoning_effort,
    )

    budget = task.budget
    side_effects = {"read-only", "local-write"}
    if assignment.effective_permissions.external_write:
        side_effects.add("external-write")
    limits = ApiSessionLimits(
        max_model_turns=budget.max_turns or DEFAULT_MAX_MODEL_TURNS,
        max_tool_calls=DEFAULT_MAX_TOOL_CALLS,
        max_parallel_tool_calls=DEFAULT_MAX_PARALLEL_TOOL_CALLS,
        max_tool_result_chars=DEFAULT_MAX_TOOL_RESULT_CHARS,
        max_output_tokens_per_turn=budget.max_output_tokens or DEFAULT_MAX_OUTPUT_TOKENS_PER_TURN,
        max_seconds=float(budget.max_seconds or DEFAULT_MAX_SECONDS),
        allowed_tool_side_effects=frozenset(side_effects),
    )

    required_outputs = tuple(
        item if isinstance(item, str) else str(item.get("contract", ""))
        for item in task.required_outputs
    )
    attempt = attempt_id or ("A-" + uuid.uuid4().hex.upper()[:12])
    started = started_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    profile_ref = f"registry/agents/{task.agent_profile}.yaml"
    request = ModelRequest(
        model=binding.model,
        messages=(
            _system_message(task, profile, assignment, manifests, root_path),
            _user_message(task, assignment, required_outputs),
        ),
        tools=EXECUTION_TOOL_DEFINITIONS,
        response_format=CLOSEOUT_RESPONSE_FORMAT,
        reasoning_effort=binding.reasoning_effort,
    )
    return ExecutionPlan(
        attempt_id=attempt,
        task_id=task.task_id,
        task_revision=task.revision,
        root=str(root_path),
        attempt_dir=f"work/{task.task_id}/{attempt}",
        model_binding=binding,
        request=request,
        limits=limits,
        input_lock=task.input_refs,
        readable_inputs=(
            tuple(reference.path for reference in task.input_refs)
            + ((base_state.path,) if base_state is not None else ())
        ),
        write_scope=task.write_scope,
        required_outputs=required_outputs,
        skill_lock=tuple(lock.identifier for lock in assignment.skill_lock),
        assignment_ref=_relative_ref(root_path, assignment_path),
        profile_ref=profile_ref,
        handoff_policy=task.handoff_policy,
        started_at=started,
        base_state=base_state,
    )


def _block(code: str, message: str) -> ContractRisk:
    return ContractRisk(code, RiskLevel.BLOCK, message)


def _load_mapping(path: str | Path) -> Mapping[str, Any]:
    document = load_document(path)
    if not isinstance(document, Mapping):
        raise ContractError("document", f"must be an object: {path}")
    return document


def _check_profile(
    task: TaskPacket,
    assignment: ResolvedTask,
    root_path: Path,
    risks: list[ContractRisk],
) -> AgentProfile | None:
    profile_ref = f"registry/agents/{task.agent_profile}.yaml"
    versioned_prefix = f"{task.agent_profile}@"
    if assignment.agent_profile != task.agent_profile and not assignment.agent_profile.startswith(
        versioned_prefix
    ):
        risks.append(
            _block(
                "EXEC-PROFILE-MISMATCH",
                f"assignment binds Agent Profile {assignment.agent_profile!r}, "
                f"task requests {task.agent_profile!r}",
            )
        )
        return None
    profile_path = resolve_within_root(root_path, profile_ref)
    profile: AgentProfile | None = None
    try:
        if profile_path is None:
            raise ContractError("agent_profile", "profile path escapes the project root")
        profile = AgentProfile.from_mapping(_load_mapping(profile_path))
    except Exception as exc:  # Any failure here means an unloadable profile.
        risks.append(
            _block("EXEC-PROFILE-MISMATCH", f"Agent Profile cannot be loaded: {profile_ref}: {exc}")
        )
        return None
    if profile.agent_profile_id != task.agent_profile:
        risks.append(
            _block(
                "EXEC-PROFILE-MISMATCH",
                f"profile file {profile_ref} defines {profile.agent_profile_id!r}, "
                f"task requests {task.agent_profile!r}",
            )
        )
        return None
    if "@" in assignment.agent_profile:
        live = f"{profile.agent_profile_id}@{profile.version}"
        if assignment.agent_profile != live:
            risks.append(
                _block(
                    "EXEC-PROFILE-MISMATCH",
                    f"assignment pins Agent Profile {assignment.agent_profile!r}, live profile is {live!r}",
                )
            )
            return None
    return profile


def _check_skill_lock(
    assignment: ResolvedTask,
    root_path: Path,
    risks: list[ContractRisk],
) -> dict[tuple[str, str], SkillManifest]:
    # Registry load verifies its own pins against the live files and raises
    # ContractError on drift; here only the frozen Assignment lock is compared
    # against those verified pins, using historical-replay semantics so legacy
    # Skills can still execute an already-frozen Assignment.
    registry = AcceptedSkillRegistry.load(project_root=root_path)
    identifiers = tuple(lock.identifier for lock in assignment.skill_lock)
    try:
        selected = registry.require(identifiers, purpose="historical-replay")
    except SkillRegistrySelectionError as exc:
        risks.append(_block("EXEC-SKILL-DRIFT", str(exc)))
        return {}
    manifests: dict[tuple[str, str], SkillManifest] = {}
    for lock, manifest in zip(assignment.skill_lock, selected):
        locked_hash = lock.content_hash.removeprefix("sha256:").lower()
        live_hash = manifest.source_content_hash.removeprefix("sha256:").lower()
        locked_package = (lock.package_hash or "").removeprefix("sha256:").lower()
        live_package = (manifest.source_package_hash or "").removeprefix("sha256:").lower()
        mismatches: list[str] = []
        if locked_hash != live_hash:
            mismatches.append(f"content_hash locked={locked_hash} live={live_hash}")
        if lock.source_locator != manifest.source_locator:
            mismatches.append(
                f"source_locator locked={lock.source_locator!r} live={manifest.source_locator!r}"
            )
        if locked_package != live_package:
            mismatches.append(f"package_hash locked={locked_package} live={live_package}")
        if mismatches:
            risks.append(
                _block("EXEC-SKILL-DRIFT", f"Skill lock drift for {lock.identifier}: " + "; ".join(mismatches))
            )
        else:
            manifests[(lock.skill_id, lock.version)] = manifest
    return manifests


def _relative_ref(root: Path, path: str | Path) -> str:
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _skill_source(manifest: SkillManifest, root_path: Path) -> str:
    locator = manifest.source_locator
    resolved = resolve_within_root(root_path, locator) if locator else None
    if resolved is None:
        return "(pinned Skill source is unavailable)"
    return resolved.read_text(encoding="utf-8")[:MAX_SKILL_SOURCE_CHARS]


def _system_message(
    task: TaskPacket,
    profile: AgentProfile,
    assignment: ResolvedTask,
    manifests: Mapping[tuple[str, str], SkillManifest],
    root_path: Path,
) -> Message:
    ceiling = profile.permission_ceiling
    lines = [
        "You are executing exactly one frozen research Task in a fresh, bounded, isolated API session.",
        f"Agent Profile: {profile.agent_profile_id}@{profile.version}",
        f"Profile purpose: {profile.purpose}",
        "Permission ceiling: "
        f"filesystem={ceiling.filesystem}, network={ceiling.network}, "
        f"external_write={'allowed' if ceiling.external_write else 'forbidden'}"
        + (f", allowed_roots={', '.join(ceiling.allowed_roots)}" if ceiling.allowed_roots else ""),
        "Allowed tool capabilities: " + ", ".join(profile.allowed_tool_capabilities),
        "Delegation is "
        + ("allowed within the Task limits." if profile.delegation_allowed else "forbidden; never spawn subagents."),
        "",
        "Locked Skill instructions (pinned by the Skill Assignment; apply them exactly):",
    ]
    for lock in assignment.skill_lock:
        manifest = manifests[(lock.skill_id, lock.version)]
        pinned = manifest.source_content_hash.removeprefix("sha256:").lower()
        lines.append(f"--- Skill {lock.identifier} sha256:{pinned} ---")
        lines.append(_skill_source(manifest, root_path))
    policy = task.handoff_policy
    lines.extend(
        [
            "",
            "Output contracts: " + ", ".join(assignment.output_contracts),
            "",
            "Handoff requirements:",
            "- Persist a Handoff Packet with summary, artifact references, limitations, and unresolved items.",
            f"- require_transfer_manifest={str(policy.require_transfer_manifest).lower()}",
            f"- semantic_review={policy.semantic_review}",
            f"- minimum_semantic_samples={policy.minimum_semantic_samples}",
            "",
            'End with exactly one JSON object: {"status": "completed"|"safe-paused", '
            '"summary": string, "limitations": [string], "unresolved": [string]}.',
        ]
    )
    return Message("system", (ContentBlock(kind="text", text="\n".join(lines) + "\n"),))


def _user_message(
    task: TaskPacket,
    assignment: ResolvedTask,
    required_outputs: tuple[str, ...],
) -> Message:
    lines = [
        f"Task {task.task_id}@{task.revision} (Skill Assignment {assignment.assignment_id}).",
        "Goal: " + task.goal,
    ]
    if task.active_modes:
        lines.append("Active modes: " + ", ".join(task.active_modes))
    lines.append(
        "Input references (pinned path + sha256 only; content is not inlined — read with the read_file tool):"
    )
    lines.extend(f"- {reference.path} sha256:{reference.sha256}" for reference in task.input_refs)
    lines.append("Write scope:")
    lines.extend(f"- {scope}" for scope in task.write_scope)
    lines.append(
        "Write every formal output with the write_artifact tool under a bare file name; "
        "inspect written files with list_outputs."
    )
    lines.append("Required outputs:")
    lines.extend(f"- {item}" for item in required_outputs)
    lines.append(
        "Each required output file must explicitly declare its contract identity "
        "(schema_version plus the contract's own identity fields, e.g. object_type for "
        "research objects) so it passes the repository schema for that contract; "
        "write one object per file."
    )
    lines.append("Completion checks:")
    lines.extend(f"- {condition}" for condition in task.completion_checks)
    lines.append("Safe-pause conditions:")
    lines.extend(f"- {condition}" for condition in task.safe_pause_conditions)
    lines.append("Stop conditions:")
    lines.extend(f"- {condition}" for condition in task.stop_conditions)
    lines.append(
        "Do not expand the Task, load other Skills, read undeclared files, or request "
        "main-context history; none is provided."
    )
    lines.append(
        'Final message contract: once you stop calling tools, your last message must be '
        'exactly one JSON object {"status": "completed"|"safe-paused", "summary": string, '
        '"limitations": [string], "unresolved": [string]} and nothing else — no prose, '
        "no Markdown code fence, no text before or after it."
    )
    return Message("user", (ContentBlock(kind="text", text="\n".join(lines) + "\n"),))
