"""H3 synthetic execution in frozen order, with retained Attempts and cold replay."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from research_workbench.evaluation.harness_preflight import validate_harness_preflight
from research_workbench.evaluation.harness_runtime import (
    execute_slice, persist, plain, reference, replay_slice,
)
from research_workbench.evaluation.pins import EvaluationInputs, digest, file_ref, require, timestamp
from research_workbench.execution.baseline import run_baseline_session
from research_workbench.execution.baseline_closeout import verify_baseline_receipt
from research_workbench.execution.baseline_envelope import compile_baseline_envelope

KIND = "evaluation_harness_execution"
BASELINE_ARMS = {"plain-agent", "plain-agent-tool"}
BOUNDARIES = dict.fromkeys(("runtime_input", "execution_authority", "supply_selection",
                           "human_decision", "task_completion", "analysis_eligibility"), False)


@dataclass(frozen=True)
class HarnessContext:
    """Caller-owned pins/time; none are recovered from a result being checked."""
    expected_plan_ref: Mapping[str, Any]
    expected_preflight_ref: Mapping[str, Any]
    expected_protocol_ref: Mapping[str, Any]
    expected_case_closure_ref: Mapping[str, Any]
    case_selection_frozen_at: str
    expected_run_id: str
    expected_preflight_checked_at: str


@dataclass(frozen=True)
class HarnessPorts:
    """Explicit local ports, without selectors or fallback implementations.

    Factories must return new Provider/Driver instances. Only the M6 producer
    receives the Tool handlers; A1 never receives them. Python ports are trusted
    local code, not an OS sandbox or a grant to call a live provider.
    """
    baseline_provider: Callable
    baseline_tools: tuple
    core_driver: Callable
    skill_driver: Callable


def _context(inputs, context, admission_verifier):
    args = dict(vars(context))
    preflight_ref = args.pop("expected_preflight_ref")
    preflight = validate_harness_preflight(inputs,
        inputs.read(preflight_ref, "evaluation_harness_preflight"),
        **args, admission_verifier=admission_verifier)
    protocol = inputs.read(context.expected_protocol_ref, "system_evaluation_protocol")
    require(protocol["purpose"] == "synthetic-contract-proof",
            "H3 entry requires a synthetic Protocol; formal M5-004 gates are separate")
    plan = inputs.read(context.expected_plan_ref, "evaluation_harness_plan")
    return plan, preflight


def _archive(inputs, context):
    path = (inputs.root / ".rwb" / "harness" / digest(context.expected_run_id)).resolve()
    require(path.is_relative_to(inputs.root), "Harness archive escapes evaluation root")
    return path


def _destination(inputs, case, slot):
    task = inputs.read(case["task_ref"], "task_packet")
    scope = task["write_scope"][0]
    require(bool(scope) and "\\" not in scope and ":" not in scope
            and not any(char in scope for char in "*?[]")
            and not scope.startswith("/") and all(p not in {"", ".", ".."} for p in scope.split("/")),
            "Harness requires a concrete portable Task write directory")
    path = (inputs.root / scope / "harness" / slot["attempt_id"]).resolve()
    permissions = task["permissions"]
    require(path.is_relative_to(inputs.root) and path != inputs.root
            and permissions["filesystem"] in {"worktree-write", "read-write"}
            and any(path.is_relative_to((inputs.root / p).resolve())
                    for p in permissions["allowed_roots"]),
            "Harness Attempt is outside frozen Task write permission")
    return path


def _slices(inputs, preflight, case, arm_id):
    binding = next(b for b in preflight["request"]["case_bindings"] if b["case_id"] == case["case_id"])
    if arm_id == "mode-no-skill":
        candidates = inputs.read(binding["pairwise_ref"])["a3_runtime_bindings"]
    else:
        candidates = inputs.read(binding["a4_overlay_ref"])["runtime_bindings"]
    result = [b for b in candidates if file_ref(inputs.read(b["snapshot_ref"])["task_ref"]) == case["task_ref"]]
    require(bool(result), "Harness arm has no qualified Task slices")
    return [{k: file_ref(b[k]) for k in ("snapshot_ref", "bundle_ref", "view_ref")}
            for b in sorted(result, key=lambda b: digest(b["snapshot_ref"]))]


def _envelope(inputs, context, preflight, case, arm_id, slot):
    return compile_baseline_envelope(inputs, protocol_ref=context.expected_protocol_ref,
        task_ref=case["task_ref"], public_payload_ref=case["public_payload_ref"], arm_id=arm_id,
        envelope_id="H3-" + slot["attempt_id"], accountable_owner="evaluation-harness",
        qualification_ref=(preflight["request"]["a2_qualification_ref"] if arm_id == "plain-agent-tool" else None))


def _m11_progress(inputs, context, receipt_refs, required):
    """An arm shares its frozen budget across all its capability slices."""
    hosts = [inputs.read(inputs.read(ref)["host_report_ref"]) for ref in receipt_refs]
    for before, after in zip(hosts, hosts[1:]):
        require(timestamp(after["started_at"]) >= timestamp(before["completed_at"]),
                "Harness slice clock regressed between calls")
    if any(host["status"] != "completed" for host in hosts):
        return ("post-call-failed" if any(h["execution_phase"] == "post-call" for h in hosts)
                else "preflight-blocked")
    protocol = inputs.read(context.expected_protocol_ref)
    budget = {**inputs.read(protocol["manifest_ref"])["frozen_conditions"]["budget"],
              "max_seconds": protocol["execution_time_budget_seconds"]}
    totals = {
        "max_turns": sum(h["actual_facts"]["turns"] for h in hosts),
        "max_output_tokens": sum(h["actual_facts"]["output_tokens"] for h in hosts),
        "max_seconds": (timestamp(hosts[-1]["completed_at"]) - timestamp(hosts[0]["started_at"])).total_seconds(),
    }
    full = len(hosts) == required
    if (totals["max_seconds"] >= budget["max_seconds"]
            or any(value > budget[key] or (not full and value == budget[key]) for key, value in totals.items())):
        return "post-call-failed"
    return "completed" if full else "in-progress"


def _inspect(inputs, context, preflight, case, arm_id, slot, entry):
    """Derive lifecycle and retry class only after independent receipt replay."""
    destination = _destination(inputs, case, slot)
    require(entry["slot"] == slot and entry["arm_id"] == arm_id,
            "Harness planned slot/arm substitution")
    require(inputs.read(entry["started_ref"]) == {"block_index": entry["block_index"],
            "arm_id": arm_id, "slot": plain(slot)}, "Harness started marker differs from retained Attempt")
    if arm_id in BASELINE_ARMS:
        require(len(entry["receipts"]) == 1, "baseline requires exactly one Receipt")
        envelope_ref = entry["envelope_ref"]
        require(inputs.read(envelope_ref) == _envelope(inputs, context, preflight, case, arm_id, slot),
                "Harness baseline envelope differs from frozen plan")
        receipt_ref = entry["receipts"][0]
        require(receipt_ref["path"] == (destination / "receipt.json").relative_to(inputs.root).as_posix(),
                "Harness baseline Receipt path substitution")
        receipt = verify_baseline_receipt(inputs.root, receipt_ref,
            expected_envelope_ref=envelope_ref, schema_root=inputs.catalog.root)
        require(receipt["attempt_id"] == slot["attempt_id"], "Harness baseline Attempt substitution")
        require(timestamp(receipt["started_at"]) >= timestamp(context.expected_preflight_checked_at),
                "Harness actual execution precedes preflight")
        for ref in (receipt["trace_index_ref"], receipt["validation_ref"], *receipt["artifact_refs"]):
            require((inputs.root / ref["path"]).resolve().is_relative_to(destination),
                    "Harness baseline output escapes its fresh Attempt")
        lifecycle = receipt["status"]
        retry_class = ("provider-transient" if lifecycle == "post-call-failed"
                       and receipt["reason"] in {"provider-error:transient", "provider-error:rate_limit"} else None)
        return lifecycle, retry_class
    require(entry["envelope_ref"] is None, "M11 arm cannot substitute a baseline envelope")
    slices = _slices(inputs, preflight, case, arm_id)
    require(0 < len(entry["receipts"]) <= len(slices), "Harness slice coverage mismatch")
    lifecycle = "in-progress"
    for index, receipt_ref in enumerate(entry["receipts"]):
        require(lifecycle == "in-progress", "Harness continued after a failed capability slice or exhausted budget")
        replay_slice(inputs, slices[index], receipt_ref,
            attempt_id=f"{slot['attempt_id']}-S{index}", destination=destination / str(index),
            skill=arm_id == "mode-candidate-skill", not_before=context.expected_preflight_checked_at)
        lifecycle = _m11_progress(inputs, context, entry["receipts"][:index + 1], len(slices))
    require(lifecycle != "in-progress", "Harness completed arm omits required slices")
    return lifecycle, None


def _can_retry(plan, slot, lifecycle, retry_class):
    policy = plan["design"]["retry"]
    return (lifecycle == "post-call-failed" and retry_class in policy["eligible_failures"]
            and slot["retry_index"] < policy["max_retries"])


def execute_harness(inputs: EvaluationInputs, *, context: HarnessContext, ports: HarnessPorts,
                    clock, admission_verifier, monotonic_clock=time.monotonic):
    """Execute frozen complete blocks, stopping at the first nonretryable failure.

    Every started slot is reserved before dispatch. An unexpected exception leaves
    an unfinished journal and all available runtime evidence; it cannot produce a
    replay-valid completed run. Reusing the run identity or an Attempt is refused.
    """
    plan, preflight = _context(inputs, context, admission_verifier)
    directory = _archive(inputs, context)
    directory.mkdir(parents=True, exist_ok=False)
    persist(inputs.root, directory / "context.json", vars(context))
    entries, instances = [], []

    def fresh(factory, *args):
        instance = factory(*args)
        require(not any(instance is prior for prior in instances), "Harness requires fresh Provider/Driver instances")
        instances.append(instance)
        return instance

    for block_index, block in enumerate(plan["blocks"]):
        case = next(c for c in plan["cases"] if c["case_id"] == block["case_id"])
        for arm in block["arms"]:
            arm_id = arm["arm_id"]
            retry_index = 0
            while True:
                slot = arm["attempt_slots"][retry_index]
                require(timestamp(clock.now().isoformat()) >= timestamp(context.expected_preflight_checked_at),
                        "Harness execution clock precedes preflight")
                inputs.recheck()
                destination = _destination(inputs, case, slot)
                require(not destination.exists(), "Harness Attempt already exists")
                identity = {"block_index": block_index, "arm_id": arm_id, "slot": plain(slot)}
                sequence = len(entries)
                started_ref = persist(inputs.root, directory / f"{sequence:06d}-started.json", identity)
                entry = {**identity, "receipts": [], "envelope_ref": None, "started_ref": started_ref}
                if arm_id in BASELINE_ARMS:
                    entry["envelope_ref"] = persist(inputs.root, directory / f"{sequence:06d}-envelope.json",
                        _envelope(inputs, context, preflight, case, arm_id, slot))
                    result = run_baseline_session(inputs.root, envelope_ref=entry["envelope_ref"],
                        expected_protocol_ref=context.expected_protocol_ref,
                        provider=fresh(ports.baseline_provider),
                        tools=ports.baseline_tools if arm_id == "plain-agent-tool" else (),
                        attempt_path=destination.relative_to(inputs.root).as_posix(), attempt_id=slot["attempt_id"],
                        receipt_id="RECEIPT-" + slot["attempt_id"], clock=monotonic_clock,
                        utc_clock=lambda: clock.now().isoformat(), schema_root=inputs.catalog.root)
                    entry["receipts"].append(result["receipt_ref"])
                else:
                    destination.mkdir(parents=True, exist_ok=False)
                    skill = arm_id == "mode-candidate-skill"
                    slices = _slices(inputs, preflight, case, arm_id)
                    for index, binding in enumerate(slices):
                        inputs.recheck()
                        receipt_ref = execute_slice(inputs, binding, attempt_id=f"{slot['attempt_id']}-S{index}",
                            destination=destination / str(index), clock=clock, skill=skill,
                            driver_factory=lambda *args: fresh(ports.skill_driver if skill else ports.core_driver, *args))
                        entry["receipts"].append(receipt_ref)
                        replay_slice(inputs, binding, receipt_ref,
                            attempt_id=f"{slot['attempt_id']}-S{index}", destination=destination / str(index), skill=skill,
                            not_before=context.expected_preflight_checked_at)
                        lifecycle = _m11_progress(inputs, context, entry["receipts"], len(slices))
                        if lifecycle in {"post-call-failed", "preflight-blocked"}:
                            break
                lifecycle, retry_class = _inspect(inputs, context, preflight, case, arm_id, slot, entry)
                entry.update(lifecycle=lifecycle, retry_class=retry_class)
                entries.append(persist(inputs.root, directory / f"{sequence:06d}-finished.json", entry))
                if lifecycle == "completed":
                    break
                if not _can_retry(plan, slot, lifecycle, retry_class):
                    return _finish(inputs, context, directory, entries, "stopped")
                retry_index += 1
    return _finish(inputs, context, directory, entries, "completed")


def _finish(inputs, context, directory, entries, status):
    result = {"schema_version": "0.1.0", "record_kind": KIND, "version": "1.0.0",
              "context": plain(vars(context)), "attempt_refs": entries, "status": status,
              "context_ref": reference(inputs.root, directory / "context.json"),
              "boundaries": dict(BOUNDARIES)}
    inputs.validate(KIND, result)
    inputs.recheck()
    return persist(inputs.root, directory / "result.json", result)


def replay_harness(inputs: EvaluationInputs, result_ref, *, context: HarnessContext, admission_verifier):
    """Cold file replay: no port factories, Provider/Tool, Driver or checker execution."""
    plan, preflight = _context(inputs, context, admission_verifier)
    document = inputs.read(result_ref, KIND)
    require(document["context"] == plain(vars(context)), "Harness result outer context substitution")
    directory = _archive(inputs, context)
    require(document["context_ref"]["path"] == (directory / "context.json").relative_to(inputs.root).as_posix()
            and inputs.read(document["context_ref"]) == plain(vars(context)),
            "Harness retained context substitution")
    require(result_ref["path"] == (directory / "result.json").relative_to(inputs.root).as_posix(),
            "Harness result path substitution")
    refs = document["attempt_refs"]
    require(len(list(directory.glob("*-started.json"))) == len(refs)
            == len(list(directory.glob("*-finished.json"))), "Harness omitted or unfinished Attempt")
    cursor, stopped = 0, False
    for block_index, block in enumerate(plan["blocks"]):
        case = next(c for c in plan["cases"] if c["case_id"] == block["case_id"])
        for arm in block["arms"]:
            retry_index = 0
            while True:
                slot = arm["attempt_slots"][retry_index]
                require(cursor < len(refs), "Harness dropped a scheduled or failed Attempt")
                ref = refs[cursor]
                require(ref["path"] == (directory / f"{cursor:06d}-finished.json").relative_to(inputs.root).as_posix(),
                        "Harness journal order substitution")
                entry = inputs.read(ref)
                require(set(entry) == {"block_index", "arm_id", "slot", "receipts", "envelope_ref",
                                       "started_ref", "lifecycle", "retry_class"}, "Harness Attempt fields differ")
                require(entry["started_ref"]["path"] ==
                        (directory / f"{cursor:06d}-started.json").relative_to(inputs.root).as_posix(),
                        "Harness started marker order substitution")
                require(entry["block_index"] == block_index, "Harness block substitution")
                lifecycle, retry_class = _inspect(inputs, context, preflight, case, arm["arm_id"], slot, entry)
                require((entry["lifecycle"], entry["retry_class"]) == (lifecycle, retry_class),
                        "Harness self-reported lifecycle/retry differs from actual receipts")
                cursor += 1
                if lifecycle == "completed":
                    break
                if not _can_retry(plan, slot, lifecycle, retry_class):
                    stopped = True
                    break
                retry_index += 1
            if stopped:
                break
        if stopped:
            break
    require(cursor == len(refs), "Harness contains unscheduled Attempts after stopping")
    require(document["status"] == ("stopped" if stopped else "completed"), "Harness run status substitution")
    inputs.recheck()
    return document
