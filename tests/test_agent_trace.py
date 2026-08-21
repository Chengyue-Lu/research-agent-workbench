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
    _create_exclusive,
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

    def rewrite_message(self, position: int, mutate_envelope, mutate_entry=lambda _entry: None) -> None:
        index_path = self.attempt / "INDEX.yaml"
        index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        entry = index["messages"][position]
        message_path = self.attempt / entry["path"]
        envelope, body = _parse_message(message_path)
        envelope = dict(envelope)
        mutate_envelope(envelope)
        content = b"---\n" + yaml.safe_dump(envelope, sort_keys=False).encode() + b"---\n" + body + b"\n"
        message_path.write_bytes(content)
        entry["sha256"] = __import__("hashlib").sha256(content).hexdigest()
        mutate_entry(entry)
        index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")

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
                "result_entered_context": True,
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

    def test_generic_tool_result_does_not_claim_context_delivery_implicitly(self) -> None:
        recorder = self.recorder()
        recorder.record(
            "tool-result",
            {
                "call_id": "call-1",
                "name": "read_file",
                "status": "succeeded",
                "arguments": {"path": "inputs/a.txt"},
                "result": "observed but not delivered",
            },
        )
        recorder.seal("safe-paused")
        events = [
            json.loads(line)
            for line in (self.attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        tool_event = next(event for event in events if event["event_type"] == "tool-call")
        self.assertFalse(tool_event["payload"]["result_entered_context"])
        self.assertNotIn("result_ref", tool_event["payload"])
        self.assertEqual([], list((self.attempt / "tool-events").iterdir()))

    def test_typed_fact_events_form_a_valid_trace(self) -> None:
        recorder = self.recorder()
        recorder.record_content_read(
            "inputs/a.txt",
            access="content",
            allowlist_basis="Task read allowlist",
            content_sha256="0" * 64,
        )
        recorder.record_tool_call(
            operation_id="shell-1",
            tool_name="read_file",
            status="succeeded",
            arguments={"path": "inputs/a.txt"},
            result="bounded content",
            result_entered_context=True,
        )
        recorder.record_file_revision(
            "outputs/result.txt",
            action="created",
            new_sha256="1" * 64,
            reason="bounded output",
        )
        recorder.record_external_action(
            action_id="publish-1",
            target_category="local-fixture",
            authorization_basis="test fixture authorization",
            side_effect_status="planned",
        )
        recorder.record_attempt_status("safe-paused", reason="fixture boundary reached")
        recorder.seal()

        result = validate_attempt_trace(self.root, self.attempt)
        self.assertFalse(result.blocked, result.risks)
        events = [
            json.loads(line)
            for line in (self.attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(
            [
                "attempt-status",
                "content-read",
                "tool-call",
                "file-revision",
                "external-action",
                "attempt-status",
            ],
            [event["event_type"] for event in events],
        )

    def test_typed_fact_events_expose_boundary_violations(self) -> None:
        recorder = self.recorder()
        recorder.record_content_read(
            "private/secret.txt",
            access="content",
            allowlist_basis="injected invalid fixture",
        )
        recorder.record_tool_call(
            operation_id="shell-1",
            tool_name="shell",
            status="attempted",
            arguments={"command": "echo bounded"},
        )
        recorder.record_file_revision("elsewhere/result.txt", action="created")
        recorder.seal("safe-paused")
        codes = {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks}
        self.assertTrue(
            {"TRACE-READ-OUTSIDE-SCOPE"}.issubset(codes)
        )

    def test_typed_tool_result_requires_content_before_context_delivery(self) -> None:
        recorder = self.recorder()
        with self.assertRaises(ValueError):
            recorder.record_tool_call(
                operation_id="tool-1",
                tool_name="read_file",
                status="delivered",
                arguments={},
                result_entered_context=True,
            )

    def test_hash_tamper_is_blocking(self) -> None:
        recorder = self.recorder()
        recorder.record("provider-request", {"model": "test"})
        recorder.record("session-status", {"status": "safe_paused", "reason": "budget"})
        recorder.seal()
        message = next((self.attempt / "messages").iterdir())
        message.write_bytes(message.read_bytes() + b"tamper")
        result = validate_attempt_trace(self.root, self.attempt)
        self.assertTrue(result.blocked)
        self.assertIn("TRACE-HASH-MISMATCH", {risk.code for risk in result.risks})

    def test_completed_trace_with_capture_gap_is_blocking(self) -> None:
        recorder = self.recorder()
        recorder.record_capture_gap("messages", "injected post-call storage outage")
        recorder.record("session-status", {"status": "completed", "reason": "invalid completion fixture"})
        recorder.seal()
        result = validate_attempt_trace(self.root, self.attempt)
        codes = {risk.code for risk in result.risks}
        self.assertTrue(result.blocked)
        self.assertIn("TRACE-CAPTURE-DELAYED", codes)

    def test_index_path_escape_is_blocking(self) -> None:
        recorder = self.recorder()
        recorder.record("session-status", {"status": "safe_paused", "reason": "fixture"})
        recorder.seal()
        index_path = self.attempt / "INDEX.yaml"
        index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        index["task_ref"]["path"] = "../outside.yaml"
        index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")
        result = validate_attempt_trace(self.root, self.attempt)
        self.assertIn("TRACE-EVENT-MISSING", {risk.code for risk in result.risks})

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
        self.assertIn("TRACE-SEQUENCE-GAP", codes)
        self.assertIn("TRACE-ACTOR-UNOWNED", codes)

    def test_existing_trace_artifact_is_not_overwritten(self) -> None:
        self.attempt.mkdir(parents=True)
        (self.attempt / "INDEX.yaml").write_text("owned: true\n", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.recorder()
        self.assertEqual("owned: true\n", (self.attempt / "INDEX.yaml").read_text(encoding="utf-8"))

    def test_exclusive_write_failure_removes_partial_artifact(self) -> None:
        target = self.root / "partial.trace"
        with patch(
            "research_workbench.observability.trace.os.fsync",
            side_effect=OSError("injected storage failure"),
        ):
            with self.assertRaises(OSError):
                _create_exclusive(target, b"must not survive")
        self.assertFalse(target.exists())

    def test_atomic_index_failure_preserves_previous_index_and_blocks_replay(self) -> None:
        recorder = self.recorder()
        index_path = self.attempt / "INDEX.yaml"
        previous = index_path.read_bytes()
        with patch(
            "research_workbench.observability.trace.os.replace",
            side_effect=OSError("injected atomic publication failure"),
        ):
            with self.assertRaises(OSError):
                recorder.record_content_read(
                    "inputs/a.txt",
                    access="content",
                    allowlist_basis="fixture",
                )
        self.assertEqual(previous, index_path.read_bytes())
        self.assertFalse(list(self.attempt.glob(".INDEX.yaml.*.tmp")))
        codes = {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks}
        self.assertIn("TRACE-HASH-MISMATCH", codes)

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
        self.assertIn("TRACE-EVENT-MISSING", {risk.code for risk in validate_attempt_trace(self.root, missing).risks})
        outside = self.root.parent / "outside-attempt"
        self.assertIn("TRACE-READ-OUTSIDE-SCOPE", {risk.code for risk in validate_attempt_trace(self.root, outside).risks})
        self.attempt.mkdir(parents=True)
        (self.attempt / "INDEX.yaml").write_text("- not\n- a mapping\n", encoding="utf-8")
        self.assertIn("TRACE-EVENT-MISSING", {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks})

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
        self.assertIn("TRACE-ACTOR-UNOWNED", codes)
        self.assertIn("TRACE-EVENT-MISSING", codes)
        self.rewrite_index(lambda index: index.update({"actors_ref": {}}))
        codes = {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks}
        self.assertIn("TRACE-EVENT-MISSING", codes)

    def test_identity_drift_and_malformed_index_values_fail_as_structured_risks(self) -> None:
        recorder = self.recorder()
        recorder.seal("safe-paused")
        actors_path = self.attempt / "ACTORS.yaml"
        actors = yaml.safe_load(actors_path.read_text(encoding="utf-8"))
        actors["task_id"] = "OTHER"
        actors["actors"].append(dict(actors["actors"][0]))
        actors_path.write_text(yaml.safe_dump(actors, sort_keys=False), encoding="utf-8")
        actors_hash = __import__("hashlib").sha256(actors_path.read_bytes()).hexdigest()
        self.rewrite_index(
            lambda index: (
                index["actors_ref"].update({"sha256": actors_hash}),
                index.update(
                    {
                        "owner_actor_id": "ghost",
                        "task_revision": "not-an-integer",
                        "capture_gaps": "not-a-list",
                        "read_allowlist": None,
                    }
                ),
            )
        )
        result = validate_attempt_trace(self.root, self.attempt)
        codes = {risk.code for risk in result.risks}
        self.assertTrue(result.blocked)
        self.assertIn("TRACE-EVENT-MISSING", codes)
        self.assertIn("TRACE-ACTOR-UNOWNED", codes)

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
            "TRACE-EVENT-MISSING",
            "TRACE-ACTOR-UNOWNED",
            "TRACE-READ-OUTSIDE-SCOPE",
            "TRACE-TRANSIENT-RESULT-MISSING",
            "TRACE-PROCESS-ARTIFACT-OVERWRITTEN",
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
            "TRACE-SEQUENCE-GAP",
            "TRACE-HASH-MISMATCH",
            "TRACE-MESSAGE-MISSING",
            "TRACE-ACTOR-UNOWNED",
            "TRACE-REDACTION-UNDECLARED",
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

    def test_validator_rejects_hash_consistent_non_json_message_body(self) -> None:
        recorder = self.recorder()
        recorder.record("provider-request", {"request": {"model": "test"}})
        recorder.seal("safe-paused")
        message = next((self.attempt / "messages").iterdir())
        envelope, _ = _parse_message(message)
        envelope = dict(envelope)
        body = b"not-json"
        digest = __import__("hashlib").sha256(body).hexdigest()
        envelope["content_sha256"] = digest
        content = b"---\n" + yaml.safe_dump(envelope, sort_keys=False).encode() + b"---\n" + body + b"\n"
        message.write_bytes(content)
        message_digest = __import__("hashlib").sha256(content).hexdigest()
        self.rewrite_index(
            lambda index: index["messages"][0].update(
                {"sha256": message_digest, "content_sha256": digest}
            )
        )
        codes = {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks}
        self.assertIn("TRACE-MESSAGE-MISSING", codes)

    def test_false_complete_unfrozen_and_unknown_record_kind(self) -> None:
        recorder = self.recorder()
        with self.assertRaises(ValueError):
            recorder.record("unknown-kind", {})
        recorder.record("session-status", {"status": "completed", "reason": "fixture"})
        self.rewrite_index(lambda index: index.update({"trace_status": "active"}))
        codes = {risk.code for risk in validate_attempt_trace(self.root, self.attempt).risks}
        self.assertIn("TRACE-EVENT-MISSING", codes)
        recorder.seal()
        with self.assertRaises(RuntimeError):
            recorder.record("provider-request", {"request": {}})
        with self.assertRaises(RuntimeError):
            recorder.record_file_revision("outputs/late.txt", action="created")

    def test_actor_owner_and_message_owner_drift_are_canonical_blocks(self) -> None:
        recorder = self.recorder()
        recorder.record("provider-request", {"request": {"model": "test"}})
        recorder.seal("safe-paused")
        self.rewrite_index(lambda index: index.update({"owner": "Other Owner"}))
        self.rewrite_message(
            0,
            lambda envelope: envelope.update({"accountable_owner": "Other Owner"}),
        )

        risks = validate_attempt_trace(self.root, self.attempt).risks
        self.assertIn("TRACE-ACTOR-UNOWNED", {risk.code for risk in risks})
        details = {risk.message.split("]", 1)[0] + "]" for risk in risks}
        self.assertIn("[owner-drift]", details)
        self.assertIn("[message-owner-drift]", details)

    def test_transient_result_origin_and_ref_mutations_fail_closed(self) -> None:
        recorder = self.recorder()
        recorder.record_tool_call(
            operation_id="op-transient",
            tool_name="read_file",
            status="delivered",
            arguments={"path": "inputs/a.txt"},
            result="entered context",
            result_entered_context=True,
        )
        recorder.seal("safe-paused")
        original = [
            json.loads(line)
            for line in (self.attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        tool_position = next(
            position for position, event in enumerate(original) if event["event_type"] == "tool-call"
        )

        without_origin = json.loads(json.dumps(original))
        without_origin[tool_position]["payload"].pop("result_origin")
        without_origin[tool_position]["payload"].pop("result_ref")
        self.rewrite_events([json.dumps(event) for event in without_origin])
        risks = validate_attempt_trace(self.root, self.attempt).risks
        self.assertIn("TRACE-TRANSIENT-RESULT-MISSING", {risk.code for risk in risks})
        self.assertTrue(any("[result-origin-missing]" in risk.message for risk in risks))

        without_ref = json.loads(json.dumps(original))
        without_ref[tool_position]["payload"].pop("result_ref")
        self.rewrite_events([json.dumps(event) for event in without_ref])
        risks = validate_attempt_trace(self.root, self.attempt).risks
        self.assertIn("TRACE-TRANSIENT-RESULT-MISSING", {risk.code for risk in risks})
        self.assertTrue(any("[transient-result-ref-missing]" in risk.message for risk in risks))

    def test_capture_gap_index_message_and_completeness_are_bidirectional(self) -> None:
        recorder = self.recorder()
        recorder.record("provider-request", {"request": {"model": "test"}})
        recorder.record_capture_gap(
            "messages",
            "injected partial export",
            affected_ids=("MSG-0001",),
        )
        recorder.seal("safe-paused")
        gap_id = self.rewrite_index(lambda _index: None)["capture_gaps"][0]["event_id"]
        self.rewrite_message(
            0,
            lambda envelope: envelope.update(
                {"capture_status": "partial", "capture_gap_event_id": gap_id}
            ),
            lambda entry: entry.update(
                {"capture_status": "partial", "capture_gap_event_id": gap_id}
            ),
        )
        result = validate_attempt_trace(self.root, self.attempt)
        self.assertFalse(result.blocked, result.risks)
        self.assertIn("TRACE-CAPTURE-DELAYED", {risk.code for risk in result.risks})

        self.rewrite_index(
            lambda index: index.update({"capture_gaps": [], "completeness": "complete"})
        )
        risks = validate_attempt_trace(self.root, self.attempt).risks
        self.assertTrue(any(risk.level.value == "block" for risk in risks))
        self.assertTrue(any("[capture-gap-event-unindexed]" in risk.message for risk in risks))
        self.assertTrue(any("[capture-completeness-drift]" in risk.message for risk in risks))

    def test_delayed_message_requires_delayed_completeness_without_gap_ref(self) -> None:
        recorder = self.recorder()
        recorder.record("provider-request", {"request": {"model": "test"}})
        recorder.seal("safe-paused")
        self.rewrite_message(
            0,
            lambda envelope: envelope.update({"capture_status": "delayed"}),
            lambda entry: entry.update({"capture_status": "delayed"}),
        )
        self.rewrite_index(lambda index: index.update({"completeness": "delayed"}))
        events = [
            json.loads(line)
            for line in (self.attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        capture = next(event for event in events if event["event_type"] == "message-capture")
        capture["payload"]["action"] = "exported-delayed"
        self.rewrite_events([json.dumps(event) for event in events])
        result = validate_attempt_trace(self.root, self.attempt)
        self.assertFalse(result.blocked, result.risks)
        self.assertIn("TRACE-CAPTURE-DELAYED", {risk.code for risk in result.risks})

        self.rewrite_index(lambda index: index.update({"completeness": "complete"}))
        risks = validate_attempt_trace(self.root, self.attempt).risks
        self.assertTrue(any("[capture-completeness-drift]" in risk.message for risk in risks))

    def test_attempt_status_chain_and_index_final_status_are_bound(self) -> None:
        recorder = self.recorder()
        recorder.seal("safe-paused")
        events = [
            json.loads(line)
            for line in (self.attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        events[-1]["payload"]["from_status"] = "planned"
        events[-1]["payload"]["to_status"] = "failed"
        self.rewrite_events([json.dumps(event) for event in events])

        risks = validate_attempt_trace(self.root, self.attempt).risks
        self.assertTrue(any("[attempt-status-chain-drift]" in risk.message for risk in risks))
        self.assertTrue(any("[attempt-status-index-drift]" in risk.message for risk in risks))

    def test_index_message_projection_matches_every_hash_bound_envelope_field(self) -> None:
        recorder = self.recorder()
        recorder.record("provider-request", {"request": {"model": "test"}})
        recorder.seal("safe-paused")
        index_path = self.attempt / "INDEX.yaml"
        original = index_path.read_text(encoding="utf-8")
        mutations = {
            "message_id": "MSG-9999",
            "sequence": 9,
            "kind": "provider-response",
            "sender_actor_id": "provider-openai-responses",
            "receiver_actor_ids": ["runtime-AT-0001"],
            "created_at": "2026-08-21T01:00:00Z",
            "capture_status": "delayed",
            "capture_gap_event_id": "EVT-9999",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                index = yaml.safe_load(original)
                index["messages"][0][field] = value
                index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")
                risks = validate_attempt_trace(self.root, self.attempt).risks
                self.assertTrue(
                    any("[message-index-envelope-drift]" in risk.message for risk in risks),
                    risks,
                )
        index_path.write_text(original, encoding="utf-8")

    def test_event_and_message_ids_must_be_unique(self) -> None:
        recorder = self.recorder()
        recorder.record("provider-request", {"request": {"model": "one"}})
        recorder.record("provider-request", {"request": {"model": "two"}})
        recorder.seal("safe-paused")
        events = [
            json.loads(line)
            for line in (self.attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        events[1]["event_id"] = events[0]["event_id"]
        self.rewrite_events([json.dumps(event) for event in events])
        self.rewrite_index(
            lambda index: index["messages"][1].update(
                {"message_id": index["messages"][0]["message_id"]}
            )
        )
        risks = validate_attempt_trace(self.root, self.attempt).risks
        self.assertTrue(any("[duplicate-event-id]" in risk.message for risk in risks))
        self.assertTrue(any("[duplicate-message-id]" in risk.message for risk in risks))

    def test_all_runtime_event_payloads_are_sanitized_with_metadata(self) -> None:
        recorder = self.recorder()
        recorder.record_file_revision(
            "outputs/result.txt",
            action="created",
            reason="token=revision-secret-value",
        )
        recorder.record_external_action(
            action_id="external-1",
            target_category="fixture",
            authorization_basis="Bearer external-secret-value",
            side_effect_status="planned",
        )
        recorder.record("session-status", {"status": "waiting", "reason": "api_key=session-secret-value"})
        recorder.record_capture_gap("events", "secret=capture-secret-value")
        recorder.seal()
        rendered = (self.attempt / "events.jsonl").read_text(encoding="utf-8")
        for secret in (
            "revision-secret-value",
            "external-secret-value",
            "session-secret-value",
            "capture-secret-value",
        ):
            self.assertNotIn(secret, rendered)
        events = [json.loads(line) for line in rendered.splitlines()]
        redacted_types = {
            event["event_type"] for event in events if event.get("redactions")
        }
        self.assertTrue(
            {"file-revision", "external-action", "attempt-status", "capture-gap"}.issubset(redacted_types)
        )
        self.assertFalse(validate_attempt_trace(self.root, self.attempt).blocked)

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
