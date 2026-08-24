import json
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts import hash_file
from research_workbench.io import load_document


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/mode-skill-routing/mode-action-routing-v1.yaml.txt"
ACTION_REGISTRY = ROOT / "registry/modes/actions.json"


class ModeActionRoutingFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        cls.cases = cls.document["cases"]
        cls.action_registry = json.loads(ACTION_REGISTRY.read_text(encoding="utf-8"))
        cls.resolutions = {
            path.as_posix(): load_document(path)
            for path in sorted((ROOT / "examples/method-resolutions").glob("*.yaml"))
        }

    def test_fixture_has_eight_unique_bounded_cases(self) -> None:
        self.assertEqual(8, len(self.cases))
        ids = [case["case_id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual("diagnostic-planning-only", self.document["status"])
        self.assertFalse(self.document["formal_contract"])
        self.assertTrue(self.document["formal_action_refs"])
        self.assertEqual("registry/modes/actions.json", self.document["formal_action_registry_ref"])
        self.assertTrue(self.document["formal_method_resolution_refs"])
        self.assertEqual(
            "schemas/v0.1.0/method-resolution.schema.json",
            self.document["method_resolution_schema_ref"],
        )

    def test_formal_method_resolution_refs_are_hash_pinned_and_bijective(self) -> None:
        referenced: set[str] = set()
        for case in self.cases:
            reference = case["method_resolution_ref"]
            path = ROOT / reference["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(reference["sha256"], hash_file(path))
            resolution = load_document(path)
            self.assertEqual(case["case_id"], resolution["source_case_id"])
            task_reference = case["task_ref"]
            task_path = ROOT / task_reference["path"]
            self.assertEqual(task_reference["sha256"], hash_file(task_path))
            task = load_document(task_path)
            self.assertEqual(task["task_id"], resolution["task_ref"]["task_id"])
            self.assertEqual(task["revision"], resolution["task_ref"]["revision"])
            self.assertEqual(task_reference["sha256"], resolution["task_ref"]["sha256"])
            referenced.add(path.as_posix())
        self.assertEqual(set(self.resolutions), referenced)

    def test_formal_resolutions_preserve_diagnostic_boundary_decisions(self) -> None:
        for case in self.cases:
            with self.subTest(case=case["case_id"]):
                resolution = load_document(ROOT / case["method_resolution_ref"]["path"])
                selected_modes = resolution["mode_resolution"]["selected_mode_refs"]
                primary_mode = case["mode_decision"].get("primary_mode")
                expected_modes = [] if primary_mode is None else [f"{primary_mode}@0.1.0"]
                self.assertEqual(case["mode_decision"]["status"], resolution["mode_resolution"]["status"])
                self.assertEqual(expected_modes, selected_modes)
                self.assertEqual(
                    [case["mode_decision"].get("unresolved_mode")]
                    if case["mode_decision"].get("unresolved_mode")
                    else [],
                    resolution["mode_resolution"]["unresolved_mode_ids"],
                )
                source_actions = {
                    action.get("action_ref") or action.get("planning_action_id")
                    for action in case["actions"]
                }
                resolved_actions = {
                    decision.get("action_ref") or decision.get("planning_action_id")
                    for decision in resolution["action_decisions"]
                }
                self.assertEqual(source_actions, resolved_actions)
                capabilities = {
                    value
                    for decision in resolution["action_decisions"]
                    for value in decision["capability_requirements"]
                }
                self.assertEqual(set(case["tool_capabilities"]), capabilities)
                self.assertEqual(case["skill_needs"], resolution["skill_disposition"]["need_refs"])
                self.assertEqual(case["human_gates"], resolution["human_gate_refs"])
                self.assertEqual(case["route_status"], resolution["resolution_status"])
                self.assertEqual(
                    set(case["forbidden_routes"]),
                    {item["alternative_id"] for item in resolution["rejected_alternatives"]},
                )

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
                "capability-requirement",
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
