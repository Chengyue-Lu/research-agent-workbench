"""Published-intake provenance and shared-budget package caller tests.

All Providers/evidence are explicit offline test ports. These checks establish
bounded engineering behavior, never live qualification or scientific acceptance.
"""
import copy
import json
import tempfile
import unittest
from unittest import mock
from dataclasses import replace
from pathlib import Path

from research_workbench.adapters.models import ContentBlock, FinishReason, ModelResponse
from research_workbench.entry.caller import run_frozen_intake_workflow
from research_workbench.entry.intake_call import IntakeCallBudget, call_intake
from research_workbench.entry.workflow import WorkflowBudget, run_research_workflow
from research_workbench.execution import PinnedExecutionInput, load_runtime_bundle, validate_generic_execution_receipt
from research_workbench.io import load_document
from research_workbench.scaffold import _protocol
from tests.entry_chain_support import PREFIX, write_document
from tests.entry_factory_support import FactoryTestInputs
from tests.test_entry_driver import ScriptedRoleProvider
from tests.test_entry_intake_call import IntakeProvider


class CallerRoleProvider(ScriptedRoleProvider):
    def __init__(self, children=0):
        super().__init__()
        self.children = children
        self.task = None

    def generate(self, request):
        base = super().generate(request)
        payload = json.loads(request.messages[1].content[0].text)
        context = payload["caller_context"]
        control = {"decision": "complete", "delegations": [],
                   "summary": "Offline bounded observation.", "limitations": ["No live qualification."],
                   "next_actions": ["Human review remains separate."]}
        if request.metadata["entry_role"] == "main" and context["phase"] == "plan-or-execute" and self.children:
            children = []
            for index in range(self.children):
                child = copy.deepcopy(self.task)
                child["task_id"] = "CALLER-CHILD-" + str(index)
                child["budget"] = copy.deepcopy(self.task["delegation"]["sub_budget"])
                child["delegation"] = {"allowed": False, "max_depth": 0, "max_parallel": 0}
                child["write_scope"] = [f"{PREFIX}/child-{index}/**"]
                children.append({"task": child})
            control.update(decision="delegate", delegations=children)
        elif context["phase"] == "consume-child-results":
            control["summary"] = "Consumed " + str(len(context["child_results"])) + " actual child results."
        return ModelResponse(base.response_id, base.provider, base.model,
            (ContentBlock("text", text=json.dumps(control)),), FinishReason.COMPLETE, usage=base.usage)


class EntryCallerTests(unittest.TestCase):
    def prepare(self, root, *, intake_variant="valid", children=0, external_requirement=False):
        provider = CallerRoleProvider(children)
        inputs = FactoryTestInputs(root, provider)
        protocol = _protocol("OFFLINE-CALLER")
        protocol["active_modes"] = inputs.task["active_modes"]
        protocol["question_refs"] = inputs.task["question_refs"]
        protocol["budgets"].update(max_parallel_subagents=3, max_delegation_depth=2)
        intake = call_intake(root, intake_task=inputs.task,
            intake_profile=load_document(root / inputs.options["profile_pin"].path),
            protocol_ceiling=protocol, task_ceiling=inputs.task,
            provider=IntakeProvider(intake_variant), model="bounded-local-model",
            directory=PREFIX + "/intake", budget=IntakeCallBudget(100, 128, 10000, 60),
            context={"approved_method": inputs.method,
                     "requirements": [] if external_requirement else [inputs.requirement]},
            clock=lambda: 0.0)
        refs = {Path(ref.path).name: ref for ref in intake.draft_refs}
        options = {}
        for name, keyword in (("task.json", "task_pin"), ("method.json", "method_pin"),
                              ("requirement-1.json", "requirement_pin")):
            if name in refs:
                options[keyword] = PinnedExecutionInput(refs[name].path, refs[name].sha256)
        factory = inputs.build_factory(**options)
        provider.task = copy.deepcopy(factory.root_task)
        return inputs, intake, factory, provider

    def run_caller(self, root, intake, factory, **options):
        defaults = dict(intake_result=intake, binding_factory=factory,
            directory=PREFIX + "/workflow", budget=WorkflowBudget(8, 10000, 100, 128, 120, 3, 2),
            accountable_owner="offline caller test", deadline_monotonic=120, clock=lambda: 0.0)
        defaults.update(options)
        return run_frozen_intake_workflow(root, **defaults)

    def test_actual_intake_products_zero_one_three_children_and_receipt_cold_replay(self):
        for children in (0, 1, 3):
            with self.subTest(children=children), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                _, intake, factory, provider = self.prepare(root, children=children)
                result = self.run_caller(root, intake, factory)
                self.assertIsNotNone(result.workflow, result.reason)
                workflow = result.workflow
                self.assertEqual("stage-completed", workflow.status, workflow.summary)
                expected = 2 if children == 0 else children + 3
                self.assertEqual(expected, workflow.model_calls)
                self.assertEqual(38 * expected, workflow.known_tokens)
                self.assertEqual(0, workflow.held_tokens)
                self.assertEqual(expected - 1, len(provider.requests))
                self.assertTrue(result.intake_report_verified)
                self.assertEqual((), result.external_control_refs)
                self.assertFalse(result.task_completion)
                self.assertFalse(result.human_acceptance)
                if children:
                    payload = json.loads(provider.requests[-1].messages[1].content[0].text)
                    actual = payload["caller_context"]["child_results"]
                    self.assertEqual(children, len(actual))
                    self.assertTrue(all(len(child["receipt_refs"]) == 1 for child in actual))
                for record in factory.records:
                    receipt = next(item for item in workflow.observations
                        if item["ordinal"] == record["ordinal"])["receipt_refs"][0]
                    # Follow only the actual record pins, never workspace discovery.
                    bundle_ref = record["bundle"]
                    bundle = load_runtime_bundle(bundle_ref["path"], project_root=root)
                    validated = validate_generic_execution_receipt(receipt["path"],
                        expected_sha256=receipt["sha256"], bundle=bundle)
                    self.assertFalse(validated.document["boundaries"]["task_completion"])
                self.assertTrue(all(ref in result.artifact_refs for ref in intake.artifact_refs))

    def test_explicit_external_requirement_keeps_distinct_producer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, intake, factory, _ = self.prepare(root, external_requirement=True)
            result = self.run_caller(root, intake, factory)
            self.assertEqual("stage-completed", result.workflow.status, result.workflow.summary)
            self.assertEqual(inputs.requirement_pin.path, result.external_control_refs[0].path)
            self.assertNotIn(result.external_control_refs[0], intake.draft_refs)

    def test_failed_rejected_and_unknown_intake_never_dispatch_or_reset_hold(self):
        for variant in ("invalid-json", "length", "failed-send"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                _, intake, factory, provider = self.prepare(root, intake_variant=variant)
                result = self.run_caller(root, intake, factory)
                self.assertIsNone(result.workflow)
                self.assertIs(result.intake, intake)
                self.assertEqual([], provider.requests)
                self.assertFalse((root / (PREFIX + "/workflow")).exists())
                self.assertTrue(result.intake_report_verified, result.reason)
                if variant == "failed-send":
                    self.assertEqual(228, result.intake.held_tokens)
                    self.assertIsNone(result.intake.input_tokens)

    def test_report_result_substitution_and_published_control_drift_stop_before_dispatch(self):
        for variant in ("usage", "status", "task-drift", "seed-task"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                inputs, intake, factory, provider = self.prepare(root)
                if variant == "usage":
                    intake = replace(intake, input_tokens=31)
                elif variant == "status":
                    intake = replace(intake, status="partial")
                elif variant == "task-drift":
                    (root / factory.task_pin.path).write_text("{}", encoding="utf-8")
                else:
                    factory = inputs.build_factory(method_pin=factory.method_pin,
                                                   requirement_pin=factory.requirement_pin)
                result = self.run_caller(root, intake, factory)
                self.assertIsNone(result.workflow, result.reason)
                self.assertEqual([], provider.requests)
                self.assertFalse((root / (PREFIX + "/workflow")).exists())

    def test_external_requirement_must_be_requested_by_actual_task_and_method(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, intake, factory, provider = self.prepare(root, external_requirement=True)
            changed = copy.deepcopy(inputs.requirement)
            changed["requirement_id"] = "undeclared-capability"
            pin = write_document(root, "controls/undeclared-requirement.json", changed)
            factory = inputs.build_factory(task_pin=factory.task_pin, method_pin=factory.method_pin,
                                           requirement_pin=pin)
            result = self.run_caller(root, intake, factory)
            self.assertIsNone(result.workflow)
            self.assertIn("REQUIREMENT-NOT-DECLARED", result.reason)
            self.assertEqual([], provider.requests)

    def test_deadline_cancellation_and_total_call_budget_are_not_restarted_after_intake(self):
        for variant in ("deadline", "cancel", "calls"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                _, intake, factory, provider = self.prepare(root)
                options = {"deadline_monotonic": 0} if variant == "deadline" else (
                    {"cancel_requested": lambda: True} if variant == "cancel" else
                    {"budget": WorkflowBudget(1, 10000, 100, 128, 120, 3, 2)})
                result = self.run_caller(root, intake, factory, **options)
                self.assertIsNone(result.workflow)
                self.assertEqual([], provider.requests)
                self.assertEqual(38, result.intake.input_tokens + result.intake.output_tokens)

    def test_remaining_deadline_and_successful_intake_usage_are_shared_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, intake, factory, _ = self.prepare(root)
            with mock.patch("research_workbench.entry.caller.run_research_workflow",
                            wraps=run_research_workflow) as dispatch:
                result = self.run_caller(root, intake, factory, deadline_monotonic=30,
                                         clock=lambda: 20.0,
                                         budget=WorkflowBudget(2, 266, 100, 128, 120, 3, 2))
            self.assertIsNotNone(result.workflow, result.reason)
            self.assertEqual("stage-completed", result.workflow.status, result.workflow.summary)
            self.assertEqual(2, result.workflow.model_calls)
            self.assertEqual(76, result.workflow.known_tokens)
            self.assertLessEqual(dispatch.call_args.kwargs["budget"].max_seconds, 10)
            self.assertEqual((intake.as_role_observation(),), dispatch.call_args.kwargs["prior_usage"])

    def test_factory_root_mismatch_retains_actual_intake_without_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as other:
            root = Path(temporary)
            _, intake, _, provider = self.prepare(root)
            factory = FactoryTestInputs(Path(other), provider).build_factory()
            result = self.run_caller(root, intake, factory)
            self.assertIsNone(result.workflow)
            self.assertIn("ROOT-MISMATCH", result.reason)
            self.assertEqual([], provider.requests)

    def test_elapsed_preflight_time_does_not_extend_original_deadline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, intake, factory, provider = self.prepare(root)
            readings = iter((20.0, 31.0))
            result = self.run_caller(root, intake, factory, deadline_monotonic=30,
                                     clock=lambda: next(readings, 31.0))
            self.assertEqual("safe-paused", result.workflow.status)
            self.assertEqual(1, result.workflow.model_calls)
            self.assertEqual(38, result.workflow.known_tokens)
            self.assertEqual([], provider.requests)
            self.assertEqual((), factory.record_refs)


if __name__ == "__main__":
    unittest.main()
