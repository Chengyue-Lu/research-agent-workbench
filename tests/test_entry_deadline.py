"""Original-deadline dispatch proofs through actual offline package consumers.

The injected clock and Provider are deterministic local ports, not live API
qualification. No fixture is treated as an authorization or usage record.
"""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from research_workbench.adapters.models import ApiSessionLimits, ClientTool, ToolDefinition
from research_workbench.adapters.models import IsolatedApiSessionRunner, ProviderRegistry
from research_workbench.adapters.models import session as session_module
from research_workbench.entry import executor as executor_module
from research_workbench.entry.caller import run_frozen_intake_workflow
from research_workbench.entry.driver import SessionExecutionDriver
from research_workbench.entry.executor import FrozenRoleExecutor
from research_workbench.entry.factory import ApiRoleBindingFactory
from research_workbench.entry.intake_call import IntakeCallBudget, call_intake
from research_workbench.entry.workflow import WorkflowBudget, run_research_workflow
from research_workbench.execution import PinnedExecutionInput, load_runtime_bundle, validate_generic_execution_receipt
from research_workbench.io import load_document
from research_workbench.observability.trace import AgentTraceRecorder
from research_workbench.scaffold import _protocol
from tests.entry_chain_support import OfflineRoleFactory, PREFIX, ROOT
from tests.entry_factory_support import FactoryTestInputs
from tests.test_entry_bridge_flow import DynamicProvider
from tests.test_entry_caller import CallerRoleProvider
from tests.test_entry_intake_call import IntakeProvider
from tests import test_api_session_runner as ordinary_session
from tests import test_conformance_session_policy as conformance_session


class MutableClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


class EntryDeadlineTests(unittest.TestCase):
    def prepare_caller(self, root):
        provider = CallerRoleProvider()
        inputs = FactoryTestInputs(root, provider)
        protocol = _protocol("OFFLINE-DEADLINE")
        protocol["active_modes"] = inputs.task["active_modes"]
        protocol["question_refs"] = inputs.task["question_refs"]
        protocol["budgets"].update(max_parallel_subagents=3, max_delegation_depth=2)
        intake = call_intake(root, intake_task=inputs.task,
            intake_profile=load_document(root / inputs.options["profile_pin"].path),
            protocol_ceiling=protocol, task_ceiling=inputs.task,
            provider=IntakeProvider("valid"), model="bounded-local-model",
            directory=PREFIX + "/intake", budget=IntakeCallBudget(100, 128, 10000, 60),
            context={"approved_method": inputs.method, "requirements": [inputs.requirement]},
            clock=lambda: 0.0)
        refs = {Path(ref.path).name: ref for ref in intake.draft_refs}
        factory = inputs.build_factory(**{
            field: PinnedExecutionInput(refs[name].path, refs[name].sha256)
            for name, field in (("task.json", "task_pin"), ("method.json", "method_pin"),
                                ("requirement-1.json", "requirement_pin"))})
        provider.task = copy.deepcopy(factory.root_task)
        return intake, factory, provider

    def call(self, root, intake, factory, clock):
        return run_frozen_intake_workflow(root, intake_result=intake, binding_factory=factory,
            directory=PREFIX + "/workflow", budget=WorkflowBudget(4, 10000, 100, 128, 120, 3, 2),
            accountable_owner="offline deadline test", deadline_monotonic=120, clock=clock)

    def test_factory_crosses_original_120_deadline_zero_provider_and_no_unknown_hold(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, clock = Path(temporary), MutableClock()
            intake, factory, provider = self.prepare_caller(root)
            original = ApiRoleBindingFactory.__call__
            invocations = []
            def delayed(actual, invocation):
                invocations.append(invocation)
                binding = original(actual, invocation)
                clock.now = 121.0
                return binding
            with mock.patch.object(ApiRoleBindingFactory, "__call__", delayed):
                result = self.call(root, intake, factory, clock)
            self.assertEqual(120, invocations[0].deadline_monotonic)
            self.assertEqual(121, invocations[0].clock())
            self.assertEqual("safe-paused", result.workflow.status, result.reason)
            self.assertEqual([], provider.requests)
            self.assertEqual(1, result.workflow.model_calls)  # actual earlier intake only
            self.assertEqual(38, result.workflow.known_tokens)
            self.assertEqual(0, result.workflow.held_tokens)
            self.assertEqual(0, result.workflow.observations[0]["model_calls"])
            self.assertIn("during factory", result.workflow.summary)
            self.assertTrue(factory.record_refs)  # preserve freezing already performed

    def test_bundle_preparation_expiry_stops_at_host_with_zero_provider(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, clock = Path(temporary), MutableClock()
            intake, factory, provider = self.prepare_caller(root)
            original = executor_module.load_runtime_bundle
            def delayed(*args, **kwargs):
                bundle = original(*args, **kwargs)
                clock.now = 121.0
                return bundle
            with mock.patch.object(executor_module, "load_runtime_bundle", delayed):
                result = self.call(root, intake, factory, clock)
            self.assertEqual([], provider.requests)
            self.assertEqual("safe-paused", result.workflow.status)
            observation = result.workflow.observations[0]
            self.assertEqual(0, observation["model_calls"])
            host_ref = next(ref for ref in observation["artifact_refs"] if ref["path"].endswith("/host.json"))
            host = load_document(root / host_ref["path"])
            self.assertEqual("preflight-blocked", host["execution_phase"])
            self.assertEqual(0, host["actual_facts"]["provider_invocations"])
            self.assertEqual(0, result.workflow.held_tokens)

    def test_role_request_preparation_expiry_does_not_restart_runner_timer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, clock = Path(temporary), MutableClock()
            intake, factory, provider = self.prepare_caller(root)
            original = executor_module.build_role_request
            def delayed(*args, **kwargs):
                request = original(*args, **kwargs)
                clock.now = 121.0
                return request
            with mock.patch.object(executor_module, "build_role_request", delayed):
                result = self.call(root, intake, factory, clock)
            self.assertEqual([], provider.requests)
            self.assertEqual("safe-paused", result.workflow.status)
            self.assertEqual(0, result.workflow.observations[0]["model_calls"])
            self.assertEqual(0, result.workflow.held_tokens)
            self.assertIn("wall-time-budget", result.workflow.summary)

    def test_provider_intent_capture_crosses_deadline_zero_actual_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, clock = Path(temporary), MutableClock()
            intake, factory, provider = self.prepare_caller(root)
            original = AgentTraceRecorder.record
            def delayed(recorder, kind, payload):
                result = original(recorder, kind, payload)
                if kind == "provider-request":
                    clock.now = 121.0
                return result
            with mock.patch.object(AgentTraceRecorder, "record", delayed):
                result = self.call(root, intake, factory, clock)
            self.assertEqual([], provider.requests)
            self.assertEqual("safe-paused", result.workflow.status)
            self.assertEqual(0, result.workflow.observations[0]["model_calls"])
            self.assertEqual(38, result.workflow.known_tokens)
            self.assertEqual(0, result.workflow.held_tokens)

    def run_tools(self, root, clock, *, expire_at=None):
        reads = []
        def read(arguments):
            reads.append(arguments["path"])
            if expire_at == "next-provider":
                clock.now = 121.0
            return "bounded synthetic input"
        tool = ClientTool(ToolDefinition("research-contract-check", "Read approved synthetic material.",
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}), read)
        limits = ApiSessionLimits(2, 1, 1, 1024, 128, 120)
        provider = DynamicProvider(tool=True)
        factory = OfflineRoleFactory(root, provider, tool=tool, session_limits=limits)
        provider.factory = factory
        executor = FrozenRoleExecutor(root, binding_factory=factory, accountable_owner="offline deadline test")
        original = AgentTraceRecorder.record
        def delayed(recorder, kind, payload):
            result = original(recorder, kind, payload)
            if kind == expire_at:
                clock.now = 121.0
            return result
        with mock.patch.object(AgentTraceRecorder, "record", delayed):
            result = run_research_workflow(root, directory=PREFIX + "/workflow", task=factory.task,
                executor=executor, budget=WorkflowBudget(3, 10000, 100, 128, 120, 3, 2,
                    max_session_model_turns=2), clock=clock)
        return factory, executor, result, provider, reads

    def test_tool_intent_capture_crosses_deadline_retains_response_usage_without_tool(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, executor, result, provider, reads = self.run_tools(Path(temporary), MutableClock(), expire_at="tool-attempted")
            self.assertEqual("safe-paused", result.status)
            self.assertEqual(1, len(provider.requests))
            self.assertEqual([], reads)
            self.assertEqual(1, result.model_calls)
            self.assertEqual(38, result.known_tokens)
            self.assertEqual(0, result.held_tokens)
            self.assertEqual(0, executor.results[0].host_report["actual_facts"]["tool_invocations"])
            self.assertEqual("wall-time-budget", executor.results[0].session.stop_reason)

    def test_after_actual_tool_time_expiry_prevents_following_provider_and_preserves_usage(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, executor, result, provider, reads = self.run_tools(Path(temporary), MutableClock(), expire_at="next-provider")
            self.assertEqual("safe-paused", result.status)
            self.assertEqual(1, len(provider.requests))
            self.assertEqual(["materials/approved.txt"], reads)
            self.assertEqual(1, result.model_calls)
            self.assertEqual(38, result.known_tokens)
            self.assertEqual(0, result.held_tokens)
            self.assertEqual(1, executor.results[0].host_report["actual_facts"]["tool_invocations"])

    def test_unexpired_real_caller_uses_shared_clock_despite_factory_zero_clock(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, clock = Path(temporary), MutableClock(20.0)
            intake, factory, provider = self.prepare_caller(root)
            result = self.call(root, intake, factory, clock)
            self.assertEqual("stage-completed", result.workflow.status, result.workflow.summary)
            self.assertEqual(1, len(provider.requests))
            self.assertEqual(2, result.workflow.model_calls)
            self.assertEqual(76, result.workflow.known_tokens)
            self.assertEqual(0, result.workflow.held_tokens)
            self.assertIsNotNone(result.handoff_ref, result.reason)
            receipt = result.workflow.observations[0]["receipt_refs"][0]
            bundle_ref = factory.records[0]["bundle"]
            bundle = load_runtime_bundle(bundle_ref["path"], project_root=root)
            validate_generic_execution_receipt(receipt["path"], expected_sha256=receipt["sha256"], bundle=bundle)

    def test_unexpired_tool_path_runs_both_requests_and_retains_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            factory, executor, result, provider, reads = self.run_tools(root, MutableClock(20.0))
            self.assertEqual("stage-completed", result.status, result.summary)
            self.assertEqual(2, len(provider.requests))
            self.assertEqual(["materials/approved.txt"], reads)
            self.assertEqual(76, result.known_tokens)
            self.assertEqual(0, result.held_tokens)
            self.assertIsNotNone(executor.results[0].receipt_ref, executor.results[0].closeout_error)
            bundle = load_runtime_bundle(factory.bindings[0].bundle_ref.path, project_root=root, schema_root=ROOT / "schemas")
            pin = executor.results[0].receipt_ref
            validate_generic_execution_receipt(pin.path, expected_sha256=pin.sha256, bundle=bundle, schema_root=ROOT / "schemas")

    def session_inputs(self, *, conformance, clock):
        invoked = []
        if conformance:
            provider = conformance_session.FakeProvider(conformance_session.response(),
                conformance_session.response(tool=False))
            provider_name = "synthetic"
            request = conformance_session.request()
            limits = conformance_session.limits(max_seconds=120)
            definition = conformance_session.definition()
            options = {"tool_choice_transition": conformance_session.policy()}
        else:
            provider = ordinary_session.ScriptedProvider(
                ordinary_session.response("tool", ordinary_session.FinishReason.TOOL_CALL,
                    tool_calls=(ordinary_session.ToolCall("lookup-1", "lookup", {"id": "one"}),)),
                ordinary_session.response("final", ordinary_session.FinishReason.COMPLETE, text="done"))
            provider_name = "fake"
            request = ordinary_session.request()
            limits = ordinary_session.limits(max_seconds=120)
            definition = ordinary_session.lookup_definition()
            options = {}
        registry = ProviderRegistry()
        registry.register(provider_name, provider)
        runner = IsolatedApiSessionRunner(registry, tools=(ClientTool(definition,
            lambda arguments: invoked.append(dict(arguments)) or "bounded result"),), clock=clock)
        options.update(provider_name=provider_name, request=request, limits=limits, deadline_monotonic=120)
        return runner, provider, invoked, options

    def test_ordinary_and_conformance_slow_true_guards_stop_before_actual_dispatch(self):
        for conformance in (False, True):
            for phase in ("provider", "tool"):
                with self.subTest(conformance=conformance, phase=phase):
                    clock = MutableClock(119.0)
                    runner, provider, invoked, options = self.session_inputs(conformance=conformance, clock=clock)
                    def slow_guard(kind, payload):
                        if kind == phase:
                            clock.now = 121.0
                        return True
                    result = runner.run(**options, dispatch_guard=slow_guard)
                    expected_models = 0 if phase == "provider" else 1
                    self.assertEqual("safe-paused", result.status.value)
                    self.assertEqual("wall-time-budget", result.stop_reason)
                    self.assertEqual(expected_models, len(provider.requests))
                    self.assertEqual(expected_models, runner.dispatch_facts["provider_invocations"])
                    self.assertEqual([], invoked)
                    self.assertEqual(0, runner.dispatch_facts["tool_invocations"])
                    self.assertEqual(0, result.tool_calls)
                    if expected_models:
                        self.assertEqual(7, result.usage.total_tokens)

    def test_conformance_slow_final_validation_stops_tool_after_preserving_model_usage(self):
        clock = MutableClock(119.0)
        runner, provider, invoked, options = self.session_inputs(conformance=True, clock=clock)
        original = session_module.validate_response_contract
        validations = 0
        def delayed(*args, **kwargs):
            nonlocal validations
            result = original(*args, **kwargs)
            validations += 1
            if validations == 2:  # final Tool validation after durable summary
                clock.now = 121.0
            return result
        with mock.patch.object(session_module, "validate_response_contract", delayed):
            result = runner.run(**options)
        self.assertEqual("safe-paused", result.status.value)
        self.assertEqual("wall-time-budget", result.stop_reason)
        self.assertEqual(1, len(provider.requests))
        self.assertEqual([], invoked)
        self.assertEqual(7, result.usage.total_tokens)
        self.assertEqual(1, runner.dispatch_facts["provider_invocations"])
        self.assertEqual(0, runner.dispatch_facts["tool_invocations"])

    def test_slow_guard_still_within_deadline_preserves_both_session_paths(self):
        for conformance in (False, True):
            with self.subTest(conformance=conformance):
                clock = MutableClock(119.0)
                runner, provider, invoked, options = self.session_inputs(conformance=conformance, clock=clock)
                def bounded_guard(kind, payload):
                    clock.now += 0.1
                    return True
                result = runner.run(**options, dispatch_guard=bounded_guard)
                self.assertEqual("completed", result.status.value)
                self.assertEqual(2, len(provider.requests))
                self.assertEqual(1, len(invoked))
                self.assertEqual(14, result.usage.total_tokens)
                self.assertEqual(2, runner.dispatch_facts["provider_invocations"])
                self.assertEqual(1, runner.dispatch_facts["tool_invocations"])

    def test_conformance_slow_final_validation_within_deadline_still_executes_tool(self):
        clock = MutableClock(119.0)
        runner, provider, invoked, options = self.session_inputs(conformance=True, clock=clock)
        original = session_module.validate_response_contract
        validations = 0
        def delayed(*args, **kwargs):
            nonlocal validations
            result = original(*args, **kwargs)
            validations += 1
            if validations == 2:
                clock.now += 0.1
            return result
        with mock.patch.object(session_module, "validate_response_contract", delayed):
            result = runner.run(**options)
        self.assertEqual("completed", result.status.value)
        self.assertEqual(2, len(provider.requests))
        self.assertEqual(1, len(invoked))
        self.assertEqual(14, result.usage.total_tokens)
        self.assertEqual(2, runner.dispatch_facts["provider_invocations"])
        self.assertEqual(1, runner.dispatch_facts["tool_invocations"])

    def test_actual_dispatch_facts_reset_per_run_and_snapshots_are_detached(self):
        clock = MutableClock(119.0)
        runner, provider, invoked, options = self.session_inputs(conformance=False, clock=clock)
        def late_guard(kind, payload):
            clock.now = 121.0
            return True
        stopped = runner.run(**options, dispatch_guard=late_guard)
        self.assertEqual("safe-paused", stopped.status.value)
        detached = runner.dispatch_facts
        detached["provider_invocations"] = 999
        self.assertEqual(0, runner.dispatch_facts["provider_invocations"])
        clock.now = 119.0
        completed = runner.run(**options)
        self.assertEqual("completed", completed.status.value)
        self.assertEqual(2, len(provider.requests))
        self.assertEqual(1, len(invoked))
        self.assertEqual(2, runner.dispatch_facts["provider_invocations"])
        self.assertEqual(1, runner.dispatch_facts["tool_invocations"])

    def test_package_driver_slow_true_guard_zero_actual_send_without_unknown_hold(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, clock = Path(temporary), MutableClock()
            intake, factory, provider = self.prepare_caller(root)
            original = SessionExecutionDriver._dispatch
            def delayed(driver, kind, payload):
                admitted = original(driver, kind, payload)
                clock.now = 121.0
                return admitted
            with mock.patch.object(SessionExecutionDriver, "_dispatch", delayed):
                result = self.call(root, intake, factory, clock)
            self.assertEqual("safe-paused", result.workflow.status)
            self.assertEqual([], provider.requests)
            self.assertEqual(1, result.workflow.model_calls)  # intake only
            self.assertEqual(38, result.workflow.known_tokens)
            self.assertEqual(0, result.workflow.held_tokens)
            self.assertEqual(0, result.workflow.observations[0]["model_calls"])
            self.assertEqual(0, result.workflow.observations[0]["input_tokens"])

    def test_package_driver_slow_true_tool_guard_does_not_count_uninvoked_handler(self):
        with tempfile.TemporaryDirectory() as temporary:
            clock = MutableClock()
            original = SessionExecutionDriver._dispatch
            def delayed(driver, kind, payload):
                admitted = original(driver, kind, payload)
                if kind == "tool":
                    clock.now = 121.0
                return admitted
            with mock.patch.object(SessionExecutionDriver, "_dispatch", delayed):
                _, executor, result, provider, reads = self.run_tools(Path(temporary), clock)
            self.assertEqual("safe-paused", result.status)
            self.assertEqual(1, len(provider.requests))
            self.assertEqual([], reads)
            self.assertEqual(38, result.known_tokens)
            self.assertEqual(0, result.held_tokens)
            self.assertEqual(0, result.observations[0]["tool_calls"])
            self.assertEqual(0, executor.results[0].host_report["actual_facts"]["tool_invocations"])

    def test_package_real_send_exception_is_actual_one_with_unknown_usage_and_no_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, clock = Path(temporary), MutableClock()
            intake, factory, provider = self.prepare_caller(root)
            provider.fail = True
            result = self.call(root, intake, factory, clock)
            self.assertEqual("safe-paused", result.workflow.status)
            self.assertEqual(1, len(provider.requests))
            self.assertEqual(2, result.workflow.model_calls)  # intake and actual failed role send
            self.assertEqual(38, result.workflow.known_tokens)
            self.assertEqual(228, result.workflow.held_tokens)
            self.assertEqual(1, result.workflow.observations[0]["model_calls"])
            self.assertIsNone(result.workflow.observations[0]["input_tokens"])


if __name__ == "__main__":
    unittest.main()
