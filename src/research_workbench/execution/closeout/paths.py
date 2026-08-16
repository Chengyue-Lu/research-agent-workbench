"""Canonical closeout path layout and root-confined path resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.contracts import is_path_safe_identifier

from .errors import CloseoutError

@dataclass(frozen=True, slots=True)
class _CloseoutPaths:
    attempt_root: str

    @property
    def manifest(self) -> str:
        return f"{self.attempt_root}/transfer-manifest.yaml"

    @property
    def handoff(self) -> str:
        return f"{self.attempt_root}/handoff.yaml"

    @property
    def audit(self) -> str:
        return f"{self.attempt_root}/transfer-audit.yaml"

    @property
    def task_context(self) -> str:
        return f"{self.attempt_root}/context-task.yaml"

    @property
    def attempt(self) -> str:
        return f"{self.attempt_root}/attempt.yaml"

    @property
    def receipt(self) -> str:
        return f"{self.attempt_root}/execution-receipt.yaml"

    @property
    def model_assignment(self) -> str:
        return f"{self.attempt_root}/model-assignment.yaml"

    @property
    def provider_conformance(self) -> str:
        return f"{self.attempt_root}/provider-conformance.yaml"

    @property
    def main_context(self) -> str:
        return f"{self.attempt_root}/context-main.yaml"

    @property
    def main_state(self) -> str:
        return f"{self.attempt_root}/main-state.yaml"

    @property
    def static_final_paths(self) -> tuple[str, ...]:
        return (
            self.manifest,
            self.handoff,
            self.audit,
            self.task_context,
            self.attempt,
            self.receipt,
            self.model_assignment,
            self.main_context,
            self.main_state,
        )


def _stage_path(root: Path, relative: str) -> Path:
    resolved = resolve_within_root(root, relative)
    if resolved is None:
        raise CloseoutError("REF-OUTSIDE-ROOT", relative)
    return resolved


def _stage_locations(
    project_root: Path,
    attempt_id: str,
    *,
    create: bool,
) -> tuple[Path, Path]:
    project = project_root.resolve()
    rw_root = project / ".rwb"
    closeout_root = rw_root / "closeout"
    stage_parent = closeout_root / attempt_id
    stage_root = stage_parent / "tree"
    for path in (rw_root, closeout_root, stage_parent, stage_root):
        if path.is_symlink():
            raise CloseoutError(
                "CLOSEOUT-STAGE-PATH",
                f"staging components must not be symlinks: {path}",
            )
    if create:
        stage_root.mkdir(parents=True, exist_ok=True)
    if stage_parent.exists() and not stage_parent.is_dir():
        raise CloseoutError("CLOSEOUT-STAGE-PATH", "attempt stage is not a directory")
    if stage_root.exists() and not stage_root.is_dir():
        raise CloseoutError("CLOSEOUT-STAGE-PATH", "stage tree is not a directory")
    resolved_closeout = closeout_root.resolve()
    resolved_parent = stage_parent.resolve()
    try:
        resolved_parent.relative_to(resolved_closeout)
        resolved_closeout.relative_to(project)
    except ValueError as exc:
        raise CloseoutError("CLOSEOUT-STAGE-PATH", "staging path escapes the project") from exc
    return stage_parent, stage_root


def _attempt_intent_path(project_root: Path, attempt_id: str, *, create: bool) -> Path:
    if not is_path_safe_identifier(attempt_id):
        raise CloseoutError("CLOSEOUT-ATTEMPT-ID", "attempt_id is not path-safe")
    project = project_root.resolve()
    rw_root = project / ".rwb"
    intent_root = rw_root / "attempt-intents"
    intent_path = intent_root / f"{attempt_id}.yaml"
    for path in (rw_root, intent_root, intent_path):
        if path.is_symlink():
            raise CloseoutError(
                "API-ATTEMPT-INTENT-PATH",
                f"execution intent components must not be symlinks: {path}",
            )
    if create:
        intent_root.mkdir(parents=True, exist_ok=True)
    if intent_root.exists() and not intent_root.is_dir():
        raise CloseoutError("API-ATTEMPT-INTENT-PATH", "intent root is not a directory")
    resolved_root = intent_root.resolve()
    resolved_path = intent_path.resolve()
    try:
        resolved_root.relative_to(project)
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise CloseoutError("API-ATTEMPT-INTENT-PATH", "intent path escapes the project") from exc
    return intent_path


def _final_path(root: Path, relative: str) -> Path:
    resolved = resolve_within_root(root, relative)
    if resolved is None:
        raise CloseoutError("REF-OUTSIDE-ROOT", relative)
    return resolved


def _file_ref(path: str, sha256: str, revision: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"path": path, "sha256": sha256}
    if revision is not None:
        value["revision"] = revision
    return value
