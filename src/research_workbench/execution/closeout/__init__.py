"""Crash-consistent file closeout for one bounded API Attempt.

This package deliberately implements a commit-last protocol, not a multi-file
transaction: immutable documents are staged and validated, published by
exclusive hard link, and only then made resumable by publishing Main State.
An unpublished or partially published bundle is therefore unreachable from a
new authoritative checkpoint. A fully validated stage has an exact publication
plan and can resume without re-running the model; an incomplete build fails
closed for explicit recovery.
"""

from __future__ import annotations

from .errors import CloseoutContractSnapshot, CloseoutError, CloseoutPublication, TERMINAL_STATUSES
from .publish import (
    capture_closeout_contracts,
    closeout_api_attempt,
    contract_snapshot_document,
    inspect_committed_closeout,
    resume_staged_closeout,
    validate_closeout_preconditions,
)
from .stage import (
    fail_if_api_attempt_intent_exists,
    record_api_attempt_intent,
    staged_closeout_exists,
)

__all__ = [
    "CloseoutContractSnapshot",
    "CloseoutError",
    "CloseoutPublication",
    "TERMINAL_STATUSES",
    "capture_closeout_contracts",
    "closeout_api_attempt",
    "contract_snapshot_document",
    "fail_if_api_attempt_intent_exists",
    "inspect_committed_closeout",
    "record_api_attempt_intent",
    "resume_staged_closeout",
    "staged_closeout_exists",
    "validate_closeout_preconditions",
]
