"""Actual package material consumers with injected offline Provider ports.

Synthetic source records and conformance fixtures establish engineering paths,
never live API/source qualification or scientific/Human acceptance.
"""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from research_workbench.adapters.models import ContentBlock, ModelResponse
from research_workbench.artifacts.admission import build_admission_mapping, sidecar_path_for
from research_workbench.entry.binding import EntryBindingError
from research_workbench.entry.caller import run_frozen_intake_workflow
from research_workbench.entry.driver import SessionExecutionDriver, execute_role_slice
from research_workbench.entry.intake_call import IntakeCallBudget, call_intake
from research_workbench.entry.roles import build_role_request
from research_workbench.entry.workflow import WorkflowBudget
from research_workbench.execution import PinnedExecutionInput, load_runtime_bundle, validate_generic_execution_receipt
from research_workbench.io import load_document
from research_workbench.scaffold import _protocol
from tests.entry_chain_support import PREFIX, write_document
from tests.entry_factory_support import FactoryTestInputs
from tests.test_entry_caller import CallerRoleProvider
from tests.test_entry_intake_call import IntakeProvider


RAW_PATH = "sources/raw/material.txt"
SIDECAR_PATH = sidecar_path_for(RAW_PATH)
DERIVATIVE_PATH = "artifacts/selected-excerpt.txt"
UNSELECTED_PATH = "artifacts/unselected-missing-excerpt.txt"
MATERIAL_PATHS = (RAW_PATH, SIDECAR_PATH, DERIVATIVE_PATH)


class SidecarDroppingIntakeProvider(IntakeProvider):
    def generate(self, request):
        response = super().generate(request)
        proposal = json.loads(response.output[0].text)
        proposal["task"]["input_refs"] = [ref for ref in proposal["task"]["input_refs"]
                                           if ref["path"] != SIDECAR_PATH]
        return ModelResponse(response.response_id, response.provider, response.model,
            (ContentBlock("text", text=json.dumps(proposal)),), response.finish_reason, usage=response.usage)


def material_inputs(root, *, children=1):
    provider = CallerRoleProvider(children)
    inputs = FactoryTestInputs(root, provider)
    source = b"Synthetic exact source text.\n"
    derived = b"Selected synthetic excerpt.\n"
    refs = []
    for path, content in ((RAW_PATH, source), (DERIVATIVE_PATH, derived)):
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        refs.append({"path": path, "sha256": hashlib.sha256(content).hexdigest()})
    admission = build_admission_mapping(original_filename="material.txt", admitted_path=RAW_PATH, content=source,
        origin={"uri": "https://example.org/offline-material-fixture"},
        acquired_at="2026-10-11T00:00:00+08:00", operator="offline fixture",
        license_or_data_use="synthetic engineering fixture", parser_name="utf8-text", parser_version="1.0.0",
        sensitivity="fixture-only", egress_restriction="no-permission-grant",
        derivatives=({**refs[1], "relation": "text-excerpt"},
                     {"path": UNSELECTED_PATH, "sha256": "a" * 64, "relation": "metadata-only"}))
    raw = yaml.safe_dump(admission, sort_keys=False).encode("utf-8")
    (root / SIDECAR_PATH).write_bytes(raw)
    inputs.task["input_refs"] = [refs[0], {"path": SIDECAR_PATH, "sha256": hashlib.sha256(raw).hexdigest()}, refs[1]]
    repin_control_inputs(inputs)
    return inputs, provider


def repin_control_inputs(inputs):
    inputs.task_pin = write_document(inputs.root, "controls/root-task.json", inputs.task)
    inputs.method["task_ref"].update(task_id=inputs.task["task_id"], revision=inputs.task.get("revision", 1),
                                       sha256=inputs.task_pin.sha256)
    inputs.method_pin = write_document(inputs.root, "controls/root-method.json", inputs.method)
    inputs.options.update(task_pin=inputs.task_pin, method_pin=inputs.method_pin)


def material_intake(root, inputs, provider=None, **options):
    provider = provider if provider is not None else IntakeProvider()
    protocol = _protocol("OFFLINE-MATERIAL-BRIDGE")
    protocol["active_modes"] = inputs.task["active_modes"]
    protocol["question_refs"] = inputs.task["question_refs"]
    protocol["budgets"].update(max_parallel_subagents=3, max_delegation_depth=2)
    result = call_intake(root, intake_task=inputs.task,
        intake_profile=load_document(root / inputs.options["profile_pin"].path),
        protocol_ceiling=protocol, task_ceiling=inputs.task, provider=provider,
        model="bounded-local-model", directory=PREFIX + "/intake",
        budget=IntakeCallBudget(100, 128, 10000, 60),
        context={"approved_method": inputs.method, "requirements": [inputs.requirement]},
        clock=lambda: 0.0, **options)
    return result, provider


def actual_product_factory(root, inputs, intake, provider):
    refs = {Path(ref.path).name: ref for ref in intake.draft_refs}
    factory = inputs.build_factory(**{keyword: PinnedExecutionInput(refs[name].path, refs[name].sha256)
        for name, keyword in (("task.json", "task_pin"), ("method.json", "method_pin"),
                              ("requirement-1.json", "requirement_pin"))})
    provider.task = copy.deepcopy(factory.root_task)
    return factory


def execute_binding(root, binding, *, request_builder=None, session_clock=None, **options):
    return execute_role_slice(root, bundle_ref=binding.bundle_ref, view_ref=binding.view_ref,
        role="main", provider=binding.provider, binding_observer=binding.binding_observer,
        output_dir=binding.output_dir, output_path=binding.output_path, output_contract=binding.output_contract,
        attempt_id=binding.attempt_id, report_id="HOST-" + binding.attempt_id,
        receipt_id="RECEIPT-" + binding.attempt_id, accountable_owner="offline material bridge",
        schema_root=binding.schema_root, host_clock=binding.host_clock,
        session_clock=session_clock if session_clock is not None else (lambda: 0.0),
        request_builder=request_builder, **options)


class EntryMaterialBridgeTests(unittest.TestCase):
    def assert_material_payload(self, request, expected_refs):
        payload = json.loads(request.messages[1].content[0].text)
        expected = {ref["path"]: ref["sha256"] for ref in expected_refs}
        self.assertEqual(expected, {ref["path"]: ref["sha256"] for ref in payload["task"]["input_refs"]})
        self.assertEqual(expected, {item["path"]: item["sha256"] for item in payload["inputs"]})
        self.assertEqual(3, len(payload["inputs"]))
        kinds = {item["path"]: item["material_provenance"]["kind"] for item in payload["inputs"]}
        self.assertEqual({RAW_PATH: "raw-source", SIDECAR_PATH: "source-admission", DERIVATIVE_PATH: "source-derivative"}, kinds)
        for item in payload["inputs"]:
            provenance = item["material_provenance"]
            self.assertEqual(expected[SIDECAR_PATH], provenance["admission_ref"]["sha256"])
            self.assertEqual(expected[RAW_PATH], provenance["raw_ref"]["sha256"])
            self.assertEqual("not-established", provenance["scientific_qualification"])
            self.assertFalse(provenance["permission_grant"])
        selected = next(item for item in payload["inputs"] if item["path"] == DERIVATIVE_PATH)
        self.assertEqual("text-excerpt", selected["material_provenance"]["relation"])
        self.assertEqual(expected[DERIVATIVE_PATH], selected["material_provenance"]["derivative_ref"]["sha256"])
        return payload

    def test_actual_intake_factory_host_child_and_fresh_main_consume_exact_material_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, provider = material_inputs(root)
            original_open = Path.open
            forbidden_reads = []
            def explicit_only(path, *args, **kwargs):
                if path == root / UNSELECTED_PATH:
                    forbidden_reads.append(path)
                    raise AssertionError("unselected derivative has no read authorization")
                return original_open(path, *args, **kwargs)
            with patch.object(Path, "open", explicit_only):
                intake, intake_provider = material_intake(root, inputs)
                self.assertEqual("success", intake.status, intake.details)
                factory = actual_product_factory(root, inputs, intake, provider)
                result = run_frozen_intake_workflow(root, intake_result=intake, binding_factory=factory,
                    directory=PREFIX + "/workflow", budget=WorkflowBudget(4, 10000, 100, 128, 120, 3, 2),
                    accountable_owner="offline material bridge", deadline_monotonic=120, clock=lambda: 0.0)
                self.assertIsNotNone(result.workflow, result.reason)
                self.assertEqual("stage-completed", result.workflow.status, result.workflow.summary)
                self.assertEqual((4, 152, 0), (result.workflow.model_calls, result.workflow.known_tokens, result.workflow.held_tokens))
                self.assertEqual((1, 3, 3), (len(intake_provider.requests), len(provider.requests), len(factory.records)))
                for request in [*intake_provider.requests, *provider.requests]:
                    self.assert_material_payload(request, inputs.task["input_refs"])
                phases = [json.loads(request.messages[1].content[0].text)["caller_context"]["phase"] for request in provider.requests]
                self.assertEqual(["plan-or-execute", "plan-or-execute", "consume-child-results"], phases)
                consumed = json.loads(provider.requests[-1].messages[1].content[0].text)["caller_context"]["child_results"]
                self.assertEqual("CALLER-CHILD-0", consumed[0]["handoff"]["task_id"])
                self.assertEqual(1, len(consumed[0]["receipt_refs"]))
                self.assertIsNotNone(result.handoff_ref, result.reason)
                for record in factory.records:
                    bundle = load_runtime_bundle(record["bundle"]["path"], project_root=root)
                    frozen_task = load_document(root / record["task"]["path"])
                    self.assertEqual(inputs.task["input_refs"], frozen_task["input_refs"])
                    observed = next(item for item in result.workflow.observations if item["ordinal"] == record["ordinal"])
                    pin = observed["receipt_refs"][0]
                    checked = validate_generic_execution_receipt(pin["path"], expected_sha256=pin["sha256"], bundle=bundle)
                    self.assertFalse(checked.document["boundaries"]["task_completion"])
                self.assertEqual([], forbidden_reads)
            self.assertFalse((root / UNSELECTED_PATH).exists())
            self.assertFalse(result.human_acceptance)
            self.assertFalse(result.task_completion)

    def test_missing_explicit_sidecar_blocks_intake_and_direct_factory_without_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, provider = material_inputs(root)
            inputs.task["input_refs"] = [ref for ref in inputs.task["input_refs"] if ref["path"] != SIDECAR_PATH]
            repin_control_inputs(inputs)
            intake, intake_provider = material_intake(root, inputs)
            self.assertEqual("rejected", intake.status)
            self.assertIn("MATERIAL-ADMISSION-MISSING", json.dumps(intake.details))
            self.assertEqual((0, 0, 0, 0), (intake.model_calls, intake.input_tokens, intake.output_tokens, intake.held_tokens))
            self.assertEqual([], intake_provider.requests)
            self.assertEqual((), intake.draft_refs)
            factory = inputs.build_factory()
            with self.assertRaisesRegex(EntryBindingError, "MATERIAL-ADMISSION-MISSING"):
                factory(inputs.invocation(task=inputs.task))
            self.assertEqual([], provider.requests)
            self.assertEqual([], factory.records)
            self.assertEqual((), factory.record_refs)

    def test_model_dropping_sidecar_is_compiler_rejected_with_actual_intake_usage_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, provider = material_inputs(root)
            intake, intake_provider = material_intake(root, inputs, SidecarDroppingIntakeProvider())
            self.assertEqual("rejected", intake.status, intake.details)
            self.assertEqual("INTAKE-COMPILER-REJECTED", intake.reason)
            self.assertIn("MATERIAL-ADMISSION-MISSING", json.dumps(intake.details))
            self.assertEqual((1, 30, 8, 0), (intake.model_calls, intake.input_tokens, intake.output_tokens, intake.held_tokens))
            self.assertEqual(1, len(intake_provider.requests))
            self.assertEqual((), intake.draft_refs)
            self.assertTrue((root / (PREFIX + "/intake/response.json")).is_file())
            self.assertFalse((root / (PREFIX + "/intake/draft/task.json")).exists())
            self.assertEqual([], provider.requests)

    def test_intake_guard_drift_of_raw_sidecar_or_selected_derivative_keeps_zero_actual_calls(self):
        for target in MATERIAL_PATHS:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                inputs, _ = material_inputs(root)
                callbacks = []
                def mutate_after_initial_material_check(request):
                    self.assert_material_payload(request, inputs.task["input_refs"])
                    callbacks.append(request)
                    (root / target).write_bytes(b"changed after intake guard\n")
                    return True
                intake, provider = material_intake(root, inputs, before_dispatch=mutate_after_initial_material_check)
                self.assertNotEqual("success", intake.status)
                self.assertEqual(1, len(callbacks))
                self.assertEqual([], provider.requests)
                self.assertEqual((0, 0, 0, 0), (intake.model_calls, intake.input_tokens, intake.output_tokens, intake.held_tokens))
                self.assertEqual((), intake.draft_refs)

    def test_driver_builder_drift_of_each_material_item_blocks_actual_provider_dispatch(self):
        for target in MATERIAL_PATHS:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                inputs, provider = material_inputs(root)
                intake, intake_provider = material_intake(root, inputs)
                self.assertEqual("success", intake.status, intake.details)
                factory = actual_product_factory(root, inputs, intake, provider)
                binding = factory(inputs.invocation(task=factory.root_task))
                built = []
                def drift_after_builder(*args, **kwargs):
                    request = build_role_request(*args, **kwargs)
                    self.assert_material_payload(request, inputs.task["input_refs"])
                    built.append(request)
                    (root / target).write_bytes(b"changed after role input construction\n")
                    return request
                result = execute_binding(root, binding, request_builder=drift_after_builder)
                self.assertEqual(1, len(built))
                self.assertEqual(1, len(intake_provider.requests))
                self.assertEqual([], provider.requests)
                self.assertEqual(1, len(factory.records))
                self.assertEqual(0, result.host_report["actual_facts"]["provider_invocations"])
                self.assertEqual(0, result.host_report["actual_facts"]["tool_invocations"])
                self.assertNotEqual("completed", result.host_report["status"])
                self.assertFalse((root / binding.output_path).exists())

    def test_driver_post_capture_drift_is_rechecked_at_final_dispatch_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, provider = material_inputs(root)
            intake, _ = material_intake(root, inputs)
            self.assertEqual("success", intake.status, intake.details)
            factory = actual_product_factory(root, inputs, intake, provider)
            binding = factory(inputs.invocation(task=factory.root_task))
            captured = []
            original_record = SessionExecutionDriver.record
            def drift_after_capture(driver, kind, payload):
                original_record(driver, kind, payload)
                if kind == "provider-request":
                    captured.append(payload["request"])
                    (root / SIDECAR_PATH).write_bytes(b"changed after retained provider-request\n")
            with patch.object(SessionExecutionDriver, "record", drift_after_capture):
                result = execute_binding(root, binding)
            self.assertEqual(1, len(captured))
            self.assert_material_payload(captured[0], inputs.task["input_refs"])
            self.assertEqual([], provider.requests)
            self.assertEqual(0, result.host_report["actual_facts"]["provider_invocations"])
            self.assertEqual(0, result.host_report["actual_facts"]["tool_invocations"])
            self.assertNotEqual("completed", result.host_report["status"])
            self.assertFalse((root / binding.output_path).exists())

    def test_runner_last_clock_drift_never_counts_facade_as_actual_provider_dispatch(self):
        for target in MATERIAL_PATHS:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                inputs, provider = material_inputs(root)
                intake, intake_provider = material_intake(root, inputs)
                self.assertEqual("success", intake.status, intake.details)
                factory = actual_product_factory(root, inputs, intake, provider)
                binding = factory(inputs.invocation(task=factory.root_task))
                state = {"armed": False, "mutations": 0}
                admitted_requests = []
                original_dispatch = SessionExecutionDriver._dispatch
                def arm_after_driver_admission(driver, kind, payload):
                    admitted = original_dispatch(driver, kind, payload)
                    if kind == "provider" and admitted:
                        self.assert_material_payload(payload["request"], inputs.task["input_refs"])
                        admitted_requests.append(payload["request"])
                        state["armed"] = True
                    return admitted
                def drift_at_runner_last_clock():
                    if state["armed"]:
                        state["armed"] = False
                        state["mutations"] += 1
                        (root / target).write_bytes(b"changed in Runner final clock callback\n")
                    return 0.0
                with patch.object(SessionExecutionDriver, "_dispatch", arm_after_driver_admission):
                    result = execute_binding(root, binding, session_clock=drift_at_runner_last_clock)
                self.assertEqual((1, 1), (len(admitted_requests), state["mutations"]))
                self.assertEqual(1, len(intake_provider.requests))
                self.assertEqual([], provider.requests)
                facts = result.host_report["actual_facts"]
                self.assertEqual((0, 0, 0), (facts["provider_invocations"], facts["tool_invocations"], facts["output_tokens"]))
                self.assertNotIn("output-token-usage-unavailable", facts["capture_gaps"])
                self.assertNotEqual("completed", result.host_report["status"])
                self.assertFalse((root / binding.output_path).exists())
                self.assertIsNotNone(result.session)
                self.assertEqual(0, result.session.model_turns)
                self.assertIsNone(result.session.final_response)
                trace = load_document(root / result.trace_ref.path)
                self.assertEqual(["provider-request"], [message["kind"] for message in trace["messages"]])
                # Captured request intent is retained, while the current
                # closeout contract cannot reconcile it with zero actual calls.
                self.assertIsNone(result.receipt_ref)
                self.assertIn("Host provider invocation count does not match Execution Trace", result.closeout_error)


if __name__ == "__main__":
    unittest.main()
