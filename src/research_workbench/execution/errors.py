from __future__ import annotations


class CompileError(ValueError):
    """A blocking condition detected before any model API call.

    Codes are stable identifiers (``TASK-STALE-INPUT``, ``COMPILE-*``) so the
    runner, the CLI, and closeout evidence can reference the exact reason a
    session never started.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


class CloseoutError(ValueError):
    """A blocking condition while staging, validating, or publishing files.

    Codes (``EXEC-CLOSEOUT-*``) distinguish staging crashes, validation
    failures, path conflicts, and post-publish verification failures.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")
