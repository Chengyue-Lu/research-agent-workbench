"""M10-003 runner-owned fresh-process Phase C Gate tests."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from research_workbench.artifacts.integrity import hash_bytes
from research_workbench.io import load_document_bytes
from research_workbench.research_state import GateCase, run_gate_case, run_phase_c_gate
from research_workbench.research_state import gate as gate_module
from research_workbench.research_state import fresh_actor
from research_workbench.validation.schemas import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]
CASE_A_MANIFEST = ROOT / "examples/phase-c/m10-003-gate/case-a/source-manifest.json"
CASE_A_ORACLE = ROOT / "examples/phase-c/m10-003-gate/case-a/runner-private.oracle"
CASE_B_MANIFEST = ROOT / "examples/phase-c/m10-003-gate/case-b/source-manifest.json"
CASE_B_ORACLE = ROOT / "examples/phase-c/m10-003-gate/case-b/runner-private.oracle"


def _case(manifest: Path, oracle: Path) -> GateCase:
    return GateCase(manifest, oracle)


def _manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _materialize_case(
    destination: Path,
    manifest_path: Path,
    oracle_path: Path,
    *,
    mutate_alias: str | None = None,
    mutate_document=None,
) -> GateCase:
    manifest = _manifest(manifest_path)
    for entry in manifest["documents"]:
        relative = Path(*entry["source_ref"]["path"].split("/"))
        source = ROOT / relative
        content = source.read_bytes()
        if entry["alias"] == mutate_alias:
            document = load_document_bytes(source, content)
            mutate_document(document)
            content = yaml.safe_dump(document, sort_keys=False).encode("utf-8")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        entry["source_ref"]["sha256"] = hash_bytes(content)
    staged_manifest = destination / "runner" / "source-manifest.json"
    staged_oracle = destination / "runner" / "runner-private.oracle"
    _write_json(staged_manifest, manifest)
    staged_oracle.parent.mkdir(parents=True, exist_ok=True)
    staged_oracle.write_bytes(oracle_path.read_bytes())
    return GateCase(staged_manifest, staged_oracle)


class CanonicalGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_phase_c_gate(
            [_case(CASE_A_MANIFEST, CASE_A_ORACLE), _case(CASE_B_MANIFEST, CASE_B_ORACLE)],
            project_root=ROOT,
        )

    def test_two_bounded_cases_pass_in_distinct_fresh_processes(self) -> None:
        self.assertEqual(self.report["machine_gate"]["status"], "pass")
        cases = self.report["machine_gate"]["cases"]
        self.assertEqual({item["profile"] for item in cases}, {"evidence-synthesis", "simulation-negative"})
        pids = {item["actor_pid"] for item in cases}
        self.assertEqual(len(pids), 2)
        self.assertNotIn(os.getpid(), pids)
        self.assertTrue(all(item["answer_sha256"] for item in cases))

    def test_actor_read_surface_is_exact_and_excludes_private_oracle(self) -> None:
        for result in self.report["machine_gate"]["cases"]:
            with self.subTest(case=result["case_id"]):
                self.assertEqual(result["read_surface"], sorted(result["read_surface"]))
                self.assertTrue(all("oracle" not in path for path in result["read_surface"]))
                self.assertIn("exact:no-input-writes", result["oracle_checks"])

    def test_negative_case_avoids_the_known_failed_path(self) -> None:
        negative = next(
            item
            for item in self.report["machine_gate"]["cases"]
            if item["profile"] == "simulation-negative"
        )
        self.assertIn("predicate:known-failed-paths-are-avoided", negative["oracle_checks"])
        self.assertIn(
            "predicate:recommendation-does-not-repeat-known-failure",
            negative["oracle_checks"],
        )

    def test_machine_pass_keeps_human_r2_and_topic_5_closed(self) -> None:
        self.assertEqual(self.report["human_semantic_review"]["status"], "pending")
        self.assertEqual(self.report["r2_closeout"]["status"], "pending")
        self.assertEqual(self.report["phase_c_closeout"], "pending")
        self.assertFalse(self.report["boundaries"]["reviewer_reconstruction_proven"])
        self.assertFalse(self.report["boundaries"]["scientific_correctness_proven"])
        self.assertFalse(self.report["boundaries"]["topic_5_authorized"])
        self.assertEqual(SchemaCatalog().validate("phase_c_gate_report", self.report), [])

    def test_consumer_logic_is_independently_replayable_from_staged_bytes(self) -> None:
        for manifest_path, oracle_path in (
            (CASE_A_MANIFEST, CASE_A_ORACLE),
            (CASE_B_MANIFEST, CASE_B_ORACLE),
        ):
            with self.subTest(manifest=manifest_path.name), tempfile.TemporaryDirectory() as temporary:
                manifest = gate_module._load_json_object(manifest_path)
                actor_root = Path(temporary)
                actor_manifest, answer_path, expected_surface = gate_module._stage_case(
                    manifest,
                    project_root=ROOT,
                    actor_root=actor_root,
                    oracle=oracle_path,
                )
                with mock.patch.object(fresh_actor.FileAccessPolicy, "install"):
                    answer = fresh_actor.run_actor(actor_manifest, answer_path)
                self.assertEqual(answer["status"], "ok")
                self.assertEqual(answer["read_surface"], expected_surface)
                self.assertEqual(answer["input_write_surface"], [])


class RunnerOwnedClosureTest(unittest.TestCase):
    def test_process_policy_denies_unlisted_reads_and_input_writes(self) -> None:
        script = """
from pathlib import Path
from research_workbench.research_state.fresh_actor import FileAccessPolicy
root = Path.cwd().resolve()
allowed = root / 'allowed.txt'
secret = root / 'secret.txt'
output = root / 'output.json'
policy = FileAccessPolicy(root=root, allowed_reads={allowed}, allowed_writes={output})
policy.install()
blocked = []
try:
    secret.read_text(encoding='utf-8')
except PermissionError:
    blocked.append('read')
try:
    allowed.write_text('mutated', encoding='utf-8')
except PermissionError:
    blocked.append('write')
output.write_text('ok', encoding='utf-8')
raise SystemExit(0 if blocked == ['read', 'write'] else 1)
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            allowed = root / "allowed.txt"
            allowed.write_text("original", encoding="utf-8")
            (root / "secret.txt").write_text("private", encoding="utf-8")
            completed = subprocess.run(
                [os.sys.executable, "-c", script],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            retained = allowed.read_text(encoding="utf-8")
            output = (root / "output.json").read_text(encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(retained, "original")
        self.assertEqual(output, "ok")

    def test_source_pin_drift_blocks_before_actor_spawn(self) -> None:
        manifest = _manifest(CASE_A_MANIFEST)
        manifest["documents"][0]["source_ref"]["sha256"] = "ab" * 32
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            _write_json(path, manifest)
            with mock.patch.object(gate_module.subprocess, "run") as spawn:
                result = run_gate_case(_case(path, CASE_A_ORACLE), project_root=ROOT)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("source byte pin drifts" in item for item in result["oracle_checks"]))
        spawn.assert_not_called()

    def test_duplicate_identity_and_source_path_block_before_actor_spawn(self) -> None:
        manifest = _manifest(CASE_A_MANIFEST)
        duplicate = copy.deepcopy(manifest["documents"][0])
        duplicate["alias"] = "duplicate-claim"
        manifest["documents"].append(duplicate)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            _write_json(path, manifest)
            with mock.patch.object(gate_module.subprocess, "run") as spawn:
                result = run_gate_case(_case(path, CASE_A_ORACLE), project_root=ROOT)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("repeats identity" in item for item in result["oracle_checks"]))
        spawn.assert_not_called()

    def test_private_oracle_cannot_be_declared_as_actor_input(self) -> None:
        manifest = _manifest(CASE_A_MANIFEST)
        entry = manifest["documents"][0]
        entry["source_ref"] = {
            "path": CASE_A_ORACLE.relative_to(ROOT).as_posix(),
            "sha256": hash_bytes(CASE_A_ORACLE.read_bytes()),
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            _write_json(path, manifest)
            with mock.patch.object(gate_module.subprocess, "run") as spawn:
                result = run_gate_case(_case(path, CASE_A_ORACLE), project_root=ROOT)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("oracle cannot be part" in item for item in result["oracle_checks"]))
        spawn.assert_not_called()

    def test_oracle_is_read_only_after_fresh_actor_exits(self) -> None:
        events: list[str] = []
        original_run = subprocess.run
        original_load = gate_module._load_oracle

        def traced_run(*args, **kwargs):
            events.append("actor")
            return original_run(*args, **kwargs)

        def traced_load(path):
            events.append("oracle")
            return original_load(path)

        with mock.patch.object(gate_module.subprocess, "run", side_effect=traced_run), mock.patch.object(
            gate_module, "_load_oracle", side_effect=traced_load
        ):
            result = run_gate_case(_case(CASE_A_MANIFEST, CASE_A_ORACLE), project_root=ROOT)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(events, ["actor", "oracle"])


class FreshActorAdversarialTest(unittest.TestCase):
    def test_stale_method_trace_is_rejected_in_the_fresh_actor(self) -> None:
        def make_stale(document: dict) -> None:
            current = next(item for item in document["state_refs"] if item["role"] == "current")
            current["ref"]["revision"] = 1

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            case = _materialize_case(
                root,
                CASE_A_MANIFEST,
                CASE_A_ORACLE,
                mutate_alias="method-trace",
                mutate_document=make_stale,
            )
            with mock.patch.object(gate_module.subprocess, "run", wraps=subprocess.run) as spawn:
                result = run_gate_case(case, project_root=root)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("stale for the selected State" in item for item in result["oracle_checks"]))
        spawn.assert_called_once()

    def test_duplicate_candidate_path_id_is_rejected_by_actor(self) -> None:
        manifest = _manifest(CASE_B_MANIFEST)
        manifest["candidate_paths"].append(copy.deepcopy(manifest["candidate_paths"][0]))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            _write_json(path, manifest)
            result = run_gate_case(_case(path, CASE_B_ORACLE), project_root=ROOT)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("candidate path identity" in item for item in result["oracle_checks"]))

    def test_wrong_kind_reopen_basis_is_rejected_by_actor(self) -> None:
        manifest = _manifest(CASE_B_MANIFEST)
        manifest["candidate_paths"][0]["reopen_basis_refs"] = [
            {"object_id": "HYP-PC-B", "revision": 1}
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            _write_json(path, manifest)
            result = run_gate_case(_case(path, CASE_B_ORACLE), project_root=ROOT)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("reopen basis is absent or wrong-kind" in item for item in result["oracle_checks"]))

    def test_weak_private_oracle_is_rejected_after_actor_run(self) -> None:
        oracle = json.loads(CASE_A_ORACLE.read_text(encoding="utf-8"))
        oracle["exact_output"].pop("known_failures")
        with tempfile.TemporaryDirectory() as temporary:
            oracle_path = Path(temporary) / "weak.oracle"
            _write_json(oracle_path, oracle)
            with mock.patch.object(gate_module.subprocess, "run", wraps=subprocess.run) as spawn:
                result = run_gate_case(_case(CASE_A_MANIFEST, oracle_path), project_root=ROOT)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("runner-owned minimum" in item for item in result["oracle_checks"]))
        spawn.assert_called_once()


class CliBoundaryTest(unittest.TestCase):
    def test_cli_generates_a_fresh_report_and_refuses_to_overwrite_it(self) -> None:
        from research_workbench.cli import main

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report.json"
            arguments = [
                "research-state",
                "gate",
                "--case",
                str(CASE_A_MANIFEST),
                str(CASE_A_ORACLE),
                "--case",
                str(CASE_B_MANIFEST),
                str(CASE_B_ORACLE),
                "--root",
                str(ROOT),
                "--output",
                str(output),
            ]
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                first = main(arguments)
                second = main(arguments)
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(first, 0, stream.getvalue())
        self.assertEqual(report["machine_gate"]["status"], "pass")
        self.assertEqual(second, 2)
        self.assertIn("already exists", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
