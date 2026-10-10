"""Bridge integration checks using real producers and explicit offline ports."""
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from research_workbench.adapters.models import (
    ApiSessionLimits, Capability, ClientTool, ContentBlock, FinishReason, ModelResponse, ToolCall, ToolDefinition,
)
from research_workbench.entry.executor import FrozenRoleExecutor
from research_workbench.entry.roles import read_pinned_inputs
from research_workbench.entry.workflow import WorkflowBudget, run_research_workflow
from research_workbench.execution import load_runtime_bundle, validate_generic_execution_receipt
from research_workbench.io import load_document
from tests.entry_chain_support import OfflineRoleFactory, PREFIX, ROOT
from tests.test_entry_driver import ScriptedRoleProvider


def control(summary="A bounded observation was retained.", *, decision="complete", delegations=()):
    return {"decision": decision, "delegations": list(delegations), "summary": summary,
            "limitations": ["Offline test port, no live qualification or scientific acceptance."],
            "next_actions": ["Review the retained slice."]}


class DynamicProvider(ScriptedRoleProvider):
    def __init__(self, count=0, *, fail_child=False, tool=False):
        super().__init__()
        self.count, self.fail_child, self.tool = count, fail_child, tool
        self.factory = None
        self.sent_tool = False

    def capabilities(self):
        capabilities = super().capabilities()
        return replace(capabilities, supported=capabilities.supported | {Capability.TOOLS}) if self.tool else capabilities

    def generate(self, request):
        role = request.metadata["entry_role"]
        payload = json.loads(request.messages[1].content[0].text)
        if self.fail_child and role == "child":
            self.requests.append(request)
            raise RuntimeError("offline child send failure")
        base = super().generate(request)
        if self.tool and not self.sent_tool:
            self.sent_tool = True
            return ModelResponse(base.response_id, base.provider, base.model, (), FinishReason.TOOL_CALL,
                tool_calls=(ToolCall("READ-1", "research-contract-check", {"path": "materials/approved.txt"}),),
                usage=base.usage)
        context = payload.get("caller_context") or {}
        if role == "main" and context.get("phase") == "plan-or-execute" and self.count:
            output = control(decision="delegate", delegations=[{"task": self.factory.child(i)} for i in range(self.count)])
        elif role == "main" and context.get("phase") == "consume-child-results":
            children = context["child_results"]
            output = control("Consumed actual receipts for " + ", ".join(child["task_id"] for child in children))
        else:
            output = control()
        return ModelResponse(base.response_id, base.provider, base.model,
            (ContentBlock("text", text=json.dumps(output)),), FinishReason.COMPLETE, usage=base.usage)


class EntryBridgeFlowTests(unittest.TestCase):
    def _run(self, root, provider, *, tool=None, direct_tool=False, limits=None, budget=None):
        factory = OfflineRoleFactory(root, provider, tool=tool, direct_tool=direct_tool, session_limits=limits)
        provider.factory = factory
        executor = FrozenRoleExecutor(root, binding_factory=factory, accountable_owner="offline bridge test owner")
        result = run_research_workflow(root, directory=PREFIX + "/workflow", task=factory.task,
            executor=executor, budget=budget or WorkflowBudget(8, 10000, 100, 128, 120, 3, 2), clock=lambda: 0.0)
        return factory, executor, result

    def _replay_all(self, root, factory, executor):
        for binding, result in zip(factory.bindings, executor.results):
            self.assertIsNone(result.closeout_error)
            self.assertIsNotNone(result.receipt_ref)
            bundle = load_runtime_bundle(binding.bundle_ref.path, project_root=root, schema_root=ROOT / "schemas")
            receipt = validate_generic_execution_receipt(result.receipt_ref.path,
                expected_sha256=result.receipt_ref.sha256, bundle=bundle, schema_root=ROOT / "schemas")
            self.assertFalse(receipt.document["boundaries"]["task_completion"])

    def test_main_chooses_zero_one_or_three_children_each_uses_actual_frozen_task_and_receipt(self):
        for count in (0, 1, 3):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                provider = DynamicProvider(count)
                factory, executor, result = self._run(root, provider)
                expected_calls = 1 if count == 0 else count + 2
                self.assertEqual("stage-completed", result.status, result.summary)
                self.assertEqual(expected_calls, result.model_calls)
                self.assertEqual(expected_calls * 38, result.known_tokens)
                self.assertEqual(0, result.held_tokens)
                self.assertEqual(expected_calls, len(factory.selections))
                self._replay_all(root, factory, executor)
                for binding, request in zip(factory.bindings, provider.requests):
                    view = load_document(root / binding.view_ref.path)
                    supply_pin = view["selected_supply_report_ref"]
                    supply = load_document(root / supply_pin["path"])
                    constraints = json.loads(request.messages[1].content[0].text)["caller_context"]["execution_adapter_constraints"]
                    self.assertEqual(supply_pin, constraints["supply_ref"])
                    self.assertEqual(supply["required_permissions"], constraints["required_permissions"])
                    self.assertEqual(supply["data_egress_behavior"], constraints["data_egress_behavior"])
                if count:
                    request = provider.requests[-1]
                    payload = json.loads(request.messages[1].content[0].text)
                    children = payload["caller_context"]["child_results"]
                    self.assertEqual(count, len(children))
                    for child in children:
                        self.assertEqual("completed", child["execution_status"])
                        self.assertEqual({"model_calls": 1, "tool_calls": 0, "input_tokens": 30, "output_tokens": 8}, child["usage"])
                        self.assertEqual(1, len(child["receipt_refs"]))
                        self.assertTrue(any(pin["path"].endswith("output.json") for pin in child["artifact_refs"]))
                        for pin in child["artifact_refs"]:
                            self.assertNotIn(pin["path"], [i["path"] for i in payload["inputs"]])
                    self.assertNotEqual(provider.requests[0].metadata["input_snapshot_sha256"], request.metadata["input_snapshot_sha256"])

    def test_failed_child_retains_actual_send_and_full_hold_and_never_calls_main_again(self):
        with tempfile.TemporaryDirectory() as temporary:
            provider = DynamicProvider(3, fail_child=True)
            factory, executor, result = self._run(Path(temporary), provider)
            self.assertEqual("safe-paused", result.status)
            self.assertEqual(2, len(provider.requests))
            self.assertEqual(2, result.model_calls)
            self.assertEqual(38, result.known_tokens)
            self.assertEqual(228, result.held_tokens)
            self.assertEqual(("CHILD-1", "CHILD-2"), result.unstarted_tasks)
            self.assertIsNone(executor.results[-1].receipt_ref)

    def test_optional_procedure_and_direct_readonly_tool_feed_model_trace_host_receipt(self):
        for direct_tool in (False, True):
            with self.subTest(direct_tool=direct_tool), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                reads = []
                factory_box = []
                def exact_read(arguments):
                    refs = factory_box[0].task["input_refs"]
                    selected = [ref for ref in refs if ref["path"] == arguments.get("path")]
                    if len(selected) != 1 or set(arguments) != {"path"}:
                        raise ValueError("requested Tool input is outside the exact Task read set")
                    record = read_pinned_inputs(root, selected)[0]
                    reads.append(record["path"])
                    return record["text"]
                tool = ClientTool(ToolDefinition("research-contract-check", "Read the exact approved synthetic input.",
                    {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}),
                    exact_read, "read-only")
                provider = DynamicProvider(tool=True)
                limits = ApiSessionLimits(max_model_turns=2, max_tool_calls=1, max_parallel_tool_calls=1,
                    max_tool_result_chars=1024, max_output_tokens_per_turn=128, max_seconds=60)
                factory = OfflineRoleFactory(root, provider, tool=tool, direct_tool=direct_tool, session_limits=limits)
                factory_box.append(factory)
                provider.factory = factory
                executor = FrozenRoleExecutor(root, binding_factory=factory, accountable_owner="offline bridge test owner")
                result = run_research_workflow(root, directory=PREFIX + "/workflow", task=factory.task, executor=executor,
                    budget=WorkflowBudget(3, 10000, 100, 128, 120, 3, 2, max_session_model_turns=2), clock=lambda: 0.0)
                self.assertEqual("stage-completed", result.status, result.summary)
                self.assertEqual(2, result.model_calls)
                self.assertEqual(76, result.known_tokens)
                self.assertEqual(["materials/approved.txt"], reads)
                executed = executor.results[0]
                self.assertEqual(1, executed.host_report["actual_facts"]["tool_invocations"])
                trace = load_document(root / executed.trace_ref.path)
                ledger = root / Path(executed.trace_ref.path).parent / trace["event_ledger"]["path"]
                tool_events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()
                               if json.loads(line)["event_type"] == "tool-call"]
                self.assertEqual(2, len(tool_events))
                self.assertTrue(all(item["payload"]["tool_name"] == factory.tool_ref for item in tool_events))
                self.assertEqual(["attempted", "succeeded"], [item["payload"]["status"] for item in tool_events])
                result_pin = tool_events[-1]["payload"]["result_ref"]
                retained_result = load_document(ledger.parent / result_pin["path"])
                self.assertIn("bounded synthetic", retained_result)
                self.assertTrue(any(message.role == "tool" for message in provider.requests[1].messages))
                self._replay_all(root, factory, executor)

    def test_multi_turn_reservation_is_required_before_entering_provider(self):
        with tempfile.TemporaryDirectory() as temporary:
            provider = DynamicProvider()
            _, _, result = self._run(Path(temporary), provider,
                budget=WorkflowBudget(3, 300, 100, 128, 120, 3, 2, max_session_model_turns=2))
            self.assertEqual("safe-paused", result.status)
            self.assertEqual([], provider.requests)
            self.assertEqual(0, result.model_calls)
            self.assertIn("reservation", result.summary)

    def test_missing_tool_mapping_or_writing_handler_blocks_before_provider(self):
        for variant in ("missing-map", "writing"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                invoked = []
                tool = ClientTool(ToolDefinition("research-contract-check", "Bounded test.", {"type": "object"}),
                    lambda args: invoked.append(args), "external-write" if variant == "writing" else "read-only")
                provider = DynamicProvider(tool=True)
                limits = ApiSessionLimits(max_model_turns=2, max_tool_calls=1, max_parallel_tool_calls=1,
                    max_tool_result_chars=1024, max_output_tokens_per_turn=128, max_seconds=60)
                factory = OfflineRoleFactory(root, provider, tool=tool, session_limits=limits)
                provider.factory = factory
                def bind(invocation):
                    binding = factory(invocation)
                    return replace(binding, tool_refs={}) if variant == "missing-map" else binding
                executor = FrozenRoleExecutor(root, binding_factory=bind, accountable_owner="offline bridge test owner")
                result = run_research_workflow(root, directory=PREFIX + "/workflow", task=factory.task, executor=executor,
                    budget=WorkflowBudget(3, 10000, 100, 128, 120, 3, 2, max_session_model_turns=2), clock=lambda: 0.0)
                self.assertEqual("safe-paused", result.status)
                self.assertEqual([], provider.requests)
                self.assertEqual([], invoked)

    def test_tool_handler_failure_or_oversize_preserves_failure_and_stops_second_request(self):
        for variant in ("handler-failed", "oversize"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                def handler(arguments):
                    if variant == "handler-failed":
                        raise ValueError("the exact requested input could not be read")
                    return "x" * 2048
                tool = ClientTool(ToolDefinition("research-contract-check", "Bounded test.", {"type": "object"}), handler, "read-only")
                limits = ApiSessionLimits(max_model_turns=2, max_tool_calls=1, max_parallel_tool_calls=1,
                    max_tool_result_chars=1024, max_output_tokens_per_turn=128, max_seconds=60)
                provider = DynamicProvider(tool=True)
                factory, executor, result = self._run(Path(temporary), provider, tool=tool, limits=limits,
                    budget=WorkflowBudget(3, 10000, 100, 128, 120, 3, 2, max_session_model_turns=2))
                self.assertEqual("safe-paused", result.status)
                self.assertEqual(1, len(provider.requests))
                self.assertEqual(1, result.model_calls)
                self.assertEqual(38, result.known_tokens)
                self.assertEqual(0, result.held_tokens)
                self.assertEqual(1, executor.results[0].host_report["actual_facts"]["tool_invocations"])
                self.assertEqual("failed", executor.results[0].host_report["status"])


if __name__ == "__main__":
    unittest.main()
