"""M4-004 run manifest and reproduction tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research_workbench.artifacts.integrity import hash_bytes
from research_workbench.artifacts.repro import RunManifest, check_run_manifest
from research_workbench.contracts.risks import RiskLevel
from research_workbench.validation.documents import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog

MODEL = b"def simulate(params):\n    return params['gain'] * 2\n"
PARAMS = b"gain: 0.5\n"
LOCK = b"python-3.11\npytest-8\n"
OUTPUT = b"gain_doubled,1.0\n"
TASK = b"schema_version: 0.1.0\ntask_id: SIM-001\n"


def _write_project(root: Path) -> None:
    run = root / "runs" / "RUN-SIM-001"
    (run / "outputs").mkdir(parents=True, exist_ok=True)
    (run / "model.py").write_bytes(MODEL)
    (run / "params.yaml.txt").write_bytes(PARAMS)
    (run / "environment-lock.yaml.txt").write_bytes(LOCK)
    (run / "outputs" / "metrics.csv").write_bytes(OUTPUT)
    tasks = root / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    (tasks / "SIM-001.yaml").write_bytes(TASK)


def _manifest(root: Path, **overrides) -> dict:
    manifest = {
        "schema_version": "0.1.0",
        "run_id": "RUN-SIM-001",
        "method_ref": "M-SIM-002@3",
        "input_refs": [
            {"path": "runs/RUN-SIM-001/model.py", "sha256": hash_bytes(MODEL)},
            {"path": "runs/RUN-SIM-001/params.yaml.txt", "sha256": hash_bytes(PARAMS)},
        ],
        "parameters_ref": {"path": "runs/RUN-SIM-001/params.yaml.txt", "sha256": hash_bytes(PARAMS)},
        "environment": {
            "platform": "windows",
            "runtime": "python-3.11",
            "lock_ref": {
                "path": "runs/RUN-SIM-001/environment-lock.yaml.txt",
                "sha256": hash_bytes(LOCK),
            },
        },
        "agent_execution": {
            "task_ref": "tasks/SIM-001.yaml",
            "profile_ref": "simulation-auditor@0.1.0",
        },
        "status": "completed",
        "outputs": [
            {"path": "runs/RUN-SIM-001/outputs/metrics.csv", "sha256": hash_bytes(OUTPUT)}
        ],
        "limitations": ["synthetic fixture"],
    }
    manifest.update(overrides)
    return manifest


class RunManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _write_project(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _risks(self, manifest: dict, rerun_dir: Path | None = None):
        return check_run_manifest(self.root, manifest, rerun_dir)

    def test_valid_manifest_passes_and_infers_kind(self) -> None:
        manifest = _manifest(self.root)
        self.assertEqual(self._risks(manifest), [])
        self.assertEqual(infer_document_kind(manifest), "run_manifest")
        self.assertEqual(SchemaCatalog().validate("run_manifest", manifest), [])

    def test_no_skill_path_is_first_class(self) -> None:
        parsed = RunManifest.from_mapping(_manifest(self.root))
        self.assertTrue(parsed.has_no_skill_path)
        self.assertIsNone(parsed.skill_assignment_ref)
        self.assertEqual(self._risks(_manifest(self.root)), [])

    def test_input_hash_drift_blocks(self) -> None:
        (self.root / "runs" / "RUN-SIM-001" / "model.py").write_bytes(MODEL + b"# drifted\n")
        risks = self._risks(_manifest(self.root))
        self.assertTrue(
            any(r.code == "ARTIFACT-HASH-MISMATCH" and r.level == RiskLevel.BLOCK for r in risks)
        )

    def test_missing_lock_is_repro_gap(self) -> None:
        (self.root / "runs" / "RUN-SIM-001" / "environment-lock.yaml.txt").unlink()
        risks = self._risks(_manifest(self.root))
        self.assertTrue(any(r.code == "REPRO-GAP" and "environment.lock_ref" in r.message for r in risks))

    def test_incomplete_status_warns(self) -> None:
        risks = self._risks(_manifest(self.root, status="incomplete"))
        self.assertTrue(
            any(r.code == "REPRO-GAP" and r.level == RiskLevel.WARNING for r in risks)
        )

    def test_rerun_matching_outputs_passes(self) -> None:
        with tempfile.TemporaryDirectory() as rerun:
            rerun_dir = Path(rerun)
            (rerun_dir / "metrics.csv").write_bytes(OUTPUT)
            self.assertEqual(self._risks(_manifest(self.root), rerun_dir), [])

    def test_rerun_diverging_output_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as rerun:
            rerun_dir = Path(rerun)
            (rerun_dir / "metrics.csv").write_bytes(b"gain_doubled,2.0\n")
            risks = self._risks(_manifest(self.root), rerun_dir)
            self.assertTrue(
                any(r.code == "ARTIFACT-HASH-MISMATCH" and "rerun" in r.message for r in risks)
            )

    def test_rerun_missing_output_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as rerun:
            risks = self._risks(_manifest(self.root), Path(rerun))
            self.assertTrue(
                any(r.code == "REPRO-GAP" and "rerun did not reproduce" in r.message for r in risks)
            )

    def test_schema_rejects_forged_empty_assignment_fields(self) -> None:
        manifest = _manifest(self.root)
        manifest["agent_execution"]["skill_assignment_ref"] = ""
        self.assertNotEqual(SchemaCatalog().validate("run_manifest", manifest), [])


if __name__ == "__main__":
    unittest.main()
