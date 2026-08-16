"""Shared error and value types for the crash-consistent closeout package."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TERMINAL_STATUSES = frozenset(
    {"completed", "stage-completed", "safe-paused", "blocked", "incomplete", "failed"}
)
_TERMINAL_STATUSES = TERMINAL_STATUSES
_RFC3339_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class CloseoutError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class CloseoutPublication:
    status: str
    main_state_ref: str
    published_refs: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CloseoutContractSnapshot:
    """Exact pre-execution bytes for one trusted closeout contract."""

    ref: str
    kind: str
    sha256: str
    payload: bytes = field(repr=False)
