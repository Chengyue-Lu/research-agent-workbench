import unittest
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]


class VersionedSchemaTests(unittest.TestCase):
    def test_all_seven_research_object_types_have_valid_positive_fixtures(self) -> None:
        catalog = SchemaCatalog(ROOT / "schemas")
        paths = sorted((ROOT / "examples" / "objects").rglob("*.yaml"))
        self.assertGreaterEqual(len(paths), 7)
        for path in paths:
            with self.subTest(path=path.name):
                self.assertEqual([], catalog.validate("research_object", load_document(path)))

    def test_all_seven_research_object_types_reject_negative_fixtures(self) -> None:
        catalog = SchemaCatalog(ROOT / "schemas")
        paths = sorted((ROOT / "tests" / "fixtures" / "invalid" / "objects").glob("*.json"))
        self.assertEqual(7, len(paths))
        for path in paths:
            with self.subTest(path=path.name):
                self.assertTrue(catalog.validate("research_object", load_document(path)))

    def test_contract_schema_catalog_is_complete(self) -> None:
        catalog = SchemaCatalog(ROOT / "schemas")
        self.assertEqual(
            {
                "agent_profile",
                "agent_trace_actors",
                "agent_trace_envelope",
                "agent_trace_event",
                "agent_trace_index",
                "attempt",
                "attempt_completion_manifest",
                "context_snapshot",
                "deterministic_check_report",
                "decision_authority_matrix",
                "decision_authority_preflight",
                "execution_receipt",
                "handoff_packet",
                "handoff_transfer_audit",
                "handoff_transfer_manifest",
                "main_state",
                "method_resolution",
                "mode_action",
                "mode_action_registry",
                "project_protocol",
                "provider_conformance_report",
                "research_mode",
                "research_mode_migration",
                "research_object",
                "skill_manifest",
                "skill_assignment",
                "skill_archive_audit",
                "skill_evaluation",
                "task_packet",
            },
            set(catalog.document_kinds),
        )


if __name__ == "__main__":
    unittest.main()
