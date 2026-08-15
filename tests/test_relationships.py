import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from research_workbench.artifacts import hash_file
from research_workbench.capability import AgentProfile, ResolutionError, SkillManifest, resolve_task
from research_workbench.contracts import ContractError
from research_workbench.io import load_document
from research_workbench.tasks import FileReference, HandoffPacket, TaskPacket
from research_workbench.protocol import ProjectProtocol
from research_workbench.validation import (
    RiskLevel,
    check_handoff_against_task,
    check_claim_ceiling,
    check_references,
    check_task_binding,
    check_write_scope_overlap,
)


ROOT = Path(__file__).resolve().parents[1]


class RelationshipValidationTests(unittest.TestCase):
    def load(self, relative: str):
        return load_document(ROOT / relative)

    def test_evidence_task_binding_has_no_blocking_gap(self) -> None:
        task = TaskPacket.from_mapping(self.load("examples/task-evidence.yaml"))
        profile = AgentProfile.from_mapping(self.load("examples/profiles/evidence-scout.yaml"))
        skill = SkillManifest.from_mapping(self.load("examples/skills/literature-evidence-extraction.yaml"))
        risks = check_task_binding(task, profile, [skill])
        self.assertEqual([], [risk for risk in risks if risk.level == RiskLevel.BLOCK])

    def test_handoff_matches_task_and_live_input_hash(self) -> None:
        task = TaskPacket.from_mapping(self.load("examples/task-evidence.yaml"))
        handoff = HandoffPacket.from_mapping(self.load("examples/handoff-evidence.yaml"))
        self.assertEqual([], check_handoff_against_task(task, handoff, project_root=ROOT))

    def test_failed_handoff_without_research_artifacts_does_not_fabricate_manifest(self) -> None:
        task = TaskPacket.from_mapping(self.load("examples/task-evidence.yaml"))
        baseline = HandoffPacket.from_mapping(self.load("examples/handoff-evidence.yaml"))
        failed = replace(
            baseline,
            status="failed",
            artifact_refs=(),
            validation_refs=(),
            transfer_manifest_ref=None,
        )
        codes = {risk.code for risk in check_handoff_against_task(task, failed)}
        self.assertNotIn("HANDOFF-TRANSFER-MANIFEST-MISSING", codes)

    def test_persisted_partial_artifacts_still_require_transfer_manifest(self) -> None:
        task = TaskPacket.from_mapping(self.load("examples/task-evidence.yaml"))
        baseline = HandoffPacket.from_mapping(self.load("examples/handoff-evidence.yaml"))
        partial = replace(baseline, status="safe-paused", transfer_manifest_ref=None)
        codes = {risk.code for risk in check_handoff_against_task(task, partial)}
        self.assertIn("HANDOFF-TRANSFER-MANIFEST-MISSING", codes)

    def test_handoff_references_reject_drive_relative_and_outside_paths(self) -> None:
        document = self.load("examples/handoff-evidence.yaml")
        document["artifact_refs"] = ["C:outside.yaml"]
        with self.assertRaises(ContractError):
            HandoffPacket.from_mapping(document)

        task = TaskPacket.from_mapping(self.load("examples/task-evidence.yaml"))
        baseline = HandoffPacket.from_mapping(self.load("examples/handoff-evidence.yaml"))
        escaped = replace(baseline, artifact_refs=("../outside.yaml",))
        codes = {
            risk.code
            for risk in check_handoff_against_task(task, escaped, project_root=ROOT)
        }
        self.assertIn("HANDOFF-REF-OUTSIDE-ROOT", codes)

    def test_missing_skill_and_capability_are_both_reported(self) -> None:
        task = TaskPacket.from_mapping(self.load("examples/task-evidence.yaml"))
        profile = AgentProfile.from_mapping(self.load("examples/profiles/evidence-scout.yaml"))
        codes = {risk.code for risk in check_task_binding(task, profile, [])}
        self.assertIn("SKILL-MISSING", codes)
        self.assertIn("TASK-SKILL-MISMATCH", codes)

    def test_changed_file_marks_reference_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "input.txt"
            target.write_text("before", encoding="utf-8")
            reference = FileReference("input.txt", hash_file(target))
            target.write_text("after", encoding="utf-8")
            risks = check_references(root, [reference])
            self.assertEqual(["REF-HASH-MISMATCH"], [risk.code for risk in risks])

    def test_claim_above_project_ceiling_is_blocked(self) -> None:
        protocol = ProjectProtocol.from_mapping(self.load("examples/project-protocol.yaml"))
        risks = check_claim_ceiling(protocol, "experimentally_supported")
        self.assertEqual(["CLAIM-OVERREACH"], [risk.code for risk in risks])

    def test_overlapping_write_scopes_are_blocked(self) -> None:
        evidence = TaskPacket.from_mapping(self.load("examples/task-evidence.yaml"))
        duplicate = replace(evidence, task_id="EVID-002", write_scope=("work/EVID-001/shared/**",))
        risks = check_write_scope_overlap([evidence, duplicate])
        self.assertEqual(["TASK-WRITE-OVERLAP"], [risk.code for risk in risks])

    def test_resolver_blocks_write_scope_outside_permission_intersection(self) -> None:
        task = TaskPacket.from_mapping(self.load("examples/task-evidence.yaml"))
        profile = AgentProfile.from_mapping(self.load("examples/profiles/evidence-scout.yaml"))
        skill = SkillManifest.from_mapping(self.load("examples/skills/literature-evidence-extraction.yaml"))
        escaped = replace(task, write_scope=("objects/claims/**",))
        with self.assertRaises(ResolutionError) as caught:
            resolve_task(escaped, profile, [skill])
        self.assertEqual(["TASK-PERMISSION-ESCALATION"], [risk.code for risk in caught.exception.risks])


if __name__ == "__main__":
    unittest.main()
