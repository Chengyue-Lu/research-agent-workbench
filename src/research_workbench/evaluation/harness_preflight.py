"""Recompute a Harness candidate using M5 contracts; never execute an arm."""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from research_workbench.evaluation.harness_plan import (
    BOUNDARIES,
    validate_harness_plan,
    validate_request,
)
from research_workbench.evaluation.pins import (
    EvaluationInputs,
    digest,
    file_ref,
    require,
    timestamp,
)
from research_workbench.evaluation.system_protocol import validate_protocol
from research_workbench.evaluation.qualification import validate_qualification
from research_workbench.evaluation.overlap import validate_overlap
from research_workbench.evaluation.overlay import AdmissionVerifier, validate_overlay
from research_workbench.evaluation.comparability import validate_comparability
from research_workbench.execution.baseline_envelope import compile_baseline_envelope

KIND = "evaluation_harness_preflight"


def produce_a3_qualification(
    inputs: EvaluationInputs,
    *,
    protocol_ref: Mapping[str, Any],
    qualification_id: str,
    preflight_checked_at: str,
    bindings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Assemble supplied Resolver outputs; select or manufacture no Snapshot."""
    protocol = validate_protocol(inputs, protocol_ref)
    document = {
        "schema_version": "0.1.0",
        "record_kind": "arm_execution_qualification",
        "version": "1.0.0",
        "qualification_id": qualification_id,
        "protocol_ref": file_ref(protocol_ref),
        "manifest_ref": file_ref(protocol["manifest_ref"]),
        "arm_id": "mode-no-skill",
        "producer": "evaluation-harness",
        "checked_at": preflight_checked_at,
        "bindings": copy.deepcopy(list(bindings)),
        "qualified": True,
        "boundaries": copy.deepcopy(
            inputs.catalog.schema_for_kind("arm_execution_qualification")["properties"][
                "boundaries"
            ]["const"]
        ),
    }
    validate_qualification(inputs, document, expected_protocol_ref=protocol_ref)
    return document


def validator_identity(inputs: EvaluationInputs) -> dict[str, Any]:
    """Bind this orchestration and its direct evaluation/transport validators."""
    from research_workbench.evaluation import (
        comparability,
        harness_plan,
        overlap,
        overlay,
        pins,
        qualification,
        system_protocol,
    )
    from research_workbench.execution import baseline_envelope

    files = [
        Path(m.__file__)
        for m in (
            comparability,
            harness_plan,
            overlap,
            overlay,
            pins,
            qualification,
            system_protocol,
            baseline_envelope,
        )
    ]
    files.append(Path(__file__))
    sources = {
        "/".join(p.parts[p.parts.index("research_workbench") :]): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in files
    }
    return {
        "identity": "evaluation-harness-preflight",
        "version": "1.0.0",
        "sources": dict(sorted(sources.items())),
        "schemas_sha256": digest(inputs.schema_hashes),
    }


def _fresh(chains: Sequence[Mapping[str, Any]], checked_at: str) -> None:
    for chain in chains:
        availability = chain["selected_supply_report"]["availability"]
        require(
            timestamp(availability["observed_at"])
            <= timestamp(checked_at)
            <= timestamp(availability["valid_until"]),
            "Harness runtime availability is stale or future",
        )


def compile_harness_preflight(
    inputs: EvaluationInputs,
    *,
    plan_ref: Mapping[str, Any],
    expected_protocol_ref: Mapping[str, Any],
    expected_case_closure_ref: Mapping[str, Any],
    case_selection_frozen_at: str,
    expected_run_id: str,
    preflight_id: str,
    preflight_checked_at: str,
    a2_qualification_ref: Mapping[str, Any],
    a3_qualification_ref: Mapping[str, Any],
    overlap_ref: Mapping[str, Any],
    case_bindings: Sequence[Mapping[str, Any]],
    admission_verifier: AdmissionVerifier | None = None,
) -> dict[str, Any]:
    """Check exact qualifications/lineage independently of declared outcomes.

    Valid overlap downgrades confirmatory eligibility. Unresolved overlap or
    missing trusted admission verification blocks this four-arm preflight.
    Caller time is explicit; a saved result never becomes live authorization.
    """
    request = {
        "plan_ref": copy.deepcopy(plan_ref),
        "preflight_id": preflight_id,
        "preflight_checked_at": preflight_checked_at,
        "a2_qualification_ref": copy.deepcopy(a2_qualification_ref),
        "a3_qualification_ref": copy.deepcopy(a3_qualification_ref),
        "overlap_ref": copy.deepcopy(overlap_ref),
        "case_bindings": copy.deepcopy(list(case_bindings)),
    }
    validate_request(inputs, KIND, request)
    plan = validate_harness_plan(
        inputs,
        inputs.read(plan_ref, "evaluation_harness_plan"),
        expected_protocol_ref=expected_protocol_ref,
        expected_case_closure_ref=expected_case_closure_ref,
        case_selection_frozen_at=case_selection_frozen_at,
        expected_run_id=expected_run_id,
    )
    require(
        timestamp(preflight_checked_at) >= timestamp(case_selection_frozen_at),
        "preflight precedes frozen case selection",
    )
    require(
        callable(admission_verifier),
        "Harness needs an externally supplied admission verifier",
    )
    initial_validator = validator_identity(inputs)
    qualifications = {}
    for arm_id, reference in (
        ("plain-agent-tool", a2_qualification_ref),
        ("mode-no-skill", a3_qualification_ref),
    ):
        document = inputs.read(reference, "arm_execution_qualification")
        require(document["arm_id"] == arm_id, "Harness qualification arm substitution")
        require(
            timestamp(document["checked_at"]) <= timestamp(preflight_checked_at),
            "Harness qualification is from the future",
        )
        chains = validate_qualification(
            inputs, document, expected_protocol_ref=expected_protocol_ref
        )
        _fresh(chains, preflight_checked_at)
        qualifications[arm_id] = {
            "ref": file_ref(reference),
            "bindings_sha256": digest(document["bindings"]),
        }
    overlap = validate_overlap(
        inputs,
        inputs.read(overlap_ref, "admission_evidence_overlap"),
        expected_protocol_ref=expected_protocol_ref,
        expected_case_closure_ref=expected_case_closure_ref,
        case_selection_frozen_at=case_selection_frozen_at,
    )
    require(overlap["overlap_status"] != "unresolved", "Harness overlap is unresolved")
    by_case = {b["case_id"]: b for b in case_bindings}
    require(
        len(by_case) == len(case_bindings)
        and set(by_case) == {c["case_id"] for c in plan["cases"]},
        "preflight bindings must exactly cover unique planned cases",
    )
    cases = []
    for case in plan["cases"]:
        binding = by_case[case["case_id"]]
        overlay = inputs.read(binding["a4_overlay_ref"], "a4_execution_qualification")
        require(
            file_ref(overlay["task_ref"]) == case["task_ref"],
            "Harness overlay Task substitution",
        )
        require(
            file_ref(overlay["admission_overlap_assessment_ref"])
            == file_ref(overlap_ref),
            "Harness overlay overlap substitution",
        )
        require(
            timestamp(overlay["checked_at"]) <= timestamp(preflight_checked_at),
            "Harness overlay is from the future",
        )
        a4 = validate_overlay(
            inputs,
            overlay,
            expected_protocol_ref=expected_protocol_ref,
            expected_case_closure_ref=expected_case_closure_ref,
            case_selection_frozen_at=case_selection_frozen_at,
            admission_verifier=admission_verifier,
        )
        _fresh(a4, preflight_checked_at)
        pairwise = inputs.read(binding["pairwise_ref"], "a3_a4_pairwise_comparability")
        require(
            pairwise["stage"] == "plan-pre-run",
            "Harness requires pre-run pairwise evidence",
        )
        require(
            file_ref(pairwise["a3_qualification_ref"]) == file_ref(a3_qualification_ref)
            and file_ref(pairwise["a4_overlay_ref"])
            == file_ref(binding["a4_overlay_ref"]),
            "Harness pairwise qualification/overlay substitution",
        )
        require(
            timestamp(pairwise["checked_at"]) <= timestamp(preflight_checked_at),
            "Harness pairwise record is from the future",
        )
        comparison = validate_comparability(
            inputs,
            pairwise,
            expected_protocol_ref=expected_protocol_ref,
            expected_case_closure_ref=expected_case_closure_ref,
            case_selection_frozen_at=case_selection_frozen_at,
            admission_verifier=admission_verifier,
        )
        payloads = {}
        for arm_id in ("plain-agent", "plain-agent-tool"):
            envelope = compile_baseline_envelope(
                inputs,
                protocol_ref=expected_protocol_ref,
                task_ref=case["task_ref"],
                public_payload_ref=case["public_payload_ref"],
                arm_id=arm_id,
                envelope_id="H2-" + digest([case["case_id"], arm_id]),
                accountable_owner="evaluation-harness",
                qualification_ref=(
                    a2_qualification_ref if arm_id == "plain-agent-tool" else None
                ),
            )
            payloads[arm_id] = digest(envelope["provider_visible_payload"])
        require(
            payloads["plain-agent"] == case["public_payload_sha256"],
            "Harness public payload drift",
        )
        cases.append(
            {
                "case_id": case["case_id"],
                "comparison": copy.deepcopy(comparison),
                "baseline_payload_sha256": payloads,
                "primary_confirmatory_eligible": overlap[
                    "primary_confirmatory_eligible"
                ],
                "pilot_primary_eligible": False,
            }
        )
    request["case_bindings"] = sorted(
        request["case_bindings"], key=lambda b: b["case_id"]
    )
    require(
        validator_identity(inputs) == initial_validator,
        "Harness validator changed during preflight",
    )
    result = {
        "schema_version": "0.1.0",
        "record_kind": KIND,
        "version": "1.0.0",
        "status": "preflight-checked",
        "request": request,
        "validator": initial_validator,
        "qualifications": qualifications,
        "overlap": copy.deepcopy(dict(overlap)),
        "cases": cases,
        "boundaries": dict(BOUNDARIES),
    }
    inputs.validate(KIND, result)
    inputs.recheck()
    return result


def validate_harness_preflight(
    inputs: EvaluationInputs,
    document: Mapping[str, Any],
    *,
    expected_plan_ref: Mapping[str, Any],
    expected_protocol_ref: Mapping[str, Any],
    expected_case_closure_ref: Mapping[str, Any],
    case_selection_frozen_at: str,
    expected_run_id: str,
    expected_preflight_checked_at: str,
    admission_verifier: AdmissionVerifier | None = None,
) -> dict[str, Any]:
    """Recheck a hash-pinned record; caller owns plan, time and admission trust."""
    inputs.validate(KIND, document)
    request = document["request"]
    require(
        file_ref(request["plan_ref"]) == file_ref(expected_plan_ref)
        and request["preflight_checked_at"] == expected_preflight_checked_at,
        "Harness preflight outer plan/time substitution",
    )
    expected = compile_harness_preflight(
        inputs,
        **request,
        expected_protocol_ref=expected_protocol_ref,
        expected_case_closure_ref=expected_case_closure_ref,
        case_selection_frozen_at=case_selection_frozen_at,
        expected_run_id=expected_run_id,
        admission_verifier=admission_verifier,
    )
    require(
        document == expected, "Harness preflight differs from independent recomputation"
    )
    return expected
