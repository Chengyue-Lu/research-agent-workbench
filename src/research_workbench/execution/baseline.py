"""M6 A1/A2 transport: a frozen public request through the existing API loop."""

from __future__ import annotations

import hashlib
import inspect
import json
import platform
import socket
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_workbench.adapters.models.port import (
    ContentBlock, DataPolicy, Message, ModelProvider, ModelRequest,
    ProviderRegistry, ToolDefinition,
)
from research_workbench.adapters.models.session import (
    ApiSessionLimits, ApiSessionStatus, ClientTool, IsolatedApiSessionRunner,
)
from research_workbench.evaluation.pins import (
    EvaluationInputs, EvaluationValidationError, digest, file_ref, require, timestamp,
)
from research_workbench.execution.baseline_envelope import (
    compiler_reference, validate_baseline_envelope,
)
from research_workbench.observability.trace import AgentTraceRecorder, sanitize_trace_value


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_plain(item) for item in value)
    return value


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(function: Callable) -> Path:
    name = inspect.getsourcefile(function)
    require(name is not None, "baseline callable requires a file-bound implementation")
    return Path(name).resolve()


def observe_baseline_binding(
    provider: ModelProvider, *, model: str, model_slot: str
) -> dict[str, Any]:
    """Observe the actual local transport before freezing the Protocol.

    The model hash identifies the selected provider capability descriptor,
    not model weights or an independently authenticated remote deployment.
    """
    caps = provider.capabilities()
    adapter_hash = _hash(_source(provider.generate))
    adapter_name = f"{type(provider).__module__}.{type(provider).__qualname__}"
    host = {"machine": socket.gethostname(), "platform": platform.platform()}
    return {
        "provider": {"ref": caps.provider, "version": caps.adapter_version,
                     "content_hash": digest(_plain(caps))},
        "adapter": {"ref": adapter_name, "version": caps.adapter_version,
                    "content_hash": adapter_hash},
        "model": {"ref": model, "version": "provider-capability-descriptor-v1",
                  "content_hash": digest({"capabilities": _plain(caps), "model": model}),
                  "model_class": "provider-reported", "slot": model_slot,
                  "capabilities": sorted(str(cap) for cap in caps.supported)},
        "runtime": {"ref": platform.python_implementation(),
                    "version": platform.python_version(), "content_hash": _hash(Path(sys.executable))},
        "host": {"ref": host["machine"], "version": "m6-baseline-transport-1.0.0",
                 "content_hash": digest({"host": host, "transport": _hash(Path(__file__)),
                                         "session": _hash(_source(IsolatedApiSessionRunner.run))})},
    }


def _reference(root: Path, path: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(), "sha256": _hash(path)}


def _write(root: Path, path: Path, document: Mapping[str, Any]) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(_plain(document), stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return _reference(root, path)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _data_policy(inputs: EvaluationInputs, metadata: Mapping[str, Any]) -> DataPolicy:
    document = inputs.read(metadata["context"]["data_policy_ref"], "project_protocol")
    boundary = document["data_boundary"]
    return DataPolicy(
        local_only=(metadata["permissions"].get("network") == "forbidden"
                    or boundary.get("local_only", False)),
        zero_data_retention_required=boundary.get("zero_data_retention_required", False),
        training_opt_out_required=boundary.get("training_opt_out_required", False),
        allowed_regions=tuple(boundary.get("allowed_regions", ())),
    )


def _request(inputs: EvaluationInputs, envelope: Mapping[str, Any]) -> ModelRequest:
    public = envelope["provider_visible_payload"]
    metadata = envelope["transport_enforcement_metadata"]
    # Only this positive projection can enter messages. No Task/Profile/Method,
    # metadata, provider extensions, private oracle or future action is copied.
    body = {key: public[key] for key in ("instruction", "inputs", "required_outputs")}
    return ModelRequest(
        model=metadata["execution_binding"]["model"]["ref"],
        messages=(Message("user", (ContentBlock("text", text=json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )),)),),
        tools=tuple(ToolDefinition(**tool) for tool in public["tools"]),
        max_output_tokens=metadata["budget"]["max_output_tokens"],
        data_policy=_data_policy(inputs, metadata),
    )


def _tool_inputs(inputs: EvaluationInputs, metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Read already-qualified, Task-specific bindings; never select a Supply."""
    if metadata["qualification_ref"] is None:
        return {}
    qualification = inputs.read(metadata["qualification_ref"], "arm_execution_qualification")
    result = {}
    for binding in qualification["bindings"]:
        snapshot = inputs.read(binding["runtime_snapshot_ref"], "resolved_capability_snapshot")
        if file_ref(snapshot["task_ref"]) != metadata["task_ref"]:
            continue
        interface = inputs.read(binding["interface_ref"], "evaluation_provider_interface")
        supply = inputs.read(snapshot["selected_supply_report_ref"], "capability_supply_report")
        result[interface["provider_visible_interface"]["name"]] = {
            "implementation_ref": file_ref(binding["implementation_ref"]),
            "availability": supply["availability"], "snapshot": snapshot,
        }
    return result


class _BaselineSink:
    def __init__(self, *, inputs, envelope_ref, envelope, provider, tools, recorder,
                 clock, utc_clock, started, started_at, tool_inputs):
        self.inputs, self.envelope_ref, self.envelope = inputs, envelope_ref, envelope
        self.metadata = envelope["transport_enforcement_metadata"]
        self.provider, self.tools, self.recorder = provider, tools, recorder
        self.clock, self.utc_clock = clock, utc_clock
        self.started, self.started_at = started, started_at
        self.tool_inputs = tool_inputs
        self.use_refs = [{"path": path, "sha256": sha} for path, sha in sorted(inputs.hashes.items())]
        self.facts: list[dict[str, str]] = []
        self.provider_count = 0
        self.actual_binding = None
        self.last_response = None
        self.problem = None

    def _observed(self, model=None):
        expected = self.metadata["execution_binding"]["model"]
        return observe_baseline_binding(self.provider, model=model or expected["ref"], model_slot=expected["slot"])

    def preflight(self, tool_name=None):
        require(self.clock() - self.started < self.metadata["budget"]["max_seconds"], "pre-call time budget")
        for reference in self.use_refs:
            self.inputs.read_bytes(reference)
        require(compiler_reference() == self.metadata["compiler_ref"], "baseline compiler changed")
        require(self._observed() == self.metadata["execution_binding"], "actual transport binding drift")
        now = timestamp(self.utc_clock())
        for binding in self.tool_inputs.values():
            availability = binding["availability"]
            require(timestamp(availability["observed_at"]) <= now <= timestamp(availability["valid_until"]),
                    "A2 availability expired at use boundary")
        if tool_name is not None:
            binding = self.tool_inputs[tool_name]
            source = _source(self.tools[tool_name].execute)
            require(source == (self.inputs.root / binding["implementation_ref"]["path"]).resolve(),
                    "actual Tool callable differs from qualified implementation path")
            require(_hash(source) == binding["implementation_ref"]["sha256"], "actual Tool bytes drift")

    def fact(self, operation, phase, call_id, *, binding, tool_ref=None):
        event = json.loads((self.recorder.attempt_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        document = {
            "schema_version": "0.1.0", "record_kind": "baseline_execution_fact", "version": "1.0.0",
            "fact_id": f"BASELINE-FACT-{len(self.facts) + 1:04d}", "attempt_id": self.recorder.attempt_id,
            "envelope_ref": self.envelope_ref, "operation": operation, "phase": phase, "call_id": call_id,
            "event_sequence": event["sequence"], "event_sha256": digest(event),
            "started_at": self.started_at, "observed_at": self.utc_clock(),
            "elapsed_seconds": self.clock() - self.started, "binding": binding,
            "tool_ref": tool_ref, "use_refs": self.use_refs,
        }
        self.inputs.validate("baseline_execution_fact", document)
        ref = self.recorder.record_decision_snapshot(document["fact_id"], document)
        root_ref = {"path": (self.recorder.attempt_dir / ref["path"]).relative_to(self.inputs.root).as_posix(),
                    "sha256": ref["sha256"]}
        self.facts.append(root_ref)

    def record(self, kind, payload):
        if kind in {"provider-request", "tool-attempted"}:
            require(self.problem is None, self.problem or "post-call failure")
            self.preflight(payload.get("name") if kind == "tool-attempted" else None)
        # Normalize dataclasses before the existing recursive sanitizer so
        # nested provider metadata receives the same treatment as artifacts.
        self.recorder.record(kind, _plain(payload))
        if kind == "provider-request":
            self.provider_count += 1
            self.fact("provider", "before", f"provider-{self.provider_count}", binding=self._observed())
        elif kind == "provider-response":
            response = payload["response"]
            self.last_response, _ = sanitize_trace_value(_plain(response))
            self.actual_binding = self._observed(response.model)
            # Response provider/model are observations, not expected metadata.
            self.actual_binding["provider"]["ref"] = response.provider
            self.fact("provider", "after", f"provider-{self.provider_count}", binding=self.actual_binding)
            if self.actual_binding != self.metadata["execution_binding"]:
                self.problem = "post-call actual transport binding drift"
            if response.usage.input_tokens is not None and response.usage.input_tokens > self.metadata["context"]["max_input_tokens"]:
                self.problem = "post-call input token budget"
        elif kind in {"tool-attempted", "tool-result"}:
            name = payload["name"]
            self.fact("tool", "before" if kind == "tool-attempted" else "after", payload["call_id"],
                      binding=self._observed(), tool_ref=self.tool_inputs[name]["implementation_ref"])
            if kind == "tool-result" and payload["status"] == "failed":
                self.problem = "post-call Tool failed"
        if kind in {"provider-response", "tool-result"}:
            if self.clock() - self.started >= self.metadata["budget"]["max_seconds"]:
                self.problem = "post-call time budget (detective; no hard preemption)"


def run_baseline_session(
    root: str | Path, *, envelope_ref: Mapping[str, Any], expected_protocol_ref: Mapping[str, Any],
    provider: ModelProvider, attempt_path: str, attempt_id: str, receipt_id: str,
    tools: tuple[ClientTool, ...] = (), clock: Callable[[], float] = time.monotonic,
    utc_clock: Callable[[], str] = _utc, schema_root: str | Path | None = None,
) -> dict[str, Any]:
    """Run one fresh frozen arm and persist even unsuccessful transport outcomes.

    No live provider authorization is inferred here: callers freeze the public
    case and register the authorized adapter before invoking this producer.
    """
    from research_workbench.execution.baseline_closeout import (
        produce_baseline_closeout, verify_baseline_receipt,
    )

    inputs = EvaluationInputs(root, schema_root)
    envelope_ref = file_ref(envelope_ref)
    envelope_bytes = inputs.read_bytes(envelope_ref)
    envelope = inputs.read(envelope_ref, "baseline_execution_envelope")
    validate_baseline_envelope(inputs, envelope, expected_protocol_ref=expected_protocol_ref)
    metadata = envelope["transport_enforcement_metadata"]
    task = inputs.read(metadata["task_ref"], "task_packet")
    destination = (inputs.root / attempt_path).resolve()
    require(destination.is_relative_to(inputs.root) and destination != inputs.root, "Attempt escapes project root")
    require(any(destination.is_relative_to((inputs.root / item).resolve()) for item in metadata["write_scope"]),
            "Attempt is outside frozen Task write scope")
    permissions = metadata["permissions"]
    require(permissions.get("filesystem") in {"worktree-write", "read-write"},
            "Task filesystem permission does not allow Attempt writes")
    require(any(destination.is_relative_to((inputs.root / item).resolve())
                for item in permissions.get("allowed_roots", metadata["write_scope"])),
            "Attempt is outside Task permission roots")
    require(not destination.exists(), "baseline Attempt must be fresh")
    request = _request(inputs, envelope)
    tool_inputs = _tool_inputs(inputs, metadata)
    tool_map = {tool.definition.name: tool for tool in tools}
    require(len(tool_map) == len(tools), "duplicate baseline Tool handler")
    require(set(tool_map) == set(tool_inputs), "baseline handler set differs from A2 qualification")
    require([_plain(tool_map[t.name].definition) for t in request.tools] == [_plain(t) for t in request.tools],
            "baseline handler interface differs from frozen Tool")
    # v1 executes qualified read-only ClientTools; file writing by the transport
    # is confined to the declared Attempt. A callable is not an OS sandbox.
    require(all(tool.side_effect == "read-only" for tool in tools), "baseline v1 requires read-only ClientTools")
    budget = metadata["budget"]
    for key, ceiling in task["budget"].items():
        require(budget[key] <= ceiling, f"baseline exceeds Task {key} ceiling")
    parallel = budget["max_parallel"] if tools else 0
    require(not tools or parallel > 0, "frozen parallel Tool budget is zero")
    max_tool_chars = 1  # No Tool results are possible for A1.
    if tools:
        context_policy = inputs.read(metadata["context"]["policy_ref"], "project_protocol")["context_policy"]
        max_tool_chars = context_policy.get("baseline_transport", {}).get("max_tool_result_chars")
        require(type(max_tool_chars) is int and max_tool_chars > 0,
                "A2 requires an explicit frozen max_tool_result_chars in its context policy")
    limits = ApiSessionLimits(
        max_model_turns=budget["max_turns"], max_tool_calls=budget["max_turns"] * parallel,
        max_parallel_tool_calls=parallel, max_tool_result_chars=max_tool_chars,
        max_output_tokens_per_turn=budget["max_output_tokens"], max_seconds=budget["max_seconds"],
    )
    started_at, started = utc_clock(), clock()
    recorder = AgentTraceRecorder(
        destination, task_id=task["task_id"], task_revision=task["revision"], attempt_id=attempt_id,
        task_snapshot=task, accountable_owner=metadata["accountable_owner"], actor_id="m6-baseline-transport",
        runtime_identity="m6-baseline-transport@1.0.0", provider=metadata["execution_binding"]["provider"]["ref"],
        read_allowlist=list(inputs.hashes), write_scope=metadata["write_scope"], tool_allowlist=list(tool_map),
        created_at=started_at,
    )
    snapshot_path = destination / ("envelope" + Path(envelope_ref["path"]).suffix)
    with snapshot_path.open("xb") as stream:
        stream.write(envelope_bytes)
    envelope_snapshot_ref = _reference(inputs.root, snapshot_path)
    sink = _BaselineSink(inputs=inputs, envelope_ref=envelope_ref, envelope=envelope, provider=provider,
                         tools=tool_map, recorder=recorder, clock=clock, utc_clock=utc_clock,
                         started=started, started_at=started_at, tool_inputs=tool_inputs)
    registry = ProviderRegistry()
    provider_name = metadata["execution_binding"]["provider"]["ref"]
    registry.register(provider_name, provider)
    status, reason = "blocked", "preflight blocked"
    try:
        sink.preflight()
        result = IsolatedApiSessionRunner(registry, tools=tools, clock=clock).run(
            provider_name=provider_name, request=request, limits=limits, event_sink=sink)
        status = "completed" if result.status == ApiSessionStatus.COMPLETED and sink.problem is None else "failed"
        reason = sink.problem or result.stop_reason
    except (EvaluationValidationError, ValueError, KeyError, OSError) as exc:
        reason = str(exc)
        status = "failed" if sink.provider_count else "blocked"
    if recorder.redaction_count:
        status, reason = "failed", "trace redaction prevents exact transport replay"
    recorder.record_attempt_status(status, reason=reason)
    sink.fact("session", "end", "session", binding=sink.actual_binding)
    trace_ref = recorder.seal(status)
    trace_ref = {"path": (destination / trace_ref["path"]).relative_to(inputs.root).as_posix(), "sha256": trace_ref["sha256"]}
    artifact_refs = []
    if sink.last_response is not None:
        artifact_refs.append(_write(inputs.root, destination / "output.json", sink.last_response))
    validation = {
        "schema_version": "0.1.0", "report_id": f"CHECK-{attempt_id}",
        "checker": {"checker_id": "baseline-transport-closeout", "version": "1.0.0",
                    "source_ref": {"path": "src/research_workbench/execution/baseline.py", "sha256": _hash(Path(__file__))}},
        "subject_refs": [trace_ref, *artifact_refs], "status": "pass" if status == "completed" else "fail",
        "checks": [{"code": "BASELINE-TRANSPORT", "status": "pass" if status == "completed" else "fail", "detail": reason}],
        "scope": "fixed A1/A2 transport output capture; not Task or scientific acceptance",
        "limitations": ["Provider-reported model identity is not model-weight authentication.",
                        "Synchronous calls have post-call time detection, not hard preemption."],
    }
    inputs.validate("deterministic_check_report", validation)
    validation_ref = _write(inputs.root, destination / "validation.json", validation)
    receipt = produce_baseline_closeout(inputs.root, receipt_id=receipt_id, envelope_ref=envelope_ref,
        envelope_snapshot_ref=envelope_snapshot_ref,
        protocol_ref=file_ref(expected_protocol_ref), trace_index_ref=trace_ref, fact_refs=sink.facts,
        artifact_refs=artifact_refs, validation_ref=validation_ref, schema_root=schema_root)
    receipt_ref = _write(inputs.root, destination / "receipt.json", receipt)
    try:
        verify_baseline_receipt(inputs.root, receipt_ref, expected_envelope_ref=envelope_ref, schema_root=schema_root)
        replay_valid, replay_error = True, None
    except (EvaluationValidationError, ValueError, OSError) as exc:
        replay_valid, replay_error = False, str(exc)
    return {"receipt_ref": receipt_ref, "receipt": receipt, "replay_valid": replay_valid, "replay_error": replay_error}
