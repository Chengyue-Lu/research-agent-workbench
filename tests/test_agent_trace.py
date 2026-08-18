import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

import yaml

from research_workbench.artifacts import hash_file
from research_workbench.trace import validate_trace_archive


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path("examples/agent-trace/valid")


class AgentTraceValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.fixture = self.root / FIXTURE
        self.fixture.parent.mkdir(parents=True)
        shutil.copytree(ROOT / FIXTURE, self.fixture)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _load_yaml(self, name: str) -> dict[str, Any]:
        value = yaml.safe_load((self.fixture / name).read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def _write_yaml(self, name: str, value: dict[str, Any]) -> None:
        (self.fixture / name).write_text(
            yaml.safe_dump(value, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def _load_events(self) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in (self.fixture / "events.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _write_events(self, events: list[dict[str, Any]], *, sync_index: bool = True) -> None:
        event_path = self.fixture / "events.jsonl"
        event_path.write_text(
            "".join(json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n" for event in events),
            encoding="utf-8",
        )
        index = self._load_yaml("INDEX.yaml")
        event_hash = hash_file(event_path)
        index["event_ledger_ref"]["sha256"] = event_hash
        if sync_index:
            fields = ("event_id", "sequence", "event_type", "actor_id", "occurred_at", "status")
            index["events"] = [{field: event[field] for field in fields} for event in events]
        self._write_yaml("INDEX.yaml", index)
        self._refresh_envelope(event_hash=event_hash)

    def _refresh_envelope(self, *, event_hash: str | None = None) -> None:
        envelope = self._load_yaml("TRACE.yaml")
        if event_hash is not None:
            envelope["event_ledger_ref"]["sha256"] = event_hash
        envelope["index_ref"]["sha256"] = hash_file(self.fixture / "INDEX.yaml")
        self._write_yaml("TRACE.yaml", envelope)

    def _mutate_event(self, event_id: str, mutation: Callable[[dict[str, Any]], None]) -> None:
        events = self._load_events()
        event = next(item for item in events if item["event_id"] == event_id)
        mutation(event)
        self._write_events(events)

    def _codes(self) -> set[str]:
        report = validate_trace_archive(self.fixture / "TRACE.yaml", root=self.root)
        return {risk.code for risk in report.risks}

    def test_valid_trace_fixture_passes(self) -> None:
        report = validate_trace_archive(self.fixture / "TRACE.yaml", root=self.root)
        self.assertFalse(report.blocked)
        self.assertEqual(11, report.event_count)
        self.assertEqual(2, report.message_count)
        self.assertEqual(0, report.capture_gap_count)

    def test_event_sequence_gap_is_blocked(self) -> None:
        self._mutate_event("EVT-0004", lambda event: event.__setitem__("sequence", 5))
        self.assertIn("TRACE-SEQUENCE-GAP", self._codes())

    def test_unknown_actor_is_blocked(self) -> None:
        self._mutate_event("EVT-0004", lambda event: event.__setitem__("actor_id", "unknown-agent"))
        self.assertIn("TRACE-ACTOR-UNOWNED", self._codes())

    def test_read_outside_allowlist_is_blocked(self) -> None:
        def mutate(event: dict[str, Any]) -> None:
            event["target"] = {"kind": "file", "path": "README.md"}

        self._mutate_event("EVT-0004", mutate)
        self.assertIn("TRACE-READ-OUTSIDE-SCOPE", self._codes())

    def test_unlisted_tool_is_blocked(self) -> None:
        self._mutate_event("EVT-0005", lambda event: event["target"].__setitem__("id", "shell"))
        self.assertIn("TRACE-TOOL-OUTSIDE-SCOPE", self._codes())

    def test_transient_tool_result_without_retained_payload_is_blocked(self) -> None:
        self._mutate_event("EVT-0006", lambda event: event.pop("result_ref"))
        self.assertIn("TRACE-TRANSIENT-RESULT-MISSING", self._codes())

    def test_process_artifact_revision_cannot_silently_overwrite(self) -> None:
        def mutate(event: dict[str, Any]) -> None:
            event["details"]["operation"] = "modify"
            event["details"]["old_sha256"] = event["details"]["new_sha256"]

        self._mutate_event("EVT-0007", mutate)
        self.assertIn("TRACE-PROCESS-ARTIFACT-OVERWRITTEN", self._codes())

    def test_process_artifact_target_must_match_recorded_revision(self) -> None:
        self._mutate_event(
            "EVT-0007",
            lambda event: event["details"].__setitem__("new_sha256", "0" * 64),
        )
        self.assertIn("TRACE-PROCESS-ARTIFACT-OVERWRITTEN", self._codes())

    def test_message_events_must_match_sender_and_receiver(self) -> None:
        self._mutate_event("EVT-0002", lambda event: event.__setitem__("actor_id", "worker-agent"))
        self.assertIn("TRACE-MESSAGE-MISSING", self._codes())

    def test_external_action_requires_auditable_human_approval(self) -> None:
        envelope = self._load_yaml("TRACE.yaml")
        envelope["external_actions"] = "human-approved-only"
        self._write_yaml("TRACE.yaml", envelope)

        def mutate(event: dict[str, Any]) -> None:
            event["event_type"] = "external-action"
            event["target"] = {"kind": "external", "id": "github"}
            event["authorization"] = {"basis": "claimed approval", "allowed": True}

        self._mutate_event("EVT-0004", mutate)
        self.assertIn("TRACE-EXTERNAL-UNAUTHORIZED", self._codes())

    def test_message_visible_payload_hash_mismatch_is_blocked(self) -> None:
        message_path = self.fixture / "messages/0001-main-agent-to-worker-agent-assignment.md"
        text = message_path.read_text(encoding="utf-8")
        marker = "content_sha256: "
        prefix, rest = text.split(marker, 1)
        _, suffix = rest.split("\n", 1)
        message_path.write_text(prefix + marker + ("0" * 64) + "\n" + suffix, encoding="utf-8")
        index = self._load_yaml("INDEX.yaml")
        index["messages"][0]["content_ref"]["sha256"] = hash_file(message_path)
        self._write_yaml("INDEX.yaml", index)
        self._refresh_envelope()
        self.assertIn("TRACE-HASH-MISMATCH", self._codes())

    def test_capture_status_cannot_claim_an_unrecorded_gap(self) -> None:
        envelope = self._load_yaml("TRACE.yaml")
        envelope["capture_status"] = "gap-declared"
        self._write_yaml("TRACE.yaml", envelope)
        self.assertIn("TRACE-CAPTURE-STATUS-MISMATCH", self._codes())


if __name__ == "__main__":
    unittest.main()
