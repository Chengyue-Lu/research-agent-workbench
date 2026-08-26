"""Phase C: research state, failure, decision, method trace, and gates."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.research_state import (
    ClosureIndex,
    check_human_decision,
    check_method_trace,
    check_research_failure,
    check_research_state,
)
from research_workbench.research_state.fresh_actor import run_actor
from research_workbench.validation.documents import infer_document_kind, validate_documents
from research_workbench.validation.schemas import SchemaCatalog

ROOT = Path(__file__).resolve().parents[1]
CASE_A = ROOT / "examples" / "phase-c" / "case-a-evidence-synthesis"
CASE_B = ROOT / "examples" / "phase-c" / "case-b-simulation-negative"


def _index_for(*case_dirs: Path) -> ClosureIndex:
    documents: dict[Path, object] = {}
    for case_dir in case_dirs:
        for path in sorted(case_dir.rglob("*.yaml")):
            documents[path] = load_document(path)
    return ClosureIndex.from_documents(documents)


def _load(path: Path) -> dict:
    return load_document(path)


class FixtureSchemaTest(unittest.TestCase):
    def test_all_phase_c_documents_pass_schema(self) -> None:
        cases = {
            "research_state": CASE_A / "states" / "RSTATE-PC-A-r2.yaml",
            "research_failure": CASE_B / "failures" / "RFAIL-PC-B-001.yaml",
            "human_decision_record": CASE_A / "decisions" / "HDEC-PC-A-001.yaml",
            "method_trace": CASE_B / "traces" / "MTRACE-PC-B.yaml",
        }
        for kind, path in cases.items():
            document = _load(path)
            self.assertEqual(infer_document_kind(document), kind)
            self.assertEqual(SchemaCatalog().validate(kind, document), [], f"{kind}: {path}")

    def test_failure_requires_learned_and_revisit(self) -> None:
        document = _load(CASE_B / "failures" / "RFAIL-PC-B-001.yaml")
        stripped = {key: value for key, value in document.items()
                    if key not in ("learned_result", "revisit_condition")}
        self.assertNotEqual(SchemaCatalog().validate("research_failure", stripped), [])


class StateClosureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = _index_for(CASE_A)
        self.state = _load(CASE_A / "states" / "RSTATE-PC-A-r2.yaml")

    def test_clean_state_passes(self) -> None:
        self.assertEqual(check_research_state(self.state, self.index), [])

    def test_cross_lineage_supersession_rejected(self) -> None:
        mutated = copy.deepcopy(self.state)
        mutated["supersedes"] = {"object_id": "RSTATE-PC-B", "revision": 1}
        merged = _index_for(CASE_A, CASE_B)
        problems = check_research_state(mutated, merged)
        self.assertTrue(any("same state_id" in problem for problem in problems))

    def test_non_incremental_supersession_rejected(self) -> None:
        mutated = copy.deepcopy(self.state)
        mutated["revision"] = 1
        problems = check_research_state(mutated, self.index)
        self.assertTrue(any("strictly earlier" in problem for problem in problems))

    def test_stale_current_entry_rejected(self) -> None:
        mutated = copy.deepcopy(self.state)
        # index a newer question revision so entry[0] pinned at r1 is stale
        newer = copy.deepcopy(_load(CASE_A / "objects" / "Q-PC-A.yaml"))
        newer["revision"] = 2
        merged = _index_for(CASE_A)
        from research_workbench.research_state.closure import IndexedDocument

        merged.by_id["Q-PC-A"].append(
            IndexedDocument("research_object", "Q-PC-A", 2, Path("objects/Q-PC-A-r2.yaml"), newer)
        )
        problems = check_research_state(mutated, merged)
        self.assertTrue(any("stale" in problem for problem in problems))

    def test_invalidated_item_requires_provenance(self) -> None:
        mutated = copy.deepcopy(self.state)
        mutated["open_items"][0]["status"] = "invalidated"
        mutated["open_items"][0].pop("provenance_refs", None)
        problems = check_research_state(mutated, self.index)
        self.assertTrue(any("invalidated item requires provenance_refs" in problem for problem in problems))

    def test_revisit_ref_must_be_failure(self) -> None:
        mutated = copy.deepcopy(self.state)
        mutated["revisit_refs"] = [{"object_id": "Q-PC-A", "revision": 1}]
        problems = check_research_state(mutated, self.index)
        self.assertTrue(any("expected research_failure" in problem for problem in problems))

    def test_pin_drift_rejected(self) -> None:
        mutated = copy.deepcopy(self.state)
        mutated["entries"][1]["ref"]["sha256"] = "ab" * 32
        problems = check_research_state(mutated, self.index)
        self.assertTrue(any("drifts" in problem for problem in problems))


class FailureClosureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = _index_for(CASE_B)
        self.failure = _load(CASE_B / "failures" / "RFAIL-PC-B-001.yaml")

    def test_clean_failure_passes(self) -> None:
        self.assertEqual(check_research_failure(self.failure, self.index), [])

    def test_dangling_evidence_ref_rejected(self) -> None:
        mutated = copy.deepcopy(self.failure)
        mutated["evidence_refs"] = [{"object_id": "EVID-PC-B-99", "revision": 1}]
        problems = check_research_failure(mutated, self.index)
        self.assertTrue(any("unresolvable" in problem for problem in problems))


class DecisionClosureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = _index_for(CASE_A)
        self.decision = _load(CASE_A / "decisions" / "HDEC-PC-A-001.yaml")

    def test_clean_decision_passes(self) -> None:
        self.assertEqual(check_human_decision(self.decision, self.index), [])

    def test_state_effect_must_be_research_state(self) -> None:
        mutated = copy.deepcopy(self.decision)
        mutated["state_effect_ref"] = {"object_id": "Q-PC-A", "revision": 1}
        problems = check_human_decision(mutated, self.index)
        self.assertTrue(any("expected research_state" in problem for problem in problems))


class MethodTraceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = _index_for(CASE_B)
        self.trace = _load(CASE_B / "traces" / "MTRACE-PC-B.yaml")

    def test_clean_trace_passes(self) -> None:
        self.assertEqual(check_method_trace(self.trace, self.index), [])

    def test_sequence_gap_rejected(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["events"][1]["sequence"] = 5
        problems = check_method_trace(mutated, self.index)
        self.assertTrue(any("contiguous" in problem for problem in problems))
    def test_execution_fact_requires_execution_ref(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["events"].append(
            {
                "sequence": 5,
                "family": "execution-fact-recorded",
                "recorded_at": "2026-08-25T10:00:00+08:00",
                "rationale": "claimed but not pinned",
                "refs": {},
            }
        )
        problems = check_method_trace(mutated, self.index)
        self.assertTrue(
            any("requires refs.execution_ref" in problem for problem in problems)
        )

    def test_explicit_actual_binding_gap_is_valid_without_execution_ref(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["events"].append(
            {
                "sequence": 5,
                "family": "execution-fact-recorded",
                "recorded_at": "2026-08-25T10:00:00+08:00",
                "rationale": "No accepted execution-fact producer exists yet; gap recorded explicitly.",
                "actual_binding_gap": True,
                "refs": {},
            }
        )
        problems = check_method_trace(mutated, self.index)
        self.assertEqual(problems, [])

    def test_gap_with_execution_ref_is_contradictory(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["events"].append(
            {
                "sequence": 5,
                "family": "execution-fact-recorded",
                "recorded_at": "2026-08-25T10:00:00+08:00",
                "rationale": "contradiction",
                "actual_binding_gap": True,
                "refs": {"execution_ref": {"object_id": "RUN-PC-B", "revision": 1}},
            }
        )
        problems = check_method_trace(mutated, self.index)
        self.assertTrue(any("must not also pin" in problem for problem in problems))

    def test_gap_flag_rejected_outside_execution_family(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["events"].append(
            {
                "sequence": 5,
                "family": "reopen-reviewable",
                "recorded_at": "2026-08-25T10:00:00+08:00",
                "rationale": "misplaced gap",
                "actual_binding_gap": True,
                "refs": {"failure_ref": {"object_id": "RFAIL-PC-B-001", "revision": 1}},
            }
        )
        problems = check_method_trace(mutated, self.index)
        self.assertTrue(any("only to execution-fact-recorded" in problem for problem in problems))

    def test_dangling_decision_ref_rejected(self) -> None:
        mutated = copy.deepcopy(self.trace)
        mutated["events"].append(
            {
                "sequence": 5,
                "family": "human-decision-applied",
                "recorded_at": "2026-08-25T10:00:00+08:00",
                "rationale": "dangling",
                "refs": {"decision_ref": {"object_id": "HDEC-NOPE", "revision": 1}},
            }
        )
        problems = check_method_trace(mutated, self.index)
        self.assertTrue(any("unresolvable" in problem for problem in problems))


class CrossValidationTest(unittest.TestCase):
    def test_validate_documents_catches_state_mutation(self) -> None:
        documents: dict[Path, object] = {}
        for path in sorted(CASE_A.rglob("*.yaml")):
            documents[path] = load_document(path)
        mutated = copy.deepcopy(documents[CASE_A / "states" / "RSTATE-PC-A-r2.yaml"])
        mutated["entries"][1]["ref"]["sha256"] = "ab" * 32
        documents[CASE_A / "states" / "RSTATE-PC-A-r2.yaml"] = mutated
        issues = validate_documents(documents)
        self.assertTrue(
            any(
                issue.code == "PHASE-C-CLOSURE-INVALID" and "drifts" in issue.message
                for issue in issues
            )
        )

    def test_validate_documents_passes_clean_cases(self) -> None:
        documents: dict[Path, object] = {}
        for case in (CASE_A, CASE_B):
            for path in sorted(case.rglob("*.yaml")):
                documents[path] = load_document(path)
        issues = validate_documents(documents)
        self.assertEqual(
            [issue for issue in issues if issue.code == "PHASE-C-CLOSURE-INVALID"], []
        )


class FreshActorBehaviorTest(unittest.TestCase):
    def test_case_a_actor_answer(self) -> None:
        answer = run_actor(CASE_A)
        self.assertEqual(answer["status"], "ok")
        self.assertEqual(answer["active_state"], "RSTATE-PC-A@2")
        self.assertIn("EVID-PC-A-01@1", answer["key_evidence_refs"])
        self.assertIn("EVID-PC-A-02@1", answer["key_evidence_refs"])
        self.assertEqual(answer["recommended_action"], "survey-counterevidence")
        self.assertNotIn("original-chat.md", answer["read_surface"])
        self.assertNotIn("oracle/notes.md", answer["read_surface"])
        self.assertTrue(
            any(item["decision_id"] == "HDEC-PC-A-001" for item in answer["decision_effects"])
        )

    def test_case_b_known_failure_avoided(self) -> None:
        answer = run_actor(CASE_B)
        self.assertEqual(answer["status"], "ok")
        classification = {item["choice_id"]: item["classification"] for item in answer["choices"]}
        self.assertEqual(classification["rerun-coarse-grid"], "known-failed-avoid")
        self.assertEqual(classification["refine-resolution"], "recommendable")
        self.assertEqual(answer["recommended_action"], "refine-resolution")
        self.assertEqual(answer["invalidated_items"], ["ASSUM-PC-B-01"])
        self.assertNotIn("original-chat.md", answer["read_surface"])

    def test_case_b_revisit_met_marks_reviewable_not_recommended(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case"
            shutil.copytree(CASE_B, case)
            status_path = case / "revisit-status.yaml.txt"
            status_path.write_text("revisit_condition_met: true\n", encoding="utf-8")
            answer = run_actor(case)
            classification = {
                item["choice_id"]: item["classification"] for item in answer["choices"]
            }
            self.assertEqual(classification["rerun-coarse-grid"], "reviewable")
            # a reviewable path is surfaced, never auto-rerun
            self.assertNotEqual(answer["recommended_action"], "rerun-coarse-grid")

    def test_actor_blocks_on_broken_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case"
            shutil.copytree(CASE_A, case)
            state_path = case / "states" / "RSTATE-PC-A-r2.yaml"
            document = load_document(state_path)
            document["entries"][1]["ref"]["sha256"] = "ab" * 32
            import yaml

            state_path.write_text(
                yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                run_actor(case)


class StagedGateTest(unittest.TestCase):
    def test_gate_passes_both_cases_as_fresh_process(self) -> None:
        for case in (CASE_A, CASE_B):
            with tempfile.TemporaryDirectory() as tmp:
                answer = Path(tmp) / "answer.json.txt"
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "research_workbench.research_state.fresh_actor",
                        str(case),
                        str(answer),
                    ],
                    capture_output=True,
                    text=True,
                    cwd=ROOT,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                payload = json.loads(answer.read_text(encoding="utf-8"))
                self.assertEqual(payload["status"], "ok")
                self.assertIn(case.name, str(case))
                # the answer records the exact read surface for oracle audit
                self.assertTrue(payload["read_surface"])

    def test_cli_gate_fails_on_predicate_mismatch(self) -> None:
        from research_workbench.cli import main
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case"
            shutil.copytree(CASE_A, case)
            oracle = case / "oracle-expected.yaml.txt"
            oracle.write_text(
                "assert_exact:\n  recommended_action: nonexistent-action\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(
                    [
                        "research-state",
                        "gate",
                        "--case",
                        str(case),
                        "--answer",
                        str(Path(tmp) / "a.json.txt"),
                    ]
                )
            self.assertEqual(code, 1)
            self.assertIn("GATE-PREDICATE", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
