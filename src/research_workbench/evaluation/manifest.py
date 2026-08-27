"""Evaluation manifest and deterministic baseline-plan checks (M5-003).

Phase D treatment arms are canonical. Coordination topology is intentionally
absent: it is an orthogonal future experimental variable, not an arm alias.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from research_workbench.artifacts.integrity import check_file_reference
from research_workbench.io import load_document
from research_workbench.tasks.models import FileReference

PHASE_D_ARMS = (
    "plain-agent",
    "plain-agent-tool",
    "mode-no-skill",
    "mode-candidate-skill",
)

MODE_METHOD_CONTROL = {
    "plain-agent": "suppressed",
    "plain-agent-tool": "suppressed",
    "mode-no-skill": "exact",
    "mode-candidate-skill": "exact",
}


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_id: str
    definition: str
    unit: str
    direction: str


#: M5-003 v0.1 comparison vocabulary. A manifest at this contract version must
#: reproduce the table verbatim; this is not a global metric ontology.
FIXED_METRIC_SET: tuple[MetricDefinition, ...] = (
    MetricDefinition(
        "method-violation",
        "Count of steps that violate the frozen Method Resolution obligations.",
        "count",
        "lower-is-better",
    ),
    MetricDefinition(
        "claim-overreach",
        "Count of claims stated beyond the allowed Claim ceiling.",
        "count",
        "lower-is-better",
    ),
    MetricDefinition(
        "provenance-error",
        "Count of outputs whose provenance chain fails deterministic checks.",
        "count",
        "lower-is-better",
    ),
    MetricDefinition(
        "counterevidence-omission",
        "Count of known counter-evidence items dropped from outputs.",
        "count",
        "lower-is-better",
    ),
    MetricDefinition(
        "human-correction-distance",
        "Number of human corrections needed before an output is acceptable.",
        "count",
        "lower-is-better",
    ),
    MetricDefinition(
        "omission-rate",
        "Share of required facts the arm failed to surface (audit omission metric).",
        "ratio",
        "lower-is-better",
    ),
    MetricDefinition(
        "rework-count",
        "Number of regenerated or redone work units (audit rework metric).",
        "count",
        "lower-is-better",
    ),
    MetricDefinition(
        "lookup-count",
        "Number of re-reads of already-delivered material (audit lookup metric).",
        "count",
        "lower-is-better",
    ),
    MetricDefinition(
        "h2-distortion-rate",
        "Share of sampled compact handoffs with semantic distortion (H2 audit metric).",
        "ratio",
        "lower-is-better",
    ),
    MetricDefinition(
        "cascade-rate",
        "Share of errors that propagate into later work units (audit cascade metric).",
        "ratio",
        "lower-is-better",
    ),
    MetricDefinition(
        "context-loaded",
        "Total context characters or tokens loaded by the arm.",
        "characters-or-tokens",
        "lower-is-better",
    ),
    MetricDefinition(
        "cost",
        "Monetary cost of the arm run.",
        "currency",
        "lower-is-better",
    ),
    MetricDefinition(
        "completion-time",
        "Wall-clock completion time of the arm run.",
        "minutes",
        "lower-is-better",
    ),
)

FIXED_METRIC_BY_ID = {metric.metric_id: metric for metric in FIXED_METRIC_SET}


def check_metric_set(metric_set: Any) -> list[str]:
    """Return human-readable drift descriptions for a manifest metric_set."""

    drifts: list[str] = []
    if not isinstance(metric_set, list):
        return ["metric_set must be an array"]
    seen: dict[str, Mapping[str, Any]] = {}
    for item in metric_set:
        if not isinstance(item, Mapping):
            drifts.append("metric_set entries must be objects")
            continue
        metric_id = item.get("metric_id")
        if not isinstance(metric_id, str):
            drifts.append("metric_set entry lacks a metric_id")
            continue
        if metric_id in seen:
            drifts.append(f"duplicate metric: {metric_id}")
            continue
        seen[metric_id] = item
    for metric in FIXED_METRIC_SET:
        item = seen.get(metric.metric_id)
        if item is None:
            drifts.append(f"fixed metric missing: {metric.metric_id}")
            continue
        for field, expected in (
            ("definition", metric.definition),
            ("unit", metric.unit),
            ("direction", metric.direction),
        ):
            if item.get(field) != expected:
                drifts.append(
                    f"metric {metric.metric_id} {field} drift: expected {expected!r}, "
                    f"got {item.get(field)!r}"
                )
    for metric_id in sorted(set(seen) - set(FIXED_METRIC_BY_ID)):
        drifts.append(f"metric outside the fixed vocabulary: {metric_id}")
    return drifts


def check_treatment_arms(document: Mapping[str, Any]) -> list[str]:
    """Require each canonical Phase D treatment exactly once."""

    legacy_problems = (
        ["arm_map is forbidden: coordination topology is not a treatment mapping"]
        if "arm_map" in document
        else []
    )
    arms = document.get("arms")
    if not isinstance(arms, list):
        return [*legacy_problems, "arms must be an array"]
    problems: list[str] = list(legacy_problems)
    counts = {arm_id: 0 for arm_id in PHASE_D_ARMS}
    for arm in arms:
        if not isinstance(arm, Mapping):
            problems.append("arms contain a non-object entry")
            continue
        arm_id = arm.get("arm_id")
        if arm_id not in PHASE_D_ARMS:
            problems.append(f"arms contain an invalid arm_id: {arm_id!r}")
            continue
        counts[str(arm_id)] += 1
    for arm_id, count in counts.items():
        if count == 0:
            problems.append(f"canonical Phase D arm missing: {arm_id}")
        elif count > 1:
            problems.append(f"duplicate canonical Phase D arm: {arm_id}")
    if len(arms) != len(PHASE_D_ARMS):
        problems.append("arms must contain exactly the four canonical Phase D treatments")
    return problems


def check_evidence_classes(document: Mapping[str, Any]) -> list[str]:
    """Frozen conditions must declare the evidence classes a run must leave."""

    problems: list[str] = []
    frozen = document.get("frozen_conditions")
    if not isinstance(frozen, Mapping):
        return problems
    classes = frozen.get("evidence_classes")
    if not isinstance(classes, list) or not classes:
        problems.append(
            "frozen_conditions.evidence_classes must be a non-empty string array"
        )
    return problems


def check_frozen_conditions(document: Mapping[str, Any]) -> list[str]:
    """Require one exact, shared comparison envelope for every treatment."""

    problems: list[str] = []
    frozen = document.get("frozen_conditions")
    if not isinstance(frozen, Mapping):
        return ["frozen_conditions must be an object"]
    task_refs = frozen.get("task_packet_refs")
    if not isinstance(task_refs, list) or not task_refs:
        problems.append("frozen_conditions.task_packet_refs must pin a non-empty Task set")
    model = frozen.get("model")
    if not isinstance(model, Mapping) or any(
        not isinstance(model.get(key), str) or not model.get(key)
        for key in ("slot_id", "provider_adapter", "model_id")
    ):
        problems.append("frozen_conditions.model must pin slot, adapter, and exact model_id")
    elif not isinstance(model.get("pool_ref"), Mapping):
        problems.append("frozen_conditions.model.pool_ref must pin the model pool file")
    for key in ("host", "budget", "context"):
        if not isinstance(frozen.get(key), Mapping):
            problems.append(f"frozen_conditions.{key} must be an exact shared object")

    controlled_keys = {
        "task_packet_refs",
        "model",
        "model_binding",
        "model_pool_ref",
        "host",
        "budget",
        "context",
        "context_policy_ref",
        "data_policy_ref",
    }
    for arm in document.get("arms", []):
        if not isinstance(arm, Mapping):
            continue
        for key in sorted(controlled_keys.intersection(arm)):
            problems.append(
                f"arm {arm.get('arm_id')!r} overrides shared controlled condition {key!r}"
            )
    return problems


def check_treatment_bindings(document: Mapping[str, Any]) -> list[str]:
    """Require exact control exposure, Tool/Snapshot, and Skill bindings."""

    problems: list[str] = []
    for arm in document.get("arms", []):
        if not isinstance(arm, Mapping):
            continue
        arm_id = arm.get("arm_id")
        control = arm.get("treatment_control")
        expected_control = MODE_METHOD_CONTROL.get(str(arm_id))
        if not isinstance(control, Mapping):
            problems.append(f"{arm_id} requires an explicit treatment_control")
        elif control.get("mode_method_control") != expected_control:
            problems.append(
                f"{arm_id} requires mode_method_control={expected_control!r}"
            )
        elif expected_control == "exact":
            if not isinstance(control.get("mode_refs"), list) or not control.get("mode_refs"):
                problems.append(f"{arm_id} requires exact mode_refs")
            if (
                not isinstance(control.get("method_resolution_refs"), list)
                or not control.get("method_resolution_refs")
            ):
                problems.append(f"{arm_id} requires exact method_resolution_refs")
        elif any(key in control for key in ("mode_refs", "method_resolution_refs")):
            problems.append(
                f"{arm_id} suppresses Mode/Method control and must not expose control refs"
            )
        snapshots = arm.get("capability_snapshot_refs")
        if arm_id in {"plain-agent-tool", "mode-no-skill"} and (
            not isinstance(snapshots, list) or not snapshots
        ):
            problems.append(f"{arm_id} requires at least one frozen Capability Snapshot")
        if arm_id == "plain-agent" and any(
            key in arm for key in ("capability_snapshot_refs", "skill_binding", "skill_evaluation_ref")
        ):
            problems.append("plain-agent must not carry Tool/Snapshot or Skill treatment bindings")
        if arm_id == "mode-candidate-skill":
            binding = arm.get("skill_binding")
            if not isinstance(binding, Mapping) or any(
                not binding.get(key) for key in ("skill_id", "version", "content_hash", "source_ref")
            ):
                problems.append("mode-candidate-skill requires an exact skill_binding")
            if not isinstance(arm.get("skill_evaluation_ref"), Mapping):
                problems.append("mode-candidate-skill requires skill_evaluation_ref")
        elif any(key in arm for key in ("skill_binding", "skill_evaluation_ref")):
            problems.append(f"{arm_id} must not carry candidate-Skill treatment fields")
    return problems


def check_snapshot_treatment_semantics(
    arm_id: str, snapshot: Mapping[str, Any]
) -> list[str]:
    """Validate the Supply projection exposed by a treatment Snapshot."""

    problems: list[str] = []
    identity = snapshot.get("supply_identity")
    if not isinstance(identity, Mapping):
        return [f"{arm_id} Capability Snapshot lacks supply_identity"]
    supply_kind = identity.get("supply_kind")
    components = identity.get("components")
    component_values = components if isinstance(components, list) else []
    component_kinds = {
        component.get("component_kind")
        for component in component_values
        if isinstance(component, Mapping)
    }
    if arm_id == "plain-agent-tool" and supply_kind != "tool":
        problems.append(
            "plain-agent-tool Capability Snapshot must expose exact Tool supply"
        )
    if arm_id == "mode-no-skill" and (
        supply_kind == "skill" or "skill" in component_kinds
    ):
        problems.append("mode-no-skill Capability Snapshot must not expose Skill supply")
    return problems


def check_evaluation_manifest(document: Mapping[str, Any]) -> list[str]:
    """All deterministic checks for one evaluation manifest."""

    return [
        *check_metric_set(document.get("metric_set")),
        *check_treatment_arms(document),
        *check_frozen_conditions(document),
        *check_evidence_classes(document),
        *check_treatment_bindings(document),
    ]


def compile_baseline_plan(document: Mapping[str, Any]) -> dict[str, Any]:
    """Compile a deterministic, non-executing four-arm baseline harness plan."""

    from research_workbench.validation.schemas import SchemaCatalog

    schema_errors = SchemaCatalog().validate("evaluation_manifest", document)
    problems = check_evaluation_manifest(document)
    if schema_errors or problems:
        schema_messages = [f"{item.pointer}: {item.message}" for item in schema_errors]
        raise ValueError(
            "invalid evaluation manifest: " + "; ".join([*schema_messages, *problems])
        )
    frozen = copy.deepcopy(document["frozen_conditions"])
    encoded = json.dumps(frozen, sort_keys=True, separators=(",", ":")).encode("utf-8")
    frozen_digest = hashlib.sha256(encoded).hexdigest()
    by_id = {str(arm["arm_id"]): arm for arm in document["arms"]}
    return {
        "schema_version": "0.1.0",
        "manifest_id": document["manifest_id"],
        "status": "compiled-not-executed",
        "frozen_conditions_sha256": frozen_digest,
        "frozen_conditions": frozen,
        "arms": [
            {
                "arm_id": arm_id,
                "frozen_conditions_sha256": frozen_digest,
                "treatment": copy.deepcopy(by_id[arm_id]),
            }
            for arm_id in PHASE_D_ARMS
        ],
        "limitations": [
            "This plan freezes inputs and treatments; it does not authorize or report execution."
        ],
    }


def check_reference_closure(root: str | Path, document: Mapping[str, Any]) -> list[str]:
    """Bind treatment references to the frozen Task and exact Skill identity."""

    problems: list[str] = []
    frozen = document.get("frozen_conditions")
    if not isinstance(frozen, Mapping):
        return problems
    task_paths = {
        str(reference.get("path"))
        for reference in frozen.get("task_packet_refs", [])
        if isinstance(reference, Mapping) and reference.get("path")
    }
    task_documents: list[Mapping[str, Any]] = []
    expected_tasks: set[tuple[Any, Any, str]] = set()
    for raw_ref in frozen.get("task_packet_refs", []):
        if not isinstance(raw_ref, Mapping):
            continue
        check = check_file_reference(root, FileReference.from_mapping(raw_ref))
        if check.valid and check.resolved_path is not None:
            task = load_document(check.resolved_path)
            if isinstance(task, Mapping):
                task_documents.append(task)
                expected_tasks.add(
                    (
                        task.get("task_id"),
                        task.get("revision"),
                        str(raw_ref.get("sha256", "")).removeprefix("sha256:"),
                    )
                )
    model = frozen.get("model")
    if isinstance(model, Mapping) and isinstance(model.get("pool_ref"), Mapping):
        check = check_file_reference(root, FileReference.from_mapping(model["pool_ref"]))
        if check.valid and check.resolved_path is not None:
            pool = load_document(check.resolved_path)
            slots = pool.get("slots", []) if isinstance(pool, Mapping) else []
            selected = next(
                (
                    slot
                    for slot in slots
                    if isinstance(slot, Mapping) and slot.get("slot_id") == model.get("slot_id")
                ),
                None,
            )
            if selected is None:
                problems.append(
                    f"exact Model slot_id {model.get('slot_id')!r} is absent from pinned model pool"
                )
            elif selected.get("provider_adapter") != model.get("provider_adapter"):
                problems.append(
                    "exact Model provider_adapter does not match the selected pinned pool slot"
                )
    for arm in document.get("arms", []):
        if not isinstance(arm, Mapping):
            continue
        for raw_ref in arm.get("capability_snapshot_refs", []):
            if not isinstance(raw_ref, Mapping):
                continue
            check = check_file_reference(root, FileReference.from_mapping(raw_ref))
            if not check.valid or check.resolved_path is None:
                continue
            snapshot = load_document(check.resolved_path)
            if isinstance(snapshot, Mapping):
                problems.extend(
                    check_snapshot_treatment_semantics(str(arm.get("arm_id")), snapshot)
                )
            snapshot_task = (
                snapshot.get("task_ref", {}).get("document_path")
                if isinstance(snapshot, Mapping)
                else None
            )
            if snapshot_task not in task_paths:
                problems.append(
                    f"{arm.get('arm_id')} Capability Snapshot binds Task {snapshot_task!r}, "
                    "outside frozen_conditions.task_packet_refs"
                )

            control = arm.get("treatment_control")
            if arm.get("arm_id") == "mode-no-skill" and isinstance(control, Mapping):
                control_paths = {
                    str(reference.get("path"))
                    for reference in control.get("method_resolution_refs", [])
                    if isinstance(reference, Mapping)
                }
                snapshot_method_path = (
                    snapshot.get("method_resolution_ref", {}).get("document_path")
                    if isinstance(snapshot, Mapping)
                    and isinstance(snapshot.get("method_resolution_ref"), Mapping)
                    else None
                )
                if snapshot_method_path not in control_paths:
                    problems.append(
                        "mode-no-skill Capability Snapshot is not bound to its exact "
                        "treatment Method Resolution"
                    )

        control = arm.get("treatment_control")
        if isinstance(control, Mapping) and control.get("mode_method_control") == "exact":
            mode_refs = control.get("mode_refs", [])
            active_mode_ids = {
                str(mode_id)
                for task in task_documents
                for mode_id in task.get("active_modes", [])
                if isinstance(mode_id, str)
            }
            controlled_mode_ids = {
                str(mode_ref).partition("@")[0]
                for mode_ref in mode_refs
                if isinstance(mode_ref, str)
            }
            if controlled_mode_ids != active_mode_ids:
                problems.append(
                    f"{arm.get('arm_id')} exact mode_refs do not match the frozen Task active_modes"
                )
            for raw_ref in control.get("method_resolution_refs", []):
                if not isinstance(raw_ref, Mapping):
                    continue
                check = check_file_reference(root, FileReference.from_mapping(raw_ref))
                if not check.valid or check.resolved_path is None:
                    continue
                resolution = load_document(check.resolved_path)
                if not isinstance(resolution, Mapping):
                    problems.append("method_resolution_ref must resolve to an object")
                    continue
                mode_resolution = resolution.get("mode_resolution")
                selected_modes = (
                    mode_resolution.get("selected_mode_refs")
                    if isinstance(mode_resolution, Mapping)
                    else None
                )
                if not isinstance(selected_modes, list) or {
                    str(value) for value in selected_modes
                } != {str(value) for value in mode_refs}:
                    problems.append(
                        f"{arm.get('arm_id')} treatment mode_refs do not match the pinned "
                        "Method Resolution"
                    )
                task_ref = resolution.get("task_ref")
                actual_task = (
                    (
                        task_ref.get("task_id"),
                        task_ref.get("revision"),
                        str(task_ref.get("sha256", "")).removeprefix("sha256:"),
                    )
                    if isinstance(task_ref, Mapping)
                    else None
                )
                if actual_task not in expected_tasks:
                    problems.append(
                        f"{arm.get('arm_id')} Method Resolution is not bound to a frozen Task"
                    )

        if arm.get("arm_id") != "mode-candidate-skill":
            continue
        binding = arm.get("skill_binding")
        raw_evaluation_ref = arm.get("skill_evaluation_ref")
        if not isinstance(binding, Mapping) or not isinstance(raw_evaluation_ref, Mapping):
            continue
        check = check_file_reference(root, FileReference.from_mapping(raw_evaluation_ref))
        if not check.valid or check.resolved_path is None:
            continue
        evaluation = load_document(check.resolved_path)
        if not isinstance(evaluation, Mapping):
            problems.append("skill_evaluation_ref must resolve to an object")
            continue
        expected = {
            "skill_id": evaluation.get("skill_id"),
            "version": evaluation.get("skill_version"),
            "content_hash": evaluation.get("skill_package_hash"),
            "source_ref": evaluation.get("skill_source_ref"),
        }
        for key, value in expected.items():
            if binding.get(key) != value:
                problems.append(
                    f"mode-candidate-skill binding {key} does not match pinned Skill Evaluation"
                )
    return problems
