import copy
import unittest
from pathlib import Path

from research_workbench.artifacts import hash_file
from research_workbench.io import iter_documents, load_document
from research_workbench.validation.documents import validate_documents
from research_workbench.validation.schemas import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "registry/modes/actions.json"
ACTION_ROOT = ROOT / "registry/modes/actions"


class ModeActionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = SchemaCatalog(ROOT / "schemas")
        cls.action_paths = sorted(ACTION_ROOT.rglob("*.yaml"))
        cls.actions = [load_document(path) for path in cls.action_paths]
        cls.registry = load_document(REGISTRY_PATH)

    def test_two_formal_modes_preserve_eight_actions_across_two_revisions(self) -> None:
        self.assertEqual(32, len(self.actions))
        by_mode: dict[str, list[dict]] = {}
        for action in self.actions:
            by_mode.setdefault(action["mode_ref"], []).append(action)
        self.assertEqual(
            {
                "evidence-synthesis@0.1.0",
                "evidence-synthesis@0.2.0",
                "simulation@0.1.0",
                "simulation@0.2.0",
            },
            set(by_mode),
        )
        self.assertTrue(all(len(actions) == 8 for actions in by_mode.values()))
        references = {f"{action['action_id']}@{action['version']}" for action in self.actions}
        self.assertEqual(32, len(references))

    def test_every_action_has_complete_method_boundary_fields(self) -> None:
        required_nonempty = (
            "triggers",
            "non_triggers",
            "failure_modes",
            "required_artifacts",
            "stop_conditions",
            "blocked_conditions",
        )
        for action in self.actions:
            with self.subTest(action=action["action_id"]):
                self.assertEqual([], self.catalog.validate("mode_action", action))
                self.assertTrue(all(action[field] for field in required_nonempty))
                self.assertEqual(
                    {"may_support", "cannot_alone_support", "notes"},
                    set(action["claim_effects"]),
                )

    def test_registry_is_hash_pinned_and_closed(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "registry"])
        }
        self.assertEqual([], validate_documents(documents))
        indexed = {
            (entry["action_id"], entry["version"]): entry
            for entry in self.registry["entries"]
        }
        self.assertEqual(32, len(indexed))
        for path, action in zip(self.action_paths, self.actions, strict=True):
            entry = indexed[(action["action_id"], action["version"])]
            self.assertEqual(hash_file(path), entry["content_hash"].removeprefix("sha256:"))

    def test_registry_hash_drift_is_blocked(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "registry"])
        }
        mutated = copy.deepcopy(documents[REGISTRY_PATH])
        mutated["entries"][0]["content_hash"] = f"sha256:{'0' * 64}"
        documents[REGISTRY_PATH] = mutated
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("MODE-ACTION-HASH-MISMATCH", codes)

    def test_unknown_mode_relation_is_blocked(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "registry"])
        }
        action_path = self.action_paths[0]
        action = copy.deepcopy(documents[action_path])
        action["mode_ref"] = "unadmitted-mode@1.0.0"
        documents[action_path] = action
        registry = copy.deepcopy(documents[REGISTRY_PATH])
        registry["entries"][0]["mode_ref"] = action["mode_ref"]
        documents[REGISTRY_PATH] = registry
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("MODE-ACTION-MODE-MISSING", codes)

    def test_unindexed_action_is_blocked(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "registry"])
        }
        mutated = copy.deepcopy(documents[REGISTRY_PATH])
        mutated["entries"] = mutated["entries"][1:]
        documents[REGISTRY_PATH] = mutated
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("MODE-ACTION-UNINDEXED", codes)

    def test_empty_trigger_set_is_schema_invalid(self) -> None:
        action = copy.deepcopy(self.actions[0])
        action["triggers"] = []
        self.assertTrue(self.catalog.validate("mode_action", action))

    def test_claim_effects_use_only_canonical_claim_strengths(self) -> None:
        action = copy.deepcopy(self.actions[0])
        action["claim_effects"]["may_support"] = ["looks-convincing"]
        self.assertTrue(self.catalog.validate("mode_action", action))

    def test_claim_effect_sides_are_disjoint(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "registry"])
        }
        action_path = self.action_paths[0]
        action = copy.deepcopy(documents[action_path])
        action["claim_effects"]["may_support"] = ["source_reported"]
        documents[action_path] = action
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("MODE-ACTION-CLAIM-EFFECT-CONFLICT", codes)

    def test_action_cannot_support_strength_forbidden_by_its_mode(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "registry"])
        }
        action_path = self.action_paths[0]
        action = copy.deepcopy(documents[action_path])
        action["claim_effects"]["may_support"] = ["simulation_supported"]
        documents[action_path] = action
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("MODE-ACTION-CLAIM-NOT-ALLOWED", codes)

    def test_human_gate_is_an_opaque_identifier_not_embedded_decision_data(self) -> None:
        action = copy.deepcopy(self.actions[0])
        action["human_gates"] = ["approve:alice:forever"]
        self.assertTrue(self.catalog.validate("mode_action", action))

    def test_arbitrary_metadata_extension_is_rejected(self) -> None:
        action = copy.deepcopy(self.actions[0])
        action["metadata"] = {"approved": True}
        self.assertTrue(self.catalog.validate("mode_action", action))

    def test_published_identity_is_declared_append_only(self) -> None:
        action_schema = load_document(ROOT / "schemas/v0.1.0/mode-action.schema.json")
        registry_schema = load_document(
            ROOT / "schemas/v0.1.0/mode-action-registry.schema.json"
        )
        self.assertIn("immutable", action_schema["$comment"])
        self.assertIn("append-only", registry_schema["$comment"])


if __name__ == "__main__":
    unittest.main()
