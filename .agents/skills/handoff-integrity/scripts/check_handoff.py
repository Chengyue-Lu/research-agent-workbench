#!/usr/bin/env python3
"""Validate one Handoff Packet against a Task Packet and live repository files."""

from __future__ import annotations

import argparse
from pathlib import Path

from research_workbench.capability import ResolvedTask
from research_workbench.context import assess_handoff_transfer
from research_workbench.io import load_document
from research_workbench.tasks import FileReference, HandoffPacket, TaskPacket
from research_workbench.validation import check_handoff_against_task, check_references


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("handoff")
    parser.add_argument("--task", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--audit")
    args = parser.parse_args()

    task = TaskPacket.from_mapping(load_document(args.task))
    handoff = HandoffPacket.from_mapping(load_document(args.handoff))
    assignment = None
    if handoff.skill_assignment_ref:
        assignment = ResolvedTask.from_mapping(
            load_document(Path(args.root) / handoff.skill_assignment_ref)
        )
    risks = check_handoff_against_task(
        task,
        handoff,
        project_root=args.root,
        assignment=assignment,
    )
    if assignment is not None:
        risks.extend(
            check_references(
                args.root,
                (
                    FileReference(lock.source_locator, lock.content_hash.removeprefix("sha256:"))
                    for lock in assignment.skill_lock
                    if lock.source_locator
                ),
            )
        )
    if args.audit:
        assessment = assess_handoff_transfer(load_document(args.audit), root=args.root)
        print(
            f"HANDOFF-TRANSFER verdict={assessment.verdict} "
            f"review_required={str(assessment.review_required).lower()}"
        )
        risks.extend(assessment.risks)
    blocked = False
    for risk in risks:
        print(f"{risk.level.upper()} {risk.code} {risk.message}")
        blocked = blocked or risk.level == "block"
    if blocked:
        return 1
    print("OK handoff integrity checks passed; scientific correctness was not evaluated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
