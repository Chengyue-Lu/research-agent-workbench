from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from research_workbench.contracts import ContractRisk, RiskLevel
from research_workbench.execution import archive as archive_module
from research_workbench.execution import recovery as recovery_module
from research_workbench.tasks import FileReference


class ExecutionArchiveHelperTests(unittest.TestCase):
    """Fast archive validator units; full replay stays in behavioral suites."""

    def test_payload_publication_deduplication_and_mapping_guards(self) -> None:
        duplicate = ContractRisk("DUP", RiskLevel.BLOCK, "same")
        self.assertEqual((duplicate,), archive_module._dedupe([duplicate, duplicate]))
        self.assertIn(b"key: value", archive_module._yaml_payload({"key": "value"}))
        self.assertEqual({"key": "value"}, json.loads(archive_module._json_payload({"key": "value"})))
        self.assertEqual(
            {"values": ["a", "b"]},
            archive_module._with_unique_path({"values": ["a"]}, field="values", relative="b"),
        )
        self.assertEqual(
            {"ref": {"path": "a", "sha256": "0" * 64}},
            archive_module._with_reference(
                {}, field="ref", reference={"path": "a", "sha256": "0" * 64}
            ),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "nested" / "value.bin"
            archive_module._publish_exclusive(target, b"value")
            self.assertEqual(b"value", target.read_bytes())
            with self.assertRaises(FileExistsError):
                archive_module._publish_exclusive(target, b"replacement")

            risks: list[ContractRisk] = []
            scalar = root / "scalar.yaml"
            scalar.write_text("[]\n", encoding="utf-8")
            self.assertIsNone(archive_module._load_mapping(scalar, "scalar", risks))
            self.assertEqual("EXEC-ARCHIVE-INVALID", risks[-1].code)
            broken = root / "broken.yaml"
            broken.write_text("not: [yaml", encoding="utf-8")
            self.assertIsNone(archive_module._load_mapping(broken, "broken", risks))

    def test_finalize_isolated_transaction_orders_marker_last(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attempt_dir = root / "attempts" / "A-1"
            attempt_dir.mkdir(parents=True)
            (attempt_dir / archive_module.TRACE_INDEX_FILENAME).write_text("{}\n", encoding="utf-8")
            protocol = root / "protocol.yaml"
            protocol.write_text("{}\n", encoding="utf-8")
            attempt = {"attempt_id": "A-1", "artifact_refs": []}
            receipt = {"status": "completed", "output_refs": []}
            parsed_receipt = SimpleNamespace(execution_kind="model-api", status="completed")
            with (
                mock.patch.object(
                    archive_module,
                    "validate_attempt_trace",
                    return_value=SimpleNamespace(risks=()),
                ),
                mock.patch.object(archive_module, "derive_session_transcript", return_value=()),
                mock.patch.object(archive_module.SchemaCatalog, "validate", return_value=[]),
                mock.patch.object(archive_module.AttemptRecord, "from_mapping", return_value=SimpleNamespace()),
                mock.patch.object(
                    archive_module.ExecutionReceipt, "from_mapping", return_value=parsed_receipt
                ),
                mock.patch.object(archive_module.ProjectProtocol, "from_mapping", return_value=SimpleNamespace()),
                mock.patch.object(archive_module, "check_execution_receipt", return_value=[]),
            ):
                result = archive_module.finalize_execution_archive(
                    root=root,
                    attempt_dir=attempt_dir,
                    attempt_document=attempt,
                    receipt_document=receipt,
                    protocol=protocol,
                )
            self.assertFalse(result.blocked)
            self.assertEqual(attempt_dir / archive_module.COMPLETION_MANIFEST_FILENAME, result.completion_manifest)
            self.assertTrue(result.completion_manifest.is_file())

            with self.assertRaises(FileExistsError):
                archive_module.finalize_execution_archive(
                    root=root,
                    attempt_dir=attempt_dir,
                    attempt_document=attempt,
                    receipt_document=receipt,
                    protocol=protocol,
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attempt_dir = root / "attempt"
            attempt_dir.mkdir()
            blocked = ContractRisk("TRACE-BLOCK", RiskLevel.BLOCK, "blocked")
            with mock.patch.object(
                archive_module,
                "validate_attempt_trace",
                return_value=SimpleNamespace(risks=(blocked, blocked)),
            ):
                result = archive_module.finalize_execution_archive(
                    root=root,
                    attempt_dir=attempt_dir,
                    attempt_document={},
                    receipt_document={},
                    protocol="missing.yaml",
                )
            self.assertTrue(result.blocked)
            self.assertEqual(1, len(result.risks))

    def test_verify_archive_validator_success_and_fail_closed_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root.parent / "outside-attempt"
            self.assertEqual(
                "EXEC-ARCHIVE-INVALID",
                archive_module.verify_execution_archive(outside, root=root, protocol="protocol.yaml")[0].code,
            )
            attempt_dir = root / "attempt"
            attempt_dir.mkdir()
            self.assertEqual(
                "EXEC-COMPLETION-MARKER-MISSING",
                archive_module.verify_execution_archive(
                    attempt_dir, root=root, protocol="protocol.yaml"
                )[0].code,
            )

            names = (
                archive_module.ATTEMPT_FILENAME,
                archive_module.RECEIPT_FILENAME,
                archive_module.TRANSCRIPT_FILENAME,
                archive_module.TRACE_INDEX_FILENAME,
            )
            for name in names:
                (attempt_dir / name).write_text(
                    "{}\n" if name != archive_module.TRANSCRIPT_FILENAME else json.dumps(
                        {
                            "schema_version": "0.1.0",
                            "source": "agent-trace-derived-view",
                            "attempt_id": "A-1",
                            "turns": [],
                        }
                    ),
                    encoding="utf-8",
                )
            marker_path = attempt_dir / archive_module.COMPLETION_MANIFEST_FILENAME
            marker_path.write_text("{}\n", encoding="utf-8")
            references = [
                FileReference(
                    (attempt_dir / name).relative_to(root).as_posix(),
                    "0" * 64,
                )
                for name in names
            ]
            marker = {
                "attempt_id": "A-1",
                "status": "completed",
                "files": [
                    {"path": reference.path, "sha256": reference.sha256}
                    for reference in references
                ],
            }
            attempt = SimpleNamespace(attempt_id="A-1")
            receipt = SimpleNamespace(status="completed")
            with (
                mock.patch.object(
                    archive_module,
                    "_load_mapping",
                    side_effect=lambda path, _label, _risks: (
                        marker
                        if path.name == archive_module.COMPLETION_MANIFEST_FILENAME
                        else {}
                    ),
                ),
                mock.patch.object(archive_module.SchemaCatalog, "validate", return_value=[]),
                mock.patch.object(
                    archive_module.FileReference,
                    "from_mapping",
                    side_effect=references,
                ),
                mock.patch.object(archive_module, "check_references", return_value=[]),
                mock.patch.object(archive_module, "_schema_risks", return_value=[]),
                mock.patch.object(archive_module.AttemptRecord, "from_mapping", return_value=attempt),
                mock.patch.object(archive_module.ExecutionReceipt, "from_mapping", return_value=receipt),
                mock.patch.object(
                    archive_module,
                    "validate_attempt_trace",
                    return_value=SimpleNamespace(risks=()),
                ),
                mock.patch.object(archive_module, "derive_session_transcript", return_value=[]),
            ):
                risks = archive_module.verify_execution_archive(
                    attempt_dir, root=root, protocol="missing.yaml"
                )
            self.assertIn("EXEC-ARCHIVE-INVALID", {risk.code for risk in risks})


class RecoveryHelperTests(unittest.TestCase):
    """Exercise recovery preflight decisions without archive replay."""

    def test_mapping_loader_and_blocked_archive_short_circuit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            risks: list[ContractRisk] = []
            scalar = root / "scalar.yaml"
            scalar.write_text("[]\n", encoding="utf-8")
            self.assertIsNone(recovery_module._load_mapping(scalar, "state", risks))
            self.assertEqual("RECOVERY-SOURCE-INVALID", risks[-1].code)
            blocked = ContractRisk("ARCHIVE", RiskLevel.BLOCK, "invalid")
            with mock.patch.object(
                recovery_module, "verify_execution_archive", return_value=(blocked,)
            ):
                result = recovery_module.prepare_recovery_attempt(
                    root=root,
                    previous_attempt_dir="old",
                    main_state="state.yaml",
                    protocol="protocol.yaml",
                    new_attempt_id="NEW",
                    new_attempt_dir="new",
                )
            self.assertTrue(result.blocked)
            self.assertIn("RECOVERY-PREVIOUS-INVALID", {risk.code for risk in result.risks})

    def test_valid_preflight_builds_a_distinct_seed_from_frozen_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = root / "old"
            old.mkdir()
            (old / recovery_module.ATTEMPT_FILENAME).write_text("{}\n", encoding="utf-8")
            handoff_path = root / "handoff.yaml"
            handoff_path.write_text("{}\n", encoding="utf-8")
            state_path = root / "state.yaml"
            state_path.write_text("{}\n", encoding="utf-8")
            trace_ref = FileReference("old/INDEX.yaml", "0" * 64)
            attempt = SimpleNamespace(
                status="safe-paused",
                handoff_ref="handoff.yaml",
                task_id="TASK",
                task_revision=1,
                attempt_id="OLD",
                input_lock=(),
                skill_lock=(),
                skill_assignment_ref=None,
                trace_ref=trace_ref,
            )
            handoff = SimpleNamespace(
                task_id="TASK",
                attempt_id="OLD",
                status="safe-paused",
                input_lock=(),
                skill_lock=(),
            )
            state = SimpleNamespace(
                machine_state_refs=(),
                active_tasks=(
                    SimpleNamespace(
                        task_id="TASK",
                        status="safe-paused",
                        expected_handoff="handoff.yaml",
                    ),
                ),
                recent_handoffs=(SimpleNamespace(ref="handoff.yaml"),),
                continuity_status="safe-paused",
            )
            with (
                mock.patch.object(recovery_module, "verify_execution_archive", return_value=()),
                mock.patch.object(recovery_module.AttemptRecord, "from_mapping", return_value=attempt),
                mock.patch.object(recovery_module.HandoffPacket, "from_mapping", return_value=handoff),
                mock.patch.object(recovery_module.MainStatePacket, "from_mapping", return_value=state),
                mock.patch.object(recovery_module.SchemaCatalog, "validate", return_value=[]),
                mock.patch.object(recovery_module, "check_references", return_value=[]),
            ):
                result = recovery_module.prepare_recovery_attempt(
                    root=root,
                    previous_attempt_dir=old,
                    main_state=state_path,
                    protocol="protocol.yaml",
                    new_attempt_id="NEW",
                    new_attempt_dir="new",
                )
            self.assertFalse(result.blocked)
            self.assertEqual("NEW", result.seed.new_attempt_id)
            self.assertEqual("RECOVERY-READY", result.risks[-1].code)


if __name__ == "__main__":
    unittest.main()
