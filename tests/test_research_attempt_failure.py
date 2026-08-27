"""M10-002 Attempt lineage and Research Failure candidate tests."""

from __future__ import annotations

import contextlib
import copy
import io
import unittest
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.research_state import (
    ClosureIndex,
    check_research_attempt_lineage,
    check_research_failure,
)
from research_workbench.validation.documents import infer_document_kind, validate_documents
from research_workbench.validation.schemas import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]
STATE_A = ROOT / "examples" / "phase-c" / "m10-001-case-a"
STATE_B = ROOT / "examples" / "phase-c" / "m10-001-case-b"
LINEAGE_A = ROOT / "examples" / "phase-c" / "m10-002-case-a"
LINEAGE_B = ROOT / "examples" / "phase-c" / "m10-002-case-b"


def _documents(*roots: Path) -> dict[Path, object]:
    return {
        path: load_document(path)
        for root in roots
        for path in sorted(root.rglob("*.yaml"))
    }


def _index(*roots: Path) -> ClosureIndex:
    return ClosureIndex.from_documents(_documents(*roots))


def _lineage(case: Path, attempt_id: str) -> dict:
    return load_document(case / "attempt-lineage" / f"{attempt_id}.yaml")


class FixtureContractTest(unittest.TestCase):
    def test_bounded_lineage_cases_pass_schema_and_closure(self) -> None:
        for state_case, lineage_case in ((STATE_A, LINEAGE_A), (STATE_B, LINEAGE_B)):
            with self.subTest(case=lineage_case.name):
                documents = _documents(state_case, lineage_case)
                index = ClosureIndex.from_documents(documents)
                for path in sorted(lineage_case.rglob("*.yaml")):
                    document = documents[path]
                    kind = infer_document_kind(document)
                    self.assertIn(
                        kind,
                        {"attempt", "research_attempt_lineage", "research_failure"},
                        path,
                    )
                    self.assertEqual(SchemaCatalog().validate(kind, document), [], path)
                    if kind == "research_attempt_lineage":
                        self.assertEqual(check_research_attempt_lineage(document, index), [], path)
                    elif kind == "research_failure":
                        self.assertEqual(check_research_failure(document, index), [], path)
                self.assertEqual(validate_documents(documents), [])

    def test_two_attempts_share_state_while_state_evolves_independently(self) -> None:
        first = _lineage(LINEAGE_A, "A-PC-A-01")
        reopened = _lineage(LINEAGE_A, "A-PC-A-02")
        evolved = load_document(STATE_A / "states" / "RSTATE-PC-A-r2.yaml")
        self.assertEqual(first["state_ref"], reopened["state_ref"])
        self.assertEqual(first["state_ref"], {"object_id": "RSTATE-PC-A", "revision": 1})
        self.assertEqual(evolved["revision"], 2)
        self.assertEqual(
            check_research_attempt_lineage(reopened, _index(STATE_A, LINEAGE_A)),
            [],
        )

    def test_failure_universal_minimum_is_only_learned_and_revisit_content(self) -> None:
        minimal = {
            "schema_version": "0.1.0",
            "failure_id": "RFAIL-MIN",
            "revision": 1,
            "content_hash": "12" * 32,
            "learned_result": "The tested path does not distinguish the alternatives.",
            "revisit_condition": "A discriminating observation becomes available.",
        }
        self.assertEqual(SchemaCatalog().validate("research_failure", minimal), [])
        self.assertEqual(check_research_failure(minimal, ClosureIndex.from_documents({})), [])

    def test_failure_does_not_accept_parallel_failure_or_gap_fields(self) -> None:
        failure = load_document(LINEAGE_B / "failures" / "RFAIL-PC-B-001.yaml")
        for forbidden in (
            "execution_failure",
            "negative_evidence_ref",
            "capability_gap",
            "skill_need_ref",
        ):
            with self.subTest(field=forbidden):
                mutated = copy.deepcopy(failure)
                mutated[forbidden] = "must remain a separate contract"
                self.assertNotEqual(SchemaCatalog().validate("research_failure", mutated), [])


class ExactLineageClosureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = _index(STATE_A, LINEAGE_A)
        self.first = _lineage(LINEAGE_A, "A-PC-A-01")
        self.reopened = _lineage(LINEAGE_A, "A-PC-A-02")

    def test_execution_attempt_byte_pin_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.first)
        mutated["execution_attempt_ref"]["sha256"] = "ab" * 32
        problems = check_research_attempt_lineage(mutated, self.index)
        self.assertTrue(any("loaded file bytes" in item for item in problems))

    def test_execution_attempt_identity_must_match_sidecar(self) -> None:
        mutated = copy.deepcopy(self.reopened)
        first_ref = self.first["execution_attempt_ref"]
        mutated["execution_attempt_ref"] = copy.deepcopy(first_ref)
        problems = check_research_attempt_lineage(mutated, self.index)
        self.assertTrue(any("target attempt_id" in item for item in problems))

    def test_execution_attempt_file_is_type_bound(self) -> None:
        mutated = copy.deepcopy(self.first)
        mutated["execution_attempt_ref"] = {
            "path": (
                "examples/phase-c/m10-002-case-a/attempt-lineage/A-PC-A-01.yaml"
            ),
            "sha256": "ab" * 32,
        }
        problems = check_research_attempt_lineage(mutated, self.index)
        self.assertTrue(any("role/type mismatch" in item for item in problems))

    def test_execution_attempt_must_be_in_explicit_closure(self) -> None:
        documents = _documents(STATE_A, LINEAGE_A)
        attempt_path = LINEAGE_A / "attempts" / "A-PC-A-01.yaml"
        documents.pop(attempt_path)
        problems = check_research_attempt_lineage(
            self.first, ClosureIndex.from_documents(documents)
        )
        self.assertTrue(any("absent from the explicit closure" in item for item in problems))

    def test_predecessor_and_reopen_justification_are_independent(self) -> None:
        mutated = copy.deepcopy(self.reopened)
        mutated.pop("reopen_justification")
        self.assertEqual(
            SchemaCatalog().validate("research_attempt_lineage", mutated), []
        )
        self.assertEqual(check_research_attempt_lineage(mutated, self.index), [])

        without_predecessor = copy.deepcopy(self.reopened)
        without_predecessor.pop("predecessor_attempt_ref")
        self.assertEqual(
            SchemaCatalog().validate("research_attempt_lineage", without_predecessor), []
        )
        self.assertEqual(
            check_research_attempt_lineage(without_predecessor, self.index), []
        )

    def test_reopen_justification_requires_a_ref_or_changed_condition(self) -> None:
        mutated = copy.deepcopy(self.reopened)
        mutated["reopen_justification"]["basis_refs"] = []
        mutated["reopen_justification"]["changed_conditions"] = []
        self.assertNotEqual(
            SchemaCatalog().validate("research_attempt_lineage", mutated), []
        )

    def test_reopen_basis_is_type_bound(self) -> None:
        mutated = copy.deepcopy(self.reopened)
        mutated["reopen_justification"]["basis_refs"] = [
            {"object_id": "Q-PC-A", "revision": 1}
        ]
        problems = check_research_attempt_lineage(mutated, self.index)
        self.assertTrue(any("role/type mismatch" in item for item in problems))

    def test_predecessor_must_be_distinct_attempt(self) -> None:
        mutated = copy.deepcopy(self.first)
        mutated["predecessor_attempt_ref"] = {
            "object_id": "RATTEMPT-PC-A-01",
            "revision": 1,
        }
        mutated["reopen_justification"] = {
            "statement": "invalid self-loop",
            "basis_refs": [],
            "changed_conditions": ["synthetic self-loop"],
        }
        problems = check_research_attempt_lineage(mutated, self.index)
        self.assertTrue(any("distinct predecessor" in item for item in problems))

    def test_predecessor_must_be_versioned_and_type_bound(self) -> None:
        unversioned = copy.deepcopy(self.reopened)
        unversioned["predecessor_attempt_ref"] = "RATTEMPT-PC-A-01"
        self.assertTrue(
            any(
                "lacks a revision" in item
                for item in check_research_attempt_lineage(unversioned, self.index)
            )
        )
        wrong_type = copy.deepcopy(self.reopened)
        wrong_type["predecessor_attempt_ref"] = {
            "object_id": "RSTATE-PC-A",
            "revision": 1,
        }
        self.assertTrue(
            any(
                "role/type mismatch" in item
                for item in check_research_attempt_lineage(wrong_type, self.index)
            )
        )

    def test_duplicate_lineage_identity_is_rejected(self) -> None:
        documents = _documents(STATE_A, LINEAGE_A)
        documents[Path("duplicate/A-PC-A-01.yaml")] = copy.deepcopy(self.first)
        problems = check_research_attempt_lineage(
            self.reopened, ClosureIndex.from_documents(documents)
        )
        self.assertTrue(
            any("duplicate identity RATTEMPT-PC-A-01@1" in item for item in problems)
        )


class FailureProfileClosureTest(unittest.TestCase):
    def test_profile_source_must_be_attempt_lineage(self) -> None:
        failure = load_document(LINEAGE_B / "failures" / "RFAIL-PC-B-001.yaml")
        failure["execution_profile"]["source_attempt_ref"] = {
            "object_id": "RSTATE-PC-B",
            "revision": 1,
        }
        problems = check_research_failure(failure, _index(STATE_B, LINEAGE_B))
        self.assertTrue(any("role/type mismatch" in item for item in problems))

    def test_profile_is_all_or_nothing(self) -> None:
        failure = load_document(LINEAGE_B / "failures" / "RFAIL-PC-B-001.yaml")
        failure["execution_profile"].pop("uncertainty")
        self.assertNotEqual(SchemaCatalog().validate("research_failure", failure), [])


class RepositoryIntegrationTest(unittest.TestCase):
    def test_validate_documents_reports_lineage_pin_failure(self) -> None:
        documents = _documents(STATE_A, LINEAGE_A)
        lineage_path = LINEAGE_A / "attempt-lineage" / "A-PC-A-01.yaml"
        mutated = copy.deepcopy(documents[lineage_path])
        mutated["execution_attempt_ref"]["sha256"] = "ab" * 32
        documents[lineage_path] = mutated
        issues = validate_documents(documents)
        self.assertTrue(
            any(
                issue.code == "RESEARCH-ATTEMPT-CLOSURE-INVALID"
                and "loaded file bytes" in issue.message
                for issue in issues
            )
        )

    def test_cli_validates_lineage_against_explicit_closure(self) -> None:
        from research_workbench.cli import main

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(
                [
                    "research-state",
                    "validate",
                    str(LINEAGE_A / "attempt-lineage" / "A-PC-A-02.yaml"),
                    "--closure",
                    str(STATE_A),
                    "--closure",
                    str(LINEAGE_A),
                ]
            )
        self.assertEqual(code, 0, output.getvalue())
        self.assertIn("research_attempt_lineage", output.getvalue())


if __name__ == "__main__":
    unittest.main()
