from __future__ import annotations

import copy
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.cli import _document_reference_risks
from research_workbench.contracts import ContractError
from research_workbench.io import load_document
from research_workbench.observability import ExecutionReceipt, check_execution_receipt
from research_workbench.protocol import ProjectProtocol
from research_workbench.validation.schemas import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]
TRACE_FIXTURE = ROOT / "tests/fixtures/trace/valid/h1-complete"
TRACE_RELATIVE = Path("archive/TRACE-001/A-001/INDEX.yaml")


class ExecutionReceiptTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = ProjectProtocol.from_mapping(
            load_document(ROOT / "examples/project-protocol.yaml")
        )

    @staticmethod
    def _copy_project(directory: str) -> Path:
        project = Path(directory) / "project"
        shutil.copytree(TRACE_FIXTURE, project)
        return project

    @staticmethod
    def _trace_ref(project: Path, *, sha256: str | None = None) -> dict[str, str]:
        return {
            "path": TRACE_RELATIVE.as_posix(),
            "sha256": sha256 or hash_file(project / TRACE_RELATIVE),
        }

    @classmethod
    def _documents(
        cls,
        project: Path,
        *,
        attempt_trace_ref: dict[str, str] | None,
        receipt_trace_ref: dict[str, str] | None,
    ) -> tuple[dict, dict]:
        attempt = {
            "schema_version": "0.1.0",
            "task_id": "TRACE-001",
            "task_revision": 1,
            "attempt_id": "A-001",
            "status": "completed",
            "started_at": "2026-08-16T00:00:00Z",
            "finished_at": "2026-08-16T00:00:10Z",
            "trigger_reason": "receipt Trace compatibility test",
            "input_lock": [],
            "skill_lock": [],
            "skill_assignment_ref": "support/assignment.yaml",
            "execution_receipt_ref": "receipts/receipt.yaml",
            "artifact_refs": [],
        }
        if attempt_trace_ref is not None:
            attempt["agent_trace_index_ref"] = copy.deepcopy(attempt_trace_ref)
        receipt = {
            "schema_version": "0.1.0",
            "receipt_id": "XR-TRACE-001",
            "execution_kind": "model-api",
            "attempt_ref": "attempts/attempt.yaml",
            "task_id": "TRACE-001",
            "task_revision": 1,
            "agent_profile_ref": "support/profile.yaml",
            "skill_assignment_ref": "support/assignment.yaml",
            "model_assignment_ref": {
                "path": "support/model-assignment.yaml",
                "sha256": "0" * 64,
            },
            "execution_contract": "fixture-h1@0.1.0",
            "handoff_tier": "H1",
            "handoff_tier_reasons": ["fixture-model-api"],
            "started_at": "2026-08-16T00:00:00Z",
            "finished_at": "2026-08-16T00:00:10Z",
            "status": "completed",
            "model_binding": {
                "provider_adapter_id": "fixture-local",
                "requested_model": "fixture-model",
            },
            "runtime": {
                "name": "fixture-runtime",
                "version": "1",
                "adapter_version": "0.1.0",
            },
            "model_usage_status": "unavailable",
            "model_usage": [],
            "coordination": {
                "delegated_attempts": 0,
                "handoff_count": 0,
                "review_rounds": 0,
                "max_parallel_observed": 0,
            },
            "trace": {
                "mode": "minimal",
                "external": False,
                "sensitive_data_detected": False,
                "redactions_applied": 0,
            },
            "output_refs": [],
            "validation_refs": [],
            "limitations": [],
        }
        if receipt_trace_ref is not None:
            receipt["agent_trace_index_ref"] = copy.deepcopy(receipt_trace_ref)
        return attempt, receipt

    @staticmethod
    def _write_documents(project: Path, attempt: dict, receipt: dict) -> None:
        for relative, document in (
            ("attempts/attempt.yaml", attempt),
            ("receipts/receipt.yaml", receipt),
        ):
            path = project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

    def _risks(self, project: Path, receipt_document: dict):
        return check_execution_receipt(
            ExecutionReceipt.from_mapping(receipt_document),
            self.protocol,
            root=project,
            receipt_ref="receipts/receipt.yaml",
        )

    def test_schema_and_model_accept_optional_hash_bound_trace_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_project(directory)
            trace_ref = self._trace_ref(project)
            _attempt, receipt_document = self._documents(
                project,
                attempt_trace_ref=trace_ref,
                receipt_trace_ref=trace_ref,
            )

            self.assertEqual(
                SchemaCatalog().validate("execution_receipt", receipt_document),
                [],
            )
            receipt = ExecutionReceipt.from_mapping(receipt_document)
            self.assertEqual(receipt.agent_trace_index_ref.path, trace_ref["path"])
            self.assertEqual(receipt.agent_trace_index_ref.sha256, trace_ref["sha256"])

            receipt_document["agent_trace_index_ref"] = trace_ref["path"]
            self.assertTrue(
                SchemaCatalog().validate("execution_receipt", receipt_document)
            )
            with self.assertRaisesRegex(ContractError, "agent_trace_index_ref"):
                ExecutionReceipt.from_mapping(receipt_document)

    def test_legacy_receipt_without_trace_ref_remains_compatible(self) -> None:
        receipt = ExecutionReceipt.from_mapping(
            load_document(ROOT / "examples/observability/execution-evidence-contract.yaml")
        )
        risks = check_execution_receipt(
            receipt,
            self.protocol,
            root=ROOT,
            receipt_ref="examples/observability/execution-evidence-contract.yaml",
        )

        self.assertIsNone(receipt.agent_trace_index_ref)
        self.assertNotIn("RECEIPT-TRACE-REQUIRED", {risk.code for risk in risks})

    def test_new_model_api_receipt_requires_trace_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_project(directory)
            attempt, receipt = self._documents(
                project,
                attempt_trace_ref=None,
                receipt_trace_ref=None,
            )
            self._write_documents(project, attempt, receipt)

            codes = {risk.code for risk in self._risks(project, receipt)}
            self.assertIn("RECEIPT-TRACE-REQUIRED", codes)

    def test_matching_attempt_and_receipt_trace_pass_bundle_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_project(directory)
            trace_ref = self._trace_ref(project)
            attempt, receipt = self._documents(
                project,
                attempt_trace_ref=trace_ref,
                receipt_trace_ref=trace_ref,
            )
            self._write_documents(project, attempt, receipt)

            codes = {risk.code for risk in self._risks(project, receipt)}
            self.assertFalse(
                {
                    code
                    for code in codes
                    if code.startswith("TRACE-") or "TRACE" in code
                }
            )

    def test_attempt_receipt_trace_path_or_hash_mismatch_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_project(directory)
            trace_ref = self._trace_ref(project)
            stale_ref = self._trace_ref(project, sha256="0" * 64)
            attempt, receipt = self._documents(
                project,
                attempt_trace_ref=stale_ref,
                receipt_trace_ref=trace_ref,
            )
            self._write_documents(project, attempt, receipt)

            codes = {risk.code for risk in self._risks(project, receipt)}
            self.assertIn("RECEIPT-ATTEMPT-TRACE-MISMATCH", codes)
            self.assertIn("REF-HASH-MISMATCH", codes)

            attempt["agent_trace_index_ref"] = {
                "path": "archive/TRACE-001/A-001/OTHER-INDEX.yaml",
                "sha256": trace_ref["sha256"],
            }
            self._write_documents(project, attempt, receipt)
            path_codes = {risk.code for risk in self._risks(project, receipt)}
            self.assertIn("RECEIPT-ATTEMPT-TRACE-MISMATCH", path_codes)

    def test_live_trace_hash_drift_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_project(directory)
            stale_ref = self._trace_ref(project, sha256="0" * 64)
            attempt, receipt = self._documents(
                project,
                attempt_trace_ref=stale_ref,
                receipt_trace_ref=stale_ref,
            )
            self._write_documents(project, attempt, receipt)

            codes = {risk.code for risk in self._risks(project, receipt)}
            self.assertNotIn("RECEIPT-ATTEMPT-TRACE-MISMATCH", codes)
            self.assertIn("REF-HASH-MISMATCH", codes)

    def test_receipt_checker_runs_agent_trace_bundle_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_project(directory)
            trace_ref = self._trace_ref(project)
            attempt, receipt = self._documents(
                project,
                attempt_trace_ref=trace_ref,
                receipt_trace_ref=trace_ref,
            )
            self._write_documents(project, attempt, receipt)
            message_path = (
                project
                / "archive/TRACE-001/A-001/messages/"
                "0001-main-agent-to-trace-reviewer-assignment.md"
            )
            message_path.write_text(
                message_path.read_text(encoding="utf-8") + "drift\n",
                encoding="utf-8",
            )

            codes = {risk.code for risk in self._risks(project, receipt)}
            self.assertIn("TRACE-HASH-MISMATCH", codes)

    def test_cli_receipt_reference_walk_checks_trace_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_project(directory)
            stale_ref = self._trace_ref(project, sha256="0" * 64)
            attempt, receipt = self._documents(
                project,
                attempt_trace_ref=stale_ref,
                receipt_trace_ref=stale_ref,
            )
            self._write_documents(project, attempt, receipt)
            for relative in ("support/profile.yaml", "support/assignment.yaml"):
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture: true\n", encoding="utf-8")

            codes = {
                risk.code
                for risk in _document_reference_risks(receipt, project)
            }
            self.assertIn("REF-HASH-MISMATCH", codes)


if __name__ == "__main__":
    unittest.main()
