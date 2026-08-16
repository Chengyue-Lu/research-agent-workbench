"""One narrow Task-to-API-to-files orchestration function for K-API-2."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
from pathlib import Path, PurePosixPath
from typing import Any

from research_workbench.adapters.models import (
    ApiSessionLimits,
    ApiSessionResult,
    ApiSessionStatus,
    IsolatedApiSessionRunner,
    ModelAssignment,
    ProviderError,
    ProviderRegistry,
)
from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.execution.closeout import (
    TERMINAL_STATUSES,
    CloseoutError,
    CloseoutPublication,
    capture_closeout_contracts,
    closeout_api_attempt,
    contract_snapshot_document,
    fail_if_api_attempt_intent_exists,
    inspect_committed_closeout,
    record_api_attempt_intent,
    resume_staged_closeout,
    staged_closeout_exists,
    validate_closeout_preconditions,
)
from research_workbench.execution.compiler import (
    ApiExecutionCompilationError,
    compile_api_execution,
    derive_execution_controls,
    verify_execution_material,
)
from research_workbench.execution.contracts import (
    ContractAdmission,
    ExecutionContractError,
    default_execution_contract_registry,
)
from research_workbench.execution.output import ApiTaskOutputError
from research_workbench.execution.tool_registry import (
    ExecutionToolRegistryError,
    default_execution_tool_registry,
)
from research_workbench.execution.closeout.verify import _validate_output_paths
from research_workbench.observability.trace_recorder import (
    ApiTraceMetadata,
    BoundaryCallStatus,
    CaptureGapKind,
    FrozenReadMetadata,
    FrozenTraceReference,
    TraceActorMetadata,
    TraceCaptureGap,
    TraceRecorderError,
    begin_api_trace,
)
from research_workbench.protocol import ProjectProtocol
from research_workbench.io import load_document, write_yaml_exclusive
from research_workbench.tasks import FileReference, TaskPacket


class _ProviderEphemeralCleanupError(RuntimeError):
    """A Provider-private continuation could not be discarded safely."""


def _discard_provider_ephemeral_state(provider: Any) -> None:
    discard = getattr(provider, "discard_ephemeral_continuation", None)
    if not callable(discard):
        return
    try:
        discard()
    except Exception as exc:
        raise _ProviderEphemeralCleanupError from exc


class _TraceSessionObserver:
    """Bridge sanitized runner boundaries into one two-phase Trace recorder."""

    def __init__(self, recorder: Any, *, occurred_at: Callable[[], str]) -> None:
        self._recorder = recorder
        self._occurred_at = occurred_at
        self._provider_tokens: dict[int, int] = {}
        self._tool_tokens: dict[int, int] = {}
        self.completed_provider_calls = 0

    def provider_call_started(
        self,
        *,
        call_number: int,
        provider_identity: str,
        model: str,
    ) -> None:
        token = self._recorder.record_provider_call_started(
            occurred_at=self._occurred_at(),
            provider_identity=provider_identity,
            model=model,
        )
        if token != call_number:
            raise TraceRecorderError("Provider boundary sequence differs from the runner")
        self._provider_tokens[call_number] = token

    def provider_call_finished(self, *, call_number: int, status: str) -> None:
        token = self._provider_tokens.pop(call_number, None)
        if token is None:
            raise TraceRecorderError("Provider finish lacks its runner start boundary")
        self._recorder.record_provider_call_finished(
            token,
            occurred_at=self._occurred_at(),
            status=BoundaryCallStatus(status),
        )
        self.completed_provider_calls += 1

    def tool_call_started(self, *, call_number: int, tool_name: str) -> None:
        token = self._recorder.record_tool_call_started(
            occurred_at=self._occurred_at(),
            tool_name=tool_name,
        )
        if token != call_number:
            raise TraceRecorderError("Tool boundary sequence differs from the runner")
        self._tool_tokens[call_number] = token

    def tool_call_finished(
        self,
        *,
        call_number: int,
        tool_name: str,
        status: str,
        result_char_count: int,
        result_entered_context: bool,
        frozen_read_path: str | None,
        frozen_read_sha256: str | None,
        captured_result: object | None,
    ) -> None:
        del tool_name  # the recorder reuses the already frozen start-boundary name
        token = self._tool_tokens.pop(call_number, None)
        if token is None:
            raise TraceRecorderError("Tool finish lacks its runner start boundary")
        frozen_read = (
            FrozenReadMetadata(frozen_read_path, frozen_read_sha256)
            if frozen_read_path is not None and frozen_read_sha256 is not None
            else None
        )
        self._recorder.record_tool_call_finished(
            token,
            occurred_at=self._occurred_at(),
            status=BoundaryCallStatus(status),
            result_char_count=result_char_count,
            result_entered_context=result_entered_context,
            frozen_read=frozen_read,
            captured_result=captured_result,
        )


def run_task_api_attempt(
    *,
    root: str | Path,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    model_assignment: ModelAssignment,
    providers: ProviderRegistry,
    runtime_limits: ApiSessionLimits,
    attempt_id: str,
    started_at: str,
    finished_at: str,
    next_actions: Mapping[str, str],
    trace_accountable_owner: str,
    trace_baseline: str | None = None,
    previous_main_state_ref: str | None = None,
    extra_limitations: tuple[str, ...] = (),
    fault_injector: Callable[[str], None] | None = None,
    event_clock: Callable[[], str] | None = None,
    provider_conformance_document: Mapping[str, Any] | None = None,
    provider_conformance_expected_sha256: str | None = None,
) -> CloseoutPublication:
    """Run exactly one fresh API Attempt and return no transcript-bearing object."""

    missing_actions = sorted(TERMINAL_STATUSES - set(next_actions))
    invalid_actions = sorted(
        key
        for key in TERMINAL_STATUSES & set(next_actions)
        if not isinstance(next_actions[key], str) or not next_actions[key].strip()
    )
    if missing_actions or invalid_actions:
        affected = missing_actions + invalid_actions
        raise ValueError(
            "next_actions requires a non-empty action for every terminal status: "
            + ", ".join(affected)
        )
    project_root = Path(root).resolve()
    has_stage = staged_closeout_exists(root=project_root, attempt_id=attempt_id)
    contract_specifications = [
        (protocol_ref, "project_protocol"),
        (task_ref, "task_packet"),
        (profile_ref, "agent_profile"),
        (assignment_ref, "skill_assignment"),
    ]
    if previous_main_state_ref is not None:
        contract_specifications.append((previous_main_state_ref, "main_state"))
    contract_snapshots = capture_closeout_contracts(
        project_root, tuple(contract_specifications)
    )
    protocol = ProjectProtocol.from_mapping(
        contract_snapshot_document(contract_snapshots, protocol_ref)
    )
    task = TaskPacket.from_mapping(contract_snapshot_document(contract_snapshots, task_ref))
    profile = AgentProfile.from_mapping(
        contract_snapshot_document(contract_snapshots, profile_ref)
    )
    assignment = ResolvedTask.from_mapping(
        contract_snapshot_document(contract_snapshots, assignment_ref)
    )
    try:
        model_assignment = ModelAssignment.from_mapping(model_assignment.to_mapping())
    except (TypeError, ValueError) as exc:
        raise CloseoutError(
            "MODEL-ASSIGNMENT-INVALID", "Model Assignment is not canonically immutable"
        ) from exc
    binding = model_assignment.to_binding()
    profile_digest = next(
        snapshot.sha256 for snapshot in contract_snapshots if snapshot.ref == profile_ref
    )
    if model_assignment.attempt_id != attempt_id:
        raise CloseoutError(
            "MODEL-ASSIGNMENT-ATTEMPT-MISMATCH",
            "Model Assignment does not match the requested Attempt",
        )
    if (model_assignment.task_id, model_assignment.task_revision) != (
        task.task_id,
        task.revision,
    ):
        raise CloseoutError(
            "MODEL-ASSIGNMENT-TASK-MISMATCH",
            "Model Assignment does not match the frozen Task",
        )
    if (
        model_assignment.agent_profile_ref.path != profile_ref
        or model_assignment.agent_profile_ref.sha256 != profile_digest
    ):
        raise CloseoutError(
            "MODEL-ASSIGNMENT-PROFILE-MISMATCH",
            "Model Assignment does not hash-pin the frozen Agent Profile",
        )
    if model_assignment.selection_source == "profile-default" and (
        model_assignment.slot_id != profile.model_policy.get("default_slot")
    ):
        raise CloseoutError(
            "MODEL-SLOT-MISMATCH",
            "profile-default Model Assignment does not use the Profile default slot",
        )
    try:
        execution_contract = default_execution_contract_registry().require(task, assignment)
        effective_data_policy, effective_limits = derive_execution_controls(
            protocol=protocol,
            task=task,
            runtime_limits=runtime_limits,
            execution_contract=execution_contract,
        )
    except (ExecutionContractError, ApiExecutionCompilationError) as exc:
        raise CloseoutError(exc.code, str(exc).split(": ", 1)[-1]) from exc
    if model_assignment.effective_data_policy != effective_data_policy:
        raise CloseoutError(
            "MODEL-ASSIGNMENT-DATA-POLICY",
            "Model Assignment data policy differs from the frozen Project Protocol",
        )
    if model_assignment.execution_limits != effective_limits:
        raise CloseoutError(
            "MODEL-ASSIGNMENT-EXECUTION-LIMITS",
            "Model Assignment limits differ from the effective bounded Task limits",
        )
    frozen_contract_payloads = _freeze_contract_payloads(
        project_root,
        execution_contract.supporting_refs,
        model_assignment,
    )
    previous_main_state_document = (
        contract_snapshot_document(contract_snapshots, previous_main_state_ref)
        if previous_main_state_ref is not None
        else None
    )
    committed = inspect_committed_closeout(
        root=project_root,
        task_id=task.task_id,
        attempt_id=attempt_id,
        protocol_ref=protocol_ref,
        task_ref=task_ref,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        previous_main_state_ref=previous_main_state_ref,
        expected_provider_adapter_id=binding.provider_adapter,
        expected_model=binding.model,
        expected_model_assignment_id=model_assignment.model_assignment_id,
        expected_execution_contract=execution_contract.identifier,
    )
    if committed is not None:
        return committed
    if has_stage:
        return resume_staged_closeout(
            root=project_root,
            attempt_id=attempt_id,
            expected_task_id=task.task_id,
            expected_protocol_ref=protocol_ref,
            expected_task_ref=task_ref,
            expected_profile_ref=profile_ref,
            expected_assignment_ref=assignment_ref,
            expected_provider_adapter_id=binding.provider_adapter,
            expected_model=binding.model,
            expected_model_assignment_id=model_assignment.model_assignment_id,
            expected_execution_contract=execution_contract.identifier,
            expected_previous_main_state_ref=previous_main_state_ref,
            fault_injector=fault_injector,
        )
    model_assignment_ref = _persist_model_assignment(
        project_root,
        task,
        assignment,
        attempt_id,
        model_assignment,
    )
    validate_closeout_preconditions(
        root=project_root,
        protocol=protocol,
        task=task,
        profile=profile,
        assignment=assignment,
        protocol_ref=protocol_ref,
        task_ref=task_ref,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        attempt_id=attempt_id,
        started_at=started_at,
        finished_at=finished_at,
        previous_main_state_ref=previous_main_state_ref,
        previous_main_state_document=previous_main_state_document,
    )

    intent_created = record_api_attempt_intent(
        root=project_root,
        attempt_id=attempt_id,
        task_id=task.task_id,
        protocol_ref=protocol_ref,
        task_ref=task_ref,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        provider_adapter_id=binding.provider_adapter,
        requested_model=binding.model,
        model_assignment_id=model_assignment.model_assignment_id,
        model_assignment_ref=model_assignment_ref,
        execution_contract=execution_contract.identifier,
        started_at=started_at,
        previous_main_state_ref=previous_main_state_ref,
    )
    if not intent_created:
        fail_if_api_attempt_intent_exists(
            root=project_root,
            attempt_id=attempt_id,
            task_id=task.task_id,
            protocol_ref=protocol_ref,
            task_ref=task_ref,
            profile_ref=profile_ref,
            assignment_ref=assignment_ref,
            provider_adapter_id=binding.provider_adapter,
            requested_model=binding.model,
            model_assignment_id=model_assignment.model_assignment_id,
            model_assignment_ref=model_assignment_ref,
            execution_contract=execution_contract.identifier,
            previous_main_state_ref=previous_main_state_ref,
        )
        raise CloseoutError(
            "API-ATTEMPT-ALREADY-STARTED",
            "another invocation already recorded this Attempt; Provider replay is forbidden",
        )

    attempt_root = f"work/{task.task_id}/{attempt_id}"
    coordinator_actor_id = "main-runtime"
    worker_actor_id = "model-worker"
    trace_paths = (
        f"{attempt_root}/ACTORS.yaml",
        f"{attempt_root}/INDEX.yaml",
        f"{attempt_root}/events.jsonl",
        f"{attempt_root}/messages/0001-{coordinator_actor_id}-to-{worker_actor_id}-assignment.md",
        f"{attempt_root}/messages/0002-{worker_actor_id}-to-{coordinator_actor_id}-handoff.md",
        f"{attempt_root}/tool-events/0001-provider-call-started.json",
    )
    _validate_output_paths(project_root, task, assignment, trace_paths)
    try:
        trace_recorder = begin_api_trace(
            project_root,
            ApiTraceMetadata(
                trace_id=f"TRACE-{task.task_id}-{attempt_id}",
                task_id=task.task_id,
                task_revision=task.revision,
                attempt_id=attempt_id,
                baseline=(
                    trace_baseline
                    or f"model-assignment-{model_assignment_ref.sha256}"
                ),
                task_path=task_ref,
                archive_root=attempt_root,
                owner_actor_id=coordinator_actor_id,
                coordinator_actor_id=coordinator_actor_id,
                worker_actor_id=worker_actor_id,
                actors=(
                    TraceActorMetadata(
                        actor_id=coordinator_actor_id,
                        actor_type="agent",
                        role="coordinator",
                        runtime_identity="rwb-main-runtime@0.1.0",
                        accountable_owner=trace_accountable_owner,
                    ),
                    TraceActorMetadata(
                        actor_id=worker_actor_id,
                        actor_type="agent",
                        role="worker",
                        runtime_identity=(
                            f"{binding.provider_adapter}@{binding.model}"
                        ),
                        accountable_owner=trace_accountable_owner,
                    ),
                ),
                read_allowlist=tuple(
                    dict.fromkeys(
                        (task_ref, *(reference.path for reference in task.input_refs))
                    )
                ),
                write_scope=task.write_scope,
                tool_allowlist=assignment.resolved_tools,
            ),
            started_at=started_at,
            assignment_at=started_at,
        )
    except TraceRecorderError as exc:
        raise CloseoutError(
            "AGENT-TRACE-CAPTURE-FAILED",
            "Agent Trace assignment capture failed before Provider dispatch",
        ) from exc
    boundary_time = event_clock or (lambda: started_at)
    trace_observer = _TraceSessionObserver(trace_recorder, occurred_at=boundary_time)

    def closeout_terminal(
        *,
        terminal_status: str,
        failure_code: str | None,
        failure_summary: str | None,
        action_key: str | None = None,
        session_result: ApiSessionResult | None = None,
        output: Mapping[str, Any] | None = None,
        admission: ContractAdmission | None = None,
        provider_adapter_id: str | None = None,
        requested_model: str | None = None,
        provider_adapter_version: str = "unavailable",
        expected_provider_identity: str | None = None,
        limits: ApiSessionLimits | None = None,
        external_provider: bool = False,
        frozen_input_payloads: Mapping[str, bytes] | None = None,
    ) -> CloseoutPublication:
        """Close out at one terminal boundary; defaults hold the pre-compile phase."""

        terminal_finished_at = event_clock() if event_clock is not None else finished_at
        trace_status = action_key or terminal_status
        gaps: tuple[TraceCaptureGap, ...] = ()
        if trace_observer.completed_provider_calls == 0:
            gaps = (
                TraceCaptureGap(CaptureGapKind.RUNTIME_EXPORT, terminal_finished_at),
            )
        def seal_trace(
            *,
            stage_root: Path,
            handoff_refs: tuple[str, ...],
            decision_refs: tuple[str, ...],
            output_refs: tuple[str, ...],
            check_refs: tuple[str, ...],
        ) -> tuple[FileReference, Mapping[str, bytes]]:
            def freeze(paths: tuple[str, ...]) -> tuple[FrozenTraceReference, ...]:
                frozen: list[FrozenTraceReference] = []
                for relative in paths:
                    candidate = resolve_within_root(stage_root, relative)
                    if (
                        candidate is None
                        or not candidate.is_file()
                        or candidate.is_symlink()
                    ):
                        raise TraceRecorderError(
                            f"staged closeout reference is unavailable: {relative}"
                        )
                    payload = candidate.read_bytes()
                    frozen.append(
                        FrozenTraceReference(
                            relative,
                            hashlib.sha256(payload).hexdigest(),
                            payload,
                        )
                    )
                return tuple(frozen)

            try:
                bundle = trace_recorder.seal(
                    attempt_status=trace_status,
                    handoff_at=terminal_finished_at,
                    finished_at=terminal_finished_at,
                    capture_gaps=gaps,
                    handoff_refs=freeze(handoff_refs),
                    decision_refs=freeze(decision_refs),
                    output_refs=freeze(output_refs),
                    check_refs=freeze(check_refs),
                )
            except TraceRecorderError as exc:
                _raise_if_contract_snapshots_drifted(
                    project_root,
                    contract_snapshots,
                )
                raise CloseoutError(
                    "AGENT-TRACE-CAPTURE-FAILED",
                    "Agent Trace could not be sealed; this Attempt cannot be replayed",
                ) from exc
            return (
                FileReference(bundle.index_path, bundle.index_sha256),
                dict(bundle.payloads),
            )

        return closeout_api_attempt(
            root=project_root,
            protocol_ref=protocol_ref,
            task_ref=task_ref,
            profile_ref=profile_ref,
            assignment_ref=assignment_ref,
            attempt_id=attempt_id,
            started_at=started_at,
            finished_at=terminal_finished_at,
            terminal_status=terminal_status,
            next_action=next_actions[action_key or terminal_status],
            provider_adapter_id=provider_adapter_id or binding.provider_adapter,
            requested_model=requested_model or binding.model,
            provider_adapter_version=provider_adapter_version,
            expected_provider_identity=expected_provider_identity,
            limits=limits or model_assignment.execution_limits,
            session_result=session_result,
            output=output,
            failure_code=failure_code,
            failure_summary=failure_summary,
            previous_main_state_ref=previous_main_state_ref,
            external_provider=external_provider,
            provider_conformance_document=provider_conformance_document,
            provider_conformance_expected_sha256=provider_conformance_expected_sha256,
            extra_limitations=extra_limitations,
            fault_injector=fault_injector,
            contract_snapshots=contract_snapshots,
            frozen_input_payloads=frozen_input_payloads,
            frozen_contract_payloads=frozen_contract_payloads,
            execution_contract=execution_contract,
            admission=admission,
            model_assignment=model_assignment,
            agent_trace_sealer=seal_trace,
        )

    try:
        material = verify_execution_material(project_root, task, assignment)
        contract_tools = default_execution_tool_registry().build_tools(
            root=project_root,
            task=task,
            limits=model_assignment.execution_limits,
            contract=execution_contract,
            assignment=assignment,
        )
    except (ApiExecutionCompilationError, ExecutionToolRegistryError) as exc:
        return closeout_terminal(
            terminal_status="blocked",
            failure_code=exc.code,
            failure_summary=(
                "Frozen execution material failed verification before Provider generation "
                "or a tool call."
            ),
        )

    frozen_input_payloads = dict(
        zip(
            (reference.path for reference in material.input_refs),
            material.input_payloads,
            strict=True,
        )
    )

    try:
        provider = providers.get(binding.provider_adapter)
        snapshot = provider.capabilities()
    except Exception as exc:
        return closeout_terminal(
            terminal_status="blocked",
            failure_code="PROVIDER-CAPABILITIES-UNAVAILABLE",
            failure_summary=(
                f"Provider capability discovery raised {type(exc).__name__}; "
                "no exception message was persisted."
            ),
            frozen_input_payloads=frozen_input_payloads,
        )

    try:
        compiled = compile_api_execution(
            protocol=protocol,
            task=task,
            profile=profile,
            assignment=assignment,
            binding=binding,
            provider_capabilities=snapshot,
            verified_material=material,
            runtime_limits=runtime_limits,
            tool_catalog={tool.definition.name: tool for tool in contract_tools},
            execution_contract=execution_contract,
            model_assignment=model_assignment,
        )
    except ApiExecutionCompilationError as exc:
        return closeout_terminal(
            terminal_status="blocked",
            failure_code=exc.code,
            failure_summary=(
                "Task-to-API compilation was blocked before Provider generation or a tool call."
            ),
            provider_adapter_version=snapshot.adapter_version,
            expected_provider_identity=snapshot.provider,
            frozen_input_payloads=frozen_input_payloads,
        )

    runner = IsolatedApiSessionRunner(
        providers,
        tools=compiled.client_tools,
        observer=trace_observer,
    )
    try:
        try:
            result = runner.run(
                adapter_id=compiled.adapter_id,
                request=compiled.request,
                limits=compiled.limits,
                expected_capabilities=compiled.provider_capabilities,
            )
        finally:
            _discard_provider_ephemeral_state(provider)
    except _ProviderEphemeralCleanupError:
        return closeout_terminal(
            terminal_status="failed",
            failure_code="PROVIDER-EPHEMERAL-CLEANUP-FAILED",
            failure_summary=(
                "Provider-private continuation cleanup failed; no exception message "
                "was persisted and the Provider instance must not be reused."
            ),
            provider_adapter_id=compiled.adapter_id,
            requested_model=compiled.request.model,
            provider_adapter_version=snapshot.adapter_version,
            expected_provider_identity=snapshot.provider,
            limits=compiled.limits,
            external_provider=snapshot.deployment != "local",
            frozen_input_payloads=frozen_input_payloads,
        )
    except TraceRecorderError as exc:
        raise CloseoutError(
            "AGENT-TRACE-CAPTURE-FAILED",
            "Agent Trace runtime capture failed; this Attempt cannot be replayed",
        ) from exc
    except Exception as exc:  # normalize the bounded execution boundary, not arbitrary process errors
        return closeout_terminal(
            terminal_status="failed",
            failure_code=_execution_exception_code(exc),
            failure_summary=(
                f"The isolated API runner raised {type(exc).__name__}; "
                "no exception message was persisted."
            ),
            provider_adapter_id=compiled.adapter_id,
            requested_model=compiled.request.model,
            provider_adapter_version=snapshot.adapter_version,
            expected_provider_identity=snapshot.provider,
            limits=compiled.limits,
            external_provider=snapshot.deployment != "local",
            frozen_input_payloads=frozen_input_payloads,
        )

    try:
        verify_execution_material(project_root, task, assignment)
    except ApiExecutionCompilationError as exc:
        return closeout_terminal(
            terminal_status="blocked",
            action_key=_effective_status("blocked", result),
            failure_code=exc.code,
            failure_summary=(
                "Frozen Task input or selected Skill material drifted during the isolated session; "
                "no model output was admitted."
            ),
            session_result=result,
            provider_adapter_id=compiled.adapter_id,
            requested_model=compiled.request.model,
            provider_adapter_version=snapshot.adapter_version,
            expected_provider_identity=snapshot.provider,
            limits=compiled.limits,
            external_provider=snapshot.deployment != "local",
            frozen_input_payloads=frozen_input_payloads,
        )

    status = result.status.value
    output: Mapping[str, Any] | None = None
    admission: ContractAdmission | None = None
    failure_code: str | None = None
    failure_summary: str | None = None
    if result.status == ApiSessionStatus.COMPLETED:
        try:
            admission = compiled.execution_contract.admit_response(
                result.final_response,
                task=task,
                protocol=protocol,
            )
            status = admission.success_status
        except ApiTaskOutputError as exc:
            status = "failed"
            failure_code = exc.code
            failure_summary = "The terminal model output did not satisfy the trusted API output contract."
        except Exception:
            status = "failed"
            failure_code = "API-OUTPUT-VALIDATION-EXCEPTION"
            failure_summary = (
                "The trusted API output boundary rejected an unexpected validation failure; "
                "no exception message or model output was persisted."
            )
    effective_status = _effective_status(status, result)
    return closeout_terminal(
        terminal_status=status,
        action_key=effective_status,
        failure_code=failure_code,
        failure_summary=failure_summary,
        session_result=result,
        output=output,
        admission=admission,
        provider_adapter_id=compiled.adapter_id,
        requested_model=compiled.request.model,
        provider_adapter_version=snapshot.adapter_version,
        expected_provider_identity=snapshot.provider,
        limits=compiled.limits,
        external_provider=snapshot.deployment != "local",
        frozen_input_payloads=frozen_input_payloads,
    )


def _effective_status(status: str, result: Any) -> str:
    if result.tool_failures:
        return "failed"
    if set(result.observed_models) - {result.requested_model}:
        return "failed"
    return status


def _raise_if_contract_snapshots_drifted(
    project_root: Path,
    snapshots: tuple[Any, ...],
) -> None:
    """Preserve contract-drift precedence when Trace sealing sees the drift first."""

    for snapshot in snapshots:
        resolved = resolve_within_root(project_root, snapshot.ref)
        if (
            resolved is None
            or not resolved.is_file()
            or resolved.read_bytes() != snapshot.payload
        ):
            raise CloseoutError(
                "EXECUTION-CONTRACT-DRIFT",
                f"contract bytes changed during Attempt: {snapshot.ref}",
            )


def _execution_exception_code(exc: Exception) -> str:
    if isinstance(exc, ProviderError):
        return "PROVIDER-" + exc.category.value.upper().replace("-", "_")
    return "API-SESSION-EXCEPTION"


def _persist_model_assignment(
    project_root: Path,
    task: TaskPacket,
    assignment: ResolvedTask,
    attempt_id: str,
    model_assignment: ModelAssignment,
) -> FileReference:
    """Publish the immutable Model Assignment before any Provider boundary."""

    relative = f"work/{task.task_id}/{attempt_id}/model-assignment.yaml"
    _validate_output_paths(project_root, task, assignment, (relative,))
    # ``relative`` is trusted, path-safe generated identity and was authorized
    # above.  Construct the literal path after that check instead of resolving
    # a concurrently-created parent twice on Windows.
    path = project_root.joinpath(*PurePosixPath(relative).parts)
    try:
        write_yaml_exclusive(path, model_assignment.to_mapping())
    except FileExistsError as exc:
        raise CloseoutError(
            "MODEL-ASSIGNMENT-DRIFT",
            "an immutable Model Assignment already exists with different bytes",
        ) from exc
    try:
        persisted = load_document(path)
        recovered = ModelAssignment.from_mapping(persisted)
    except Exception as exc:
        raise CloseoutError(
            "MODEL-ASSIGNMENT-DRIFT",
            "persisted Model Assignment cannot be canonically recovered",
        ) from exc
    if recovered.model_assignment_id != model_assignment.model_assignment_id:
        raise CloseoutError(
            "MODEL-ASSIGNMENT-DRIFT",
            "persisted Model Assignment identity differs before Provider dispatch",
        )
    return FileReference(relative, hash_file(path))


def _freeze_contract_payloads(
    project_root: Path,
    supporting_refs: tuple[str, ...],
    model_assignment: ModelAssignment,
) -> dict[str, bytes]:
    references = set(supporting_refs)
    if model_assignment.selection_ref is not None:
        references.add(model_assignment.selection_ref.path)
    payloads: dict[str, bytes] = {}
    for relative in sorted(references):
        resolved = resolve_within_root(project_root, relative)
        if resolved is None or not resolved.is_file() or resolved.is_symlink():
            raise CloseoutError(
                "EXECUTION-CONTRACT-SNAPSHOT",
                f"execution support reference is unavailable: {relative}",
            )
        payloads[relative] = resolved.read_bytes()
    if model_assignment.selection_ref is not None:
        expected = model_assignment.selection_ref.sha256
        payload = payloads[model_assignment.selection_ref.path]
        if hashlib.sha256(payload).hexdigest() != expected:
            raise CloseoutError(
                "MODEL-ASSIGNMENT-SELECTION-DRIFT",
                "Model Assignment override reference digest differs before execution",
            )
    return payloads
