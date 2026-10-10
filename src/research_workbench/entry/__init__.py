"""Explicit application entry points over the existing RWB file contracts.

Provider/role executors are supplied by a trusted caller; importing this package
never loads credentials, scans project history, dispatches, or writes state.
"""

from research_workbench.entry.workflow import (
    RoleInvocation, RoleObservation, WorkflowBudget, WorkflowResult, run_research_workflow,
)

__all__ = ["RoleInvocation", "RoleObservation", "WorkflowBudget", "WorkflowResult", "run_research_workflow"]
