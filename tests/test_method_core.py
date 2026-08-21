import copy
import unittest
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.method import (
    DecisionAuthorityMatrix,
    MethodResolution,
    ModeAction,
    assess_method_resolution,
    migrate_research_mode_v01_to_v02,
)
from research_workbench.protocol import ResearchMode
from research_workbench.validation import SchemaCatalog, validate_documents


ROOT = Path(__file__).resolve().parents[1]


class MethodCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = SchemaCatalog(ROOT / "schemas")
        self.matrix = DecisionAuthorityMatrix.from_mapping(
            load_document(ROOT / "registry/method/decision-authority.yaml")
        )

    def test_sixteen_mode_actions_are_first_class_and_schema_valid(self) -> None:
        paths = sorted((ROOT / "registry/mode-actions").rglob("*.yaml"))
        self.assertEqual(16, len(paths))
        actions = [ModeAction.from_mapping(load_document(path)) for path in paths]
        self.assertEqual(16, len({action.action_id for action in actions}))
        for path in paths:
            with self.subTest(path=path.name):
                self.assertEqual([], self.catalog.validate("mode_action", load_document(path)))

    def test_eight_diagnostic_routes_are_formal_method_resolutions(self) -> None:
        paths = sorted((ROOT / "examples/method-resolutions").glob("ROUTE-*.yaml"))
        self.assertEqual(8, len(paths))
        statuses = set()
        for path in paths:
            with self.subTest(path=path.name):
                document = load_document(path)
                self.assertEqual([], self.catalog.validate("method_resolution", document))
                resolution = MethodResolution.from_mapping(document)
                self.assertTrue(resolution.provider_neutral)
                statuses.add(resolution.status)
        self.assertEqual(
            {"resolved", "human-required", "blocked", "split-required"},
            statuses,
        )

    def test_mode_v02_migration_is_reproducible_and_removes_skill_recommendation(self) -> None:
        for mode_id in ("evidence-synthesis", "simulation"):
            source = load_document(ROOT / f"examples/modes/{mode_id}.yaml")
            target = load_document(ROOT / f"registry/modes/{mode_id}.yaml")
            migrated = migrate_research_mode_v01_to_v02(
                source,
                action_refs=target["action_refs"],
                migration_id=target["migration"]["migration_id"],
            )
            self.assertEqual(target, migrated)
            self.assertNotIn("recommended_skill_capabilities", target)
            self.assertEqual([], self.catalog.validate("research_mode", target))
            parsed = ResearchMode.from_mapping(target)
            self.assertEqual((), parsed.recommended_skill_capabilities)
            self.assertEqual(8, len(parsed.action_refs))

    def test_decision_authority_accepts_resolved_no_skill_baseline(self) -> None:
        resolution = MethodResolution.from_mapping(
            load_document(ROOT / "examples/method-resolutions/ROUTE-ES-FROZEN-001.yaml")
        )
        assessment = assess_method_resolution(resolution, self.matrix)
        self.assertTrue(assessment.allowed, assessment.errors)

    def test_decision_authority_rejects_provider_specific_method_semantics(self) -> None:
        document = load_document(
            ROOT / "examples/method-resolutions/ROUTE-ES-FROZEN-001.yaml"
        )
        altered = copy.deepcopy(document)
        altered["mechanism_resolutions"][0]["provider"] = "vendor-specific"
        resolution = MethodResolution.from_mapping(altered)
        assessment = assess_method_resolution(resolution, self.matrix)
        self.assertFalse(assessment.allowed)
        self.assertTrue(any("Provider/Model" in error for error in assessment.errors))

    def test_pinned_mode_action_hash_drift_is_blocking(self) -> None:
        path = ROOT / "registry/modes/evidence-synthesis.yaml"
        document = load_document(path)
        altered = copy.deepcopy(document)
        altered["action_refs"][0]["sha256"] = "0" * 64
        issues = validate_documents({path: altered})
        self.assertTrue(any(issue.code == "METHOD-ACTION-REF-DRIFT" for issue in issues))


if __name__ == "__main__":
    unittest.main()
