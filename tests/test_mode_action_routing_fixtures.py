import json
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/mode-skill-routing/mode-action-routing-v1.yaml.txt"
ACTION_REGISTRY = ROOT / "registry/modes/actions.json"


class ModeActionRoutingFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        cls.cases = cls.document["cases"]
        cls.action_registry = json.loads(ACTION_REGISTRY.read_text(encoding="utf-8"))

    def test_fixture_has_eight_unique_bounded_cases(self) -> None:
        self.assertEqual(8, len(self.cases))
        ids = [case["case_id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual("diagnostic-planning-only", self.document["status"])
        self.assertFalse(self.document["formal_contract"])
        self.assertTrue(self.document["formal_action_refs"])
        self.assertEqual("registry/modes/actions.json", self.document["formal_action_registry_ref"])

    def test_formal_action_refs_are_versioned_and_hash_pinned(self) -> None:
        registered = {
            f"{entry['action_id']}@{entry['version']}": entry
            for entry in self.action_registry["entries"]
        }
        referenced = {
            action["action_ref"]
            for case in self.cases
            for action in case["actions"]
            if "action_ref" in action
        }
        self.assertTrue(referenced)
        self.assertLessEqual(referenced, registered.keys())
        for action_ref in referenced:
            self.assertRegex(registered[action_ref]["content_hash"], r"^sha256:[0-9a-f]{64}$")

    def test_only_frozen_tool_capability_ids_are_used(self) -> None:
        allowed = set(self.document["allowed_tool_capabilities"])
        used = {tool for case in self.cases for tool in case["tool_capabilities"]}
        self.assertLessEqual(used, allowed)
        self.assertEqual(
            {
                "document-read",
                "literature-search",
                "bounded-compute",
                "research-contract-check",
            },
            used,
        )

    def test_required_boundary_outcomes_are_covered(self) -> None:
        outcomes = {value for case in self.cases for value in case["expected_outcomes"]}
        self.assertLessEqual(
            {
                "tool-only",
                "no-skill",
                "skill-need",
                "human-gate",
                "capability-gap",
                "blocked",
                "no-new-mode",
                "ambiguous-mode",
                "split-task",
            },
            outcomes,
        )

    def test_needs_do_not_become_implicit_skill_assignments(self) -> None:
        need_cases = [case for case in self.cases if case["skill_needs"]]
        self.assertTrue(need_cases)
        self.assertTrue(all(case["skill_assignments"] == [] for case in need_cases))

    def test_internal_handoff_lane_can_end_at_template_no_skill(self) -> None:
        case = next(case for case in self.cases if case["case_id"] == "ROUTE-ES-FROZEN-001")
        internal = next(
            action
            for action in case["actions"]
            if action.get("planning_action_id") == "NEED-INT-COMPACT-HANDOFF"
        )
        self.assertEqual("task-template", internal["mechanism"])
        self.assertIn("no-skill", case["expected_outcomes"])

    def test_candidate_mode_gap_is_split_and_blocked(self) -> None:
        case = next(case for case in self.cases if case["case_id"] == "ROUTE-SPLIT-OBS-SIM-008")
        self.assertEqual("ambiguous-blocked", case["mode_decision"]["status"])
        self.assertEqual("observational-statistics", case["mode_decision"]["unresolved_mode"])
        self.assertEqual("split-and-block", case["route_status"])
        self.assertTrue(case["human_gates"])


if __name__ == "__main__":
    unittest.main()
