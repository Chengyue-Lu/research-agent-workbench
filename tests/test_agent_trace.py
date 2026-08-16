from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.io import load_document
from research_workbench.validation.documents import Severity
from research_workbench.validation.schemas import SchemaCatalog
from research_workbench.validation.trace import validate_agent_trace


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/trace/valid/h1-complete"
INDEX_RELATIVE = Path("archive/TRACE-001/A-001/INDEX.yaml")
LEDGER_RELATIVE = Path("archive/TRACE-001/A-001/events.jsonl")


class AgentTraceSchemaTests(unittest.TestCase):
    def test_trace_schema_catalog_entries_compile(self) -> None:
        catalog = SchemaCatalog(ROOT / "schemas")
        self.assertTrue(
            {
                "agent_trace_envelope",
                "agent_trace_actors",
                "agent_trace_event",
                "agent_trace_index",
            }.issubset(catalog.document_kinds)
        )

    def test_event_variant_requires_content_hash_for_content_read(self) -> None:
        event = {
            "schema_version": "0.1.0",
            "event_id": "EVT-0001",
            "task_id": "TRACE-001",
            "task_revision": 1,
            "attempt_id": "A-001",
            "sequence": 1,
            "event_type": "content-read",
            "actor_id": "main-agent",
            "occurred_at": "2026-08-16T00:00:00Z",
            "payload": {
                "path": "TASK.yaml",
                "access": "content",
                "read_range": "full",
                "allowlist_basis": "TASK",
            },
        }
        errors = SchemaCatalog(ROOT / "schemas").validate("agent_trace_event", event)
        self.assertTrue(any("content_sha256" in error.message for error in errors))

    def test_partial_envelope_requires_capture_gap_event(self) -> None:
        envelope = {
            "schema_version": "0.1.0",
            "message_id": "MSG-0001",
            "task_id": "TRACE-001",
            "task_revision": 1,
            "attempt_id": "A-001",
            "sequence": 1,
            "kind": "assignment",
            "sender_actor_id": "main-agent",
            "receiver_actor_ids": ["trace-reviewer"],
            "accountable_owner": "路诚钺",
            "created_at": "2026-08-16T00:00:00Z",
            "content_sha256": "0" * 64,
            "attachment_refs": [],
            "redactions": [],
            "capture_status": "partial",
        }
        errors = SchemaCatalog(ROOT / "schemas").validate("agent_trace_envelope", envelope)
        self.assertTrue(any("capture_gap_event_id" in error.message for error in errors))


class AgentTraceValidationTests(unittest.TestCase):
    def _copy_fixture(self, directory: str) -> Path:
        project = Path(directory) / "project"
        shutil.copytree(FIXTURE, project)
        return project

    @staticmethod
    def _index(project: Path) -> dict:
        return copy.deepcopy(load_document(project / INDEX_RELATIVE))

    @staticmethod
    def _write_index(project: Path, index: dict) -> None:
        (project / INDEX_RELATIVE).write_text(
            yaml.safe_dump(index, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    @staticmethod
    def _events(project: Path) -> list[dict]:
        return [
            json.loads(line)
            for line in (project / LEDGER_RELATIVE).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _write_events(self, project: Path, events: list[dict], index: dict) -> None:
        ledger = project / LEDGER_RELATIVE
        ledger.write_text(
            "".join(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n" for event in events),
            encoding="utf-8",
        )
        index["event_ledger"]["event_count"] = len(events)
        index["event_ledger"]["sha256"] = hash_file(ledger)

    @staticmethod
    def _codes(project: Path) -> tuple[set[str], list]:
        issues = validate_agent_trace(INDEX_RELATIVE, root=project)
        return {issue.code for issue in issues}, issues

    def test_complete_h1_fixture_has_no_issues(self) -> None:
        issues = validate_agent_trace(INDEX_RELATIVE, root=FIXTURE)
        self.assertEqual([], issues)

    def test_raw_message_tamper_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            message = project / "archive/TRACE-001/A-001/messages/0001-main-agent-to-trace-reviewer-assignment.md"
            message.write_text(message.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
            codes, _ = self._codes(project)
        self.assertIn("TRACE-HASH-MISMATCH", codes)

    def test_missing_indexed_message_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            message = project / self._index(project)["messages"][0]["path"]
            message.unlink()
            codes, _ = self._codes(project)
        self.assertIn("TRACE-MESSAGE-MISSING", codes)

    def test_extra_unindexed_message_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            messages = project / "archive/TRACE-001/A-001/messages"
            shutil.copy2(
                messages / "0001-main-agent-to-trace-reviewer-assignment.md",
                messages / "0003-unindexed-message.md",
            )
            codes, _ = self._codes(project)
        self.assertIn("TRACE-MESSAGE-MISSING", codes)

    def test_undeclared_message_sequence_gap_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            index = self._index(project)
            index["messages"][1]["sequence"] = 3
            self._write_index(project, index)
            codes, _ = self._codes(project)
        self.assertIn("TRACE-SEQUENCE-GAP", codes)

    def test_whole_file_and_raw_body_hash_drift_are_distinguished(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            message = project / self._index(project)["messages"][0]["path"]
            message.write_text(
                message.read_text(encoding="utf-8").replace(
                    "2026-08-16T00:00:01Z", "2026-08-16T00:00:01+00:00", 1
                ),
                encoding="utf-8",
                newline="",
            )
            _, header_issues = self._codes(project)
        self.assertTrue(any("message MSG-0001 hash mismatch" in issue.message for issue in header_issues))
        self.assertFalse(any("raw message payload" in issue.message for issue in header_issues))

        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            index = self._index(project)
            message = project / index["messages"][0]["path"]
            message.write_text(
                message.read_text(encoding="utf-8").replace(
                    "Review the bounded Trace fixture.", "Review the changed Trace fixture."
                ),
                encoding="utf-8",
                newline="",
            )
            new_hash = hash_file(message)
            index["messages"][0]["sha256"] = new_hash
            events = self._events(project)
            events[1]["payload"]["new_sha256"] = new_hash
            self._write_events(project, events, index)
            self._write_index(project, index)
            _, body_issues = self._codes(project)
        self.assertTrue(any("raw message payload" in issue.message for issue in body_issues))
        self.assertFalse(any("message MSG-0001 hash mismatch" in issue.message for issue in body_issues))

    def test_index_path_outside_root_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            outside_index = FIXTURE / INDEX_RELATIVE
            issues = validate_agent_trace(outside_index, root=project)
        self.assertIn("TRACE-REF-OUTSIDE-ROOT", {issue.code for issue in issues})

    def test_unknown_message_owner_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            message = project / "archive/TRACE-001/A-001/messages/0001-main-agent-to-trace-reviewer-assignment.md"
            content = message.read_text(encoding="utf-8").replace(
                "accountable_owner: 路诚钺", "accountable_owner: unassigned", 1
            )
            message.write_text(content, encoding="utf-8")
            codes, _ = self._codes(project)
        self.assertIn("TRACE-ACTOR-UNOWNED", codes)

    def test_undeclared_redaction_marker_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            message = project / "archive/TRACE-001/A-001/messages/0001-main-agent-to-trace-reviewer-assignment.md"
            content = message.read_text(encoding="utf-8").replace(
                "Review the bounded Trace fixture.", "Review [[REDACTED:secret-1]]."
            )
            message.write_text(content, encoding="utf-8")
            codes, _ = self._codes(project)
        self.assertIn("TRACE-REDACTION-UNDECLARED", codes)

    def test_content_read_outside_allowlist_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            index = self._index(project)
            events = self._events(project)
            events.append(
                {
                    "schema_version": "0.1.0",
                    "event_id": "EVT-0008",
                    "task_id": "TRACE-001",
                    "task_revision": 1,
                    "attempt_id": "A-001",
                    "sequence": 8,
                    "event_type": "content-read",
                    "actor_id": "trace-reviewer",
                    "occurred_at": "2026-08-16T00:00:09Z",
                    "payload": {
                        "path": "docs/private.md",
                        "access": "content",
                        "read_range": "full",
                        "allowlist_basis": "TASK",
                        "content_sha256": "0" * 64,
                    },
                }
            )
            self._write_events(project, events, index)
            self._write_index(project, index)
            codes, _ = self._codes(project)
        self.assertIn("TRACE-READ-OUTSIDE-SCOPE", codes)

    def test_tool_outside_allowlist_and_unpersisted_result_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            index = self._index(project)
            events = self._events(project)
            events.append(
                {
                    "schema_version": "0.1.0",
                    "event_id": "EVT-0008",
                    "task_id": "TRACE-001",
                    "task_revision": 1,
                    "attempt_id": "A-001",
                    "sequence": 8,
                    "event_type": "tool-call",
                    "actor_id": "trace-reviewer",
                    "occurred_at": "2026-08-16T00:00:09Z",
                    "payload": {
                        "operation_id": "OP-001",
                        "tool_name": "unapproved-tool",
                        "allowlist_basis": "TASK",
                        "status": "succeeded",
                        "started_at": "2026-08-16T00:00:08Z",
                        "finished_at": "2026-08-16T00:00:09Z",
                        "arguments": {},
                        "redactions": [],
                        "result_entered_context": True,
                    },
                }
            )
            self._write_events(project, events, index)
            self._write_index(project, index)
            codes, _ = self._codes(project)
        self.assertIn("TRACE-TOOL-OUTSIDE-SCOPE", codes)
        self.assertIn("TRACE-TRANSIENT-RESULT-MISSING", codes)

    def test_process_artifact_modification_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            index = self._index(project)
            events = self._events(project)
            old_hash = index["messages"][0]["sha256"]
            events.append(
                {
                    "schema_version": "0.1.0",
                    "event_id": "EVT-0008",
                    "task_id": "TRACE-001",
                    "task_revision": 1,
                    "attempt_id": "A-001",
                    "sequence": 8,
                    "event_type": "file-revision",
                    "actor_id": "main-agent",
                    "occurred_at": "2026-08-16T00:00:09Z",
                    "payload": {
                        "path": index["messages"][0]["path"],
                        "action": "modified",
                        "old_sha256": old_hash,
                        "old_revision": 1,
                        "new_sha256": "0" * 64,
                        "new_revision": 2,
                    },
                }
            )
            self._write_events(project, events, index)
            self._write_index(project, index)
            codes, _ = self._codes(project)
        self.assertIn("TRACE-PROCESS-ARTIFACT-OVERWRITTEN", codes)

    def test_blank_jsonl_record_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            index = self._index(project)
            ledger = project / LEDGER_RELATIVE
            ledger.write_text(ledger.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            index["event_ledger"]["sha256"] = hash_file(ledger)
            self._write_index(project, index)
            codes, _ = self._codes(project)
        self.assertIn("TRACE-EVENT-MISSING", codes)

    def test_missing_file_revision_and_message_capture_linkage_are_detected(self) -> None:
        for event_index in (1, 2):
            with self.subTest(event_index=event_index), tempfile.TemporaryDirectory() as directory:
                project = self._copy_fixture(directory)
                index = self._index(project)
                events = self._events(project)
                events[event_index]["event_type"] = "attempt-status"
                events[event_index]["payload"] = {
                    "from_status": "running",
                    "to_status": "running",
                    "reason": "remove one required trace linkage",
                }
                self._write_events(project, events, index)
                self._write_index(project, index)
                codes, _ = self._codes(project)
                self.assertIn("TRACE-EVENT-MISSING", codes)

    def test_event_count_and_ledger_hash_mismatches_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            index = self._index(project)
            index["event_ledger"]["event_count"] += 1
            self._write_index(project, index)
            count_codes, _ = self._codes(project)
        self.assertIn("TRACE-EVENT-MISSING", count_codes)

        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            index = self._index(project)
            index["event_ledger"]["sha256"] = "0" * 64
            self._write_index(project, index)
            hash_codes, _ = self._codes(project)
        self.assertIn("TRACE-HASH-MISMATCH", hash_codes)

    def test_declared_delayed_capture_is_a_nonblocking_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            index = self._index(project)
            message_path = project / index["messages"][0]["path"]
            message_path.write_text(
                message_path.read_text(encoding="utf-8").replace(
                    "capture_status: complete", "capture_status: delayed", 1
                ),
                encoding="utf-8",
                newline="",
            )
            new_hash = hash_file(message_path)
            index["messages"][0]["sha256"] = new_hash
            index["messages"][0]["capture_status"] = "delayed"
            index["completeness"] = "delayed"
            events = self._events(project)
            events[1]["payload"]["new_sha256"] = new_hash
            self._write_events(project, events, index)
            self._write_index(project, index)
            _, issues = self._codes(project)
        self.assertEqual([], [issue for issue in issues if issue.severity == Severity.ERROR])
        self.assertIn("TRACE-CAPTURE-DELAYED", {issue.code for issue in issues})

    def test_declared_capture_gap_is_a_nonblocking_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            index = self._index(project)
            events = self._events(project)
            events.append(
                {
                    "schema_version": "0.1.0",
                    "event_id": "EVT-0008",
                    "task_id": "TRACE-001",
                    "task_revision": 1,
                    "attempt_id": "A-001",
                    "sequence": 8,
                    "event_type": "capture-gap",
                    "actor_id": "main-agent",
                    "occurred_at": "2026-08-16T00:00:09Z",
                    "payload": {
                        "affected_stream": "messages",
                        "reason_category": "platform-unavailable",
                        "reason": "fixture platform omitted one visible message",
                        "sequence_start": 3,
                        "sequence_end": 3,
                        "affected_ids": ["MSG-0003"],
                    },
                }
            )
            index["capture_gaps"] = [
                {
                    "event_id": "EVT-0008",
                    "affected_stream": "messages",
                    "sequence_start": 3,
                    "sequence_end": 3,
                    "affected_ids": ["MSG-0003"],
                }
            ]
            index["completeness"] = "gapped"
            self._write_events(project, events, index)
            self._write_index(project, index)
            _, issues = self._codes(project)
        self.assertEqual([], [issue for issue in issues if issue.severity == Severity.ERROR])
        self.assertIn("TRACE-CAPTURE-GAP", {issue.code for issue in issues})

    def test_false_complete_claim_over_declared_gap_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._copy_fixture(directory)
            index = self._index(project)
            events = self._events(project)
            events.append(
                {
                    "schema_version": "0.1.0",
                    "event_id": "EVT-0008",
                    "task_id": "TRACE-001",
                    "task_revision": 1,
                    "attempt_id": "A-001",
                    "sequence": 8,
                    "event_type": "capture-gap",
                    "actor_id": "main-agent",
                    "occurred_at": "2026-08-16T00:00:09Z",
                    "payload": {
                        "affected_stream": "messages",
                        "reason_category": "capture-failure",
                        "reason": "fixture gap contradicts a complete claim",
                        "sequence_start": 3,
                        "sequence_end": 3,
                    },
                }
            )
            index["capture_gaps"] = [
                {
                    "event_id": "EVT-0008",
                    "affected_stream": "messages",
                    "sequence_start": 3,
                    "sequence_end": 3,
                }
            ]
            self._write_events(project, events, index)
            self._write_index(project, index)
            _, issues = self._codes(project)
        errors = [issue for issue in issues if issue.severity == Severity.ERROR]
        self.assertIn("TRACE-SEQUENCE-GAP", {issue.code for issue in errors})


if __name__ == "__main__":
    unittest.main()
