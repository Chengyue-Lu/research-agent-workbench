"""One narrow Task-to-API-to-files orchestration function for K-API-2."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from research_workbench.adapters.models import (
    ApiSessionLimits,
    ApiSessionStatus,
    IsolatedApiSessionRunner,
    ModelBinding,
    ProviderError,
    ProviderRegistry,
)
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.execution.closeout import (
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
    build_document_read_tool,
    compile_api_execution,
    verify_execution_material,
)
from research_workbench.execution.output import ApiTaskOutputError, parse_api_task_output
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import TaskPacket


_REQUIRED_ACTIONS = frozenset(
    {"completed", "safe-paused", "incomplete", "failed", "blocked"}
)


def run_task_api_attempt(
    *,
    root: str | Path,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    binding: ModelBinding,
    providers: ProviderRegistry,
    runtime_limits: ApiSessionLimits,
    attempt_id: str,
    started_at: str,
    finished_at: str,
    next_actions: Mapping[str, str],
    previous_main_state_ref: str | None = None,
    extra_limitations: tuple[str, ...] = (),
    fault_injector: Callable[[str], None] | None = None,
) -> CloseoutPublication:
    """Run exactly one fresh API Attempt and return no transcript-bearing object."""

    missing_actions = sorted(_REQUIRED_ACTIONS - set(next_actions))
    if missing_actions or any(
        not isinstance(next_actions[key], str) or not next_actions[key].strip()
        for key in _REQUIRED_ACTIONS
    ):
        raise ValueError(
            "next_actions requires non-empty completed, safe-paused, incomplete, failed, "
            "and blocked entries"
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
            expected_previous_main_state_ref=previous_main_state_ref,
            fault_injector=fault_injector,
        )
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
        previous_main_state_ref=previous_main_state_ref,
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

    try:
        material = verify_execution_material(project_root, task, assignment)
        document_read = build_document_read_tool(project_root, task)
    except ApiExecutionCompilationError as exc:
        return closeout_api_attempt(
            root=project_root,
            protocol_ref=protocol_ref,
            task_ref=task_ref,
            profile_ref=profile_ref,
            assignment_ref=assignment_ref,
            attempt_id=attempt_id,
            started_at=started_at,
            finished_at=finished_at,
            terminal_status="blocked",
            next_action=next_actions["blocked"],
            provider_adapter_id=binding.provider_adapter,
            requested_model=binding.model,
            provider_adapter_version="unavailable",
            expected_provider_identity=None,
            limits=runtime_limits,
            failure_code=exc.code,
            failure_summary="Frozen execution material failed verification before Provider generation or a tool call.",
            previous_main_state_ref=previous_main_state_ref,
            external_provider=False,
            extra_limitations=extra_limitations,
            fault_injector=fault_injector,
            contract_snapshots=contract_snapshots,
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
        return closeout_api_attempt(
            root=project_root,
            protocol_ref=protocol_ref,
            task_ref=task_ref,
            profile_ref=profile_ref,
            assignment_ref=assignment_ref,
            attempt_id=attempt_id,
            started_at=started_at,
            finished_at=finished_at,
            terminal_status="blocked",
            next_action=next_actions["blocked"],
            provider_adapter_id=binding.provider_adapter,
            requested_model=binding.model,
            provider_adapter_version="unavailable",
            expected_provider_identity=None,
            limits=runtime_limits,
            failure_code="PROVIDER-CAPABILITIES-UNAVAILABLE",
            failure_summary=(
                f"Provider capability discovery raised {type(exc).__name__}; "
                "no exception message was persisted."
            ),
            previous_main_state_ref=previous_main_state_ref,
            external_provider=False,
            extra_limitations=extra_limitations,
            fault_injector=fault_injector,
            contract_snapshots=contract_snapshots,
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
            tool_catalog={"document-read": document_read},
        )
    except ApiExecutionCompilationError as exc:
        return closeout_api_attempt(
            root=project_root,
            protocol_ref=protocol_ref,
            task_ref=task_ref,
            profile_ref=profile_ref,
            assignment_ref=assignment_ref,
            attempt_id=attempt_id,
            started_at=started_at,
            finished_at=finished_at,
            terminal_status="blocked",
            next_action=next_actions["blocked"],
            provider_adapter_id=binding.provider_adapter,
            requested_model=binding.model,
            provider_adapter_version=snapshot.adapter_version,
            expected_provider_identity=snapshot.provider,
            limits=runtime_limits,
            failure_code=exc.code,
            failure_summary="Task-to-API compilation was blocked before Provider generation or a tool call.",
            previous_main_state_ref=previous_main_state_ref,
            external_provider=False,
            extra_limitations=extra_limitations,
            fault_injector=fault_injector,
            contract_snapshots=contract_snapshots,
            frozen_input_payloads=frozen_input_payloads,
        )

    runner = IsolatedApiSessionRunner(providers, tools=compiled.client_tools)
    intent_created = record_api_attempt_intent(
        root=project_root,
        attempt_id=attempt_id,
        task_id=task.task_id,
        protocol_ref=protocol_ref,
        task_ref=task_ref,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        provider_adapter_id=compiled.adapter_id,
        requested_model=compiled.request.model,
        started_at=started_at,
        previous_main_state_ref=previous_main_state_ref,
    )
    if not intent_created:
        raise CloseoutError(
            "API-ATTEMPT-ALREADY-STARTED",
            "another invocation already recorded this Attempt; Provider replay is forbidden",
        )
    try:
        result = runner.run(
            adapter_id=compiled.adapter_id,
            request=compiled.request,
            limits=compiled.limits,
            expected_capabilities=compiled.provider_capabilities,
        )
    except Exception as exc:  # normalize the bounded execution boundary, not arbitrary process errors
        code = _execution_exception_code(exc)
        return closeout_api_attempt(
            root=project_root,
            protocol_ref=protocol_ref,
            task_ref=task_ref,
            profile_ref=profile_ref,
            assignment_ref=assignment_ref,
            attempt_id=attempt_id,
            started_at=started_at,
            finished_at=finished_at,
            terminal_status="failed",
            next_action=next_actions["failed"],
            provider_adapter_id=compiled.adapter_id,
            requested_model=compiled.request.model,
            provider_adapter_version=snapshot.adapter_version,
            expected_provider_identity=snapshot.provider,
            limits=compiled.limits,
            failure_code=code,
            failure_summary=f"The isolated API runner raised {type(exc).__name__}; no exception message was persisted.",
            previous_main_state_ref=previous_main_state_ref,
            external_provider=snapshot.deployment != "local",
            extra_limitations=extra_limitations,
            fault_injector=fault_injector,
            contract_snapshots=contract_snapshots,
            frozen_input_payloads=frozen_input_payloads,
        )

    try:
        verify_execution_material(project_root, task, assignment)
    except ApiExecutionCompilationError as exc:
        effective_status = _effective_status("blocked", result)
        return closeout_api_attempt(
            root=project_root,
            protocol_ref=protocol_ref,
            task_ref=task_ref,
            profile_ref=profile_ref,
            assignment_ref=assignment_ref,
            attempt_id=attempt_id,
            started_at=started_at,
            finished_at=finished_at,
            terminal_status="blocked",
            next_action=next_actions[effective_status],
            provider_adapter_id=compiled.adapter_id,
            requested_model=compiled.request.model,
            provider_adapter_version=snapshot.adapter_version,
            expected_provider_identity=snapshot.provider,
            limits=compiled.limits,
            session_result=result,
            failure_code=exc.code,
            failure_summary=(
                "Frozen Task input or selected Skill material drifted during the isolated session; "
                "no model output was admitted."
            ),
            previous_main_state_ref=previous_main_state_ref,
            external_provider=snapshot.deployment != "local",
            extra_limitations=extra_limitations,
            fault_injector=fault_injector,
            contract_snapshots=contract_snapshots,
            frozen_input_payloads=frozen_input_payloads,
        )

    status = result.status.value
    output: Mapping[str, Any] | None = None
    failure_code: str | None = None
    failure_summary: str | None = None
    if result.status == ApiSessionStatus.COMPLETED:
        try:
            output = parse_api_task_output(
                result.final_response,
                task=task,
                protocol=protocol,
            )
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
    return closeout_api_attempt(
        root=project_root,
        protocol_ref=protocol_ref,
        task_ref=task_ref,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        attempt_id=attempt_id,
        started_at=started_at,
        finished_at=finished_at,
        terminal_status=status,
        next_action=next_actions[effective_status],
        provider_adapter_id=compiled.adapter_id,
        requested_model=compiled.request.model,
        provider_adapter_version=snapshot.adapter_version,
        expected_provider_identity=snapshot.provider,
        limits=compiled.limits,
        session_result=result,
        output=output,
        failure_code=failure_code,
        failure_summary=failure_summary,
        previous_main_state_ref=previous_main_state_ref,
        external_provider=snapshot.deployment != "local",
        extra_limitations=extra_limitations,
        fault_injector=fault_injector,
        contract_snapshots=contract_snapshots,
        frozen_input_payloads=frozen_input_payloads,
    )


def _effective_status(status: str, result: Any) -> str:
    if result.tool_failures:
        return "failed"
    if set(result.observed_models) - {result.requested_model}:
        return "failed"
    return status


def _execution_exception_code(exc: Exception) -> str:
    if isinstance(exc, ProviderError):
        return "PROVIDER-" + exc.category.value.upper().replace("-", "_")
    return "API-SESSION-EXCEPTION"
