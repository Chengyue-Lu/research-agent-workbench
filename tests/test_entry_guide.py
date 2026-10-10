import hashlib
import json
import copy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research_workbench.adapters.models.port import (
    Capability, ContentBlock, FinishReason, ModelResponse, ProviderCapabilities,
    ProviderRegistry, ToolCall, Usage,
)
from research_workbench.entry.guide import ask_guide, build_guide_request
from research_workbench.entry.roles import EntryInputError
from research_workbench.tasks.models import FileReference


class OfflineGuideProvider:
    def capabilities(self):
        return ProviderCapabilities("offline-guide", "test-only", frozenset({Capability.TEXT}),
                                    models=("offline-model",), deployment="local")

    def generate(self, request):
        self.request = request
        return ModelResponse("guide-test", "offline-guide", "offline-model",
                             (ContentBlock("text", text="MainState is waiting."),), FinishReason.COMPLETE,
                             tool_calls=(ToolCall("unexpected", "write-state", {}),),
                             usage=Usage(input_tokens=None, output_tokens=9))


class EntryGuideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        state = {"schema_version": "0.1.0", "checkpoint_id": "CP-GUIDE", "continuity_status": "waiting",
                 "project_protocol_ref": "project-protocol.json", "current_questions": [], "pinned_constraints": [],
                 "accepted_decisions": [], "active_tasks": [], "recent_handoffs": [], "open_conflicts": [],
                 "open_risks": ["human review pending"], "next_actions": ["ask human"], "artifact_index_refs": [],
                 "machine_state_refs": [{"path": "not-approved.json", "sha256": "0" * 64}]}
        raw = json.dumps(state).encode("utf-8")
        (self.root / "main-state.json").write_bytes(raw)
        self.ref = FileReference("main-state.json", hashlib.sha256(raw).hexdigest())
        (self.root / "main-chat.txt").write_text("private old main history", encoding="utf-8")

    def stage_checkpoint(self, *, legacy=False):
        from research_workbench.entry.state import publish_workflow_checkpoint
        from research_workbench.entry.workflow import WorkflowBudget, run_research_workflow
        from research_workbench.scaffold import _protocol
        from tests.test_entry_workflow import ScriptedExecutor, child, output, task

        initial = json.loads(output("delegate", [child("REVIEW")]))
        initial["limitations"] = ["child review pending at initial planning"]
        actual_child = json.loads(output(summary="actual separate child observation"))
        actual_child.update(limitations=["measurement unavailable"], unresolved=["beta remains unresolved"],
                            human_decision_required=["Human chooses whether beta is needed."])
        final = json.loads(output(summary="new main returned after receiving the child"))
        final["limitations"] = ["driver publication pending at model-time"]
        result = run_research_workflow(self.root, directory="work/flow", task=task(),
            executor=ScriptedExecutor([json.dumps(initial), json.dumps(actual_child), json.dumps(final)]),
            budget=WorkflowBudget(12, 10000, 100, 100, 60, 4, 2))
        if legacy:
            report_path = self.root / result.report_ref["path"]
            report = json.loads(report_path.read_bytes())
            report.pop("journal_ref")
            raw = json.dumps(report).encode("utf-8")
            report_path.write_bytes(raw)
            result = replace(result, report_ref={"path": result.report_ref["path"],
                                               "sha256": hashlib.sha256(raw).hexdigest()})
        protocol_raw = json.dumps(_protocol("GUIDE-STAGE")).encode("utf-8")
        (self.root / "protocol.json").write_bytes(protocol_raw)
        state_ref = publish_workflow_checkpoint(self.root, result=result,
            protocol_ref={"path": "protocol.json", "sha256": hashlib.sha256(protocol_raw).hexdigest()},
            checkpoint_id="GUIDE-STAGES", output="work/state.json", write_scope=["work/**"],
            stage_evidence_output="work/stage.json")
        state = json.loads((self.root / state_ref.path).read_bytes())
        stage_ref = FileReference.from_mapping(next(ref for ref in state["machine_state_refs"]
                                                   if ref["path"] == "work/stage.json"))
        # The test caller explicitly grants these generated fixture pins. Guide
        # does not infer such permission from their appearance in MainState.
        return state_ref, stage_ref, tuple(state["machine_state_refs"])

    def stage_request(self, state_ref, stage_ref, verification_refs=()):
        return build_guide_request(self.root, question="Explain the recorded stages", main_state_ref=state_ref,
            approved_refs=(stage_ref,), stage_evidence_ref=stage_ref,
            verification_refs=verification_refs, model="offline-model")

    def test_guide_only_consumes_approved_snapshot_without_following_refs(self):
        request = build_guide_request(self.root, question="Why waiting?", main_state_ref=self.ref,
                                      model="offline-model")
        self.assertEqual((), request.tools)
        self.assertEqual(2, len(request.messages))
        payload = json.loads(request.messages[1].content[0].text)
        self.assertEqual(["main-state.json"], [item["path"] for item in payload["approved_inputs"]])
        self.assertNotIn("private old main history", request.messages[1].content[0].text)
        self.assertFalse((self.root / "not-approved.json").exists())
        self.assertNotIn("stage_evidence_assessment", payload)

    def test_stage_snapshot_requires_exact_explicit_read_grant(self):
        raw = b'{"source":"not authorized by this reference alone"}'
        (self.root / "stage.json").write_bytes(raw)
        stage = FileReference("stage.json", hashlib.sha256(raw).hexdigest())
        wrong_pin = FileReference("stage.json", "0" * 64)
        # MainState's machine refs and a caller-supplied stage selector do not
        # authorize a read. Reject even before encountering this bad MainState.
        for approved in ((), (wrong_pin,)):
            with self.subTest(approved=approved), self.assertRaisesRegex(
                    EntryInputError, "exact approved input pin"):
                build_guide_request(self.root, question="Explain", main_state_ref=wrong_pin,
                    approved_refs=approved, stage_evidence_ref=stage, model="offline-model")

    def test_stage_snapshot_hash_drift_blocks_before_source_preflight(self):
        stage = FileReference("stage.json", hashlib.sha256(b"original").hexdigest())
        (self.root / stage.path).write_bytes(b"changed")
        with self.assertRaisesRegex(EntryInputError, "input hash mismatch"):
            build_guide_request(self.root, question="Explain", main_state_ref=self.ref,
                approved_refs=(stage,), stage_evidence_ref=stage, model="offline-model")

    def test_verification_refs_cannot_form_an_implicit_stage_or_model_input(self):
        raw = b"private verification original"
        (self.root / "verification.txt").write_bytes(raw)
        source = FileReference("verification.txt", hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(EntryInputError, "require stage evidence"):
            build_guide_request(self.root, question="Explain", main_state_ref=self.ref,
                verification_refs=(source,), model="offline-model")

    def test_checked_stages_use_actual_sources_without_extra_model_snapshots(self):
        state_ref, stage_ref, verification = self.stage_checkpoint()
        secret = b"unrelated private verification original"
        (self.root / "verification.txt").write_bytes(secret)
        unused = FileReference("verification.txt", hashlib.sha256(secret).hexdigest())
        original_read = Path.read_bytes

        def guard(path):
            if path.resolve() == (self.root / unused.path).resolve():
                self.fail("unused verification grant was read")
            return original_read(path)

        with patch.object(Path, "read_bytes", new=guard):
            request = self.stage_request(state_ref, stage_ref, (*verification, unused))
        payload = json.loads(request.messages[1].content[0].text)
        self.assertEqual([state_ref.path, stage_ref.path], [item["path"] for item in payload["approved_inputs"]])
        self.assertNotIn("verification_refs", payload)
        self.assertNotIn(secret.decode(), request.messages[1].content[0].text)
        facts = payload["stage_evidence_assessment"]
        self.assertEqual("checked", facts["status"])
        self.assertEqual("source-checked", facts["qualification"])
        self.assertNotIn("stages", facts)
        self.assertNotIn("final_observation", facts)
        stage = json.loads(payload["approved_inputs"][1]["text"])
        self.assertEqual(["plan-or-execute", "plan-or-execute", "consume-child-results"],
                         [item["phase"] for item in stage["stages"]])
        self.assertEqual(["MAIN", "REVIEW", "MAIN"], [item["task_id"] for item in stage["stages"]])
        self.assertTrue(stage["stages"][-1]["child_results_consumed"])
        self.assertIn("child review pending at initial planning", stage["stages"][0]["negative_items"]["limitations"])
        self.assertIn("beta remains unresolved", stage["final_observation"]["unresolved"])
        self.assertEqual("safe-paused", stage["final_observation"]["handoff_status"])
        self.assertNotIn(unused.path, [ref["path"] for ref in facts["checked_refs"]])
        self.assertEqual(hashlib.sha256(request.messages[1].content[0].text.encode()).hexdigest(),
                         request.metadata["input_snapshot_sha256"])
        self.assertEqual((), request.tools)

    def test_missing_source_grants_do_not_open_visible_machine_refs(self):
        state_ref, stage_ref, verification = self.stage_checkpoint()
        forbidden = {(self.root / ref["path"]).resolve() for ref in verification if ref["path"] != stage_ref.path}
        original_read = Path.read_bytes

        def guard(path):
            if path.resolve() in forbidden:
                self.fail("source was opened without an explicit verification read grant")
            return original_read(path)

        with patch.object(Path, "read_bytes", new=guard):
            request = self.stage_request(state_ref, stage_ref)
        facts = json.loads(request.messages[1].content[0].text)["stage_evidence_assessment"]
        self.assertEqual("not-checked", facts["status"])
        self.assertTrue(facts["missing_verification_refs"])
        self.assertNotIn("stages", facts)

    def test_forged_stage_or_source_pin_cannot_replace_actual_source_records(self):
        from research_workbench.context.models import checkpoint_digest

        state_ref, stage_ref, verification = self.stage_checkpoint()
        original_state = json.loads((self.root / state_ref.path).read_bytes())
        original_stage = json.loads((self.root / stage_ref.path).read_bytes())
        for corruption in ("stage", "source", "authority"):
            stage = copy.deepcopy(original_stage)
            if corruption == "stage":
                stage["stages"][0]["ordinal"] = 99
            elif corruption == "source":
                stage["sources"]["report_ref"]["sha256"] = "0" * 64
            else:
                stage["human_acceptance"] = True
            raw = json.dumps(stage).encode("utf-8")
            (self.root / stage_ref.path).write_bytes(raw)
            false_stage = FileReference(stage_ref.path, hashlib.sha256(raw).hexdigest())
            state = copy.deepcopy(original_state)
            for ref in state["machine_state_refs"]:
                if ref["path"] == stage_ref.path:
                    ref["sha256"] = false_stage.sha256
            state["checkpoint_digest"] = checkpoint_digest(state)
            state_raw = json.dumps(state).encode("utf-8")
            (self.root / state_ref.path).write_bytes(state_raw)
            false_state = FileReference(state_ref.path, hashlib.sha256(state_raw).hexdigest())
            with self.subTest(corruption=corruption), self.assertRaises(EntryInputError):
                self.stage_request(false_state, false_stage, verification)

    def test_source_hash_drift_blocks_before_provider_generation(self):
        state_ref, stage_ref, verification = self.stage_checkpoint()
        stage = json.loads((self.root / stage_ref.path).read_bytes())
        (self.root / stage["sources"]["report_ref"]["path"]).write_bytes(b"{}")
        provider, registry = OfflineGuideProvider(), ProviderRegistry()
        registry.register("offline-guide", provider)
        with self.assertRaisesRegex(EntryInputError, "hash drift"):
            ask_guide(self.root, providers=registry, provider_name="offline-guide", question="Explain",
                main_state_ref=state_ref, approved_refs=(stage_ref,), stage_evidence_ref=stage_ref,
                verification_refs=verification, model="offline-model")
        self.assertFalse(hasattr(provider, "request"))

    def test_old_report_without_journal_is_unknown_and_not_reconstructed(self):
        state_ref, stage_ref, verification = self.stage_checkpoint(legacy=True)
        request = self.stage_request(state_ref, stage_ref, verification)
        facts = json.loads(request.messages[1].content[0].text)["stage_evidence_assessment"]
        self.assertEqual("unknown", facts["status"])
        self.assertNotIn("stages", facts)
        self.assertEqual([], json.loads(json.loads(request.messages[1].content[0].text)
                                       ["approved_inputs"][1]["text"])["stages"])
        self.assertTrue(facts["limitations"])

    def test_checked_stage_ask_returns_actual_usage_without_project_writes_or_tools(self):
        state_ref, stage_ref, verification = self.stage_checkpoint()
        before = {path.relative_to(self.root).as_posix(): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        provider, registry = OfflineGuideProvider(), ProviderRegistry()
        registry.register("offline-guide", provider)
        response = ask_guide(self.root, providers=registry, provider_name="offline-guide", question="Explain",
            main_state_ref=state_ref, approved_refs=(stage_ref,), stage_evidence_ref=stage_ref,
            verification_refs=verification, model="offline-model")
        self.assertEqual("checked", json.loads(provider.request.messages[1].content[0].text)
                         ["stage_evidence_assessment"]["status"])
        self.assertEqual(9, response.usage.output_tokens)
        self.assertIsNone(response.usage.input_tokens)
        self.assertEqual((), provider.request.tools)
        self.assertEqual(before, {path.relative_to(self.root).as_posix(): path.read_bytes()
                                 for path in self.root.rglob("*") if path.is_file()})

    def test_injected_call_returns_unknown_usage_and_does_not_write_or_execute_tools(self):
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        provider, registry = OfflineGuideProvider(), ProviderRegistry()
        registry.register("offline-guide", provider)
        response = ask_guide(self.root, providers=registry, provider_name="offline-guide",
                             question="Explain the checkpoint", main_state_ref=self.ref, model="offline-model")
        self.assertEqual(9, response.usage.output_tokens)
        self.assertIsNone(response.usage.input_tokens)
        self.assertEqual((), provider.request.tools)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.root.iterdir()})

    def test_bad_pin_and_invalid_mainstate_block_before_provider_call(self):
        with self.assertRaises(EntryInputError):
            build_guide_request(self.root, question="Explain", main_state_ref=FileReference(self.ref.path, "0" * 64),
                                model="offline-model")
        raw = b"{}"
        (self.root / "main-state.json").write_bytes(raw)
        with self.assertRaises(EntryInputError):
            build_guide_request(self.root, question="Explain", main_state_ref=FileReference(self.ref.path, hashlib.sha256(raw).hexdigest()),
                                model="offline-model")


if __name__ == "__main__":
    unittest.main()
