import copy
import json
import unittest
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog, validate_documents


ROOT = Path(__file__).resolve().parents[1]
RESOLUTION_ROOT = ROOT / "examples/method-resolutions"
TASK_ROOT = ROOT / "examples/method-resolution-tasks"
ACTION_REGISTRY = ROOT / "registry/modes/actions.json"
MODE_ROOT = ROOT / "registry/modes"


class MethodResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = sorted(RESOLUTION_ROOT.glob("*.yaml"))
        cls.documents = {path: load_document(path) for path in cls.paths}
        cls.task_paths = sorted(TASK_ROOT.glob("*.yaml"))
        cls.task_documents = {path: load_document(path) for path in cls.task_paths}
        cls.catalog = SchemaCatalog(ROOT / "schemas")
        cls.action_registry = json.loads(ACTION_REGISTRY.read_text(encoding="utf-8"))
        cls.validation_documents = {
            **cls.documents,
            **cls.task_documents,
            ACTION_REGISTRY: cls.action_registry,
            **{
                ROOT / entry["document_path"]: load_document(ROOT / entry["document_path"])
                for entry in cls.action_registry["entries"]
            },
            **{
                path: load_document(path)
                for path in sorted(
                    [*MODE_ROOT.glob("*.yaml"), *MODE_ROOT.glob("v*/*.yaml")]
                )
            },
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
                self.assertIn("sha256", document["task_ref"])
        self.assertEqual(8, len(self.task_paths))

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

    def test_wrong_task_hash_is_blocking(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        path = RESOLUTION_ROOT / "ROUTE-SIM-REPLAY-004.yaml"
        documents[path]["task_ref"]["sha256"] = "0" * 64
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("METHOD-RESOLUTION-TASK-HASH-MISMATCH", codes)

    def test_wrong_mode_action_is_blocking(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        path = RESOLUTION_ROOT / "ROUTE-ES-FROZEN-001.yaml"
        decision = documents[path]["action_decisions"][0]
        registered = {
            f"{entry['action_id']}@{entry['version']}": entry
            for entry in self.action_registry["entries"]
        }
        decision["action_ref"] = "SIM-A2@1.0.0"
        decision["action_content_hash"] = registered["SIM-A2@1.0.0"]["content_hash"]
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("METHOD-RESOLUTION-ACTION-MODE-MISMATCH", codes)

    def test_required_action_gate_missing_or_renamed_is_blocking(self) -> None:
        path = RESOLUTION_ROOT / "ROUTE-SIM-CONVERGENCE-005.yaml"
        for replacement in ([], ["renamed-claim-gate"]):
            with self.subTest(replacement=replacement):
                documents = copy.deepcopy(self.validation_documents)
                decision = documents[path]["action_decisions"][1]
                decision["human_gate_refs"] = replacement
                documents[path]["human_gate_refs"] = sorted(
                    {
                        gate
                        for item in documents[path]["action_decisions"]
                        for gate in item["human_gate_refs"]
                    }
                )
                codes = {issue.code for issue in validate_documents(documents)}
                self.assertIn("METHOD-RESOLUTION-ACTION-GATE-MISSING", codes)

    def test_additive_gate_is_allowed(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        path = RESOLUTION_ROOT / "ROUTE-SIM-CONVERGENCE-005.yaml"
        documents[path]["action_decisions"][0]["human_gate_refs"].append(
            "additional-convergence-review"
        )
        documents[path]["human_gate_refs"].append("additional-convergence-review")
        self.assertEqual([], validate_documents(documents))

    def test_action_artifact_stop_block_and_claim_effects_cannot_be_weakened(self) -> None:
        path = RESOLUTION_ROOT / "ROUTE-SIM-REPLAY-004.yaml"
        mutations = (
            (
                lambda decision: decision["obligations"][0]["required_evidence"].remove("input-lock"),
                "METHOD-RESOLUTION-ACTION-ARTIFACT-MISSING",
            ),
            (
                lambda decision: decision["stop_conditions"].clear(),
                "METHOD-RESOLUTION-ACTION-STOP-MISSING",
            ),
            (
                lambda decision: decision["blocked_conditions"].clear(),
                "METHOD-RESOLUTION-ACTION-BLOCK-MISSING",
            ),
            (
                lambda decision: decision.__setitem__("claim_effects", {"may_support": ["accepted"]}),
                "METHOD-RESOLUTION-CLAIM-EFFECT-OVERRIDE",
            ),
        )
        for mutate, expected_code in mutations:
            with self.subTest(expected_code=expected_code):
                documents = copy.deepcopy(self.validation_documents)
                mutate(documents[path]["action_decisions"][0])
                codes = {issue.code for issue in validate_documents(documents)}
                self.assertIn(expected_code, codes)

    def test_skill_need_is_method_stable_without_supply_implementation(self) -> None:
        for path in (
            RESOLUTION_ROOT / "ROUTE-ES-SEARCH-002.yaml",
            RESOLUTION_ROOT / "ROUTE-ES-CONFLICT-003.yaml",
            RESOLUTION_ROOT / "ROUTE-SIM-CONVERGENCE-005.yaml",
        ):
            with self.subTest(path=path.name):
                document = self.documents[path]
                self.assertEqual("skill-need", document["skill_disposition"]["status"])
                self.assertEqual("proceed", document["resolution_status"])
                self.assertFalse(
                    any(
                        "capability-gap" in decision["mechanisms"]
                        for decision in document["action_decisions"]
                    )
                )

    def test_diagnostic_case_reference_is_optional(self) -> None:
        document = copy.deepcopy(next(iter(self.documents.values())))
        document.pop("source_case_id")
        self.assertEqual([], self.catalog.validate("method_resolution", document))

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
        decision.pop("planning_action_id")
        document["resolution_status"] = "need-not-implemented"
        self.assertTrue(self.catalog.validate("method_resolution", document))
        document["resolution_status"] = "proceed"
        decision["mechanisms"].append("capability-gap")
        self.assertTrue(self.catalog.validate("method_resolution", document))


if __name__ == "__main__":
    unittest.main()
