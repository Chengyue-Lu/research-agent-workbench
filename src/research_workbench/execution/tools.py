"""Bounded, read-only client tools for isolated API child sessions.

Client tools are the only executable surface a child session can reach. Each
tool stays inside its declared side-effect class, reads only declared task
inputs or effective allowed roots, refuses oversized documents instead of
truncating them, and records every call in a session tool log.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from research_workbench.adapters.models import ClientTool, ToolDefinition
from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.execution.errors import CompileError


DOCUMENT_READ_NAME = "document-read"

DOCUMENT_READ_DEFINITION = ToolDefinition(
    name=DOCUMENT_READ_NAME,
    description=(
        "Read one bounded document from the declared task inputs or the "
        "effective allowed roots. Returns the full document text."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Repository-relative document path.",
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    },
)

TOOL_NAMES = frozenset({DOCUMENT_READ_NAME})


class ToolCallRecord:
    """One executed (or rejected) client-tool call, kept for closeout evidence."""

    __slots__ = ("name", "arguments", "ok", "error", "result_chars")

    def __init__(
        self,
        name: str,
        arguments: Mapping[str, Any],
        ok: bool,
        error: str | None,
        result_chars: int,
    ) -> None:
        self.name = name
        self.arguments = dict(arguments)
        self.ok = ok
        self.error = error
        self.result_chars = result_chars


class SessionToolLog:
    """Append-only record of the client-tool calls of one attempt."""

    def __init__(self) -> None:
        self._records: list[ToolCallRecord] = []

    def record(self, entry: ToolCallRecord) -> None:
        self._records.append(entry)

    @property
    def records(self) -> tuple[ToolCallRecord, ...]:
        return tuple(self._records)

    @property
    def failures(self) -> tuple[ToolCallRecord, ...]:
        return tuple(record for record in self._records if not record.ok)


def build_client_tools(
    tool_names: tuple[str, ...],
    *,
    root: Path,
    readable_paths: tuple[str, ...],
    allowed_roots: tuple[str, ...],
    max_read_chars: int,
    log: SessionToolLog,
) -> tuple[ClientTool, ...]:
    """Build the declared client tools; unknown names are a compile blocker."""

    unknown = sorted(set(tool_names) - TOOL_NAMES)
    if unknown:
        raise CompileError(
            "COMPILE-TOOL-UNAVAILABLE",
            "no client tool implementation for: " + ", ".join(unknown),
        )
    builders = {DOCUMENT_READ_NAME: _document_read_tool}
    return tuple(
        builders[name](
            root=root,
            readable_paths=readable_paths,
            allowed_roots=allowed_roots,
            max_read_chars=max_read_chars,
            log=log,
        )
        for name in tool_names
    )


def _document_read_tool(
    *,
    root: Path,
    readable_paths: tuple[str, ...],
    allowed_roots: tuple[str, ...],
    max_read_chars: int,
    log: SessionToolLog,
) -> ClientTool:
    def execute(arguments: Mapping[str, Any]) -> str:
        raw_path = arguments.get("path")
        normalized = raw_path.replace("\\", "/").lstrip("/") if isinstance(raw_path, str) else ""
        try:
            content = _read_bounded(
                root, normalized, readable_paths, allowed_roots, max_read_chars
            )
        except Exception as exc:
            log.record(
                ToolCallRecord(DOCUMENT_READ_NAME, arguments, False, type(exc).__name__, 0)
            )
            raise
        log.record(ToolCallRecord(DOCUMENT_READ_NAME, arguments, True, None, len(content)))
        return content

    return ClientTool(DOCUMENT_READ_DEFINITION, execute, side_effect="read-only")


def _read_bounded(
    root: Path,
    normalized: str,
    readable_paths: tuple[str, ...],
    allowed_roots: tuple[str, ...],
    max_read_chars: int,
) -> str:
    if not normalized:
        raise ValueError("document-read requires a non-empty path")
    if PurePosixPath(normalized).is_absolute() or ".." in PurePosixPath(normalized).parts:
        raise PermissionError(f"path is not repository-relative: {normalized}")
    if normalized not in readable_paths and not _within_roots(normalized, allowed_roots):
        raise PermissionError(
            "path is not a declared input or allowed root: " + normalized
        )
    resolved = resolve_within_root(root, normalized)
    if resolved is None:
        raise PermissionError("path escapes the project root: " + normalized)
    if not resolved.is_file():
        raise FileNotFoundError("document not found: " + normalized)
    size = resolved.stat().st_size
    if size > max_read_chars:
        raise ValueError(
            f"document exceeds the read cap ({size} > {max_read_chars} chars): {normalized}"
        )
    return resolved.read_text(encoding="utf-8")


def _within_roots(path: str, allowed_roots: tuple[str, ...]) -> bool:
    return any(
        path == root or path.startswith(root.rstrip("/") + "/") for root in allowed_roots
    )
