"""Deterministic branch evidence for Phase C fail-closed validators."""

from __future__ import annotations

import copy
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import yaml

from research_workbench.artifacts.integrity import hash_bytes
from research_workbench.io import load_document
from research_workbench.research_state import closure, fresh_actor, gate
from research_workbench.research_state.boundaries import (
    AUTHORITY_LIMITS,
    TRUSTED_RUNTIME_SCHEMA_SURFACE,
)


ROOT = Path(__file__).resolve().parents[1]
CASE_A_MANIFEST = ROOT / "examples/phase-c/m10-003-gate/case-a/source-manifest.json"
CASE_A_ORACLE = ROOT / "examples/phase-c/m10-003-gate/case-a/runner-private.oracle"
CASE_B_MANIFEST = ROOT / "examples/phase-c/m10-003-gate/case-b/source-manifest.json"
CASE_B_ORACLE = ROOT / "examples/phase-c/m10-003-gate/case-b/runner-private.oracle"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _materialize_manifest(destination: Path, source: Path = CASE_A_MANIFEST) -> Path:
    manifest = json.loads(source.read_text(encoding="utf-8"))
    for entry in manifest["documents"]:
        relative = Path(*entry["source_ref"]["path"].split("/"))
        content = (ROOT / relative).read_bytes()
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        entry["source_ref"]["sha256"] = hash_bytes(content)
    path = destination / "source-manifest.json"
    _write_json(path, manifest)
    return path


def _indexed(
    identifier: str = "ITEM",
    *,
    revision: int = 1,
    kind: str = "research_object",
    semantic_type: str = "evidence",
    path: Path | None = Path("objects/item.yaml"),
    content_hash: str | None = "a" * 64,
    file_sha256: str | None = "b" * 64,
    document: dict | None = None,
) -> closure.IndexedDocument:
    value = dict(document or {})
    if content_hash is not None:
        value.setdefault("content_hash", content_hash)
    return closure.IndexedDocument(
        kind, semantic_type, identifier, revision, path, value, file_sha256
    )


class ClosureDefensiveBranchTests(unittest.TestCase):
    def test_path_loading_resolution_and_file_ref_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = root / "state.yaml"
            valid.write_text("state_id: STATE\nrevision: 1\n", encoding="utf-8")
            missing = root / "missing.yaml"
            index = closure.ClosureIndex.from_paths([missing, valid])
        self.assertEqual(index.resolve("STATE@2")["status"], "revision-missing")

        pathless = _indexed(path=None)
        first = _indexed(identifier="A", path=Path("shared.yaml"), file_sha256=None)
        second = _indexed(identifier="B", path=Path("nested/shared.yaml"))
        index = closure.ClosureIndex._from_indexed([pathless, first, second])
        for raw in (None, {"path": "", "sha256": "a"}, {"path": "../x", "sha256": "a"}, {"path": "x"}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                index.resolve_file_ref(raw)
        self.assertEqual(
            index.resolve_file_ref({"path": "shared.yaml", "sha256": "b" * 64})["status"],
            "ambiguous",
        )
        only = closure.ClosureIndex._from_indexed([first])
        self.assertEqual(
            only.resolve_file_ref({"path": "shared.yaml", "sha256": "b" * 64})["status"],
            "hash-unverifiable",
        )

    def test_indexing_and_reference_parser_reject_malformed_variants(self) -> None:
        self.assertIsNone(closure._index_document(None, []))
        malformed = (
            {"state_id": "", "revision": 1},
            {"lineage_id": "", "execution_attempt_ref": {}, "revision": 1},
            {"failure_id": "", "learned_result": "x", "revision": 1},
            {"trace_id": "", "method_application": {}, "revision": 1},
            {"resolution_id": "", "mode_resolution": {}, "revision": 1},
            {"record_kind": "actual-execution-binding", "fact_id": ""},
            {"snapshot_id": "", "selected_supply_report_ref": {}, "revision": 1},
            {"task_id": "", "goal": "x", "revision": 1},
            {"attempt_id": "", "started_at": "x", "task_revision": 1},
        )
        for document in malformed:
            with self.subTest(document=document):
                self.assertIsNone(closure._index_document(Path("x.yaml"), document))
        self.assertIsNotNone(
            closure._index_document(
                Path("object.yaml"),
                {"object_type": "evidence", "object_id": "E", "revision": 1},
            )
        )
        for raw in ("", "A@x", "A@0", {"object_id": ""}, {"object_id": "A", "revision": 0}, 42):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                closure._parse_object_ref(raw)

    def test_reference_problem_rendering_covers_all_resolution_statuses(self) -> None:
        good = _indexed()
        no_content = _indexed(identifier="NOHASH", content_hash=None)
        duplicate_a = _indexed(identifier="DUP")
        duplicate_b = _indexed(identifier="DUP", path=Path("other.yaml"))
        index = closure.ClosureIndex._from_indexed(
            [good, no_content, duplicate_a, duplicate_b]
        )
        cases = (
            (None, "unsupported"),
            ("MISSING@1", "unresolvable"),
            ("ITEM", "lacks a revision"),
            ("ITEM@2", "not found"),
            ("DUP@1", "ambiguous"),
            ({"object_id": "NOHASH", "revision": 1, "sha256": "a" * 64}, "cannot be verified"),
            ({"object_id": "ITEM", "revision": 1, "sha256": "c" * 64}, "drifts"),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertTrue(
                    any(expected in item for item in closure._ref_problems(index, raw, "ref"))
                )
        self.assertTrue(
            any(
                "role/type mismatch" in item
                for item in closure._ref_problems(
                    index, "ITEM@1", "ref", expected_types=("decision",)
                )
            )
        )

    def test_file_ref_problem_rendering_and_safe_helpers(self) -> None:
        entry = _indexed(path=Path("item.yaml"), file_sha256=None)
        duplicate = _indexed(identifier="OTHER", path=Path("item.yaml"))
        index = closure.ClosureIndex._from_indexed([entry, duplicate])
        problems, selected = closure._file_ref_problems(index, None, "file")
        self.assertIsNone(selected)
        self.assertTrue(any("must be an object" in item for item in problems))
        problems, _ = closure._file_ref_problems(
            index, {"path": "item.yaml", "sha256": "b" * 64}, "file"
        )
        self.assertTrue(any("ambiguous" in item for item in problems))
        only = closure.ClosureIndex._from_indexed([entry])
        problems, _ = closure._file_ref_problems(
            only, {"path": "item.yaml", "sha256": "b" * 64}, "file"
        )
        self.assertTrue(any("cannot be verified" in item for item in problems))
        self.assertIsNone(closure._resolved_entry(only, None))
        self.assertIsNone(closure._ref_identity(None))

    def test_state_lineage_failure_and_trace_defensive_shapes(self) -> None:
        index = closure.ClosureIndex()
        state = {
            "state_id": "STATE",
            "revision": 2,
            "supersedes": None,
            "entries": [{"role": "question", "ref": None}],
            "open_items": [{"status": "resolved", "provenance_refs": [None]}],
        }
        self.assertTrue(closure.check_research_state(state, index))
        lineage = {
            "attempt_id": "A",
            "lineage_id": "L",
            "execution_attempt_ref": None,
            "state_ref": None,
            "predecessor_attempt_ref": None,
            "reopen_justification": "assertion",
            "failure_refs": [None],
        }
        problems = closure.check_research_attempt_lineage(lineage, index)
        self.assertTrue(any("structured independent" in item for item in problems))
        self.assertTrue(
            closure.check_research_failure(
                {"origin_kind": "execution", "execution_profile": None}, index
            )
        )
        self.assertTrue(
            closure.check_research_failure(
                {"origin_kind": "non-execution", "execution_profile": {}}, index
            )
        )
        trace = {
            "attempt_ref": None,
            "task_ref": None,
            "method_application": [],
            "state_refs": [None, {"role": "from-state", "ref": None}, {"role": "from-state", "ref": None}],
            "path_dispositions": [None],
            "human_decision_refs": [None],
            "actual_binding": {"status": "unavailable"},
            "supersedes": None,
        }
        self.assertTrue(closure.check_method_trace(trace, index))

    def test_exceptional_relations_and_captured_path_effects_are_rejected(self) -> None:
        state = {"state_id": "S", "revision": 2, "supersedes": 42, "entries": [], "open_items": []}
        self.assertTrue(closure.check_research_state(state, closure.ClosureIndex()))
        lineage = {
            "attempt_id": "A",
            "lineage_id": "L",
            "execution_attempt_ref": None,
            "state_ref": None,
            "predecessor_attempt_ref": 42,
            "reopen_justification": {"changed_conditions": [None]},
            "failure_refs": [],
        }
        self.assertTrue(closure.check_research_attempt_lineage(lineage, closure.ClosureIndex()))

        case_roots = (
            ROOT / "examples/phase-c/m10-001-case-a",
            ROOT / "examples/phase-c/m10-002-case-a",
            ROOT / "examples/phase-c/m3-009-case-a",
        )
        documents = {
            path: load_document(path)
            for case_root in case_roots
            for path in case_root.rglob("*.yaml")
        }
        trace_path = ROOT / "examples/phase-c/m3-009-case-a/traces/MTRACE-PC-A.yaml"
        trace = copy.deepcopy(documents[trace_path])
        fact_ref = {"path": "facts/fact.json", "sha256": "f" * 64}
        trace["actual_binding"] = {
            "status": "captured",
            "coverage": "exact",
            "execution_fact_ref": fact_ref,
        }
        trace["path_dispositions"][0]["execution_fact_refs"] = [fact_ref]
        trace["path_dispositions"][0]["disposition"] = "rejected"
        trace["path_dispositions"][0]["state_refs"] = []
        fact = _indexed(
            identifier="FACT",
            kind="execution_trace_fact",
            semantic_type="execution_trace_fact",
            path=Path("facts/fact.json"),
            file_sha256="f" * 64,
            document={"record_kind": "actual-execution-binding", "fact_id": "FACT"},
        )
        index = closure.ClosureIndex.from_documents(documents)
        index.by_id.setdefault("FACT", []).append(fact)
        problems = closure.check_method_trace(trace, index)
        self.assertTrue(any("applied path" in item for item in problems))
        self.assertTrue(any("State effect" in item for item in problems))

        trace["revision"] = 2
        trace["supersedes"] = "OTHER-TRACE@2"
        problems = closure.check_method_trace(trace, index)
        self.assertTrue(any("same Method Trace lineage" in item for item in problems))
        self.assertTrue(any("strictly earlier" in item for item in problems))


class FreshActorHelperBranchTests(unittest.TestCase):
    def test_write_modes_path_identity_and_projection_helpers(self) -> None:
        self.assertFalse(fresh_actor._is_write_mode(None))
        self.assertFalse(fresh_actor._is_write_mode("rb"))
        self.assertTrue(fresh_actor._is_write_mode("a+"))
        self.assertTrue(fresh_actor._is_write_mode(os.O_WRONLY))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            with self.assertRaises(ValueError):
                fresh_actor._safe_staged_path(root, "../escape")
        for kind, field in (
            ("research_state", "state_id"),
            ("research_object", "object_id"),
            ("research_attempt_lineage", "lineage_id"),
            ("attempt", "attempt_id"),
            ("research_failure", "failure_id"),
            ("task_packet", "task_id"),
            ("method_resolution", "resolution_id"),
            ("method_trace", "trace_id"),
        ):
            with self.subTest(kind=kind):
                self.assertEqual(fresh_actor._identity(kind, {field: "ID", "revision": 1}), ("ID", 1))
                with self.assertRaises(ValueError):
                    fresh_actor._identity(kind, {field: "", "revision": 1})
                with self.assertRaises(ValueError):
                    fresh_actor._identity(kind, {field: "ID", "revision": 0})
        state = {"entries": [{"role": "claim", "disposition": "current", "ref": "C@1"}, None]}
        self.assertEqual(fresh_actor._selected_ref_strings(state, "claim"), ["C@1"])
        trace = {"path_dispositions": [{"failure_refs": ["F@1"]}, None]}
        self.assertEqual(fresh_actor._trace_failure_refs(trace), ["F@1"])

    def test_file_access_policy_enforces_each_read_write_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            allowed = root / "allowed.txt"
            output = root / "output.txt"
            trusted = root / "trusted"
            trusted.mkdir()
            allowed.write_text("ok", encoding="utf-8")
            policy = fresh_actor.FileAccessPolicy(
                root=root,
                allowed_reads={allowed},
                allowed_writes={output},
                trusted_read_roots=(trusted,),
            )
            with self.assertRaises(PermissionError):
                policy.record_manifest_read(root / "other")
            with self.assertRaises(PermissionError):
                policy.read_bytes(root / "other")
            self.assertEqual(policy.read_bytes(allowed), b"ok")
            policy._audit("other", ())
            policy._audit("open", (1, "r"))
            policy._audit("open", (object(), "r"))
            policy._audit("open", (allowed, "r"))
            policy._audit("open", (trusted / "schema.json", "r"))
            policy._audit("open", (output, "w"))
            with self.assertRaises(PermissionError):
                policy._audit("open", (allowed, "w"))
            with self.assertRaises(PermissionError):
                policy._audit("open", (root.parent / "outside.txt", "w"))
            self.assertIn("allowed.txt", policy.input_write_surface)

    def test_candidate_classification_rejects_ambiguous_or_unproven_paths(self) -> None:
        failures = {"F@1": {"failure_id": "F"}}
        kinds = {"E@1": "evidence", "Q@1": "question"}
        invalid_cases = (
            [None],
            [{"path_id": ""}],
            [{"path_id": "A"}, {"path_id": "A"}],
            [{"path_id": "A", "repeats_failure_ref": "F"}],
            [{"path_id": "A", "repeats_failure_ref": "UNKNOWN@1"}],
            [{"path_id": "A", "repeats_failure_ref": "F@1", "reopen_basis_refs": ["E"]}],
            [{"path_id": "A", "repeats_failure_ref": "F@1", "reopen_basis_refs": ["Q@1"]}],
        )
        for candidates in invalid_cases:
            with self.subTest(candidates=candidates), self.assertRaises(ValueError):
                fresh_actor._classify_paths(candidates, failures, kinds)
        classified, recommended = fresh_actor._classify_paths(
            [
                {"path_id": "new"},
                {"path_id": "avoid", "repeats_failure_ref": "F@1"},
                {"path_id": "review", "repeats_failure_ref": "F@1", "reopen_basis_refs": ["E@1"]},
            ],
            failures,
            kinds,
        )
        self.assertEqual(recommended, "new")
        self.assertEqual([item["classification"] for item in classified], ["recommendable", "known-failed-avoid", "reviewable"])

    def test_actor_main_records_success_and_fail_closed_outputs(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(fresh_actor.main([]), 2)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "answer.json"
            with mock.patch.object(fresh_actor, "run_actor", return_value={"status": "ok"}):
                self.assertEqual(fresh_actor.main(["manifest.json", str(output)]), 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "ok")
            output.unlink()
            with mock.patch.object(fresh_actor, "run_actor", side_effect=ValueError("blocked")):
                self.assertEqual(fresh_actor.main(["manifest.json", str(output)]), 1)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "blocked")
            output.unlink()
            with mock.patch.object(fresh_actor, "run_actor", side_effect=ValueError("blocked")), mock.patch.object(
                Path, "open", side_effect=OSError("cannot write")
            ):
                self.assertEqual(fresh_actor.main(["manifest.json", str(output)]), 1)

    def test_run_actor_rejects_manifest_bytes_identity_kind_and_alias_drift(self) -> None:
        def exercise(mutator, *, mock_validation: bool = False, output_exists: bool = False) -> None:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                project = root / "project"
                manifest_path = _materialize_manifest(project)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                actor_root = root / "actor"
                actor_root.mkdir()
                actor_manifest, answer_path, _, _ = gate._stage_case(
                    manifest,
                    project_root=project,
                    actor_root=actor_root,
                    oracle=CASE_A_ORACLE,
                )
                mutator(actor_manifest, answer_path)
                if output_exists:
                    answer_path.write_text("occupied", encoding="utf-8")
                validation = mock.patch.object(fresh_actor, "validate_documents", return_value=[])
                context = validation if mock_validation else mock.patch.object(
                    fresh_actor.FileAccessPolicy, "install"
                )
                with context, mock.patch.object(fresh_actor.FileAccessPolicy, "install"):
                    with self.assertRaises((FileExistsError, ValueError)):
                        fresh_actor.run_actor(actor_manifest, answer_path)

        def rewrite_manifest(transform):
            def mutate(path: Path, _answer: Path) -> None:
                value = json.loads(path.read_text(encoding="utf-8"))
                transform(value, path.parent)
                _write_json(path, value)
            return mutate

        variants = (
            (lambda path, answer: None, False, True),
            (lambda path, answer: _write_json(path, []), False, False),
            (rewrite_manifest(lambda value, root: value.update(documents=[])), False, False),
            (rewrite_manifest(lambda value, root: value["documents"].__setitem__(0, None)), False, False),
            (rewrite_manifest(lambda value, root: value["documents"][0].update(alias="")), False, False),
            (rewrite_manifest(lambda value, root: value["documents"][0].update(sha256="0" * 64)), False, False),
            (rewrite_manifest(lambda value, root: value["documents"][0].update(kind="method_trace")), False, False),
            (rewrite_manifest(lambda value, root: value["documents"][0]["identity"].update(object_id="OTHER")), False, False),
            (rewrite_manifest(lambda value, root: value.update(state_alias="missing")), True, False),
            (rewrite_manifest(lambda value, root: value.update(method_trace_alias="missing")), True, False),
        )
        for mutator, mock_validation, output_exists in variants:
            with self.subTest(mutator=mutator):
                exercise(mutator, mock_validation=mock_validation, output_exists=output_exists)

    def test_run_actor_rejects_non_object_invalid_and_stale_staged_documents(self) -> None:
        def exercise(alias: str, transform, *, mock_validation: bool = False) -> None:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                project = root / "project"
                manifest_path = _materialize_manifest(project)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                actor_root = root / "actor"
                actor_root.mkdir()
                actor_manifest, answer_path, _, _ = gate._stage_case(
                    manifest,
                    project_root=project,
                    actor_root=actor_root,
                    oracle=CASE_A_ORACLE,
                )
                actor_value = json.loads(actor_manifest.read_text(encoding="utf-8"))
                entry = next(item for item in actor_value["documents"] if item["alias"] == alias)
                staged = actor_root / entry["path"]
                content = transform(staged)
                staged.write_bytes(content)
                entry["sha256"] = hash_bytes(content)
                _write_json(actor_manifest, actor_value)
                validation = (
                    mock.patch.object(fresh_actor, "validate_documents", return_value=[])
                    if mock_validation
                    else mock.patch.object(fresh_actor.FileAccessPolicy, "install")
                )
                with validation, mock.patch.object(fresh_actor.FileAccessPolicy, "install"):
                    with self.assertRaises(ValueError):
                        fresh_actor.run_actor(actor_manifest, answer_path)

        exercise("state-current", lambda path: b"- not-an-object\n")
        def invalid_state(path: Path) -> bytes:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            document["entries"][0]["ref"] = "MISSING@1"
            return yaml.safe_dump(document, sort_keys=False).encode("utf-8")

        exercise("state-current", invalid_state)

        def inactive(path: Path) -> bytes:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            document["status"] = "archived"
            return yaml.safe_dump(document, sort_keys=False).encode("utf-8")

        exercise("state-current", inactive, mock_validation=True)

        def stale_trace(path: Path) -> bytes:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            next(item for item in document["state_refs"] if item["role"] == "current")["ref"]["revision"] = 1
            return yaml.safe_dump(document, sort_keys=False).encode("utf-8")

        exercise("method-trace", stale_trace, mock_validation=True)


class GateHelperBranchTests(unittest.TestCase):
    def test_json_paths_identity_and_manifest_schema_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            scalar = root / "scalar.json"
            _write_json(scalar, [])
            with self.assertRaises(ValueError):
                gate._load_json_object(scalar)
            for raw in ("", "/absolute", "../escape", "C:/escape"):
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    gate._safe_source_path(root, raw)
        for kind, field in (("research_state", "state_id"), ("method_trace", "trace_id")):
            self.assertEqual(gate._identity(kind, {field: "ID", "revision": 1}), ("ID", 1))
            with self.assertRaises(ValueError):
                gate._identity(kind, {field: "", "revision": 1})
            with self.assertRaises(ValueError):
                gate._identity(kind, {field: "ID", "revision": 0})
        self.assertTrue(gate._manifest_errors({}))

    def test_oracle_shape_predicates_and_exact_surface_are_closed(self) -> None:
        oracle, digest = gate._load_oracle(CASE_A_ORACLE)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        answer = copy.deepcopy(dict(oracle["exact_output"]))
        answer["case_data_read_surface"] = list(oracle["exact_case_data_read_surface"])
        answer["trusted_runtime_schema_surface"] = TRUSTED_RUNTIME_SCHEMA_SURFACE
        answer["input_write_surface"] = []
        self.assertTrue(gate._evaluate_oracle(oracle, answer, expected_surface=answer["case_data_read_surface"]))
        self.assertFalse(gate._check_predicate("unknown", answer))
        self.assertFalse(gate._check_predicate("unknown", {"candidate_paths": None}))

        mutations = (
            ({"case_id": "wrong"}, "case_id"),
            ({"case_data_read_surface": []}, "read surface"),
            ({"trusted_runtime_schema_surface": []}, "runtime/schema"),
            ({"input_write_surface": ["x"]}, "write"),
            ({"active_state": "wrong"}, "output mismatch"),
        )
        for delta, expected in mutations:
            mutated = copy.deepcopy(answer)
            mutated.update(delta)
            with self.subTest(delta=delta), self.assertRaisesRegex(ValueError, expected):
                gate._evaluate_oracle(oracle, mutated, expected_surface=answer["case_data_read_surface"])
        with self.assertRaisesRegex(ValueError, "runner-owned staged closure"):
            gate._evaluate_oracle(oracle, answer, expected_surface=["different"])
        predicate_oracle = copy.deepcopy(dict(oracle))
        predicate_oracle["predicates"] = ["recommendation-does-not-repeat-known-failure"]
        predicate_oracle["exact_output"]["candidate_paths"] = []
        predicate_oracle["exact_output"]["recommended_path"] = None
        predicate_failure = copy.deepcopy(answer)
        predicate_failure["candidate_paths"] = []
        predicate_failure["recommended_path"] = None
        with self.assertRaisesRegex(ValueError, "predicate failed"):
            gate._evaluate_oracle(
                predicate_oracle,
                predicate_failure,
                expected_surface=answer["case_data_read_surface"],
            )

    def test_oracle_rejects_each_malformed_contract_class(self) -> None:
        canonical = json.loads(CASE_A_ORACLE.read_text(encoding="utf-8"))
        variants = []
        variants.append([])
        wrong_keys = copy.deepcopy(canonical); wrong_keys["extra"] = True; variants.append(wrong_keys)
        weak_output = copy.deepcopy(canonical); weak_output["exact_output"].pop("active_state"); variants.append(weak_output)
        weak_surface = copy.deepcopy(canonical); weak_surface["exact_case_data_read_surface"] = []; variants.append(weak_surface)
        bad_predicates = copy.deepcopy(canonical); bad_predicates["predicates"] = ["unknown"]; variants.append(bad_predicates)
        no_topic = copy.deepcopy(canonical); no_topic["predicates"] = ["known-failed-paths-are-avoided"]; variants.append(no_topic)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for position, value in enumerate(variants):
                path = root / f"oracle-{position}.json"
                _write_json(path, value)
                with self.subTest(position=position), self.assertRaises(ValueError):
                    gate._load_oracle(path)

    def test_run_gate_case_and_aggregate_reject_invalid_actor_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scalar = root / "scalar.json"
            _write_json(scalar, [])
            with self.assertRaises(ValueError):
                gate.run_gate_case(gate.GateCase(scalar, CASE_A_ORACLE), project_root=ROOT)
            invalid = root / "invalid.json"
            _write_json(invalid, {})
            self.assertEqual(
                gate.run_gate_case(gate.GateCase(invalid, CASE_A_ORACLE), project_root=ROOT)["status"],
                "fail",
            )

            manifest = root / "manifest.json"
            manifest.write_bytes(CASE_A_MANIFEST.read_bytes())

            def stage_with_answer(value: object):
                def stage(_manifest, *, project_root, actor_root, oracle):
                    actor_manifest = actor_root / "actor.json"
                    answer = actor_root / "answer.json"
                    _write_json(actor_manifest, {})
                    if value is not None:
                        _write_json(answer, value)
                    return actor_manifest, answer, ["actor.json"], "c" * 64
                return stage

            actor_results = (
                (SimpleNamespace(returncode=1, stderr="driver failed"), None),
                (SimpleNamespace(returncode=0, stderr=""), []),
                (SimpleNamespace(returncode=0, stderr=""), {"status": "blocked"}),
                (SimpleNamespace(returncode=0, stderr=""), {"status": "ok", "actor_pid": 0}),
                (SimpleNamespace(returncode=0, stderr=""), {"status": "ok", "actor_pid": os.getpid()}),
                (SimpleNamespace(returncode=0, stderr=""), {"status": "ok", "actor_pid": os.getpid() + 1000, "authority_limits": []}),
            )
            for completed, answer in actor_results:
                with self.subTest(answer=answer), mock.patch.object(gate, "_stage_case", side_effect=stage_with_answer(answer)), mock.patch.object(gate.subprocess, "run", return_value=completed):
                    result = gate.run_gate_case(gate.GateCase(manifest, CASE_A_ORACLE), project_root=ROOT)
                    self.assertEqual(result["status"], "fail")

        with self.assertRaises(ValueError):
            gate.run_phase_c_gate([], project_root=ROOT)
        with self.assertRaises(ValueError):
            gate.run_phase_c_gate(
                [gate.GateCase(CASE_A_MANIFEST, CASE_A_ORACLE)] * 2, project_root=ROOT
            )
        with mock.patch.object(
            gate,
            "_load_json_object",
            side_effect=[
                {"case_id": "A", "profile": "evidence-synthesis"},
                {"case_id": "B", "profile": "evidence-synthesis"},
            ],
        ), self.assertRaisesRegex(ValueError, "requires one evidence-synthesis"):
            gate.run_phase_c_gate(
                [
                    gate.GateCase(CASE_A_MANIFEST, CASE_A_ORACLE),
                    gate.GateCase(CASE_B_MANIFEST, CASE_B_ORACLE),
                ],
                project_root=ROOT,
            )

    def test_stage_case_rejects_manifest_entry_and_source_contract_drift(self) -> None:
        def execute(transform, *, materialize: bool = False) -> None:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                if materialize:
                    path = _materialize_manifest(root)
                    manifest = json.loads(path.read_text(encoding="utf-8"))
                    project_root = root
                else:
                    manifest = json.loads(CASE_A_MANIFEST.read_text(encoding="utf-8"))
                    project_root = ROOT
                transform(manifest, project_root)
                with self.assertRaises(ValueError):
                    gate._stage_case(
                        manifest,
                        project_root=project_root,
                        actor_root=root / "actor",
                        oracle=CASE_A_ORACLE,
                    )

        variants = (
            lambda value, root: value["documents"].__setitem__(0, None),
            lambda value, root: value["documents"][0].update(alias=""),
            lambda value, root: value["documents"][0].update(identity=None),
            lambda value, root: value["documents"][0].update(identity={"object_id": "", "revision": 1}),
            lambda value, root: value["documents"][0].update(source_ref=None),
            lambda value, root: value["documents"].append(
                {
                    **copy.deepcopy(value["documents"][0]),
                    "alias": "duplicate-path",
                    "identity": {"object_id": "OTHER", "revision": 1},
                }
            ),
            lambda value, root: value["documents"][0].update(kind="method_trace"),
            lambda value, root: value["documents"][0].update(identity={"object_id": "OTHER", "revision": 1}),
        )
        for transform in variants:
            with self.subTest(transform=transform):
                execute(transform)

        def non_object(value, root):
            entry = value["documents"][0]
            path = root / Path(*entry["source_ref"]["path"].split("/"))
            content = b"- not-an-object\n"
            path.write_bytes(content)
            entry["source_ref"]["sha256"] = hash_bytes(content)

        def invalid_closure(value, root):
            entry = next(item for item in value["documents"] if item["alias"] == "state-current")
            path = root / Path(*entry["source_ref"]["path"].split("/"))
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            document["entries"][0]["ref"] = "MISSING@1"
            content = yaml.safe_dump(document, sort_keys=False).encode("utf-8")
            path.write_bytes(content)
            entry["source_ref"]["sha256"] = hash_bytes(content)

        execute(non_object, materialize=True)
        execute(invalid_closure, materialize=True)

    def test_gate_report_schema_failure_is_visible(self) -> None:
        passed = gate._failure_result("A", "evidence-synthesis", "bounded")
        other = gate._failure_result("B", "simulation-negative", "bounded")
        with mock.patch.object(gate, "_load_json_object", side_effect=[{"case_id": "A", "profile": "evidence-synthesis"}, {"case_id": "B", "profile": "simulation-negative"}]), mock.patch.object(gate, "run_gate_case", side_effect=[passed, other]), mock.patch.object(gate.SchemaCatalog, "validate", return_value=[SimpleNamespace(pointer="/x", message="bad")]):
            with self.assertRaisesRegex(ValueError, "invalid Phase C Gate report"):
                gate.run_phase_c_gate(
                    [gate.GateCase(CASE_A_MANIFEST, CASE_A_ORACLE), gate.GateCase(CASE_B_MANIFEST, CASE_B_ORACLE)],
                    project_root=ROOT,
                )


if __name__ == "__main__":
    unittest.main()
