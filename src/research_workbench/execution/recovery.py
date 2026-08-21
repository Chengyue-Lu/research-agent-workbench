"""File-only recovery preflight that always targets a new Attempt."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.context import MainStatePacket
from research_workbench.contracts import ContractError, ContractRisk, RiskLevel
from research_workbench.execution.archive import (
    ATTEMPT_FILENAME,
    verify_execution_archive,
)
from research_workbench.io import load_document
from research_workbench.tasks import AttemptRecord, FileReference, HandoffPacket
from research_workbench.validation.relationships import check_references
from research_workbench.validation.schemas import SchemaCatalog


@dataclass(frozen=True, slots=True)
class RecoverySeed:
    task_id: str
    task_revision: int
    previous_attempt_id: str
    new_attempt_id: str
    new_attempt_dir: str
    input_lock: tuple[FileReference, ...]
    skill_lock: tuple[str, ...]
    skill_assignment_ref: str | None
    previous_trace_ref: FileReference
    handoff_ref: str
    main_state_ref: str


@dataclass(frozen=True, slots=True)
class RecoveryPreparation:
    seed: RecoverySeed | None
    risks: tuple[ContractRisk, ...]

    @property
    def blocked(self) -> bool:
        return any(risk.level == RiskLevel.BLOCK for risk in self.risks)


def _risk(code: str, level: RiskLevel, message: str) -> ContractRisk:
    return ContractRisk(code, level, message)


def _load_mapping(path: Path, label: str, risks: list[ContractRisk]) -> Mapping | None:
    try:
        document = load_document(path)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        risks.append(_risk("RECOVERY-SOURCE-INVALID", RiskLevel.BLOCK, f"{label}: {exc}"))
        return None
    if not isinstance(document, Mapping):
        risks.append(_risk("RECOVERY-SOURCE-INVALID", RiskLevel.BLOCK, f"{label} is not an object"))
        return None
    return document


def prepare_recovery_attempt(
    *,
    root: str | Path,
    previous_attempt_dir: str | Path,
    main_state: str | Path,
    protocol: str | Path,
    new_attempt_id: str,
    new_attempt_dir: str | Path,
) -> RecoveryPreparation:
    """Validate frozen state and return a seed without creating the new Attempt."""

    project_root = Path(root).resolve()
    archive_risks = list(
        verify_execution_archive(
            previous_attempt_dir,
            root=project_root,
            protocol=protocol,
        )
    )
    if any(risk.level == RiskLevel.BLOCK for risk in archive_risks):
        archive_risks.append(
            _risk(
                "RECOVERY-PREVIOUS-INVALID",
                RiskLevel.BLOCK,
                "previous Attempt archive does not pass file-only replay",
            )
        )
        return RecoveryPreparation(None, tuple(archive_risks))

    raw_previous = Path(previous_attempt_dir)
    previous_dir = (
        raw_previous if raw_previous.is_absolute() else project_root / raw_previous
    ).resolve()
    risks = archive_risks
    attempt_document = _load_mapping(previous_dir / ATTEMPT_FILENAME, "previous Attempt", risks)
    if attempt_document is None:
        return RecoveryPreparation(None, tuple(risks))
    try:
        attempt = AttemptRecord.from_mapping(attempt_document)
    except ContractError as exc:
        risks.append(_risk("RECOVERY-SOURCE-INVALID", RiskLevel.BLOCK, str(exc)))
        return RecoveryPreparation(None, tuple(risks))
    if attempt.status != "safe-paused":
        risks.append(
            _risk(
                "RECOVERY-STATUS-INVALID",
                RiskLevel.BLOCK,
                "recovery currently requires a safe-paused previous Attempt",
            )
        )
    if not attempt.handoff_ref:
        risks.append(
            _risk("RECOVERY-HANDOFF-MISSING", RiskLevel.BLOCK, "previous Attempt has no Handoff")
        )
        handoff = None
    else:
        handoff_path = resolve_within_root(project_root, attempt.handoff_ref)
        handoff_document = (
            _load_mapping(handoff_path, "Handoff", risks)
            if handoff_path is not None and handoff_path.is_file()
            else None
        )
        if handoff_document is None:
            risks.append(
                _risk(
                    "RECOVERY-HANDOFF-MISSING",
                    RiskLevel.BLOCK,
                    "previous Handoff is missing or outside the project root",
                )
            )
            handoff = None
        else:
            try:
                handoff = HandoffPacket.from_mapping(handoff_document)
            except ContractError as exc:
                risks.append(_risk("RECOVERY-SOURCE-INVALID", RiskLevel.BLOCK, str(exc)))
                handoff = None
    if handoff is not None and (
        handoff.task_id != attempt.task_id
        or handoff.attempt_id != attempt.attempt_id
        or handoff.status != attempt.status
        or handoff.input_lock != attempt.input_lock
        or handoff.skill_lock != attempt.skill_lock
    ):
        risks.append(
            _risk(
                "RECOVERY-HANDOFF-MISMATCH",
                RiskLevel.BLOCK,
                "Handoff identity, status, input lock, or Skill lock differs from Attempt",
            )
        )

    raw_state = Path(main_state)
    state_path = raw_state if raw_state.is_absolute() else project_root / raw_state
    state_path = state_path.resolve()
    try:
        state_relative = state_path.relative_to(project_root).as_posix()
    except ValueError:
        state_relative = ""
    state_document = (
        _load_mapping(state_path, "Main State", risks)
        if state_relative and state_path.is_file()
        else None
    )
    state = None
    if state_document is None:
        risks.append(
            _risk(
                "RECOVERY-STATE-MISSING",
                RiskLevel.BLOCK,
                "Main State is missing or outside the project root",
            )
        )
    else:
        schema_errors = SchemaCatalog().validate("main_state", state_document)
        risks.extend(
            _risk(
                "RECOVERY-SOURCE-INVALID",
                RiskLevel.BLOCK,
                f"Main State{error.pointer}: {error.message}",
            )
            for error in schema_errors
        )
        try:
            state = MainStatePacket.from_mapping(state_document)
        except ContractError as exc:
            risks.append(_risk("RECOVERY-SOURCE-INVALID", RiskLevel.BLOCK, str(exc)))
    if state is not None:
        risks.extend(check_references(project_root, state.machine_state_refs))
        active = {
            item.task_id: (item.status, item.expected_handoff)
            for item in state.active_tasks
        }
        recent = {item.ref for item in state.recent_handoffs}
        expected = active.get(attempt.task_id)
        if (
            state.continuity_status != "safe-paused"
            or expected != ("safe-paused", attempt.handoff_ref)
            or attempt.handoff_ref not in recent
        ):
            risks.append(
                _risk(
                    "RECOVERY-STATE-MISMATCH",
                    RiskLevel.BLOCK,
                    "Main State does not bind the safe-paused Task and Handoff",
                )
            )

    raw_new_dir = Path(new_attempt_dir)
    target_dir = raw_new_dir if raw_new_dir.is_absolute() else project_root / raw_new_dir
    target_dir = target_dir.resolve()
    try:
        target_relative = target_dir.relative_to(project_root).as_posix()
    except ValueError:
        target_relative = ""
    if (
        not new_attempt_id.strip()
        or new_attempt_id == attempt.attempt_id
        or not target_relative
        or target_dir == previous_dir
        or target_dir.exists()
    ):
        risks.append(
            _risk(
                "RECOVERY-ATTEMPT-REUSE",
                RiskLevel.BLOCK,
                "recovery must target a distinct, non-existing Attempt directory and ID",
            )
        )
    if attempt.trace_ref is None:
        risks.append(
            _risk(
                "RECOVERY-PREVIOUS-INVALID",
                RiskLevel.BLOCK,
                "previous model-api Attempt has no Trace reference",
            )
        )
    if any(risk.level == RiskLevel.BLOCK for risk in risks):
        return RecoveryPreparation(None, tuple(risks))

    risks.append(
        _risk(
            "RECOVERY-READY",
            RiskLevel.INFO,
            "frozen Main State, Trace, and Handoff can seed a distinct new Attempt",
        )
    )
    return RecoveryPreparation(
        RecoverySeed(
            task_id=attempt.task_id,
            task_revision=attempt.task_revision,
            previous_attempt_id=attempt.attempt_id,
            new_attempt_id=new_attempt_id,
            new_attempt_dir=target_relative,
            input_lock=attempt.input_lock,
            skill_lock=attempt.skill_lock,
            skill_assignment_ref=attempt.skill_assignment_ref,
            previous_trace_ref=attempt.trace_ref,
            handoff_ref=str(attempt.handoff_ref),
            main_state_ref=state_relative,
        ),
        tuple(risks),
    )


__all__ = [
    "RecoveryPreparation",
    "RecoverySeed",
    "prepare_recovery_attempt",
]
