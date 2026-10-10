"""Optional no-Skill Role -> isolated Session -> frozen Host archive bridge.

Observers are caller-owned observations of configured implementation/source
bindings, never a copy of the selected View. This module grants no live API
qualification, Task completion, Skill admission, or recovery authority.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from research_workbench.adapters.models import (
    ApiSessionLimits, ApiSessionResult, ApiSessionStatus, ClientTool,
    IsolatedApiSessionRunner, ModelProvider, ModelRequest, ProviderRegistry,
)
from research_workbench.artifacts.integrity import hash_bytes, resolve_within_root
from research_workbench.entry.materials import MaterialInputError, read_material_inputs
from research_workbench.execution.generic_closeout import (
    CloseoutPin, GenericCloseoutValidationError, build_generic_execution_receipt,
    validate_generic_execution_receipt,
)
from research_workbench.execution.host import (
    ExecutionDriverResult, FrozenExecutionRequest, HostClock, SystemHostClock,
    ValidatedExecutionView, execute_frozen_view, load_resolved_execution_view,
)
from research_workbench.execution.runtime_bundle import load_runtime_bundle
from research_workbench.io import load_document_bytes
from research_workbench.observability.trace import AgentTraceRecorder, validate_attempt_trace
from research_workbench.validation.schemas import SchemaCatalog


class EntryDriverError(ValueError):
    """A caller configuration or exact-input boundary could not be satisfied."""


class _MaterialCheckedProvider:
    """Recheck after all Runner callbacks, before entering the actual Provider."""
    def __init__(self, driver):
        self.driver = driver

    def capabilities(self):
        return self.driver.provider.capabilities()

    def generate(self, request):
        self.driver._read_inputs()
        self.driver._provider_invocations += 1
        return self.driver.provider.generate(request)


@dataclass(frozen=True, slots=True)
class ObservedExecutionBinding:
    binding: Mapping[str, Any]
    supply_report_ref: str


@dataclass(frozen=True, slots=True)
class RoleSliceResult:
    host_report: Mapping[str, Any]
    host_report_ref: CloseoutPin
    trace_ref: CloseoutPin
    validation_ref: CloseoutPin | None
    receipt_ref: CloseoutPin | None
    session: ApiSessionResult | None
    closeout_error: str | None


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _pin(root: Path, path: Path) -> CloseoutPin:
    return CloseoutPin(path.relative_to(root).as_posix(), hash_bytes(path.read_bytes()))


def _read_pin(root: Path, pin: CloseoutPin) -> tuple[Path, bytes]:
    path = resolve_within_root(root, pin.path)
    if path is None or not path.is_file():
        raise EntryDriverError("input must be an existing project-relative file")
    content = path.read_bytes()
    if hash_bytes(content) != pin.sha256.lower().removeprefix("sha256:"):
        raise EntryDriverError("input hash drift: " + pin.path)
    return path, content


def _scope_path(root: Path, relative: str, view: Mapping[str, Any]) -> Path:
    path = resolve_within_root(root, relative)
    permissions = view["effective_constraints"]["permissions"]
    if permissions["filesystem"] in {"forbidden", "read-only"} or path is None:
        raise EntryDriverError("execution output requires an authorized write scope")
    allowed = [resolve_within_root(root, item) for item in permissions["allowed_roots"]]
    if not any(item is not None and (item == path or item in path.parents) for item in allowed):
        raise EntryDriverError("execution output escapes effective write scope")
    return path


def _persist(root: Path, path: Path, document: Any) -> CloseoutPin:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(_plain(document), stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return _pin(root, path)


def _task(view: ValidatedExecutionView) -> Mapping[str, Any]:
    path = resolve_within_root(view.project_root, view.document["task_ref"]["path"])
    return view.runtime_bundle.documents[path]


def _observe(provider: ModelProvider, observer: Callable[[ModelProvider], Any]) -> ObservedExecutionBinding:
    value = observer(provider)
    if isinstance(value, ObservedExecutionBinding):
        observed = value
    elif isinstance(value, Mapping) and "selected_supply_report_ref" in value:
        observed = ObservedExecutionBinding(
            {key: value[key] for key in ("provider", "adapter", "model", "runtime", "host")},
            str(value["selected_supply_report_ref"]),
        )
    else:
        raise EntryDriverError("actual Binding and Supply observation are both required")
    binding = _plain(observed.binding)
    if set(binding) != {"provider", "adapter", "model", "runtime", "host"} or not observed.supply_report_ref:
        raise EntryDriverError("observer must provide exact five-component Binding and Supply")
    if provider.capabilities().provider != binding["provider"]["ref"]:
        raise EntryDriverError("Provider capability identity disagrees with actual observer")
    return ObservedExecutionBinding(binding, observed.supply_report_ref)


def _default_request_builder(*args: Any, **kwargs: Any) -> ModelRequest:
    from research_workbench.entry.roles import build_role_request
    return build_role_request(*args, **kwargs)


def _tool_signature(definitions: Sequence[Any]) -> str:
    return json.dumps([{"name": item.name, "description": item.description,
                        "input_schema": _plain(item.input_schema), "strict": item.strict}
                       for item in definitions], sort_keys=True, allow_nan=False)


class SessionExecutionDriver:
    """One prebound no-Skill Session, with optional explicit readonly Tools."""

    def __init__(
        self, root: str | Path, *, view: ValidatedExecutionView, role: str,
        provider: ModelProvider, binding_observer: Callable[[ModelProvider], Any],
        recorder: AgentTraceRecorder, output_path: str, output_contract: str,
        input_refs: Sequence[Mapping[str, str]] = (), limits: ApiSessionLimits | None = None,
        session_clock: Callable[[], float] = time.monotonic,
        deadline_monotonic: float | None = None,
        cancel_requested: Callable[[], bool] | None = None,
        request_builder: Callable[..., ModelRequest] | None = None,
        request_payloads: Sequence[str] = ("project-context",),
        observation: ObservedExecutionBinding | None = None,
        tools: Sequence[ClientTool] = (), tool_refs: Mapping[str, str] | None = None,
    ) -> None:
        prepared_at = session_clock()
        if (isinstance(prepared_at, bool) or not isinstance(prepared_at, (int, float))
                or not math.isfinite(prepared_at)):
            raise EntryDriverError("Session clock must be finite")
        if deadline_monotonic is not None and (
                isinstance(deadline_monotonic, bool) or not isinstance(deadline_monotonic, (int, float))
                or not math.isfinite(deadline_monotonic)):
            raise EntryDriverError("absolute Session deadline must be finite")
        self.root = Path(root).resolve()
        if self.root != view.project_root:
            raise EntryDriverError("Driver and View roots differ")
        self.view, self.role, self.provider = view, role, provider
        self.observer, self.recorder = binding_observer, recorder
        self._declared = observation or _observe(provider, binding_observer)
        self._actual = self._declared
        self.output_path = _scope_path(self.root, output_path, view.document)
        self.output_contract = output_contract
        if not output_contract:
            raise EntryDriverError("an explicit output contract is required")
        self.input_refs = tuple(dict(item) for item in input_refs) or tuple(
            _plain(item) for item in _task(view).get("input_refs", ()))
        declared = {_plain(item)["path"]: _plain(item) for item in _task(view).get("input_refs", ()) if isinstance(item, Mapping)}
        for item in self.input_refs:
            if item != declared.get(item.get("path")):
                raise EntryDriverError("Role input is not an exact declared Task input")
        self._read_inputs()
        self._provider_invocations = 0
        self.clock, self.cancel = session_clock, cancel_requested
        self.builder = request_builder or _default_request_builder
        budget = view.document["effective_constraints"]["budget"]
        self.limits = replace(limits, allowed_tool_side_effects=frozenset(limits.allowed_tool_side_effects)) if limits else ApiSessionLimits(
            max_model_turns=1, max_tool_calls=0, max_parallel_tool_calls=0,
            max_tool_result_chars=1, max_output_tokens_per_turn=int(budget.get("max_output_tokens", 1024)),
            max_seconds=float(budget.get("max_seconds", 60)),
        )
        for name in ("max_model_turns", "max_tool_calls", "max_parallel_tool_calls",
                     "max_tool_result_chars", "max_output_tokens_per_turn"):
            if type(getattr(self.limits, name)) is not int:
                raise EntryDriverError("Session count/token limits must be integers")
        if (isinstance(self.limits.max_seconds, bool)
                or not isinstance(self.limits.max_seconds, (int, float))
                or not math.isfinite(self.limits.max_seconds)):
            raise EntryDriverError("Session deadline must be finite")
        if self.limits.max_total_tokens is not None and type(self.limits.max_total_tokens) is not int:
            raise EntryDriverError("Session total token limit must be an integer")
        if (self.limits.max_model_turns > budget.get("max_turns", self.limits.max_model_turns)
                or self.limits.max_model_turns * self.limits.max_output_tokens_per_turn
                > budget.get("max_output_tokens", self.limits.max_model_turns * self.limits.max_output_tokens_per_turn)
                or self.limits.max_seconds > budget.get("max_seconds", self.limits.max_seconds)):
            raise EntryDriverError("Session limits exceed frozen Host budget")
        self.remote = provider.capabilities().deployment != "local"
        self.payloads = tuple(sorted(set(request_payloads))) if self.remote else ()
        permissions = view.document["effective_constraints"]["permissions"]
        egress = view.document["effective_constraints"]["data_egress"]
        if self.remote and (permissions["network"] in {"none", "forbidden"} or egress["policy"] == "forbidden"):
            raise EntryDriverError("remote Provider forbidden by frozen network/data policy")
        if self.remote and not self.payloads:
            raise EntryDriverError("remote request requires explicit payload classification")
        if (egress["policy"] == "allowlisted-only" and not set(self.payloads).issubset(egress["allowed_payloads"])) or set(self.payloads).intersection(egress["forbidden_payloads"]):
            raise EntryDriverError("request payload classification exceeds frozen egress policy")
        supply_path = resolve_within_root(self.root, view.document["selected_supply_report_ref"]["path"])
        supply = view.runtime_bundle.documents[supply_path]
        if supply["supply_identity"]["supply_kind"] not in {"procedure", "tool"} or view.runtime_bundle.manifest["skill_extension"]["enabled"]:
            raise EntryDriverError("only procedure/direct Tool no-Skill Supply is supported by this Driver")
        self.tools = tuple(ClientTool(replace(item.definition, input_schema=_plain(item.definition.input_schema)),
                                      item.execute, item.side_effect) for item in tools)
        self.tool_refs = dict(tool_refs or {})
        names = {item.definition.name for item in self.tools}
        if len(names) != len(self.tools) or set(self.tool_refs) != names:
            raise EntryDriverError("each unique ClientTool requires exactly one explicit Supply component ref")
        if self.tools and (limits is None or self.limits.max_tool_calls < 1
                           or self.limits.max_parallel_tool_calls < 1):
            raise EntryDriverError("Tools require explicit positive call and batch limits")
        if not self.tools and (self.limits.max_tool_calls or self.limits.max_parallel_tool_calls):
            raise EntryDriverError("Tool budgets require declared ClientTools")
        if (self.limits.allowed_tool_side_effects - {"read-only"}
                or any(item.side_effect != "read-only" for item in self.tools)):
            raise EntryDriverError("this Driver supports readonly Tool handlers only")
        selected_refs = {item["component_ref"] for item in supply["supply_identity"].get("components", ())
                         if item["component_kind"] == "tool"}
        if not set(self.tool_refs.values()).issubset(selected_refs):
            raise EntryDriverError("Tool identity is outside the selected Supply components")
        if self.tools:
            profile_pin = view.document["agent_profile_ref"]
            profile_path, profile_bytes = _read_pin(self.root, CloseoutPin(profile_pin["path"], profile_pin["sha256"]))
            self.recorder.record_content_read(profile_pin["path"], access="content",
                allowlist_basis="frozen View Profile Tool ceiling", content_sha256=hash_bytes(profile_bytes))
            profile = load_document_bytes(profile_path, profile_bytes)
            if (not names.issubset(set(_task(view).get("required_capabilities", ())))
                    or not names.issubset(set(profile.get("allowed_tool_capabilities", ())))
                    or not names.issubset(set(supply.get("provided_capabilities", ())))):
                raise EntryDriverError("Tool names must be explicitly allowed by Task, Profile and selected Supply")
        if supply["supply_identity"]["supply_kind"] == "tool" and not self.tools:
            raise EntryDriverError("direct Tool Supply requires explicit ClientTools")
        self.tool_definitions = tuple(item.definition for item in self.tools)
        self.tool_signature = _tool_signature(self.tool_definitions)
        self.session: ApiSessionResult | None = None
        self.requests = 0
        self.responses: list[Any] = []
        self.gaps: list[str] = []
        self.failure: str | None = None
        self.tool_invocations = 0
        self.used_tool_refs: set[str] = set()
        self.tool_call_ids: set[str] = set()
        self.started = prepared_at
        self.deadline = min(prepared_at + self.limits.max_seconds, deadline_monotonic) if deadline_monotonic is not None else prepared_at + self.limits.max_seconds
        self._executed = False
        self._runner: IsolatedApiSessionRunner | None = None

    @property
    def binding(self) -> Mapping[str, Any]:
        return _plain(self._declared.binding)

    @property
    def selected_supply_report_ref(self) -> str:
        return self._declared.supply_report_ref

    def _check_use(self) -> None:
        self._actual = _observe(self.provider, self.observer)
        if self._actual != self._declared:
            self.failure = "ENTRY-ACTUAL-BINDING-DRIFT"
            raise EntryDriverError("actual implementation Binding/Supply changed before use")
        if self.cancel and self.cancel():
            self.failure = "ENTRY-CANCELLED"
            raise EntryDriverError("execution cancellation requested before use")
        if _tool_signature(self.tool_definitions) != self.tool_signature:
            self.failure = "ENTRY-TOOL-DEFINITION-DRIFT"
            raise EntryDriverError("declared Tool definitions changed before use")
        profile = self.view.document["agent_profile_ref"]
        _read_pin(self.root, CloseoutPin(profile["path"], profile["sha256"]))
        self._read_inputs()

    def _read_inputs(self) -> tuple[dict[str, Any], ...]:
        try:
            return read_material_inputs(self.root, self.input_refs)
        except MaterialInputError as exc:
            self.failure = exc.code
            raise EntryDriverError(str(exc)) from exc

    def record(self, kind: str, payload: Mapping[str, Any]) -> None:
        self._sync_dispatch_facts()
        if kind == "provider-request":
            self._check_use()
            current = payload["request"]
            if (self.requests >= self.limits.max_model_turns
                    or current.model != self._declared.binding["model"]["ref"]
                    or _tool_signature(current.tools) != self.tool_signature):
                self.failure = "ENTRY-REQUEST-BOUNDARY"
                raise EntryDriverError("request exceeds frozen model/Tool/call boundary")
            self.recorder.record(kind, payload)
        elif kind == "provider-response":
            self.recorder.record(kind, payload)
            response = payload["response"]
            self.responses.append(response)
            self._actual = _observe(self.provider, self.observer)
            if (self._actual != self._declared or response.provider != self._actual.binding["provider"]["ref"]
                    or response.model != self._actual.binding["model"]["ref"]):
                self.failure = "ENTRY-RESPONSE-BINDING-DRIFT"
                self.gaps.append("response-binding-disagrees-with-configured-observation")
                self.recorder.record_capture_gap("events", self.gaps[-1])
                raise EntryDriverError("response/configured Binding drift")
        elif kind in {"tool-attempted", "tool-result"}:
            name, call_id = payload["name"], payload["call_id"]
            if name not in self.tool_refs:
                raise EntryDriverError("undeclared Tool event")
            if kind == "tool-attempted":
                self._check_use()
                if self.tool_invocations >= self.limits.max_tool_calls or call_id in self.tool_call_ids:
                    raise EntryDriverError("Tool count exhausted or call identity reused")
            elif call_id not in self.tool_call_ids:
                raise EntryDriverError("Tool result has no retained invocation")
            # Trace/Host/Receipt use frozen component identity; Session keeps the
            # request's client name for result assembly and handler lookup.
            self.recorder.record(kind, {**payload, "name": self.tool_refs[name]})
            if kind == "tool-result" and payload.get("status") == "failed":
                self.failure = self.failure or "ENTRY-TOOL-FAILED"
        else:
            if kind == "capture-gap":
                self.gaps.append(str(payload.get("reason", "capture-gap")))
            self.recorder.record(kind, payload)

    def _dispatch(self, kind: str, payload: Mapping[str, Any]) -> bool:
        """Further restrict admission; only the Runner counts real invocations."""
        now = self.clock()
        if (isinstance(now, bool) or not isinstance(now, (int, float))
                or not math.isfinite(now) or now < self.started or now >= self.deadline):
            self.failure = "ENTRY-TIME-BUDGET"
            return False
        if self.cancel and self.cancel():
            self.failure = "ENTRY-CANCELLED"
            return False
        # Cancellation observation is caller code and can itself be slow.
        now = self.clock()
        if (isinstance(now, bool) or not isinstance(now, (int, float))
                or not math.isfinite(now) or now < self.started or now >= self.deadline):
            self.failure = "ENTRY-TIME-BUDGET"
            return False
        # Caller callbacks and durable capture precede this final read check.
        self._read_inputs()
        return True

    def _sync_dispatch_facts(self) -> None:
        if self._runner is None:
            return
        facts = self._runner.dispatch_facts
        # A rejected guard facade is not an invocation of the actual Provider.
        self.requests = self._provider_invocations
        self.tool_invocations = facts["tool_invocations"]
        self.tool_call_ids = {call_id for call_id, _ in facts["tool_calls"]}
        self.used_tool_refs = {self.tool_refs[name] for _, name in facts["tool_calls"]}

    def execute(self, request: FrozenExecutionRequest) -> ExecutionDriverResult:
        if self._executed:
            raise EntryDriverError("a Driver cannot reuse an execution slice")
        self._executed = True
        if request.view != self.view.document or request.bundle_documents != self.view.runtime_bundle.documents:
            raise EntryDriverError("Driver received a substituted frozen request")
        profile_pin = self.view.document["agent_profile_ref"]
        profile_path, profile_bytes = _read_pin(self.root, CloseoutPin(profile_pin["path"], profile_pin["sha256"]))
        profile = load_document_bytes(profile_path, profile_bytes)
        task = _plain(_task(self.view))
        self.recorder.record_content_read(profile_pin["path"], access="content", allowlist_basis="frozen View Profile", content_sha256=hash_bytes(profile_bytes))
        for item in self._read_inputs():
            self.recorder.record_content_read(item["path"], access="content", allowlist_basis="exact Task input", content_sha256=item["sha256"])
        model_request = self.builder(self.root, role=self.role, task=task, profile=profile,
            model=str(self._declared.binding["model"]["ref"]), input_refs=self.input_refs,
            tools=self.tool_definitions, max_output_tokens=self.limits.max_output_tokens_per_turn)
        if (not isinstance(model_request, ModelRequest)
                or _tool_signature(model_request.tools) != self.tool_signature
                or model_request.model != self._declared.binding["model"]["ref"]):
            raise EntryDriverError("Role builder must return the frozen model and exact declared Tools")
        model_request = replace(model_request, data_policy=replace(
            model_request.data_policy, local_only=model_request.data_policy.local_only or not self.remote,
            allow_provider_server_tools=False))
        registry = ProviderRegistry()
        registry.register(str(self._declared.binding["provider"]["ref"]), _MaterialCheckedProvider(self))
        runner = IsolatedApiSessionRunner(registry, tools=self.tools, clock=self.clock)
        self._runner = runner
        started = self.started
        try:
            self.session = runner.run(provider_name=str(self._declared.binding["provider"]["ref"]),
                request=model_request, limits=self.limits, event_sink=self,
                deadline_monotonic=self.deadline, dispatch_guard=self._dispatch,
                cancel_requested=lambda: bool(self.failure) or bool(self.cancel and self.cancel()))
        except Exception as exc:
            self.failure = self.failure or "ENTRY-SESSION-EXCEPTION"
            if not isinstance(exc, EntryDriverError):
                self.gaps.append("session-exception:" + type(exc).__name__)
                self.recorder.record_capture_gap("events", self.gaps[-1])
        finally:
            self._sync_dispatch_facts()
        if self.requests and (not self.responses or any(response.usage.output_tokens is None for response in self.responses)):
            self.gaps.append("output-token-usage-unavailable")
            self.recorder.record_capture_gap("events", self.gaps[-1])
        artifacts: tuple[Mapping[str, str], ...] = ()
        completed = self.session is not None and self.session.status == ApiSessionStatus.COMPLETED and not self.failure and not self.gaps
        if self.session is not None and self.session.final_response is not None:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            text = "\n".join(block.text for block in self.session.final_response.output if block.text is not None)
            with self.output_path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
            output = _pin(self.root, self.output_path)
            self.recorder.record_file_revision(output.path, action="created", new_sha256=output.sha256, reason="actual Role response")
            artifacts = ({"path": output.path, "sha256": output.sha256, "contract": self.output_contract},)
        return ExecutionDriverResult(
            status="completed" if completed else "failed", actual_binding=self._actual.binding,
            actual_supply_report_ref=self._actual.supply_report_ref,
            turns=len(self.responses), output_tokens=sum(response.usage.output_tokens or 0 for response in self.responses),
            elapsed_seconds=max(0.0, self.clock() - started), provider_invocations=self.requests,
            tool_invocations=self.tool_invocations, tool_refs=tuple(sorted(self.used_tool_refs)),
            data_egress_payloads=self.payloads if self.requests else (), artifacts=artifacts,
            facts_complete=not self.gaps, capture_gaps=tuple(self.gaps),
            failure_code=self.failure or (None if completed else "ENTRY-SESSION-NOT-COMPLETED"),
            re_resolution_required=bool(self.failure and "DRIFT" in self.failure),
        )


def execute_role_slice(
    root: str | Path, *, bundle_ref: CloseoutPin, view_ref: CloseoutPin,
    role: str, provider: ModelProvider, binding_observer: Callable[[ModelProvider], Any],
    output_dir: str, output_path: str, output_contract: str, attempt_id: str,
    report_id: str, receipt_id: str, accountable_owner: str,
    input_refs: Sequence[Mapping[str, str]] = (), limits: ApiSessionLimits | None = None,
    host_clock: HostClock | None = None, session_clock: Callable[[], float] = time.monotonic,
    deadline_monotonic: float | None = None,
    cancel_requested: Callable[[], bool] | None = None, schema_root: str | Path | None = None,
    request_builder: Callable[..., ModelRequest] | None = None,
    request_payloads: Sequence[str] = ("project-context",),
    dispatch_guard: Callable[[str], bool] | None = None,
    tools: Sequence[ClientTool] = (), tool_refs: Mapping[str, str] | None = None,
) -> RoleSliceResult:
    """Save actual execution files, then verify their Core Receipt independently.

    Partial failures remain retained; unavailable facts never become a complete
    Receipt. Output locations must lie in the frozen permission intersection.
    """
    prepared_at = session_clock()
    if (isinstance(prepared_at, bool) or not isinstance(prepared_at, (int, float))
            or not math.isfinite(prepared_at)):
        raise EntryDriverError("Session clock must be finite")
    if deadline_monotonic is not None and (
            isinstance(deadline_monotonic, bool) or not isinstance(deadline_monotonic, (int, float))
            or not math.isfinite(deadline_monotonic)):
        raise EntryDriverError("absolute Session deadline must be finite")
    project_root = Path(root).resolve()
    _read_pin(project_root, bundle_ref)
    bundle = load_runtime_bundle(bundle_ref.path, project_root=project_root, schema_root=schema_root)
    if bundle.manifest_sha256 != bundle_ref.sha256.lower().removeprefix("sha256:"):
        raise EntryDriverError("Runtime Bundle changed while loading")
    view = load_resolved_execution_view(view_ref.path, expected_sha256=view_ref.sha256, bundle=bundle, schema_root=schema_root)
    duration = limits.max_seconds if limits is not None else float(view.document["effective_constraints"]["budget"].get("max_seconds", 60))
    deadline_monotonic = min(prepared_at + duration, deadline_monotonic) if deadline_monotonic is not None else prepared_at + duration
    destination = _scope_path(project_root, output_dir, view.document)
    output = _scope_path(project_root, output_path, view.document)
    if output.exists() or destination.exists():
        raise FileExistsError("Role execution requires fresh output/archive paths")
    if output == destination or output in destination.parents:
        raise EntryDriverError("output path collides with archive directory")
    if destination in output.parents:
        relative_output = output.relative_to(destination)
        if relative_output.parts[0] in {"trace", "host.json", "validation.json", "receipt.json",
                "checker-source.py", "closeout-failure.json"}:
            raise EntryDriverError("output path collides with reserved archive files")
    if not accountable_owner.strip():
        raise EntryDriverError("a named accountable owner is required")
    observed = _observe(provider, binding_observer)
    destination.mkdir(parents=True, exist_ok=False)
    task = _plain(_task(view))
    clock = host_clock or SystemHostClock()
    read_allowlist = [str(item["path"]) for item in bundle.manifest["documents"]]
    read_allowlist += [bundle_ref.path, view_ref.path, view.document["agent_profile_ref"]["path"]]
    actual_inputs = tuple(input_refs) or tuple(task.get("input_refs", ()))
    read_allowlist += [str(item["path"]) for item in actual_inputs]
    recorder = AgentTraceRecorder(destination / "trace", task_id=task["task_id"],
        task_revision=task.get("revision", 1), attempt_id=attempt_id, task_snapshot=task,
        accountable_owner=accountable_owner, actor_id="entry-role-driver",
        runtime_identity=str(observed.binding["runtime"]["ref"]), provider=str(observed.binding["provider"]["ref"]),
        read_allowlist=read_allowlist,
        write_scope=[str(item).rstrip("/") + "/**" for item in view.document["effective_constraints"]["permissions"]["allowed_roots"]],
        tool_allowlist=list((tool_refs or {}).values()), created_at=clock.now().isoformat())
    view_reference = {"ref": f"{view.document['view_id']}@r{view.document['revision']}", "path": view_ref.path, "sha256": view_ref.sha256}
    recorder.record_decision_snapshot("execution-scope-binding", {
        "schema_version": "0.1.0", "record_kind": "execution-scope-binding",
        "view_ref": view_reference, "execution_scope": _plain(view.document["execution_scope"]),
    })
    driver = SessionExecutionDriver(project_root, view=view, role=role, provider=provider,
        binding_observer=binding_observer, observation=observed, recorder=recorder,
        output_path=output_path, output_contract=output_contract, input_refs=actual_inputs,
        limits=limits, session_clock=session_clock, cancel_requested=cancel_requested,
        deadline_monotonic=deadline_monotonic,
        request_builder=request_builder, request_payloads=request_payloads,
        tools=tools, tool_refs=tool_refs)
    if driver.tools:
        recorder.record_decision_snapshot("entry-client-tool-binding", {
            "client_tool_bindings": [{"client_name": item.definition.name,
                "component_ref": driver.tool_refs[item.definition.name], "side_effect": item.side_effect}
                for item in driver.tools],
            "definitions_sha256": hash_bytes(driver.tool_signature.encode("utf-8")),
            "limits": {name: getattr(driver.limits, name) for name in (
                "max_model_turns", "max_tool_calls", "max_parallel_tool_calls", "max_tool_result_chars")},
        })
    def admitted(started_at):
        now = session_clock()
        if (isinstance(now, bool) or not isinstance(now, (int, float))
                or not math.isfinite(now) or now < prepared_at or now >= deadline_monotonic):
            return False
        if dispatch_guard is not None and dispatch_guard(started_at) is not True:
            return False
        # A caller guard can itself consume time; never extend the deadline.
        now = session_clock()
        return (not isinstance(now, bool) and isinstance(now, (int, float))
                and math.isfinite(now) and prepared_at <= now < deadline_monotonic)

    host = execute_frozen_view(view, driver, report_id=report_id, attempt_id=attempt_id,
        clock=clock, schema_root=schema_root, dispatch_guard=admitted)
    host_pin = _persist(project_root, destination / "host.json", host)
    if host["execution_phase"] == "post-call":
        recorder.record_execution_fact(fact_id=attempt_id, view_ref=host["view_ref"],
            actual_binding=host["actual_binding"], actual_supply_report_ref=host["actual_supply_report_ref"])
    recorder.record_attempt_status(host["status"], reason="Role execution slice Host result")
    recorder.seal()
    trace_pin = _pin(project_root, recorder.index_path)
    validation_pin = receipt_pin = None
    error = None
    try:
        catalog = SchemaCatalog(schema_root)
        if catalog.validate("execution_host_report", host) or validate_attempt_trace(project_root, recorder.index_path).blocked:
            raise GenericCloseoutValidationError("retained Host/Trace validation did not pass")
        if host["actual_facts"]["complete"] is not True:
            raise GenericCloseoutValidationError("actual facts unavailable; complete Receipt is forbidden")
        subjects = [asdict(host_pin), asdict(trace_pin), *[{"path": item["path"], "sha256": item["sha256"]} for item in host["artifacts"]]]
        for subject in subjects:
            _read_pin(project_root, CloseoutPin(**subject))
        checker = destination / "checker-source.py"
        with checker.open("xb") as stream:
            stream.write(Path(__file__).read_bytes())
        validation = {
            "schema_version": "0.1.0", "report_id": "CHECK-" + attempt_id, "status": "pass",
            "checker": {"checker_id": "entry-role-file-integrity", "version": "1.0.0", "source_ref": asdict(_pin(project_root, checker))},
            "subject_refs": subjects, "checks": [{"code": "SUBJECT-INTEGRITY", "status": "pass", "detail": "Actual Host schema, Trace boundary and retained subject hashes checked."}],
            "scope": "execution-contract-only", "limitations": ["Structural execution evidence; no scientific or live qualification acceptance."],
        }
        validation_pin = _persist(project_root, destination / "validation.json", validation)
        receipt = build_generic_execution_receipt(view, bundle, host_report=host_pin,
            trace_index=trace_pin, validations=(validation_pin,), receipt_id=receipt_id, schema_root=schema_root)
        receipt_pin = _persist(project_root, destination / "receipt.json", receipt)
        validate_generic_execution_receipt(receipt_pin.path, expected_sha256=receipt_pin.sha256,
            bundle=bundle, schema_root=schema_root)
    except (ValueError, OSError) as exc:
        error = str(exc)
        _persist(project_root, destination / "closeout-failure.json", {"status": "incomplete", "reason": error})
        receipt_pin = None
    return RoleSliceResult(host, host_pin, trace_pin, validation_pin, receipt_pin, driver.session, error)


__all__ = ["EntryDriverError", "ObservedExecutionBinding", "RoleSliceResult", "SessionExecutionDriver", "execute_role_slice"]
