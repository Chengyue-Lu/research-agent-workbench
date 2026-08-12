from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    mapping_tuple,
    optional_string,
    require_relative_path,
    require_string,
    string_tuple,
)


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

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MainStatePacket":
        index_refs = string_tuple(data, "artifact_index_refs")
        for index, ref in enumerate(index_refs):
            require_relative_path(ref, f"artifact_index_refs[{index}]")
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
        )
