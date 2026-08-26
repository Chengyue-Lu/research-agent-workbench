"""M10-001 durable Research State candidate tests."""

from __future__ import annotations

import copy
import contextlib
import io
import unittest
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.research_state import ClosureIndex, IndexedDocument, check_research_state
from research_workbench.validation.documents import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog

ROOT = Path(__file__).resolve().parents[1]
CASE_A = ROOT / "examples" / "phase-c" / "m10-001-case-a"
CASE_B = ROOT / "examples" / "phase-c" / "m10-001-case-b"


def _documents(*case_dirs: Path) -> dict[Path, object]:
    return {
        path: load_document(path)
        for case_dir in case_dirs
        for path in sorted(case_dir.rglob("*.yaml"))
    }


def _index(*case_dirs: Path) -> ClosureIndex:
    return ClosureIndex.from_documents(_documents(*case_dirs))


def _state(case_dir: Path, name: str) -> dict:
    return load_document(case_dir / "states" / name)


class FixtureContractTest(unittest.TestCase):
    def test_two_bounded_cases_pass_schema_and_closure(self) -> None:
        for case_dir, state_name in (
            (CASE_A, "RSTATE-PC-A-r2.yaml"),
            (CASE_B, "RSTATE-PC-B-r2.yaml"),
        ):
            with self.subTest(case=case_dir.name):
                documents = _documents(case_dir)
                for path, document in documents.items():
                    kind = infer_document_kind(document)
                    expected = "research_state" if "state_id" in document else "research_object"
                    self.assertEqual(kind, expected, path)
                    self.assertEqual(SchemaCatalog().validate(expected, document), [], path)
                self.assertEqual(check_research_state(_state(case_dir, state_name), _index(case_dir)), [])

    def test_human_decision_reuses_kernel_decision_object(self) -> None:
        decision = load_document(CASE_A / "objects" / "D-PC-A.yaml")
        self.assertEqual(decision["object_type"], "decision")
        self.assertEqual(infer_document_kind(decision), "research_object")
        self.assertEqual(SchemaCatalog().validate("research_object", decision), [])

    def test_downstream_failure_roles_are_not_in_m10_001_schema(self) -> None:
        state = _state(CASE_A, "RSTATE-PC-A-r2.yaml")
        state["entries"][0]["role"] = "human-decision"
        state["revisit_refs"] = []
        self.assertNotEqual(SchemaCatalog().validate("research_state", state), [])


class ExactClosureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = _index(CASE_A)
        self.state = _state(CASE_A, "RSTATE-PC-A-r2.yaml")

    def test_cross_lineage_supersession_is_rejected(self) -> None:
        state = copy.deepcopy(self.state)
        state["supersedes"] = {"object_id": "RSTATE-PC-B", "revision": 1}
        problems = check_research_state(state, _index(CASE_A, CASE_B))
        self.assertTrue(any("same state_id" in item for item in problems))

    def test_non_incremental_supersession_is_rejected(self) -> None:
        state = copy.deepcopy(self.state)
        state["revision"] = 1
        self.assertTrue(any("strictly earlier" in item for item in check_research_state(state, self.index)))

    def test_unversioned_reference_is_rejected(self) -> None:
        state = copy.deepcopy(self.state)
        state["entries"][0]["ref"] = "Q-PC-A"
        self.assertTrue(any("lacks a revision" in item for item in check_research_state(state, self.index)))

    def test_hash_drift_is_rejected(self) -> None:
        state = copy.deepcopy(self.state)
        state["entries"][1]["ref"]["sha256"] = "ab" * 32
        self.assertTrue(any("drifts" in item for item in check_research_state(state, self.index)))

    def test_pin_without_target_content_hash_is_rejected(self) -> None:
        state = _state(CASE_B, "RSTATE-PC-B-r2.yaml")
        state["entries"][0]["ref"]["sha256"] = "ab" * 32
        problems = check_research_state(state, _index(CASE_B))
        self.assertTrue(any("cannot be verified" in item for item in problems))

    def test_entry_role_must_match_target_semantic_type(self) -> None:
        state = copy.deepcopy(self.state)
        state["entries"][1]["role"] = "claim"
        problems = check_research_state(state, self.index)
        self.assertTrue(any("role/type mismatch" in item for item in problems))

    def test_stale_current_revision_is_rejected(self) -> None:
        state = copy.deepcopy(self.state)
        question = load_document(CASE_A / "objects" / "Q-PC-A.yaml")
        newer = copy.deepcopy(question)
        newer["revision"] = 2
        index = _index(CASE_A)
        index.by_id["Q-PC-A"].append(
            IndexedDocument(
                "research_object",
                "question",
                "Q-PC-A",
                2,
                Path("objects/Q-PC-A-r2.yaml"),
                newer,
            )
        )
        self.assertTrue(any("stale" in item for item in check_research_state(state, index)))

    def test_closed_open_item_requires_provenance(self) -> None:
        state = copy.deepcopy(self.state)
        state["open_items"][0].pop("provenance_refs")
        self.assertTrue(any("closed item" in item for item in check_research_state(state, self.index)))


class AmbiguousIdentityTest(unittest.TestCase):
    def test_duplicate_identity_is_rejected_even_if_not_selected(self) -> None:
        documents = _documents(CASE_A)
        question = load_document(CASE_A / "objects" / "Q-PC-A.yaml")
        documents[Path("duplicate/Q-PC-A.yaml")] = copy.deepcopy(question)
        index = ClosureIndex.from_documents(documents)
        problems = check_research_state(_state(CASE_A, "RSTATE-PC-A-r2.yaml"), index)
        self.assertTrue(any("duplicate identity Q-PC-A@1" in item for item in problems))

    def test_duplicate_exact_ref_resolves_as_ambiguous(self) -> None:
        question = load_document(CASE_A / "objects" / "Q-PC-A.yaml")
        index = ClosureIndex.from_documents(
            [
                (Path("one.yaml"), question),
                (Path("two.yaml"), copy.deepcopy(question)),
            ]
        )
        self.assertEqual(
            index.resolve({"object_id": "Q-PC-A", "revision": 1})["status"],
            "ambiguous",
        )


class RepositoryIntegrationTest(unittest.TestCase):
    def test_cli_consumes_only_explicit_closure(self) -> None:
        from research_workbench.cli import main

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(
                [
                    "research-state",
                    "validate",
                    str(CASE_A / "states" / "RSTATE-PC-A-r2.yaml"),
                    "--closure",
                    str(CASE_A),
                ]
            )
        self.assertEqual(exit_code, 0)
        self.assertIn("explicit_documents=6", output.getvalue())

    def test_validate_documents_reports_state_closure_failure(self) -> None:
        from research_workbench.validation.documents import validate_documents

        documents = _documents(CASE_A)
        state_path = CASE_A / "states" / "RSTATE-PC-A-r2.yaml"
        state = copy.deepcopy(documents[state_path])
        state["entries"][1]["role"] = "claim"
        documents[state_path] = state
        issues = validate_documents(documents)
        self.assertTrue(
            any(
                issue.code == "RESEARCH-STATE-CLOSURE-INVALID"
                and "role/type mismatch" in issue.message
                for issue in issues
            )
        )


if __name__ == "__main__":
    unittest.main()
