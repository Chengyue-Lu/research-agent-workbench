"""Four-axis held-out assessment from exact, independently reloadable inputs."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from research_workbench.evaluation.pins import (
    EvaluationInputs,
    EvaluationValidationError,
    arm,
    digest,
    file_ref,
    require,
    timestamp,
)
from research_workbench.evaluation.system_protocol import validate_protocol

AXES = ("case", "task", "formal-input", "private-oracle")


def validator_identity(inputs: EvaluationInputs) -> dict[str, Any]:
    """Pin this validator and its M5 parsing/protocol/schema dependencies.

    Pins are derived from the executing installation, never from files selected
    by an assessment author. Records do not contain their own content hash.
    """
    package_root = Path(__file__).parent.parent
    entry = {
        "path": "src/research_workbench/evaluation/overlap.py",
        "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    deps = []
    # Conservative implementation closure includes indirect validators/loaders.
    # An assessment cannot supply a shorter dependency list to validate itself.
    for path in sorted(package_root.rglob("*.py")):
        if path.resolve() == Path(__file__).resolve() or "_runtime_data" in path.parts:
            continue
        deps.append(
            {
                "path": "src/research_workbench/"
                + path.relative_to(package_root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    for name, expected in sorted(inputs.schema_hashes.items()):
        deps.append(
            {
                "path": "schemas/v0.1.0/" + name,
                "sha256": expected,
            }
        )
    return {
        "validator_id": "M5-OVERLAP-VALIDATOR",
        "version": "1.0.0",
        "entrypoint_ref": entry,
        "dependency_refs": deps,
    }


def _subjects(inputs: EvaluationInputs, closure: Mapping[str, Any], label: str):
    inputs.validate("evaluation_case_closure", closure)
    subjects: dict[str, list[dict[str, str]]] = {axis: [] for axis in AXES}
    unresolved: list[str] = []
    seen_cases: set[str] = set()
    for index, case in enumerate(closure["cases"]):
        prefix = f"{label}.cases[{index}]"
        entries = [
            (axis, case[key])
            for axis, key in (
                ("case", "case"),
                ("task", "task"),
                ("private-oracle", "private_oracle"),
            )
        ]
        entries += [("formal-input", item) for item in case["formal_inputs"]]
        entries += [
            ("checker", case["checker"]),
            ("human-adjudication", case["human_adjudication"]),
        ]
        if not case["formal_inputs"]:
            unresolved.append(prefix + ": formal input closure absent")
        if case["task_kind"] != "formal-task":
            unresolved.append(prefix + ": opaque Task lacks comparable formal identity")
        for category, subject in entries:
            if subject["state"] != "resolved":
                unresolved.append(
                    f"{prefix}.{category}: {subject['state']}: {subject['reason']}"
                )
                continue
            try:
                inputs.read_bytes(subject["ref"])
                if category == "task" and case["task_kind"] == "formal-task":
                    task = inputs.read(subject["ref"], "task_packet")
                    require(
                        subject["identity"] == f"{task['task_id']}@r{task['revision']}",
                        "formal Task identity mismatch",
                    )
                if category == "case":
                    case_doc = inputs.read(subject["ref"])
                    require(
                        case_doc.get("case_id") == subject["identity"],
                        "case identity mismatch",
                    )
                    for key in (
                        "task_kind",
                        "task",
                        "formal_inputs",
                        "private_oracle",
                        "checker",
                        "human_adjudication",
                    ):
                        require(
                            case_doc.get(key) == case[key],
                            f"case commitment {key} substitution",
                        )
                    require(
                        subject["identity"] not in seen_cases, "duplicate case identity"
                    )
                    seen_cases.add(subject["identity"])
                if category in {"checker", "human-adjudication"}:
                    provenance = inputs.read(subject["ref"])
                    require(
                        provenance.get("identity") == subject["identity"]
                        and provenance.get("case_id") == case["case"]["identity"]
                        and provenance.get("oracle_ref")
                        == case["private_oracle"]["ref"],
                        "case-specific oracle provenance mismatch",
                    )
            except EvaluationValidationError as exc:
                unresolved.append(f"{prefix}.{category}: {exc}")
                continue
            if category in subjects:
                subjects[category].append(
                    {"identity": subject["identity"], **file_ref(subject["ref"])}
                )
    normalized = {
        axis: sorted(
            {digest(item): item for item in values}.values(),
            key=lambda item: (item["identity"], item["path"], item["sha256"]),
        )
        for axis, values in subjects.items()
    }
    return normalized, unresolved


def derive_overlap(
    inputs: EvaluationInputs,
    admission: Mapping[str, Any],
    comparison: Mapping[str, Any],
):
    """Return normalized closures and a deterministic result, including gaps."""
    left, gaps = _subjects(inputs, admission, "admission")
    right, right_gaps = _subjects(inputs, comparison, "comparison")
    gaps.extend(right_gaps)
    overlaps = []
    for axis in AXES:
        for a in left[axis]:
            for b in right[axis]:
                identity_equal, hash_equal = (
                    a["identity"] == b["identity"],
                    a["sha256"] == b["sha256"],
                )
                if identity_equal or hash_equal:
                    overlaps.append(
                        {
                            "category": axis,
                            "admission_identity": a["identity"],
                            "comparison_identity": b["identity"],
                            "by": "identity-and-hash"
                            if identity_equal and hash_equal
                            else "identity"
                            if identity_equal
                            else "hash",
                        }
                    )
    overlaps = sorted(
        {digest(item): item for item in overlaps}.values(),
        key=lambda item: (
            item["category"],
            item["admission_identity"],
            item["comparison_identity"],
            item["by"],
        ),
    )
    status = "unresolved" if gaps else "admission-overlap" if overlaps else "held-out"
    result = {
        "overlap_status": status,
        "overlap_refs": overlaps,
        "unresolved_reasons": sorted(set(gaps)),
        "primary_confirmatory_eligible": status == "held-out",
    }
    return left, right, result


def validate_overlap(
    inputs: EvaluationInputs,
    document: Mapping[str, Any],
    *,
    expected_protocol_ref: Mapping[str, Any],
    expected_case_closure_ref: Mapping[str, Any],
    case_selection_frozen_at: str,
) -> Mapping[str, Any]:
    inputs.validate("admission_evidence_overlap", document)
    admission, comparison, declared = (
        document[key]
        for key in (
            "admission_case_closure",
            "comparison_input_closure",
            "assessment_result",
        )
    )
    require(
        file_ref(comparison["protocol_ref"]) == file_ref(expected_protocol_ref),
        "overlap Protocol substitution",
    )
    require(
        file_ref(comparison["case_closure_ref"]) == file_ref(expected_case_closure_ref),
        "case selection changed after overlap check",
    )
    protocol = validate_protocol(inputs, expected_protocol_ref)
    require(
        timestamp(protocol["frozen_at"])
        <= timestamp(declared["checked_at"])
        <= timestamp(case_selection_frozen_at),
        "overlap checked_at is outside freeze order",
    )
    require(
        declared["validator"] == validator_identity(inputs),
        "overlap validator identity/version/hash drift",
    )
    manifest = inputs.manifest(protocol["manifest_ref"])
    a4 = arm(manifest, "mode-candidate-skill")
    require(
        file_ref(admission["skill_evaluation_ref"])
        == file_ref(a4["skill_evaluation_ref"]),
        "admission Evaluation substitution",
    )
    evaluation = inputs.read(admission["skill_evaluation_ref"], "skill_evaluation")
    for key in ("candidate_id", "skill_id", "skill_version"):
        require(admission[key] == evaluation[key], f"admission {key} mismatch")
    closure = admission["closure"]
    require(
        protocol["admission_case_closure_ref"] is not None,
        "Protocol must independently pin the admission case closure",
    )
    require(
        closure
        == inputs.read(
            protocol["admission_case_closure_ref"], "evaluation_case_closure"
        ),
        "admission closure differs from the externally frozen Protocol",
    )
    require(closure["scope"] == "admission", "admission closure scope mismatch")
    proposed = inputs.read(expected_case_closure_ref, "evaluation_case_closure")
    require(proposed["scope"] == "confirmatory", "comparison closure scope mismatch")
    require(
        len(proposed["cases"]) == protocol["design"]["stopping"]["case_count"],
        "frozen case count differs from Protocol",
    )
    for case in proposed["cases"]:
        if case["task"]["state"] == "resolved" and case["task_kind"] == "formal-task":
            require(
                file_ref(case["task"]["ref"])
                in manifest["frozen_conditions"]["task_packet_refs"],
                "comparison Task is outside frozen Manifest",
            )
    require(
        comparison["admission_closure_sha256"] == digest(admission),
        "admission closure digest mismatch",
    )
    require(
        len(closure["cases"]) == len(evaluation["cases"]),
        "admission case closure is incomplete",
    )
    for declared_case, original in zip(closure["cases"], evaluation["cases"]):
        require(
            declared_case["case"]["identity"] == original["case_id"],
            "admission case identity/order mismatch",
        )
        if declared_case["task"]["state"] == "resolved":
            require(
                file_ref(declared_case["task"]["ref"])
                == file_ref(original["task_contract_ref"]),
                "admission Task closure substituted",
            )
        require(
            len(declared_case["formal_inputs"]) == 1,
            "admission Evaluation v0.1 binds one formal input per case",
        )
        if declared_case["formal_inputs"][0]["state"] == "resolved":
            require(
                file_ref(declared_case["formal_inputs"][0]["ref"])
                == file_ref(original["input_ref"]),
                "admission formal input substituted",
            )
    left, right, result = derive_overlap(inputs, closure, proposed)
    require(
        comparison["admission_subjects"] == left
        and comparison["comparison_subjects"] == right,
        "normalized overlap subjects drift",
    )
    require(
        comparison["input_digest"] == digest({"admission": left, "comparison": right}),
        "comparison input digest drift",
    )
    for key, value in result.items():
        require(declared[key] == value, f"derived {key} mismatch")
    inputs.recheck()
    return result
