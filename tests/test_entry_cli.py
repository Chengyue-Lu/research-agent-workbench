import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.cli import main
from tests.test_entry_intake import control_documents


class EntryCliTests(unittest.TestCase):
    def test_draft_publishes_checked_outputs_and_rejects_expansion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol, task = control_documents()
            for name, document in (("protocol.json", protocol), ("task.json", task),
                ("response.json", {"protocol": protocol, "task": task, "unknowns": []})):
                (root/name).write_text(json.dumps(document), encoding="utf-8")
            args = ["entry", "draft", "--root", str(root), "--response", "response.json",
                    "--protocol-ceiling", "protocol.json", "--task-ceiling", "task.json", "--output-directory", "drafts/run1"]
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = main(args)
            self.assertEqual(0, code, stream.getvalue())
            report = json.loads(stream.getvalue())
            self.assertEqual("draft", report["status"])
            for ref in report["artifacts"]:
                self.assertEqual(ref["sha256"], hashlib.sha256((root/ref["path"]).read_bytes()).hexdigest())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(2, main(args))  # exclusive publication
            task["permissions"]["network"] = "allowed"
            (root/"response.json").write_text(json.dumps({"protocol": protocol, "task": task, "unknowns": []}), encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(2, main(args[:-1]+["drafts/run2"]))
            self.assertFalse((root/"drafts/run2").exists())

    def test_guide_preview_has_no_disk_side_effect_or_provider_send_and_rejects_bad_pin(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = {"schema_version": "0.1.0", "checkpoint_id": "CLI", "continuity_status": "waiting",
                "project_protocol_ref": "protocol.json", "current_questions": [], "pinned_constraints": [],
                "accepted_decisions": [], "active_tasks": [], "recent_handoffs": [], "open_conflicts": [],
                "open_risks": [], "next_actions": ["Human review"], "artifact_index_refs": [],
                "machine_state_refs": [{"path": "protocol.json", "sha256": "0"*64}]}
            path = root/"state.json"
            path.write_text(json.dumps(state), encoding="utf-8")
            before = path.read_bytes()
            args = ["entry", "guide-preview", "--root", str(root), "--state", "state.json", "--state-sha256",
                hashlib.sha256(before).hexdigest(), "--question", "What needs review?", "--model", "offline-model"]
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = main(args)
            self.assertEqual(0, code, stream.getvalue())
            request = json.loads(stream.getvalue())
            self.assertEqual("guide", request["metadata"]["entry_role"])
            self.assertEqual([], request["tools"])
            self.assertEqual(before, path.read_bytes())
            args[args.index("--state-sha256")+1] = "0"*64
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(2, main(args))


if __name__ == "__main__":
    unittest.main()
