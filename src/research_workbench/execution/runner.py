"""Execute one compiled ExecutionPlan as a bounded isolated API session.

The runner wires three governed file tools (read_file, write_artifact,
list_outputs) into the K-API-1 IsolatedApiSessionRunner, records every tool
call as a ToolEvent, proxies the bound provider through a recording wrapper
so the closeout can persist a credential-free transcript, and re-checks the
input lock after the run. See docs/implementation/K_API_2_FILE_LOOP.md §3.
"""

from __future__ import annotations

import posixpath
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from research_workbench.adapters.models.port import (
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCategory,
    ProviderRegistry,
    ToolDefinition,
)
from research_workbench.adapters.models.session import (
    AggregateUsage,
    ApiSessionResult,
    ApiSessionStatus,
    ClientTool,
    IsolatedApiSessionRunner,
)
from research_workbench.artifacts.integrity import (
    check_file_reference,
    hash_file,
    resolve_within_root,
)
from research_workbench.execution.models import (
    ATTEMPT_DIRNAME_OUTPUTS,
    ExecutionPlan,
    ExecutionRunResult,
    ToolEvent,
    FrozenContractRef,
    _plain,
)
from research_workbench.io import load_document
from research_workbench.observability.trace import AgentTraceRecorder, derive_session_transcript

READ_FILE_TOOL = "read_file"
WRITE_ARTIFACT_TOOL = "write_artifact"
LIST_OUTPUTS_TOOL = "list_outputs"

TOOL_SIDE_EFFECTS = {
    READ_FILE_TOOL: "read-only",
    WRITE_ARTIFACT_TOOL: "local-write",
    LIST_OUTPUTS_TOOL: "read-only",
}


class RecordingProvider:
    """ModelProvider proxy that records (request, response) pairs for the transcript.

    The recorded request is the provider-neutral control-plane payload; it
    never carries credentials, so the transcript stays safe to persist.
    """

    def __init__(
        self,
        inner: ModelProvider,
        *,
        deadline: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._deadline = deadline
        self._clock = clock
        self.records: list[dict[str, Any]] = []

    def capabilities(self) -> ProviderCapabilities:
        return self._inner.capabilities()

    def generate(self, request: ModelRequest) -> ModelResponse:
        # Concrete HTTP adapters expose timeout_seconds. Tighten it before
        # every call so one provider request cannot overrun the remaining
        # session deadline. Scripted/custom providers remain provider-neutral.
        if self._deadline is not None and hasattr(self._inner, "timeout_seconds"):
            remaining = self._deadline - self._clock()
            if remaining <= 0:
                raise ProviderError(
                    ProviderErrorCategory.CANCELLED,
                    "execution deadline expired before provider call",
                )
            current_timeout = getattr(self._inner, "timeout_seconds")
            setattr(self._inner, "timeout_seconds", min(float(current_timeout), remaining))
        try:
            response = self._inner.generate(request)
        except ProviderError as exc:
            if self._deadline is not None and self._clock() >= self._deadline:
                raise ProviderError(
                    ProviderErrorCategory.CANCELLED,
                    "execution deadline reached during provider call",
                ) from exc
            raise
        self.records.append({"request": _plain(request), "response": _plain(response)})
        return response


def execute_plan(
    plan: ExecutionPlan,
    *,
    providers: ProviderRegistry,
    clock: Callable[[], float] = time.monotonic,
    cancel_requested: Callable[[], bool] | None = None,
) -> ExecutionRunResult:
    attempt_path = resolve_within_root(Path(plan.root).resolve(), plan.attempt_dir)
    if attempt_path is None:
        raise ValueError("attempt_dir escapes the project root")
    if attempt_path.is_dir() and any(attempt_path.iterdir()):
        raise ValueError(
            "attempt directory is not empty; verify or adjudicate the existing attempt "
            "and resume with a fresh attempt identity"
        )
    file_tools = _AttemptFileTools(plan)
    client_tools = tuple(
        file_tools.client_tool(definition.name, definition) for definition in plan.request.tools
    )
    recording = RecordingProvider(
        providers.get(plan.provider),
        deadline=clock() + plan.limits.max_seconds,
        clock=clock,
    )
    session_providers = ProviderRegistry()
    session_providers.register(plan.provider, recording)

    # This initialization is the pre-provider durability gate. Any failure
    # propagates before the runner can dispatch a network request.
    task_snapshot: Mapping[str, Any] = {
        "schema_version": "0.1.0",
        "task_id": plan.task_id,
        "revision": plan.task_revision,
        "snapshot_kind": "minimal-task-identity",
    }
    if plan.task_ref is not None:
        frozen_task_path = resolve_within_root(Path(plan.root).resolve(), plan.task_ref)
        if frozen_task_path is None or not frozen_task_path.is_file():
            raise ValueError("task_ref does not resolve within the project root")
        loaded_task = load_document(frozen_task_path)
        if not isinstance(loaded_task, Mapping):
            raise ValueError("task_ref must resolve to a mapping")
        task_snapshot = loaded_task
    recorder = AgentTraceRecorder(
        attempt_path,
        task_id=plan.task_id,
        task_revision=plan.task_revision,
        attempt_id=plan.attempt_id,
        task_snapshot=task_snapshot,
        accountable_owner=plan.accountable_owner,
        actor_id=plan.actor_id,
        runtime_identity=f"{plan.model_binding.provider_adapter}:{plan.request.model}",
        provider=plan.provider,
        read_allowlist=plan.readable_inputs,
        write_scope=plan.write_scope,
        tool_allowlist=tuple(tool.name for tool in plan.request.tools),
    )

    if plan.request.tools and plan.limits.max_tool_calls == 0:
        # The session kernel rejects this combination up front; the plan level
        # instead pauses before any model turn or tool side effect.
        session = _paused_without_tools(plan)
        recorder.record(
            "session-status",
            {"status": session.status.value, "reason": session.stop_reason},
        )
    else:
        runner = IsolatedApiSessionRunner(session_providers, tools=client_tools, clock=clock)
        session = runner.run(
            provider_name=plan.provider,
            request=plan.request,
            limits=plan.limits,
            cancel_requested=cancel_requested,
            event_sink=recorder,
        )

    trace_local_ref = recorder.seal(session.status.value)

    stale_inputs = tuple(
        reference.path
        for reference in plan.input_lock
        if not check_file_reference(plan.root, reference).valid
    )
    return ExecutionRunResult(
        session=session,
        tool_events=tuple(file_tools.events),
        stale_inputs=stale_inputs,
        transcript=derive_session_transcript(attempt_path),
        trace_ref=FrozenContractRef(
            path=f"{plan.attempt_dir}/{trace_local_ref['path']}",
            sha256=str(trace_local_ref["sha256"]),
        ),
        trace_redactions=recorder.redaction_count,
    )


def _paused_without_tools(plan: ExecutionPlan) -> ApiSessionResult:
    return ApiSessionResult(
        status=ApiSessionStatus.SAFE_PAUSED,
        stop_reason="tool-call-budget",
        provider=plan.provider,
        requested_model=plan.request.model,
        observed_models=(),
        model_turns=0,
        tool_calls=0,
        usage=AggregateUsage(
            input_tokens=None,
            output_tokens=None,
            cached_input_tokens=None,
            reasoning_tokens=None,
            provider_reported_cost=None,
            currency=None,
        ),
        final_response=None,
        warnings=("tool-call budget is zero; paused before the first model turn",),
    )


class _AttemptFileTools:
    """Governed file access for one attempt: locked inputs plus its outputs dir."""

    def __init__(self, plan: ExecutionPlan) -> None:
        self.events: list[ToolEvent] = []
        self._root = Path(plan.root).resolve()
        attempt_dir = resolve_within_root(self._root, plan.attempt_dir)
        if attempt_dir is None:
            raise ValueError("attempt_dir escapes the project root")
        self._outputs_dir = attempt_dir / ATTEMPT_DIRNAME_OUTPUTS
        self._readable_inputs = frozenset(
            _normalize_path(path) for path in plan.readable_inputs
        )

    def client_tool(self, name: str, definition: ToolDefinition) -> ClientTool:
        handlers = {
            READ_FILE_TOOL: self._read_file,
            WRITE_ARTIFACT_TOOL: self._write_artifact,
            LIST_OUTPUTS_TOOL: self._list_outputs,
        }
        if name not in handlers:
            raise ValueError(f"unknown execution client tool: {name}")
        return ClientTool(definition, self._record(name, handlers[name]), TOOL_SIDE_EFFECTS[name])

    def _record(
        self,
        name: str,
        handler: Callable[[Mapping[str, Any]], object],
    ) -> Callable[[Mapping[str, Any]], object]:
        def execute(arguments: Mapping[str, Any]) -> object:
            try:
                result = handler(arguments)
            except Exception as exc:
                # Tool failures record only their exception type, never the message.
                self.events.append(
                    ToolEvent(
                        name=name,
                        ok=False,
                        side_effect=TOOL_SIDE_EFFECTS[name],
                        path=_requested_path(arguments),
                        detail=type(exc).__name__,
                    )
                )
                raise
            path, sha256 = _result_target(result)
            self.events.append(
                ToolEvent(
                    name=name,
                    ok=True,
                    side_effect=TOOL_SIDE_EFFECTS[name],
                    path=path,
                    sha256=sha256,
                )
            )
            return result

        return execute

    def _read_file(self, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        raw = arguments.get("path")
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("read_file requires a non-empty path")
        path = _normalize_path(raw)
        target = resolve_within_root(self._root, path)
        if target is None or not (
            path in self._readable_inputs or _is_within(target, self._outputs_dir)
        ):
            raise PermissionError("read_file path is outside the execution read scope")
        if not target.is_file():
            raise FileNotFoundError(path)
        return {
            "path": path,
            "sha256": hash_file(target),
            "content": target.read_text(encoding="utf-8"),
        }

    def _write_artifact(self, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        name = arguments.get("name")
        content = arguments.get("content")
        if not isinstance(name, str) or not _is_bare_filename(name):
            raise ValueError("write_artifact name must be a bare file name")
        if not isinstance(content, str):
            raise TypeError("write_artifact content must be a string")
        self._outputs_dir.mkdir(parents=True, exist_ok=True)
        target = self._outputs_dir / name
        with target.open("x", encoding="utf-8") as stream:
            stream.write(content)
        return {
            "path": target.relative_to(self._root).as_posix(),
            "sha256": hash_file(target),
        }

    def _list_outputs(self, arguments: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        if not self._outputs_dir.is_dir():
            return []
        return [
            {"name": item.name, "sha256": hash_file(item)}
            for item in sorted(self._outputs_dir.iterdir(), key=lambda entry: entry.name)
            if item.is_file()
        ]


def _normalize_path(path: str) -> str:
    return posixpath.normpath(path.replace("\\", "/"))


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _is_bare_filename(name: str) -> bool:
    return (
        bool(name.strip())
        and name not in {".", ".."}
        and all(character not in name for character in "/\\:")
    )


def _requested_path(arguments: Mapping[str, Any]) -> str | None:
    for key in ("path", "name"):
        value = arguments.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _result_target(result: object) -> tuple[str | None, str | None]:
    if isinstance(result, Mapping):
        path = result.get("path")
        sha256 = result.get("sha256")
        return (
            path if isinstance(path, str) else None,
            sha256 if isinstance(sha256, str) else None,
        )
    return None, None
