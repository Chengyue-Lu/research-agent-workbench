"""Task-to-API execution workstream (K-API-2).

The package compiles frozen research contracts into one fresh, bounded API
child session and closes it out atomically into formal research files.
"""

from research_workbench.execution.artifacts import (
    SessionOutcome,
    build_closeout_documents,
    outcome_from_result,
)
from research_workbench.execution.closeout import (
    PUBLISH_ORDER,
    CloseoutDocument,
    CloseoutError,
    CloseoutPlan,
    CloseoutResult,
    ROLE_KINDS,
    run_closeout,
    serialize_document,
)
from research_workbench.execution.compiler import (
    EVIDENCE_OUTPUT_SCHEMA,
    OUTPUT_CONTRACT_SCHEMAS,
    CompileReport,
    CompiledSession,
    compile_session,
)
from research_workbench.execution.errors import CompileError
from research_workbench.execution.options import ExecutionPolicy
from research_workbench.execution.status import CloseoutStatuses, map_outcome
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
    "PUBLISH_ORDER",
    "ROLE_KINDS",
    "CloseoutDocument",
    "CloseoutError",
    "CloseoutPlan",
    "CloseoutResult",
    "CloseoutStatuses",
    "CompileError",
    "CompileReport",
    "CompiledSession",
    "ExecutionPolicy",
    "SessionOutcome",
    "SessionToolLog",
    "ToolCallRecord",
    "build_client_tools",
    "build_closeout_documents",
    "compile_session",
    "map_outcome",
    "outcome_from_result",
    "run_closeout",
    "serialize_document",
]
