"""Joint entry/Session/Host/receipt/state proofs using an offline Provider port."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research_workbench.adapters.models import ContentBlock, FinishReason, ModelResponse
from research_workbench.artifacts.integrity import hash_file
from research_workbench.entry.executor import FrozenRoleBinding, FrozenRoleExecutor
from research_workbench.entry.guide import build_guide_request
from research_workbench.entry.state import publish_workflow_checkpoint
from research_workbench.entry.workflow import WorkflowBudget, run_research_workflow
from research_workbench.execution import CloseoutPin
from research_workbench.io import load_document
from research_workbench.scaffold import _protocol
from tests.execution_fixtures import ExecutionViewFixture, SequenceClock, plain
from tests.test_entry_driver import ScriptedRoleProvider, observe

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "work/TASK-MR-ES-FROZEN-001"


class ControlProvider(ScriptedRoleProvider):
    def generate(self, request):
        response = super().generate(request)
        return ModelResponse(response.response_id, response.provider, response.model,
            (ContentBlock("text", text=json.dumps({"decision": "complete", "delegations": [],
                "summary": "actual offline role output", "limitations": ["offline Provider port"],
                "next_actions": ["Human review of this stage."]})),), FinishReason.COMPLETE, usage=response.usage)


class EntryExecutorTests(unittest.TestCase):
    def prepare(self, root, provider, *, substitute=False):
        helper = ExecutionViewFixture()
        bundle, inputs = helper._build(root)
        view = helper._produce(root, bundle, inputs)
        path = root / "view/resolved.yaml"
        path.write_text(json.dumps(view), encoding="utf-8")
        main = plain(bundle.documents[(root/view["task_ref"]["path"]).resolve()])
        if substitute:
            main = copy.deepcopy(main)
            main["goal"] = "different requested goal"
        frozen = FrozenRoleBinding(CloseoutPin("bundle/manifest.yaml", hash_file(bundle.manifest_path)),
            CloseoutPin("view/resolved.yaml", hash_file(path)), provider, observe,
            PREFIX+"/archive", PREFIX+"/role.json", "deterministic-check-report", "JOINT-OFFLINE-001",
            schema_root=ROOT/"schemas",
            host_clock=SequenceClock("2026-08-26T00:00:01Z", "2026-08-26T00:00:02Z", "2026-08-26T00:00:03Z"),
            session_clock=lambda: 0.0)
        executor = FrozenRoleExecutor(root, binding_factory=lambda invocation: frozen,
                                      accountable_owner="offline joint test owner")
        result = run_research_workflow(root, directory=PREFIX+"/workflow", task=main, executor=executor,
            budget=WorkflowBudget(3, 10000, 100, 128, 60, 3, 2))
        return result, executor

    def test_joint_role_request_session_host_receipt_workflow_checkpoint_and_guide(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = ControlProvider()
            result, executor = self.prepare(root, provider)
            self.assertEqual("stage-completed", result.status, result.summary)
            self.assertEqual(1, result.model_calls)
            self.assertEqual(38, result.known_tokens)
            self.assertEqual(0, result.held_tokens)
            self.assertEqual(1, len(provider.requests))
            self.assertIn("delegations", provider.requests[0].messages[1].content[0].text)
            self.assertIsNotNone(executor.results[0].receipt_ref)
            self.assertFalse(result.task_completion)
            raw = json.dumps(_protocol("JOINT")).encode("utf-8")
            (root/"protocol.json").write_bytes(raw)
            protocol = {"path": "protocol.json", "sha256": hashlib.sha256(raw).hexdigest()}
            state_ref = publish_workflow_checkpoint(root, result=result, protocol_ref=protocol, checkpoint_id="JOINT-STATE",
                output=PREFIX+"/state.json", write_scope=[PREFIX+"/**"], created_at="2026-10-07T00:00:00Z")
            state = load_document(root/state_ref.path)
            self.assertEqual([], state["accepted_decisions"])
            self.assertIn(executor.results[0].receipt_ref.path, [r["path"] for r in state["machine_state_refs"]])
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            request = build_guide_request(root, question="Explain this stage", main_state_ref=state_ref, model="offline-model")
            self.assertEqual((), request.tools)
            self.assertEqual([state_ref.path], [r["path"] for r in json.loads(request.messages[1].content[0].text)["approved_inputs"]])
            self.assertEqual(before, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()})

    def test_failed_actual_send_is_one_call_and_full_unknown_hold_without_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            provider = ControlProvider(fail=True)
            result, executor = self.prepare(Path(temporary), provider)
            self.assertEqual("safe-paused", result.status)
            self.assertEqual(1, result.model_calls)
            self.assertEqual(228, result.held_tokens)
            self.assertIsNone(result.observations[0]["input_tokens"])
            self.assertEqual(1, len(provider.requests))
            self.assertEqual(0, executor.results[0].session.model_turns)
            self.assertIsNone(executor.results[0].receipt_ref)

    def test_exact_frozen_task_substitution_stops_before_provider(self):
        with tempfile.TemporaryDirectory() as temporary:
            provider = ControlProvider()
            result, executor = self.prepare(Path(temporary), provider, substitute=True)
            self.assertEqual("safe-paused", result.status)
            self.assertEqual([], provider.requests)
            self.assertEqual([], executor.results)
            self.assertGreater(result.held_tokens, 0)  # caller cannot infer whether a generic executor sent.

    def test_incomplete_host_zero_placeholders_preserve_unknown_reservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            unknown = SimpleNamespace(session=None, host_report_ref=CloseoutPin("retained/host.json", "1"*64),
                trace_ref=CloseoutPin("retained/trace.json", "2"*64), validation_ref=None, receipt_ref=None,
                closeout_error="driver exception", host_report={"status": "failed", "execution_phase": "driver-exception",
                    "actual_facts": {"complete": False, "provider_invocations": 0}})
            with patch("research_workbench.entry.executor.execute_role_slice", return_value=unknown):
                result, executor = self.prepare(Path(temporary), ControlProvider())
            self.assertEqual("safe-paused", result.status)
            self.assertEqual(228, result.held_tokens)
            self.assertEqual([], list(result.observations))
            self.assertEqual([unknown], executor.results)


if __name__ == "__main__":
    unittest.main()
