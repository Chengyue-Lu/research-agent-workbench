"""Offline Driver execution proofs; fixture qualification is not live evidence."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.adapters.models import (
    ApiSessionLimits, Capability, ContentBlock, FinishReason, ModelResponse,
    ProviderCapabilities, Usage,
)
from research_workbench.artifacts.integrity import hash_file
from research_workbench.entry.driver import (
    EntryDriverError, ObservedExecutionBinding, execute_role_slice,
)
from research_workbench.execution import (
    CloseoutPin, load_runtime_bundle, validate_generic_execution_receipt,
)
from research_workbench.io import load_document
from tests.execution_fixtures import ExecutionViewFixture, SequenceClock, plain


ROOT = Path(__file__).resolve().parents[1]


class ScriptedRoleProvider:
    """Actual port calls against explicit independent offline metadata."""

    def __init__(self, *, usage=None, model="bounded-local-model", fail=False, deployment="local"):
        self.requests = []
        self.usage = usage if usage is not None else Usage(input_tokens=30, output_tokens=8)
        self.model, self.fail, self.deployment = model, fail, deployment
        self.metadata = {
            "provider": {"ref": "local", "version": "1", "content_hash": "1" * 64},
            "adapter": {"ref": "local-procedure", "version": "1.0.0", "content_hash": "1" * 64},
            "model": {"ref": "bounded-local-model", "version": "1.0.0", "content_hash": "1" * 64,
                      "model_class": "bounded", "slot": "worker", "capabilities": ["structured-output"]},
            "runtime": {"ref": "python", "version": "3.11+", "content_hash": "1" * 64},
            "host": {"ref": "bounded-test-host", "version": "1", "content_hash": "1" * 64},
        }
        self.supply = "supply-no-skill-contract-check@1.0.0"

    def capabilities(self):
        return ProviderCapabilities(provider="local", adapter_version="1.0.0",
            supported=frozenset({Capability.TEXT, Capability.STRUCTURED_OUTPUT}),
            models=("bounded-local-model",), deployment=self.deployment)

    def generate(self, request):
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("offline injected failure")
        return ModelResponse(response_id="OFFLINE-RESPONSE", provider="local", model=self.model,
            output=(ContentBlock("text", text=json.dumps({"decision": "finish", "childTasks": [],
                "summary": "bounded offline response", "limitations": ["offline scripted Provider"], "next_actions": []})),),
            finish_reason=FinishReason.COMPLETE, usage=self.usage)


def observe(provider):
    return ObservedExecutionBinding(copy.deepcopy(provider.metadata), provider.supply)


class EntryDriverTests(unittest.TestCase):
    def _inputs(self, root):
        helper = ExecutionViewFixture()
        bundle, inputs = helper._build(root)
        view = helper._produce(root, bundle, inputs)
        path = root / "view/resolved.yaml"
        path.write_text(json.dumps(view), encoding="utf-8")
        return CloseoutPin("bundle/manifest.yaml", hash_file(bundle.manifest_path)), CloseoutPin("view/resolved.yaml", hash_file(path))

    def _run(self, root, provider, **kwargs):
        bundle_ref, view_ref = self._inputs(root)
        options = dict(root=root, bundle_ref=bundle_ref, view_ref=view_ref,
            role="main", provider=provider, binding_observer=observe,
            output_dir="work/TASK-MR-ES-FROZEN-001/archive",
            output_path="work/TASK-MR-ES-FROZEN-001/role.json",
            output_contract="deterministic-check-report", attempt_id="ENTRY-OFFLINE-001",
            report_id="HOST-ENTRY-001", receipt_id="RECEIPT-ENTRY-001",
            accountable_owner="ENTRY offline test owner", schema_root=ROOT / "schemas",
            host_clock=SequenceClock("2026-08-26T00:00:01Z", "2026-08-26T00:00:02Z", "2026-08-26T00:00:03Z"),
            session_clock=lambda: 0.0)
        options.update(kwargs)
        return execute_role_slice(**options)

    def test_real_role_request_port_trace_host_closeout_and_independent_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            provider = ScriptedRoleProvider()
            result = self._run(root, provider)
            self.assertEqual("completed", result.host_report["status"], result.closeout_error)
            self.assertIsNone(result.closeout_error)
            self.assertIsNotNone(result.receipt_ref)
            self.assertEqual(1, len(provider.requests))
            request = provider.requests[0]
            self.assertEqual("main", request.metadata["entry_role"])
            self.assertIn("human", request.messages[0].content[0].text.lower())
            self.assertIn("Resolve evidence extraction", request.messages[1].content[0].text)
            self.assertEqual((), request.tools)
            self.assertEqual(1, result.host_report["actual_facts"]["provider_invocations"])
            self.assertEqual(8, result.host_report["actual_facts"]["output_tokens"])
            self.assertEqual(0, result.host_report["actual_facts"]["tool_invocations"])
            trace = load_document(root / result.trace_ref.path)
            self.assertEqual(["provider-request", "provider-response"], [item["kind"] for item in trace["messages"]])
            bundle = load_runtime_bundle("bundle/manifest.yaml", project_root=root, schema_root=ROOT / "schemas")
            replayed = validate_generic_execution_receipt(result.receipt_ref.path,
                expected_sha256=result.receipt_ref.sha256, bundle=bundle, schema_root=ROOT / "schemas")
            self.assertFalse(replayed.document["boundaries"]["task_completion"])
            self.assertEqual("action-capability-slice-only", replayed.document["completion_claim"])
            (root / result.host_report["artifacts"][0]["path"]).write_text("changed", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_generic_execution_receipt(result.receipt_ref.path,
                    expected_sha256=result.receipt_ref.sha256, bundle=bundle, schema_root=ROOT / "schemas")

    def test_observer_binding_or_supply_drift_blocks_before_provider(self):
        for subject in ("model", "supply"):
            with self.subTest(subject=subject), tempfile.TemporaryDirectory() as temp:
                provider = ScriptedRoleProvider()
                if subject == "model":
                    provider.metadata["model"]["ref"] = "actual-other-model"
                else:
                    provider.supply = "actual-other-supply@1.0.0"
                result = self._run(Path(temp), provider)
                self.assertEqual("blocked", result.host_report["status"])
                self.assertEqual([], provider.requests)
                self.assertIsNotNone(result.receipt_ref, result.closeout_error)
                self.assertEqual(0, result.host_report["actual_facts"]["provider_invocations"])

    def test_response_drift_is_retained_failed_and_never_falls_back(self):
        with tempfile.TemporaryDirectory() as temp:
            provider = ScriptedRoleProvider(model="observed-other-model")
            result = self._run(Path(temp), provider)
            self.assertEqual("failed", result.host_report["status"])
            self.assertEqual(1, len(provider.requests))
            self.assertFalse(result.host_report["actual_facts"]["complete"])
            self.assertIsNone(result.receipt_ref)
            self.assertIn("response-binding", " ".join(result.host_report["actual_facts"]["capture_gaps"]))

    def test_contemporaneous_observer_drift_blocks_before_actual_send(self):
        with tempfile.TemporaryDirectory() as temp:
            provider = ScriptedRoleProvider()
            calls = 0
            def changing_observer(actual_provider):
                nonlocal calls
                calls += 1
                if calls == 2:
                    actual_provider.metadata["model"]["ref"] = "new-configured-model"
                return observe(actual_provider)
            result = self._run(Path(temp), provider, binding_observer=changing_observer)
            self.assertEqual("failed", result.host_report["status"])
            self.assertEqual([], provider.requests)
            self.assertEqual("new-configured-model", result.host_report["actual_binding"]["model"]["ref"])
            self.assertEqual(0, result.host_report["actual_facts"]["provider_invocations"])

    def test_actual_usage_above_host_intersection_fails_after_real_call(self):
        with tempfile.TemporaryDirectory() as temp:
            provider = ScriptedRoleProvider(usage=Usage(input_tokens=30, output_tokens=9999))
            result = self._run(Path(temp), provider)
            self.assertEqual("failed", result.host_report["status"])
            self.assertEqual("HOST-BUDGET-VIOLATION", result.host_report["diagnostic"]["code"])
            self.assertEqual(9999, result.host_report["actual_facts"]["output_tokens"])
            self.assertEqual(1, len(provider.requests))
            self.assertIsNotNone(result.receipt_ref, result.closeout_error)

    def test_unknown_output_usage_is_not_promoted_to_complete_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self._run(Path(temp), ScriptedRoleProvider(usage=Usage(input_tokens=30)))
            self.assertEqual("failed", result.host_report["status"])
            self.assertIsNone(result.session.usage.output_tokens)
            self.assertIsNone(result.receipt_ref)
            self.assertIn("output-token-usage-unavailable", result.host_report["actual_facts"]["capture_gaps"])

    def test_actual_provider_exception_retains_attempted_request_and_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            provider = ScriptedRoleProvider(fail=True)
            result = self._run(Path(temp), provider)
            self.assertEqual("failed", result.host_report["status"])
            self.assertEqual(1, result.host_report["actual_facts"]["provider_invocations"])
            self.assertIsNone(result.receipt_ref)
            self.assertEqual("failed", result.session.status.value)
            self.assertEqual(1, len(provider.requests))

    def test_cancel_before_dispatch_retains_failed_slice_without_fake_call(self):
        with tempfile.TemporaryDirectory() as temp:
            provider = ScriptedRoleProvider()
            result = self._run(Path(temp), provider, cancel_requested=lambda: True)
            self.assertEqual("failed", result.host_report["status"])
            self.assertEqual("safe-paused", result.session.status.value)
            self.assertEqual([], provider.requests)
            self.assertIsNotNone(result.receipt_ref, result.closeout_error)

    def test_write_scope_remote_policy_and_limits_fail_before_provider(self):
        cases = ({"output_path": "outside/response.json"},
            {"limits": ApiSessionLimits(max_model_turns=1, max_tool_calls=0, max_parallel_tool_calls=0,
                max_tool_result_chars=1, max_output_tokens_per_turn=9999, max_seconds=30)})
        for options in cases:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temp:
                provider = ScriptedRoleProvider()
                with self.assertRaises(EntryDriverError):
                    self._run(Path(temp), provider, **options)
                self.assertEqual([], provider.requests)
        with tempfile.TemporaryDirectory() as temp:
            provider = ScriptedRoleProvider(deployment="remote")
            with self.assertRaises(EntryDriverError):
                self._run(Path(temp), provider)
            self.assertEqual([], provider.requests)


if __name__ == "__main__":
    unittest.main()
