"""Real local A1/A2 transport sessions and file-only closeout replay."""

from __future__ import annotations

import copy
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from research_workbench.adapters.models import (
    Capability, ClientTool, ContentBlock, FinishReason, ModelResponse,
    ProviderCapabilities, ProviderError, ProviderErrorCategory, ToolCall, ToolDefinition, Usage,
)
from research_workbench.cli import main
from research_workbench.evaluation.pins import EvaluationValidationError
from research_workbench.execution.baseline import _tool_inputs, observe_baseline_binding, run_baseline_session
from research_workbench.execution.baseline_closeout import verify_baseline_receipt
from research_workbench.validation.document_kinds import infer_document_kind
from tests.baseline_fixtures import A1, A2, AT, ROOT, BaselineFixture


class ScriptedProvider:
    """File-bound local adapter; callbacks inject changes during real calls."""

    def __init__(self, *responses, on_call=None):
        self.responses = list(responses)
        self.requests = []
        self.on_call = on_call

    def capabilities(self):
        return ProviderCapabilities(
            provider="baseline-fixture", adapter_version="1.0.0",
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
            models=("baseline-fixture",), deployment="local",
        )

    def generate(self, request):
        self.requests.append(request)
        if self.on_call is not None:
            self.on_call(len(self.requests), request)
        if not self.responses:
            raise AssertionError("unexpected baseline provider call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def response(identity, *, tool=False):
    return ModelResponse(
        response_id=identity, provider="baseline-fixture", model="baseline-fixture",
        output=() if tool else (ContentBlock("text", text="7"),),
        finish_reason=FinishReason.TOOL_CALL if tool else FinishReason.COMPLETE,
        tool_calls=(ToolCall("call-1", "bounded_operation", {"value": "7"}),) if tool else (),
        usage=Usage(input_tokens=5, output_tokens=2),
    )


class BaselineExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.template = BaselineFixture(Path(temporary.name))
        cls.template.build()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.f = copy.deepcopy(self.template)
        self.f.root = Path(temporary.name)
        shutil.copytree(self.template.root, self.f.root, dirs_exist_ok=True)

    def freeze(self, provider, arm=A1):
        binding = observe_baseline_binding(provider, model="baseline-fixture", model_slot="primary")
        self.f.build_baseline(arm, execution_binding=binding)
        return binding

    def run_arm(self, provider, *, tools=(), **options):
        return run_baseline_session(
            self.f.root, envelope_ref=self.f.envelope_ref,
            expected_protocol_ref=self.f.protocol_ref, provider=provider,
            attempt_path="work/TASK-MR-ES-FROZEN-001/A1", attempt_id="BASELINE-A1",
            receipt_id="BASELINE-RECEIPT-A1", tools=tools, utc_clock=lambda: AT,
            schema_root=ROOT / "schemas", **options,
        )

    def load_tool(self):
        source = self.f.root / self.f.bindings[A2]["implementation_ref"]["path"]
        specification = importlib.util.spec_from_file_location("baseline_qualified_tool", source)
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        return ClientTool(ToolDefinition(**self.f.tool_definition), module.bounded_operation)

    @contextlib.contextmanager
    def observe_tool_calls(self, tool, *, on_call=None, after_return=None):
        """Observe the qualified callable without wrapping or changing its source."""
        calls = []
        original = sys.getprofile()

        def profile(frame, event, _value):
            if frame.f_code is tool.execute.__code__:
                if event == "call":
                    calls.append(dict(frame.f_locals["value"]))
                    if on_call is not None:
                        on_call()
                elif event == "return" and after_return is not None:
                    after_return()

        sys.setprofile(profile)
        try:
            yield calls
        finally:
            sys.setprofile(original)

    def assert_public_validation(self, result):
        documents = [self.f.envelope, result["receipt"]]
        documents.extend(self.f.doc(ref["path"]) for ref in result["receipt"]["fact_refs"])
        for document in documents:
            self.assertEqual(infer_document_kind(document), document["record_kind"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([
                "validate", str(self.f.root / self.f.envelope_ref["path"]),
                str(self.f.root / result["receipt_ref"]["path"]),
                "--root", str(self.f.root),
            ])
        self.assertEqual(code, 0, output.getvalue())
        self.assertIn("errors=0", output.getvalue())

    def assert_fresh_file_replay(self, result, *, implementation=None):
        script = r'''
import json, pathlib, subprocess, sys
from unittest.mock import patch
from research_workbench.execution.baseline_closeout import verify_baseline_receipt
from tests.test_baseline_execution import ScriptedProvider
arguments = json.loads(sys.argv[1])
implementation = arguments.pop("implementation")
if implementation is not None:
    forbidden = pathlib.Path(implementation).resolve()
    def audit(event, values):
        if event == "exec" and pathlib.Path(values[0].co_filename).resolve() == forbidden:
            raise AssertionError("file replay imported the Tool implementation")
    sys.addaudithook(audit)
with patch.object(ScriptedProvider, "generate", side_effect=AssertionError("Provider rerun")), \
     patch.object(ScriptedProvider, "capabilities", side_effect=AssertionError("Provider observation rerun")), \
     patch("research_workbench.execution.baseline.run_baseline_session", side_effect=AssertionError("transport rerun")), \
     patch.object(subprocess, "Popen", side_effect=AssertionError("replay launched a process")):
    receipt = verify_baseline_receipt(**arguments)
print(json.dumps({"status": receipt["status"], "attempt_id": receipt["attempt_id"]}))
'''
        arguments = {
            "root": str(self.f.root), "receipt_ref": result["receipt_ref"],
            "expected_envelope_ref": self.f.envelope_ref, "schema_root": str(ROOT / "schemas"),
            "implementation": str(implementation) if implementation is not None else None,
        }
        environment = {
            key: value for key, value in os.environ.items()
            if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
        }
        environment["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(ROOT)])
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, "-X", "utf8", "-c", script, json.dumps(arguments)],
            cwd=self.f.root, env=environment, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], result["receipt"]["status"])

    def assert_preserved_failure(self, result, *, replay_valid):
        self.assertEqual(result["receipt"]["status"], "post-call-failed")
        self.assertEqual(result["replay_valid"], replay_valid, result["replay_error"])
        self.assertEqual(self.f.doc(result["receipt_ref"]["path"]), result["receipt"])
        self.assertFalse(result["receipt"]["task_completion"])
        self.assertEqual(self.f.doc(result["receipt"]["validation_ref"]["path"])["status"], "fail")

    def test_a1_completes_using_only_the_public_payload(self):
        provider = ScriptedProvider(response("a1-final"))
        binding = self.freeze(provider)
        result = run_baseline_session(
            self.f.root, envelope_ref=self.f.envelope_ref,
            expected_protocol_ref=self.f.protocol_ref, provider=provider,
            attempt_path="work/TASK-MR-ES-FROZEN-001/A1", attempt_id="BASELINE-A1",
            receipt_id="BASELINE-RECEIPT-A1", schema_root=ROOT / "schemas",
        )
        self.assertEqual(result["receipt"]["status"], "completed")
        self.assertTrue(result["replay_valid"], result["replay_error"])
        self.assertEqual(result["receipt"]["actual_binding"], binding)
        self.assertEqual(len(provider.requests), 1)
        request = provider.requests[0]
        self.assertEqual(request.tools, ())
        payload = json.loads(request.messages[0].content[0].text)
        self.assertEqual(set(payload), {"instruction", "inputs", "required_outputs"})
        self.assertFalse(result["receipt"]["task_completion"])
        self.assertTrue(all(value is False for value in result["receipt"]["boundaries"].values()))
        self.assert_public_validation(result)
        self.assert_fresh_file_replay(result)

    def test_a2_uses_the_qualified_callable_then_replays_without_tools(self):
        provider = ScriptedProvider(response("a2-call", tool=True), response("a2-final"))
        self.freeze(provider, A2)
        tool = self.load_tool()
        with self.observe_tool_calls(tool) as calls:
            result = self.run_arm(provider, tools=(tool,))
        self.assertEqual(calls, [{"value": "7"}])
        self.assertEqual(len(provider.requests), 2)
        self.assertEqual(result["receipt"]["status"], "completed")
        self.assertTrue(result["replay_valid"], result["replay_error"])
        tool_messages = [message for message in provider.requests[1].messages if message.role == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertEqual(tool_messages[0].content[0].data["output"], {"value": "7"})
        self.assert_public_validation(result)
        implementation = self.f.root / self.f.bindings[A2]["implementation_ref"]["path"]
        self.assert_fresh_file_replay(result, implementation=implementation)
        self.assertEqual(len(provider.requests), 2)

        # Reuse this same successful Attempt: rehashing a different admitted
        # input as the Tool must not replace the frozen qualified callable.
        forged = copy.deepcopy(result["receipt"])
        trace = self.f.doc(forged["trace_index_ref"]["path"])
        trace_directory = Path(forged["trace_index_ref"]["path"]).parent
        changed_facts = 0
        for reference in forged["fact_refs"]:
            fact = self.f.doc(reference["path"])
            if fact["operation"] != "tool":
                continue
            self.assertIn(self.f.public_input_ref, fact["use_refs"])
            fact["tool_ref"] = copy.deepcopy(self.f.public_input_ref)
            replacement = self.f.write(reference["path"], fact)
            reference.update(replacement)
            child = next(
                entry for entry in trace["decision_refs"]
                if (trace_directory / entry["path"]).as_posix() == reference["path"]
            )
            child["sha256"] = replacement["sha256"]
            changed_facts += 1
        self.assertEqual(changed_facts, 2)
        forged["trace_index_ref"] = self.f.write(forged["trace_index_ref"]["path"], trace)
        validation = self.f.doc(forged["validation_ref"]["path"])
        for reference in validation["subject_refs"]:
            if reference["path"] == forged["trace_index_ref"]["path"]:
                reference.update(forged["trace_index_ref"])
        forged["validation_ref"] = self.f.write(forged["validation_ref"]["path"], validation)
        forged_ref = self.f.write(result["receipt_ref"]["path"], forged)
        with self.assertRaisesRegex(EvaluationValidationError, "qualified Tool"):
            verify_baseline_receipt(
                self.f.root, forged_ref, expected_envelope_ref=self.f.envelope_ref,
                schema_root=ROOT / "schemas",
            )
        self.assertEqual(len(provider.requests), 2)

    def test_envelope_drift_after_tool_return_blocks_the_next_provider(self):
        provider = ScriptedProvider(response("a2-call", tool=True), response("must-not-run"))
        self.freeze(provider, A2)
        tool = self.load_tool()
        envelope = self.f.root / self.f.envelope_ref["path"]
        original = envelope.read_bytes()

        def drift():
            envelope.write_bytes(original + b"\n")

        with self.observe_tool_calls(tool, after_return=drift) as calls:
            result = self.run_arm(provider, tools=(tool,))
        self.assertEqual(calls, [{"value": "7"}])
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(len(provider.responses), 1)
        self.assert_preserved_failure(result, replay_valid=False)
        self.assertEqual((self.f.root / result["receipt"]["envelope_snapshot_ref"]["path"]).read_bytes(), original)

    def test_tool_file_drift_before_invocation_preserves_the_failed_attempt(self):
        provider = ScriptedProvider(response("a2-call", tool=True), response("must-not-run"))
        self.freeze(provider, A2)
        tool = self.load_tool()
        source = self.f.root / self.f.bindings[A2]["implementation_ref"]["path"]
        original = source.read_bytes()
        provider.on_call = lambda *_: source.write_bytes(original + b"\n# drift\n")
        with self.observe_tool_calls(tool) as calls:
            result = self.run_arm(provider, tools=(tool,))
        self.assertEqual(calls, [])
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(len(provider.responses), 1)
        self.assert_preserved_failure(result, replay_valid=False)

    def test_provider_exception_keeps_a_replayable_failure(self):
        provider = ScriptedProvider(ProviderError(ProviderErrorCategory.TRANSIENT, "fixture failure"))
        self.freeze(provider)
        result = self.run_arm(provider)
        self.assertEqual(len(provider.requests), 1)
        self.assert_preserved_failure(result, replay_valid=True)
        self.assertIsNone(result["receipt"]["actual_binding"])
        self.assertEqual(result["receipt"]["artifact_refs"], [])
        self.assertIn("provider-error", result["receipt"]["reason"])

    def test_post_call_deadline_is_a_retained_failure_not_completion(self):
        provider = ScriptedProvider(response("late-final"))
        self.freeze(provider)
        now = [0.0]
        deadline = self.f.envelope["transport_enforcement_metadata"]["budget"]["max_seconds"]
        provider.on_call = lambda *_: now.__setitem__(0, float(deadline))
        result = self.run_arm(provider, clock=lambda: now[0])
        self.assertEqual(len(provider.requests), 1)
        self.assert_preserved_failure(result, replay_valid=True)
        self.assertIn("post-call time budget", result["receipt"]["reason"])
        self.assertEqual(len(result["receipt"]["artifact_refs"]), 1)
        self.assertEqual(result["receipt"]["elapsed_seconds"], deadline)

    def test_rehashed_actual_binding_cannot_override_independent_trace_facts(self):
        provider = ScriptedProvider(response("a1-final"))
        self.freeze(provider)
        result = self.run_arm(provider)
        forged = copy.deepcopy(result["receipt"])
        forged["actual_binding"]["provider"]["ref"] = "forged-provider"
        forged_ref = self.f.write(result["receipt_ref"]["path"], forged)
        with self.assertRaisesRegex(EvaluationValidationError, "contradicts replayed execution facts"):
            verify_baseline_receipt(
                self.f.root, forged_ref, expected_envelope_ref=self.f.envelope_ref,
                schema_root=ROOT / "schemas",
            )
        self.assertEqual(len(provider.requests), 1)

    def test_changed_provider_capabilities_block_before_any_provider_call(self):
        provider = ScriptedProvider(response("must-not-run"))
        self.freeze(provider)
        changed = replace(provider.capabilities(), adapter_version="2.0.0")
        provider.capabilities = lambda: changed
        result = self.run_arm(provider)
        self.assertEqual(provider.requests, [])
        self.assertEqual(result["receipt"]["status"], "preflight-blocked")
        self.assertIn("actual transport binding drift", result["receipt"]["reason"])
        self.assertIsNone(result["receipt"]["actual_binding"])
        self.assertTrue(result["replay_valid"], result["replay_error"])
        self.assertEqual(result["receipt"]["artifact_refs"], [])

    def test_observed_model_drift_is_preserved_in_the_failed_receipt(self):
        provider = ScriptedProvider(replace(response("changed-model"), model="different-observed-model"))
        frozen = self.freeze(provider)
        result = self.run_arm(provider)
        self.assert_preserved_failure(result, replay_valid=True)
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(result["receipt"]["actual_binding"]["model"]["ref"], "different-observed-model")
        self.assertNotEqual(result["receipt"]["actual_binding"], frozen)
        self.assertIn("actual transport binding drift", result["receipt"]["reason"])

    def test_excess_observed_input_tokens_preserve_a_detected_post_call_failure(self):
        provider = ScriptedProvider(response("large-observed-input"))
        self.freeze(provider)
        limit = self.f.envelope["transport_enforcement_metadata"]["context"]["max_input_tokens"]
        provider.responses[0] = replace(provider.responses[0], usage=Usage(input_tokens=limit + 1, output_tokens=2))
        result = self.run_arm(provider)
        self.assert_preserved_failure(result, replay_valid=True)
        self.assertEqual(len(provider.requests), 1)
        self.assertIn("post-call input token budget", result["receipt"]["reason"])
        captured = self.f.doc(result["receipt"]["artifact_refs"][0]["path"])
        self.assertEqual(captured["usage"]["input_tokens"], limit + 1)

    def test_real_tool_exception_is_retained_and_stops_further_provider_calls(self):
        provider = ScriptedProvider(response("a2-call", tool=True), response("must-not-run"))
        self.freeze(provider, A2)
        tool = self.load_tool()

        def denied():
            raise PermissionError("synthetic local execution failure")

        with self.observe_tool_calls(tool, on_call=denied) as calls:
            result = self.run_arm(provider, tools=(tool,))
        self.assertEqual(calls, [{"value": "7"}])
        self.assertEqual(len(provider.requests), 1)
        self.assert_preserved_failure(result, replay_valid=True)
        self.assertIn("Tool failed", result["receipt"]["reason"])
        events_path = self.f.root / "work/TASK-MR-ES-FROZEN-001/A1/events.jsonl"
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
        tool_events = [event for event in events if event["event_type"] == "tool-call"]
        self.assertEqual([event["payload"]["status"] for event in tool_events], ["attempted", "failed"])

    def test_sanitized_response_is_the_only_output_persisted_with_the_trace(self):
        credential = "synthetic-baseline-credential-marker"
        private_reasoning = "synthetic-baseline-private-reasoning-marker"
        produced = replace(
            response("sanitized-response"),
            provider_metadata={"api_key": credential, "reasoning_content": private_reasoning},
            output=(ContentBlock("text", text="7"), ContentBlock("reasoning", text=private_reasoning)),
        )
        provider = ScriptedProvider(produced)
        self.freeze(provider)
        result = self.run_arm(provider)
        self.assert_preserved_failure(result, replay_valid=True)
        self.assertEqual(len(provider.requests), 1)
        output = self.f.doc(result["receipt"]["artifact_refs"][0]["path"])
        self.assertEqual(output["provider_metadata"]["api_key"], "[REDACTED:credential]")
        self.assertEqual(output["provider_metadata"]["reasoning_content"], "[OMITTED:hidden-reasoning]")
        attempt = self.f.root / "work/TASK-MR-ES-FROZEN-001/A1"
        for path in attempt.rglob("*"):
            if path.is_file():
                data = path.read_bytes()
                self.assertNotIn(credential.encode(), data, path.name)
                self.assertNotIn(private_reasoning.encode(), data, path.name)

    def test_tool_projection_ignores_bindings_for_another_task(self):
        provider = ScriptedProvider()
        self.freeze(provider, A2)
        metadata = copy.deepcopy(self.f.envelope["transport_enforcement_metadata"])
        expected = _tool_inputs(self.f.inputs(), metadata)
        qualification = self.f.doc(self.f.qualification_ref["path"])
        other_binding = copy.deepcopy(qualification["bindings"][0])
        other_snapshot = self.f.doc(other_binding["runtime_snapshot_ref"]["path"])
        other_task = copy.deepcopy(self.f.task)
        other_task["task_id"] = "TASK-OTHER-BASELINE"
        other_ref = self.f.write("baseline/other-task.json", other_task)
        other_snapshot["task_ref"] = self.f.c_ref("TASK-OTHER-BASELINE@r1", other_ref)
        other_binding["runtime_snapshot_ref"] = self.f.write("baseline/other-snapshot.json", other_snapshot)
        qualification["bindings"].append(other_binding)
        metadata["qualification_ref"] = self.f.write("baseline/multi-task-helper-input.json", qualification)
        # The existing A2 chain was fully qualified above. This added row is
        # only an input to the Task-projection helper, not a claim that a
        # complete multi-Task qualification or execution has been produced.
        self.assertEqual(_tool_inputs(self.f.inputs(), metadata), expected)
        self.assertEqual(provider.requests, [])


if __name__ == "__main__":
    unittest.main()
