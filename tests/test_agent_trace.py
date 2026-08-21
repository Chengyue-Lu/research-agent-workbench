from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from research_workbench.cli import main
from research_workbench.observability.trace import (
    AgentTraceRecorder,
    _parse_message,
    _plain,
    derive_session_transcript,
    sanitize_trace_value,
    validate_attempt_trace,
)
from research_workbench.io import load_document
from research_workbench.validation.schemas import SchemaCatalog

ROOT = Path(__file__).resolve().parents[1]


class AgentTraceTests(unittest.TestCase):
    def test_four_trace_schema_fixture_pairs(self) -> None:
        catalog = SchemaCatalog(ROOT / "schemas")
        fixture_root = ROOT / "tests/fixtures/trace"
        for stem, kind in (
            ("actors", "agent_trace_actors"),
            ("envelope", "agent_trace_envelope"),
            ("event", "agent_trace_event"),
            ("index", "agent_trace_index"),
        ):
            valid = load_document(next(fixture_root.glob(f"{stem}.valid.*")))
            invalid = load_document(next(fixture_root.glob(f"{stem}.invalid.*")))
            self.assertEqual([], catalog.validate(kind, valid), stem)
            self.assertTrue(catalog.validate(kind, invalid), stem)

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.attempt = self.root / "work" / "TRACE-TEST" / "AT-0001"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def recorder(self) -> AgentTraceRecorder:
        return AgentTraceRecorder(
            self.attempt,
            task_id="TRACE-TEST",
            task_revision=1,
            attempt_id="AT-0001",
            task_snapshot={"task_id": "TRACE-TEST", "revision": 1},
            accountable_owner="Huang Yi",
            actor_id="runtime-AT-0001",
            runtime_identity="pytest-runtime",
            provider="openai-responses",
            read_allowlist=("inputs/**",),
            write_scope=("outputs/**",),
            tool_allowlist=("read_file",),
            created_at="2026-08-21T00:00:00Z",
        )

    def rewrite_index(self, mutate) -> dict:
        index_path = self.attempt / "INDEX.yaml"
        index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        mutate(index)
        index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")
        return index

    def rewrite_events(self, lines: list[str], event_count: int | None = None) -> None:
        events_path = self.attempt / "events.jsonl"
        events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        digest = __import__("hashlib").sha256(events_path.read_bytes()).hexdigest()
        self.rewrite_index(
            lambda index: index["event_ledger"].update(
                {"sha256": digest, "event_count": event_count if event_count is not None else len(lines)}
            )
        )

    def test_recorder_captures_before_send_redacts_and_validates(self) -> None:
        recorder = self.recorder()
        recorder.record(
            "provider-request",
            {"model": "env-bound", "headers": {"Authorization": "Bearer do-not-store-this-token"}},
        )
        recorder.record(
            "provider-response",
            {"text": "ok", "reasoning_content": "private chain of thought"},
        )
        recorder.record(
            "tool-attempted",
            {"call_id": "call-1", "name": "read_file", "arguments": {"path": "inputs/a.txt"}},
        )
        recorder.record(
            "tool-result",
            {
                "call_id": "call-1",
                "name": "read_file",
                "status": "succeeded",
                "arguments": {"path": "inputs/a.txt"},
                "result": "bounded content",
            },
        )
        recorder.record("session-status", {"status": "completed", "reason": "bounded session complete"})
        first = recorder.seal()
        self.assertEqual(first, recorder.seal())
        self.assertGreaterEqual(recorder.redaction_count, 2)

        package = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in self.attempt.rglob("*")
            if path.is_file()
        )
        self.assertNotIn("do-not-store-this-token", package)
        self.assertNotIn("private chain of thought", package)
        self.assertIn("[REDACTED:credential]", package)
        self.assertIn("[OMITTED:hidden-reasoning]", package)
        result = validate_attempt_trace(self.root, self.attempt)
        self.assertFalse(result.blocked, result.risks)

    def test_hash_tamper_is_blocking(self) -> None:
        recorder = self.recorder()
        recorder.record("provider-request", {"model": "test"})
        recorder.record("session-status", {"status": "safe_paused", "reason": "budget"})
        recorder.seal()
        message = next((self.attempt / "messages").iterdir())
        message.write_bytes(message.read_bytes() + b"tamper")
        result = validate_attempt_trace(self.root, self.attempt)
        self.assertTrue(result.blocked)
        self.assertIn("TRACE-HASH-DRIFT", {risk.code for risk in result.risks})

    def test_completed_trace_with_capture_gap_is_blocking(self) -> None:
        recorder = self.recorder()
        recorder.record_capture_gap("messages", "injected post-call storage outage")
        recorder.record("session-status", {"status": "completed", "reason": "invalid completion fixture"})
        recorder.seal()
        result = validate_attempt_trace(self.root, self.attempt)
        codes = {risk.code for risk in result.risks}
        self.assertTrue(result.blocked)
        self.assertIn("TRACE-CAPTURE-GAP", codes)

    def test_index_path_escape_is_blocking(self) -> None:
        recorder = self.recorder()
        recorder.record("session-status", {"status": "safe_paused", "reason": "fixture"})
        recorder.seal()
        index_path = self.attempt / "INDEX.yaml"
        index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        index["task_ref"]["path"] = "../outside.yaml"
        index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")
        result = validate_attempt_trace(self.root, self.attempt)
        self.assertIn("TRACE-PATH-ESCAPE", {risk.code for risk in result.risks})

    def test_event_sequence_and_unknown_actor_are_blocking(self) -> None:
        recorder = self.recorder()
        recorder.record("provider-request", {"model": "test"})
        recorder.seal("safe-paused")
        events_path = self.attempt / "events.jsonl"
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
        events[-1]["sequence"] = 99
        events[-1]["actor_id"] = "unregistered"
        events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
        index_path = self.attempt / "INDEX.yaml"
        index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        import hashlib

        index["event_ledger"]["sha256"] = hashlib.sha256(events_path.read_bytes()).hexdigest()
        index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")
        result = validate_attempt_trace(self.root, self.attempt)
        codes = {risk.code for risk in result.risks}
        self.assertIn("TRACE-EVENT-SEQUENCE", codes)
        self.assertIn("TRACE-ACTOR-UNKNOWN", codes)

    def test_existing_trace_artifact_is_not_overwritten(self) -> None:
        self.attempt.mkdir(parents=True)
        (self.attempt / "INDEX.yaml").write_text("owned: true\n", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.recorder()
        self.assertEqual("owned: true\n", (self.attempt / "INDEX.yaml").read_text(encoding="utf-8"))

    def test_sanitizer_catches_key_and_value_shapes(self) -> None:
        cleaned, redactions = sanitize_trace_value(
            {"api_key": "plain", "message": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz", "reasoning_content": "hidden"}
        )
        self.assertEqual("[REDACTED:credential]", cleaned["api_key"])
        self.assertEqual("[REDACTED:credential]", cleaned["message"])
        self.assertEqual("[OMITTED:hidden-reasoning]", cleaned["reasoning_content"])
        self.assertEqual(3, len(redactions))
        self.assertFalse(any("plain" in str(item) for item in redactions))

    def test_sanitizer_omits_entire_provider_reasoning_block(self) -> None:
        cleaned, redactions = sanitize_trace_value(
            {"output": [{"kind": "reasoning", "data": {"summary": "must never persist"}}]}
        )
        rendered = json.dumps(cleaned)
        self.assertNotIn("must never persist", rendered)
        self.assertIn("[OMITTED:hidden-reasoning]", rendered)
        self.assertEqual("hidden-reasoning", redactions[0]["category"])

    def test_cli_accepts_attempt_directory_or_index(self) -> None:
        recorder = self.recorder()
        recorder.record("session-status", {"status": "safe_paused", "reason": "fixture"})
        recorder.seal()
        with patch("builtins.print"):
            self.assertEqual(0, main(["trace", "validate", "--attempt", str(self.attempt), "--root", str(self.root)]))
            self.assertEqual(0, main(["trace", "validate", "--attempt", str(self.attempt / "INDEX.yaml"), "--root", str(self.root)]))

    def test_missing_invalid_and_outside_index_fail_closed(self) -> None:
        missing = self.root / "work/missing"
        missing.mkdir(parents=True)
        self.assertIn("TRACE-INDEX-MISSING", {risk.code for risk in validate_attempt_trace(self.root, missing).risks})
        outside = self.root.parent / "outside-attempt"
        self.assertIn("TRACE-PATH-ESCAPE", {risk.code for risk in validate_attempt_trace(self.root, outside).risks})
        self.attempt.mkdir(parents=True)
        (self.attempt / "INDEX.yaml").write_text("- not\n- a mapping\n", encoding="utf-8")
        self.assertIn("TRACE-INDEX-INVALID", {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks})

    def test_invalid_actor_and_reference_shapes_are_structured_blocks(self) -> None:
        recorder = self.recorder()
        recorder.seal("safe-paused")
        actors_path = self.attempt / "ACTORS.yaml"
        actors_path.write_text("- invalid\n", encoding="utf-8")
        actors_hash = __import__("hashlib").sha256(actors_path.read_bytes()).hexdigest()
        self.rewrite_index(
            lambda index: (
                index["actors_ref"].update({"sha256": actors_hash}),
                index.update({"task_ref": {"path": "missing-task.yaml", "sha256": "0" * 64}}),
            )
        )
        codes = {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks}
        self.assertIn("TRACE-ACTORS-INVALID", codes)
        self.assertIn("TRACE-REF-MISSING", codes)
        self.rewrite_index(lambda index: index.update({"actors_ref": {}}))
        codes = {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks}
        self.assertIn("TRACE-REF-INVALID", codes)

    def test_event_ledger_fault_matrix_and_boundaries(self) -> None:
        recorder = self.recorder()
        recorder.seal("safe-paused")
        base = json.loads((self.attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()[0])

        def event(sequence: int, event_type: str, payload, *, actor: str = "runtime-AT-0001", task: str = "TRACE-TEST") -> str:
            value = dict(base)
            value.update({"event_id": f"EVT-{sequence:04d}", "sequence": sequence, "event_type": event_type, "actor_id": actor, "task_id": task, "payload": payload})
            return json.dumps(value)

        lines = [
            json.dumps(base),
            event(2, "content-read", {"path": "secret.txt", "access": "content", "allowlist_basis": "fixture"}),
            event(3, "tool-call", {"operation_id": "op-x", "tool_name": "shell", "status": "delivered", "arguments": {}, "redactions": [], "result_entered_context": True, "result_origin": "transient"}),
            event(4, "file-revision", {"path": "INDEX.yaml", "action": "modified"}),
            event(5, "file-revision", {"path": "elsewhere.txt", "action": "created"}),
            event(6, "attempt-status", "not-a-mapping"),
            event(7, "attempt-status", {"to_status": "waiting", "reason": "identity fault"}, actor="ghost", task="OTHER"),
            "",
            "{bad-json",
            "[]",
        ]
        self.rewrite_events(lines, event_count=99)
        codes = {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks}
        expected = {
            "TRACE-EVENT-BLANK", "TRACE-EVENT-INVALID", "TRACE-EVENT-COUNT",
            "TRACE-SCHEMA-INVALID", "TRACE-ACTOR-UNKNOWN", "TRACE-IDENTITY-DRIFT",
            "TRACE-READ-OUTSIDE-ALLOWLIST", "TRACE-TOOL-OUTSIDE-ALLOWLIST",
            "TRACE-REF-INVALID", "TRACE-PROCESS-ARTIFACT-OVERWRITE", "TRACE-WRITE-OUTSIDE-SCOPE",
        }
        self.assertTrue(expected.issubset(codes), expected - codes)

    def test_message_fault_matrix_detects_all_drift_classes(self) -> None:
        recorder = self.recorder()
        recorder.record("provider-request", {"request": {"model": "test"}})
        recorder.seal("safe-paused")
        message = next((self.attempt / "messages").iterdir())
        envelope, _body = _parse_message(message)
        envelope = dict(envelope)
        envelope.update({"task_id": "OTHER", "sender_actor_id": "ghost", "content_sha256": "0" * 64, "redactions": []})
        body = b'"[REDACTED:credential]"'
        content = b"---\n" + yaml.safe_dump(envelope, sort_keys=False).encode() + b"---\n" + body + b"\n"
        message.write_bytes(content)
        digest = __import__("hashlib").sha256(content).hexdigest()
        self.rewrite_index(lambda index: (index["messages"][0].update({"sha256": digest, "sequence": 2}), index["messages"].append("bad-entry")))
        (self.attempt / "messages" / "unindexed.trace").write_text("extra", encoding="utf-8")
        codes = {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks}
        expected = {
            "TRACE-MESSAGE-SEQUENCE", "TRACE-CONTENT-HASH", "TRACE-ENVELOPE-DRIFT",
            "TRACE-IDENTITY-DRIFT", "TRACE-ACTOR-UNKNOWN", "TRACE-REDACTION-UNDECLARED",
            "TRACE-MESSAGE-UNINDEXED", "TRACE-SCHEMA-INVALID",
        }
        self.assertTrue(expected.issubset(codes), expected - codes)

    def test_message_parser_and_derived_transcript_fail_closed(self) -> None:
        for name, content in (("no-header", b"bad"), ("no-body", b"---\nkey: value\n"), ("bad-header", b"---\n- list\n---\n{}\n")):
            path = self.root / name
            path.write_bytes(content)
            with self.assertRaises(ValueError):
                _parse_message(path)
        recorder = self.recorder()
        recorder.record("provider-request", {"request": {"model": "test"}})
        recorder.seal("safe-paused")
        transcript = derive_session_transcript(self.attempt)
        self.assertIsNone(transcript[0]["response"])
        message = next((self.attempt / "messages").iterdir())
        message.write_bytes(message.read_bytes() + b"tamper")
        with self.assertRaises(ValueError):
            derive_session_transcript(self.attempt)

    def test_false_complete_unfrozen_and_unknown_record_kind(self) -> None:
        recorder = self.recorder()
        with self.assertRaises(ValueError):
            recorder.record("unknown-kind", {})
        recorder.record("session-status", {"status": "completed", "reason": "fixture"})
        self.rewrite_index(lambda index: index.update({"trace_status": "active"}))
        codes = {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks}
        self.assertIn("TRACE-FALSE-COMPLETE", codes)
        recorder.seal()
        with self.assertRaises(RuntimeError):
            recorder.record("provider-request", {"request": {}})

    def test_plain_supports_to_mapping_and_object_dict(self) -> None:
        class WithMapping:
            def to_mapping(self):
                return {"value": 1}

        class WithDict:
            def __init__(self):
                self.data = 2

        self.assertEqual({"value": 1}, _plain(WithMapping()))
        self.assertEqual({"data": 2}, _plain(WithDict()))


if __name__ == "__main__":
    unittest.main()
