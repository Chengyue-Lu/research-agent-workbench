"""Three-state A3/A4 comparison of reloaded qualified execution surfaces."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from research_workbench.evaluation.overlay import AdmissionVerifier, validate_overlay
from research_workbench.evaluation.pins import (
    EvaluationInputs,
    digest,
    file_ref,
    require,
    timestamp,
)
from research_workbench.evaluation.qualification import validate_qualification
from research_workbench.evaluation.system_protocol import (
    validate_protocol,
    validate_view_shared_conditions,
)
from research_workbench.execution.host import load_resolved_execution_view
from research_workbench.execution.runtime_bundle import load_runtime_bundle


def comparison_surface(chains: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Keep obligations/order intact; canonicalize only unordered multisets."""
    return {
        "tasks": sorted(digest(c["task"]) for c in chains),
        "methods": sorted(digest(c["method_resolution"]) for c in chains),
        "requirements": sorted(digest(c["requirement"]) for c in chains),
        "non_skill_components": sorted(
            digest(component)
            for c in chains
            for component in c["snapshot"]["supply_identity"]["components"]
            if component["component_kind"] != "skill"
        ),
        "non_skill_supplies": sorted(
            digest(
                {
                    "identity": c["snapshot"]["supply_identity"],
                    "report": c["snapshot"]["selected_supply_report_ref"]["ref"],
                }
            )
            for c in chains
            if c["snapshot"]["supply_identity"]["supply_kind"] != "skill"
        ),
        "interfaces": sorted(
            digest(
                {
                    key: c["interface"][key]
                    for key in (
                        "provider_visible_interface",
                        "supported_inputs",
                        "supported_outputs",
                        "provided_capabilities",
                    )
                }
            )
            for c in chains
        ),
        "supply_boundaries": sorted(
            digest(
                {
                    key: c["snapshot"][key]
                    for key in (
                        "supply_required_permissions",
                        "supply_data_egress",
                        "supply_side_effects",
                    )
                }
            )
            for c in chains
        ),
        "execution_bindings": sorted(digest(c["view"]["binding"]) for c in chains),
        "execution_constraints": sorted(
            digest(
                {
                    key: c["view"][key]
                    for key in (
                        "effective_constraints",
                        "profile_constraints",
                        "required_outputs",
                        "completion_checks",
                        "safe_pause_conditions",
                        "stop_conditions",
                    )
                }
            )
            for c in chains
        ),
    }


def derive_comparability(
    a3: Mapping[str, Any], a4: Mapping[str, Any], *, admitted_skill_count: int
) -> dict[str, Any]:
    """Pure comparison does not establish the supplied surfaces' eligibility."""
    keys = {
        "tasks",
        "methods",
        "requirements",
        "non_skill_components",
        "non_skill_supplies",
        "interfaces",
        "supply_boundaries",
        "execution_bindings",
        "execution_constraints",
    }
    require(set(a3) == set(a4) == keys, "incomplete pairwise comparison surface")
    mismatches = sorted(key for key in keys if a3[key] != a4[key])
    if admitted_skill_count != 1:
        mismatches.append("admitted-skill-extension-count")
    if any(
        not a3[key] or not a4[key]
        for key in keys - {"non_skill_components", "non_skill_supplies"}
    ):
        mismatches.append("incomplete-surface")
    if any(
        key in mismatches
        for key in (
            "tasks",
            "execution_bindings",
            "incomplete-surface",
            "admitted-skill-extension-count",
        )
    ):
        status, interpretation = "not-comparable", "unavailable"
    elif mismatches:
        status, interpretation = "skill-bearing-package", "skill-bearing-package-effect"
    else:
        status, interpretation = "exact-skill-only", "skill-conditional-increment"
    return {
        "status": status,
        "interpretation": interpretation,
        "mismatches": sorted(mismatches),
        "comparison_digest": digest(
            {"a3": a3, "a4": a4, "admitted_skill_count": admitted_skill_count}
        ),
    }


def validate_comparability(
    inputs: EvaluationInputs,
    document: Mapping[str, Any],
    *,
    expected_protocol_ref: Mapping[str, Any],
    expected_case_closure_ref: Mapping[str, Any] | None = None,
    case_selection_frozen_at: str | None = None,
    admission_verifier: AdmissionVerifier | None = None,
) -> Mapping[str, Any]:
    inputs.validate("a3_a4_pairwise_comparability", document)
    require(
        file_ref(document["protocol_ref"]) == file_ref(expected_protocol_ref),
        "pairwise Protocol substitution",
    )
    qualification = inputs.read(
        document["a3_qualification_ref"], "arm_execution_qualification"
    )
    require(
        qualification["arm_id"] == "mode-no-skill", "pairwise A3 qualification required"
    )
    a3 = validate_qualification(
        inputs, qualification, expected_protocol_ref=expected_protocol_ref
    )
    overlay = inputs.read(document["a4_overlay_ref"], "a4_execution_qualification")
    a4 = validate_overlay(
        inputs,
        overlay,
        expected_protocol_ref=expected_protocol_ref,
        expected_case_closure_ref=expected_case_closure_ref,
        case_selection_frozen_at=case_selection_frozen_at,
        admission_verifier=admission_verifier,
    )
    require(
        file_ref(document["manifest_ref"])
        == file_ref(qualification["manifest_ref"])
        == file_ref(overlay["manifest_ref"]),
        "pairwise Manifest substitution",
    )
    require(
        file_ref(document["case_closure_ref"]) == file_ref(overlay["case_closure_ref"]),
        "pairwise case closure substitution",
    )
    require(
        timestamp(document["checked_at"])
        >= max(
            timestamp(qualification["checked_at"]), timestamp(overlay["checked_at"])
        ),
        "pairwise check precedes qualification",
    )
    bindings = document["a3_runtime_bindings"]
    require(
        sorted(digest(file_ref(b["snapshot_ref"])) for b in bindings)
        == sorted(
            digest(file_ref(b["runtime_snapshot_ref"]))
            for b in qualification["bindings"]
        ),
        "pairwise A3 Snapshot coverage mismatch",
    )
    for chain, qualified_binding in zip(a3, qualification["bindings"]):
        binding = next(
            b
            for b in bindings
            if file_ref(b["snapshot_ref"])
            == file_ref(qualified_binding["runtime_snapshot_ref"])
        )
        inputs.read_bytes(binding["bundle_ref"])
        bundle = load_runtime_bundle(
            binding["bundle_ref"]["path"],
            project_root=inputs.root,
            schema_root=inputs.catalog.root,
        )
        require(
            bundle.manifest_sha256 == binding["bundle_ref"]["sha256"]
            and file_ref(bundle.manifest["entrypoint"])
            == file_ref(binding["snapshot_ref"]),
            "pairwise A3 Bundle substitution",
        )
        view = load_resolved_execution_view(
            binding["view_ref"]["path"],
            expected_sha256=binding["view_ref"]["sha256"],
            bundle=bundle,
            schema_root=inputs.catalog.root,
        )
        chain["view"] = view.document
        protocol = validate_protocol(inputs, expected_protocol_ref)
        validate_view_shared_conditions(
            view.document, inputs.manifest(document["manifest_ref"]), protocol
        )
    count = sum(
        component["component_kind"] == "skill"
        for c in a4
        for component in c["snapshot"]["supply_identity"]["components"]
    )
    result = derive_comparability(
        comparison_surface(a3), comparison_surface(a4), admitted_skill_count=count
    )
    require(
        document["result"] == result, "pairwise result/interpretation/mismatch drift"
    )
    if document["stage"] == "analysis-input":
        prior = inputs.read(
            document["preregistered_record_ref"], "a3_a4_pairwise_comparability"
        )
        require(
            prior["stage"] == "plan-pre-run",
            "analysis input must reference preregistration",
        )
        prior_result = validate_comparability(
            inputs,
            prior,
            expected_protocol_ref=expected_protocol_ref,
            expected_case_closure_ref=expected_case_closure_ref,
            case_selection_frozen_at=case_selection_frozen_at,
            admission_verifier=admission_verifier,
        )
        for key in (
            "manifest_ref",
            "case_closure_ref",
            "a3_qualification_ref",
            "a4_overlay_ref",
            "a3_runtime_bindings",
        ):
            require(document[key] == prior[key], f"pairwise preregistered {key} drift")
        require(
            timestamp(document["checked_at"]) >= timestamp(prior["checked_at"]),
            "analysis comparison precedes preregistration",
        )
        require(result == prior_result, "preregistered comparison drift")
    inputs.recheck()
    return result
