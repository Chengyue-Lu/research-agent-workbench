import contextlib
import copy
import io
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts import hash_file
from research_workbench.cli import main
from research_workbench.context import assess_handoff_transfer
from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "examples/handoff-transfer-audit-evidence.yaml"


def _run_cli(arguments: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(arguments)
    return code, output.getvalue()


def _copy_transfer_fixture(root: Path) -> None:
    paths = (
        "examples/task-evidence.yaml",
        "examples/handoff-evidence.yaml",
        "examples/handoff-transfer-evidence.yaml",
        "examples/handoff-transfer-audit-evidence.yaml",
        "examples/fixtures/paper-001.txt",
        "examples/objects/evidence/EVID-001-01.yaml",
        "examples/objects/claim/CLAIM-EVID-001-BOUNDARY.yaml",
        "examples/vertical-slice/evidence-assignment.yaml",
    )
    for relative in paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


class HandoffTransferTests(unittest.TestCase):
    def test_repository_fixture_is_structurally_ready_without_semantic_overclaim(self) -> None:
        audit = load_document(AUDIT)
        self.assertEqual([], SchemaCatalog().validate("handoff_transfer_audit", audit))
        assessment = assess_handoff_transfer(audit, root=ROOT)
        self.assertEqual("structurally-ready", assessment.verdict)
        self.assertFalse(assessment.review_required)
        self.assertEqual(
            {"HANDOFF-SEMANTIC-UNREVIEWED"},
            {risk.code for risk in assessment.risks},
        )

    def test_direct_assessor_rejects_malformed_audit_contract(self) -> None:
        audit = copy.deepcopy(load_document(AUDIT))
        del audit["generated_at"]
        assessment = assess_handoff_transfer(audit, root=ROOT)
        self.assertEqual("not-transfer-ready", assessment.verdict)
        self.assertEqual(
            {"HANDOFF-AUDIT-CONTRACT"},
            {risk.code for risk in assessment.risks},
        )

    def test_completed_independent_human_sample_can_record_transfer_readiness(self) -> None:
        audit = copy.deepcopy(load_document(AUDIT))
        audit["review"] = {
            "status": "completed",
            "reviewer_kind": "human",
            "reviewer_independent": True,
            "sampled_item_ids": ["HTI-EVID-FACT-001"],
            "findings": [
                {
                    "item_id": "HTI-EVID-FACT-001",
                    "status": "preserved",
                    "detail": "Synthetic test review of the source and Handoff locators.",
                }
            ],
            "reviewed_at": "2026-08-13T00:02:00Z",
        }
        assessment = assess_handoff_transfer(audit, root=ROOT)
        self.assertEqual("transfer-ready-after-review", assessment.verdict)
        self.assertEqual((), assessment.risks)

    def test_distorted_sample_blocks_transfer(self) -> None:
        audit = copy.deepcopy(load_document(AUDIT))
        audit["review"] = {
            "status": "completed",
            "reviewer_kind": "human",
            "reviewer_independent": True,
            "sampled_item_ids": ["HTI-EVID-INFERENCE-001"],
            "findings": [
                {
                    "item_id": "HTI-EVID-INFERENCE-001",
                    "status": "distorted",
                    "detail": "The Handoff upgraded an unresolved boundary.",
                }
            ],
            "reviewed_at": "2026-08-13T00:02:00Z",
        }
        assessment = assess_handoff_transfer(audit, root=ROOT)
        self.assertEqual("not-transfer-ready", assessment.verdict)
        self.assertIn("HANDOFF-SUMMARY-DISTORTION", {risk.code for risk in assessment.risks})

    def test_missing_mapping_and_negative_section_are_visible(self) -> None:
        audit = copy.deepcopy(load_document(AUDIT))
        audit["mappings"] = [
            item
            for item in audit["mappings"]
            if item["item_id"] != "HTI-EVID-UNRESOLVED-001"
        ]
        assessment = assess_handoff_transfer(audit, root=ROOT)
        codes = {risk.code for risk in assessment.risks}
        self.assertEqual("not-transfer-ready", assessment.verdict)
        self.assertIn("HANDOFF-AUDIT-COVERAGE", codes)
        self.assertIn("HANDOFF-NEGATIVE-UNMAPPED", codes)

    def test_critical_manifest_item_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _copy_transfer_fixture(root)
            manifest_path = root / "examples/handoff-transfer-evidence.yaml"
            manifest = load_document(manifest_path)
            manifest["items"][0]["criticality"] = "critical"
            manifest_path.write_text(
                yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            audit_path = root / "examples/handoff-transfer-audit-evidence.yaml"
            audit = load_document(audit_path)
            audit["manifest_ref"]["sha256"] = hash_file(manifest_path)
            assessment = assess_handoff_transfer(audit, root=root)
        self.assertTrue(assessment.review_required)
        self.assertEqual("not-transfer-ready", assessment.verdict)
        self.assertIn(
            "HANDOFF-SEMANTIC-REVIEW-REQUIRED",
            {risk.code for risk in assessment.risks},
        )

    def test_cli_reports_structural_only_status_without_blocking(self) -> None:
        code, output = _run_cli(
            ["handoff", "audit-transfer", str(AUDIT), "--root", str(ROOT)]
        )
        self.assertEqual(0, code)
        self.assertIn("verdict: structurally-ready", output)
        self.assertIn("HANDOFF-SEMANTIC-UNREVIEWED", output)


if __name__ == "__main__":
    unittest.main()
