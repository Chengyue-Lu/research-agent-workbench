"""Closed registry of trusted client-tool factories for API execution.

The registry performs exact contract/Assignment admission before constructing
any tool.  It has no dynamic registration, ranking, fallback, or general code
execution surface.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

from research_workbench.adapters.models import ApiSessionLimits, ClientTool
from research_workbench.execution.tools import (
    build_bounded_compute_tool,
    build_document_read_tool,
    build_frozen_text_read_tool,
)
from research_workbench.tasks import TaskPacket


class ExecutionToolContract(Protocol):
    tool_names: frozenset[str]


class ExecutionToolAssignment(Protocol):
    resolved_tools: tuple[str, ...]


class ExecutionToolRegistryError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


ToolFactory = Callable[[str | Path, TaskPacket, ApiSessionLimits], ClientTool]


def _document_read_factory(
    root: str | Path,
    task: TaskPacket,
    limits: ApiSessionLimits,
) -> ClientTool:
    return build_document_read_tool(
        root,
        task,
        max_bytes=limits.max_tool_result_chars,
    )


def _file_read_factory(
    root: str | Path,
    task: TaskPacket,
    limits: ApiSessionLimits,
) -> ClientTool:
    return build_frozen_text_read_tool(
        "file-read",
        root,
        task,
        max_bytes=limits.max_tool_result_chars,
    )


def _bounded_compute_factory(
    root: str | Path,
    task: TaskPacket,
    limits: ApiSessionLimits,
) -> ClientTool:
    del root, task
    return build_bounded_compute_tool(
        max_values_per_call=limits.max_compute_values_per_call
    )


_TRUSTED_FACTORIES: Mapping[str, ToolFactory] = MappingProxyType(
    {
        "document-read": _document_read_factory,
        "file-read": _file_read_factory,
        "bounded-compute": _bounded_compute_factory,
    }
)


class ExecutionToolRegistry:
    """Construct only the exact trusted tools frozen by a contract and Assignment."""

    __slots__ = ()

    @property
    def trusted_tool_names(self) -> frozenset[str]:
        return frozenset(_TRUSTED_FACTORIES)

    def build_tools(
        self,
        *,
        root: str | Path,
        task: TaskPacket,
        limits: ApiSessionLimits,
        contract: ExecutionToolContract,
        assignment: ExecutionToolAssignment,
    ) -> tuple[ClientTool, ...]:
        contract_names = _validated_tool_sequence(
            getattr(contract, "tool_names", None),
            "contract.tool_names",
        )
        assignment_names = _validated_tool_sequence(
            getattr(assignment, "resolved_tools", None),
            "assignment.resolved_tools",
        )
        if not contract_names or not assignment_names:
            raise ExecutionToolRegistryError(
                "EXECUTION-TOOL-EMPTY",
                "contract and Assignment must each freeze at least one tool",
            )

        unknown = tuple(
            dict.fromkeys(
                name
                for name in (*contract_names, *assignment_names)
                if name not in _TRUSTED_FACTORIES
            )
        )
        if unknown:
            raise ExecutionToolRegistryError(
                "EXECUTION-TOOL-UNKNOWN",
                "untrusted tool name: " + ", ".join(unknown),
            )
        if frozenset(contract_names) != frozenset(assignment_names):
            raise ExecutionToolRegistryError(
                "EXECUTION-TOOL-MISMATCH",
                "contract.tool_names and assignment.resolved_tools must match exactly",
            )

        built: list[ClientTool] = []
        for name in assignment_names:
            tool = _TRUSTED_FACTORIES[name](root, task, limits)
            if tool.definition.name != name:
                raise ExecutionToolRegistryError(
                    "EXECUTION-TOOL-FACTORY",
                    f"trusted factory returned the wrong tool for {name}",
                )
            built.append(tool)
        return tuple(built)


def default_execution_tool_registry() -> ExecutionToolRegistry:
    return _DEFAULT_EXECUTION_TOOL_REGISTRY


def _validated_tool_sequence(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list, set, frozenset)):
        raise ExecutionToolRegistryError(
            "EXECUTION-TOOL-NAMES",
            f"{field} must be a concrete collection of normalized tool names",
        )
    names = tuple(value)
    if any(
        not isinstance(name, str) or not name or name != name.strip()
        for name in names
    ):
        raise ExecutionToolRegistryError(
            "EXECUTION-TOOL-NAMES",
            f"{field} contains an invalid tool name",
        )
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in names:
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)
    if duplicates:
        raise ExecutionToolRegistryError(
            "EXECUTION-TOOL-DUPLICATE",
            f"{field} repeats: " + ", ".join(duplicates),
        )
    return names


_DEFAULT_EXECUTION_TOOL_REGISTRY = ExecutionToolRegistry()
