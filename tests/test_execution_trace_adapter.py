from __future__ import annotations

import copy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.io import load_document
from research_workbench.cli import main
from research_workbench.context import checkpoint_digest
from research_workbench.execution import (
    COMPLETION_MANIFEST_FILENAME,
    finalize_execution_archive,
    prepare_recovery_attempt,
    verify_execution_archive,
)
from research_workbench.observability import ExecutionReceipt, check_execution_receipt
from research_workbench.observability.trace import AgentTraceRecorder
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import AttemptRecord

ROOT = Path(__file__).resolve().parents[1]


class ExecutionTraceLinkTests(unittest.TestCase):
    def build_project(self, root: Path) -> tuple[Path, Path, dict, dict]:
        for relative in (
            "examples/project-protocol.yaml",
            "registry/agents/evidence-scout.yaml",
            "examples/vertical-slice/evidence-assignment.yaml",
        ):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)

        output = root / "work/output.txt"
        output.parent.mkdir(parents=True)
        output.write_text("bounded output\n", encoding="utf-8")

        recorder = AgentTraceRecorder(
            root / "traces/AT-TRACE",
            task_id="EVID-001",
            task_revision=1,
            attempt_id="AT-TRACE",
            task_snapshot={"task_id": "EVID-001", "revision": 1},
            accountable_owner="Huang Yi",
            actor_id="runtime-AT-TRACE",
            runtime_identity="model-api-test",
            provider="fake",
            read_allowlist=("examples/**",),
            write_scope=("work/**",),
            tool_allowlist=(),
        )
        recorder.record_attempt_status("completed", reason="fixture execution completed")
        trace_ref = recorder.seal()
        trace_ref = {
            "path": "traces/AT-TRACE/INDEX.yaml",
            "sha256": trace_ref["sha256"],
        }

        attempt = {
            "schema_version": "0.1.0",
            "task_id": "EVID-001",
            "task_revision": 1,
            "attempt_id": "AT-TRACE",
            "status": "completed",
            "started_at": "2026-08-21T00:00:00Z",
            "finished_at": "2026-08-21T00:01:00Z",
            "trigger_reason": "execution trace adapter fixture",
            "input_lock": [],
            "skill_lock": ["literature-evidence-extraction@0.1.0"],
            "skill_assignment_ref": "examples/vertical-slice/evidence-assignment.yaml",
            "trace_ref": trace_ref,
            "execution_receipt_ref": "receipts/receipt.yaml",
            "artifact_refs": ["work/output.txt"],
        }
        attempt_path = root / "attempts/attempt.yaml"
        attempt_path.parent.mkdir(parents=True)
        attempt_path.write_text(yaml.safe_dump(attempt, sort_keys=False), encoding="utf-8")

        receipt = {
            "schema_version": "0.1.0",
            "receipt_id": "XR-TRACE-001",
            "execution_kind": "model-api",
            "attempt_ref": "attempts/attempt.yaml",
            "task_id": "EVID-001",
            "task_revision": 1,
            "agent_profile_ref": "registry/agents/evidence-scout.yaml",
            "skill_assignment_ref": "examples/vertical-slice/evidence-assignment.yaml",
            "trace_ref": trace_ref,
            "started_at": "2026-08-21T00:00:00Z",
            "finished_at": "2026-08-21T00:01:00Z",
            "status": "completed",
            "runtime": {
                "name": "isolated-api-session",
                "version": "0.1.0",
                "adapter_version": "0.1.0",
            },
            "model_usage_status": "measured",
            "model_usage": [
                {
                    "provider": "fake",
                    "model": "worker-model",
                    "requests": 1,
                    "input_tokens": 5,
                    "output_tokens": 2,
                }
            ],
            "coordination": {
                "delegated_attempts": 0,
                "handoff_count": 0,
                "review_rounds": 0,
                "max_parallel_observed": 0,
            },
            "trace": {
                "mode": "redacted",
                "external": False,
                "sensitive_data_detected": False,
                "redactions_applied": 0,
            },
            "output_refs": ["work/output.txt"],
            "validation_refs": [],
            "limitations": [],
        }
        receipt_path = root / "receipts/receipt.yaml"
        receipt_path.parent.mkdir(parents=True)
        receipt_path.write_text(yaml.safe_dump(receipt, sort_keys=False), encoding="utf-8")
        return attempt_path, receipt_path, attempt, receipt

    def assess(self, root: Path, document: dict):
        receipt = ExecutionReceipt.from_mapping(document)
        protocol = ProjectProtocol.from_mapping(
            load_document(root / "examples/project-protocol.yaml")
        )
        return check_execution_receipt(
            receipt,
            protocol,
            root=root,
            receipt_ref="receipts/receipt.yaml",
        )

    def test_legacy_attempt_and_receipt_without_trace_remain_readable(self) -> None:
        attempt = AttemptRecord.from_mapping(load_document(ROOT / "examples/attempt-evidence.yaml"))
        receipt = ExecutionReceipt.from_mapping(
            load_document(ROOT / "examples/observability/execution-evidence-contract.yaml")
        )
        self.assertIsNone(attempt.trace_ref)
        self.assertIsNone(receipt.trace_ref)

    def test_historical_model_api_receipt_without_trace_remains_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt_path, _, attempt, receipt = self.build_project(root)
            attempt.pop("trace_ref")
            attempt_path.write_text(yaml.safe_dump(attempt, sort_keys=False), encoding="utf-8")
            receipt.pop("trace_ref")
            risks = self.assess(root, receipt)
        self.assertEqual([], risks)

    def test_valid_trace_link_replays_from_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, _, _, receipt = self.build_project(root)
            risks = self.assess(root, receipt)
        self.assertEqual([], [risk for risk in risks if risk.level == "block"])
        self.assertIn("TRACE-VALID", {risk.code for risk in risks})

    def test_attempt_receipt_trace_mismatch_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt_path, _, attempt, receipt = self.build_project(root)
            attempt["trace_ref"] = {
                "path": "traces/other/INDEX.yaml",
                "sha256": "0" * 64,
            }
            attempt_path.write_text(yaml.safe_dump(attempt, sort_keys=False), encoding="utf-8")
            codes = {risk.code for risk in self.assess(root, receipt)}
        self.assertIn("RECEIPT-TRACE-MISMATCH", codes)

    def test_trace_identity_and_status_drift_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt_path, _, attempt, receipt = self.build_project(root)
            other = AgentTraceRecorder(
                root / "traces/OTHER",
                task_id="OTHER",
                task_revision=1,
                attempt_id="AT-OTHER",
                task_snapshot={"task_id": "OTHER", "revision": 1},
                accountable_owner="Huang Yi",
                actor_id="runtime-other",
                runtime_identity="identity-drift-fixture",
                provider="fake",
                read_allowlist=(),
                write_scope=(),
                tool_allowlist=(),
            )
            other.seal("safe-paused")
            index_path = root / "traces/OTHER/INDEX.yaml"
            new_ref = {"path": "traces/OTHER/INDEX.yaml", "sha256": hash_file(index_path)}
            receipt["trace_ref"] = new_ref
            attempt["trace_ref"] = new_ref
            attempt_path.write_text(yaml.safe_dump(attempt, sort_keys=False), encoding="utf-8")
            codes = {risk.code for risk in self.assess(root, receipt)}
        self.assertIn("RECEIPT-TRACE-IDENTITY", codes)
        self.assertIn("RECEIPT-TRACE-STATUS", codes)

    def test_trace_link_shape_is_optional_but_strict_when_present(self) -> None:
        legacy = load_document(ROOT / "examples/observability/execution-evidence-contract.yaml")
        malformed = copy.deepcopy(legacy)
        malformed["trace_ref"] = "INDEX.yaml"
        with self.assertRaisesRegex(Exception, "trace_ref"):
            ExecutionReceipt.from_mapping(malformed)


class ExecutionArchiveCloseoutTests(unittest.TestCase):
    def build_project(self, root: Path):
        return ExecutionTraceLinkTests().build_project(root)

    def finalize_fixture(self, root: Path):
        _, _, attempt, receipt = self.build_project(root)
        return finalize_execution_archive(
            root=root,
            attempt_dir="traces/AT-TRACE",
            attempt_document=attempt,
            receipt_document=receipt,
            protocol="examples/project-protocol.yaml",
        )

    def test_marker_last_closeout_and_file_only_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            published: list[str] = []
            from research_workbench.execution import archive

            original = archive._publish_exclusive

            def recording_publish(path: Path, payload: bytes) -> None:
                published.append(path.name)
                original(path, payload)

            with patch.object(archive, "_publish_exclusive", side_effect=recording_publish):
                result = self.finalize_fixture(root)
            self.assertFalse(result.blocked, result.risks)
            self.assertIsNotNone(result.completion_manifest)
            self.assertEqual(COMPLETION_MANIFEST_FILENAME, published[-1])
            first = verify_execution_archive(
                "traces/AT-TRACE",
                root=root,
                protocol="examples/project-protocol.yaml",
            )
            second = verify_execution_archive(
                "traces/AT-TRACE",
                root=root,
                protocol="examples/project-protocol.yaml",
            )
            self.assertEqual(first, second)
            self.assertEqual([], [risk for risk in first if risk.level == "block"])
            with patch("builtins.print"):
                self.assertEqual(
                    0,
                    main(
                        [
                            "execute",
                            "verify",
                            "--attempt",
                            "traces/AT-TRACE",
                            "--root",
                            str(root),
                            "--protocol",
                            "examples/project-protocol.yaml",
                        ]
                    ),
                )

    def test_marker_publication_failure_leaves_uncommitted_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            from research_workbench.execution import archive

            original = archive._publish_exclusive

            def fail_marker(path: Path, payload: bytes) -> None:
                if path.name == COMPLETION_MANIFEST_FILENAME:
                    raise OSError("injected marker publication failure")
                original(path, payload)

            with patch.object(archive, "_publish_exclusive", side_effect=fail_marker):
                with self.assertRaises(OSError):
                    self.finalize_fixture(root)
            marker = root / "traces/AT-TRACE" / COMPLETION_MANIFEST_FILENAME
            self.assertFalse(marker.exists())
            codes = {
                risk.code
                for risk in verify_execution_archive(
                    "traces/AT-TRACE",
                    root=root,
                    protocol="examples/project-protocol.yaml",
                )
            }
            self.assertIn("EXEC-COMPLETION-MARKER-MISSING", codes)

    def test_missing_trace_blocks_before_closeout_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt_dir = root / "work/missing-trace"
            attempt_dir.mkdir(parents=True)
            result = finalize_execution_archive(
                root=root,
                attempt_dir=attempt_dir,
                attempt_document={"attempt_id": "A"},
                receipt_document={},
                protocol="protocol.yaml",
            )
            self.assertTrue(result.blocked)
            self.assertIn("TRACE-INDEX-MISSING", {risk.code for risk in result.risks})
            self.assertEqual([], list(attempt_dir.iterdir()))

    def test_transcript_tamper_and_unrecorded_file_are_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.finalize_fixture(root)
            self.assertFalse(result.blocked, result.risks)
            attempt_dir = root / "traces/AT-TRACE"
            (attempt_dir / "session-transcript.json").write_text(
                '{"turns": ["fabricated"]}\n', encoding="utf-8"
            )
            (attempt_dir / "late-file.txt").write_text("not committed\n", encoding="utf-8")
            codes = {
                risk.code
                for risk in verify_execution_archive(
                    attempt_dir,
                    root=root,
                    protocol="examples/project-protocol.yaml",
                )
            }
            self.assertIn("EXEC-TRANSCRIPT-DRIFT", codes)
            self.assertIn("EXEC-COMPLETION-MARKER-INVALID", codes)

    def test_frozen_attempt_cannot_be_republished(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.finalize_fixture(root)
            self.assertFalse(result.blocked, result.risks)
            with self.assertRaises(FileExistsError):
                self.finalize_fixture(root)


class ExecutionRecoveryTests(unittest.TestCase):
    def build_safe_pause_archive(self, root: Path) -> tuple[Path, Path]:
        for relative in (
            "examples/project-protocol.yaml",
            "registry/agents/simulation-auditor.yaml",
            "examples/vertical-slice/simulation-assignment.yaml",
            "examples/fixtures/run-manifest.txt",
            "tests/fixtures/valid/simulation-vv-report.yaml",
            "examples/continuity/context-task-safe-pause.yaml",
        ):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)

        attempt_dir = root / "work/SIM-001/AT-RECOVERY-SOURCE"
        recorder = AgentTraceRecorder(
            attempt_dir,
            task_id="SIM-001",
            task_revision=1,
            attempt_id="AT-RECOVERY-SOURCE",
            task_snapshot={"task_id": "SIM-001", "revision": 1},
            accountable_owner="Huang Yi",
            actor_id="runtime-recovery-source",
            runtime_identity="safe-pause-recovery-fixture",
            provider="fake",
            read_allowlist=("examples/**",),
            write_scope=("work/**",),
            tool_allowlist=(),
        )
        recorder.record_attempt_status("safe-paused", reason="budget boundary")
        recorder.seal()

        receipt_relative = "work/SIM-001/AT-RECOVERY-SOURCE/execution-receipt.yaml"
        handoff_relative = "work/SIM-001/AT-RECOVERY-SOURCE/handoff.yaml"
        handoff = copy.deepcopy(
            load_document(ROOT / "examples/continuity/handoff-safe-pause.yaml")
        )
        handoff["attempt_id"] = "AT-RECOVERY-SOURCE"
        handoff["execution_receipt_ref"] = receipt_relative
        handoff_path = attempt_dir / "handoff.yaml"
        handoff_path.write_text(yaml.safe_dump(handoff, sort_keys=False), encoding="utf-8")

        attempt = copy.deepcopy(
            load_document(ROOT / "examples/continuity/attempt-safe-pause.yaml")
        )
        attempt["attempt_id"] = "AT-RECOVERY-SOURCE"
        attempt["handoff_ref"] = handoff_relative
        receipt = copy.deepcopy(
            load_document(ROOT / "examples/continuity/execution-safe-pause.yaml")
        )
        receipt.update(
            {
                "execution_kind": "model-api",
                "receipt_id": "XR-RECOVERY-SOURCE",
                "model_usage_status": "unavailable",
                "model_usage": [],
                "runtime": {
                    "name": "isolated-api-session",
                    "version": "0.1.0",
                    "adapter_version": "0.1.0",
                },
                "trace": {
                    "mode": "redacted",
                    "external": False,
                    "sensitive_data_detected": False,
                    "redactions_applied": 0,
                },
                "output_refs": [
                    "tests/fixtures/valid/simulation-vv-report.yaml",
                    handoff_relative,
                ],
            }
        )
        result = finalize_execution_archive(
            root=root,
            attempt_dir=attempt_dir,
            attempt_document=attempt,
            receipt_document=receipt,
            protocol="examples/project-protocol.yaml",
        )
        self.assertFalse(result.blocked, result.risks)

        attempt_path = attempt_dir / "attempt.yaml"
        receipt_path = attempt_dir / "execution-receipt.yaml"
        trace_path = attempt_dir / "INDEX.yaml"
        state = copy.deepcopy(
            load_document(ROOT / "examples/continuity/main-state-safe-pause.yaml")
        )
        state.pop("context_snapshot_ref", None)
        state["active_tasks"] = [
            {
                "task_id": "SIM-001",
                "status": "safe-paused",
                "expected_handoff": handoff_relative,
            }
        ]
        state["recent_handoffs"] = [
            {"ref": handoff_relative, "disposition": "paused-recoverable"}
        ]
        state["machine_state_refs"] = [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hash_file(path),
            }
            for path in (attempt_path, receipt_path, handoff_path, trace_path)
        ]
        state["checkpoint_id"] = "MS-RECOVERY-SOURCE"
        state["checkpoint_digest"] = checkpoint_digest(state)
        state_path = root / "state/main-state.yaml"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
        return attempt_dir, state_path

    def test_new_process_recovers_only_to_a_distinct_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt_dir, state_path = self.build_safe_pause_archive(root)
            target = root / "work/SIM-001/AT-RECOVERY-TARGET"
            result = prepare_recovery_attempt(
                root=root,
                previous_attempt_dir=attempt_dir,
                main_state=state_path,
                protocol="examples/project-protocol.yaml",
                new_attempt_id="AT-RECOVERY-TARGET",
                new_attempt_dir=target,
            )
            self.assertFalse(result.blocked, result.risks)
            self.assertIsNotNone(result.seed)
            self.assertFalse(target.exists(), "preflight must not create the new Attempt")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "research_workbench",
                    "execute",
                    "recovery-check",
                    "--previous-attempt",
                    str(attempt_dir),
                    "--main-state",
                    str(state_path),
                    "--new-attempt-id",
                    "AT-RECOVERY-NEW-PROCESS",
                    "--new-attempt-dir",
                    str(root / "work/SIM-001/AT-RECOVERY-NEW-PROCESS"),
                    "--protocol",
                    "examples/project-protocol.yaml",
                    "--root",
                    str(root),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            self.assertIn("RECOVERY-READY", completed.stdout)

    def test_recovery_rejects_attempt_reuse_and_tampered_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt_dir, state_path = self.build_safe_pause_archive(root)
            reused = prepare_recovery_attempt(
                root=root,
                previous_attempt_dir=attempt_dir,
                main_state=state_path,
                protocol="examples/project-protocol.yaml",
                new_attempt_id="AT-RECOVERY-SOURCE",
                new_attempt_dir=attempt_dir,
            )
            self.assertIn("RECOVERY-ATTEMPT-REUSE", {risk.code for risk in reused.risks})
            (attempt_dir / "events.jsonl").write_text("tampered\n", encoding="utf-8")
            tampered = prepare_recovery_attempt(
                root=root,
                previous_attempt_dir=attempt_dir,
                main_state=state_path,
                protocol="examples/project-protocol.yaml",
                new_attempt_id="AT-NEW",
                new_attempt_dir=root / "work/SIM-001/AT-NEW",
            )
            self.assertIn("RECOVERY-PREVIOUS-INVALID", {risk.code for risk in tampered.risks})

    def test_recovery_reports_malformed_main_state_as_structured_risk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt_dir, state_path = self.build_safe_pause_archive(root)
            state_path.write_text("active_tasks: [\n", encoding="utf-8")
            result = prepare_recovery_attempt(
                root=root,
                previous_attempt_dir=attempt_dir,
                main_state=state_path,
                protocol="examples/project-protocol.yaml",
                new_attempt_id="AT-RECOVERY-MALFORMED-STATE",
                new_attempt_dir=root / "work/SIM-001/AT-RECOVERY-MALFORMED-STATE",
            )
            codes = {risk.code for risk in result.risks}
            self.assertTrue(result.blocked)
            self.assertIn("RECOVERY-SOURCE-INVALID", codes)
            self.assertIn("RECOVERY-STATE-MISSING", codes)


if __name__ == "__main__":
    unittest.main()
