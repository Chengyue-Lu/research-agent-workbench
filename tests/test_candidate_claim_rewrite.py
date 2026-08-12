import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research_workbench.artifacts.integrity import hash_directory, hash_file
from research_workbench.capability.catalog import load_candidates
from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill-lab/candidates/claim-preserving-rewrite/scripts/check_claim_preservation.py"
FIXTURES = ROOT / "tests/fixtures/claim-preserving-rewrite"


class ClaimPreservingRewriteCandidateTests(unittest.TestCase):
    def run_checker(self, revision: str) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(FIXTURES / "source.txt"),
                str(FIXTURES / revision),
                "--lock",
                str(FIXTURES / "claim-lock.json"),
                "--json",
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_revision_preserves_surface_locks(self) -> None:
        result = self.run_checker("valid-revision.txt")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertIs(report["valid"], True)
        self.assertIn("human review", report["scope"])

    def test_invalid_revision_reports_independent_drift_codes(self) -> None:
        result = self.run_checker("invalid-revision.txt")
        self.assertEqual(1, result.returncode)
        report = json.loads(result.stdout)
        failed = {item["code"] for item in report["checks"] if item["status"] == "fail"}
        self.assertTrue(
            {
                "CLAIM-NUMBER-DRIFT",
                "CLAIM-CITATION-DRIFT",
                "CLAIM-POLARITY-DRIFT",
                "CLAIM-STRENGTHENED",
                "CLAIM-CAUSALITY-INTRODUCED",
            }.issubset(failed)
        )

    def test_empty_revision_is_explicitly_blocked(self) -> None:
        result = self.run_checker("empty-revision.txt")
        self.assertEqual(1, result.returncode)
        report = json.loads(result.stdout)
        failed = {item["code"] for item in report["checks"] if item["status"] == "fail"}
        self.assertIn("CLAIM-REVISION-EMPTY", failed)

    def test_checker_writes_a_pinned_formal_report_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report.json"
            command = [
                sys.executable,
                str(SCRIPT),
                str(FIXTURES / "source.txt"),
                str(FIXTURES / "valid-revision.txt"),
                "--lock",
                str(FIXTURES / "claim-lock.json"),
                "--root",
                str(ROOT),
                "--output",
                str(output),
            ]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            report = load_document(output)
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        committed = load_document(
            ROOT / "examples/evals/claim-preserving-rewrite/with-skill-check.json"
        )
        self.assertEqual(0, first.returncode, first.stdout + first.stderr)
        self.assertEqual([], SchemaCatalog().validate("deterministic_check_report", report))
        self.assertEqual("pass", report["status"])
        self.assertEqual(
            {key: value for key, value in committed.items() if key != "report_id"},
            {key: value for key, value in report.items() if key != "report_id"},
        )
        self.assertNotEqual(0, second.returncode)

    def test_candidate_is_not_discoverable_or_accepted(self) -> None:
        self.assertTrue(SCRIPT.is_file())
        self.assertFalse((ROOT / ".agents/skills/claim-preserving-rewrite").exists())
        candidates = load_candidates(ROOT / "registry/skills/candidates.json")
        candidate = next(item for item in candidates if item["candidate_id"] == "rwb-claim-preserving-rewrite")
        self.assertEqual("triage", candidate["status"])
        package = SCRIPT.parents[1]
        self.assertEqual(
            candidate["content_hash"].removeprefix("sha256:"),
            hash_file(package / "SKILL.md"),
        )
        self.assertEqual(
            candidate["package_hash"].removeprefix("sha256:"),
            hash_directory(package),
        )
        manifest = load_document(ROOT / "registry/skills/candidates/claim-preserving-rewrite.yaml")
        self.assertEqual([], SchemaCatalog().validate("skill_manifest", manifest))
        manifest_source = manifest["source"]
        self.assertEqual(
            candidate["content_hash"].removeprefix("sha256:"),
            manifest_source["content_hash"],
        )
        self.assertEqual(
            candidate["package_hash"].removeprefix("sha256:"),
            manifest_source["package_hash"],
        )
        sources = load_document(ROOT / "registry/skills/sources.json")["sources"]
        source = next(item for item in sources if item["source_id"] == candidate["source_id"])
        self.assertEqual(candidate["package_hash"], source["revision"])


if __name__ == "__main__":
    unittest.main()
