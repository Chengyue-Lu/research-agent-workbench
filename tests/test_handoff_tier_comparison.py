import copy
import unittest
from pathlib import Path

from research_workbench.contracts import RiskLevel
from research_workbench.io import load_document
from research_workbench.selection import assess_handoff_tier_comparison
from research_workbench.validation import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/evals/handoff-tiers/fixture-comparison.yaml"


class HandoffTierComparisonTests(unittest.TestCase):
    def test_fixture_has_exact_tiers_recomputed_metrics_and_only_fixture_warning(self) -> None:
        document = load_document(FIXTURE)
        self.assertEqual([], SchemaCatalog().validate("handoff_tier_comparison", document))
        self.assertEqual({"H0", "H1", "H2"}, {arm["tier"] for arm in document["arms"]})
        risks = assess_handoff_tier_comparison(document, root=ROOT)
        self.assertFalse([risk for risk in risks if risk.level == RiskLevel.BLOCK], risks)
        self.assertEqual(
            {"HANDOFF-COMPARISON-FIXTURE-ONLY"},
            {risk.code for risk in risks},
        )

    def test_capture_gap_is_detected(self) -> None:
        document = copy.deepcopy(load_document(FIXTURE))
        h1 = next(arm for arm in document["arms"] if arm["tier"] == "H1")
        h1["metrics"]["archived_message_count"] = 1
        risks = assess_handoff_tier_comparison(document, root=ROOT)
        self.assertIn("HANDOFF-ARCHIVE-GAP", {risk.code for risk in risks})

    def test_fixture_only_comparison_cannot_declare_a_best_tier(self) -> None:
        document = copy.deepcopy(load_document(FIXTURE))
        document["declared_best_tier"] = "H2"
        risks = assess_handoff_tier_comparison(document, root=ROOT)
        self.assertIn("HANDOFF-COMPARISON-OVERCLAIM", {risk.code for risk in risks})


if __name__ == "__main__":
    unittest.main()
