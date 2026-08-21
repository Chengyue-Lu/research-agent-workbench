from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.observability.trace import AgentTraceRecorder, validate_attempt_trace

try:
    from hypothesis import given, settings, strategies as st
except ImportError:  # Optional dev dependency; CI installs project[test].
    given = settings = st = None

HAS_HYPOTHESIS = given is not None
if not HAS_HYPOTHESIS:
    class _DummyStrategies:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    def _dummy_decorator(*args, **kwargs):
        return lambda function: function

    given = settings = _dummy_decorator
    st = _DummyStrategies()


def _recorder(root: Path) -> AgentTraceRecorder:
    return AgentTraceRecorder(
        root / "work/T/AT-PROP",
        task_id="T",
        task_revision=1,
        attempt_id="AT-PROP",
        task_snapshot={"task_id": "T", "revision": 1},
        accountable_owner="property-test-owner",
        actor_id="runtime-property",
        runtime_identity="property-test",
        provider="scripted",
        read_allowlist=("inputs/**",),
        write_scope=("outputs/**",),
        tool_allowlist=(),
    )


@unittest.skipUnless(HAS_HYPOTHESIS, "install project[test] for Hypothesis state-space tests")
class TracePropertyTests(unittest.TestCase):
    @settings(max_examples=20, deadline=None)
    @given(st.integers(min_value=2, max_value=500))
    def test_any_non_contiguous_event_sequence_is_blocked(self, bad_sequence: int) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = _recorder(root)
            recorder.seal("safe-paused")
            events_path = recorder.attempt_dir / "events.jsonl"
            lines = events_path.read_text(encoding="utf-8").splitlines()
            import json

            event = json.loads(lines[-1])
            event["sequence"] = bad_sequence + len(lines)
            lines[-1] = json.dumps(event)
            events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            index_path = recorder.attempt_dir / "INDEX.yaml"
            index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
            index["event_ledger"]["sha256"] = hashlib.sha256(events_path.read_bytes()).hexdigest()
            index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")
            codes = {risk.code for risk in validate_attempt_trace(root, recorder.attempt_dir).risks}
            self.assertIn("TRACE-EVENT-SEQUENCE", codes)

    @settings(max_examples=20, deadline=None)
    @given(st.integers(min_value=1, max_value=8))
    def test_any_parent_path_escape_is_blocked(self, depth: int) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = _recorder(root)
            recorder.seal("safe-paused")
            index_path = recorder.attempt_dir / "INDEX.yaml"
            index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
            index["task_ref"]["path"] = "../" * depth + "outside.yaml"
            index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")
            codes = {risk.code for risk in validate_attempt_trace(root, recorder.attempt_dir).risks}
            self.assertIn("TRACE-PATH-ESCAPE", codes)

    @settings(max_examples=20, deadline=None)
    @given(st.binary(min_size=1, max_size=32))
    def test_any_message_byte_append_breaks_hash_binding(self, suffix: bytes) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = _recorder(root)
            recorder.record("provider-request", {"request": {"model": "test"}})
            recorder.seal("safe-paused")
            message = next((recorder.attempt_dir / "messages").iterdir())
            message.write_bytes(message.read_bytes() + suffix)
            codes = {risk.code for risk in validate_attempt_trace(root, recorder.attempt_dir).risks}
            self.assertIn("TRACE-HASH-DRIFT", codes)


if __name__ == "__main__":
    unittest.main()
