"""Run reconstruction executes research code; reference validation never does."""

from __future__ import annotations

import copy
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

import yaml

from research_workbench.artifacts import run_reconstruction as reconstruction
from research_workbench.artifacts.integrity import hash_file
from research_workbench.cli import main
from research_workbench.contracts import ContractError
from research_workbench.validation.schemas import SchemaCatalog
from tests import test_artifacts_promotion as promotion_fixtures


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = Path("examples/run-reconstruction/linear-recurrence")


class RunReconstructionTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.case = self.root / CASE_PATH
        shutil.copytree(REPO_ROOT / CASE_PATH, self.case)
        self.manifest_path = self.case / "manifest.yaml"
        self.manifest = yaml.safe_load(self.manifest_path.read_bytes())
        environment = json.loads((self.case / "environment.json").read_bytes())
        environment.update(python_implementation=platform.python_implementation(),
                           python_version=platform.python_version(), platform=sys.platform)
        (self.case / "environment.json").write_text(json.dumps(environment), encoding="utf-8")
        self.repin("environment_ref")
        self.save()

    def ref(self, path: Path) -> dict:
        return {"path": path.relative_to(self.root).as_posix(), "sha256": hash_file(path)}

    def repin(self, role: str) -> None:
        previous = self.manifest[role]
        self.manifest[role] = self.ref(self.root / previous["path"])
        if "revision" in previous:
            self.manifest[role]["revision"] = previous["revision"]
        for binding in [*self.manifest["input_bindings"], self.manifest["environment_binding"]]:
            if binding["file_ref"]["path"] == previous["path"]:
                binding["file_ref"] = copy.deepcopy(self.manifest[role])

    def save(self) -> None:
        self.manifest_path.write_text(yaml.safe_dump(self.manifest), encoding="utf-8")

    def run_case(self, name: str = "A-001") -> dict:
        self.save()
        return reconstruction.reproduce_run(self.root, self.manifest_path,
                                            attempt_dir=f"work/M4-004/{name}")

    def program(self, text: str) -> None:
        (self.case / "simulate.py").write_text(text, encoding="utf-8")
        self.repin("code_ref")

    def test_shipped_manifest_pins_are_closed_without_execution(self) -> None:
        manifest = yaml.safe_load((REPO_ROOT / CASE_PATH / "manifest.yaml").read_bytes())
        with mock.patch.object(reconstruction.subprocess, "Popen", side_effect=AssertionError("must not execute")):
            self.assertEqual(reconstruction.check_run_manifest(REPO_ROOT, manifest), [])
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["validate", str(REPO_ROOT / CASE_PATH), "--root", str(REPO_ROOT)]), 0)

    def test_real_fresh_process_has_no_agent_environment_and_report_is_generically_valid(self) -> None:
        original = (self.case / "simulate.py").read_text(encoding="utf-8")
        self.program("import os, sys\nassert 'RWB_AGENT_SESSION' not in os.environ\n"
                     "assert sys.flags.isolated and sys.flags.no_site\n" + original)
        with mock.patch.dict(os.environ, {"RWB_AGENT_SESSION": "private-session"}):
            report = self.run_case()
        self.assertEqual(report["status"], "matched")
        self.assertTrue(report["executed"])
        self.assertNotEqual(report["child_pid"], os.getpid())
        self.assertTrue(report["negative_result"])
        self.assertEqual(report["returncode"], 0)
        self.assertEqual(SchemaCatalog().validate("run_reconstruction_report", report), [])
        stage = self.root / report["cwd"]
        self.assertEqual((stage / "outputs/trajectory.csv").read_bytes(), (self.case / "trajectory.csv").read_bytes())
        self.assertFalse(any(report["authority_boundaries"].values()))
        report_path = self.root / "work/M4-004/A-001/reconstruction-report.json"
        with mock.patch.object(reconstruction.subprocess, "Popen", side_effect=AssertionError("read only")):
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["validate", str(report_path), "--root", str(self.root)]), 0)
        (stage / "outputs/trajectory.csv").write_bytes(b"changed\n")
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["validate", str(report_path), "--root", str(self.root)]), 1)

    def test_each_input_pin_drift_stops_before_execution(self) -> None:
        refs = [self.manifest[role] for role in ("run_ref", "code_ref", "input_ref", "parameters_ref", "environment_ref")]
        refs.append(self.manifest["expected_outputs"][0]["artifact_ref"])
        with mock.patch.object(reconstruction.subprocess, "Popen", side_effect=AssertionError("must not execute")):
            for index, reference in enumerate(refs):
                with self.subTest(reference=reference["path"]):
                    path = self.root / reference["path"]
                    original = path.read_bytes()
                    path.write_bytes(original + b" ")
                    report = self.run_case(f"drift-{index}")
                    self.assertEqual(report["status"], "pin-drift")
                    self.assertFalse(report["executed"])
                    path.write_bytes(original)

    def test_missing_input_and_mismatched_environment_are_distinct_preflight_failures(self) -> None:
        original = (self.case / "inputs.json.txt").read_bytes()
        (self.case / "inputs.json.txt").unlink()
        self.assertEqual(self.run_case("missing")["status"], "prerequisite-missing")
        (self.case / "inputs.json.txt").write_bytes(original)
        environment = json.loads((self.case / "environment.json").read_bytes())
        environment["python_version"] = "3.0.0"
        (self.case / "environment.json").write_text(json.dumps(environment), encoding="utf-8")
        self.repin("environment_ref")
        report = self.run_case("environment")
        self.assertEqual(report["status"], "prerequisite-missing")
        self.assertFalse(report["executed"])

    def test_unadmitted_raw_input_cannot_be_executed_even_with_correct_bytes(self) -> None:
        raw_input = self.root / "sources/raw/input.json.txt"
        raw_input.parent.mkdir(parents=True)
        raw_input.write_bytes((self.case / "inputs.json.txt").read_bytes())
        self.manifest["input_ref"] = self.ref(raw_input)
        self.manifest["input_bindings"][0]["file_ref"] = self.ref(raw_input)
        with mock.patch.object(reconstruction.subprocess, "Popen", side_effect=AssertionError("must not execute")):
            report = self.run_case()
        self.assertEqual(report["status"], "manifest-invalid")
        self.assertFalse(report["executed"])
        self.assertIn("admission", report["detail"].lower())

    def test_repinned_parameter_change_is_output_difference_not_pin_drift(self) -> None:
        (self.case / "parameters.json.txt").write_text('{"x0":0,"a":2}', encoding="utf-8")
        self.repin("parameters_ref")
        report = self.run_case()
        self.assertEqual(report["status"], "output-different")
        self.assertTrue(report["executed"])
        self.assertFalse(report["comparisons"][0]["matched"])
        self.assertTrue((self.case / "trajectory.csv").is_file())
        self.assertTrue((self.root / report["output_refs"][0]["path"]).is_file())

    def test_missing_and_extra_outputs_are_reported(self) -> None:
        self.program("from pathlib import Path\nPath('outputs/extra.txt').write_text('extra')\n")
        report = self.run_case()
        self.assertEqual(report["status"], "output-different")
        rows = {row["output_path"]: row for row in report["comparisons"]}
        self.assertIsNone(rows["trajectory.csv"]["actual_sha256"])
        self.assertIsNone(rows["extra.txt"]["expected_sha256"])

    def test_nonzero_and_timeout_keep_partial_artifacts_and_diagnostics(self) -> None:
        prefix = "from pathlib import Path\nPath('outputs/partial.txt').write_text('partial')\n"
        self.program(prefix + "import sys\nprint('diagnostic', file=sys.stderr)\nraise SystemExit(7)\n")
        report = self.run_case("nonzero")
        self.assertEqual(report["status"], "run-failed")
        self.assertEqual(report["returncode"], 7)
        self.assertIn(b"diagnostic", (self.root / report["stderr_ref"]["path"]).read_bytes())
        self.assertEqual(len(report["output_refs"]), 1)
        self.program(prefix + "import time\ntime.sleep(5)\n")
        self.manifest["timeout_seconds"] = 1
        report = self.run_case("timeout")
        self.assertEqual(report["status"], "run-failed")
        self.assertIn("timeout", report["detail"])
        self.assertEqual(len(report["output_refs"]), 1)

    def test_path_boundary_alias_run_identity_and_authority_are_rejected(self) -> None:
        original = copy.deepcopy(self.manifest)
        variants = []
        for path in ("../outside.py", "sources/inbox/untrusted.py"):
            candidate = copy.deepcopy(original)
            candidate["code_ref"]["path"] = path
            variants.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["input_ref"] = candidate["parameters_ref"]
        variants.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["run_id"] = "ANOTHER-RUN"
        variants.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["authority_boundaries"]["claim_acceptance"] = True
        variants.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["expected_outputs"].append(candidate["expected_outputs"][0])
        variants.append(candidate)
        for candidate in variants:
            with self.subTest(candidate=candidate):
                self.assertEqual(reconstruction.check_run_manifest(self.root, candidate)[0]["status"], "manifest-invalid")

    def test_existing_or_external_attempt_is_never_overwritten(self) -> None:
        self.run_case()
        with self.assertRaises(FileExistsError):
            self.run_case()
        with self.assertRaises(ContractError):
            reconstruction.reproduce_run(self.root, self.manifest_path, attempt_dir="objects/run-output")
        with self.assertRaises(ContractError):
            reconstruction.reproduce_run(self.root, self.root.parent / "outside.yaml", attempt_dir="work/unused")

    def test_malformed_manifest_or_pinned_document_fails_clearly_without_execution(self) -> None:
        self.manifest_path.write_text("manifest_kind: [", encoding="utf-8")
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["run", "check", str(self.manifest_path), "--root", str(self.root)]), 2)
        with self.assertRaises(ContractError):
            reconstruction.reproduce_run(self.root, self.manifest_path, attempt_dir="work/unallocated")
        self.assertFalse((self.root / "work/unallocated").exists())
        (self.case / "run.yaml").write_text("object_id: [", encoding="utf-8")
        self.repin("run_ref")
        report = self.run_case()
        self.assertEqual(report["status"], "manifest-invalid")
        self.assertFalse(report["executed"])

    def test_repinning_run_does_not_allow_unrelated_input_environment_or_output_refs(self) -> None:
        original = yaml.safe_load((self.case / "run.yaml").read_bytes())
        changes = {"input_refs": ["INPUT-UNRELATED@99"],
                   "environment_ref": "ENV-UNRELATED@99",
                   "output_refs": ["ARTIFACT-UNRELATED@99"]}
        for field, value in changes.items():
            with self.subTest(field=field):
                run = dict(original, **{field: value})
                (self.case / "run.yaml").write_text(yaml.safe_dump(run), encoding="utf-8")
                self.repin("run_ref")
                self.assertEqual(reconstruction.check_run_manifest(self.root, self.manifest)[0]["status"], "manifest-invalid")
                with mock.patch.object(reconstruction.subprocess, "Popen", side_effect=AssertionError("must not execute")):
                    report = self.run_case(field)
                self.assertEqual(report["status"], "manifest-invalid")
                self.assertFalse(report["executed"])

    def test_object_revision_and_declared_hash_close_without_reinterpreting_file_bytes(self) -> None:
        run = yaml.safe_load((self.case / "run.yaml").read_bytes())
        self.manifest["input_bindings"][0]["object_ref"] = {"object_id": "INPUT-M4-LINEAR-001", "revision": 1}
        self.manifest["expected_outputs"][0]["object_ref"] = {"object_id": "ARTIFACT-M4-TRAJECTORY-001", "revision": 1}
        environment_ref = {"object_id": "ENV-M4-LINEAR-001", "revision": 1, "sha256": "a" * 64}
        run["environment_ref"] = environment_ref
        self.manifest["environment_binding"]["object_ref"] = dict(environment_ref, sha256="sha256:" + "A" * 64)
        (self.case / "run.yaml").write_text(yaml.safe_dump(run), encoding="utf-8")
        self.repin("run_ref")
        self.assertNotEqual(environment_ref["sha256"], self.manifest["environment_ref"]["sha256"])
        self.assertEqual(self.run_case("declared-hash")["status"], "matched")
        for field, value in (("revision", 2), ("sha256", "b" * 64)):
            changed = copy.deepcopy(run)
            changed["environment_ref"][field] = value
            (self.case / "run.yaml").write_text(yaml.safe_dump(changed), encoding="utf-8")
            self.repin("run_ref")
            self.assertEqual(reconstruction.check_run_manifest(self.root, self.manifest)[0]["status"], "manifest-invalid")
        run["revision"] = 2
        (self.case / "run.yaml").write_text(yaml.safe_dump(run), encoding="utf-8")
        self.repin("run_ref")
        self.assertEqual(reconstruction.check_run_manifest(self.root, self.manifest)[0]["status"], "manifest-invalid")

    def test_object_file_bindings_reject_duplicates_missing_extra_and_wrong_files(self) -> None:
        original = copy.deepcopy(self.manifest)
        variants = []
        candidate = copy.deepcopy(original)
        candidate["input_bindings"][0] = candidate["input_bindings"][1]
        variants.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["input_bindings"].pop()
        variants.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["input_bindings"].append(candidate["input_bindings"][0])
        variants.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["input_bindings"][0]["file_ref"] = candidate["code_ref"]
        variants.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["environment_binding"]["file_ref"] = candidate["input_ref"]
        variants.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["input_bindings"][0]["object_ref"] = "INPUT-M4-LINEAR-001"
        variants.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["run_ref"].pop("revision")
        variants.append(candidate)
        candidate = copy.deepcopy(original)
        candidate["input_bindings"][0]["file_ref"]["revision"] = 99
        variants.append(candidate)
        for candidate in variants:
            with self.subTest(candidate=candidate):
                self.assertEqual(reconstruction.check_run_manifest(self.root, candidate)[0]["status"], "manifest-invalid")

    def test_cli_runs_from_unrelated_cwd_without_existing_agent_process(self) -> None:
        environment = dict(os.environ, PYTHONPATH=str(REPO_ROOT / "src"))
        command = [sys.executable, "-c", "from research_workbench.cli import main; raise SystemExit(main())",
                   "run", "reproduce", self.manifest_path.as_posix(), "--root", str(self.root),
                   "--attempt-dir", "work/M4-004/cli-fresh"]
        result = subprocess.run(command, cwd=self.root.parent, env=environment, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)["status"], "matched")

    def test_actual_promotion_receipt_binds_published_target_without_checker_reexecution(self) -> None:
        fixture = promotion_fixtures.PromotionFixture()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.output.write_bytes((self.case / "trajectory.csv").read_bytes())
        fixture.rerun_host()
        result = fixture.execute()
        shutil.copytree(self.case, fixture.root / CASE_PATH)
        manifest = copy.deepcopy(self.manifest)
        manifest["expected_outputs"][0]["artifact_ref"] = fixture.ref(fixture.root / "objects/M4-002/result.txt")
        manifest["promotion_receipt_ref"] = fixture.ref(fixture.root / result.receipt)
        with mock.patch.object(reconstruction.subprocess, "Popen", side_effect=AssertionError("read only")):
            self.assertEqual(reconstruction.check_run_manifest(fixture.root, manifest), [])
            manifest["expected_outputs"][0]["artifact_ref"] = fixture.ref(fixture.root / CASE_PATH / "trajectory.csv")
            self.assertEqual(reconstruction.check_run_manifest(fixture.root, manifest)[0]["status"], "manifest-invalid")


if __name__ == "__main__":
    unittest.main()
