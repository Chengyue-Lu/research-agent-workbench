"""Verify the archived M5 capture adapter with synthetic, isolated spools."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_workbench.observability.trace import AgentTraceRecorder

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / (
    "docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/"
    "attempts/M5-006-IMPLEMENTATION-001/export_capture.py"
)
SPEC = importlib.util.spec_from_file_location("m5_delayed_capture_export", EXPORTER)
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)

H4_EXPORTER = ROOT / (
    "docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/"
    "attempts/M5-007-H4-001/export_capture.py"
)
H4_SPEC = importlib.util.spec_from_file_location("m5_h4_delayed_capture_export", H4_EXPORTER)
H4_EXPORT = importlib.util.module_from_spec(H4_SPEC)
H4_SPEC.loader.exec_module(H4_EXPORT)


class M5TraceExportTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "docs").mkdir()
        (self.root / "docs/TASKS.md").write_text(
            "# Synthetic development task\n| M5-006 | READY | synthetic fixture |\n",
            encoding="utf-8",
        )
        self.spool = self.root / ".rwb/m5-006"
        self.spool.mkdir(parents=True)
        self.attempt = self.spool / "M5-006-SYNTHETIC-001"

    def invoke(self, *, attempt: str | None = None, script: bool = False) -> dict:
        argv = [str(EXPORTER), "--root", str(self.root), "--attempt", attempt or ".rwb/m5-006/M5-006-SYNTHETIC-001"]
        output = io.StringIO()
        with patch("sys.argv", argv), patch("subprocess.check_output", return_value="a" * 40 + "\n"), contextlib.redirect_stdout(output):
            if script:
                runpy.run_path(str(EXPORTER), run_name="__main__")
            else:
                EXPORT.main()
        return json.loads(output.getvalue())

    def write_spool(self, rows: list[dict]) -> None:
        (self.spool / "capture-synthetic.json").write_text(json.dumps(rows), encoding="utf-8")

    def test_cli_preserves_payload_bytes_gaps_and_observed_outcomes(self) -> None:
        self.write_spool([
            {"tool": "exec_command", "arguments": {"cmd": "synthetic success"}, "result": {"status": "fulfilled", "value": {"exit_code": 0, "output": "fixture\r\n"}}},
            {"tool": "exec_command", "result": {"exit_code": 1, "output": "synthetic failure"}},
            {"tool": "exec_command", "result": {"session_id": 1}},
            {"tool": "apply_patch", "result": {}},
            {"tool": "apply_patch", "arguments": "synthetic patch", "result": "unclassified result"},
            {"tool": "exec_command", "arguments": {"cmd": "missing result"}},
            {"tool": "exec_command", "result": {"status": "fulfilled"}},
        ])
        raw_evidence = b"synthetic diagnostic evidence\r\n"
        (self.spool / "focused-tests.log").write_bytes(raw_evidence)
        result = self.invoke(script=True)
        self.assertFalse(result["blocked"], result)
        self.assertEqual(["TRACE-CAPTURE-DELAYED"], [risk["code"] for risk in result["risks"]])
        events = [json.loads(line) for line in (self.attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        calls = [event["payload"] for event in events if event["event_type"] == "tool-call"]
        self.assertEqual(["succeeded", "failed", "attempted", "unknown", "unknown"], [call["status"] for call in calls])
        self.assertEqual(["shell", "shell", "shell", "apply_patch", "apply_patch"], [call["tool_name"] for call in calls])
        self.assertEqual({"patch": "synthetic patch"}, calls[-1]["arguments"])
        first_result = json.loads((self.attempt / calls[0]["result_ref"]["path"]).read_text(encoding="utf-8"))
        self.assertEqual("fixture\r\n", first_result["output"])
        missing = json.loads((self.attempt / "evidence/calls-with-uncaptured-results.json").read_text(encoding="utf-8"))
        self.assertEqual(["delayed-capture-0006", "delayed-capture-0007"], [row["operation_id"] for row in missing])
        self.assertTrue({row["operation_id"] for row in missing}.isdisjoint(call["operation_id"] for call in calls))
        self.assertEqual(raw_evidence, (self.attempt / "evidence/focused-tests.log").read_bytes())
        self.assertEqual(EXPORTER.read_bytes(), (self.attempt / "export_capture.py").read_bytes())
        self.assertIn("Delayed export initialized", events[0]["payload"]["reason"])
        self.assertEqual("incomplete", events[-1]["payload"]["to_status"])

    def test_empty_spool_remains_explicitly_gapped(self) -> None:
        result = self.invoke()
        self.assertFalse(result["blocked"], result)
        events = [json.loads(line) for line in (self.attempt / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertFalse(any(event["event_type"] == "tool-call" for event in events))
        self.assertTrue(any(event["event_type"] == "capture-gap" for event in events))

    def test_existing_or_escaping_archive_is_rejected_without_overwrite(self) -> None:
        self.attempt.mkdir(parents=True)
        sentinel = self.attempt / "sentinel.txt"
        sentinel.write_bytes(b"retain me")
        for target in (".rwb/m5-006/M5-006-SYNTHETIC-001", "../outside-archive"):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "new path inside"):
                self.invoke(attempt=target)
        self.assertEqual(b"retain me", sentinel.read_bytes())

    def test_post_seal_evidence_corruption_produces_block_and_nonzero_exit(self) -> None:
        self.write_spool([{"tool": "exec_command", "result": {"exit_code": 0}}])
        original_seal = AgentTraceRecorder.seal

        def corrupt_after_seal(recorder, *args, **kwargs):
            result = original_seal(recorder, *args, **kwargs)
            result_path = next((self.attempt / "tool-events").glob("*.json"))
            result_path.write_bytes(result_path.read_bytes() + b" ")
            return result

        with patch.object(AgentTraceRecorder, "seal", corrupt_after_seal), self.assertRaises(SystemExit) as raised:
            self.invoke()
        self.assertEqual(1, raised.exception.code)
        report = json.loads((self.attempt / "trace-validation.json").read_text(encoding="utf-8"))
        self.assertTrue(report["blocked"])
        self.assertTrue(any(risk["level"] == "block" for risk in report["risks"]))


class H4TraceExportTests(unittest.TestCase):
    """Execute archived code without rewriting the frozen implementation Attempt."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.archive = self.root / H4_EXPORTER.parent.relative_to(ROOT)
        self.archive.mkdir(parents=True)
        self.script = self.archive / H4_EXPORTER.name
        self.script.write_bytes(H4_EXPORTER.read_bytes())
        (self.root / "docs/TASKS.md").write_text(
            "# Synthetic Task index\n| M5-007 | IN_PROGRESS | synthetic fixture |\n",
            encoding="utf-8",
        )
        (self.root / ".rwb").mkdir()
        self.write_spool([])

    def write_spool(self, rows):
        (self.root / ".rwb/h4-capture.json").write_text(json.dumps(rows), encoding="utf-8")

    def invoke(self, *, script=False):
        output = io.StringIO()
        with patch.object(Path, "cwd", return_value=self.root), \
             patch("subprocess.check_output", return_value="b" * 40 + "\n"), \
             patch.object(H4_EXPORT, "__file__", str(self.script)), contextlib.redirect_stdout(output):
            if script:
                # Run the exact archived CLI code with a disposable __file__.
                # The canonical code filename lets CI measure the real subject;
                # its bytes and behavior are unchanged, including SystemExit.
                with self.assertRaises(SystemExit) as raised:
                    exec(compile(H4_EXPORTER.read_bytes(), str(H4_EXPORTER), "exec"),
                         {"__name__": "__main__", "__file__": str(self.script)})
                status = raised.exception.code
            else:
                status = H4_EXPORT.main()
        return status, json.loads(output.getvalue())

    def events(self):
        return [json.loads(line) for line in (self.archive / "trace/events.jsonl")
                .read_text(encoding="utf-8").splitlines()]

    def test_cli_preserves_observed_results_outcomes_and_task_binding(self):
        rows = [
            {"tool": "exec_command", "arguments": {"cmd": "synthetic success"},
             "result": {"exit_code": 0, "output": "synthetic\r\n"}},
            {"tool": "exec_command", "arguments": {}, "result": {"exit_code": 1}},
            {"tool": "write_stdin", "arguments": {"session_id": 7}, "result": {"session_id": 7}},
            {"tool": "apply_patch", "arguments": {"patch": "synthetic patch"}, "result": {}},
            {"tool": "apply_patch", "arguments": {}, "result": "unclassified result"},
        ]
        self.write_spool(rows)
        status, report = self.invoke(script=True)
        self.assertEqual(status, 0)
        self.assertFalse(report["blocked"])
        self.assertEqual([r["code"] for r in report["risks"]], ["TRACE-CAPTURE-DELAYED"])
        events = self.events()
        calls = [e["payload"] for e in events if e["event_type"] == "tool-call"]
        self.assertEqual([c["status"] for c in calls], ["succeeded", "failed", "attempted", "unknown", "unknown"])
        self.assertEqual([c["tool_name"] for c in calls], ["shell", "shell", "shell", "apply_patch", "apply_patch"])
        for row, call in zip(rows, calls):
            result = json.loads((self.archive / "trace" / call["result_ref"]["path"]).read_text(encoding="utf-8"))
            self.assertEqual(result, row["result"])
            self.assertEqual(call["arguments"], row["arguments"])
        import yaml
        task = yaml.safe_load((self.archive / "trace/TASK.yaml").read_text(encoding="utf-8"))
        self.assertEqual(task["task_id"], "M5-007")
        self.assertEqual(task["implementation_head"], "b" * 40)
        self.assertIn("Delayed H4a export", events[0]["payload"]["reason"])
        self.assertEqual(events[-1]["payload"]["to_status"], "incomplete")
        self.assertEqual(self.script.read_bytes(), H4_EXPORTER.read_bytes())

    def test_empty_spool_preserves_explicit_event_and_message_gaps(self):
        status, report = self.invoke()
        self.assertEqual(status, 0)
        self.assertFalse(report["blocked"])
        events = self.events()
        self.assertFalse(any(e["event_type"] == "tool-call" for e in events))
        gaps = [e for e in events if e["event_type"] == "capture-gap"]
        self.assertEqual(len(gaps), 2)
        self.assertTrue(all(e["task_id"] == "M5-007" for e in events))

    def test_existing_or_escaping_archive_is_rejected_without_writes(self):
        trace = self.archive / "trace"
        trace.mkdir()
        sentinel = trace / "sentinel.txt"
        sentinel.write_bytes(b"retained original bytes")
        with self.assertRaisesRegex(ValueError, "fresh trace directory"):
            self.invoke()
        outside = self.root.parent / "outside-h4-export.py"
        with patch.object(Path, "cwd", return_value=self.root), \
             patch.object(H4_EXPORT, "__file__", str(outside)), \
             patch("subprocess.check_output", side_effect=AssertionError("Git must not run")):
            with self.assertRaisesRegex(ValueError, "within the worktree"):
                H4_EXPORT.main()
        self.assertEqual(sentinel.read_bytes(), b"retained original bytes")
        self.assertFalse((self.archive / "trace-validation.json").exists())

    def test_post_seal_tampering_blocks_cli_and_persists_failure_report(self):
        self.write_spool([{"tool": "exec_command", "arguments": {}, "result": {"exit_code": 0}}])
        seal = AgentTraceRecorder.seal

        def corrupt_after_seal(recorder, *args, **kwargs):
            result = seal(recorder, *args, **kwargs)
            path = next((self.archive / "trace/tool-events").glob("*.json"))
            path.write_bytes(path.read_bytes() + b" ")
            return result

        with patch.object(AgentTraceRecorder, "seal", corrupt_after_seal):
            status, report = self.invoke(script=True)
        self.assertEqual(status, 1)
        self.assertTrue(report["blocked"])
        self.assertTrue(any(r["level"] == "block" for r in report["risks"]))
        self.assertEqual(json.loads((self.archive / "trace-validation.json").read_text()), report)
