"""Bounded Phase C Research State, Attempt lineage, and Failure candidates."""

from typing import Any

from research_workbench.research_state.closure import (
    ClosureIndex,
    IndexedDocument,
    check_method_trace,
    check_research_attempt_lineage,
    check_research_failure,
    check_research_state,
)


def __getattr__(name: str) -> Any:
    """Load the runner-owned Gate lazily so closure validators stay acyclic."""

    if name in {"GateCase", "run_gate_case", "run_phase_c_gate"}:
        from research_workbench.research_state import gate

        return getattr(gate, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ClosureIndex",
    "IndexedDocument",
    "check_method_trace",
    "check_research_attempt_lineage",
    "check_research_failure",
    "check_research_state",
    "GateCase",
    "run_gate_case",
    "run_phase_c_gate",
]
