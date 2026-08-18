import unittest
from pathlib import Path

import yaml

from research_workbench.capability import AcceptedSkillRegistry


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/mode-skill-routing/accepted-skill-migration-v1.yaml.txt"


class AcceptedSkillMigrationFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        cls.entries = cls.document["entries"]
        cls.registry = AcceptedSkillRegistry.load(project_root=ROOT)

    def test_fixture_pins_every_current_accepted_package(self) -> None:
        expected = {
            (entry.skill_id, entry.version): (entry.content_hash, entry.package_hash)
            for entry in self.registry.entries
        }
        actual = {
            (entry["skill_id"], entry["version"]): (
                entry["content_hash"],
                entry["package_hash"],
            )
            for entry in self.entries
        }
        self.assertEqual(expected, actual)

    def test_migration_claims_only_bounded_registry_enforcement_and_no_new_packages(self) -> None:
        self.assertFalse(self.document["formal_contract"])
        self.assertTrue(self.document["runtime_enforced"])
        self.assertTrue(self.document["policy"]["preserve_historical_resolution"])
        self.assertFalse(self.document["policy"]["allow_in_place_package_mutation"])
        self.assertTrue(all(entry["next_version"] is None for entry in self.entries))

    def test_no_legacy_skill_is_assigned_by_new_action_routes(self) -> None:
        legacy_ids = {entry["skill_id"] for entry in self.entries}
        routed_needs = {
            need
            for entry in self.entries
            for route in entry["action_routes"]
            for need in route["skill_needs"]
        }
        self.assertTrue(legacy_ids.isdisjoint(routed_needs))
        self.assertEqual(
            {
                "NEED-ES-CONFLICT-SYNTHESIS",
                "NEED-SIM-CONVERGENCE-STUDY",
                "NEED-SIM-SENSITIVITY-UQ",
            },
            routed_needs,
        )

    def test_method_bundles_split_into_action_specific_mechanisms(self) -> None:
        literature = next(
            entry for entry in self.entries if entry["skill_id"] == "literature-evidence-extraction"
        )
        simulation = next(entry for entry in self.entries if entry["skill_id"] == "simulation-vv")
        literature_actions = {
            action
            for route in literature["action_routes"]
            for action in route["action_ids"]
        }
        simulation_actions = {
            action
            for route in simulation["action_routes"]
            for action in route["action_ids"]
        }
        self.assertEqual({"ES-A3", "ES-A4", "ES-A6"}, literature_actions)
        self.assertEqual(
            {"SIM-A2", "SIM-A3", "SIM-A4", "SIM-A5", "SIM-A6", "SIM-A7"},
            simulation_actions,
        )
        self.assertNotEqual("accepted-active", literature["lifecycle_decision"])
        self.assertNotEqual("accepted-active", simulation["lifecycle_decision"])

    def test_handoff_wrapper_moves_to_tool_template_and_human_boundary(self) -> None:
        handoff = next(entry for entry in self.entries if entry["skill_id"] == "handoff-integrity")
        self.assertEqual("deprecated-wrapper", handoff["lifecycle_decision"])
        self.assertEqual("forbidden", handoff["new_assignment"])
        route = handoff["action_routes"][0]
        self.assertEqual(["research-contract-check"], route["tools"])
        self.assertEqual([], route["skill_needs"])
        self.assertIn("human-sample", route["mechanism"])


if __name__ == "__main__":
    unittest.main()
