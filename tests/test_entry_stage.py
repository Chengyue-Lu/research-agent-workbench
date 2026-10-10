"""Actual offline caller records; these checks do not qualify model semantics."""
import copy
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from research_workbench.context.models import checkpoint_digest
from research_workbench.entry.handoff import publish_workflow_handoff
from research_workbench.entry.stage import assess_workflow_stage_evidence, publish_workflow_stage_evidence
from research_workbench.entry.state import publish_workflow_checkpoint
from research_workbench.entry.workflow import RoleObservation, WorkflowBudget, run_research_workflow
from research_workbench.scaffold import _protocol
from tests.test_entry_workflow import ScriptedExecutor, child, output, task


def _write(root, path, document):
    destination = root / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    return {"path": path, "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def make_stage_checkpoint(root, children=0, *, failed=False, unknown=False, legacy=False):
    protocol_ref = _write(root, "protocol.json", _protocol("STAGE"))
    early = json.loads(output("delegate", [child("C" + str(i)) for i in range(children)])) if children else json.loads(output())
    early["limitations"] = ["At this stage child results have not returned."] if children else ["Bounded native stub has no output Receipt."]
    responses = [json.dumps(early)]
    if children:
        for i in range(children):
            value = json.loads(output(summary="Child " + str(i) + " returned."))
            value.update(limitations=["Child scope limitation " + str(i)], unresolved=["Unresolved " + str(i)],
                         human_decision_required=["Human choice " + str(i)])
            responses.append(json.dumps(value))
        responses.append(output(summary="Fresh main returned."))
    if failed:
        responses[1 if children else 0] = RoleObservation("failed", output(), 1, 20, 15, limitations=("Actual failed slice",))
    if unknown:
        responses[1 if children else 0] = RuntimeError("Offline unknown outbound observation")
    result = run_research_workflow(root, directory="work/flow", task=task(), executor=ScriptedExecutor(responses),
        budget=WorkflowBudget(12, 10000, 100, 100, 60, 4, 2))
    if legacy:
        report = json.loads((root / result.report_ref["path"]).read_bytes())
        report.pop("journal_ref")
        report_ref = _write(root, result.report_ref["path"], report)
        result = replace(result, report_ref=report_ref)
    state_ref = publish_workflow_checkpoint(root, result=result, protocol_ref=protocol_ref,
        checkpoint_id="STAGE-STATE", output="work/state.json", write_scope=["work/**"], stage_evidence_output="work/stage.json")
    state = json.loads((root / state_ref.path).read_bytes())
    evidence_ref = next(ref for ref in state["machine_state_refs"] if ref["path"] == "work/stage.json")
    return state_ref, evidence_ref, list(state["machine_state_refs"])


class EntryStageTests(unittest.TestCase):
    def test_declared_source_revision_is_retained_and_checked_with_exact_hash(self):
        from research_workbench.entry.stage import _pin, _read
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = _write(root, "record.json", {"revision": 2, "fact": "bounded record"})
            reference["revision"] = 2
            self.assertEqual(reference, _pin(reference))
            self.assertEqual(2, _read(root, reference)["revision"])
            self.assertEqual((root / "record.json").read_bytes(), _read(root, reference, raw=True))
            with self.assertRaisesRegex(ValueError, "revision drift"):
                _read(root, {**reference, "revision": 3}, raw=True)

    def test_zero_one_and_variable_children_preserve_stage_negatives_and_actual_consumption(self):
        for count in (0, 1, 2):
            with self.subTest(children=count), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                state, evidence, grants = make_stage_checkpoint(root, count)
                document = json.loads((root / evidence["path"]).read_bytes())
                producer = json.loads((root / document["sources"]["final_producer_ref"]["path"]).read_bytes())
                # Native producer retains the optional null; the sidecar uses
                # the same exact pin with absent optional revision.
                self.assertIn("revision", producer["task_ref"])
                self.assertIsNone(producer["task_ref"]["revision"])
                self.assertNotIn("revision", document["sources"]["final_task_ref"])
                checked = assess_workflow_stage_evidence(root, main_state_ref=state, evidence_ref=evidence, verification_refs=grants)
                self.assertEqual("checked", checked["status"])
                self.assertEqual("source-checked", checked["qualification"])
                self.assertEqual(count + (2 if count else 1), len(checked["stages"]))
                self.assertEqual(count > 0, checked["stages"][-1]["child_results_consumed"])
                self.assertEqual(count, len(checked["stages"][-1]["input_child_task_ids"]))
                self.assertFalse(any("observation" in stage or "text" in stage for stage in checked["stages"]))
                if count:
                    self.assertIn("not returned", checked["stages"][0]["negative_items"]["limitations"][0])
                    self.assertIn("Unresolved 0", checked["final_observation"]["unresolved"])
                    self.assertIn("Human choice 0", checked["final_observation"]["human_decision_required"])
                self.assertEqual("safe-paused", checked["final_observation"]["handoff_status"])
                document = json.loads((root / evidence["path"]).read_bytes())
                self.assertFalse(document["human_acceptance"])
                self.assertFalse(document["task_completion"])

    def test_missing_source_grant_never_opens_source_and_legacy_report_is_unknown(self):
        import research_workbench.entry.stage as stage
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence, grants = make_stage_checkpoint(root)
            original = stage._read
            reads = []
            def observe(project, pin, **options):
                reads.append(stage._pin(pin)["path"])
                return original(project, pin, **options)
            with mock.patch.object(stage, "_read", side_effect=observe):
                assessment = assess_workflow_stage_evidence(root, main_state_ref=state, evidence_ref=evidence)
            self.assertEqual("not-checked", assessment["status"])
            self.assertEqual([state.path, evidence["path"]], reads)
            self.assertTrue(assessment["missing_verification_refs"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence, grants = make_stage_checkpoint(root, legacy=True)
            assessment = assess_workflow_stage_evidence(root, main_state_ref=state, evidence_ref=evidence, verification_refs=grants)
            self.assertEqual("unknown", assessment["status"])
            self.assertEqual([], assessment["stages"])

    def test_failed_and_unknown_dispatches_do_not_invent_success_or_consumption(self):
        for options in ({"failed": True}, {"unknown": True}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                state, evidence, grants = make_stage_checkpoint(root, 2, **options)
                assessment = assess_workflow_stage_evidence(root, main_state_ref=state, evidence_ref=evidence, verification_refs=grants)
                self.assertEqual("safe-paused", assessment["final_observation"]["status"])
                self.assertTrue(assessment["final_observation"]["unstarted_tasks"])
                self.assertFalse(any(stage["child_results_consumed"] for stage in assessment["stages"]))
                self.assertIn("failed" if options.get("failed") else "unknown", [stage["execution_status"] for stage in assessment["stages"]])

    def test_hash_and_even_rehashed_phase_tamper_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_ref, evidence_ref, grants = make_stage_checkpoint(root)
            stage_document = json.loads((root / evidence_ref["path"]).read_bytes())
            stage_document["stages"][0]["phase"] = "consume-child-results"
            _write(root, evidence_ref["path"], stage_document)
            with self.assertRaisesRegex(ValueError, "hash drift"):
                assess_workflow_stage_evidence(root, main_state_ref=state_ref, evidence_ref=evidence_ref, verification_refs=grants)
            changed_evidence = _write(root, evidence_ref["path"], stage_document)
            state = json.loads((root / state_ref.path).read_bytes())
            state["machine_state_refs"] = [changed_evidence if ref["path"] == changed_evidence["path"] else ref for ref in state["machine_state_refs"]]
            state["checkpoint_digest"] = checkpoint_digest(state)
            changed_state = _write(root, state_ref.path, state)
            with self.assertRaisesRegex(ValueError, "canonical content drift"):
                assess_workflow_stage_evidence(root, main_state_ref=changed_state, evidence_ref=changed_evidence, verification_refs=grants)

    def test_producer_scope_duplicate_and_journal_hash_drift_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = run_research_workflow(root, directory="work/flow", task=task(), executor=ScriptedExecutor([output()]),
                budget=WorkflowBudget(12, 10000, 100, 100, 60, 4, 2))
            handoff = publish_workflow_handoff(root, result=result)
            args = dict(result=result, handoff_ref=handoff, output="work/stage.json", write_scope=["work/**"])
            with self.assertRaisesRegex(ValueError, "write scope"):
                publish_workflow_stage_evidence(root, **{**args, "output": "outside.json"})
            publish_workflow_stage_evidence(root, **args)
            with self.assertRaises(FileExistsError):
                publish_workflow_stage_evidence(root, **args)
            report = json.loads((root / result.report_ref["path"]).read_bytes())
            (root / report["journal_ref"]["path"]).write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash drift"):
                publish_workflow_stage_evidence(root, **{**args, "output": "work/drift-stage.json"})
            self.assertFalse((root / "work/drift-stage.json").exists())
