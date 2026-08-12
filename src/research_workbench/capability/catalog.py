from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from research_workbench.io import load_document


DEFAULT_CANDIDATES = Path("registry/skills/candidates.json")


def load_candidates(path: str | Path = DEFAULT_CANDIDATES) -> list[dict[str, Any]]:
    document = load_document(path)
    if not isinstance(document, Mapping) or document.get("registry_kind") != "skill_candidates":
        raise ValueError(f"not a skill candidate registry: {path}")
    candidates = document.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError(f"candidate registry has no candidate list: {path}")
    return [dict(candidate) for candidate in candidates if isinstance(candidate, Mapping)]


def filter_candidates(
    candidates: Iterable[Mapping[str, Any]],
    *,
    status: str | None = None,
    mode: str | None = None,
    capability: str | None = None,
) -> list[Mapping[str, Any]]:
    return [
        candidate
        for candidate in candidates
        if (status is None or candidate.get("status") == status)
        and (mode is None or mode in candidate.get("applicable_modes", []))
        and (capability is None or capability in candidate.get("capabilities", []))
    ]
