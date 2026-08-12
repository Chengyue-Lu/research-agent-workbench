import unittest
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]


class VersionedSchemaTests(unittest.TestCase):
    def test_all_seven_research_object_types_have_valid_positive_fixtures(self) -> None:
        catalog = SchemaCatalog(ROOT / "schemas")
        paths = sorted((ROOT / "examples" / "objects").rglob("*.yaml"))
        self.assertEqual(7, len(paths))
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
                "attempt",
                "context_snapshot",
                "execution_receipt",
                "handoff_packet",
                "main_state",
                "project_protocol",
                "provider_conformance_report",
                "research_mode",
                "research_object",
                "skill_manifest",
                "skill_assignment",
                "task_packet",
            },
            set(catalog.document_kinds),
        )


if __name__ == "__main__":
    unittest.main()
