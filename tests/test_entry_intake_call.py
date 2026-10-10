"""Actual intake port to exact control products and bounded role consumption."""
import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from research_workbench.adapters.models import ContentBlock, FinishReason, ModelResponse, ProviderRegistry
from research_workbench.entry.executor import FrozenRoleExecutor
from research_workbench.entry.guide import ask_guide
from research_workbench.entry.intake_call import IntakeCallBudget, call_intake
from research_workbench.entry.state import publish_workflow_checkpoint
from research_workbench.entry.workflow import WorkflowBudget, run_research_workflow
from research_workbench.execution import PinnedExecutionInput
from research_workbench.io import load_document
from research_workbench.scaffold import _protocol
from tests.entry_chain_support import OfflineRoleFactory, PREFIX
from tests.test_entry_bridge_flow import DynamicProvider
from tests.test_entry_driver import ScriptedRoleProvider


class IntakeProvider(ScriptedRoleProvider):
    def __init__(self, variant="valid", *, remote=False):
        super().__init__(deployment="remote" if remote else "local")
        self.variant = variant

    def generate(self, request):
        base = super().generate(request)
        if self.variant == "failed-send":
            raise RuntimeError("offline send failure")
        payload = json.loads(request.messages[1].content[0].text)["caller_context"]
        proposal = copy.deepcopy(payload["control_ceilings"])
        proposal.update(method=payload["context"]["approved_method"], requirements=payload["context"]["requirements"],
                        unknowns=["No live source qualification in the offline synthetic test."])
        if self.variant == "permissions":
            proposal["task"]["permissions"]["network"] = "arbitrary"
        text = "not JSON" if self.variant == "invalid-json" else json.dumps(proposal)
        reason = FinishReason.LENGTH if self.variant == "length" else FinishReason.COMPLETE
        return ModelResponse(base.response_id, base.provider, base.model,
            (ContentBlock("text", text=text),), reason, usage=base.usage)


class EntryIntakeCallTests(unittest.TestCase):
    def _inputs(self, root):
        factory = OfflineRoleFactory(root, DynamicProvider())
        protocol = _protocol("SYNTHETIC-CONTROL-CALL")
        protocol["active_modes"] = factory.task["active_modes"]
        protocol["question_refs"] = factory.task["question_refs"]
        protocol["budgets"].update(max_parallel_subagents=3, max_delegation_depth=2)
        profile = load_document(root / factory.inputs["agent_profile"].path)
        context = {"approved_method": factory.seed_method, "requirements": [load_document(root / "bundle/requirement.yaml")]}
        return factory, protocol, profile, context

    def _call(self, root, provider, **kwargs):
        factory, protocol, profile, context = self._inputs(root)
        options = dict(intake_task=factory.task, intake_profile=profile, protocol_ceiling=protocol,
            task_ceiling=factory.task, provider=provider, model="bounded-local-model", directory=PREFIX + "/intake",
            budget=IntakeCallBudget(100, 128, 10000, 60), context=context, clock=lambda: 0.0)
        options.update(kwargs)
        return factory, call_intake(root, **options)

    def test_model_intake_exact_products_dynamic_child_closeout_checkpoint_and_actual_guide(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intake_provider = IntakeProvider()
            factory, intake = self._call(root, intake_provider)
            self.assertEqual("success", intake.status, intake.details)
            self.assertEqual(1, intake.model_calls)
            self.assertEqual((30, 8, 0), (intake.input_tokens, intake.output_tokens, intake.held_tokens))
            refs = {Path(ref.path).name: ref for ref in intake.draft_refs}
            factory.task = load_document(root / refs["task.json"].path)
            factory.seed_method = load_document(root / refs["method.json"].path)
            factory.published_controls = {name: PinnedExecutionInput(ref.path, ref.sha256) for name, ref in refs.items()}
            provider = DynamicProvider(1)
            provider.factory = factory
            factory.provider = provider
            executor = FrozenRoleExecutor(root, binding_factory=factory, accountable_owner="offline full bridge test owner")
            workflow = run_research_workflow(root, directory=PREFIX + "/workflow", task=factory.task, executor=executor,
                budget=WorkflowBudget(4, 10000, 100, 128, 120, 3, 2), clock=lambda: 0.0,
                prior_usage=(intake.as_role_observation(),))
            self.assertEqual("stage-completed", workflow.status, workflow.summary)
            self.assertEqual(4, workflow.model_calls)
            self.assertEqual(152, workflow.known_tokens)
            self.assertEqual(0, workflow.held_tokens)
            self.assertEqual(["main", "child", "main"], [request.metadata["entry_role"] for request in provider.requests])
            for index in (0, 2):
                view = load_document(root / factory.bindings[index].view_ref.path)
                self.assertEqual(refs["task.json"].path, view["task_ref"]["path"])
                self.assertEqual(refs["task.json"].sha256, view["task_ref"]["sha256"])
            self.assertTrue(all(result.receipt_ref for result in executor.results))
            state = publish_workflow_checkpoint(root, result=workflow, protocol_ref=refs["project-protocol.json"],
                checkpoint_id="INTAKE-CONTROL-STATE", output=PREFIX + "/mainstate.json", write_scope=[PREFIX + "/**"],
                created_at="2026-10-07T00:00:00Z")
            before = {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            registry = ProviderRegistry()
            guide = ScriptedRoleProvider()
            registry.register("local", guide)
            response = ask_guide(root, providers=registry, provider_name="local", question="Explain the retained state.",
                main_state_ref=state, model="bounded-local-model")
            self.assertEqual(1, len(guide.requests))
            self.assertEqual("guide", guide.requests[0].metadata["entry_role"])
            self.assertEqual((), guide.requests[0].tools)
            self.assertEqual(30, response.usage.input_tokens)
            self.assertEqual(before, {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()})
            self.assertFalse(workflow.task_completion)
            self.assertFalse(workflow.human_acceptance)

    def test_invalid_or_incomplete_or_permission_expanding_model_output_is_retained_without_draft(self):
        for variant in ("invalid-json", "length", "permissions"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                provider = IntakeProvider(variant)
                _, result = self._call(root, provider)
                self.assertIn(result.status, {"rejected", "failed"})
                self.assertEqual(1, result.model_calls)
                self.assertEqual((30, 8), (result.input_tokens, result.output_tokens))
                self.assertEqual((), result.draft_refs)
                self.assertTrue((root / (PREFIX + "/intake/response.json")).is_file())
                self.assertFalse((root / (PREFIX + "/intake/draft/draft.json")).exists())

    def test_failed_send_preserves_request_actual_call_and_full_unknown_hold_without_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = IntakeProvider("failed-send")
            _, result = self._call(root, provider)
            self.assertEqual("failed", result.status)
            self.assertEqual(1, result.model_calls)
            self.assertEqual(1, len(provider.requests))
            self.assertEqual(228, result.held_tokens)
            self.assertIsNone(result.input_tokens)
            self.assertIsNone(result.output_tokens)
            self.assertTrue((root / (PREFIX + "/intake/request.json")).is_file())
            self.assertIsNotNone(result.report_ref)

    def test_dispatch_denied_or_remote_policy_denied_preserves_zero_actual_calls(self):
        for variant in ("guard", "remote"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                provider = IntakeProvider(remote=variant == "remote")
                _, result = self._call(Path(temporary), provider,
                    **({"before_dispatch": lambda request: False} if variant == "guard" else {}))
                self.assertIn(result.status, {"not-started", "rejected"})
                self.assertEqual(0, result.model_calls)
                self.assertEqual(0, result.held_tokens)
                self.assertEqual([], provider.requests)

    def test_outside_write_scope_creates_no_report_or_provider_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = IntakeProvider()
            _, result = self._call(root, provider, directory="outside/intake")
            self.assertEqual("rejected", result.status)
            self.assertIsNone(result.report_ref)
            self.assertEqual([], provider.requests)
            self.assertFalse((root / "outside").exists())


if __name__ == "__main__":
    unittest.main()
