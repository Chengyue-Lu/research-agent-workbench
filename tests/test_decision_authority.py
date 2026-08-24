import copy
import unittest
from pathlib import Path

from research_workbench.artifacts.integrity import hash_file
from research_workbench.contracts.common import ContractError
from research_workbench.io import iter_documents, load_document
from research_workbench.protocol import (
    DECISION_AUTHORITY_MATRIX_REF,
    DecisionAuthorityMatrix,
    evaluate_authority_rule_eligibility,
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
        cls.eligibility_paths = sorted(PREFLIGHT_ROOT.glob("*.yaml"))
        cls.eligibility_records = {
            path: load_document(path) for path in cls.eligibility_paths
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

    def test_matrix_and_eligibility_records_are_schema_valid(self) -> None:
        self.assertEqual(
            [],
            self.catalog.validate("decision_authority_matrix", self.matrix_document),
        )
        self.assertEqual(9, len(self.eligibility_records))
        for path, document in self.eligibility_records.items():
            with self.subTest(path=path.name):
                self.assertEqual(
                    [],
                    self.catalog.validate("authority_rule_eligibility", document),
                )

    def test_all_recorded_results_are_deterministically_recomputed(self) -> None:
        statuses: list[str] = []
        codes: set[str] = set()
        for path, document in self.eligibility_records.items():
            with self.subTest(path=path.name):
                expected = evaluate_authority_rule_eligibility(
                    document,
                    self.matrix_document,
                    matrix_content_hash=self.matrix_hash,
                )
                self.assertEqual(expected, document["result"])
                statuses.append(expected["status"])
                codes.add(expected["code"])
        self.assertEqual(4, statuses.count("eligible"))
        self.assertEqual(5, statuses.count("blocked"))
        self.assertLessEqual(
            {
                "AUTHORITY-RULE-ELIGIBLE",
                "AUTHORITY-RULE-DENIED",
                "AUTHORITY-ASSERTED-FACTS-MISSING",
                "AUTHORITY-HUMAN-GATE-REQUIRED",
                "AUTHORITY-HUMAN-GATE-NOT-CONSUMED",
            },
            codes,
        )

    def test_repository_validation_recomputes_every_eligibility_record(self) -> None:
        documents = {
            path: load_document(path)
            for path in iter_documents([ROOT / "examples", ROOT / "registry"])
        }
        self.assertEqual([], validate_documents(documents))

    def test_agent_and_resolver_cannot_commit_reserved_decisions(self) -> None:
        agent = self.eligibility_records[PREFLIGHT_ROOT / "blocked-agent-claim-commit.yaml"]
        resolver = self.eligibility_records[
            PREFLIGHT_ROOT / "blocked-resolver-permission-commit.yaml"
        ]
        self.assertEqual("AUTHORITY-RULE-DENIED", agent["result"]["code"])
        self.assertEqual("human-gate", agent["result"]["disposition"])
        self.assertEqual("AUTHORITY-RULE-DENIED", resolver["result"]["code"])
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
            **copy.deepcopy(self.eligibility_records),
        }
        path = PREFLIGHT_ROOT / "eligible-resolver-action-commit.yaml"
        documents[path]["matrix_ref"]["content_hash"] = "sha256:" + "0" * 64
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("DECISION-AUTHORITY-RESULT-MISMATCH", codes)

    def test_duplicate_eligibility_identity_is_blocking(self) -> None:
        documents = {
            MATRIX_PATH: self.matrix_document,
            **copy.deepcopy(self.eligibility_records),
        }
        first, second = self.eligibility_paths[:2]
        documents[second]["eligibility_id"] = documents[first]["eligibility_id"]
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("AUTHORITY-RULE-ELIGIBILITY-DUPLICATE", codes)

    def test_eligibility_has_no_permission_claim_human_or_execution_effect(self) -> None:
        document = self.eligibility_records[
            PREFLIGHT_ROOT / "eligible-human-permission-relaxation.yaml"
        ]
        result = evaluate_authority_rule_eligibility(
            document,
            self.matrix_document,
            matrix_content_hash=self.matrix_hash,
        )
        self.assertEqual("eligible", result["status"])
        self.assertEqual("eligible-for-decision", result["disposition"])
        for forbidden_effect in (
            "permission_granted",
            "claim_promoted",
            "human_approval",
            "decision_executed",
        ):
            self.assertNotIn(forbidden_effect, result)


if __name__ == "__main__":
    unittest.main()
