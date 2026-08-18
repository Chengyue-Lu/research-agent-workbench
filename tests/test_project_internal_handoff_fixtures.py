import unittest
from pathlib import Path

from research_workbench.context import assess_handoff_transfer
from research_workbench.io import load_document
from research_workbench.tasks import HandoffPacket, TaskPacket
from research_workbench.validation import SchemaCatalog, check_handoff_against_task


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "examples/evals/project-internal-handoff/visible"


class ProjectInternalHandoffFixtureTests(unittest.TestCase):
    def test_h1_negative_omission_passes_current_direct_structure_checks(self) -> None:
        task_value = load_document(FIXTURE_ROOT / "pih-01-h1-task.yaml")
        handoff_value = load_document(FIXTURE_ROOT / "pih-01-h1-negative-omission.yaml")

        self.assertEqual([], SchemaCatalog().validate("task_packet", task_value))
        self.assertEqual([], SchemaCatalog().validate("handoff_packet", handoff_value))
        risks = check_handoff_against_task(
            TaskPacket.from_mapping(task_value),
            HandoffPacket.from_mapping(handoff_value),
            project_root=ROOT,
        )
        self.assertEqual([], risks)

        claim = load_document(ROOT / "examples/objects/claim/CLAIM-EVID-001-BOUNDARY.yaml")
        self.assertTrue(claim["limitations"])
        self.assertEqual([], handoff_value["limitations"])
        self.assertEqual([], handoff_value["unresolved"])

    def test_h2_semantic_reversal_is_structurally_ready_only(self) -> None:
        handoff = load_document(
            FIXTURE_ROOT / "pih-02-h2-semantic-distortion-handoff.yaml"
        )
        audit = load_document(FIXTURE_ROOT / "pih-02-h2-semantic-distortion-audit.yaml")
        manifest = load_document(ROOT / "examples/handoff-transfer-evidence.yaml")

        self.assertEqual([], SchemaCatalog().validate("handoff_packet", handoff))
        self.assertEqual([], SchemaCatalog().validate("handoff_transfer_audit", audit))
        assessment = assess_handoff_transfer(audit, root=ROOT)
        self.assertEqual("structurally-ready", assessment.verdict)
        self.assertEqual(
            {"HANDOFF-SEMANTIC-UNREVIEWED"},
            {risk.code for risk in assessment.risks},
        )

        manifest_statement = manifest["items"][1]["statement"]
        handoff_statement = handoff["result"]["inferences"][0]
        self.assertIn("does not support", manifest_statement)
        self.assertIn("supports", handoff_statement)
        self.assertNotEqual(manifest_statement, handoff_statement)


if __name__ == "__main__":
    unittest.main()
