"""Static fixture consistency tests for examples/api-execution.

The committed chains must stay schema-valid, cross-consistent, and
recoverable from files alone. They are offline contract evidence, never a
real API or scientific-value claim.
"""

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from research_workbench.cli import main as cli_main
from research_workbench.context import assess_handoff_transfer
from research_workbench.io import load_document
from research_workbench.observability import ExecutionReceipt, check_execution_receipt
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import AttemptRecord, HandoffPacket, TaskPacket
from research_workbench.validation import check_handoff_against_task
from research_workbench.validation.documents import load_and_validate


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "api-execution"

SCENARIOS = ("completed", "tool-failed", "safe-paused")

EXPECTED_STATUS = {
    "completed": "completed",
    "tool-failed": "failed",
    "safe-paused": "safe-paused",
}

RECOVERY_SCENARIOS = ("completed", "safe-paused", "tool-failed")


def run_cli(arguments: list[str]) -> tuple[int, str]:
    stream = io.StringIO()
    with redirect_stdout(stream):
        code = cli_main(arguments)
    return code, stream.getvalue()


def batch_directory(scenario: str) -> Path:
    task_root = FIXTURES / scenario / "work" / "EVID-001"
    attempts = [entry for entry in task_root.iterdir() if entry.is_dir()]
    if len(attempts) != 1:
        raise AssertionError(f"expected exactly one attempt directory: {task_root}")
    return attempts[0]


def checkpoint_path(scenario: str) -> Path:
    checkpoints = list((FIXTURES / scenario / "checkpoints").glob("MS-*.yaml"))
    if len(checkpoints) != 1:
        raise AssertionError(f"expected exactly one checkpoint: {scenario}")
    return checkpoints[0]


class ApiExecutionFixtureTests(unittest.TestCase):
    def test_all_scenarios_are_schema_and_reference_valid(self) -> None:
        paths = [path for scenario in SCENARIOS for path in (FIXTURES / scenario).rglob("*") if path.suffix in {".yaml", ".yml"}]
        documents, issues = load_and_validate(paths)
        self.assertEqual([], [issue for issue in issues if str(issue.severity) == "Severity.ERROR"])
        self.assertGreater(len(documents), 20)

    def test_chains_are_cross_consistent_and_validator_clean(self) -> None:
        task = TaskPacket.from_mapping(load_document(ROOT / "examples" / "task-evidence.yaml"))
        protocol = ProjectProtocol.from_mapping(load_document(ROOT / "examples" / "project-protocol.yaml"))
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                batch = batch_directory(scenario)
                attempt = AttemptRecord.from_mapping(load_document(batch / "attempt.yaml"))
                handoff = HandoffPacket.from_mapping(load_document(batch / "handoff.yaml"))
                receipt = ExecutionReceipt.from_mapping(
                    load_document(batch / "execution-receipt.yaml")
                )
                self.assertEqual(EXPECTED_STATUS[scenario], attempt.status)
                self.assertEqual(EXPECTED_STATUS[scenario], handoff.status)
                self.assertEqual(EXPECTED_STATUS[scenario], receipt.status)
                self.assertEqual("model-api", receipt.execution_kind)
                receipt_ref = (batch / "execution-receipt.yaml").relative_to(ROOT).as_posix()
                groups = (
                    check_execution_receipt(receipt, protocol, root=ROOT, receipt_ref=receipt_ref),
                    check_handoff_against_task(task, handoff, project_root=ROOT),
                    assess_handoff_transfer(load_document(batch / "transfer-audit.yaml"), root=ROOT).risks,
                )
                blockers = [
                    risk.code for group in groups for risk in group if risk.level.value == "block"
                ]
                self.assertEqual([], blockers)

    def test_completed_scenario_claims_only_through_machine_check(self) -> None:
        batch = batch_directory("completed")
        receipt = ExecutionReceipt.from_mapping(load_document(batch / "execution-receipt.yaml"))
        self.assertEqual("contract-satisfied", receipt.completion_claim)
        check = load_document(batch / "check-report.yaml")
        self.assertEqual("pass", check["status"])
        resolved = [Path(ref).name for ref in receipt.validation_refs]
        self.assertIn("check-report.yaml", resolved)

    def test_checker_source_pins_match_the_current_checks_module(self) -> None:
        """M-5 regression: the fixtures pin the checker by hash; editing
        execution/checks.py without regenerating must fail here."""

        from research_workbench.artifacts.integrity import hash_file

        current = hash_file(ROOT / "src" / "research_workbench" / "execution" / "checks.py")
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                check = load_document(batch_directory(scenario) / "check-report.yaml")
                source = check["checker"]["source_ref"]
                self.assertEqual("src/research_workbench/execution/checks.py", source["path"])
                self.assertEqual(current, source["sha256"])

    def test_recovery_from_files_alone_via_fresh_cli_sessions(self) -> None:
        for scenario in RECOVERY_SCENARIOS:
            with self.subTest(scenario=scenario):
                code, output = run_cli(
                    [
                        "context", "resume-check",
                        str(checkpoint_path(scenario)),
                        "--protocol", str(ROOT / "examples" / "project-protocol.yaml"),
                        "--root", str(ROOT),
                    ]
                )
                self.assertEqual(0, code, output)
                self.assertIn("no blocking", output)

    def test_readme_documents_offline_boundary(self) -> None:
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        self.assertIn("offline", readme.lower())
        self.assertIn("stale-input", readme)
        self.assertIn("regenerate", readme.lower())
        self.assertTrue((FIXTURES / "regenerate.py").is_file())
        # No fixture directory exists for the stale path: it writes nothing.
        self.assertFalse((FIXTURES / "stale").exists())


if __name__ == "__main__":
    unittest.main()
