"""Actual opt-in Guide request consumer, with an injected offline Provider."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from research_workbench.adapters.models.port import (
    Capability, ContentBlock, DataPolicyGap, FinishReason, ModelResponse,
    ProviderCapabilities, ProviderError, ProviderErrorCategory, ProviderRegistry,
    ToolCall, Usage,
)
from research_workbench.artifacts.admission import build_admission_mapping, sidecar_path_for
from research_workbench.entry.roles import EntryInputError
from research_workbench.entry.working_guide import ask_working_guide, build_working_guide_request
from tests.test_entry_roles import role_documents


class CapturingProvider:
    def __init__(self, negotiate=None, failure=None, deployment="local"):
        self.negotiate, self.failure, self.deployment = negotiate, failure, deployment
        self.requests = []
        self.response = ModelResponse(
            "guide-work-test", "offline-guide", "offline-model",
            (ContentBlock("text", text="The supplied result still needs human review."),),
            FinishReason.COMPLETE, tool_calls=(ToolCall("unexpected", "write-state", {}),),
            usage=Usage(input_tokens=None, output_tokens=9), warnings=("fixture-only",))

    def capabilities(self):
        if self.negotiate is not None:
            self.negotiate()
        return ProviderCapabilities("offline-guide", "test-only", frozenset({Capability.TEXT}),
                                    models=("offline-model",), deployment=self.deployment)

    def generate(self, request):
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        return self.response


class WorkingGuideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.task, self.profile = role_documents(self.root)
        self.task["permissions"]["filesystem"] = "read-only"
        self.profile["permission_ceiling"]["filesystem"] = "read-only"
        self.stops = [{"kind": "completed", "condition": "The supplied facts have been explained."}]

    def pin(self, path, raw):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        return {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}

    def arguments(self, **changes):
        values = dict(task=self.task, profile=self.profile, model="offline-model",
                      max_output_tokens=64, stop_conditions=self.stops)
        values.update(changes)
        return values

    def call(self, provider=None, **changes):
        provider = provider or CapturingProvider()
        registry = ProviderRegistry()
        registry.register("offline-guide", provider)
        response = ask_working_guide(self.root, providers=registry, provider_name="offline-guide",
                                    **self.arguments(**changes))
        return provider, response

    def sources(self):
        path = "sources/raw/document.txt"
        raw = b"Explicit synthetic source.\n"
        raw_ref = self.pin(path, raw)
        derivative = self.pin("artifacts/excerpt.txt", b"Selected excerpt.\n")
        admission = build_admission_mapping(
            original_filename="document.txt", admitted_path=path, content=raw,
            origin={"uri": "https://example.org/synthetic-source"},
            acquired_at="2026-10-11T00:00:00+08:00", operator="fixture",
            license_or_data_use="synthetic test input", parser_name="utf8-text",
            parser_version="1.0.0", sensitivity="fixture-only", egress_restriction="no-implied-upload")
        admission["derivatives"] = [{**derivative, "relation": "text-excerpt"}]
        sidecar = self.pin(sidecar_path_for(path), yaml.safe_dump(admission, sort_keys=False).encode("utf-8"))
        self.task["input_refs"] = [raw_ref, sidecar, derivative]
        return self.task["input_refs"]

    def test_actual_provider_consumes_work_without_full_control_and_preserves_cost_prose(self):
        self.task["goal"] = "Explain user fees and research costs; preserve this discussion."
        self.task["safe_pause_conditions"] = ["CONTROL_ONLY_SENTINEL"]
        original = copy.deepcopy(self.task)
        provider, response = self.call()
        self.assertIs(response, provider.response)
        self.assertEqual(1, len(provider.requests))
        request = provider.requests[0]
        payload = json.loads(request.messages[1].content[0].text)
        self.assertEqual({"work"}, set(payload))
        work = payload["work"]
        self.assertEqual("0.3.0", work["schema_version"])
        self.assertEqual("guide", work["role"])
        self.assertEqual(self.task["goal"], work["objective"]["goal"])
        self.assertEqual((self.root / "source.txt").read_bytes().decode(), work["materials"][0]["text"])
        self.assertEqual("ordinary-input", work["materials"][0]["material_provenance"]["kind"])
        self.assertEqual([], work["results"])
        self.assertNotIn("budget", work)
        self.assertNotIn("CONTROL_ONLY_SENTINEL", request.messages[1].content[0].text)
        self.assertNotIn("caller_context", payload)
        self.assertEqual((), request.tools)
        self.assertEqual(64, request.max_output_tokens)
        self.assertEqual("0.1.0", request.metadata["source_task_version"])
        self.assertEqual(hashlib.sha256(request.messages[1].content[0].text.encode()).hexdigest(),
                         request.metadata["input_snapshot_sha256"])
        self.assertTrue(all(value is False for value in work["boundaries"].values()))
        self.assertEqual(original, self.task)

    def test_explicit_result_is_captured_in_separate_slot_without_contract_acceptance(self):
        result = self.pin("work/result.txt", b"An actual bounded result; review remains pending.\n")
        self.task["input_refs"].append(result)
        provider, _ = self.call(result_refs=[{"kind": "formal-handoff", "source_ref": result}])
        work = json.loads(provider.requests[0].messages[1].content[0].text)["work"]
        self.assertEqual(["source.txt"], [item["path"] for item in work["materials"]])
        record, = work["results"]
        self.assertEqual(result, record["source_ref"])
        self.assertEqual((self.root / result["path"]).read_bytes().decode(), record["text"])
        self.assertEqual("captured-utf8-bytes-and-task-pin", record["verification_scope"])
        self.assertEqual("not-established", record["contract_validation"])
        self.assertEqual("not-established", record["scientific_qualification"])
        self.assertFalse(record["task_completion"])

    def test_raw_admission_derivative_reach_actual_request_with_relations(self):
        refs = self.sources()
        provider, _ = self.call()
        materials = json.loads(provider.requests[0].messages[1].content[0].text)["work"]["materials"]
        self.assertEqual(["raw-source", "source-admission", "source-derivative"],
                         [item["material_provenance"]["kind"] for item in materials])
        self.assertEqual(refs[0], materials[2]["material_provenance"]["raw_ref"])
        self.assertEqual(refs[1], materials[2]["material_provenance"]["admission_ref"])
        self.assertEqual(refs[2], materials[2]["material_provenance"]["derivative_ref"])
        self.assertTrue(all(not item["material_provenance"]["permission_grant"] for item in materials))

    def test_missing_source_closure_and_result_provenance_bypass_block_before_call(self):
        refs = self.sources()
        for arguments in ({"material_refs": refs[:1]},
                          {"material_refs": refs[1:], "result_refs": [{"kind": "result-artifact", "source_ref": refs[0]}]}):
            provider = CapturingProvider()
            with self.subTest(arguments=arguments), self.assertRaises(EntryInputError):
                self.call(provider, **arguments)
            self.assertEqual([], provider.requests)

    def test_selected_subset_does_not_read_unselected_task_inputs(self):
        secret = self.pin("unselected.txt", b"unselected private facts")
        self.task["input_refs"].append(secret)
        original = Path.read_bytes

        def guard(path):
            if path == self.root / secret["path"]:
                self.fail("unselected Task reference was opened")
            return original(path)

        with patch.object(Path, "read_bytes", guard):
            provider, _ = self.call(material_refs=self.task["input_refs"][:1])
        self.assertNotIn("unselected private facts", provider.requests[0].messages[1].content[0].text)

    def test_explicit_empty_selection_cannot_trigger_legacy_default_reads(self):
        with patch("research_workbench.entry.roles.read_pinned_inputs", side_effect=AssertionError("capture forbidden")):
            with self.assertRaisesRegex(EntryInputError, "explicit empty selection"):
                self.call(material_refs=())

    def test_result_outside_task_and_duplicate_or_flat_selectors_block_before_call(self):
        result = self.pin("work/result.txt", b"Unapproved result")
        for selectors in ([{"kind": "result-artifact", "source_ref": result}],
                          [{"kind": "result-artifact", "source_ref": self.task["input_refs"][0]}] * 2,
                          [{"kind": "result-artifact", **result}]):
            provider = CapturingProvider()
            with self.subTest(selectors=selectors), self.assertRaises(EntryInputError):
                self.call(provider, material_refs=(), result_refs=selectors)
            self.assertEqual([], provider.requests)

    def test_semantic_record_cannot_claim_an_unselected_source(self):
        unused = self.pin("unused.txt", b"not captured")
        self.task["input_refs"].append(unused)
        record = {"statement": "Claimed source", "source_ref": unused}
        with patch("research_workbench.entry.roles.read_pinned_inputs", side_effect=AssertionError("capture forbidden")):
            for field in ("necessary_decisions", "counterevidence"):
                with self.subTest(field=field), self.assertRaisesRegex(EntryInputError, "must be captured"):
                    self.call(material_refs=self.task["input_refs"][:1], **{field: [record]})

    def test_control_permission_skill_model_and_output_grant_still_block(self):
        cases = [{"max_output_tokens": 129}, {"model": "unknown"}]
        for field, value in (("permissions", {**self.task["permissions"], "filesystem": "worktree-write"}),
                             ("required_skills", ["unloaded@1.0.0"]), ("delegation", {"allowed": True}),
                             ("schema_version", "0.3.0")):
            task = copy.deepcopy(self.task)
            task[field] = value
            cases.append({"task": task})
        missing = copy.deepcopy(self.task)
        del missing["budget"]
        cases.append({"task": missing})
        for arguments in cases:
            provider = CapturingProvider()
            with self.subTest(arguments=arguments), self.assertRaises(EntryInputError):
                self.call(provider, **arguments)
            self.assertEqual([], provider.requests)

    def test_missing_explicit_output_parameter_is_not_replaced_by_fixed_default(self):
        arguments = self.arguments()
        del arguments["max_output_tokens"]
        with self.assertRaises(TypeError):
            build_working_guide_request(self.root, **arguments)

    def test_provider_negotiation_cannot_weaken_local_network_policy(self):
        provider = CapturingProvider(deployment="remote")
        with self.assertRaises(DataPolicyGap):
            self.call(provider)
        self.assertEqual([], provider.requests)

    def test_material_and_result_drift_after_negotiation_block_actual_generation(self):
        result = self.pin("work/result.txt", b"Pinned result")
        self.task["input_refs"].append(result)
        for path in ("source.txt", result["path"]):
            original = (self.root / path).read_bytes()
            provider = CapturingProvider(negotiate=lambda: (self.root / path).write_bytes(b"drift"))
            with self.subTest(path=path), self.assertRaisesRegex(EntryInputError, "hash drift|hash mismatch"):
                self.call(provider, result_refs=[{"kind": "result-artifact", "source_ref": result}])
            self.assertEqual([], provider.requests)
            (self.root / path).write_bytes(original)

    def test_cancellation_before_capture_and_before_dispatch_prevents_calls(self):
        with patch("research_workbench.entry.roles.read_pinned_inputs", side_effect=AssertionError("capture forbidden")):
            with self.assertRaisesRegex(EntryInputError, "before capture"):
                self.call(cancel_requested=lambda: True)
        checks = iter((False, True))
        provider = CapturingProvider()
        with self.assertRaisesRegex(EntryInputError, "before dispatch"):
            self.call(provider, cancel_requested=lambda: next(checks))
        self.assertEqual([], provider.requests)

    def test_returned_unknown_usage_and_tool_call_are_preserved_without_writes(self):
        self.pin("main-chat.txt", b"private main history")
        self.pin("main-state.json", b'{"status":"waiting"}')
        before = {path.relative_to(self.root).as_posix(): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        provider, response = self.call()
        self.assertIsNone(response.usage.input_tokens)
        self.assertIsNone(response.usage.total_tokens)
        self.assertEqual(9, response.usage.output_tokens)
        self.assertEqual(provider.response.tool_calls, response.tool_calls)
        self.assertNotIn("private main history", provider.requests[0].messages[1].content[0].text)
        self.assertEqual(before, {path.relative_to(self.root).as_posix(): path.read_bytes()
                                for path in self.root.rglob("*") if path.is_file()})

    def test_cancellation_during_final_pin_check_prevents_dispatch(self):
        from research_workbench.entry.roles import read_pinned_inputs
        cancelled = False

        def final_read(root, references):
            nonlocal cancelled
            snapshots = read_pinned_inputs(root, references)
            cancelled = True
            return snapshots

        provider = CapturingProvider()
        with patch("research_workbench.entry.working_guide.read_pinned_inputs", final_read):
            with self.assertRaisesRegex(EntryInputError, "before dispatch"):
                self.call(provider, cancel_requested=lambda: cancelled)
        self.assertEqual([], provider.requests)

    def test_provider_failure_is_preserved_without_retry_or_fallback(self):
        failure = ProviderError(ProviderErrorCategory.TRANSIENT, "synthetic failure", retryable=True)
        provider = CapturingProvider(failure=failure)
        with self.assertRaises(ProviderError) as caught:
            self.call(provider)
        self.assertIs(failure, caught.exception)
        self.assertEqual(1, len(provider.requests))


if __name__ == "__main__":
    unittest.main()
