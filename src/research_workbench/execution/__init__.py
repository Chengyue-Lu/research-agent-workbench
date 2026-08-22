"""K-API-2 Task-to-API file loop plus the legacy execution compatibility seam.

The shared artifact filenames (attempt.yaml, execution-receipt.yaml,
session-transcript.json) are defined identically by ``archive`` (legacy
line) and ``models`` (K-API-2 line); the package exports them once and
guards the equality so the two lines cannot drift apart silently.
"""

from research_workbench.execution import archive, models
from research_workbench.execution.archive import (
    ATTEMPT_FILENAME,
    ArchiveCloseoutResult,
    COMPLETION_MANIFEST_FILENAME,
    RECEIPT_FILENAME,
    TRANSCRIPT_FILENAME,
    finalize_execution_archive,
    verify_execution_archive,
)
from research_workbench.execution.models import (
    ATTEMPT_DIRNAME_OUTPUTS,
    CHECK_REPORT_FILENAME,
    CLOSEOUT_STATUSES,
    HANDOFF_FILENAME,
    PLAN_FILENAME,
    CloseoutResult,
    ExecutionPlan,
    ExecutionPlanError,
    ExecutionRunResult,
    ModelBinding,
    ToolEvent,
)
from research_workbench.execution.recovery import (
    RecoveryPreparation,
    RecoverySeed,
    prepare_recovery_attempt,
)
from research_workbench.execution.runner import execute_plan
from research_workbench.execution.trace_adapter import TracedSessionResult, run_traced_session

assert (
    archive.ATTEMPT_FILENAME == models.ATTEMPT_FILENAME
    and archive.RECEIPT_FILENAME == models.RECEIPT_FILENAME
    and archive.TRANSCRIPT_FILENAME == models.TRANSCRIPT_FILENAME
), "legacy archive and K-API-2 artifact filenames must stay identical"

__all__ = [
    "ATTEMPT_DIRNAME_OUTPUTS",
    "ATTEMPT_FILENAME",
    "ArchiveCloseoutResult",
    "CHECK_REPORT_FILENAME",
    "CLOSEOUT_STATUSES",
    "COMPLETION_MANIFEST_FILENAME",
    "HANDOFF_FILENAME",
    "PLAN_FILENAME",
    "RECEIPT_FILENAME",
    "RecoveryPreparation",
    "RecoverySeed",
    "TRANSCRIPT_FILENAME",
    "CloseoutResult",
    "ExecutionPlan",
    "ExecutionPlanError",
    "ExecutionRunResult",
    "ModelBinding",
    "ToolEvent",
    "TracedSessionResult",
    "execute_plan",
    "finalize_execution_archive",
    "prepare_recovery_attempt",
    "run_traced_session",
    "verify_execution_archive",
]
