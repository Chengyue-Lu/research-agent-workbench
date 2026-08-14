"""Explicit execution policy defaults for the Task-to-API compiler.

Every bound a child session runs under is either taken from the Task Packet
budget or from one of the named defaults below. The compiler records which
source produced each limit so no bound is silently invented.
"""

from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_SIDE_EFFECTS = frozenset({"read-only", "local-write", "external-write"})


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    default_max_model_turns: int = 6
    default_max_output_tokens_per_turn: int = 4096
    default_max_seconds: float = 600.0
    max_tool_calls: int = 8
    max_parallel_tool_calls: int = 1
    max_tool_result_chars: int = 20000
    max_input_chars: int = 20000
    max_skill_instruction_chars: int = 20000
    max_document_read_chars: int = 20000
    max_total_tokens: int | None = None
    max_provider_reported_cost: float | None = None
    allowed_tool_side_effects: frozenset[str] = frozenset({"read-only"})

    def __post_init__(self) -> None:
        positive_int_fields = (
            "default_max_model_turns",
            "default_max_output_tokens_per_turn",
            "max_tool_calls",
            "max_parallel_tool_calls",
            "max_tool_result_chars",
            "max_input_chars",
            "max_skill_instruction_chars",
            "max_document_read_chars",
        )
        for name in positive_int_fields:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        seconds = self.default_max_seconds
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or seconds <= 0:
            raise ValueError("default_max_seconds must be positive")
        if self.max_total_tokens is not None and (
            isinstance(self.max_total_tokens, bool) or self.max_total_tokens <= 0
        ):
            raise ValueError("max_total_tokens must be positive when supplied")
        if self.max_provider_reported_cost is not None and (
            isinstance(self.max_provider_reported_cost, bool)
            or self.max_provider_reported_cost < 0
        ):
            raise ValueError("max_provider_reported_cost must be non-negative when supplied")
        unknown = sorted(set(self.allowed_tool_side_effects) - SUPPORTED_SIDE_EFFECTS)
        if unknown:
            raise ValueError("unknown allowed tool side effects: " + ", ".join(unknown))
