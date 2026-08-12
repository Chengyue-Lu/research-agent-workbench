import contextlib
import copy
import io
import tempfile
import unittest
from pathlib import Path

from research_workbench.cli import main
from research_workbench.context import (
    CONTEXT_METRIC_NAMES,
    ContextPolicySnapshot,
    ContextSnapshot,
    MainStatePacket,
)
from research_workbench.contracts import ContractError
from research_workbench.io import load_document
from research_workbench.observability import ExecutionReceipt, check_execution_receipt
from research_workbench.protocol import ProjectProtocol


ROOT = Path(__file__).resolve().parents[1]


def run_cli(arguments: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(arguments)
    return code, output.getvalue()


class ContextGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = ProjectProtocol.from_mapping(load_document(ROOT / "examples/project-protocol.yaml"))
        self.policy = ContextPolicySnapshot.from_project_policy(self.protocol.context_policy)
        self.zero_metrics = {name: 0 for name in CONTEXT_METRIC_NAMES}

    def test_main_raw_material_is_blocked_before_context_growth(self) -> None:
        metrics = dict(self.zero_metrics)
        metrics["raw_material_chars"] = 1
        snapshot = ContextSnapshot.create(
            snapshot_id="CTX-BLOCK",
            captured_at="2026-08-13T00:00:00Z",
            scope="main",
            measurement_source="file-estimate",
            metrics=metrics,
            unknown_metrics=(),
            handoff_ready=None,
            policy=self.policy,
        )
        self.assertEqual("block", snapshot.assessment.level)
        self.assertIn("CTX-MAIN-RAW-MATERIAL", snapshot.assessment.triggered_rules)

    def test_task_compaction_is_only_recoverable_after_handoff(self) -> None:
        metrics = dict(self.zero_metrics)
        metrics["compaction_events"] = 1
        recoverable = ContextSnapshot.create(
            snapshot_id="CTX-RECOVERABLE",
            captured_at="2026-08-13T00:00:00Z",
            scope="task",
            measurement_source="runtime",
            metrics=metrics,
            unknown_metrics=(),
            handoff_ready=True,
            policy=self.policy,
        )
        lost = ContextSnapshot.create(
            snapshot_id="CTX-LOSS",
            captured_at="2026-08-13T00:00:00Z",
            scope="task",
            measurement_source="runtime",
            metrics=metrics,
            unknown_metrics=(),
            handoff_ready=False,
            policy=self.policy,
        )
        self.assertEqual("warn", recoverable.assessment.level)
        self.assertIn("CTX-SUBAGENT-COMPACTION-RECOVERABLE", recoverable.assessment.triggered_rules)
        self.assertEqual("block", lost.assessment.level)
        self.assertIn("CTX-HANDOFF-LOSS", lost.assessment.triggered_rules)

    def test_snapshot_rejects_falsified_assessment(self) -> None:
        document = copy.deepcopy(load_document(ROOT / "examples/observability/context-main-warn.yaml"))
        document["assessment"]["level"] = "ok"
        with self.assertRaises(ContractError):
            ContextSnapshot.from_mapping(document)

    def test_checkpoint_and_resume_are_file_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "demo"
            self.assertEqual(0, run_cli(["init", str(project), "--project-id", "demo"])[0])
            snapshot = project / "checkpoints" / "CTX-0001.yaml"
            assess_args = [
                "context", "assess",
                "--id", "CTX-0001",
                "--protocol", str(project / "project-protocol.yaml"),
                "--scope", "main",
                "--captured-at", "2026-08-13T00:00:00Z",
                "--metric", "loaded_chars=25000",
                "--output", str(snapshot),
            ]
            self.assertEqual(0, run_cli(assess_args)[0])
            state = project / "checkpoints" / "MS-0001.yaml"
            checkpoint_args = [
                "context", "checkpoint",
                "--id", "MS-0001",
                "--protocol", str(project / "project-protocol.yaml"),
                "--root", str(project),
                "--snapshot", str(snapshot),
                "--next-action", "Define one bounded Task.",
                "--created-at", "2026-08-13T00:01:00Z",
                "--output", str(state),
            ]
            self.assertEqual(0, run_cli(checkpoint_args)[0])
            parsed = MainStatePacket.from_mapping(load_document(state))
            self.assertIsNotNone(parsed.checkpoint_digest)
            code, output = run_cli(
                [
                    "context", "resume-check", str(state),
                    "--protocol", str(project / "project-protocol.yaml"),
                    "--root", str(project),
                ]
            )
            self.assertEqual(0, code)
            self.assertIn("no blocking", output)

    def test_tampered_checkpoint_digest_is_rejected(self) -> None:
        document = copy.deepcopy(load_document(ROOT / "examples/main-state.yaml"))
        document["next_actions"] = ["Silent goal replacement"]
        with self.assertRaises(ContractError):
            MainStatePacket.from_mapping(document)


class ExecutionReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = ProjectProtocol.from_mapping(load_document(ROOT / "examples/project-protocol.yaml"))
        self.receipt_path = ROOT / "examples/observability/execution-evidence-contract.yaml"

    def test_contract_slice_receipt_has_no_blocking_risk(self) -> None:
        receipt = ExecutionReceipt.from_mapping(load_document(self.receipt_path))
        risks = check_execution_receipt(
            receipt,
            self.protocol,
            root=ROOT,
            receipt_ref="examples/observability/execution-evidence-contract.yaml",
        )
        self.assertEqual([], risks)

    def test_cost_fanout_review_and_trace_faults_are_visible(self) -> None:
        document = copy.deepcopy(load_document(self.receipt_path))
        document["execution_kind"] = "native-agent"
        document["model_usage_status"] = "unavailable"
        document["coordination"].update(
            {
                "max_parallel_observed": 3,
                "review_rounds": 2,
                "coordination_tokens": 60,
                "execution_tokens": 40,
            }
        )
        document["trace"].update(
            {"mode": "full", "external": True, "sensitive_data_detected": True}
        )
        receipt = ExecutionReceipt.from_mapping(document)
        codes = {
            risk.code
            for risk in check_execution_receipt(
                receipt,
                self.protocol,
                root=ROOT,
                receipt_ref="examples/observability/execution-evidence-contract.yaml",
            )
        }
        self.assertTrue(
            {
                "COST-USAGE-UNKNOWN",
                "COORDINATION-COST-HIGH",
                "DELEGATION-FANOUT",
                "REVIEW-LOOP",
                "TRACE-SENSITIVE",
                "TRACE-DATA-BOUNDARY",
                "TRACE-OVERRETENTION",
            }.issubset(codes)
        )


if __name__ == "__main__":
    unittest.main()
