import copy
import unittest
from pathlib import Path

from research_workbench.artifacts.integrity import hash_file
from research_workbench.contracts.common import ContractError
from research_workbench.io import iter_documents, load_document
from research_workbench.protocol import (
    DECISION_AUTHORITY_MATRIX_REF,
    DecisionAuthorityMatrix,
    evaluate_decision_authority_preflight,
)
from research_workbench.validation import SchemaCatalog, validate_documents


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "registry/authority/decision-authority-matrix.yaml"
PREFLIGHT_ROOT = ROOT / "examples/decision-authority"


class DecisionAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = SchemaCatalog(ROOT / "schemas")
        cls.matrix_document = load_document(MATRIX_PATH)
        cls.matrix_hash = hash_file(MATRIX_PATH)
        cls.preflight_paths = sorted(PREFLIGHT_ROOT.glob("*.yaml"))
        cls.preflights = {
            path: load_document(path) for path in cls.preflight_paths
        }

    def test_matrix_is_the_exact_v1_closed_set(self) -> None:
        matrix = DecisionAuthorityMatrix.from_mapping(self.matrix_document)
        self.assertEqual(DECISION_AUTHORITY_MATRIX_REF, matrix.reference)
        self.assertEqual(7, len(matrix.entries))
        self.assertEqual(
            {
                "mode-selection",
                "action-selection",
                "mechanism-selection",
                "skill-tool-binding",
                "permission-relaxation",
                "data-boundary-relaxation",
                "claim-promotion",
            },
            {entry.decision_kind for entry in matrix.entries},
        )

    def test_matrix_and_preflights_are_schema_valid(self) -> None:
        self.assertEqual(
            [],
            self.catalog.validate("decision_authority_matrix", self.matrix_document),
        )
        self.assertEqual(9, len(self.preflights))
        for path, document in self.preflights.items():
            with self.subTest(path=path.name):
                self.assertEqual(
                    [],
                    self.catalog.validate("decision_authority_preflight", document),
                )

    def test_all_recorded_results_are_deterministically_recomputed(self) -> None:
        statuses: list[str] = []
        codes: set[str] = set()
        for path, document in self.preflights.items():
            with self.subTest(path=path.name):
                expected = evaluate_decision_authority_preflight(
                    document,
                    self.matrix_document,
                    matrix_content_hash=self.matrix_hash,
                )
                self.assertEqual(expected, document["result"])
                statuses.append(expected["status"])
                codes.add(expected["code"])
        self.assertEqual(4, statuses.count("allowed"))
        self.assertEqual(5, statuses.count("blocked"))
        self.assertLessEqual(
            {
                "AUTHORITY-ALLOWED",
                "AUTHORITY-DENIED",
                "AUTHORITY-FACTS-MISSING",
                "AUTHORITY-HUMAN-GATE-REQUIRED",
                "AUTHORITY-HUMAN-GATE-NOT-CONSUMED",
            },
            codes,
        )

    def test_repository_validation_recomputes_every_preflight(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "examples", ROOT / "registry"])
        }
        self.assertEqual([], validate_documents(documents))

    def test_agent_and_resolver_cannot_commit_reserved_decisions(self) -> None:
        agent = self.preflights[PREFLIGHT_ROOT / "blocked-agent-claim-commit.yaml"]
        resolver = self.preflights[
            PREFLIGHT_ROOT / "blocked-resolver-permission-commit.yaml"
        ]
        self.assertEqual("AUTHORITY-DENIED", agent["result"]["code"])
        self.assertEqual("human-gate", agent["result"]["disposition"])
        self.assertEqual("AUTHORITY-DENIED", resolver["result"]["code"])
        self.assertEqual("human-gate", resolver["result"]["disposition"])

    def test_matrix_cannot_grant_resolver_commit_for_claim_or_permission(self) -> None:
        matrix = copy.deepcopy(self.matrix_document)
        entry = next(
            item for item in matrix["entries"] if item["decision_kind"] == "claim-promotion"
        )
        commit = next(rule for rule in entry["rules"] if rule["operation"] == "commit")
        commit["actor_class"] = "deterministic-resolver"
        commit["human_gate_required"] = False
        with self.assertRaises(ContractError):
            DecisionAuthorityMatrix.from_mapping(matrix)

    def test_commit_fact_ceiling_cannot_be_silently_weakened(self) -> None:
        matrix = copy.deepcopy(self.matrix_document)
        entry = next(
            item for item in matrix["entries"] if item["decision_kind"] == "claim-promotion"
        )
        commit = next(rule for rule in entry["rules"] if rule["operation"] == "commit")
        commit["required_facts"].remove("claim-ceiling-allows")
        with self.assertRaises(ContractError):
            DecisionAuthorityMatrix.from_mapping(matrix)

    def test_hash_and_recorded_result_drift_are_blocking(self) -> None:
        documents = {
            MATRIX_PATH: self.matrix_document,
            **copy.deepcopy(self.preflights),
        }
        path = PREFLIGHT_ROOT / "allowed-resolver-action-commit.yaml"
        documents[path]["matrix_ref"]["content_hash"] = "sha256:" + "0" * 64
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("DECISION-AUTHORITY-RESULT-MISMATCH", codes)

    def test_duplicate_preflight_identity_is_blocking(self) -> None:
        documents = {
            MATRIX_PATH: self.matrix_document,
            **copy.deepcopy(self.preflights),
        }
        first, second = self.preflight_paths[:2]
        documents[second]["preflight_id"] = documents[first]["preflight_id"]
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("DECISION-AUTHORITY-PREFLIGHT-DUPLICATE", codes)


if __name__ == "__main__":
    unittest.main()
