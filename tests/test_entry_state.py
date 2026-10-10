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
            handoff_path = first_data["recent_handoffs"][-1]["ref"]
            self.assertNotEqual(result.report_ref["path"], handoff_path)
            formal = json.loads((root / handoff_path).read_bytes())
            self.assertEqual("safe-paused", formal["status"])  # no validated output Receipt in this native stub
            self.assertEqual(formal["status"], first_data["continuity_status"])
            self.assertEqual(formal["status"], first_data["active_tasks"][-1]["status"])
            self.assertIn(formal["producer_ref"]["path"], [ref["path"] for ref in first_data["machine_state_refs"]])
            second = publish_workflow_checkpoint(root, result=result, protocol_ref=protocol, checkpoint_id="STATE2",
                output="work/state2.json", write_scope=["work/**"], previous_state_ref={"path": first.path, "sha256": first.sha256})
            data = json.loads((root/second.path).read_bytes())
            self.assertEqual(first.path, data["previous_checkpoint_ref"])
            self.assertEqual([], data["accepted_decisions"])
            self.assertEqual(tuple(formal["recommended_next_actions"]), tuple(data["next_actions"]))

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

    def test_child_negative_items_survive_main_completion_and_checkpoint(self):
        from tests.test_entry_workflow import child
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol = root / "protocol.json"
            protocol.write_text(json.dumps(_protocol("P")), encoding="utf-8")
            protocol_pin = {"path": "protocol.json", "sha256": hashlib.sha256(protocol.read_bytes()).hexdigest()}
            actual_child = json.loads(output(summary="Child slice complete."))
            actual_child.update(limitations=["beta measurement unavailable"],
                conflicts=[{"topic": "beta", "status": "unknown"}], unresolved=["beta is unresolved"],
                human_decision_required=["Choose whether beta is needed."])
            executor = ScriptedExecutor([output("delegate", [child("C")]), json.dumps(actual_child), output()])
            result = run_research_workflow(root, directory="work/flow", task=task(), executor=executor,
                budget=WorkflowBudget(12, 10000, 100, 100, 60, 4, 2))
            checkpoint = publish_workflow_checkpoint(root, result=result, protocol_ref=protocol_pin,
                checkpoint_id="NEGATIVE-STATE", output="work/state.json", write_scope=["work/**"])
            state = json.loads((root / checkpoint.path).read_bytes())
            self.assertIn("beta measurement unavailable", state["open_risks"])
            self.assertIn("beta is unresolved", state["open_risks"])
            self.assertIn("beta", " ".join(state["open_conflicts"]))
            self.assertIn("Choose whether beta is needed.", state["next_actions"])
            self.assertEqual([], state["accepted_decisions"])
            formal = json.loads((root / state["recent_handoffs"][-1]["ref"]).read_bytes())
            self.assertEqual("safe-paused", formal["status"])
            self.assertEqual("safe-paused", state["continuity_status"])
            self.assertEqual(1, formal["unresolved"].count("Required output contracts not verified: handoff-packet"))
            self.assertIn("beta is unresolved", formal["unresolved"])
            child_result = executor.invocations[-1].context["child_results"][0]
            self.assertIn(child_result["handoff_ref"]["path"], [ref["path"] for ref in state["machine_state_refs"]])

    def test_optional_stage_publication_adds_exact_refs_without_changing_acceptance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol, result = self.prepare(root)
            ref = publish_workflow_checkpoint(root, result=result, protocol_ref=protocol, checkpoint_id="STAGE",
                output="work/state.json", write_scope=["work/**"], stage_evidence_output="work/stage.json")
            state = json.loads((root / ref.path).read_bytes())
            stage_pin = next(pin for pin in state["machine_state_refs"] if pin["path"] == "work/stage.json")
            self.assertEqual(stage_pin["sha256"], hashlib.sha256((root / stage_pin["path"]).read_bytes()).hexdigest())
            stage = json.loads((root / stage_pin["path"]).read_bytes())
            self.assertIn(stage["sources"]["journal_ref"], state["machine_state_refs"])
            self.assertIn(stage_pin["path"], state["artifact_index_refs"])
            self.assertEqual([], state["accepted_decisions"])
            self.assertTrue(state["open_risks"])
            for output_path in ("outside-stage.json", "work/state2.json"):
                with self.subTest(path=output_path), self.assertRaises(ValueError):
                    publish_workflow_checkpoint(root, result=result, protocol_ref=protocol, checkpoint_id="BAD",
                        output="work/state2.json", write_scope=["work/**"], stage_evidence_output=output_path)


if __name__ == "__main__":
    unittest.main()
