import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from research_workbench.context.models import MainStatePacket
from research_workbench.entry.state import publish_workflow_checkpoint
from research_workbench.entry.workflow import WorkflowBudget, run_research_workflow
from research_workbench.scaffold import _protocol
from tests.test_entry_workflow import ScriptedExecutor, output, task


class EntryStateTests(unittest.TestCase):
    def prepare(self, root):
        protocol = root/"protocol.json"
        protocol.write_text(json.dumps(_protocol("P")), encoding="utf-8")
        pin = {"path": "protocol.json", "sha256": hashlib.sha256(protocol.read_bytes()).hexdigest()}
        result = run_research_workflow(root, directory="work/flow", task=task(),
            executor=ScriptedExecutor([output()]), budget=WorkflowBudget(12, 10000, 100, 100, 60, 4, 2))
        return pin, result

    def test_first_checkpoint_and_manual_successor_preserve_decisions_and_references(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol, result = self.prepare(root)
            first = publish_workflow_checkpoint(root, result=result, protocol_ref=protocol, checkpoint_id="STATE1",
                output="work/state1.json", write_scope=["work/**"], created_at="2026-10-07T12:00:00Z")
            first_data = json.loads((root/first.path).read_bytes())
            MainStatePacket.from_mapping(first_data)
            self.assertEqual([], first_data["accepted_decisions"])
            second = publish_workflow_checkpoint(root, result=result, protocol_ref=protocol, checkpoint_id="STATE2",
                output="work/state2.json", write_scope=["work/**"], previous_state_ref={"path": first.path, "sha256": first.sha256})
            data = json.loads((root/second.path).read_bytes())
            self.assertEqual(first.path, data["previous_checkpoint_ref"])
            self.assertEqual([], data["accepted_decisions"])
            self.assertEqual(result.next_actions, tuple(data["next_actions"]))

    def test_no_overwrite_and_scope_or_result_drift_blocks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol, result = self.prepare(root)
            kwargs = dict(result=result, protocol_ref=protocol, checkpoint_id="S", output="work/state.json", write_scope=["work/**"])
            publish_workflow_checkpoint(root, **kwargs)
            original = (root/"work/state.json").read_bytes()
            with self.assertRaises(FileExistsError):
                publish_workflow_checkpoint(root, **kwargs)
            self.assertEqual(original, (root/"work/state.json").read_bytes())
            with self.assertRaisesRegex(ValueError, "write scope"):
                publish_workflow_checkpoint(root, **dict(kwargs, output="outside.json"))
            (root/result.report_ref["path"]).write_text("{}")
            with self.assertRaisesRegex(ValueError, "hash drift"):
                publish_workflow_checkpoint(root, **dict(kwargs, output="work/new.json"))

    def test_all_result_fields_must_match_hash_pinned_report_before_state_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol, result = self.prepare(root)
            original_report = (root/result.report_ref["path"]).read_bytes()
            changes = {
                "next_actions": ("tampered action absent from pinned report",),
                "limitations": ("invented risk",), "disposition": "human-review",
                "summary": "invented summary", "known_tokens": result.known_tokens+1,
                "held_tokens": 1, "model_calls": result.model_calls+1,
                "unstarted_tasks": ("invented child",), "task_completion": True,
                "human_acceptance": True,
                "observations": ({**result.observations[0], "text": "tampered actual response"},),
            }
            for field, value in changes.items():
                destination = f"work/tampered-{field}.json"
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "does not match retained workflow"):
                    publish_workflow_checkpoint(root, result=replace(result, **{field: value}),
                        protocol_ref=protocol, checkpoint_id="TAMPER", output=destination, write_scope=["work/**"])
                self.assertFalse((root/destination).exists())
            self.assertEqual(original_report, (root/result.report_ref["path"]).read_bytes())


if __name__ == "__main__":
    unittest.main()
