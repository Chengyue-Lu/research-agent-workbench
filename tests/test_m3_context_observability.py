import contextlib
import copy
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from research_workbench.artifacts import hash_file
from research_workbench.cli import main
from research_workbench.context import (
    CONTEXT_METRIC_NAMES,
    ContextBudgetEstimate,
    ContextPolicySnapshot,
    ContextSnapshot,
    MainStatePacket,
    checkpoint_digest,
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
            handoff_audit_ref="checks/HTA-RECOVERABLE.yaml",
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

    def test_compacted_task_cannot_self_declare_ready_without_transfer_audit(self) -> None:
        metrics = dict(self.zero_metrics)
        metrics["compaction_events"] = 1
        with self.assertRaises(ContractError):
            ContextSnapshot.create(
                snapshot_id="CTX-UNBOUND",
                captured_at="2026-08-13T00:00:00Z",
                scope="task",
                measurement_source="runtime",
                metrics=metrics,
                unknown_metrics=(),
                handoff_ready=True,
                policy=self.policy,
            )

    def test_snapshot_rejects_falsified_assessment(self) -> None:
        document = copy.deepcopy(load_document(ROOT / "examples/observability/context-main-warn.yaml"))
        document["assessment"]["level"] = "ok"
        with self.assertRaises(ContractError):
            ContextSnapshot.from_mapping(document)

    def test_next_atomic_cost_protects_closeout_reserve(self) -> None:
        rollover = ContextSnapshot.create(
            snapshot_id="CTX-AWU-ROLLOVER",
            captured_at="2026-08-13T00:00:00Z",
            scope="main",
            measurement_source="runtime",
            metrics=self.zero_metrics,
            unknown_metrics=(),
            handoff_ready=None,
            context_budget=ContextBudgetEstimate(
                "estimated", "tokens", 4000, 3000, 1000, 500
            ),
            policy=self.policy,
        )
        blocked = ContextSnapshot.create(
            snapshot_id="CTX-CLOSEOUT-BLOCK",
            captured_at="2026-08-13T00:00:00Z",
            scope="main",
            measurement_source="runtime",
            metrics=self.zero_metrics,
            unknown_metrics=(),
            handoff_ready=None,
            context_budget=ContextBudgetEstimate(
                "estimated", "tokens", 1000, 0, 800, 500
            ),
            policy=self.policy,
        )
        self.assertEqual("rollover", rollover.assessment.level)
        self.assertIn("CTX-NEXT-AWU-UNSAFE", rollover.assessment.triggered_rules)
        self.assertEqual("block", blocked.assessment.level)
        self.assertIn("CTX-CLOSEOUT-RESERVE-INSUFFICIENT", blocked.assessment.triggered_rules)

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
            self.assertEqual("active", parsed.continuity_status)
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

    def test_checkpoint_publish_failure_leaves_no_partial_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "demo"
            self.assertEqual(0, run_cli(["init", str(project), "--project-id", "demo"])[0])
            state = project / "checkpoints" / "MS-FAIL.yaml"
            arguments = [
                "context", "checkpoint",
                "--id", "MS-FAIL",
                "--protocol", str(project / "project-protocol.yaml"),
                "--root", str(project),
                "--next-action", "Retry checkpoint publication.",
                "--created-at", "2026-08-13T00:01:00Z",
                "--output", str(state),
            ]
            with mock.patch("research_workbench.cli.os.link", side_effect=OSError("injected")):
                code, output = run_cli(arguments)

            self.assertEqual(2, code)
            self.assertIn("injected", output)
            self.assertFalse(state.exists())
            self.assertEqual([], list(state.parent.glob(f".{state.name}.*.tmp")))

    def test_explicit_git_capture_fails_closed_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "demo"
            self.assertEqual(0, run_cli(["init", str(project), "--project-id", "demo"])[0])
            state = project / "checkpoints" / "MS-GIT.yaml"
            code, output = run_cli(
                [
                    "context", "checkpoint",
                    "--id", "MS-GIT",
                    "--protocol", str(project / "project-protocol.yaml"),
                    "--root", str(project),
                    "--capture-git-head",
                    "--next-action", "Create a committed baseline.",
                    "--output", str(state),
                ]
            )
            self.assertEqual(2, code)
            self.assertIn("cannot capture Git HEAD", output)
            self.assertFalse(state.exists())

    def test_tampered_checkpoint_digest_is_rejected(self) -> None:
        document = copy.deepcopy(load_document(ROOT / "examples/main-state.yaml"))
        document["next_actions"] = ["Silent goal replacement"]
        with self.assertRaises(ContractError):
            MainStatePacket.from_mapping(document)

    def test_main_state_rejects_duplicate_machine_reference_paths(self) -> None:
        document = copy.deepcopy(load_document(ROOT / "examples/main-state.yaml"))
        document["machine_state_refs"].append(copy.deepcopy(document["machine_state_refs"][0]))
        document["checkpoint_digest"] = checkpoint_digest(document)
        with self.assertRaises(ContractError):
            MainStatePacket.from_mapping(document)

    def test_resume_check_rejects_git_head_conflict(self) -> None:
        document = copy.deepcopy(load_document(ROOT / "examples/main-state.yaml"))
        document["git_head"] = "0" * 40
        document["checkpoint_digest"] = checkpoint_digest(document)
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.yaml"
            state.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
            code, output = run_cli(
                [
                    "context", "resume-check", str(state),
                    "--protocol", str(ROOT / "examples/project-protocol.yaml"),
                    "--root", str(ROOT),
                ]
            )
        self.assertEqual(1, code)
        self.assertIn("RESUME-CONFLICT-GIT", output)

    def test_safe_pause_fixture_is_file_recoverable(self) -> None:
        state = ROOT / "examples/continuity/main-state-safe-pause.yaml"
        parsed = MainStatePacket.from_mapping(load_document(state))
        self.assertEqual("safe-paused", parsed.continuity_status)
        code, output = run_cli(
            [
                "context", "resume-check", str(state),
                "--protocol", str(ROOT / "examples/project-protocol.yaml"),
                "--root", str(ROOT),
            ]
        )
        self.assertEqual(0, code, output)
        self.assertIn("no blocking", output)


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
        self.assertEqual([], [risk for risk in risks if risk.level == "block"])
        self.assertIn("HANDOFF-SEMANTIC-UNREVIEWED", {risk.code for risk in risks})

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

    def test_safe_pause_receipt_does_not_fabricate_completion(self) -> None:
        receipt_path = ROOT / "examples/continuity/execution-safe-pause.yaml"
        receipt = ExecutionReceipt.from_mapping(load_document(receipt_path))
        risks = check_execution_receipt(
            receipt,
            self.protocol,
            root=ROOT,
            receipt_ref="examples/continuity/execution-safe-pause.yaml",
        )
        self.assertEqual("safe-paused", receipt.status)
        self.assertEqual([], [risk for risk in risks if risk.level == "block"])
        self.assertNotIn("RECEIPT-MACHINE-VALIDATION-MISSING", {risk.code for risk in risks})

    def test_failed_machine_report_overrides_completed_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            for relative in (
                "examples/project-protocol.yaml",
                "registry/agents/evidence-scout.yaml",
                "examples/vertical-slice/evidence-assignment.yaml",
            ):
                target = project / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            output = project / "work/output.txt"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("bounded output\n", encoding="utf-8")
            checker = project / "checks/checker.py"
            checker.parent.mkdir(parents=True, exist_ok=True)
            checker.write_text("raise SystemExit(1)\n", encoding="utf-8")
            report = {
                "schema_version": "0.1.0",
                "report_id": "CHK-FAILED-001",
                "checker": {
                    "checker_id": "fixture-checker",
                    "version": "0.1.0",
                    "source_ref": {"path": "checks/checker.py", "sha256": hash_file(checker)},
                },
                "subject_refs": [
                    {"path": "work/output.txt", "sha256": hash_file(output)}
                ],
                "status": "fail",
                "checks": [
                    {"code": "FIXTURE-FAIL", "status": "fail", "detail": "machine exit code was 1"}
                ],
                "scope": "failure-injection",
                "limitations": [],
            }
            report_path = project / "checks/report.yaml"
            report_path.write_text(yaml.safe_dump(report, sort_keys=False), encoding="utf-8")
            attempt = {
                "schema_version": "0.1.0",
                "task_id": "EVID-001",
                "task_revision": 1,
                "attempt_id": "A-FAILED-001",
                "status": "completed",
                "started_at": "2026-08-13T00:00:00Z",
                "finished_at": "2026-08-13T00:01:00Z",
                "trigger_reason": "failure injection",
                "input_lock": [],
                "skill_lock": ["literature-evidence-extraction@0.1.0"],
                "skill_assignment_ref": "examples/vertical-slice/evidence-assignment.yaml",
                "execution_receipt_ref": "receipts/receipt.yaml",
                "artifact_refs": ["work/output.txt"],
            }
            attempt_path = project / "attempts/attempt.yaml"
            attempt_path.parent.mkdir(parents=True, exist_ok=True)
            attempt_path.write_text(yaml.safe_dump(attempt, sort_keys=False), encoding="utf-8")
            receipt_document = {
                "schema_version": "0.1.0",
                "receipt_id": "XR-FAILED-001",
                "execution_kind": "local-tool",
                "attempt_ref": "attempts/attempt.yaml",
                "task_id": "EVID-001",
                "task_revision": 1,
                "agent_profile_ref": "registry/agents/evidence-scout.yaml",
                "skill_assignment_ref": "examples/vertical-slice/evidence-assignment.yaml",
                "started_at": "2026-08-13T00:00:00Z",
                "finished_at": "2026-08-13T00:01:00Z",
                "status": "completed",
                "completion_claim": "contract-satisfied",
                "runtime": {"name": "fixture", "version": "1", "adapter_version": "0.1.0"},
                "model_usage_status": "not-applicable",
                "model_usage": [],
                "coordination": {
                    "delegated_attempts": 0,
                    "handoff_count": 0,
                    "review_rounds": 0,
                    "max_parallel_observed": 0,
                },
                "trace": {
                    "mode": "disabled",
                    "external": False,
                    "sensitive_data_detected": False,
                    "redactions_applied": 0,
                },
                "output_refs": ["work/output.txt"],
                "validation_refs": ["checks/report.yaml"],
                "limitations": [],
            }
            receipt = ExecutionReceipt.from_mapping(receipt_document)
            protocol = ProjectProtocol.from_mapping(
                load_document(project / "examples/project-protocol.yaml")
            )
            codes = {
                risk.code
                for risk in check_execution_receipt(
                    receipt,
                    protocol,
                    root=project,
                    receipt_ref="receipts/receipt.yaml",
                )
            }
            receipt_document.pop("completion_claim")
            execution_only_codes = {
                risk.code
                for risk in check_execution_receipt(
                    ExecutionReceipt.from_mapping(receipt_document),
                    protocol,
                    root=project,
                    receipt_ref="receipts/receipt.yaml",
                )
            }
        self.assertIn("RECEIPT-VALIDATION-FAILED", codes)
        self.assertNotIn("RECEIPT-VALIDATION-FAILED", execution_only_codes)

    def test_contract_satisfied_claim_requires_completed_lifecycle(self) -> None:
        document = copy.deepcopy(load_document(self.receipt_path))
        document["status"] = "safe-paused"
        with self.assertRaises(ContractError):
            ExecutionReceipt.from_mapping(document)

    def test_malformed_referenced_documents_emit_structured_block(self) -> None:
        receipt = ExecutionReceipt.from_mapping(load_document(self.receipt_path))
        references = {
            "attempt_ref": receipt.attempt_ref,
            "skill_assignment_ref": receipt.skill_assignment_ref,
            "agent_profile_ref": receipt.agent_profile_ref,
            "context_snapshot_ref": str(receipt.context_snapshot_ref),
        }
        for field, relative in references.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(yaml.safe_dump({"unexpected": "shape"}), encoding="utf-8")
                risks = check_execution_receipt(receipt, self.protocol, root=directory)
                invalid = [risk for risk in risks if risk.code == "RECEIPT-REF-INVALID"]
                self.assertEqual(1, len(invalid))
                self.assertEqual("block", invalid[0].level)
                self.assertIn(relative, invalid[0].message)

    def test_malformed_handoff_output_emits_structured_block(self) -> None:
        document = copy.deepcopy(load_document(self.receipt_path))
        document["output_refs"] = ["work/handoff.yaml"]
        document["validation_refs"] = []
        document["completion_claim"] = "execution-only"
        receipt = ExecutionReceipt.from_mapping(document)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "work/handoff.yaml"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                yaml.safe_dump({"result": {"summary": "partial"}, "attempt_id": "A-1"}),
                encoding="utf-8",
            )
            risks = check_execution_receipt(receipt, self.protocol, root=directory)
        invalid = [risk for risk in risks if risk.code == "RECEIPT-REF-INVALID"]
        self.assertEqual(1, len(invalid))
        self.assertIn("work/handoff.yaml", invalid[0].message)

    def test_assess_cli_reports_invalid_reference_as_block_not_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            shutil.copy2(ROOT / "examples/project-protocol.yaml", project / "protocol.yaml")
            receipt_path = project / "receipts/receipt.yaml"
            receipt_path.parent.mkdir(parents=True)
            shutil.copy2(self.receipt_path, receipt_path)
            attempt_path = project / "examples/attempt-evidence.yaml"
            attempt_path.parent.mkdir(parents=True)
            attempt_path.write_text(yaml.safe_dump({"unexpected": "shape"}), encoding="utf-8")
            code, output = run_cli(
                [
                    "execution",
                    "assess",
                    str(receipt_path),
                    "--protocol",
                    str(project / "protocol.yaml"),
                    "--root",
                    str(project),
                ]
            )
        self.assertEqual(1, code)
        self.assertIn("RECEIPT-REF-INVALID", output)


if __name__ == "__main__":
    unittest.main()
