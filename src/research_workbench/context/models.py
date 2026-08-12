from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    mapping_tuple,
    mapping_value,
    optional_string,
    require_relative_path,
    require_string,
    string_tuple,
)


CONTEXT_METRIC_NAMES = (
    "loaded_chars",
    "pinned_chars",
    "skill_instruction_chars",
    "raw_material_chars",
    "recent_handoffs",
    "open_items",
    "turns",
    "long_tool_outputs",
    "compaction_events",
    "hidden_decisions",
)

THRESHOLDED_CONTEXT_METRICS = (
    "loaded_chars",
    "pinned_chars",
    "skill_instruction_chars",
    "recent_handoffs",
    "open_items",
    "turns",
    "long_tool_outputs",
)

DEFAULT_CONTEXT_THRESHOLDS: Mapping[str, Mapping[str, int]] = {
    "loaded_chars": {"warn": 24_000, "rollover": 48_000},
    "pinned_chars": {"warn": 4_000, "rollover": 8_000},
    "skill_instruction_chars": {"warn": 6_000, "rollover": 12_000},
    "recent_handoffs": {"warn": 4, "rollover": 8},
    "open_items": {"warn": 8, "rollover": 16},
    "turns": {"warn": 20, "rollover": 40},
    "long_tool_outputs": {"warn": 3, "rollover": 6},
}


def _non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError(field, "must be a non-negative integer")
    return value


def _unique_strings(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if len(values) != len(set(values)):
        raise ContractError(field, "must not contain duplicates")
    return values


@dataclass(frozen=True, slots=True)
class ContextThreshold:
    warn: int
    rollover: int

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any], field: str) -> "ContextThreshold":
        warn = _non_negative_int(data.get("warn"), f"{field}.warn")
        rollover = _non_negative_int(data.get("rollover"), f"{field}.rollover")
        if rollover < warn:
            raise ContractError(field, "rollover must be greater than or equal to warn")
        return cls(warn, rollover)


@dataclass(frozen=True, slots=True)
class ContextPolicySnapshot:
    proactive_checkpoint: bool
    main_raw_material: str
    thresholds: Mapping[str, ContextThreshold]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ContextPolicySnapshot":
        proactive = data.get("proactive_checkpoint")
        if not isinstance(proactive, bool):
            raise ContractError("policy.proactive_checkpoint", "must be boolean")
        raw_policy = require_string(data, "main_raw_material")
        if raw_policy not in {"forbidden", "on-demand", "allowed"}:
            raise ContractError("policy.main_raw_material", "has unsupported value")
        raw_thresholds = mapping_value(data, "thresholds", required=True)
        unknown = sorted(set(raw_thresholds) - set(THRESHOLDED_CONTEXT_METRICS))
        missing = sorted(set(THRESHOLDED_CONTEXT_METRICS) - set(raw_thresholds))
        if unknown:
            raise ContractError("policy.thresholds", f"unknown metrics: {', '.join(unknown)}")
        if missing:
            raise ContractError("policy.thresholds", f"missing metrics: {', '.join(missing)}")
        thresholds = {
            name: ContextThreshold.from_mapping(
                mapping_value(raw_thresholds, name, required=True),
                f"policy.thresholds.{name}",
            )
            for name in THRESHOLDED_CONTEXT_METRICS
        }
        return cls(proactive, raw_policy, thresholds)

    @classmethod
    def from_project_policy(cls, data: Mapping[str, Any]) -> "ContextPolicySnapshot":
        merged: dict[str, Mapping[str, int]] = {
            name: dict(values) for name, values in DEFAULT_CONTEXT_THRESHOLDS.items()
        }
        overrides = mapping_value(data, "pressure_thresholds")
        unknown = sorted(set(overrides) - set(THRESHOLDED_CONTEXT_METRICS))
        if unknown:
            raise ContractError("context_policy.pressure_thresholds", f"unknown metrics: {', '.join(unknown)}")
        for name, value in overrides.items():
            if not isinstance(value, Mapping):
                raise ContractError(f"context_policy.pressure_thresholds.{name}", "must be an object")
            merged[name] = dict(value)
        return cls.from_mapping(
            {
                "proactive_checkpoint": data.get("proactive_checkpoint"),
                "main_raw_material": data.get("main_raw_material"),
                "thresholds": merged,
            }
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "proactive_checkpoint": self.proactive_checkpoint,
            "main_raw_material": self.main_raw_material,
            "thresholds": {
                name: {"warn": threshold.warn, "rollover": threshold.rollover}
                for name, threshold in self.thresholds.items()
            },
        }


@dataclass(frozen=True, slots=True)
class ContextAssessment:
    level: str
    triggered_rules: tuple[str, ...]
    required_actions: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ContextAssessment":
        level = require_string(data, "level")
        if level not in {"ok", "warn", "rollover", "block"}:
            raise ContractError("assessment.level", "has unsupported value")
        return cls(
            level,
            _unique_strings(string_tuple(data, "triggered_rules", required=True), "assessment.triggered_rules"),
            _unique_strings(string_tuple(data, "required_actions", required=True), "assessment.required_actions"),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "triggered_rules": list(self.triggered_rules),
            "required_actions": list(self.required_actions),
        }


def assess_context(
    *,
    scope: str,
    metrics: Mapping[str, int],
    unknown_metrics: tuple[str, ...],
    handoff_ready: bool | None,
    policy: ContextPolicySnapshot,
) -> ContextAssessment:
    levels = {"ok": 0, "warn": 1, "rollover": 2, "block": 3}
    level = "ok"
    rules: list[str] = []
    actions: list[str] = []

    def trigger(rule: str, new_level: str, action: str) -> None:
        nonlocal level
        if rule not in rules:
            rules.append(rule)
        if action not in actions:
            actions.append(action)
        if levels[new_level] > levels[level]:
            level = new_level

    for name in THRESHOLDED_CONTEXT_METRICS:
        if name not in metrics:
            continue
        value = metrics[name]
        threshold = policy.thresholds[name]
        code = name.replace("_", "-").upper()
        if value >= threshold.rollover:
            trigger(
                f"CTX-{code}-ROLLOVER",
                "rollover",
                "write and validate Main State, then start a fresh main session",
            )
        elif value >= threshold.warn:
            trigger(
                f"CTX-{code}-WARN",
                "warn",
                "write a Main State checkpoint before accepting more context",
            )

    raw_chars = metrics.get("raw_material_chars")
    if scope == "main" and raw_chars:
        if policy.main_raw_material == "forbidden":
            trigger(
                "CTX-MAIN-RAW-MATERIAL",
                "block",
                "remove raw material from main context and retain only references",
            )
        elif policy.main_raw_material == "on-demand":
            trigger(
                "CTX-MAIN-RAW-MATERIAL-ON-DEMAND",
                "warn",
                "unload raw material after resolving the current bounded dispute",
            )

    compactions = metrics.get("compaction_events")
    if compactions:
        if scope == "main":
            trigger(
                "CTX-AUTO-COMPACTION",
                "rollover",
                "treat compaction as an incident and run resume-check from Main State",
            )
        elif handoff_ready is True:
            trigger(
                "CTX-SUBAGENT-COMPACTION-RECOVERABLE",
                "warn",
                "verify the persisted Handoff before discarding the task session",
            )
        else:
            trigger(
                "CTX-HANDOFF-LOSS",
                "block",
                "persist an incomplete Handoff before continuing or discarding the task session",
            )

    if metrics.get("hidden_decisions"):
        trigger(
            "CTX-HIDDEN-STATE",
            "block",
            "promote hidden decisions to Decision artifacts before continuing",
        )

    if unknown_metrics:
        trigger(
            "CTX-METRICS-UNKNOWN",
            "warn",
            "record unavailable metrics explicitly and avoid zero-cost claims",
        )
    return ContextAssessment(level, tuple(rules), tuple(actions))


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    schema_version: str
    snapshot_id: str
    captured_at: str
    scope: str
    owner_ref: str | None
    measurement_source: str
    metrics: Mapping[str, int]
    unknown_metrics: tuple[str, ...]
    handoff_ready: bool | None
    policy: ContextPolicySnapshot
    assessment: ContextAssessment

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ContextSnapshot":
        scope = require_string(data, "scope")
        if scope not in {"main", "task"}:
            raise ContractError("scope", "must be main or task")
        source = require_string(data, "measurement_source")
        if source not in {"runtime", "manual", "file-estimate", "mixed"}:
            raise ContractError("measurement_source", "has unsupported value")
        raw_metrics = mapping_value(data, "metrics", required=True)
        unknown_names = sorted(set(raw_metrics) - set(CONTEXT_METRIC_NAMES))
        if unknown_names:
            raise ContractError("metrics", f"unknown metrics: {', '.join(unknown_names)}")
        metrics = {
            name: _non_negative_int(value, f"metrics.{name}")
            for name, value in raw_metrics.items()
        }
        unknown_metrics = _unique_strings(
            string_tuple(data, "unknown_metrics", required=True),
            "unknown_metrics",
        )
        invalid_unknown = sorted(set(unknown_metrics) - set(CONTEXT_METRIC_NAMES))
        if invalid_unknown:
            raise ContractError("unknown_metrics", f"unknown metrics: {', '.join(invalid_unknown)}")
        overlap = sorted(set(metrics) & set(unknown_metrics))
        if overlap:
            raise ContractError("metrics", f"both measured and unknown: {', '.join(overlap)}")
        uncovered = sorted(set(CONTEXT_METRIC_NAMES) - set(metrics) - set(unknown_metrics))
        if uncovered:
            raise ContractError("metrics", f"must measure or mark unknown: {', '.join(uncovered)}")
        handoff_ready = data.get("handoff_ready")
        if handoff_ready is not None and not isinstance(handoff_ready, bool):
            raise ContractError("handoff_ready", "must be boolean or null")
        policy = ContextPolicySnapshot.from_mapping(mapping_value(data, "policy", required=True))
        assessment = ContextAssessment.from_mapping(mapping_value(data, "assessment", required=True))
        expected = assess_context(
            scope=scope,
            metrics=metrics,
            unknown_metrics=unknown_metrics,
            handoff_ready=handoff_ready,
            policy=policy,
        )
        if assessment != expected:
            raise ContractError("assessment", "does not match deterministic context assessment")
        owner_ref = optional_string(data, "owner_ref")
        return cls(
            schema_version=require_string(data, "schema_version"),
            snapshot_id=require_string(data, "snapshot_id"),
            captured_at=require_string(data, "captured_at"),
            scope=scope,
            owner_ref=owner_ref,
            measurement_source=source,
            metrics=metrics,
            unknown_metrics=unknown_metrics,
            handoff_ready=handoff_ready,
            policy=policy,
            assessment=assessment,
        )

    def to_mapping(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "scope": self.scope,
            "measurement_source": self.measurement_source,
            "metrics": dict(self.metrics),
            "unknown_metrics": list(self.unknown_metrics),
            "handoff_ready": self.handoff_ready,
            "policy": self.policy.to_mapping(),
            "assessment": self.assessment.to_mapping(),
        }
        if self.owner_ref is not None:
            document["owner_ref"] = self.owner_ref
        return document

    @classmethod
    def create(
        cls,
        *,
        snapshot_id: str,
        captured_at: str,
        scope: str,
        measurement_source: str,
        metrics: Mapping[str, int],
        unknown_metrics: tuple[str, ...],
        handoff_ready: bool | None,
        policy: ContextPolicySnapshot,
        owner_ref: str | None = None,
    ) -> "ContextSnapshot":
        assessment = assess_context(
            scope=scope,
            metrics=metrics,
            unknown_metrics=unknown_metrics,
            handoff_ready=handoff_ready,
            policy=policy,
        )
        return cls.from_mapping(
            {
                "schema_version": "0.1.0",
                "snapshot_id": snapshot_id,
                "captured_at": captured_at,
                "scope": scope,
                "owner_ref": owner_ref,
                "measurement_source": measurement_source,
                "metrics": dict(metrics),
                "unknown_metrics": list(unknown_metrics),
                "handoff_ready": handoff_ready,
                "policy": policy.to_mapping(),
                "assessment": assessment.to_mapping(),
            }
        )


def checkpoint_digest(document: Mapping[str, Any]) -> str:
    canonical = {key: value for key, value in document.items() if key != "checkpoint_digest"}
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ActiveTaskState:
    task_id: str
    status: str
    expected_handoff: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ActiveTaskState":
        handoff = optional_string(data, "expected_handoff")
        if handoff is not None:
            require_relative_path(handoff, "expected_handoff")
        return cls(require_string(data, "task_id"), require_string(data, "status"), handoff)


@dataclass(frozen=True, slots=True)
class RecentHandoffState:
    ref: str
    disposition: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RecentHandoffState":
        ref = require_relative_path(require_string(data, "ref"), "ref")
        return cls(ref, require_string(data, "disposition"))


@dataclass(frozen=True, slots=True)
class MainStatePacket:
    schema_version: str
    checkpoint_id: str
    project_protocol_ref: str
    current_questions: tuple[str, ...]
    pinned_constraints: tuple[str, ...]
    accepted_decisions: tuple[str, ...]
    active_tasks: tuple[ActiveTaskState, ...]
    recent_handoffs: tuple[RecentHandoffState, ...]
    open_conflicts: tuple[str, ...]
    open_risks: tuple[str, ...]
    next_actions: tuple[str, ...]
    artifact_index_refs: tuple[str, ...]
    rollover_reason: str | None = None
    created_at: str | None = None
    previous_checkpoint_ref: str | None = None
    context_snapshot_ref: str | None = None
    checkpoint_digest: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MainStatePacket":
        index_refs = string_tuple(data, "artifact_index_refs")
        for index, ref in enumerate(index_refs):
            require_relative_path(ref, f"artifact_index_refs[{index}]")
        previous_ref = optional_string(data, "previous_checkpoint_ref")
        snapshot_ref = optional_string(data, "context_snapshot_ref")
        for field, value in (
            ("previous_checkpoint_ref", previous_ref),
            ("context_snapshot_ref", snapshot_ref),
        ):
            if value is not None:
                require_relative_path(value, field)
        digest = optional_string(data, "checkpoint_digest")
        if digest is not None:
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ContractError("checkpoint_digest", "must be a lowercase SHA-256 digest")
            expected = checkpoint_digest(data)
            if digest != expected:
                raise ContractError("checkpoint_digest", "does not match canonical Main State content")
        return cls(
            schema_version=require_string(data, "schema_version"),
            checkpoint_id=require_string(data, "checkpoint_id"),
            project_protocol_ref=require_string(data, "project_protocol_ref"),
            current_questions=string_tuple(data, "current_questions", required=True),
            pinned_constraints=string_tuple(data, "pinned_constraints", required=True),
            accepted_decisions=string_tuple(data, "accepted_decisions"),
            active_tasks=tuple(ActiveTaskState.from_mapping(item) for item in mapping_tuple(data, "active_tasks")),
            recent_handoffs=tuple(
                RecentHandoffState.from_mapping(item) for item in mapping_tuple(data, "recent_handoffs")
            ),
            open_conflicts=string_tuple(data, "open_conflicts"),
            open_risks=string_tuple(data, "open_risks"),
            next_actions=string_tuple(data, "next_actions", required=True),
            artifact_index_refs=index_refs,
            rollover_reason=optional_string(data, "rollover_reason"),
            created_at=optional_string(data, "created_at"),
            previous_checkpoint_ref=previous_ref,
            context_snapshot_ref=snapshot_ref,
            checkpoint_digest=digest,
        )
