"""Actual offline intake/factory/Host/Receipt/Handoff wave consumers.

Injected Providers and supplied conformance evidence are explicit test ports,
not live qualification. Product code does not import these fixture helpers.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.adapters.models import ContentBlock, FinishReason, ModelResponse
from research_workbench.entry.caller import run_frozen_intake_workflow
from research_workbench.entry.handoff import consume_compact_handoff, workflow_handoff_observation
from research_workbench.entry.intake_call import IntakeCallBudget, call_intake
from research_workbench.entry.workflow import WorkflowBudget
from research_workbench.execution import PinnedExecutionInput, load_runtime_bundle, validate_generic_execution_receipt
from research_workbench.io import load_document
from research_workbench.scaffold import _protocol
from tests.entry_chain_support import PREFIX
from tests.entry_factory_support import FactoryTestInputs
from tests.test_entry_caller import CallerRoleProvider
from tests.test_entry_driver import ScriptedRoleProvider
from tests.test_entry_intake_call import IntakeProvider


class NestedWaveProvider(CallerRoleProvider):
    def generate(self, request):
        base = ScriptedRoleProvider.generate(self, request)
        payload = json.loads(request.messages[1].content[0].text)
        node, context = payload["task"], payload["caller_context"]
        control = {"decision": "complete", "delegations": [], "summary": "Bounded nested result.",
                   "limitations": ["Offline test evidence only."], "next_actions": ["Human review."]}
        if context["phase"] == "plan-or-execute":
            children = []
            if request.metadata["entry_role"] == "main":
                for index in (0, 1):
                    child = copy.deepcopy(node)
                    child["task_id"] = "CALLER-CHILD-" + str(index)
                    child["budget"] = copy.deepcopy(node["delegation"]["sub_budget"])
                    child["write_scope"] = [f"{PREFIX}/child-{index}/**"]
                    child["delegation"] = ({"allowed": True, "max_depth": 1, "max_parallel": 1,
                        "sub_budget": {"max_turns": 1, "max_output_tokens": 256, "max_seconds": 30}}
                        if index == 0 else {"allowed": False, "max_depth": 0, "max_parallel": 0})
                    children.append({"task": child})
            elif node["task_id"] == "CALLER-CHILD-0":
                child = copy.deepcopy(node)
                child["task_id"] = "GRANDCHILD"
                child["budget"] = copy.deepcopy(node["delegation"]["sub_budget"])
                child["write_scope"] = [f"{PREFIX}/child-0/grandchild/**"]
                child["delegation"] = {"allowed": False, "max_depth": 0, "max_parallel": 0}
                children.append({"task": child})
            if children:
                control.update(decision="delegate", delegations=children)
        else:
            control["summary"] = "Consumed " + ", ".join(item["task_id"] for item in context["child_results"])
        return ModelResponse(base.response_id, base.provider, base.model,
            (ContentBlock("text", text=json.dumps(control)),), FinishReason.COMPLETE, usage=base.usage)


class FailedChildProvider(CallerRoleProvider):
    def generate(self, request):
        if request.metadata["entry_role"] == "child":
            self.requests.append(request)
            raise RuntimeError("Actual offline child send failed.")
        return super().generate(request)


def prepare_wave(root, *, turns=2, children=1, provider=None):
    provider = provider or CallerRoleProvider(children)
    inputs = FactoryTestInputs(root, provider)
    inputs.task["budget"]["max_turns"] = turns
    inputs.task["delegation"]["sub_budget"]["max_turns"] = min(3, turns)
    protocol = _protocol("OFFLINE-WAVE")
    protocol["active_modes"] = inputs.task["active_modes"]
    protocol["question_refs"] = inputs.task["question_refs"]
    protocol["budgets"].update(max_parallel_subagents=3, max_delegation_depth=2)
    intake_provider = IntakeProvider()
    intake = call_intake(root, intake_task=inputs.task,
        intake_profile=load_document(root / inputs.options["profile_pin"].path),
        protocol_ceiling=protocol, task_ceiling=inputs.task, provider=intake_provider,
        model="bounded-local-model", directory=PREFIX + "/intake",
        budget=IntakeCallBudget(100, 128, 10000, 60),
        context={"approved_method": inputs.method, "requirements": [inputs.requirement]}, clock=lambda: 0.0)
    refs = {Path(ref.path).name: ref for ref in intake.draft_refs}
    factory = inputs.build_factory(**{keyword: PinnedExecutionInput(refs[name].path, refs[name].sha256)
        for name, keyword in (("task.json", "task_pin"), ("method.json", "method_pin"),
                              ("requirement-1.json", "requirement_pin"))})
    provider.task = copy.deepcopy(factory.root_task)
    return intake_provider, intake, factory, provider


def run_wave(root, intake, factory, *, calls=8, tokens=10000):
    return run_frozen_intake_workflow(root, intake_result=intake, binding_factory=factory,
        directory=PREFIX + "/workflow", budget=WorkflowBudget(calls, tokens, 100, 128, 120, 3, 2),
        accountable_owner="offline wave consumer", deadline_monotonic=120, clock=lambda: 0.0)


class EntryWaveBridgeTests(unittest.TestCase):
    def _replay(self, root, result, factory):
        report = load_document(root / result.workflow.report_ref["path"])
        self.assertIsNotNone(result.handoff_ref, result.reason)
        observation = workflow_handoff_observation(report, root)
        observation["artifact_refs"].append(dict(result.workflow.report_ref))
        consume_compact_handoff(root, result.handoff_ref, expected_task=report["task"],
            expected_attempt_id=report["attempt_id"], expected_observation=observation)
        for record in factory.records:
            observation = next(item for item in report["observations"] if item["ordinal"] == record["ordinal"])
            receipt = observation["receipt_refs"][0]
            bundle = load_runtime_bundle(record["bundle"]["path"], project_root=root)
            validated = validate_generic_execution_receipt(receipt["path"], expected_sha256=receipt["sha256"], bundle=bundle)
            self.assertFalse(validated.document["boundaries"]["task_completion"])

    def test_exact_call_and_token_capacity_consumes_actual_child_handoff(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intake_provider, intake, factory, provider = prepare_wave(root)
            result = run_wave(root, intake, factory, calls=4, tokens=532)
            self.assertEqual("stage-completed", result.workflow.status, result.workflow.summary)
            self.assertEqual(4, result.workflow.model_calls)
            self.assertEqual(152, result.workflow.known_tokens)
            self.assertEqual(0, result.workflow.held_tokens)
            self.assertEqual((1, 3, 3), (len(intake_provider.requests), len(provider.requests), len(factory.records)))
            consumed = json.loads(provider.requests[-1].messages[1].content[0].text)["caller_context"]["child_results"]
            self.assertEqual("CALLER-CHILD-0", consumed[0]["handoff"]["task_id"])
            self.assertEqual(1, len(consumed[0]["receipt_refs"]))
            self._replay(root, result, factory)

    def test_parent_turn_shortage_stops_before_child_factory_and_preserves_intake(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intake_provider, intake, factory, provider = prepare_wave(root, turns=1)
            result = run_wave(root, intake, factory)
            self.assertEqual("safe-paused", result.workflow.status)
            self.assertEqual(("CALLER-CHILD-0",), result.workflow.unstarted_tasks)
            self.assertEqual((2, 76, 0), (result.workflow.model_calls, result.workflow.known_tokens, result.workflow.held_tokens))
            self.assertEqual((1, 1, 1), (len(intake_provider.requests), len(provider.requests), len(factory.records)))
            self._replay(root, result, factory)

    def test_global_call_and_token_shortage_stop_before_all_children(self):
        for calls, tokens in ((3, 10000), (8, 531)):
            with self.subTest(calls=calls, tokens=tokens), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                _, intake, factory, provider = prepare_wave(root)
                result = run_wave(root, intake, factory, calls=calls, tokens=tokens)
                self.assertEqual("safe-paused", result.workflow.status)
                self.assertEqual(("CALLER-CHILD-0",), result.workflow.unstarted_tasks)
                self.assertEqual((2, 76, 0), (result.workflow.model_calls, result.workflow.known_tokens, result.workflow.held_tokens))
                self.assertEqual((1, 1), (len(provider.requests), len(factory.records)))
                self._replay(root, result, factory)

    def test_nested_child_preserves_root_consumer_and_pending_sibling(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, intake, factory, provider = prepare_wave(root, turns=4, provider=NestedWaveProvider())
            result = run_wave(root, intake, factory, calls=7)
            self.assertEqual("stage-completed", result.workflow.status, result.workflow.summary)
            self.assertEqual((7, 266, 0), (result.workflow.model_calls, result.workflow.known_tokens, result.workflow.held_tokens))
            self.assertEqual([factory.root_task["task_id"], "CALLER-CHILD-0", "GRANDCHILD", "CALLER-CHILD-0",
                              "CALLER-CHILD-1", factory.root_task["task_id"]], [request.metadata["task_id"] for request in provider.requests])
            child_method = load_document(root / factory.records[1]["method"]["path"])
            grandchild_method = load_document(root / factory.records[2]["method"]["path"])
            self.assertEqual(child_method["limitations"], grandchild_method["limitations"])
            self.assertEqual("GRANDCHILD", grandchild_method["task_ref"]["task_id"])
            self.assertNotEqual(child_method["task_ref"]["sha256"], grandchild_method["task_ref"]["sha256"])
            self._replay(root, result, factory)

    def test_nested_shortage_preserves_all_unstarted_and_actual_prior_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, intake, factory, provider = prepare_wave(root, turns=4, provider=NestedWaveProvider())
            result = run_wave(root, intake, factory, calls=6)
            self.assertEqual("safe-paused", result.workflow.status)
            self.assertEqual({"GRANDCHILD", "CALLER-CHILD-1"}, set(result.workflow.unstarted_tasks))
            self.assertEqual((3, 114, 0), (result.workflow.model_calls, result.workflow.known_tokens, result.workflow.held_tokens))
            self.assertEqual((2, 2), (len(provider.requests), len(factory.records)))
            self._replay(root, result, factory)

    def test_actual_failed_child_holds_only_its_slice_not_future_reservations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, intake, factory, provider = prepare_wave(root, turns=4, provider=FailedChildProvider(3))
            result = run_wave(root, intake, factory)
            self.assertEqual("safe-paused", result.workflow.status)
            self.assertEqual((3, 76, 228), (result.workflow.model_calls, result.workflow.known_tokens, result.workflow.held_tokens))
            self.assertEqual(("CALLER-CHILD-1", "CALLER-CHILD-2"), result.workflow.unstarted_tasks)
            self.assertEqual(2, len(provider.requests))
            self.assertTrue(all(json.loads(request.messages[1].content[0].text)["caller_context"]["phase"] == "plan-or-execute"
                                for request in provider.requests))
