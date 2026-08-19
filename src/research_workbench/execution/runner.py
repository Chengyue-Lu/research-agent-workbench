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
    _plain,
)

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

    def __init__(self, inner: ModelProvider) -> None:
        self._inner = inner
        self.records: list[dict[str, Any]] = []

    def capabilities(self) -> ProviderCapabilities:
        return self._inner.capabilities()

    def generate(self, request: ModelRequest) -> ModelResponse:
        response = self._inner.generate(request)
        self.records.append({"request": _plain(request), "response": _plain(response)})
        return response


def execute_plan(
    plan: ExecutionPlan,
    *,
    providers: ProviderRegistry,
    clock: Callable[[], float] = time.monotonic,
) -> ExecutionRunResult:
    file_tools = _AttemptFileTools(plan)
    client_tools = tuple(
        file_tools.client_tool(definition.name, definition) for definition in plan.request.tools
    )
    recording = RecordingProvider(providers.get(plan.provider))
    session_providers = ProviderRegistry()
    session_providers.register(plan.provider, recording)

    if plan.request.tools and plan.limits.max_tool_calls == 0:
        # The session kernel rejects this combination up front; the plan level
        # instead pauses before any model turn or tool side effect.
        session = _paused_without_tools(plan)
    else:
        runner = IsolatedApiSessionRunner(session_providers, tools=client_tools, clock=clock)
        session = runner.run(provider_name=plan.provider, request=plan.request, limits=plan.limits)

    stale_inputs = tuple(
        reference.path
        for reference in plan.input_lock
        if not check_file_reference(plan.root, reference).valid
    )
    return ExecutionRunResult(
        session=session,
        tool_events=tuple(file_tools.events),
        stale_inputs=stale_inputs,
        transcript=tuple(recording.records),
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
                        path=_requested_path(arguments),
                        detail=type(exc).__name__,
                    )
                )
                raise
            path, sha256 = _result_target(result)
            self.events.append(ToolEvent(name=name, ok=True, path=path, sha256=sha256))
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
