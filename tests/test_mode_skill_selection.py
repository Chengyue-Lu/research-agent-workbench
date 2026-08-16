import copy
import unittest
from pathlib import Path

from research_workbench.contracts import RiskLevel
from research_workbench.io import load_document
from research_workbench.protocol import ResearchModeRegistry
from research_workbench.selection import (
    ModeDecisionCard,
    assess_mode_card,
    assess_mode_skill_selection,
)
from research_workbench.validation import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples/mode-skill-selection"


class ModeCardTests(unittest.TestCase):
    def test_cards_pin_only_the_two_registered_modes_and_are_symmetric(self) -> None:
        registry = ResearchModeRegistry.load(project_root=ROOT)
        self.assertEqual({"evidence-synthesis", "simulation"}, {entry.mode_id for entry in registry.entries})
        cards = []
        for path in sorted((ROOT / "registry/modes/cards").glob("*.yaml")):
            document = load_document(path)
            self.assertEqual([], SchemaCatalog().validate("mode_decision_card", document))
            card = ModeDecisionCard.from_mapping(document)
            self.assertEqual((), assess_mode_card(card, registry=registry, root=ROOT))
            cards.append(card)
        self.assertEqual(2, len(cards))
        partners = {
            card.mode_id: {str(rule["with_mode_id"]) for rule in card.combination_rules}
            for card in cards
        }
        self.assertEqual({"simulation"}, partners["evidence-synthesis"])
        self.assertEqual({"evidence-synthesis"}, partners["simulation"])


class ModeSkillSelectionTests(unittest.TestCase):
    EXPECTED = {
        "KMS-001-evidence-extraction.yaml": ("ready", True, ["literature-evidence-extraction"]),
        "KMS-002-simulation-vv.yaml": ("ready", True, ["simulation-vv"]),
        "KMS-003-mixed-source-and-run-split.yaml": ("split-task", False, []),
        "KMS-004-ambiguous-published-simulation.yaml": ("human-gate", False, []),
        "KMS-005-deterministic-handoff-no-skill.yaml": ("ready", True, []),
        "KMS-006-unsupported-experimental-task.yaml": ("human-gate", False, []),
        "KMS-007-evidence-locator-check-no-skill.yaml": ("ready", True, []),
        "KMS-008-mixed-experimental-claim-block.yaml": ("blocked", False, []),
    }

    def test_all_eight_fixtures_are_schema_valid_and_replayable(self) -> None:
        paths = sorted(FIXTURES.glob("KMS-*.yaml"))
        self.assertEqual(set(self.EXPECTED), {path.name for path in paths})
        for path in paths:
            with self.subTest(path=path.name):
                document = load_document(path)
                self.assertEqual([], SchemaCatalog().validate("mode_skill_selection", document))
                assessment = assess_mode_skill_selection(document, root=ROOT)
                verdict, ready, selected = self.EXPECTED[path.name]
                self.assertEqual(verdict, assessment.verdict)
                self.assertEqual(ready, assessment.ready)
                self.assertFalse(
                    [risk for risk in assessment.risks if risk.level == RiskLevel.BLOCK],
                    assessment.risks,
                )
                self.assertEqual(selected, document["skill_assessment"]["selected_skill_ids"])

    def test_no_skill_decisions_close_gaps_without_loading_skill_content(self) -> None:
        for name in (
            "KMS-005-deterministic-handoff-no-skill.yaml",
            "KMS-007-evidence-locator-check-no-skill.yaml",
        ):
            document = load_document(FIXTURES / name)
            self.assertEqual("no-skill", document["skill_assessment"]["outcome"])
            self.assertEqual([], document["skill_assessment"]["capability_gaps_after"])
            self.assertEqual([], document["read_plan"]["selected_skill_content_refs"])
            task = load_document(ROOT / document["task_ref"]["path"])
            self.assertEqual([], task["required_skills"])

    def test_unselected_skill_body_in_read_plan_is_blocked(self) -> None:
        document = copy.deepcopy(
            load_document(FIXTURES / "KMS-005-deterministic-handoff-no-skill.yaml")
        )
        document["read_plan"]["initial_content_refs"].append(
            {
                "path": ".agents/skills/literature-evidence-extraction/SKILL.md",
                "sha256": "c0a080ea9c4743a599000bc6978386a8dcbb8aaa09e1ed4c0e54a4deadca780b",
            }
        )
        assessment = assess_mode_skill_selection(document, root=ROOT)
        self.assertIn("SKILL-READ-PLAN-LEAK", {risk.code for risk in assessment.risks})

    def test_mixed_modes_do_not_launder_an_experimental_claim(self) -> None:
        document = load_document(FIXTURES / "KMS-008-mixed-experimental-claim-block.yaml")
        self.assertEqual("blocked", document["mode_assessment"]["outcome"])
        self.assertIn(
            "experimentally_supported",
            document["mode_assessment"]["effective_constraints"]["forbidden_claims"],
        )
        self.assertEqual([], document["skill_assessment"]["selected_skill_ids"])


if __name__ == "__main__":
    unittest.main()
