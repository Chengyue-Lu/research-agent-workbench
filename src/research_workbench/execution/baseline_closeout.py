"""File replay of bounded A1/A2 transport facts, without executing an arm."""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping, Sequence
from datetime import timedelta
from pathlib import Path
from typing import Any

from research_workbench.evaluation.pins import (
    EvaluationInputs,
    EvaluationValidationError,
    digest,
    file_ref,
    require,
    timestamp,
)
from research_workbench.observability.trace import _parse_message, validate_attempt_trace


BaselineCloseoutValidationError = EvaluationValidationError
BOUNDARIES = dict.fromkeys(
    ("supply_selection", "human_decision", "claim_acceptance", "promotion", "pruning", "recovery"),
    False,
)


def _key(reference: Mapping[str, Any]) -> str:
    return digest(file_ref(reference))


def _child_ref(root: Path, directory: Path, reference: Mapping[str, Any]) -> dict[str, str]:
    """Trace children are archive-relative; public receipt refs are root-relative."""
    ref = file_ref(reference)
    path = (directory / ref["path"]).resolve()
    require(path.is_relative_to(directory), "baseline Trace child escapes its archive")
    require(path.is_relative_to(root), "baseline Trace child escapes project root")
    return {"path": path.relative_to(root).as_posix(), "sha256": ref["sha256"]}


def _references(value: Any):
    if isinstance(value, Mapping):
        if "path" in value and "sha256" in value:
            yield file_ref(value)
        else:
            for name, child in value.items():
                # This is the historical producer identity, not a project input.
                if name != "compiler_ref":
                    yield from _references(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _references(child)


def _message(
    inputs: EvaluationInputs,
    directory: Path,
    entry: Mapping[str, Any],
) -> Mapping[str, Any]:
    ref = _child_ref(inputs.root, directory, entry)
    original = inputs.read_bytes(ref)
    header, body = _parse_message(inputs.root / ref["path"])
    content = json.loads(body)
    require(inputs.read_bytes(ref) == original, "baseline Trace message changed during replay")
    require(header["message_id"] == entry["message_id"], "baseline Trace message identity differs")
    require(isinstance(content, Mapping), "baseline Trace message body must be an object")
    return content


def _derive(
    inputs: EvaluationInputs,
    *,
    envelope_ref: Mapping[str, Any],
    envelope_snapshot_ref: Mapping[str, Any],
    protocol_ref: Mapping[str, Any],
    trace_index_ref: Mapping[str, Any],
    fact_refs: Sequence[Mapping[str, Any]],
    artifact_refs: Sequence[Mapping[str, Any]],
    validation_ref: Mapping[str, Any],
    validate_use_refs: bool = True,
) -> dict[str, Any]:
    require(file_ref(envelope_snapshot_ref)["sha256"] == file_ref(envelope_ref)["sha256"], "baseline Envelope snapshot bytes differ from frozen input")
    envelope = inputs.read(envelope_snapshot_ref, "baseline_execution_envelope")
    metadata = envelope["transport_enforcement_metadata"]
    require(file_ref(metadata["protocol_ref"]) == file_ref(protocol_ref), "baseline Protocol substitution")
    frozen = metadata["execution_binding"]
    required_inputs = {_key(ref): ref for ref in _references(envelope)}
    required_inputs.update({_key(envelope_ref): file_ref(envelope_ref), _key(protocol_ref): file_ref(protocol_ref)})

    trace = inputs.read(trace_index_ref, "agent_trace_index")
    trace_path = inputs.root / file_ref(trace_index_ref)["path"]
    directory = trace_path.parent
    require(not validate_attempt_trace(inputs.root, trace_path).blocked, "baseline Trace replay is blocked")
    require(trace["trace_status"] == "frozen" and trace["completeness"] == "complete", "baseline Trace is not complete and frozen")
    events_ref = _child_ref(inputs.root, directory, trace["event_ledger"])
    events = [json.loads(line) for line in inputs.read_bytes(events_ref).splitlines() if line.strip()]
    require(bool(events) and events[-1]["event_type"] == "attempt-status", "baseline Trace lacks its terminal status event")
    messages = {entry["message_id"]: entry for entry in trace["messages"]}

    indexed_facts = {}
    for child in trace["decision_refs"]:
        ref = _child_ref(inputs.root, directory, child)
        document = inputs.read(ref, "baseline_execution_fact")
        indexed_facts[_key(ref)] = document
    keys = [_key(ref) for ref in fact_refs]
    require(len(keys) == len(set(keys)) and set(keys) == set(indexed_facts), "baseline facts differ from Trace decision references")
    facts = [inputs.read(ref, "baseline_execution_fact") for ref in fact_refs]
    require(bool(facts), "baseline closeout requires a terminal fact")
    require(len({fact["fact_id"] for fact in facts}) == len(facts), "baseline fact identity is duplicated")
    sequences = [fact["event_sequence"] for fact in facts]
    require(sequences == sorted(set(sequences)), "baseline fact event order is duplicated or reordered")
    terminal = facts[-1]
    require(terminal["operation"] == "session" and terminal["phase"] == "end", "baseline final fact must close the session")
    require(terminal["call_id"] == "session" and terminal["tool_ref"] is None, "baseline terminal fact identity differs")
    require(terminal["event_sequence"] == events[-1]["sequence"], "baseline terminal fact does not bind final Trace event")
    started = timestamp(terminal["started_at"])
    completed = timestamp(terminal["observed_at"])
    require(started.utcoffset() == timedelta(0) and completed.utcoffset() == timedelta(0), "baseline timestamps must be UTC")
    require(completed >= started, "baseline session time interval is reversed")
    all_uses: dict[str, Mapping[str, Any]] = {}
    pending: dict[tuple[str, str], Mapping[str, Any]] = {}
    closed: set[tuple[str, str]] = set()
    consumed_events: set[int] = set()
    actual_binding = None
    last_response = None
    provider_after = []
    actual_tools: list[tuple[str, dict[str, Any]]] = []
    for fact in facts:
        require(fact["attempt_id"] == trace["attempt_id"], "baseline fact Attempt differs from Trace")
        require(file_ref(fact["envelope_ref"]) == file_ref(envelope_ref), "baseline fact Envelope substitution")
        require(fact["started_at"] == terminal["started_at"], "baseline fact start differs from session")
        observed = timestamp(fact["observed_at"])
        require(observed.utcoffset() == timedelta(0) and started <= observed <= completed, "baseline fact time is outside session")
        require(math.isfinite(fact["elapsed_seconds"]), "baseline elapsed time must be finite")
        require(fact["elapsed_seconds"] <= terminal["elapsed_seconds"], "baseline fact elapsed time exceeds session")
        sequence = fact["event_sequence"]
        require(1 <= sequence <= len(events), "baseline fact references an absent Trace event")
        event = events[sequence - 1]
        require(digest(event) == fact["event_sha256"], "baseline fact event hash differs")
        require(event["attempt_id"] == trace["attempt_id"], "baseline event Attempt differs")
        uses = {_key(ref): file_ref(ref) for ref in fact["use_refs"]}
        require(len(uses) == len(fact["use_refs"]), "baseline fact use reference is duplicated")
        all_uses.update(uses)
        operation, phase = fact["operation"], fact["phase"]
        if operation == "session":
            require(fact is terminal and phase == "end", "baseline session fact must be terminal")
            continue
        require(phase in {"before", "after"}, "baseline call fact has an invalid phase")
        call = (operation, fact["call_id"])
        if phase == "before":
            require(call not in pending and call not in closed, "baseline call identity is reused")
            require(fact["binding"] == frozen, "baseline before-call binding differs from frozen input")
            pending[call] = fact
        else:
            require(call in pending, "baseline after-call fact lacks a preceding call")
            require(fact["tool_ref"] == pending[call]["tool_ref"], "baseline Tool identity changes during call")
            closed.add(call)
            del pending[call]
        consumed_events.add(sequence)
        payload = event["payload"]
        if operation == "provider":
            require(fact["tool_ref"] is None, "baseline provider fact must not bind a Tool")
            require(event["event_type"] == "message-capture", "baseline provider fact lacks a message event")
            entry = messages.get(payload.get("message_id"))
            expected_kind = "provider-request" if phase == "before" else "provider-response"
            require(entry is not None and entry["kind"] == expected_kind, "baseline provider fact phase differs from message")
            body = _message(inputs, directory, entry)
            if phase == "after":
                response = body.get("response", body)
                require(isinstance(response, Mapping), "baseline provider response must be an object")
                binding = fact["binding"]
                require(binding is not None, "baseline provider response lacks actual binding")
                require(binding["provider"]["ref"] == response.get("provider") and binding["model"]["ref"] == response.get("model"), "baseline actual binding differs from provider response")
                actual_binding = binding
                last_response = response
                provider_after.append(fact)
        else:
            require(operation == "tool" and event["event_type"] == "tool-call", "baseline Tool fact lacks a Tool event")
            require(payload["operation_id"] == fact["call_id"], "baseline Tool call identity differs from event")
            require((payload["status"] == "attempted") == (phase == "before"), "baseline Tool event phase differs")
            require(fact["tool_ref"] is not None and fact["binding"] == frozen, "baseline Tool binding differs from frozen input")
            required_inputs[_key(fact["tool_ref"])] = file_ref(fact["tool_ref"])
            actual_tools.append((payload["tool_name"], file_ref(fact["tool_ref"])))

    execution_events = {
        event["sequence"] for event in events
        if event["event_type"] == "tool-call"
        or event["event_type"] == "message-capture"
        and messages.get(event["payload"].get("message_id"), {}).get("kind") in {"provider-request", "provider-response"}
    }
    require(consumed_events == execution_events, "baseline facts omit or invent execution events")
    terminal_uses = {_key(ref) for ref in terminal["use_refs"]}
    require(set(all_uses) <= terminal_uses and set(required_inputs) <= terminal_uses, "baseline terminal fact omits its frozen input closure")
    require(terminal["binding"] == actual_binding, "baseline terminal binding differs from last actual response")
    final_status = events[-1]["payload"]["to_status"]
    require(final_status == trace["attempt_status"], "baseline Trace final status differs")
    if final_status == "completed":
        require(bool(provider_after) and not pending, "completed baseline lacks complete call facts")
        require(all(fact["binding"] == frozen for fact in provider_after), "completed baseline contains actual binding drift")
        status = "completed"
    else:
        status = "post-call-failed" if execution_events else "preflight-blocked"
    # Failed Attempts retain their immutable observed facts even when an input
    # drift destroyed the old source bytes. They cannot acquire successful
    # eligibility this way; strict replay still rejects that unavailable closure.
    if validate_use_refs or status == "completed":
        protocol = inputs.read(protocol_ref, "system_evaluation_protocol")
        require(frozen == protocol["execution_binding"], "baseline frozen binding differs from Protocol")
        for ref in {**required_inputs, **all_uses}.values():
            inputs.read_bytes(ref)
        if actual_tools:
            require(metadata["qualification_ref"] is not None, "baseline Tool facts lack A2 qualification")
            qualification = inputs.read(metadata["qualification_ref"], "arm_execution_qualification")
            qualified_tools = set()
            for binding in qualification["bindings"]:
                snapshot = inputs.read(binding["runtime_snapshot_ref"], "resolved_capability_snapshot")
                interface = inputs.read(binding["interface_ref"], "evaluation_provider_interface")
                qualified_tools.add((
                    _key(snapshot["task_ref"]),
                    interface["provider_visible_interface"]["name"],
                    _key(binding["implementation_ref"]),
                ))
            for name, reference in actual_tools:
                require((_key(metadata["task_ref"]), name, _key(reference)) in qualified_tools,
                        "baseline actual Tool differs from qualified Tool implementation for Task")
    require(len(artifact_refs) == (1 if last_response is not None else 0), "baseline output count differs from actual response")
    if last_response is not None:
        require(inputs.read(artifact_refs[0]) == last_response, "baseline final artifact differs from actual last response")
    validation = inputs.read(validation_ref, "deterministic_check_report")
    subjects = {_key(ref) for ref in validation["subject_refs"]}
    require({_key(trace_index_ref), *(_key(ref) for ref in artifact_refs)} <= subjects, "baseline validation omits Trace or outputs")
    for ref in validation["subject_refs"]:
        inputs.read_bytes(ref)
    expected_status = "pass" if status == "completed" else "fail"
    require(validation["status"] == expected_status, "baseline validation status contradicts transport result")
    require((all(item["status"] == "pass" for item in validation["checks"])) == (status == "completed"), "baseline validation checks contradict transport result")
    return {
        "attempt_id": trace["attempt_id"],
        "status": status,
        "reason": events[-1]["payload"]["reason"],
        "started_at": terminal["started_at"],
        "completed_at": terminal["observed_at"],
        "elapsed_seconds": terminal["elapsed_seconds"],
        "actual_binding": copy.deepcopy(actual_binding),
    }


def produce_baseline_closeout(
    root: str | Path,
    *,
    receipt_id: str,
    envelope_ref: Mapping[str, Any],
    envelope_snapshot_ref: Mapping[str, Any],
    protocol_ref: Mapping[str, Any],
    trace_index_ref: Mapping[str, Any],
    fact_refs: Sequence[Mapping[str, Any]],
    artifact_refs: Sequence[Mapping[str, Any]],
    validation_ref: Mapping[str, Any],
    schema_root: str | Path | None = None,
) -> dict[str, Any]:
    """Derive a receipt from persisted facts; never accept caller status/binding."""
    inputs = EvaluationInputs(root, schema_root)
    actual = _derive(
        inputs, envelope_ref=envelope_ref, envelope_snapshot_ref=envelope_snapshot_ref,
        protocol_ref=protocol_ref,
        trace_index_ref=trace_index_ref, fact_refs=fact_refs,
        artifact_refs=artifact_refs, validation_ref=validation_ref, validate_use_refs=False,
    )
    result = {
        "schema_version": "0.1.0", "record_kind": "baseline_execution_receipt",
        "version": "1.0.0", "receipt_id": receipt_id,
        "envelope_ref": file_ref(envelope_ref), "protocol_ref": file_ref(protocol_ref),
        "envelope_snapshot_ref": file_ref(envelope_snapshot_ref),
        "trace_index_ref": file_ref(trace_index_ref),
        "fact_refs": [file_ref(ref) for ref in fact_refs],
        "artifact_refs": [file_ref(ref) for ref in artifact_refs],
        "validation_ref": file_ref(validation_ref),
        **actual, "task_completion": False, "boundaries": dict(BOUNDARIES),
    }
    inputs.validate("baseline_execution_receipt", result)
    inputs.recheck()
    return result


def verify_baseline_receipt(
    root: str | Path,
    receipt_ref: Mapping[str, Any],
    *,
    expected_envelope_ref: Mapping[str, Any],
    schema_root: str | Path | None = None,
) -> dict[str, Any]:
    """Replay historical files without Provider/Tool calls or live expiry checks."""
    inputs = EvaluationInputs(root, schema_root)
    receipt = inputs.read(receipt_ref, "baseline_execution_receipt")
    require(file_ref(receipt["envelope_ref"]) == file_ref(expected_envelope_ref), "baseline receipt Envelope substitution")
    actual = _derive(
        inputs, envelope_ref=expected_envelope_ref,
        envelope_snapshot_ref=receipt["envelope_snapshot_ref"],
        protocol_ref=receipt["protocol_ref"], trace_index_ref=receipt["trace_index_ref"],
        fact_refs=receipt["fact_refs"], artifact_refs=receipt["artifact_refs"],
        validation_ref=receipt["validation_ref"],
    )
    require(all(receipt[key] == value for key, value in actual.items()), "baseline receipt contradicts replayed execution facts")
    inputs.recheck()
    return copy.deepcopy(dict(receipt))
