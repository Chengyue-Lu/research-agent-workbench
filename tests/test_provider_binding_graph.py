"""Opt-in graph consumption, credential-boundary drift and independent replay."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from research_workbench.adapters.models.configured import ConfiguredProvider
from research_workbench.adapters.models.port import ContentBlock, Message, ModelRequest, ProviderError
from research_workbench.adapters.models.provider_binding import (
    GRAPH_POLICY, observe_provider_binding, read_provider_binding_manifest, stage_provider_binding,
)
from research_workbench.evaluation.pins import EvaluationInputs, EvaluationValidationError
from research_workbench.adapters.models.provider_source_closure import SourceClosureError
from research_workbench.execution.baseline import run_baseline_session
from research_workbench.execution.baseline_closeout import verify_baseline_receipt


ROOT = Path(__file__).resolve().parents[1]
COMPONENT_NAME = "_rwb_source_bound_components"


def _components():
    if COMPONENT_NAME not in sys.modules:
        spec = importlib.util.spec_from_file_location(COMPONENT_NAME,
            ROOT / "tests/fixtures/provider_binding_graph_v1/components.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[COMPONENT_NAME] = module
        spec.loader.exec_module(module)
    return sys.modules[COMPONENT_NAME]


def _unexpected(*args, **kwargs):
    raise AssertionError("mutated helper must be rejected before it is called")


class ProviderBindingGraphTests(unittest.TestCase):
    def setUp(self):
        from test_provider_binding import configured_fixture
        temporary = tempfile.TemporaryDirectory(prefix="rwb-provider-graph-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        original = configured_fixture(self.root)
        module = _components()
        self.provider = ConfiguredProvider(original.profile, original.resolved_config,
            module.SyntheticCredential(), module.SyntheticTransport(), self.root)

    def inputs(self):
        return EvaluationInputs(self.root, ROOT / "schemas")

    def stage(self):
        return stage_provider_binding(self.provider, root=self.root, destination="graph-binding",
                                      source_closure=True, include_conformance=True)

    def bound(self, reference):
        manifest = read_provider_binding_manifest(self.inputs(), reference).to_mapping()
        return ConfiguredProvider(self.provider.profile, self.provider.resolved_config,
            self.provider.credential, self.provider.transport, self.root,
            manifest["implementation_closure_ref"])

    def request(self):
        return ModelRequest(model="deepseek-flash",
                            messages=(Message("user", (ContentBlock("text", text="Return 7."),)),),
                            max_output_tokens=16)

    def test_opt_in_manifest_consumes_complete_pinned_graph_and_actual_provider(self):
        reference = self.stage()
        inputs = self.inputs()
        manifest = read_provider_binding_manifest(inputs, reference)
        document = manifest.to_mapping()
        self.assertEqual(document["version"], "1.1.0")
        self.assertEqual(document["binding_policy_version"], GRAPH_POLICY)
        graph = inputs.read(document["implementation_closure_ref"])
        self.assertIn("research_workbench.evaluation.pins", graph["modules"])
        self.assertIn("research_workbench.adapters", graph["modules"])
        self.assertIn("research_workbench.adapters.models.profile_conformance", graph["modules"])
        self.assertIn(document["implementation_closure_ref"]["path"], inputs.hashes)
        bound = self.bound(reference)
        observed = observe_provider_binding(bound, inputs=self.inputs(), manifest_ref=reference)
        self.assertEqual(observed["content_hash"], manifest.root)
        response = bound.generate(self.request())
        self.assertEqual(response.output[0].text, "7")
        self.assertEqual(bound.credential.resolutions, 1)
        self.assertEqual(len(bound.transport.requests), 1)

    def test_unbound_provider_and_cleared_graph_ref_cannot_use_new_manifest(self):
        reference = self.stage()
        with self.assertRaisesRegex(EvaluationValidationError, "opted into"):
            observe_provider_binding(self.provider, inputs=self.inputs(), manifest_ref=reference)
        bound = self.bound(reference)
        object.__setattr__(bound, "_implementation_closure_ref", None)
        with self.assertRaises(EvaluationValidationError):
            bound.generate(self.request())
        self.assertEqual(bound.credential.resolutions, 0)
        self.assertEqual(bound.transport.requests, [])

    def test_source_bound_instance_cannot_downgrade_to_legacy_manifest(self):
        reference = self.stage()
        bound = self.bound(reference)
        legacy = stage_provider_binding(self.provider, root=self.root, destination="legacy-binding")
        with self.assertRaisesRegex(EvaluationValidationError, "cannot use a legacy"):
            observe_provider_binding(bound, inputs=self.inputs(), manifest_ref=legacy)
        with self.assertRaisesRegex(EvaluationValidationError, "cannot stage a legacy"):
            stage_provider_binding(bound, root=self.root, destination="downgrade-binding")
        self.assertFalse((self.root / "downgrade-binding").exists())
        self.assertEqual(bound.credential.resolutions, 0)
        self.assertEqual(bound.transport.requests, [])

    def test_outside_seven_helper_and_retained_alias_mutation_stop_before_key(self):
        reference = self.stage()
        bound = self.bound(reference)
        from research_workbench.evaluation import pins
        with patch.object(pins, "sha", _unexpected):
            with self.assertRaises((ProviderError, EvaluationValidationError)):
                bound.generate(self.request())
        self.assertEqual(bound.credential.resolutions, 0)
        self.assertEqual(bound.transport.requests, [])

    def test_changed_archive_or_outer_graph_ref_never_reaches_credential(self):
        reference = self.stage()
        manifest = read_provider_binding_manifest(self.inputs(), reference).to_mapping()
        graph_ref = manifest["implementation_closure_ref"]
        graph = self.inputs().read(graph_ref)
        bound = self.bound(reference)
        source_ref = next(iter(graph["modules"].values()))["source_ref"]
        path = self.root / source_ref["path"]
        path.write_bytes(path.read_bytes() + b"\n# drift\n")
        with self.assertRaises((ProviderError, EvaluationValidationError)):
            bound.generate(self.request())
        self.assertEqual(bound.credential.resolutions, 0)

    def test_version_pairing_cannot_downgrade_graph_fields(self):
        reference = self.stage()
        document = read_provider_binding_manifest(self.inputs(), reference).to_mapping()
        variants = []
        wrong = copy.deepcopy(document)
        wrong["version"] = "1.0.0"
        variants.append(wrong)
        wrong = copy.deepcopy(document)
        wrong["binding_policy_version"] = "provider-binding-v2"
        variants.append(wrong)
        wrong = copy.deepcopy(document)
        del wrong["implementation_closure_ref"]
        variants.append(wrong)
        for candidate in variants:
            with self.subTest(candidate=candidate["version"]):
                with self.assertRaises(EvaluationValidationError):
                    self.inputs().validate("provider_binding_manifest", candidate)

    def test_rehashed_false_source_claim_is_rejected_independently(self):
        reference = self.stage()
        manifest = read_provider_binding_manifest(self.inputs(), reference).to_mapping()
        graph_ref = manifest["implementation_closure_ref"]
        graph = self.inputs().read(graph_ref)
        claims = graph["modules"]["research_workbench.evaluation.pins"]["claims"]["compiled_callables"]
        claims[next(iter(claims))] = "0" * 64
        raw = json.dumps(graph).encode()
        (self.root / graph_ref["path"]).write_bytes(raw)
        manifest["implementation_closure_ref"]["sha256"] = hashlib.sha256(raw).hexdigest()
        raw = json.dumps(manifest).encode()
        path = self.root / "forged-manifest.json"
        path.write_bytes(raw)
        forged_ref = {"path": path.name, "sha256": hashlib.sha256(raw).hexdigest()}
        with self.assertRaises((EvaluationValidationError, SourceClosureError)):
            read_provider_binding_manifest(self.inputs(), forged_ref)
        self.assertEqual(self.provider.credential.resolutions, 0)
        self.assertEqual(self.provider.transport.requests, [])

    def test_cold_manifest_read_does_not_import_synthetic_component(self):
        reference = self.stage()
        script = """import json,sys
from pathlib import Path
from research_workbench.evaluation.pins import EvaluationInputs
from research_workbench.adapters.models.provider_binding import read_provider_binding_manifest
manifest=read_provider_binding_manifest(EvaluationInputs(sys.argv[1],sys.argv[2]),json.loads(sys.argv[3]))
assert '_rwb_source_bound_components' not in sys.modules
assert manifest.to_mapping()['version']=='1.1.0'
print(manifest.root)
"""
        completed = subprocess.run([sys.executable, "-c", script, str(self.root),
            str(ROOT / "schemas"), json.dumps(reference)], cwd=ROOT,
            capture_output=True, text=True, timeout=120)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stdout.strip(), read_provider_binding_manifest(self.inputs(), reference).root)

    def frozen_envelope(self):
        from test_provider_binding import ProviderBindingTests
        reference = self.stage()
        self.provider = self.bound(reference)
        harness = SimpleNamespace(root=self.root, provider=self.provider,
                                  stage=lambda: reference, inputs=self.inputs)
        return ProviderBindingTests.frozen_envelope(harness)

    def run_baseline(self):
        fixture, reference, inputs, envelope = self.frozen_envelope()
        self.assertEqual(envelope["version"], "1.2.0")
        envelope_ref = fixture.write("baseline/graph-envelope.json", envelope)
        fixture.envelope_ref = envelope_ref
        result = run_baseline_session(self.root, envelope_ref=envelope_ref,
            expected_protocol_ref=fixture.protocol_ref, provider=self.provider,
            attempt_path="work/TASK-MR-ES-FROZEN-001/GRAPH", attempt_id="GRAPH-SYNTHETIC",
            receipt_id="GRAPH-SYNTHETIC-RECEIPT", utc_clock=lambda: "2026-08-24T12:00:00Z",
            schema_root=ROOT / "schemas")
        self.assertEqual(result["receipt"]["status"], "completed", result["receipt"]["reason"])
        self.assertTrue(result["replay_valid"], result["replay_error"])
        return fixture, reference, inputs, envelope_ref, result

    def test_v12_baseline_consumes_graph_sources_at_each_use_and_replays_cold(self):
        fixture, reference, inputs, envelope_ref, result = self.run_baseline()
        manifest = read_provider_binding_manifest(fixture.inputs(), reference).to_mapping()
        graph_ref = manifest["implementation_closure_ref"]
        graph = fixture.inputs().read(graph_ref)
        graph_refs = [graph_ref, *(row["source_ref"] for row in graph["modules"].values())]
        for ref in graph_refs:
            self.assertIn(ref["path"], inputs.hashes)
        for fact_ref in result["receipt"]["fact_refs"]:
            fact = fixture.doc(fact_ref["path"])
            for ref in graph_refs:
                self.assertIn(ref, fact["use_refs"])
        script = """import json,sys
sys.path.insert(0,sys.argv[5])
from unittest.mock import patch
from research_workbench.execution.baseline_closeout import verify_baseline_receipt
from research_workbench.adapters.models.configured import ConfiguredProvider
from research_workbench.adapters.models.http import EnvironmentCredential,UrllibTransport
with patch.object(ConfiguredProvider,'generate',side_effect=AssertionError('Provider rerun')), \\
     patch.object(ConfiguredProvider,'capabilities',side_effect=AssertionError('Provider reobservation')), \\
     patch.object(EnvironmentCredential,'available',side_effect=AssertionError('Credential probe')), \\
     patch.object(EnvironmentCredential,'resolve',side_effect=AssertionError('Credential read')), \\
     patch.object(UrllibTransport,'send',side_effect=AssertionError('Network call')):
    result=verify_baseline_receipt(sys.argv[1],json.loads(sys.argv[2]),expected_envelope_ref=json.loads(sys.argv[3]),schema_root=sys.argv[4])
assert '_rwb_source_bound_components' not in sys.modules
print(result['status'])
"""
        completed = subprocess.run([sys.executable, "-I", "-c", script, str(self.root),
            json.dumps(result["receipt_ref"]), json.dumps(envelope_ref), str(ROOT / "schemas"),
            str(ROOT / "src")], capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stdout.strip(), "completed")
        self.assertEqual(self.provider.credential.resolutions, 1)
        self.assertEqual(len(self.provider.transport.requests), 1)

    def test_v12_cold_replay_rejects_helper_source_drift_without_provider_reuse(self):
        fixture, reference, _inputs, envelope_ref, result = self.run_baseline()
        manifest = read_provider_binding_manifest(fixture.inputs(), reference).to_mapping()
        graph = fixture.inputs().read(manifest["implementation_closure_ref"])
        helper_ref = graph["modules"]["research_workbench.evaluation.pins"]["source_ref"]
        path = self.root / helper_ref["path"]
        path.write_bytes(path.read_bytes() + b"\n# retained helper archive drift\n")
        with patch.object(ConfiguredProvider, "generate", side_effect=AssertionError("Provider rerun")):
            with self.assertRaisesRegex(EvaluationValidationError, "source closure validation failed"):
                verify_baseline_receipt(self.root, result["receipt_ref"], expected_envelope_ref=envelope_ref,
                                        schema_root=ROOT / "schemas")
        self.assertEqual(self.provider.credential.resolutions, 1)
        self.assertEqual(len(self.provider.transport.requests), 1)

    def test_v12_rehashed_use_facts_require_exact_source_closure_per_invocation(self):
        from test_baseline_replay_integrity import BaselineReplayIntegrityTests
        fixture, reference, _inputs, envelope_ref, result = self.run_baseline()
        manifest = read_provider_binding_manifest(fixture.inputs(), reference).to_mapping()
        graph = fixture.inputs().read(manifest["implementation_closure_ref"])
        omitted = graph["modules"]["research_workbench.evaluation.pins"]["source_ref"]
        self.f = fixture
        BaselineReplayIntegrityTests.load_result(self, result)
        paths = [self.receipt_path, self.events_path, self.receipt["trace_index_ref"]["path"],
                 self.receipt["validation_ref"]["path"], *(ref["path"] for ref in self.receipt["fact_refs"])]
        originals = {path: (self.root / path).read_bytes() for path in paths}
        extra = fixture.write("unrelated.json", {"unrelated": True})
        for mutation in ("missing", "extra"):
            with self.subTest(mutation=mutation):
                for path, raw in originals.items():
                    (self.root / path).write_bytes(raw)
                BaselineReplayIntegrityTests.load_result(self, result)
                fact = next(item for item in self.facts if item["phase"] == "before")
                if mutation == "missing":
                    fact["use_refs"] = [ref for ref in fact["use_refs"] if ref != omitted]
                else:
                    fact["use_refs"].append(extra)
                BaselineReplayIntegrityTests.resign(self)
                with self.assertRaisesRegex(EvaluationValidationError, "use.boundary"):
                    verify_baseline_receipt(self.root, self.receipt_ref, expected_envelope_ref=envelope_ref,
                                            schema_root=ROOT / "schemas")
        self.assertEqual(self.provider.credential.resolutions, 1)
        self.assertEqual(len(self.provider.transport.requests), 1)
