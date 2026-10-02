"""Validate and publish a new, redacted profile conformance report file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from research_workbench.validation.schemas import SchemaCatalog


def write_profile_conformance_report(
    report: Mapping[str, object], destination: str | Path, *, schema_root: str | Path | None = None,
) -> None:
    """No overwrite or credential access; structural validity is not acceptance."""
    serialized = None
    try:
        serialized = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    except (TypeError, ValueError, OverflowError, RecursionError):
        pass
    if serialized is None:
        raise ValueError("profile conformance report requires finite JSON primitives")
    detached = json.loads(serialized)
    if SchemaCatalog(schema_root).validate("profile_conformance_report", detached):
        raise ValueError("profile conformance report violates its closed contract")
    # 'x' refuses every existing target, including symlinks and directories.
    # An interrupted first write remains visible; retry must choose a fresh path.
    with Path(destination).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
