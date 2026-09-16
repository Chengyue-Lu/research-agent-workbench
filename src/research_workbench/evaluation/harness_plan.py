"""Deterministic evaluation-owned schedules; compiling never starts an arm."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from research_workbench.evaluation.manifest import PHASE_D_ARMS, compile_baseline_plan
from research_workbench.evaluation.pins import (
    EvaluationInputs,
    digest,
    file_ref,
    require,
    timestamp,
)
from research_workbench.evaluation.system_protocol import validate_protocol
from research_workbench.execution.baseline_envelope import compile_baseline_envelope

KIND = "evaluation_harness_plan"
ALGORITHM = "sha256-arm-order-v1"
MAX_PLANNED_ATTEMPTS = 100_000
BOUNDARIES = {
    "runtime_input": False,
    "execution_authority": False,
    "actual_execution": False,
    "supply_selection": False,
    "human_decision": False,
    "task_completion": False,
}


def validate_request(
    inputs: EvaluationInputs, kind: str, request: Mapping[str, Any]
) -> None:
    schema = inputs.catalog.schema_for_kind(kind)
    registry = Registry().with_resources(
        (item["$id"], Resource.from_contents(item))
        for item in (inputs.catalog.schema(name) for name in inputs.catalog.names)
    )
    validator = Draft202012Validator(
        {"$ref": f"{schema['$id']}#/$defs/request"},
        registry=registry,
        format_checker=FormatChecker(),
    )
    errors = list(validator.iter_errors(request))
    require(
        not errors,
        "invalid Harness request: " + "; ".join(e.message for e in errors[:3]),
    )


def compile_harness_plan(
    inputs: EvaluationInputs,
    *,
    protocol_ref: Mapping[str, Any],
    case_closure_ref: Mapping[str, Any],
    case_selection_frozen_at: str,
    public_cases: Sequence[Mapping[str, Any]],
    plan_id: str,
    run_id: str,
) -> dict[str, Any]:
    """Freeze a schedule with reserved identities, not allocated sessions.

    ``run_id`` is supplied by the caller for one future execution. Recompiling
    the same input is reproducible; it does not authorize reusing that run.
    Public case projections must already be in the frozen Manifest context.
    """
    request = {
        "protocol_ref": copy.deepcopy(protocol_ref),
        "case_closure_ref": copy.deepcopy(case_closure_ref),
        "case_selection_frozen_at": case_selection_frozen_at,
        "public_cases": copy.deepcopy(list(public_cases)),
        "plan_id": plan_id,
        "run_id": run_id,
    }
    validate_request(inputs, KIND, request)
    protocol = validate_protocol(inputs, protocol_ref)
    require(
        timestamp(protocol["frozen_at"]) <= timestamp(case_selection_frozen_at),
        "case freeze precedes Protocol",
    )
    manifest = inputs.manifest(protocol["manifest_ref"])
    baseline = compile_baseline_plan(manifest)
    closure = inputs.read(case_closure_ref, "evaluation_case_closure")
    require(
        closure["scope"] == "confirmatory",
        "Harness requires the frozen comparison case closure",
    )
    design = protocol["design"]
    require(
        len(closure["cases"]) == design["stopping"]["case_count"],
        "Harness case count differs from Protocol",
    )
    count = (
        len(closure["cases"])
        * (design["replicates_per_case"] + design["pilot_replicates_per_case"])
        * 4
        * (design["retry"]["max_retries"] + 1)
    )
    require(
        count <= MAX_PLANNED_ATTEMPTS, "Harness plan exceeds bounded attempt inventory"
    )
    projections = {c["case_id"]: c["public_payload_ref"] for c in public_cases}
    require(len(projections) == len(public_cases), "duplicate public case identity")
    expected_ids = [case["case"]["identity"] for case in closure["cases"]]
    require(
        len(set(expected_ids)) == len(expected_ids)
        and set(projections) == set(expected_ids),
        "public cases must exactly cover unique frozen cases",
    )

    # Even if mistakenly allowlisted by a Task/context, known private bytes
    # cannot become treatment inputs under another path or identity.
    private_hashes = set()
    private_closures = [closure]
    if protocol["admission_case_closure_ref"] is not None:
        private_closures.append(
            inputs.read(
                protocol["admission_case_closure_ref"], "evaluation_case_closure"
            )
        )
    for private_closure in private_closures:
        for case in private_closure["cases"]:
            for key in ("case", "private_oracle", "checker", "human_adjudication"):
                subject = case[key]
                if subject["state"] == "resolved":
                    private_hashes.add(file_ref(subject["ref"])["sha256"])
    rows = []
    task_pins = {
        digest(file_ref(r)) for r in manifest["frozen_conditions"]["task_packet_refs"]
    }
    used_tasks = set()
    for case in sorted(closure["cases"], key=lambda c: c["case"]["identity"]):
        require(
            case["case"]["state"] == case["task"]["state"] == "resolved"
            and case["task_kind"] == "formal-task",
            "Harness needs resolved case and formal Task identities",
        )
        case_id = case["case"]["identity"]
        case_doc = inputs.read(case["case"]["ref"])
        require(
            case_doc.get("case_id") == case_id
            and all(case_doc.get(k) == v for k, v in case.items() if k != "case"),
            "case commitment differs from frozen closure",
        )
        task_ref = file_ref(case["task"]["ref"])
        task = inputs.read(task_ref, "task_packet")
        require(
            case["task"]["identity"] == f"{task['task_id']}@r{task['revision']}",
            "Harness Task identity mismatch",
        )
        used_tasks.add(digest(task_ref))
        require(digest(task_ref) in task_pins, "Harness Task outside frozen Manifest")
        require(
            bool(case["formal_inputs"])
            and all(i["state"] == "resolved" for i in case["formal_inputs"]),
            "Harness requires resolved formal inputs",
        )
        formal = {digest(file_ref(i["ref"])) for i in case["formal_inputs"]}
        for subject in case["formal_inputs"]:
            inputs.read_bytes(subject["ref"])
        projection_ref = file_ref(projections[case_id])
        projection = inputs.read(projection_ref)
        envelope = compile_baseline_envelope(
            inputs,
            protocol_ref=protocol_ref,
            task_ref=task_ref,
            public_payload_ref=projection_ref,
            arm_id="plain-agent",
            envelope_id="H1-PUBLIC-" + digest(case_id),
            accountable_owner="evaluation-harness",
        )
        public = envelope["provider_visible_payload"]
        require(
            formal == {digest(file_ref(i["ref"])) for i in public["inputs"]},
            "public projection differs from frozen case inputs",
        )
        exposed = [projection_ref, *projection["input_refs"]]
        require(
            not any(file_ref(r)["sha256"] in private_hashes for r in exposed),
            "private evaluation artifact exposed as public input",
        )
        rows.append(
            {
                "case_id": case_id,
                "case_ref": file_ref(case["case"]["ref"]),
                "task_ref": task_ref,
                "public_payload_ref": projection_ref,
                "public_payload_sha256": digest(public),
            }
        )
    require(
        used_tasks == task_pins, "Harness case closure must cover every frozen Task"
    )
    request["public_cases"] = sorted(
        request["public_cases"], key=lambda c: c["case_id"]
    )
    identity = digest(request)
    blocks = []
    for phase, replicates in (
        ("pilot", design["pilot_replicates_per_case"]),
        ("confirmatory", design["replicates_per_case"]),
    ):
        for case in rows:
            for replicate in range(1, replicates + 1):
                key = {
                    "algorithm": ALGORITHM,
                    "seed": design["randomization"]["seed"],
                    "phase": phase,
                    "case_id": case["case_id"],
                    "replicate": replicate,
                }
                order = sorted(
                    PHASE_D_ARMS, key=lambda a: (digest({**key, "arm_id": a}), a)
                )
                arms = []
                for arm_id in order:
                    slots = []
                    for retry in range(design["retry"]["max_retries"] + 1):
                        suffix = digest(
                            {
                                "plan_input_sha256": identity,
                                **key,
                                "arm_id": arm_id,
                                "retry_index": retry,
                            }
                        )
                        slots.append(
                            {
                                "retry_index": retry,
                                "attempt_id": "HA-" + suffix,
                                "session_id": "HS-" + suffix,
                                "activation": (
                                    "initial"
                                    if retry == 0
                                    else "after-eligible-failure"
                                ),
                            }
                        )
                    arms.append({"arm_id": arm_id, "attempt_slots": slots})
                blocks.append(
                    {
                        "phase": phase,
                        "case_id": case["case_id"],
                        "replicate": replicate,
                        "arms": arms,
                    }
                )
    document = {
        "schema_version": "0.1.0",
        "record_kind": KIND,
        "version": "1.0.0",
        "status": "compiled-not-executed",
        "request": request,
        "manifest_ref": file_ref(protocol["manifest_ref"]),
        "plan_input_sha256": identity,
        "frozen_conditions_sha256": baseline["frozen_conditions_sha256"],
        "permutation_algorithm": ALGORITHM,
        "design": copy.deepcopy(design),
        "cases": rows,
        "blocks": blocks,
        "boundaries": dict(BOUNDARIES),
    }
    inputs.validate(KIND, document)
    inputs.recheck()
    return document


def validate_harness_plan(
    inputs: EvaluationInputs,
    document: Mapping[str, Any],
    *,
    expected_protocol_ref: Mapping[str, Any],
    expected_case_closure_ref: Mapping[str, Any],
    case_selection_frozen_at: str,
    expected_run_id: str,
) -> dict[str, Any]:
    """An externally pinned plan is recompiled against caller-owned context."""
    inputs.validate(KIND, document)
    request = document["request"]
    require(
        file_ref(request["protocol_ref"]) == file_ref(expected_protocol_ref)
        and file_ref(request["case_closure_ref"]) == file_ref(expected_case_closure_ref)
        and request["case_selection_frozen_at"] == case_selection_frozen_at
        and request["run_id"] == expected_run_id,
        "Harness outer context substitution",
    )
    expected = compile_harness_plan(inputs, **request)
    require(
        document == expected, "Harness plan differs from deterministic frozen inputs"
    )
    return expected
