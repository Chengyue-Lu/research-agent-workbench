import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.cli import main
from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]


def run_cli(arguments: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(arguments)
    return code, output.getvalue()


class CliTests(unittest.TestCase):
    def test_validate_runs_schema_and_live_reference_checks(self) -> None:
        code, output = run_cli(
            [
                "validate",
                str(ROOT / "examples"),
                str(ROOT / "registry"),
                "--root",
                str(ROOT),
            ]
        )
        self.assertEqual(0, code)
        self.assertIn("errors=0 warnings=0", output)

    def test_invalid_fixture_returns_nonzero_with_local_pointer(self) -> None:
        code, output = run_cli(
            [
                "validate",
                str(ROOT / "tests" / "fixtures" / "invalid" / "objects" / "claim.json"),
                "--root",
                str(ROOT),
            ]
        )
        self.assertEqual(1, code)
        self.assertIn("$.strength", output)

    def test_task_resolve_emits_pinned_skill_and_effective_permissions(self) -> None:
        code, output = run_cli(
            [
                "task",
                "resolve",
                str(ROOT / "examples" / "task-evidence.yaml"),
                "--profile",
                str(ROOT / "examples" / "profiles" / "evidence-scout.yaml"),
                "--skill",
                str(ROOT / "examples" / "skills" / "literature-evidence-extraction.yaml"),
            ]
        )
        self.assertEqual(0, code)
        resolved = json.loads(output)
        self.assertEqual("worktree-write", resolved["effective_permissions"]["filesystem"])
        self.assertEqual(["work/EVID-001"], resolved["effective_permissions"]["allowed_roots"])
        self.assertEqual(64, len(resolved["skill_lock"][0]["content_hash"]))

    def test_handoff_check_matches_task_and_live_input(self) -> None:
        code, output = run_cli(
            [
                "handoff",
                "validate",
                str(ROOT / "examples" / "handoff-evidence.yaml"),
                "--task",
                str(ROOT / "examples" / "task-evidence.yaml"),
                "--root",
                str(ROOT),
            ]
        )
        self.assertEqual(0, code)
        self.assertIn("no blocking", output)

    def test_init_and_checkpoint_create_valid_non_overwriting_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "demo"
            code, _ = run_cli(["init", str(project), "--project-id", "demo"])
            self.assertEqual(0, code)
            checkpoint = project / "checkpoints" / "MS-0001.yaml"
            code, _ = run_cli(
                [
                    "context",
                    "checkpoint",
                    "--id",
                    "MS-0001",
                    "--protocol",
                    str(project / "project-protocol.yaml"),
                    "--output",
                    str(checkpoint),
                    "--root",
                    str(project),
                    "--next-action",
                    "Define the first bounded question.",
                ]
            )
            self.assertEqual(0, code)
            self.assertEqual([], SchemaCatalog(ROOT / "schemas").validate("main_state", load_document(checkpoint)))
            repeat_code, _ = run_cli(["init", str(project)])
            self.assertEqual(2, repeat_code)


if __name__ == "__main__":
    unittest.main()
