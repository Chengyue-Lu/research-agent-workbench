import copy
import unittest
from pathlib import Path

from research_workbench.contracts.common import ContractError
from research_workbench.io import iter_documents, load_document
from research_workbench.protocol import (
    ResearchMode,
    build_research_mode_migration_record,
    migrate_research_mode_v01_to_v02,
)
from research_workbench.validation import SchemaCatalog, validate_documents


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "registry/modes/actions.json"
MODE_CASES = (
    (
        "evidence-synthesis",
        "RM-MIG-EVIDENCE-SYNTHESIS-001",
        "evidence-synthesis-0.1.0-to-0.2.0.yaml",
    ),
    ("simulation", "RM-MIG-SIMULATION-001", "simulation-0.1.0-to-0.2.0.yaml"),
)


class ResearchModeMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = SchemaCatalog(ROOT / "schemas")
        cls.action_registry = load_document(REGISTRY_PATH)

    def test_v01_and_v02_are_both_explicitly_valid(self) -> None:
        for mode_id, _, _ in MODE_CASES:
            with self.subTest(mode=mode_id):
                legacy = load_document(ROOT / f"registry/modes/{mode_id}.yaml")
                current = load_document(ROOT / f"registry/modes/v0.2.0/{mode_id}.yaml")
                self.assertEqual([], self.catalog.validate("research_mode", legacy))
                self.assertEqual([], self.catalog.validate("research_mode", current))
                self.assertEqual("0.1.0", ResearchMode.from_mapping(legacy).version)
                parsed = ResearchMode.from_mapping(current)
                self.assertEqual("0.2.0", parsed.version)
                self.assertEqual(8, len(parsed.action_refs))
                self.assertEqual((), parsed.recommended_skill_capabilities)

    def test_version_shapes_fail_closed(self) -> None:
        legacy = load_document(ROOT / "registry/modes/evidence-synthesis.yaml")
        current = load_document(ROOT / "registry/modes/v0.2.0/evidence-synthesis.yaml")
        legacy_with_actions = copy.deepcopy(legacy)
        legacy_with_actions["action_refs"] = ["ES-A1@2.0.0"]
        current_with_skill = copy.deepcopy(current)
        current_with_skill["recommended_skill_capabilities"] = ["evidence-extraction"]
        self.assertTrue(self.catalog.validate("research_mode", legacy_with_actions))
        self.assertTrue(self.catalog.validate("research_mode", current_with_skill))
        with self.assertRaises(ContractError):
            ResearchMode.from_mapping(legacy_with_actions)
        with self.assertRaises(ContractError):
            ResearchMode.from_mapping(current_with_skill)

    def test_migration_is_deterministic_and_matches_checked_in_targets(self) -> None:
        for mode_id, _, _ in MODE_CASES:
            with self.subTest(mode=mode_id):
                source = load_document(ROOT / f"registry/modes/{mode_id}.yaml")
                target = load_document(ROOT / f"registry/modes/v0.2.0/{mode_id}.yaml")
                self.assertEqual(
                    target,
                    migrate_research_mode_v01_to_v02(source, self.action_registry),
                )
                self.assertNotIn("recommended_skill_capabilities", target)
                self.assertTrue(all(ref.endswith("@2.0.0") for ref in target["action_refs"]))

    def test_checked_in_records_match_raw_file_hashes_and_implementation(self) -> None:
        for mode_id, migration_id, record_name in MODE_CASES:
            with self.subTest(mode=mode_id):
                expected = build_research_mode_migration_record(
                    root=ROOT,
                    migration_id=migration_id,
                    source_mode_path=f"registry/modes/{mode_id}.yaml",
                    target_mode_path=f"registry/modes/v0.2.0/{mode_id}.yaml",
                )
                actual = load_document(ROOT / f"registry/modes/migrations/{record_name}")
                self.assertEqual(expected, actual)
                self.assertEqual([], self.catalog.validate("research_mode_migration", actual))
                self.assertEqual("research-mode-v0.1-to-v0.2", actual["implementation"]["id"])
                self.assertEqual("1.0.0", actual["implementation"]["version"])

    def test_repository_relationships_include_migration_closed_sets(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "registry"])
        }
        self.assertEqual([], validate_documents(documents))

    def test_mode_hash_drift_is_blocked(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "registry"])
        }
        migration_path = ROOT / "registry/modes/migrations/evidence-synthesis-0.1.0-to-0.2.0.yaml"
        mutated = copy.deepcopy(documents[migration_path])
        mutated["target_mode"]["content_hash"] = f"sha256:{'0' * 64}"
        documents[migration_path] = mutated
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("MODE-MIGRATION-HASH-MISMATCH", codes)

    def test_action_mapping_drift_is_blocked(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "registry"])
        }
        migration_path = ROOT / "registry/modes/migrations/simulation-0.1.0-to-0.2.0.yaml"
        mutated = copy.deepcopy(documents[migration_path])
        mutated["action_migrations"] = mutated["action_migrations"][1:]
        documents[migration_path] = mutated
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("MODE-MIGRATION-ACTION-CLOSURE", codes)
        self.assertIn("MODE-MIGRATION-ACTION-REGISTRY-CLOSURE", codes)

    def test_implementation_and_field_declaration_drift_are_blocked(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "registry"])
        }
        migration_path = ROOT / "registry/modes/migrations/evidence-synthesis-0.1.0-to-0.2.0.yaml"
        mutated = copy.deepcopy(documents[migration_path])
        mutated["implementation"]["version"] = "1.0.1"
        mutated["preserved_fields"].remove("risk_rules")
        documents[migration_path] = mutated
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertLessEqual(
            {
                "MODE-MIGRATION-IMPLEMENTATION-MISMATCH",
                "MODE-MIGRATION-FIELD-DECLARATION-MISMATCH",
            },
            codes,
        )

    def test_duplicate_and_incomplete_action_lineage_are_blocked(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "registry"])
        }
        migration_path = ROOT / "registry/modes/migrations/simulation-0.1.0-to-0.2.0.yaml"
        mutated = copy.deepcopy(documents[migration_path])
        mutated["action_migrations"][-1] = copy.deepcopy(
            mutated["action_migrations"][0]
        )
        documents[migration_path] = mutated
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertLessEqual(
            {
                "MODE-MIGRATION-ACTION-DUPLICATE",
                "MODE-MIGRATION-ACTION-REGISTRY-CLOSURE",
                "MODE-MIGRATION-ACTION-CLOSURE",
            },
            codes,
        )

    def test_migration_rejects_missing_target_action_version(self) -> None:
        source = load_document(ROOT / "registry/modes/evidence-synthesis.yaml")
        registry = copy.deepcopy(self.action_registry)
        registry["entries"] = [
            entry
            for entry in registry["entries"]
            if entry["mode_ref"] != "evidence-synthesis@0.2.0"
        ]
        with self.assertRaises(ContractError):
            migrate_research_mode_v01_to_v02(source, registry)


if __name__ == "__main__":
    unittest.main()
