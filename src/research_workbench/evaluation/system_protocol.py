"""M5-006 preregistered system estimand and measurement contracts."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import Any

from research_workbench.evaluation.manifest import FIXED_METRIC_BY_ID
from research_workbench.evaluation.pins import (
    EvaluationInputs,
    digest,
    file_ref,
    require,
    sha,
    timestamp,
)


def validate_protocol(
    inputs: EvaluationInputs, reference: Mapping[str, Any]
) -> Mapping[str, Any]:
    cache_key = digest(file_ref(reference))
    if cache_key in inputs.protocol_cache:
        inputs.recheck()
        return copy.deepcopy(inputs.protocol_cache[cache_key])
    protocol = inputs.read(reference, "system_evaluation_protocol")
    require(
        protocol["purpose"] != "confirmatory-protocol"
        or protocol["admission_case_closure_ref"] is not None,
        "confirmatory Protocol requires a frozen admission case closure",
    )
    inputs.read_bytes(protocol["decision_ref"])
    manifest = inputs.manifest(protocol["manifest_ref"])
    validate_frozen_binding(protocol["execution_binding"], manifest)
    if protocol["admission_case_closure_ref"] is not None:
        closure = inputs.read(
            protocol["admission_case_closure_ref"], "evaluation_case_closure"
        )
        require(
            closure["scope"] == "admission",
            "Protocol requires an admission-scoped case closure",
        )
    modes = [inputs.read(ref, "research_mode") for ref in protocol["mode_documents"]]
    require(
        sorted(f"{m['mode_id']}@{m['version']}" for m in modes)
        == sorted(
            {
                mode
                for treatment in manifest["arms"]
                for mode in treatment["treatment_control"].get("mode_refs", [])
            }
        ),
        "Protocol Mode closure mismatch",
    )
    actions = {}
    for ref in protocol["action_documents"]:
        action = inputs.read(ref, "mode_action")
        identity = f"{action['action_id']}@{action['version']}"
        require(identity not in actions, "duplicate Protocol Action identity")
        actions[identity] = file_ref(ref)["sha256"]
    expected_actions = {}
    for treatment in manifest["arms"]:
        for ref in treatment["treatment_control"].get("method_resolution_refs", []):
            method = inputs.read(ref, "method_resolution")
            for decision in method["action_decisions"]:
                if "action_ref" in decision:
                    expected_actions[decision["action_ref"]] = sha(
                        decision["action_content_hash"]
                    )
    require(
        actions == expected_actions,
        "Protocol Action bytes differ from frozen Method closure",
    )
    expected = sorted(
        (treatment["arm_id"], digest(file_ref(ref)))
        for treatment in manifest["arms"]
        if treatment["arm_id"] in {"plain-agent-tool", "mode-no-skill"}
        for ref in treatment.get("capability_snapshot_refs", [])
    )
    actual = sorted(
        (binding["arm_id"], digest(file_ref(binding["snapshot_ref"])))
        for binding in protocol["execution_bindings"]
    )
    require(
        expected == actual,
        "Protocol must cover every A2/A3 frozen binding exactly once",
    )
    from research_workbench.evaluation.qualification import (
        snapshot_chain,
        validate_implementation,
    )

    for binding in protocol["execution_bindings"]:
        validate_implementation(
            inputs, binding, snapshot_chain(inputs, binding["snapshot_ref"])
        )
    design = protocol["design"]
    require(
        design["stopping"]["completed_blocks"]
        == design["stopping"]["case_count"] * design["replicates_per_case"],
        "stopping blocks must equal case count times confirmatory replicates",
    )
    require(
        bool(design["retry"]["eligible_failures"])
        == (design["retry"]["max_retries"] > 0),
        "retry limit and eligible failures disagree",
    )
    timestamp(protocol["frozen_at"])
    inputs.recheck()
    inputs.protocol_cache[cache_key] = copy.deepcopy(protocol)
    return protocol


def validate_frozen_binding(
    binding: Mapping[str, Any], manifest: Mapping[str, Any]
) -> None:
    frozen = manifest["frozen_conditions"]
    for actual, expected, label in (
        (binding["model"]["ref"], frozen["model"]["model_id"], "model"),
        (binding["model"]["slot"], frozen["model"]["slot_id"], "model slot"),
        (binding["adapter"]["ref"], frozen["model"]["provider_adapter"], "adapter"),
        (binding["host"]["ref"], frozen["host"]["host_id"], "Host"),
        (binding["runtime"]["ref"], frozen["host"]["runtime"], "Runtime"),
    ):
        require(actual == expected, f"frozen {label} mismatch")


def validate_view_shared_conditions(
    view: Mapping[str, Any], manifest: Mapping[str, Any], protocol: Mapping[str, Any]
) -> None:
    require(
        digest(view["binding"]) == digest(protocol["execution_binding"]),
        "View frozen execution binding mismatch",
    )
    frozen = manifest["frozen_conditions"]
    expected_budget = {
        key: frozen["budget"][key] for key in ("max_turns", "max_output_tokens")
    }
    expected_budget["max_seconds"] = protocol["execution_time_budget_seconds"]
    require(
        dict(view["effective_constraints"]["budget"]) == expected_budget,
        "View frozen budget mismatch",
    )


def validate_measurement(
    inputs: EvaluationInputs,
    document: Mapping[str, Any],
    *,
    expected_protocol_ref: Mapping[str, Any],
) -> Mapping[str, Any]:
    inputs.validate("evaluation_measurement", document)
    require(
        file_ref(document["protocol_ref"]) == file_ref(expected_protocol_ref),
        "measurement protocol substitution",
    )
    validate_protocol(inputs, expected_protocol_ref)
    metric = FIXED_METRIC_BY_ID[document["metric_id"]]
    units = {"characters-or-tokens": {"characters", "tokens"}}
    require(
        bool(re.fullmatch(r"[A-Z]{3}", document["unit"]))
        if metric.unit == "currency"
        else document["unit"] in units.get(metric.unit, {metric.unit}),
        "measurement unit does not match metric",
    )
    value = document["value"]
    if value is not None:
        require(metric.unit != "ratio" or value <= 1, "ratio measurement exceeds one")
        require(
            metric.unit != "count" or value % 1 == 0,
            "count measurement must be integral",
        )
    for ref in document["evidence_refs"]:
        inputs.read_bytes(ref)
    inputs.recheck()
    return document
