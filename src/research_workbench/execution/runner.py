"""One-shot orchestration: compile, run, and close out a Task over the API.

``execute_task`` is the K-API-2 seam. It never talks to a real provider by
itself: provider construction is delegated to ``build_provider_registry``,
which stays unimplemented until the live-conformance workstream (M6-004)
wires real adapters. Offline callers inject a registry explicitly.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_workbench.adapters.models import (
    AggregateUsage,
    ApiSessionStatus,
    IsolatedApiSessionRunner,
    ProviderError,
    ProviderRegistry,
)
from research_workbench.adapters.models.configuration import get_provider_adapter_config
from research_workbench.adapters.models.conformance import build_live_provider
from research_workbench.adapters.models.pool import ModelBinding, ModelPool
from research_workbench.artifacts.integrity import hash_file
from research_workbench.capability.models import AgentProfile
from research_workbench.capability.resolver import ResolvedTask
from research_workbench.context.models import MainStatePacket
from research_workbench.execution.artifacts import (
    SessionOutcome,
    build_closeout_documents,
    outcome_from_result,
)
from research_workbench.execution.closeout import (
    PUBLISH_ORDER,
    CloseoutError,
    CloseoutResult,
    read_completion_marker,
    run_closeout,
)
from research_workbench.execution.compiler import CompiledSession, compile_session
from research_workbench.execution.errors import CompileError
from research_workbench.execution.options import ExecutionPolicy
from research_workbench.io import load_document
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import TaskPacket


@dataclass(frozen=True, slots=True)
class ExecutionRun:
    compiled: CompiledSession
    main_state_path: str | None
    outcome: SessionOutcome | None = None
    closeout: CloseoutResult | None = None
    dry_run: bool = False


def build_provider_registry(
    provider_adapter: str,
    *,
    config_path: Path | None = None,
    model: str | None = None,
) -> ProviderRegistry:
    """Build the live registry for one adapter, or block without a config.

    The pool binding stays the single model authority: ``model`` is passed
    through to the provider so no second environment read can diverge. The
    credential is never resolved here; it stays deferred to the outbound
    request boundary.
    """

    if config_path is None:
        raise CompileError(
            "EXEC-PROVIDER-NOT-CONFIGURED",
            f"no live provider is configured for adapter {provider_adapter!r}; "
            "pass a local provider-adapter config (never the committed disabled "
            "template) or inject a provider registry explicitly",
        )
    try:
        config = get_provider_adapter_config(config_path, provider_adapter)
    except KeyError as exc:
        raise CompileError(
            "EXEC-ADAPTER-UNKNOWN", str(exc)
        ) from exc
    try:
        provider = build_live_provider(config, model=model)
    except ValueError as exc:
        message = str(exc)
        if "disabled" in message:
            raise CompileError(
                "EXEC-ADAPTER-DISABLED",
                f"adapter {provider_adapter!r} is disabled in {config_path}; "
                "enable it in a local copy, not the committed template",
            ) from exc
        raise CompileError("EXEC-PROVIDER-INVALID", message) from exc
    registry = ProviderRegistry()
    registry.register(provider_adapter, provider)
    return registry


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def execute_task(
    *,
    root: Path,
    task_path: str,
    profile_path: str,
    assignment_path: str,
    slot: str,
    pool_path: str,
    environment: Mapping[str, str],
    protocol_path: str,
    policy: ExecutionPolicy = ExecutionPolicy(),
    provider_registry: ProviderRegistry | None = None,
    provider_config_path: str | None = None,
    base_state_path: str | None = None,
    now: Callable[[], str] = utc_now,
    dry_run: bool = False,
) -> ExecutionRun:
    """Compile, execute, and close out one Task attempt."""

    project_root = Path(root).resolve()
    task = TaskPacket.from_mapping(_load(project_root, task_path))
    profile = AgentProfile.from_mapping(_load(project_root, profile_path))
    assignment = ResolvedTask.from_mapping(_load(project_root, assignment_path))
    protocol = ProjectProtocol.from_mapping(_load(project_root, protocol_path))
    binding = _bind_slot(project_root, pool_path, slot, environment)
    compiled = compile_session(task, profile, assignment, binding, root=project_root, policy=policy)

    if dry_run:
        return ExecutionRun(compiled=compiled, main_state_path=None, dry_run=True)

    batch_root = project_root / "work" / task.task_id / compiled.attempt_id
    marker = batch_root / "closeout-complete.txt"
    claim = batch_root / "closeout-claim.txt"

    resumed = _already_published(project_root, batch_root, marker, claim)
    if resumed is not None:
        return ExecutionRun(
            compiled=compiled,
            outcome=None,
            closeout=resumed,
            main_state_path=_main_state_path(compiled.attempt_id),
        )
    registry = provider_registry or build_provider_registry(
        binding.provider_adapter,
        config_path=project_root / provider_config_path if provider_config_path else None,
        model=binding.model,
    )
    # Preflight the registry against the compiled request: model, capability,
    # and data-policy gaps block here with zero writes to the batch.
    registry.require(binding.provider_adapter, compiled.request)

    _preflight_batch(batch_root, marker, claim)
    _claim_batch(claim, now())

    started_at = now()
    outcome, finished_at = _run_session(registry, binding, compiled, now, started_at)
    base_state = (
        MainStatePacket.from_mapping(_load(project_root, base_state_path))
        if base_state_path
        else None
    )
    plan = build_closeout_documents(
        task,
        assignment,
        binding,
        compiled,
        outcome,
        root=project_root,
        protocol=protocol,
        protocol_path=protocol_path,
        profile_path=profile_path,
        task_path=task_path,
        started_at=started_at,
        finished_at=finished_at,
        base_state=base_state,
    )
    closeout = run_closeout(plan, root=project_root, protocol=protocol, task=task, assignment=assignment)
    # The claim only disappears on full success: an interrupted run leaves
    # it behind so the pre-flight check blocks the batch for a manual decision.
    claim.unlink(missing_ok=True)
    return ExecutionRun(
        compiled=compiled,
        outcome=outcome,
        closeout=closeout,
        main_state_path=plan.main_state_path,
    )


def _load(project_root: Path, relative: str) -> Mapping[str, Any]:
    document = load_document(project_root / relative)
    if not isinstance(document, Mapping):
        raise CompileError("EXEC-INPUT-INVALID", f"document is not an object: {relative}")
    return document


def _bind_slot(
    project_root: Path, pool_path: str, slot: str, environment: Mapping[str, str]
) -> ModelBinding:
    pool_document = _load(project_root, pool_path)
    pool = ModelPool.from_mapping(pool_document)
    try:
        return pool.bind(slot, environment=environment)
    except KeyError as exc:
        raise CompileError("EXEC-SLOT-UNKNOWN", str(exc)) from exc
    except ValueError as exc:
        raise CompileError("EXEC-SLOT-INVALID", str(exc)) from exc


def _already_published(
    project_root: Path, batch_root: Path, marker: Path, claim: Path
) -> CloseoutResult | None:
    """Skip the model entirely when this deterministic attempt already closed."""

    if not marker.is_file():
        return None
    entries = read_completion_marker(marker)
    if not entries:
        raise CloseoutError(
            "EXEC-CLOSEOUT-INCOMPLETE",
            "completion marker is malformed; inspect the batch manually",
        )
    published: list[tuple[str, str, str]] = []
    for _, relative, digest in entries:
        target = project_root / relative
        if not target.is_file():
            raise CloseoutError(
                "EXEC-CLOSEOUT-INCOMPLETE",
                f"marked batch lost a file: {relative}; inspect the batch manually",
            )
        if hash_file(target) != digest:
            raise CloseoutError(
                "EXEC-CLOSEOUT-PATH-CONFLICT",
                f"published batch diverges at {relative}",
            )
        published.append((_role_for(relative), relative, digest))
    claim.unlink(missing_ok=True)
    return CloseoutResult(
        published=tuple(published),
        marker_path=marker.relative_to(project_root).as_posix(),
        resumed=True,
    )


def _role_for(relative: str) -> str:
    for role in PUBLISH_ORDER:
        if role in relative:
            return role
    return "unknown"


def _preflight_batch(batch_root: Path, marker: Path, claim: Path) -> None:
    """Block execution when an interrupted run already touched this batch."""

    if marker.exists() or not batch_root.exists():
        return
    if claim.exists():
        raise CloseoutError(
            "EXEC-BATCH-CLAIMED",
            "an interrupted execution left a claim on this batch ("
            + claim.read_text(encoding="utf-8").strip()
            + "); inspect and remove it manually before re-executing",
        )
    leftovers = sorted(entry.name for entry in batch_root.iterdir())
    if leftovers:
        raise CloseoutError(
            "EXEC-CLOSEOUT-INCOMPLETE",
            "batch directory exists without a completion marker; a previous run was "
            "interrupted before verification. Inspect "
            f"{batch_root.as_posix()} and complete or remove it manually before "
            "re-executing (the model is never re-run automatically).",
        )


def _claim_batch(claim: Path, claimed_at: str) -> None:
    """Take an exclusive claim so a concurrent execution cannot duplicate work."""

    claim.parent.mkdir(parents=True, exist_ok=True)
    try:
        with claim.open("x", encoding="utf-8") as stream:
            stream.write(f"claimed_at={claimed_at}\n")
    except FileExistsError as exc:
        raise CloseoutError(
            "EXEC-BATCH-CLAIMED",
            "another execution already holds the claim on this batch; "
            "do not run the same attempt concurrently",
        ) from exc


def _run_session(
    registry: ProviderRegistry,
    binding: ModelBinding,
    compiled: CompiledSession,
    now: Callable[[], str],
    started_at: str,
) -> tuple[SessionOutcome, str]:
    runner = IsolatedApiSessionRunner(registry, tools=compiled.tools)
    try:
        result = runner.run(
            provider_name=binding.provider_adapter,
            request=compiled.request,
            limits=compiled.limits,
        )
    except ProviderError as exc:
        failure = {"kind": type(exc).__name__, "category": str(exc.category)}
        outcome = SessionOutcome(
            status=str(ApiSessionStatus.FAILED.value),
            stop_reason=str(exc.category),
            provider=binding.provider_adapter,
            requested_model=binding.model,
            observed_models=(),
            model_turns=0,
            tool_calls=0,
            usage=AggregateUsage(None, None, None, None, None, None),
            warnings=(),
            structured_output=None,
            failure=failure,
        )
        return outcome, now()
    structured = _structured_payload(result.status, result.final_response)
    outcome = replace(
        outcome_from_result(result, structured_output=structured),
        tool_failures=tuple(
            {"name": record.name, "error": record.error or "unknown"}
            for record in compiled.tool_log.records
            if not record.ok
        ),
    )
    return outcome, now()


def _structured_payload(
    status: ApiSessionStatus, final_response: Any
) -> Mapping[str, Any] | None:
    if status != ApiSessionStatus.COMPLETED or final_response is None:
        return None
    text = "".join(
        block.text or "" for block in final_response.output if block.kind == "text"
    )
    try:
        parsed = json.loads(text)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _main_state_path(attempt_id: str) -> str:
    return f"checkpoints/MS-{attempt_id.removeprefix('A-')}.yaml"


__all__ = [
    "ExecutionRun",
    "build_provider_registry",
    "execute_task",
    "utc_now",
]
