"""Evaluation-side pre-run Skill lineage; external Human admission stays external."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from research_workbench.capability.lifecycle import (
    SkillLifecycleEntry,
    SkillLifecycleRecord,
)
from research_workbench.capability.models import SkillManifest
from research_workbench.capability.release_projection import (
    projection_from_verified_release,
)
from research_workbench.evaluation.overlap import validate_overlap
from research_workbench.evaluation.pins import (
    EvaluationInputs,
    arm,
    file_ref,
    require,
    sha,
    timestamp,
)
from research_workbench.evaluation.qualification import (
    snapshot_chain,
    validate_requirement_closure,
)
from research_workbench.evaluation.system_protocol import (
    validate_protocol,
    validate_view_shared_conditions,
)
from research_workbench.execution.host import load_resolved_execution_view
from research_workbench.execution.runtime_bundle import load_runtime_bundle

# This callback is supplied by the authorized Maintainer, not deserialized from
# the record. It must independently verify the pinned evidence/Human decision
# and any promotion/build provenance; shape and status strings cannot do that.
AdmissionVerifier = Callable[[Mapping[str, Any]], bool]


def validate_overlay(
    inputs: EvaluationInputs,
    document: Mapping[str, Any],
    *,
    expected_protocol_ref: Mapping[str, Any],
    expected_case_closure_ref: Mapping[str, Any] | None = None,
    case_selection_frozen_at: str | None = None,
    admission_verifier: AdmissionVerifier | None = None,
) -> list[dict[str, Any]]:
    inputs.validate("a4_execution_qualification", document)
    require(
        expected_case_closure_ref is not None and case_selection_frozen_at is not None,
        "externally frozen case closure and freeze time required for overlay",
    )
    require(
        file_ref(document["case_closure_ref"]) == file_ref(expected_case_closure_ref)
        and document["case_selection_frozen_at"] == case_selection_frozen_at,
        "overlay externally frozen case selection mismatch",
    )
    require(
        file_ref(document["protocol_ref"]) == file_ref(expected_protocol_ref),
        "overlay Protocol substitution",
    )
    protocol = validate_protocol(inputs, expected_protocol_ref)
    require(
        file_ref(document["manifest_ref"]) == file_ref(protocol["manifest_ref"]),
        "overlay Manifest substitution",
    )
    manifest = inputs.manifest(document["manifest_ref"])
    selected_arm = arm(manifest, "mode-candidate-skill")
    require(
        file_ref(document["task_ref"])
        in manifest["frozen_conditions"]["task_packet_refs"],
        "overlay Task is outside Manifest",
    )
    require(
        file_ref(document["admission_evaluation_ref"])
        == file_ref(selected_arm["skill_evaluation_ref"]),
        "overlay Evaluation substitution",
    )
    evaluation = inputs.read(document["admission_evaluation_ref"], "skill_evaluation")
    decision = inputs.read(document["admission_decision_ref"], "research_object")
    require(
        decision.get("object_type") == "decision"
        and decision.get("status") == "accepted",
        "accepted Human Decision required",
    )
    require(
        decision.get("actor") == document["accountable_human"]
        and document["accountable_human"].casefold()
        not in {"human", "agent", "unknown", "system"},
        "named accountable Human required",
    )
    metadata = decision.get("metadata", {})
    require(
        timestamp(decision["timestamp"]) <= timestamp(document["checked_at"]),
        "Human Decision is later than pre-run qualification",
    )
    require(
        all(
            metadata.get(k) == v
            for k, v in {
                "skill_evaluation_id": evaluation["evaluation_id"],
                "skill_candidate_id": evaluation["candidate_id"],
                "decision_owner": "human",
                "skill_admission_outcome": "accept",
            }.items()
        ),
        "Human Decision candidate/Evaluation mismatch",
    )
    require(
        evaluation["admission"].get("outcome") == "accept"
        and evaluation["admission"].get("decision_ref")
        == document["admission_decision_ref"]["path"],
        "Evaluation admission Decision mismatch",
    )
    release = inputs.read(document["release_ref"], "skill_manifest")
    lifecycle = inputs.read(document["lifecycle_ref"], "skill_lifecycle_record")
    record = SkillLifecycleRecord.from_mapping(lifecycle)
    require(
        record.eligible_for_new_binding(), "Lifecycle is not eligible for new binding"
    )
    require(
        record.admission.decision_ref == document["admission_decision_ref"]["path"]
        and record.evaluation.evaluation_record_ref
        == document["admission_evaluation_ref"]["path"],
        "Lifecycle admission/Evaluation mismatch",
    )
    require(
        record.skill_ref.manifest_path == document["release_ref"]["path"]
        and (record.skill_ref.skill_id, record.skill_ref.version)
        == (release["skill_id"], release["version"]),
        "Release/Lifecycle identity mismatch",
    )
    require(
        sha(release["source"]["content_hash"]) == sha(record.skill_ref.content_hash)
        and sha(release["source"]["package_hash"])
        == sha(record.skill_ref.package_hash),
        "Release/Lifecycle content mismatch",
    )
    candidate = selected_arm["skill_binding"]
    exact_candidate = (
        candidate["skill_id"] == release["skill_id"]
        and candidate["version"] == release["version"]
        and sha(candidate["content_hash"]) == sha(record.skill_ref.package_hash)
    )
    promotion = None
    if document["promotion_provenance_ref"] is not None:
        promotion = inputs.read(document["promotion_provenance_ref"])
        require(
            promotion.get("candidate_binding") == candidate
            and promotion.get("release_ref") == document["release_ref"],
            "promotion provenance endpoints mismatch",
        )
    require(
        exact_candidate or promotion is not None,
        "candidate-to-Release substitution lacks promotion/build provenance",
    )
    projection = inputs.read(document["projection_ref"], "skill_release_projection")
    entry = SkillLifecycleEntry(
        record.reference,
        record.lifecycle_id,
        record.lifecycle_version,
        document["lifecycle_ref"]["path"],
        document["lifecycle_ref"]["sha256"],
        record,
    )
    expected_projection = projection_from_verified_release(
        lifecycle_entry=entry,
        manifest=SkillManifest.from_mapping(release),
        manifest_sha256=document["release_ref"]["sha256"],
        projection_version=projection["projection_version"],
    )
    require(
        projection == expected_projection,
        "Projection differs from exact Release/Lifecycle mapping",
    )
    require(
        admission_verifier is not None,
        "external admission/evidence verification required",
    )
    evidence = {
        "protocol_ref": expected_protocol_ref,
        "admission_case_closure_ref": protocol["admission_case_closure_ref"],
        "candidate_binding": candidate,
        "evaluation_ref": document["admission_evaluation_ref"],
        "decision_ref": document["admission_decision_ref"],
        "accountable_human": document["accountable_human"],
        "release_ref": document["release_ref"],
        "lifecycle_ref": document["lifecycle_ref"],
        "promotion_provenance_ref": document["promotion_provenance_ref"],
    }
    require(
        admission_verifier(evidence) is True,
        "external admission/evidence verification rejected",
    )
    assessment = inputs.read(
        document["admission_overlap_assessment_ref"], "admission_evidence_overlap"
    )
    result = validate_overlap(
        inputs,
        assessment,
        expected_protocol_ref=expected_protocol_ref,
        expected_case_closure_ref=expected_case_closure_ref,
        case_selection_frozen_at=case_selection_frozen_at,
    )
    require(result["overlap_status"] != "unresolved", "A4 overlap closure unresolved")
    cases = inputs.read(expected_case_closure_ref, "evaluation_case_closure")
    require(
        file_ref(document["task_ref"])
        in [
            file_ref(case["task"]["ref"])
            for case in cases["cases"]
            if case["task"]["state"] == "resolved"
        ],
        "overlay Task is outside frozen cases",
    )
    for key in ("overlap_status", "overlap_refs", "primary_confirmatory_eligible"):
        require(document[key] == result[key], f"overlay derived {key} mismatch")
    require(
        timestamp(document["checked_at"])
        >= timestamp(document["case_selection_frozen_at"]),
        "overlay precedes case selection freeze",
    )
    bindings = []
    for binding in document["runtime_bindings"]:
        chain = snapshot_chain(inputs, binding["snapshot_ref"])
        snapshot = chain["snapshot"]
        require(
            file_ref(snapshot["task_ref"]) == file_ref(document["task_ref"]),
            "A4 runtime Task substitution",
        )
        require(
            file_ref(snapshot["method_resolution_ref"])
            in selected_arm["treatment_control"]["method_resolution_refs"],
            "A4 Method is outside frozen arm",
        )
        projection_ref = snapshot["supply_identity"].get("skill_release_projection_ref")
        require(
            isinstance(projection_ref, Mapping),
            "projection-backed Skill Supply required",
        )
        require(
            file_ref(projection_ref) == file_ref(document["projection_ref"]),
            "selected Supply Projection substitution",
        )
        inputs.read_bytes(binding["bundle_ref"])
        bundle = load_runtime_bundle(
            binding["bundle_ref"]["path"],
            project_root=inputs.root,
            schema_root=inputs.catalog.root,
        )
        require(
            bundle.manifest_sha256 == binding["bundle_ref"]["sha256"],
            "Bundle external pin mismatch",
        )
        require(
            file_ref(bundle.manifest["entrypoint"])
            == file_ref(binding["snapshot_ref"]),
            "Bundle Snapshot substitution",
        )
        view = load_resolved_execution_view(
            binding["view_ref"]["path"],
            expected_sha256=binding["view_ref"]["sha256"],
            bundle=bundle,
            schema_root=inputs.catalog.root,
        )
        require(
            timestamp(view.document["execution_at"])
            == timestamp(document["checked_at"]),
            "View qualification time mismatch",
        )
        chain["interface"] = inputs.read(
            binding["interface_ref"], "evaluation_provider_interface"
        )
        require(
            chain["interface"]["supply_identity"] == snapshot["supply_identity"],
            "A4 interface Supply mismatch",
        )
        for key in ("provided_capabilities", "supported_inputs", "supported_outputs"):
            require(
                chain["interface"][key] == chain["selected_supply_report"][key],
                f"A4 interface {key} mismatch",
            )
        chain["view"] = view.document
        validate_view_shared_conditions(view.document, manifest, protocol)
        bindings.append(chain)
    validate_requirement_closure(
        inputs, bindings, manifest, selected_arm, task_ref=document["task_ref"]
    )
    inputs.recheck()
    return bindings
