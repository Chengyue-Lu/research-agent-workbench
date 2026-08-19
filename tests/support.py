"""Shared path constants and workspace helpers for tests.

New tests should import these instead of re-deriving repository paths from
__file__. Existing tests keep their local constants; this module only adds
a common home for new test code.
"""

from __future__ import annotations

import contextlib
import tempfile
from collections.abc import Iterator
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
REGISTRY = ROOT / "registry"
FIXTURES = ROOT / "tests" / "fixtures"


@contextlib.contextmanager
def temporary_workspace() -> Iterator[Path]:
    """Yield one fresh temporary directory as a Path for a test."""
    with tempfile.TemporaryDirectory() as directory:
        yield Path(directory)
