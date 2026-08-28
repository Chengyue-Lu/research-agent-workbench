"""M3-009 ref-only Method Trace candidate tests."""

from __future__ import annotations

import contextlib
import copy
import io
import unittest
from pathlib import Path

from research_workbench.artifacts.integrity import hash_file
from research_workbench.io import load_document
from research_workbench.research_state import ClosureIndex, check_method_trace
from research_workbench.validation.documents import infer_document_kind, validate_documents
from research_workbench.validation.schemas import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]
STATE_A = ROOT / "examples" / "phase-c" / "m10-001-case-a"
LINEAGE_A = ROOT / "examples" / "phase-c" / "m10-002-case-a"
TRACE_A = ROOT / "examples" / "phase-c" / "m3-009-case-a"
TRACE_PATH = TRACE_A / "traces" / "MTRACE-PC-A.yaml"
TASK_PATH = TRACE_A / "tasks" / "M10-CASE-A.yaml"
RESOLUTION_PATH = TRACE_A / "method-resolutions" / "MR-PC-A.yaml"
SNAPSHOT_PATH = (
    ROOT / "examples" / "capability-resolution" / "snapshots" / "document-read-a.yaml"
)


def _documents(*roots: Path) -> dict[Path, object]:
    return {
        path: load_document(path)
        for root in roots
        for path in sorted(root.rglob("*.yaml"))
    }


def _case_documents() -> dict[Path, object]:
    return _documents(STATE_A, LINEAGE_A, TRACE_A)


def _trace() -> dict:
    return load_document(TRACE_PATH)


class FixtureContractTest(unittest.TestCase):
    def test_bounded_method_trace_passes_schema_and_exact_closure(self) -> None:
        documents = _case_documents()
        trace = documents[TRACE_PATH]
        self.assertEqual(infer_document_kind(trace), "method_trace")
        self.assertEqual(SchemaCatalog().validate("method_trace", trace), [])
        self.assertEqual(check_method_trace(trace, ClosureIndex.from_documents(documents)), [])
        self.assertEqual(validate_documents(documents), [])

    def test_trace_records_refs_without_copying_method_or_state_bodies(self) -> None:
        trace = _trace()
        rendered = repr(trace)
        self.assertNotIn("action_content_hash", rendered)
        self.assertNotIn("open_items", rendered)
        self.assertEqual(
            trace["method_application"]["resolution_ref"],
            {"object_id": "MR-PC-A", "revision": 1},
        )
        self.assertEqual(trace["actual_binding"]["coverage"], "gap-only")


class MethodApplicationClosureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = _case_documents()
        self.trace = _trace()

    def check(self, trace: dict | None = None, documents: dict[Path, object] | None = None) -> list[str]:
        selected = documents if documents is not None else self.documents
        return check_method_trace(trace or self.trace, ClosureIndex.from_documents(selected))

    def test_method_resolution_must_be_indexed(self) -> None:
        documents = dict(self.documents)
        documents.pop(RESOLUTION_PATH)
        self.assertTrue(any("unresolvable" in item for item in self.check(documents=documents)))

    def test_method_resolution_is_type_bound(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["method_application"]["resolution_ref"] = {
            "object_id": "RSTATE-PC-A",
            "revision": 1,
        }
        self.assertTrue(any("role/type mismatch" in item for item in self.check(mutated)))

    def test_method_resolution_must_bind_same_task(self) -> None:
        documents = copy.deepcopy(self.documents)
        resolution = documents[RESOLUTION_PATH]
        resolution["task_ref"]["task_id"] = "OTHER-TASK"
        problems = self.check(documents=documents)
        self.assertTrue(any("different Task" in item for item in problems))

    def test_method_resolution_must_be_schema_valid_and_task_byte_pinned(self) -> None:
        malformed = copy.deepcopy(self.documents)
        malformed[RESOLUTION_PATH].pop("rejected_alternatives")
        self.assertTrue(
            any("schema-invalid" in item for item in self.check(documents=malformed))
        )

        drifted = copy.deepcopy(self.documents)
        drifted[RESOLUTION_PATH]["task_ref"]["sha256"] = "ab" * 32
        self.assertTrue(
            any("Task byte pin drifts" in item for item in self.check(documents=drifted))
        )

    def test_applied_modes_must_equal_resolution(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["method_application"]["mode_refs"] = ["simulation@0.1.0"]
        self.assertTrue(any("selected modes" in item for item in self.check(mutated)))

    def test_path_dispositions_cover_each_resolution_decision_once(self) -> None:
        missing = copy.deepcopy(self.trace)
        missing["path_dispositions"] = []
        self.assertTrue(any("exactly once" in item for item in self.check(missing)))

        duplicate = copy.deepcopy(self.trace)
        duplicate["path_dispositions"].append(copy.deepcopy(duplicate["path_dispositions"][0]))
        problems = self.check(duplicate)
        self.assertTrue(any("duplicate action_decision_id" in item for item in problems))

    def test_applied_ids_must_match_applied_dispositions(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["path_dispositions"][0]["disposition"] = "deferred"
        self.assertTrue(any("exactly match applied" in item for item in self.check(mutated)))


class AttemptStateDecisionClosureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = _case_documents()
        self.trace = _trace()

    def check(self, trace: dict | None = None, documents: dict[Path, object] | None = None) -> list[str]:
        selected = documents if documents is not None else self.documents
        return check_method_trace(trace or self.trace, ClosureIndex.from_documents(selected))

    def test_from_state_must_equal_attempt_start_state(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["state_refs"][0]["ref"]["revision"] = 2
        problems = self.check(mutated)
        self.assertTrue(any("Attempt lineage state_ref" in item for item in problems))

    def test_execution_attempt_task_must_match_trace_task(self) -> None:
        documents = copy.deepcopy(self.documents)
        attempt_path = LINEAGE_A / "attempts" / "A-PC-A-02.yaml"
        documents[attempt_path]["task_id"] = "OTHER-TASK"
        problems = self.check(documents=documents)
        self.assertTrue(any("execution Attempt binds a different Task" in item for item in problems))

    def test_task_question_must_intersect_state_question(self) -> None:
        documents = copy.deepcopy(self.documents)
        documents[TASK_PATH]["question_refs"] = ["Q-UNRELATED@1"]
        problems = self.check(documents=documents)
        self.assertTrue(any("do not intersect" in item for item in problems))

    def test_human_decision_ref_is_type_bound(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["human_decision_refs"] = [{"object_id": "EVID-PC-A", "revision": 1}]
        self.assertTrue(any("role/type mismatch" in item for item in self.check(mutated)))

    def test_path_basis_fields_are_type_bound(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["path_dispositions"][0]["evidence_refs"] = [
            {"object_id": "D-PC-A", "revision": 1}
        ]
        self.assertTrue(any("role/type mismatch" in item for item in self.check(mutated)))


class ActualBindingBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = _case_documents()
        self.trace = _trace()

    def test_gap_is_explicit_and_never_coverage_complete(self) -> None:
        self.assertEqual(
            check_method_trace(self.trace, ClosureIndex.from_documents(self.documents)),
            [],
        )
        mutated = copy.deepcopy(self.trace)
        mutated["actual_binding"]["coverage"] = "coverage-complete"
        self.assertNotEqual(SchemaCatalog().validate("method_trace", mutated), [])

    def test_captured_binding_fails_without_accepted_producer(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["actual_binding"] = {
            "status": "captured",
            "producer_kind": "execution_trace_fact",
            "execution_fact_ref": {
                "path": "examples/phase-c/m3-009-case-a/facts/missing.yaml",
                "sha256": "ab" * 32,
            },
            "coverage": "coverage-complete",
        }
        problems = check_method_trace(mutated, ClosureIndex.from_documents(self.documents))
        if "execution_trace_fact" not in SchemaCatalog().document_kinds:
            self.assertTrue(
                any("no accepted execution fact producer" in item for item in problems)
            )
        self.assertTrue(any("absent from the explicit closure" in item for item in problems))

    def test_selected_snapshot_is_not_actual_execution(self) -> None:
        documents = dict(self.documents)
        documents[SNAPSHOT_PATH] = load_document(SNAPSHOT_PATH)
        mutated = copy.deepcopy(self.trace)
        mutated["actual_binding"] = {
            "status": "captured",
            "producer_kind": "execution_trace_fact",
            "execution_fact_ref": {
                "path": "examples/capability-resolution/snapshots/document-read-a.yaml",
                "sha256": hash_file(SNAPSHOT_PATH),
            },
            "coverage": "coverage-complete",
        }
        problems = check_method_trace(mutated, ClosureIndex.from_documents(documents))
        self.assertTrue(any("resolved_capability_snapshot" in item for item in problems))


class IdentityAndIntegrationTest(unittest.TestCase):
    def test_duplicate_method_trace_identity_is_rejected(self) -> None:
        documents = _case_documents()
        documents[Path("duplicate/MTRACE-PC-A.yaml")] = copy.deepcopy(documents[TRACE_PATH])
        problems = check_method_trace(
            documents[TRACE_PATH], ClosureIndex.from_documents(documents)
        )
        self.assertTrue(any("duplicate identity MTRACE-PC-A@1" in item for item in problems))

    def test_validate_documents_reports_method_trace_failure(self) -> None:
        documents = _case_documents()
        mutated = copy.deepcopy(documents[TRACE_PATH])
        mutated["method_application"]["mode_refs"] = ["simulation@0.1.0"]
        documents[TRACE_PATH] = mutated
        issues = validate_documents(documents)
        self.assertTrue(
            any(
                issue.code == "METHOD-TRACE-CLOSURE-INVALID"
                and "selected modes" in issue.message
                for issue in issues
            )
        )

    def test_cli_validates_trace_against_only_explicit_roots(self) -> None:
        from research_workbench.cli import main

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(
                [
                    "research-state",
                    "validate",
                    str(TRACE_PATH),
                    "--closure",
                    str(STATE_A),
                    "--closure",
                    str(LINEAGE_A),
                    "--closure",
                    str(TRACE_A),
                ]
            )
        self.assertEqual(code, 0, output.getvalue())
        self.assertIn("method_trace", output.getvalue())


if __name__ == "__main__":
    unittest.main()
