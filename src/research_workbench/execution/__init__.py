"""Task-to-API execution workstream (K-API-2).

The package compiles frozen research contracts into one fresh, bounded API
child session and closes it out atomically into formal research files.
"""

from research_workbench.execution.compiler import (
    EVIDENCE_OUTPUT_SCHEMA,
    OUTPUT_CONTRACT_SCHEMAS,
    CompileReport,
    CompiledSession,
    compile_session,
)
from research_workbench.execution.errors import CompileError
from research_workbench.execution.options import ExecutionPolicy
from research_workbench.execution.tools import (
    DOCUMENT_READ_DEFINITION,
    DOCUMENT_READ_NAME,
    SessionToolLog,
    ToolCallRecord,
    build_client_tools,
)

__all__ = [
    "DOCUMENT_READ_DEFINITION",
    "DOCUMENT_READ_NAME",
    "EVIDENCE_OUTPUT_SCHEMA",
    "OUTPUT_CONTRACT_SCHEMAS",
    "CompileError",
    "CompileReport",
    "CompiledSession",
    "ExecutionPolicy",
    "SessionToolLog",
    "ToolCallRecord",
    "build_client_tools",
    "compile_session",
]
