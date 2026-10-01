"""Evaluation-owned actual evidence, independently rebuilt from H3 archives.

Frozen targets and observations occupy separate fields. An unstarted slot is
not an execution, and a replayable failed Attempt is not a successful result.
This module never calls an execution port or grants analysis eligibility.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from research_workbench.evaluation.harness_execution import (
    BASELINE_ARMS, BOUNDARIES, HarnessContext, _slices, replay_harness,
)
from research_workbench.evaluation.harness_preflight import validator_identity as preflight_identity
from research_workbench.evaluation.harness_runtime import load_slice, plain
from research_workbench.evaluation.pins import EvaluationInputs, file_ref, require
from research_workbench.execution.skill_facts import selected_skill_consumption

KIND = "evaluation_harness_evidence"
LIFECYCLES = {"completed": "completed", "failed": "post-call-failed", "blocked": "preflight-blocked"}


def validator_identity(inputs):
    """Pin H4 derivation, replay entrypoints, and direct baseline replay dependencies."""
    identity = preflight_identity(inputs)
    package = Path(__file__).resolve().parent.parent
    sources = dict(identity["sources"])
    for name in (
        "evaluation/harness_evidence.py", "evaluation/harness_execution.py",
        "evaluation/harness_runtime.py", "execution/baseline_closeout.py",
        "execution/baseline.py", "adapters/models/port.py",
        "execution/generic_closeout.py", "execution/skill_closeout.py",
        "execution/skill_facts.py", "observability/trace.py", "execution/host.py",
        "execution/runtime_bundle.py",
    ):
        sources["research_workbench/" + name] = hashlib.sha256((package / name).read_bytes()).hexdigest()
    return {**identity, "identity": "evaluation-harness-evidence", "sources": dict(sorted(sources.items()))}


def _targets(inputs, preflight, case, arm_id, protocol):
    """Only comparison targets are read from frozen qualification/View inputs."""
    request = preflight["request"]
    if arm_id in BASELINE_ARMS:
        qualification_ref = request["a2_qualification_ref"] if arm_id == "plain-agent-tool" else None
        tools = []
        if qualification_ref is not None:
            for binding in inputs.read(qualification_ref)["bindings"]:
                snapshot = inputs.read(binding["runtime_snapshot_ref"])
                if file_ref(snapshot["task_ref"]) == file_ref(case["task_ref"]):
                    tools.append(file_ref(binding["implementation_ref"]))
        return [{"qualification_ref": qualification_ref, "runtime_binding": None,
                 "binding": protocol["execution_binding"], "supply_report_ref": None,
                 "skill_consumption": None, "tool_implementation_refs": tools}]
    case_binding = next(c for c in request["case_bindings"] if c["case_id"] == case["case_id"])
    skill = arm_id == "mode-candidate-skill"
    targets = []
    for binding in _slices(inputs, preflight, case, arm_id):
        _, view = load_slice(inputs, binding)
        targets.append({
            "qualification_ref": case_binding["a4_overlay_ref"] if skill else request["a3_qualification_ref"],
            "runtime_binding": binding, "binding": plain(view.document["binding"]),
            "supply_report_ref": plain(view.document["selected_supply_report_ref"]),
            "skill_consumption": plain(selected_skill_consumption(view, schema_root=inputs.catalog.root)) if skill else None,
            "tool_implementation_refs": [],
        })
    return targets


def _observation(inputs, receipt_ref, baseline):
    """Read actual fields only after replay has validated their Trace derivation."""
    receipt = inputs.read(receipt_ref)
    if baseline:
        facts = [inputs.read(r, "baseline_execution_fact") for r in receipt["fact_refs"]]
        bindings = [f["binding"] for f in facts if f["operation"] == "provider" and f["phase"] == "after"]
        tools = [file_ref(f["tool_ref"]) for f in facts if f["operation"] == "tool" and f["phase"] == "before"]
        lifecycle = receipt["status"]
        actual = {"binding": receipt["actual_binding"], "binding_observations": bindings,
                  "supply_report_ref": None, "skill_consumption": None, "tool_implementation_refs": tools}
        evidence = {"host_ref": None, "trace_ref": receipt["trace_index_ref"],
                    "fact_refs": receipt["fact_refs"], "artifact_refs": receipt["artifact_refs"],
                    "validation_refs": [receipt["validation_ref"]], "diagnostic": receipt["reason"]}
    else:
        host = inputs.read(receipt["host_report_ref"])
        lifecycle = LIFECYCLES[receipt["status"]]
        actual = {"binding": host.get("actual_binding"),
                  "binding_observations": [host["actual_binding"]] if "actual_binding" in host else [],
                  "supply_report_ref": host.get("actual_supply_report_ref"),
                  "skill_consumption": host.get("actual_skill_consumption"), "tool_implementation_refs": []}
        evidence = {"host_ref": receipt["host_report_ref"], "trace_ref": receipt["trace_ref"],
                    "fact_refs": [], "artifact_refs": [file_ref(r) for r in receipt["artifact_refs"]],
                    "validation_refs": receipt["validation_refs"], "diagnostic": host.get("diagnostic")}
    for ref in [evidence["trace_ref"], *evidence["fact_refs"], *evidence["artifact_refs"], *evidence["validation_refs"]]:
        inputs.read_bytes(ref)
    return lifecycle, None if lifecycle == "preflight-blocked" else actual, evidence


def _comparison(frozen, actual):
    if actual is None or (not actual["binding_observations"] and not actual["tool_implementation_refs"]):
        return "not-observed"
    expected_supply = frozen["supply_report_ref"]
    matches = (
        actual["binding"] == frozen["binding"]
        and all(b == frozen["binding"] for b in actual["binding_observations"])
        and actual["supply_report_ref"] == (expected_supply["ref"] if expected_supply is not None else None)
        and actual["skill_consumption"] == frozen["skill_consumption"]
        and all(t in frozen["tool_implementation_refs"] for t in actual["tool_implementation_refs"])
    )
    return "matches-frozen" if matches else "differs-from-frozen"


def compile_harness_evidence(
    inputs: EvaluationInputs, *, execution_ref, context: HarnessContext, evidence_id: str, admission_verifier,
) -> dict:
    """Replay the externally selected run; retain every planned slot and slice.

    Only H3's executed Attempts acquire receipts/actual observations. Unused
    retry reservations and slots following a stopped run remain not-started.
    The caller supplies admission authority; archives cannot provide it.
    """
    identity = validator_identity(inputs)
    result = replay_harness(inputs, execution_ref, context=context, admission_verifier=admission_verifier)
    plan = inputs.read(context.expected_plan_ref)
    preflight = inputs.read(context.expected_preflight_ref)
    protocol = inputs.read(context.expected_protocol_ref)
    entries = {}
    for ref in result["attempt_refs"]:
        entry = inputs.read(ref)
        entries[entry["slot"]["attempt_id"]] = (ref, entry)
    targets = {}
    slots = []
    for block_index, block in enumerate(plan["blocks"]):
        case = next(c for c in plan["cases"] if c["case_id"] == block["case_id"])
        for arm in block["arms"]:
            arm_id = arm["arm_id"]
            key = (case["case_id"], arm_id)
            if key not in targets:
                targets[key] = _targets(inputs, preflight, case, arm_id, protocol)
            for slot in arm["attempt_slots"]:
                journal_ref, entry = entries.get(slot["attempt_id"], (None, None))
                slices = []
                receipts = entry["receipts"] if entry is not None else []
                for index, frozen in enumerate(targets[key]):
                    receipt_ref = receipts[index] if index < len(receipts) else None
                    lifecycle, actual, evidence = ("not-started", None, None)
                    if receipt_ref is not None:
                        lifecycle, actual, evidence = _observation(inputs, receipt_ref, arm_id in BASELINE_ARMS)
                    comparison = _comparison(frozen, actual)
                    require(lifecycle != "completed" or comparison == "matches-frozen",
                            "completed Harness slice differs from frozen qualification")
                    slices.append({
                        "slice_index": index,
                        "attempt_id": slot["attempt_id"] if arm_id in BASELINE_ARMS else f"{slot['attempt_id']}-S{index}",
                        "frozen": copy.deepcopy(frozen), "lifecycle": lifecycle, "receipt_ref": receipt_ref,
                        "actual": actual, "evidence": evidence, "comparison": comparison,
                    })
                slots.append({"block_index": block_index, "case_id": case["case_id"], "phase": block["phase"],
                              "replicate": block["replicate"], "arm_id": arm_id, "slot": copy.deepcopy(slot),
                              "journal_ref": journal_ref, "lifecycle": entry["lifecycle"] if entry else "not-started",
                              "retry_class": entry["retry_class"] if entry else None, "slices": slices})
    document = {"schema_version": "0.1.0", "record_kind": KIND, "version": "1.0.0", "evidence_id": evidence_id,
                "purpose": "synthetic-contract-proof", "execution_ref": file_ref(execution_ref),
                "context": copy.deepcopy(vars(context)), "validator": identity,
                "execution_status": result["status"], "slots": slots, "boundaries": dict(BOUNDARIES)}
    inputs.validate(KIND, document)
    require(identity == validator_identity(inputs), "Harness evidence validator changed during compilation")
    inputs.recheck()
    return document


def validate_harness_evidence(
    inputs: EvaluationInputs, document, *, expected_execution_ref, context: HarnessContext,
    expected_evidence_id: str, admission_verifier,
) -> dict:
    """Rebuild all summaries under caller-owned pins, never document-owned trust."""
    inputs.validate(KIND, document)
    require(document["execution_ref"] == file_ref(expected_execution_ref)
            and document["context"] == vars(context) and document["evidence_id"] == expected_evidence_id,
            "Harness evidence outer context substitution")
    require(document["validator"] == validator_identity(inputs), "Harness evidence validator identity drift")
    expected = compile_harness_evidence(inputs, execution_ref=expected_execution_ref, context=context,
                                        evidence_id=expected_evidence_id, admission_verifier=admission_verifier)
    require(document == expected, "Harness actual evidence differs from independently replayed execution")
    return expected
