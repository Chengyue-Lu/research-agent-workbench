"""Evaluation manifest metric vocabulary and cross-checks (M5-003).

The metric set is *fixed*: a manifest must carry the canonical vocabulary
verbatim.  The M5 three arms (single-agent / lightweight / multi-agent) are
mapped onto the Phase D four-arm comparison vocabulary, and both vocabularies
stop drifting apart because the mapping is part of the frozen manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

M5_ARMS = ("single-agent", "lightweight", "multi-agent")

PHASE_D_ARMS = (
    "plain-agent",
    "plain-agent-tool",
    "mode-no-skill",
    "mode-candidate-skill",
)


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_id: str
    definition: str
    unit: str
    direction: str


#: Fixed metric vocabulary: ROADMAP Phase D metrics merged with the
#: execution-recovery audit metrics (omission / rework / lookup / H2
#: distortion / cascade).  A manifest must reproduce this table verbatim.
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


def check_arm_map_and_arms(document: Mapping[str, Any]) -> list[str]:
    """Verify the M5-to-Phase-D arm mapping and arm coverage."""

    problems: list[str] = []
    arm_map = document.get("arm_map")
    if not isinstance(arm_map, Mapping):
        return ["arm_map must be an object"]
    referenced: set[str] = set()
    for m5_arm in M5_ARMS:
        target = arm_map.get(m5_arm)
        if target not in PHASE_D_ARMS:
            problems.append(
                f"arm_map.{m5_arm} must map to a Phase D arm, got {target!r}"
            )
        elif target in PHASE_D_ARMS:
            referenced.add(target)
    arms = document.get("arms")
    if not isinstance(arms, list) or not arms:
        problems.append("arms must be a non-empty array")
        return problems
    configured: set[str] = set()
    for arm in arms:
        if isinstance(arm, Mapping) and arm.get("arm_id") in PHASE_D_ARMS:
            configured.add(arm["arm_id"])
        else:
            problems.append("arms contain an invalid arm_id")
    for missing in sorted(referenced - configured):
        problems.append(f"arm_map references an unconfigured arm: {missing}")
    # Extra Phase D arms beyond the mapped three are allowed: the manifest
    # must be able to express the full four-arm comparison (plain-agent /
    # plain-agent-tool / mode-no-skill / mode-candidate-skill) even though
    # the M5 vocabulary names only three arms.
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
    """Frozen comparison conditions must pin model pool per arm."""

    problems: list[str] = []
    arms = document.get("arms")
    if not isinstance(arms, list):
        return problems
    pools = {
        arm.get("model_pool_ref", {}).get("path")
        if isinstance(arm.get("model_pool_ref"), Mapping)
        else None
        for arm in arms
        if isinstance(arm, Mapping)
    }
    pools.discard(None)
    if len(pools) == 0:
        problems.append("no arm pins a model_pool_ref; comparison is not frozen")
    elif len(pools) > 1:
        problems.append(
            "arms pin different model pools; cross-arm comparison requires one frozen pool"
        )
    return problems


def check_evaluation_manifest(document: Mapping[str, Any]) -> list[str]:
    """All deterministic checks for one evaluation manifest."""

    return [
        *check_metric_set(document.get("metric_set")),
        *check_arm_map_and_arms(document),
        *check_frozen_conditions(document),
        *check_evidence_classes(document),
    ]
