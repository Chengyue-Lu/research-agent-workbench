from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    ensure_unique,
    mapping_tuple,
    mapping_value,
    optional_string,
    require_relative_path,
    require_string,
    string_tuple,
)


def canonical_document_sha256(
    document: Mapping[str, Any], *, exclude: tuple[str, ...] = ()
) -> str:
    """Hash a contract deterministically without relying on YAML formatting."""

    payload = {key: value for key, value in document.items() if key not in exclude}
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ModeAction:
    schema_version: str
    action_id: str
    mode_id: str
    version: str
    trigger: tuple[str, ...]
    non_trigger: tuple[str, ...]
    failure_conditions: tuple[str, ...]
    required_artifact_types: tuple[str, ...]
    claim_effects: tuple[str, ...]
    human_gates: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    blocked_conditions: tuple[str, ...]
    allowed_mechanisms: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ModeAction":
        mode_id = require_string(data, "mode_id")
        action_id = require_string(data, "action_id")
        if not action_id.startswith(("ES-", "SIM-")):
            raise ContractError("action_id", "must use a stable admitted Mode Action ID")
        mechanisms = ensure_unique(
            string_tuple(data, "allowed_mechanisms", required=True),
            "allowed_mechanisms",
        )
        if not mechanisms:
            raise ContractError("allowed_mechanisms", "must not be empty")
        return cls(
            schema_version=require_string(data, "schema_version"),
            action_id=action_id,
            mode_id=mode_id,
            version=require_string(data, "version"),
            trigger=ensure_unique(string_tuple(data, "trigger", required=True), "trigger"),
            non_trigger=ensure_unique(
                string_tuple(data, "non_trigger", required=True), "non_trigger"
            ),
            failure_conditions=ensure_unique(
                string_tuple(data, "failure_conditions", required=True),
                "failure_conditions",
            ),
            required_artifact_types=ensure_unique(
                string_tuple(data, "required_artifact_types", required=True),
                "required_artifact_types",
            ),
            claim_effects=ensure_unique(
                string_tuple(data, "claim_effects", required=True), "claim_effects"
            ),
            human_gates=ensure_unique(string_tuple(data, "human_gates"), "human_gates"),
            stop_conditions=ensure_unique(
                string_tuple(data, "stop_conditions", required=True), "stop_conditions"
            ),
            blocked_conditions=ensure_unique(
                string_tuple(data, "blocked_conditions", required=True),
                "blocked_conditions",
            ),
            allowed_mechanisms=mechanisms,
        )


@dataclass(frozen=True, slots=True)
class ActionSelection:
    action_id: str
    status: str
    mode_id: str | None
    version: str | None
    source_path: str | None
    sha256: str | None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ActionSelection":
        status = require_string(data, "status")
        allowed_statuses = {"selected", "inherited", "candidate-gap"}
        if status not in allowed_statuses:
            raise ContractError("action_selections.status", f"must be one of {sorted(allowed_statuses)}")
        mode_id = optional_string(data, "mode_id")
        version = optional_string(data, "version")
        source_path = optional_string(data, "source_path")
        sha256 = optional_string(data, "sha256")
        if status == "selected":
            missing = [
                field
                for field, value in (
                    ("mode_id", mode_id),
                    ("version", version),
                    ("source_path", source_path),
                    ("sha256", sha256),
                )
                if value is None
            ]
            if missing:
                raise ContractError(
                    "action_selections", f"selected action lacks {', '.join(missing)}"
                )
        if source_path is not None:
            require_relative_path(source_path, "action_selections.source_path")
        if sha256 is not None:
            normalized = sha256.removeprefix("sha256:")
            if len(normalized) != 64 or any(char not in "0123456789abcdefABCDEF" for char in normalized):
                raise ContractError("action_selections.sha256", "must be a SHA-256 digest")
        return cls(
            action_id=require_string(data, "action_id"),
            status=status,
            mode_id=mode_id,
            version=version,
            source_path=source_path,
            sha256=sha256,
        )


@dataclass(frozen=True, slots=True)
class MethodResolution:
    schema_version: str
    resolution_id: str
    task_ref: str
    status: str
    mode_decision: Mapping[str, Any]
    action_selections: tuple[ActionSelection, ...]
    method_obligations: tuple[Mapping[str, Any], ...]
    mechanism_resolutions: tuple[Mapping[str, Any], ...]
    capability_requirements: tuple[Mapping[str, Any], ...]
    human_gates: tuple[Mapping[str, Any], ...]
    rejected_alternatives: tuple[Mapping[str, Any], ...]
    decision_records: tuple[Mapping[str, Any], ...]
    unresolved: tuple[str, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MethodResolution":
        status = require_string(data, "status")
        allowed_statuses = {"resolved", "human-required", "blocked", "split-required"}
        if status not in allowed_statuses:
            raise ContractError("status", f"must be one of {sorted(allowed_statuses)}")
        actions = tuple(
            ActionSelection.from_mapping(item) for item in mapping_tuple(data, "action_selections")
        )
        action_ids = tuple(action.action_id for action in actions)
        ensure_unique(action_ids, "action_selections.action_id")
        if not actions:
            raise ContractError("action_selections", "must not be empty")

        mechanisms = mapping_tuple(data, "mechanism_resolutions")
        mechanism_ids = tuple(require_string(item, "action_id") for item in mechanisms)
        if set(mechanism_ids) != set(action_ids):
            raise ContractError(
                "mechanism_resolutions",
                "must resolve every selected, inherited, or candidate-gap action exactly once",
            )
        ensure_unique(mechanism_ids, "mechanism_resolutions.action_id")

        human_gates = mapping_tuple(data, "human_gates")
        if status == "human-required" and not human_gates:
            raise ContractError("human_gates", "human-required resolution must name a gate")
        unresolved = string_tuple(data, "unresolved")
        if status in {"blocked", "split-required"} and not unresolved:
            raise ContractError("unresolved", f"{status} resolution must preserve unresolved work")

        capability_requirements = mapping_tuple(data, "capability_requirements")
        requirement_ids = tuple(
            require_string(item, "requirement_id") for item in capability_requirements
        )
        ensure_unique(requirement_ids, "capability_requirements.requirement_id")
        for item in capability_requirements:
            require_string(item, "capability_id")

        return cls(
            schema_version=require_string(data, "schema_version"),
            resolution_id=require_string(data, "resolution_id"),
            task_ref=require_string(data, "task_ref"),
            status=status,
            mode_decision=dict(mapping_value(data, "mode_decision", required=True)),
            action_selections=actions,
            method_obligations=mapping_tuple(data, "method_obligations"),
            mechanism_resolutions=mechanisms,
            capability_requirements=capability_requirements,
            human_gates=human_gates,
            rejected_alternatives=mapping_tuple(data, "rejected_alternatives"),
            decision_records=mapping_tuple(data, "decision_records"),
            unresolved=unresolved,
        )

    @property
    def provider_neutral(self) -> bool:
        forbidden = {"provider", "model", "host", "adapter", "endpoint"}

        def contains_forbidden(value: Any) -> bool:
            if isinstance(value, Mapping):
                return any(
                    str(key).lower() in forbidden or contains_forbidden(nested)
                    for key, nested in value.items()
                )
            if isinstance(value, (list, tuple)):
                return any(contains_forbidden(item) for item in value)
            return False

        return not contains_forbidden(
            {
                "mode_decision": self.mode_decision,
                "method_obligations": self.method_obligations,
                "mechanism_resolutions": self.mechanism_resolutions,
                "capability_requirements": self.capability_requirements,
                "human_gates": self.human_gates,
                "rejected_alternatives": self.rejected_alternatives,
                "decision_records": self.decision_records,
            }
        )
