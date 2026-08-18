from __future__ import annotations

from pathlib import Path
from typing import Iterable

from research_workbench.artifacts.integrity import ReferenceStatus, check_file_reference
from research_workbench.capability.resolver import ResolvedTask
from research_workbench.contracts.common import parse_skill_reference
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.protocol.models import ProjectProtocol
from research_workbench.tasks.models import FileReference, HandoffPacket, TaskPacket


def _skill_id_from_lock(value: str) -> str:
    return value.split("@", 1)[0]


def check_handoff_against_task(
    task: TaskPacket,
    handoff: HandoffPacket,
    *,
    project_root: str | Path | None = None,
    assignment: ResolvedTask | None = None,
) -> list[ContractRisk]:
    risks: list[ContractRisk] = []
    if task.task_id != handoff.task_id:
        risks.append(
            ContractRisk(
                "HANDOFF-TASK-MISMATCH",
                RiskLevel.BLOCK,
                f"handoff task {handoff.task_id!r} does not match {task.task_id!r}",
            )
        )
    locked_skill_ids = {_skill_id_from_lock(value) for value in handoff.skill_lock}
    locked_skill_versions = set(handoff.skill_lock)
    missing_skills = []
    for index, raw_reference in enumerate(task.required_skills):
        reference = parse_skill_reference(raw_reference, f"required_skills[{index}]")
        present = (
            reference.identifier in locked_skill_versions
            if reference.version is not None
            else reference.skill_id in locked_skill_ids
        )
        if not present:
            missing_skills.append(reference.identifier)
    missing_skills.sort()
    if missing_skills:
        risks.append(
            ContractRisk(
                "HANDOFF-SKILL-LOSS",
                RiskLevel.BLOCK,
                f"handoff does not lock required skills: {', '.join(missing_skills)}",
            )
        )

    if assignment is not None:
        if assignment.task_id != task.task_id or assignment.task_revision != task.revision:
            risks.append(
                ContractRisk(
                    "HANDOFF-ASSIGNMENT-TASK-DRIFT",
                    RiskLevel.BLOCK,
                    "Skill Assignment does not match the Task identity or revision",
                )
            )
        if assignment.agent_profile.split("@", 1)[0] != task.agent_profile:
            risks.append(
                ContractRisk(
                    "HANDOFF-ASSIGNMENT-PROFILE-DRIFT",
                    RiskLevel.BLOCK,
                    "Skill Assignment Agent Profile does not match the Task",
                )
            )
        expected_locks = {lock.identifier for lock in assignment.skill_lock}
        actual_locks = set(handoff.skill_lock)
        if expected_locks != actual_locks:
            risks.append(
                ContractRisk(
                    "HANDOFF-ASSIGNMENT-SKILL-DRIFT",
                    RiskLevel.BLOCK,
                    f"handoff Skill lock {sorted(actual_locks)!r} differs from Assignment {sorted(expected_locks)!r}",
                )
            )
        if not handoff.skill_assignment_ref:
            risks.append(
                ContractRisk(
                    "HANDOFF-ASSIGNMENT-MISSING",
                    RiskLevel.BLOCK,
                    "controlled handoff does not retain its Skill Assignment reference",
                )
            )

    expected_inputs = {(ref.path, ref.sha256) for ref in task.input_refs}
    locked_inputs = {(ref.path, ref.sha256) for ref in handoff.input_lock}
    if expected_inputs != locked_inputs:
        risks.append(
            ContractRisk(
                "TASK-STALE-INPUT",
                RiskLevel.BLOCK,
                "handoff input lock differs from the task input references",
            )
        )

    if handoff.status in {"completed", "stage-completed"} and not handoff.artifact_refs:
        risks.append(
            ContractRisk(
                "HANDOFF-MISSING-OUTPUT",
                RiskLevel.BLOCK,
                "completed handoff has no artifact references",
            )
        )
    if handoff.status == "safe-paused":
        if not handoff.unresolved:
            risks.append(
                ContractRisk(
                    "HANDOFF-SAFE-PAUSE-STATE-MISSING",
                    RiskLevel.BLOCK,
                    "safe-paused Handoff must state unfinished work",
                )
            )
        if not handoff.recommended_next_actions:
            risks.append(
                ContractRisk(
                    "HANDOFF-SAFE-PAUSE-NEXT-ACTION-MISSING",
                    RiskLevel.BLOCK,
                    "safe-paused Handoff must provide a bounded resume action",
                )
            )
    if handoff.status == "waiting" and not handoff.human_decision_required:
        risks.append(
            ContractRisk(
                "HANDOFF-WAITING-DECISION-MISSING",
                RiskLevel.BLOCK,
                "waiting Handoff must identify the human decision being awaited",
            )
        )
    if task.handoff_policy.require_transfer_manifest and not handoff.transfer_manifest_ref:
        risks.append(
            ContractRisk(
                "HANDOFF-TRANSFER-MANIFEST-MISSING",
                RiskLevel.BLOCK,
                "Task requires a Handoff Transfer Manifest but the Handoff does not reference one",
            )
        )
    if project_root is not None:
        if handoff.skill_assignment_ref:
            assignment_path = Path(project_root).resolve() / handoff.skill_assignment_ref
            if not assignment_path.is_file():
                risks.append(
                    ContractRisk(
                        "HANDOFF-ASSIGNMENT-MISSING",
                        RiskLevel.BLOCK,
                        f"Skill Assignment does not exist: {handoff.skill_assignment_ref}",
                    )
                )
        for reference in handoff.input_lock:
            check = check_file_reference(project_root, reference)
            if check.status != ReferenceStatus.OK:
                risks.append(
                    ContractRisk(
                        "TASK-STALE-INPUT",
                        RiskLevel.BLOCK,
                        f"{reference.path}: {check.status}",
                    )
                )
        for artifact in handoff.artifact_refs:
            if not (Path(project_root).resolve() / artifact).is_file():
                risks.append(
                    ContractRisk(
                        "HANDOFF-MISSING-OUTPUT",
                        RiskLevel.BLOCK,
                        f"artifact does not exist: {artifact}",
                    )
                )
        if handoff.transfer_manifest_ref:
            manifest_path = Path(project_root).resolve() / handoff.transfer_manifest_ref
            if not manifest_path.is_file():
                risks.append(
                    ContractRisk(
                        "HANDOFF-TRANSFER-MANIFEST-MISSING",
                        RiskLevel.BLOCK,
                        f"Handoff Transfer Manifest does not exist: {handoff.transfer_manifest_ref}",
                    )
                )
    return risks


def check_references(root: str | Path, references: Iterable[FileReference]) -> list[ContractRisk]:
    risks: list[ContractRisk] = []
    for reference in references:
        check = check_file_reference(root, reference)
        if check.status == ReferenceStatus.MISSING:
            risks.append(ContractRisk("REF-MISSING", RiskLevel.BLOCK, f"missing file: {reference.path}"))
        elif check.status == ReferenceStatus.HASH_MISMATCH:
            risks.append(
                ContractRisk(
                    "REF-HASH-MISMATCH",
                    RiskLevel.BLOCK,
                    f"stale reference {reference.path}: expected {reference.sha256}, got {check.actual_sha256}",
                )
            )
        elif check.status == ReferenceStatus.OUTSIDE_ROOT:
            risks.append(
                ContractRisk("REF-OUTSIDE-ROOT", RiskLevel.BLOCK, f"reference escapes project root: {reference.path}")
            )
    return risks


def _scope_anchor(scope: str) -> str:
    parts: list[str] = []
    for part in scope.replace("\\", "/").split("/"):
        if any(marker in part for marker in ("*", "?", "[")):
            break
        if part:
            parts.append(part)
    return "/".join(parts)


def check_write_scope_overlap(tasks: Iterable[TaskPacket]) -> list[ContractRisk]:
    """Conservatively flag tasks whose non-glob path prefixes overlap."""

    task_list = tuple(tasks)
    risks: list[ContractRisk] = []
    for left_index, left in enumerate(task_list):
        for right in task_list[left_index + 1 :]:
            collisions: list[str] = []
            for left_scope in left.write_scope:
                left_anchor = _scope_anchor(left_scope)
                for right_scope in right.write_scope:
                    right_anchor = _scope_anchor(right_scope)
                    if not left_anchor or not right_anchor:
                        collisions.append(f"{left_scope} <> {right_scope}")
                    elif (
                        left_anchor == right_anchor
                        or left_anchor.startswith(right_anchor + "/")
                        or right_anchor.startswith(left_anchor + "/")
                    ):
                        collisions.append(f"{left_scope} <> {right_scope}")
            if collisions:
                risks.append(
                    ContractRisk(
                        "TASK-WRITE-OVERLAP",
                        RiskLevel.BLOCK,
                        f"{left.task_id} and {right.task_id} have overlapping write scopes: "
                        + "; ".join(collisions),
                    )
                )
    return risks


def check_claim_ceiling(protocol: ProjectProtocol, claim_strength: str) -> list[ContractRisk]:
    if claim_strength in {"unresolved", "withdrawn"} or claim_strength in protocol.claim_ceiling:
        return []
    return [
        ContractRisk(
            "CLAIM-OVERREACH",
            RiskLevel.BLOCK,
            f"claim strength {claim_strength!r} is outside project ceiling {list(protocol.claim_ceiling)!r}",
        )
    ]
