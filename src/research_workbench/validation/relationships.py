from __future__ import annotations

from pathlib import Path
from typing import Iterable

from research_workbench.artifacts.integrity import ReferenceStatus, check_file_reference
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
    locked_skills = {_skill_id_from_lock(value) for value in handoff.skill_lock}
    missing_skills = sorted(set(task.required_skills) - locked_skills)
    if missing_skills:
        risks.append(
            ContractRisk(
                "HANDOFF-SKILL-LOSS",
                RiskLevel.BLOCK,
                f"handoff does not lock required skills: {', '.join(missing_skills)}",
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

    if handoff.status == "completed" and not handoff.artifact_refs:
        risks.append(
            ContractRisk(
                "HANDOFF-MISSING-OUTPUT",
                RiskLevel.BLOCK,
                "completed handoff has no artifact references",
            )
        )
    if project_root is not None:
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
