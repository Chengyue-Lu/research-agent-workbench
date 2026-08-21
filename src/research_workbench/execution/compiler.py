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

import hashlib
import json
import os
import re
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
from research_workbench.artifacts.integrity import check_file_reference, hash_file, resolve_within_root
from research_workbench.capability.catalog import AcceptedSkillRegistry, SkillRegistrySelectionError
from research_workbench.capability.models import AgentProfile, SkillManifest
from research_workbench.capability.resolver import ResolvedTask
from research_workbench.capability.snapshot import ResolvedCapabilitySnapshot
from research_workbench.context.models import MainStatePacket
from research_workbench.contracts.common import ContractError, require_relative_path
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.execution.models import (
    ExecutionPlan,
    ExecutionPlanError,
    FrozenContractRef,
    ModelBinding,
    ResolvedExecutionView,
)
from research_workbench.io import load_document
from research_workbench.method.authority import (
    DecisionAuthorityMatrix,
    assess_method_resolution,
)
from research_workbench.method.models import MethodResolution
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
    method_resolution_path: str | Path | None = None,
    capability_snapshot_path: str | Path | None = None,
    from_state_path: str | Path | None = None,
    authority_path: str | Path = "registry/method/decision-authority.yaml",
    accountable_owner: str = "local-test-owner",
    actor_id: str | None = None,
) -> ExecutionPlan:
    """Compile frozen inputs into one bounded plan or raise ExecutionPlanError."""

    root_path = Path(root).resolve()
    environment_map: Mapping[str, str] = os.environ if environment is None else environment
    task = TaskPacket.from_mapping(_load_mapping(task_path))
    assignment = ResolvedTask.from_mapping(_load_mapping(assignment_path))
    risks: list[ContractRisk] = []
    method, snapshot = _load_governed_inputs(
        root_path,
        task_path=task_path,
        task=task,
        assignment=assignment,
        method_resolution_path=method_resolution_path,
        capability_snapshot_path=capability_snapshot_path,
        authority_path=authority_path,
        risks=risks,
    )

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

    resolved_view = _build_resolved_execution_view(
        root_path,
        task_path=task_path,
        assignment_path=assignment_path,
        task=task,
        assignment=assignment,
        method=method,
        method_resolution_path=method_resolution_path,
        snapshot=snapshot,
        capability_snapshot_path=capability_snapshot_path,
        from_state_path=from_state_path,
        slot=slot,
        binding=binding,
        limits=limits,
        risks=risks,
    )
    if risks:
        raise ExecutionPlanError(tuple(risks))

    required_outputs = tuple(
        item if isinstance(item, str) else str(item.get("contract", ""))
        for item in task.required_outputs
    )
    attempt = attempt_id or (
        "A-" + resolved_view.identity_sha256[:12].upper()
        if resolved_view is not None
        else "A-" + uuid.uuid4().hex.upper()[:12]
    )
    started = started_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    profile_ref = f"registry/agents/{task.agent_profile}.yaml"
    if not isinstance(accountable_owner, str) or not accountable_owner.strip():
        raise ExecutionPlanError((_block("EXEC-OWNER-MISSING", "accountable_owner must be non-empty"),))
    runtime_actor = actor_id or f"runtime-{task.agent_profile}-{attempt}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", runtime_actor):
        raise ExecutionPlanError((_block("EXEC-ACTOR-ID-INVALID", "actor_id contains unsupported characters"),))
    request = ModelRequest(
        model=binding.model,
        messages=(
            _system_message(task, profile, assignment, manifests, root_path, method),
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
        readable_inputs=tuple(reference.path for reference in task.input_refs),
        write_scope=task.write_scope,
        required_outputs=required_outputs,
        skill_lock=tuple(lock.identifier for lock in assignment.skill_lock),
        assignment_ref=_relative_ref(root_path, assignment_path),
        profile_ref=profile_ref,
        handoff_policy=task.handoff_policy,
        started_at=started,
        resolved_view=resolved_view,
        accountable_owner=accountable_owner.strip(),
        actor_id=runtime_actor,
        task_ref=_relative_ref(root_path, task_path),
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


def _load_governed_inputs(
    root: Path,
    *,
    task_path: str | Path,
    task: TaskPacket,
    assignment: ResolvedTask,
    method_resolution_path: str | Path | None,
    capability_snapshot_path: str | Path | None,
    authority_path: str | Path,
    risks: list[ContractRisk],
) -> tuple[MethodResolution | None, ResolvedCapabilitySnapshot | None]:
    """Load and cross-check the optional strict Method/Capability control plane."""

    if (method_resolution_path is None) != (capability_snapshot_path is None):
        risks.append(
            _block(
                "EXEC-RESOLUTION-PAIR-MISSING",
                "Method Resolution and Resolved Capability Snapshot must be supplied together",
            )
        )
        return None, None
    if method_resolution_path is None or capability_snapshot_path is None:
        return None, None

    method_document = _load_mapping(method_resolution_path)
    snapshot_document = _load_mapping(capability_snapshot_path)
    authority_target = Path(authority_path)
    if not authority_target.is_absolute():
        authority_target = root / authority_target
    authority_document = _load_mapping(authority_target)
    catalog = SchemaCatalog()
    for kind, document, label in (
        ("method_resolution", method_document, "Method Resolution"),
        ("resolved_capability_snapshot", snapshot_document, "Resolved Capability Snapshot"),
        ("decision_authority", authority_document, "Decision Authority Matrix"),
    ):
        for issue in catalog.validate(kind, document):
            risks.append(
                _block(
                    "EXEC-RESOLUTION-INVALID",
                    f"{label} schema error at {issue.pointer}: {issue.message}",
                )
            )
    try:
        method = MethodResolution.from_mapping(method_document)
        snapshot = ResolvedCapabilitySnapshot.from_mapping(snapshot_document)
        matrix = DecisionAuthorityMatrix.from_mapping(authority_document)
    except ContractError as exc:
        risks.append(_block("EXEC-RESOLUTION-INVALID", str(exc)))
        return None, None

    if method.status != "resolved":
        risks.append(
            _block(
                "EXEC-METHOD-NOT-RESOLVED",
                f"Method Resolution {method.resolution_id} has status {method.status}",
            )
        )
    authority = assess_method_resolution(method, matrix)
    for error in authority.errors:
        risks.append(_block("EXEC-METHOD-AUTHORITY", error))
    if snapshot.status != "resolved":
        risks.append(
            _block(
                "EXEC-CAPABILITY-NOT-RESOLVED",
                f"capability snapshot {snapshot.snapshot_id} has status {snapshot.status}",
            )
        )

    task_relative = _strict_relative(root, task_path)
    method_relative = _strict_relative(root, method_resolution_path)
    if task_relative is None or method_relative is None:
        risks.append(
            _block(
                "EXEC-RESOLUTION-OUTSIDE-ROOT",
                "strict Method/Capability execution inputs must stay inside the project root",
            )
        )
    else:
        if method.task_ref != task_relative:
            risks.append(
                _block(
                    "EXEC-METHOD-TASK-MISMATCH",
                    f"Method Resolution binds {method.task_ref!r}, Task is {task_relative!r}",
                )
            )
        _check_exact_reference(
            root, snapshot.task_ref, task_relative, "Task", "EXEC-CAPABILITY-REF-DRIFT", risks
        )
        _check_exact_reference(
            root,
            snapshot.method_resolution_ref,
            method_relative,
            "Method Resolution",
            "EXEC-CAPABILITY-REF-DRIFT",
            risks,
        )

    selected_actions = {item.action_id for item in method.action_selections if item.status == "selected"}
    for action in method.action_selections:
        if action.status != "selected" or action.source_path is None or action.sha256 is None:
            continue
        reference = FileReference(action.source_path, action.sha256.removeprefix("sha256:"))
        check = check_file_reference(root, reference)
        if not check.valid:
            risks.append(
                _block(
                    "EXEC-METHOD-ACTION-DRIFT",
                    f"Mode Action {action.action_id} reference is {check.status}",
                )
            )
    if not selected_actions:
        risks.append(_block("EXEC-METHOD-NOT-RESOLVED", "no selected Mode Action is executable"))

    requirements: dict[str, str] = {}
    for item in method.capability_requirements:
        try:
            requirement_id = str(item["requirement_id"])
            capability_id = str(item["capability_id"])
        except KeyError:
            risks.append(
                _block(
                    "EXEC-RESOLUTION-INVALID",
                    "every Method capability requirement needs requirement_id and capability_id",
                )
            )
            continue
        requirements[requirement_id] = capability_id
    method_bindings = {
        binding.requirement_id: binding
        for binding in snapshot.bindings
        if binding.origin == "method"
    }
    if set(method_bindings) != set(requirements):
        missing = sorted(set(requirements) - set(method_bindings))
        extra = sorted(set(method_bindings) - set(requirements))
        risks.append(
            _block(
                "EXEC-CAPABILITY-COVERAGE",
                f"Method requirement bindings differ (missing={missing}, extra={extra})",
            )
        )
    for requirement_id, capability_id in requirements.items():
        binding = method_bindings.get(requirement_id)
        if binding is not None and binding.capability_id != capability_id:
            risks.append(
                _block(
                    "EXEC-CAPABILITY-COVERAGE",
                    f"{requirement_id} expects {capability_id}, snapshot binds {binding.capability_id}",
                )
            )
    task_capabilities = set(task.required_capabilities)
    method_capabilities = set(requirements.values())
    if not task_capabilities.issubset(method_capabilities):
        risks.append(
            _block(
                "EXEC-CAPABILITY-COVERAGE",
                "Method Resolution omits Task capabilities: "
                + ", ".join(sorted(task_capabilities - method_capabilities)),
            )
        )

    locked_skills = {lock.identifier for lock in assignment.skill_lock}
    bound_skills = {
        binding.implementation_id
        for binding in snapshot.bindings
        if binding.implementation_kind == "accepted-skill"
    }
    if bound_skills != locked_skills:
        risks.append(
            _block(
                "EXEC-CAPABILITY-SKILL-MISMATCH",
                f"capability Skill bindings {sorted(bound_skills)} differ from Assignment lock {sorted(locked_skills)}",
            )
        )
    for binding in snapshot.bindings:
        if binding.source_ref is not None:
            check = check_file_reference(root, binding.source_ref)
            if not check.valid:
                risks.append(
                    _block(
                        "EXEC-CAPABILITY-REF-DRIFT",
                        f"binding {binding.requirement_id} source reference is {check.status}",
                    )
                )
    return method, snapshot


def _build_resolved_execution_view(
    root: Path,
    *,
    task_path: str | Path,
    assignment_path: str | Path,
    task: TaskPacket,
    assignment: ResolvedTask,
    method: MethodResolution | None,
    method_resolution_path: str | Path | None,
    snapshot: ResolvedCapabilitySnapshot | None,
    capability_snapshot_path: str | Path | None,
    from_state_path: str | Path | None,
    slot: str,
    binding: ModelBinding,
    limits: ApiSessionLimits,
    risks: list[ContractRisk],
) -> ResolvedExecutionView | None:
    if method is None or snapshot is None:
        if from_state_path is not None:
            risks.append(
                _block(
                    "EXEC-FROM-STATE-UNGOVERNED",
                    "--from-state requires Method Resolution and a Capability Snapshot",
                )
            )
        return None
    assert method_resolution_path is not None and capability_snapshot_path is not None

    for capability_binding in snapshot.bindings:
        details = capability_binding.binding_details
        pinned_slot = details.get("slot_id")
        if isinstance(pinned_slot, str) and pinned_slot != slot:
            risks.append(
                _block(
                    "EXEC-CAPABILITY-BINDING-MISMATCH",
                    f"snapshot pins slot {pinned_slot!r}, compiler received {slot!r}",
                )
            )
        pinned_adapter = details.get("provider_adapter")
        if isinstance(pinned_adapter, str) and pinned_adapter != binding.provider_adapter:
            risks.append(
                _block(
                    "EXEC-CAPABILITY-BINDING-MISMATCH",
                    f"snapshot pins adapter {pinned_adapter!r}, compiler bound {binding.provider_adapter!r}",
                )
            )
        side_effects = set(capability_binding.permissions.get("side_effects", ()))
        disallowed = sorted(side_effects - set(limits.allowed_tool_side_effects))
        if disallowed:
            risks.append(
                _block(
                    "EXEC-CAPABILITY-PERMISSION-MISMATCH",
                    f"binding {capability_binding.requirement_id} exceeds session side effects: {disallowed}",
                )
            )

    predecessor_ref: FrozenContractRef | None = None
    if from_state_path is not None:
        state_relative = _strict_relative(root, from_state_path)
        if state_relative is None:
            risks.append(_block("EXEC-FROM-STATE-INVALID", "predecessor state is outside the root"))
        else:
            state_document = _load_mapping(from_state_path)
            for issue in SchemaCatalog().validate("main_state", state_document):
                risks.append(
                    _block(
                        "EXEC-FROM-STATE-INVALID",
                        f"Main State schema error at {issue.pointer}: {issue.message}",
                    )
                )
            try:
                state = MainStatePacket.from_mapping(state_document)
            except ContractError as exc:
                risks.append(_block("EXEC-FROM-STATE-INVALID", str(exc)))
            else:
                active = [item for item in state.active_tasks if item.task_id == task.task_id]
                if len(active) != 1 or active[0].status not in {
                    "ready", "safe-paused", "incomplete", "waiting"
                }:
                    risks.append(
                        _block(
                            "EXEC-FROM-STATE-NOT-PREDECESSOR",
                            "Main State must name this Task exactly once in a resumable predecessor status",
                        )
                    )
                if state.continuity_status == "blocked":
                    risks.append(
                        _block(
                            "EXEC-FROM-STATE-NOT-PREDECESSOR",
                            "a blocked Main State cannot authorize execution",
                        )
                    )
                if state.created_at is None or state.checkpoint_digest is None:
                    risks.append(
                        _block(
                            "EXEC-FROM-STATE-NOT-PREDECESSOR",
                            "strict predecessor state requires created_at and checkpoint_digest",
                        )
                    )
                for reference in state.machine_state_refs:
                    if not check_file_reference(root, reference).valid:
                        risks.append(
                            _block(
                                "EXEC-FROM-STATE-DRIFT",
                                f"predecessor machine state drifted: {reference.path}",
                            )
                        )
            predecessor_ref = FrozenContractRef(state_relative, hash_file(Path(from_state_path)))

    refs: list[tuple[str, str]] = []
    frozen: list[FrozenContractRef] = []
    for label, path in (
        ("task", task_path),
        ("assignment", assignment_path),
        ("method", method_resolution_path),
        ("capability", capability_snapshot_path),
    ):
        relative = _strict_relative(root, path)
        if relative is None:
            risks.append(_block("EXEC-RESOLUTION-OUTSIDE-ROOT", f"{label} is outside the root"))
            relative = str(path)
        digest = hash_file(Path(path))
        refs.append((relative, digest))
        frozen.append(FrozenContractRef(relative, digest))
    identity_payload = {
        "contracts": refs,
        "predecessor": (
            [predecessor_ref.path, predecessor_ref.sha256] if predecessor_ref is not None else None
        ),
        "bindings": sorted(
            (
                item.requirement_id,
                item.capability_id,
                item.implementation_kind,
                item.implementation_id,
            )
            for item in snapshot.bindings
        ),
        "model_binding": {
            "slot_id": binding.slot_id,
            "provider_adapter": binding.provider_adapter,
            "provider": binding.provider,
            "model": binding.model,
            "reasoning_effort": binding.reasoning_effort,
        },
        "limits": {
            "max_model_turns": limits.max_model_turns,
            "max_tool_calls": limits.max_tool_calls,
            "max_parallel_tool_calls": limits.max_parallel_tool_calls,
            "max_output_tokens_per_turn": limits.max_output_tokens_per_turn,
            "max_seconds": limits.max_seconds,
            "allowed_tool_side_effects": sorted(limits.allowed_tool_side_effects),
        },
    }
    identity = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ResolvedExecutionView(
        task_ref=frozen[0],
        assignment_ref=frozen[1],
        method_resolution_ref=frozen[2],
        capability_snapshot_ref=frozen[3],
        predecessor_state_ref=predecessor_ref,
        capability_binding_ids=tuple(
            sorted(item.requirement_id for item in snapshot.bindings)
        ),
        identity_sha256=identity,
    )


def _strict_relative(root: Path, path: str | Path) -> str | None:
    target = Path(path)
    if not target.is_absolute():
        target = root / target
    try:
        return target.resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def _check_exact_reference(
    root: Path,
    reference: FileReference,
    expected_path: str,
    label: str,
    code: str,
    risks: list[ContractRisk],
) -> None:
    if reference.path != expected_path:
        risks.append(_block(code, f"{label} reference path is {reference.path!r}, expected {expected_path!r}"))
    check = check_file_reference(root, reference)
    if not check.valid:
        risks.append(_block(code, f"{label} reference is {check.status}"))


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
    method: MethodResolution | None,
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
    if method is not None:
        lines.extend(
            [
                "",
                f"Frozen Method Resolution: {method.resolution_id}",
                "Selected Mode Actions: "
                + ", ".join(
                    item.action_id for item in method.action_selections if item.status == "selected"
                ),
                "Method obligations:",
            ]
        )
        lines.extend(
            "- " + str(item.get("obligation", ""))
            for item in method.method_obligations
            if item.get("obligation")
        )
        lines.append(
            "Do not change the selected Mode Action, mechanism, source boundary, or Human Gate."
        )
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
    if "evidence-record" in required_outputs:
        lines.append(
            "Every Evidence output must bind its exact frozen Task input in "
            "metadata.source_file_ref={path, sha256}; source_ref and locator alone are insufficient."
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
