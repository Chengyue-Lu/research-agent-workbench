"""CLI wiring tests for `rwb execute task`.

The CLI surface only proves argument plumbing and the two safe paths:
a dry run compiles without any provider, and a missing live provider blocks
with zero writes. Session behaviour itself is covered by the E2E suite.
"""

import io
import shutil
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from research_workbench.cli import main as cli_main


ROOT = Path(__file__).resolve().parents[1]

TASK_PATH = "examples/task-evidence.yaml"
PROFILE_PATH = "registry/agents/evidence-scout.yaml"
ASSIGNMENT_PATH = "examples/vertical-slice/evidence-assignment.yaml"
PROTOCOL_PATH = "examples/project-protocol.yaml"
POOL_PATH = "registry/models/pool.cli-test.yaml"
CHECKER_PATH = "src/research_workbench/execution/checks.py"

POOL_DOCUMENT = """\
schema_version: "0.1.0"
registry_kind: model_pool
pool_id: cli-test-pool
selection_policy: explicit-slot-only
slots:
  - slot_id: worker
    role: worker
    provider_adapter: live-adapter
    model_env: RWB_WORKER_MODEL
    enabled: true
    capabilities: [text, tools, structured_output]
"""


def run_cli(arguments: list[str]) -> tuple[int, str]:
    stream = io.StringIO()
    with redirect_stdout(stream):
        code = cli_main(arguments)
    return code, stream.getvalue()


class ExecuteTaskCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        shutil.copytree(ROOT / "examples" / "fixtures", self.root / "examples" / "fixtures")
        shutil.copytree(
            ROOT / ".agents" / "skills" / "literature-evidence-extraction",
            self.root / ".agents" / "skills" / "literature-evidence-extraction",
            dirs_exist_ok=True,
        )
        for relative in (TASK_PATH, PROTOCOL_PATH, ASSIGNMENT_PATH, PROFILE_PATH):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / relative, target)
        pool = self.root / POOL_PATH
        pool.parent.mkdir(parents=True, exist_ok=True)
        pool.write_text(POOL_DOCUMENT, encoding="utf-8")
        checker = self.root / CHECKER_PATH
        checker.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / CHECKER_PATH, checker)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def arguments(self, *extra: str) -> list[str]:
        return [
            "execute", "task", TASK_PATH,
            "--profile", PROFILE_PATH,
            "--assignment", ASSIGNMENT_PATH,
            "--slot", "worker",
            "--pool", POOL_PATH,
            "--protocol", PROTOCOL_PATH,
            "--root", str(self.root),
            "--model-env", "RWB_WORKER_MODEL=worker-model",
            *extra,
        ]

    def test_dry_run_compiles_and_writes_nothing(self) -> None:
        code, output = run_cli(self.arguments("--dry-run"))

        self.assertEqual(0, code, output)
        self.assertIn("compiled attempt A-", output)
        self.assertIn("no session was run", output)
        self.assertFalse((self.root / "work").exists())
        self.assertFalse((self.root / "checkpoints").exists())

    def test_dry_run_json_summary_is_machine_readable(self) -> None:
        import json

        code, output = run_cli(self.arguments("--dry-run", "--json"))

        self.assertEqual(0, code, output)
        summary = json.loads(output)
        self.assertEqual("EVID-001", summary["task_id"])
        self.assertEqual("worker", summary["slot"])
        self.assertEqual("live-adapter", summary["provider"])
        self.assertTrue(summary["dry_run"])

    def test_missing_live_provider_blocks_with_zero_writes(self) -> None:
        code, output = run_cli(self.arguments())

        self.assertEqual(2, code, output)
        self.assertIn("EXEC-PROVIDER-NOT-CONFIGURED", output)
        self.assertFalse((self.root / "work").exists())
        self.assertFalse((self.root / "checkpoints").exists())

    def test_invalid_model_env_argument_is_rejected(self) -> None:
        code, output = run_cli(
            [
                "execute", "task", TASK_PATH,
                "--profile", PROFILE_PATH,
                "--assignment", ASSIGNMENT_PATH,
                "--slot", "worker",
                "--pool", POOL_PATH,
                "--protocol", PROTOCOL_PATH,
                "--root", str(self.root),
                "--model-env", "NOT_AN_ASSIGNMENT",
                "--dry-run",
            ]
        )

        self.assertEqual(2, code, output)
        self.assertIn("NAME=VALUE", output)


if __name__ == "__main__":
    unittest.main()
