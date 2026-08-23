import copy
import json
import unittest
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog, validate_documents


ROOT = Path(__file__).resolve().parents[1]
RESOLUTION_ROOT = ROOT / "examples/method-resolutions"
ACTION_REGISTRY = ROOT / "registry/modes/actions.json"


class MethodResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = sorted(RESOLUTION_ROOT.glob("*.yaml"))
        cls.documents = {path: load_document(path) for path in cls.paths}
        cls.catalog = SchemaCatalog(ROOT / "schemas")
        cls.action_registry = json.loads(ACTION_REGISTRY.read_text(encoding="utf-8"))
        cls.validation_documents = {
            **cls.documents,
            ACTION_REGISTRY: cls.action_registry,
            **{
                ROOT / entry["document_path"]: load_document(ROOT / entry["document_path"])
                for entry in cls.action_registry["entries"]
            },
            ROOT / "examples/modes/evidence-synthesis.yaml": load_document(
                ROOT / "examples/modes/evidence-synthesis.yaml"
            ),
            ROOT / "examples/modes/simulation.yaml": load_document(
                ROOT / "examples/modes/simulation.yaml"
            ),
        }

    def test_all_eight_resolutions_are_schema_valid_and_provider_neutral(self) -> None:
        self.assertEqual(8, len(self.paths))
        forbidden_keys = {
            "provider",
            "model",
            "runtime",
            "host",
            "adapter",
            "mcp",
            "skill_assignment",
            "skill_assignments",
        }

        def keys(value):
            if isinstance(value, dict):
                yield from value.keys()
                for nested in value.values():
                    yield from keys(nested)
            elif isinstance(value, list):
                for nested in value:
                    yield from keys(nested)

        for path, document in self.documents.items():
            with self.subTest(path=path.name):
                self.assertEqual([], self.catalog.validate("method_resolution", document))
                self.assertFalse(forbidden_keys.intersection(keys(document)))
                self.assertTrue(document["rejected_alternatives"])

    def test_action_refs_pin_exact_registry_hashes(self) -> None:
        registered = {
            f"{entry['action_id']}@{entry['version']}": entry["content_hash"]
            for entry in self.action_registry["entries"]
        }
        for document in self.documents.values():
            for decision in document["action_decisions"]:
                action_ref = decision.get("action_ref")
                if action_ref is not None:
                    self.assertEqual(registered[action_ref], decision["action_content_hash"])

    def test_document_validation_closes_actions_needs_gates_and_blocks(self) -> None:
        self.assertEqual([], validate_documents(self.validation_documents))

    def test_action_hash_drift_is_blocking(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        path = RESOLUTION_ROOT / "ROUTE-SIM-REPLAY-004.yaml"
        documents[path]["action_decisions"][0]["action_content_hash"] = "sha256:" + "0" * 64
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("METHOD-RESOLUTION-ACTION-HASH-MISMATCH", codes)

    def test_skill_gate_and_block_closure_drift_is_blocking(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        path = RESOLUTION_ROOT / "ROUTE-BLOCK-PRIVATE-006.yaml"
        documents[path]["skill_disposition"]["need_refs"] = ["UNDECLARED-NEED"]
        documents[path]["human_gate_refs"] = []
        documents[path]["blocked_conditions"] = []
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertLessEqual(
            {
                "METHOD-RESOLUTION-SKILL-NEED-CLOSURE",
                "METHOD-RESOLUTION-HUMAN-GATE-CLOSURE",
                "METHOD-RESOLUTION-BLOCK-CLOSURE",
            },
            codes,
        )

    def test_duplicate_resolution_decision_obligation_and_alternative_ids_are_blocking(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        path = RESOLUTION_ROOT / "ROUTE-ES-FROZEN-001.yaml"
        document = documents[path]
        duplicate_path = RESOLUTION_ROOT / "duplicate-resolution.yaml"
        documents[duplicate_path] = copy.deepcopy(document)
        document["action_decisions"][1]["decision_id"] = document["action_decisions"][0]["decision_id"]
        document["action_decisions"][1]["obligations"][0]["obligation_id"] = (
            document["action_decisions"][0]["obligations"][0]["obligation_id"]
        )
        document["rejected_alternatives"][1]["alternative_id"] = (
            document["rejected_alternatives"][0]["alternative_id"]
        )
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertLessEqual(
            {
                "METHOD-RESOLUTION-DUPLICATE",
                "METHOD-RESOLUTION-DECISION-DUPLICATE",
                "METHOD-RESOLUTION-OBLIGATION-DUPLICATE",
                "METHOD-RESOLUTION-ALTERNATIVE-DUPLICATE",
            },
            codes,
        )

    def test_schema_rejects_implicit_assignment_and_invalid_selector(self) -> None:
        document = copy.deepcopy(next(iter(self.documents.values())))
        document["skill_assignments"] = []
        self.assertTrue(self.catalog.validate("method_resolution", document))
        document.pop("skill_assignments")
        document["provider"] = "implicit-provider"
        self.assertTrue(self.catalog.validate("method_resolution", document))
        document.pop("provider")
        decision = document["action_decisions"][0]
        decision["planning_action_id"] = "implicit-fallback"
        self.assertTrue(self.catalog.validate("method_resolution", document))


if __name__ == "__main__":
    unittest.main()
