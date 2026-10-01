"""Public M5-006 verification entrypoint; produces evaluation facts, never runs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from research_workbench.evaluation.comparability import validate_comparability
from research_workbench.evaluation.overlap import validate_overlap
from research_workbench.evaluation.overlay import AdmissionVerifier, validate_overlay
from research_workbench.evaluation.pins import EvaluationInputs, file_ref, require
from research_workbench.evaluation.qualification import validate_qualification
from research_workbench.evaluation.system_protocol import (
    validate_measurement,
    validate_protocol,
)


def verify_evaluation_record(
    root: str | Path,
    reference: Mapping[str, Any],
    *,
    expected_protocol_ref: Mapping[str, Any] | None = None,
    expected_case_closure_ref: Mapping[str, Any] | None = None,
    case_selection_frozen_at: str | None = None,
    admission_verifier: AdmissionVerifier | None = None,
    schema_root: str | Path | None = None,
) -> dict[str, Any]:
    """Recompute one externally hash-pinned record and its bounded closure.

    Consumers must separately require confirmatory eligibility / actual replay
    evidence. A valid unresolved overlap record remains ineligible. The optional
    admission verifier belongs to the authorized caller, never to record data.
    """
    inputs = EvaluationInputs(root, schema_root)
    document = inputs.read(reference)
    kind = document.get("record_kind")
    result: Mapping[str, Any]
    if kind == "system_evaluation_protocol":
        require(
            expected_protocol_ref is None
            or file_ref(expected_protocol_ref) == file_ref(reference),
            "Protocol outer pin mismatch",
        )
        validate_protocol(inputs, reference)
        result = {"protocol_id": document["protocol_id"], "primary": "A4-A2"}
    else:
        require(
            expected_protocol_ref is not None,
            "externally selected Protocol reference required",
        )
        if kind == "arm_execution_qualification":
            chains = validate_qualification(
                inputs, document, expected_protocol_ref=expected_protocol_ref
            )
            result = {
                "qualified": True,
                "arm_id": document["arm_id"],
                "binding_count": len(chains),
            }
        elif kind == "admission_evidence_overlap":
            require(
                expected_case_closure_ref is not None
                and case_selection_frozen_at is not None,
                "externally frozen case closure and freeze time required",
            )
            result = validate_overlap(
                inputs,
                document,
                expected_protocol_ref=expected_protocol_ref,
                expected_case_closure_ref=expected_case_closure_ref,
                case_selection_frozen_at=case_selection_frozen_at,
            )
        elif kind == "a4_execution_qualification":
            chains = validate_overlay(
                inputs,
                document,
                expected_protocol_ref=expected_protocol_ref,
                expected_case_closure_ref=expected_case_closure_ref,
                case_selection_frozen_at=case_selection_frozen_at,
                admission_verifier=admission_verifier,
            )
            result = {
                "binding_count": len(chains),
                "evidence_phase": "pre-run-qualification",
                "primary_confirmatory_eligible": document[
                    "primary_confirmatory_eligible"
                ],
            }
        elif kind == "a3_a4_pairwise_comparability":
            result = validate_comparability(
                inputs,
                document,
                expected_protocol_ref=expected_protocol_ref,
                expected_case_closure_ref=expected_case_closure_ref,
                case_selection_frozen_at=case_selection_frozen_at,
                admission_verifier=admission_verifier,
            )
        elif kind == "evaluation_measurement":
            validate_measurement(
                inputs, document, expected_protocol_ref=expected_protocol_ref
            )
            result = {
                "metric_id": document["metric_id"],
                "measurement_status": document["status"],
            }
        else:
            require(False, f"unsupported evaluation record: {kind}")
    inputs.recheck()
    return {
        "record_kind": kind,
        "validation": "valid",
        "execution_authority": False,
        "result": dict(result),
    }
