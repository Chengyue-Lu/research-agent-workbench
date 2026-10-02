"""Synthetic actual-instance closure and independently derived file replay."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_workbench.adapters.models import wire_codecs
from research_workbench.adapters.models.configured import ConfiguredProvider
from research_workbench.adapters.models.http import HttpResponse
from research_workbench.adapters.models.profile_configuration import ProviderAdapterConfigV2, resolve_profile_configuration
from research_workbench.adapters.models.provider_binding import (
    assert_configured_provider_binding, capture_configured_provider_binding,
    observe_provider_binding, read_provider_binding_manifest, stage_provider_binding,
)
from research_workbench.evaluation.pins import EvaluationInputs, EvaluationValidationError
from research_workbench.execution.baseline import observe_baseline_binding
from research_workbench.execution.baseline import run_baseline_session
from research_workbench.execution.baseline_closeout import verify_baseline_receipt
from research_workbench.execution.baseline_envelope import compile_baseline_envelope, validate_baseline_envelope
from tests.baseline_fixtures import A1, ROOT, BaselineFixture


class SyntheticCredential:
    label = "env:RWB_BINDING_SYNTHETIC_KEY"

    def __init__(self):
        self.resolutions = 0

    def available(self):
        raise AssertionError("binding must never probe credential presence")

    def resolve(self):
        self.resolutions += 1
        return "synthetic-binding-credential"


class SyntheticTransport:
    def __init__(self):
        self.max_response_bytes = 65536
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        document = {"id": "binding-synthetic-response", "model": "deepseek-flash", "status": "completed",
                    "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "7"}]}],
                    "usage": {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7}}
        return HttpResponse(200, {}, json.dumps(document).encode())


def configured_fixture(root: Path) -> ConfiguredProvider:
    document = json.loads((ROOT / "registry/providers/profiles/deepseek-responses-v1.json").read_text(encoding="utf-8"))
    # This fixture declares a single internally agreed profile contract, rather
    # than accepting a transient registry/profile authoring mismatch.
    document["implementation"]["codec_version"] = wire_codecs.CODEC_VERSION
    family = document["protocol"]["family"]
    document["mapping"] = {f"{name}_policy_id": f"{family}:{name}:v1" for name in (
        "role", "tool", "schema", "usage", "finish", "error",
    )}
    document["generation"]["parameter_profile_id"] = f"{family}:parameters:v1"
    raw = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode()
    path = root / "binding-input/profile.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    config = ProviderAdapterConfigV2.from_mapping({
        "adapter_id": "synthetic-deepseek-binding", "enabled": True,
        "profile_ref": {"path": "binding-input/profile.json", "sha256": hashlib.sha256(raw).hexdigest()},
        "model_selector": {"kind": "literal", "value": "deepseek-flash"},
        "credential_source": {"kind": "environment", "name": "RWB_BINDING_SYNTHETIC_KEY"},
        "capabilities": ["text"], "transport": {"timeout_seconds": 10, "max_response_bytes": 65536,
                                              "redirect_policy": "deny", "retry_policy": "none"},
        "conformance_ref": None,
    })
    profile, resolved = resolve_profile_configuration(config, root=root)
    return ConfiguredProvider(profile, resolved, SyntheticCredential(), SyntheticTransport(), root)


def _replacement(*_args, **_kwargs):
    raise AssertionError("replaced helper must not execute")


class ProviderBindingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.provider = configured_fixture(self.root)

    def inputs(self):
        return EvaluationInputs(self.root, ROOT / "schemas")

    def stage(self):
        return stage_provider_binding(self.provider, root=self.root, destination="binding-frozen")

    def test_manifest_bytes_and_canonical_root_have_distinct_meanings(self):
        reference = self.stage()
        manifest = read_provider_binding_manifest(self.inputs(), reference)
        adapter = observe_provider_binding(self.provider, inputs=self.inputs(), manifest_ref=reference)
        self.assertEqual(adapter["content_hash"], manifest.root)
        self.assertNotEqual(reference["sha256"], manifest.root)
        self.assertEqual(adapter["ref"], "research_workbench.adapters.models.configured.ConfiguredProvider")
        self.assertEqual(self.provider.credential.resolutions, 0)
        self.assertEqual(self.provider.transport.requests, [])
        public = (self.root / reference["path"]).read_text(encoding="utf-8")
        self.assertNotIn(str(self.root), public)
        self.assertNotIn("synthetic-binding-credential", public)

    def test_new_profile_never_falls_back_to_legacy_single_file_binding(self):
        with self.assertRaisesRegex(EvaluationValidationError, "explicit binding manifest"):
            observe_baseline_binding(self.provider, model="deepseek-flash", model_slot="primary")
        self.assertEqual(self.provider.credential.resolutions, 0)
        self.assertEqual(self.provider.transport.requests, [])

    def test_endpoint_and_timeout_only_drift_fail_before_credential_resolution(self):
        reference = self.stage()
        original = self.provider.profile
        # Simulate hostile mutation without weakening the frozen dataclass.
        changed = original.to_mapping()
        changed["endpoint"]["origin"] = "https://changed.example.test"
        from research_workbench.adapters.models.profile_configuration import ProviderApiProfile
        object.__setattr__(self.provider, "profile", ProviderApiProfile.from_mapping(changed))
        with self.assertRaisesRegex(EvaluationValidationError, "actual profile differs"):
            observe_provider_binding(self.provider, inputs=self.inputs(), manifest_ref=reference)
        object.__setattr__(self.provider, "profile", original)
        config = copy.deepcopy(dict(self.provider.binding_descriptor()["resolved_config"]))
        config["transport"]["timeout_seconds"] = 11
        object.__setattr__(self.provider, "resolved_config", config)
        with self.assertRaisesRegex(EvaluationValidationError, "actual config differs"):
            observe_provider_binding(self.provider, inputs=self.inputs(), manifest_ref=reference)
        self.assertEqual(self.provider.credential.resolutions, 0)
        self.assertEqual(self.provider.transport.requests, [])

    def test_runtime_helper_replacement_is_not_hidden_by_unchanged_source_bytes(self):
        snapshot = capture_configured_provider_binding(self.provider)
        with patch.object(wire_codecs, "encode_profile_request", _replacement):
            with self.assertRaisesRegex(EvaluationValidationError, "absent or replaced|imported helper"):
                assert_configured_provider_binding(self.provider, snapshot)
        self.assertEqual(self.provider.credential.resolutions, 0)
        self.assertEqual(self.provider.transport.requests, [])

    def test_runtime_policy_registry_and_imported_class_alias_are_verified(self):
        snapshot = capture_configured_provider_binding(self.provider)
        changed = {key: dict(value) for key, value in wire_codecs.NATIVE_PARAMETER_REGISTRY.items()}
        changed[("deepseek", "responses", "nonthinking")] = {"reasoning": {"effort": "high"}}
        with patch.object(wire_codecs, "NATIVE_PARAMETER_REGISTRY", changed):
            with self.assertRaisesRegex(EvaluationValidationError, "policy registry differs"):
                assert_configured_provider_binding(self.provider, snapshot)
        import research_workbench.adapters.models.configured as configured
        with patch.object(configured, "UrllibTransport", SyntheticTransport):
            with self.assertRaisesRegex(EvaluationValidationError, "imported class/helper alias"):
                assert_configured_provider_binding(self.provider, snapshot)
        self.assertEqual(self.provider.credential.resolutions, 0)
        self.assertEqual(self.provider.transport.requests, [])

    def test_component_instance_method_shadow_cannot_avoid_source_binding(self):
        snapshot = capture_configured_provider_binding(self.provider)
        for component, method in ((self.provider.transport, "send"), (self.provider.credential, "resolve")):
            with patch.object(component, method, _replacement):
                with self.subTest(method=method), self.assertRaisesRegex(EvaluationValidationError, "component method was replaced"):
                    assert_configured_provider_binding(self.provider, snapshot)
        self.assertEqual(self.provider.credential.resolutions, 0)
        self.assertEqual(self.provider.transport.requests, [])

    def test_callable_keyword_defaults_are_checked_before_and_after_construction(self):
        snapshot = capture_configured_provider_binding(self.provider)
        original = wire_codecs._response.__kwdefaults__
        changed = {**original, "warnings": ("synthetic-changed-default",)}
        with patch.object(wire_codecs._response, "__kwdefaults__", changed):
            with self.assertRaisesRegex(EvaluationValidationError, "callable defaults differ"):
                assert_configured_provider_binding(self.provider, snapshot)
            with tempfile.TemporaryDirectory() as candidate:
                with self.assertRaisesRegex(EvaluationValidationError, "callable defaults differ"):
                    configured_fixture(Path(candidate))
        self.assertEqual(self.provider.credential.resolutions, 0)
        self.assertEqual(self.provider.transport.requests, [])

    def test_cold_manifest_rejects_missing_helper_forged_runtime_and_source_drift(self):
        reference = self.stage()
        original = json.loads((self.root / reference["path"]).read_text(encoding="utf-8"))
        for field in ("missing-helper", "forged-runtime", "other-python"):
            document = copy.deepcopy(original)
            if field == "missing-helper":
                document["implementation_refs"].pop()
            elif field == "forged-runtime":
                document["implementation_refs"][0]["runtime_fingerprint"] = "0" * 64
            else:
                document["code_runtime"]["version"] = "0.0.0"
            raw = json.dumps(document).encode()
            path = self.root / (field + ".json")
            path.write_bytes(raw)
            ref = {"path": path.name, "sha256": hashlib.sha256(raw).hexdigest()}
            with self.subTest(field=field), self.assertRaises(EvaluationValidationError):
                read_provider_binding_manifest(self.inputs(), ref)
        source = self.root / original["implementation_refs"][0]["source_ref"]["path"]
        source.write_bytes(source.read_bytes() + b"\n# changed archived source\n")
        with self.assertRaisesRegex(EvaluationValidationError, "hash mismatch"):
            read_provider_binding_manifest(self.inputs(), reference)

    def frozen_envelope(self):
        reference = self.stage()
        binding = observe_baseline_binding(self.provider, model="deepseek-flash", model_slot="primary",
                                           inputs=self.inputs(), provider_binding_manifest_ref=reference)
        fixture = BaselineFixture(self.root).build_baseline(A1)
        # The existing fixture defaults to legacy compile. Explicitly freeze
        # the already-observed configured binding before invoking v1.1.
        fixture.protocol["execution_binding"] = binding
        manifest = fixture.doc(fixture.manifest_ref["path"])
        # A separately declared synthetic A1 Task uses an injected fake HTTP
        # transport. This is a test input, never authorization for a real API.
        synthetic_task = copy.deepcopy(fixture.task)
        synthetic_task["task_id"] = "TASK-MR-ES-BINDING-001"
        synthetic_task["permissions"]["network"] = "synthetic-injected-transport"
        fixture.task_ref = fixture.write("binding-input/synthetic-task.json", synthetic_task)
        manifest["frozen_conditions"]["task_packet_refs"].append(fixture.task_ref)
        old_projection = fixture.public_payload_ref
        fixture.public_projection["task_ref"] = fixture.task_ref
        fixture.public_payload_ref = fixture.write("binding-input/public-projection.json", fixture.public_projection)
        context = manifest["frozen_conditions"]["context"]
        context["initial_context_refs"][context["initial_context_refs"].index(old_projection)] = fixture.public_payload_ref
        policy = fixture.doc(context["data_policy_ref"]["path"])
        policy["data_boundary"]["local_only"] = False
        context["data_policy_ref"] = fixture.write("binding-input/synthetic-data-policy.json", policy)
        manifest["frozen_conditions"]["budget"]["max_output_tokens"] = 64
        manifest["frozen_conditions"]["model"].update(model_id="deepseek-flash", provider_adapter=binding["adapter"]["ref"])
        manifest["frozen_conditions"]["host"].update(host_id=binding["host"]["ref"], runtime=binding["runtime"]["ref"])
        pool = fixture.doc(manifest["frozen_conditions"]["model"]["pool_ref"]["path"])
        pool["slots"][0]["provider_adapter"] = binding["adapter"]["ref"]
        manifest["frozen_conditions"]["model"]["pool_ref"] = fixture.write("baseline/model-pool.json", pool)
        fixture.manifest_ref = fixture.write("evaluation/manifest.json", manifest)
        fixture.protocol["manifest_ref"] = fixture.manifest_ref
        fixture.protocol_ref = fixture.write("evaluation/protocol.json", fixture.protocol)
        inputs = fixture.inputs()
        envelope = compile_baseline_envelope(inputs, protocol_ref=fixture.protocol_ref, task_ref=fixture.task_ref,
            public_payload_ref=fixture.public_payload_ref, arm_id=A1, envelope_id="CONFIGURED-A1", accountable_owner="Synthetic owner",
            provider_binding_manifest_ref=reference)
        return fixture, reference, inputs, envelope

    def test_v11_compiler_derives_full_explicit_closure_and_protocol_root(self):
        fixture, reference, inputs, envelope = self.frozen_envelope()
        self.assertEqual(envelope["version"], "1.1.0")
        self.assertEqual(envelope["transport_enforcement_metadata"]["provider_binding_manifest_ref"], reference)
        document = read_provider_binding_manifest(fixture.inputs(), reference).to_mapping()
        for ref in [reference, document["profile_ref"], document["resolved_config_ref"],
                    *(item["source_ref"] for item in document["implementation_refs"])]:
            self.assertIn(ref["path"], inputs.hashes)
        with self.assertRaisesRegex(EvaluationValidationError, "explicit Provider binding manifest"):
            compile_baseline_envelope(fixture.inputs(), protocol_ref=fixture.protocol_ref, task_ref=fixture.task_ref,
                public_payload_ref=fixture.public_payload_ref, arm_id=A1, envelope_id="DOWNGRADE", accountable_owner="Synthetic owner")

    def test_envelope_version_branches_reject_mixed_or_missing_manifest_fields(self):
        fixture, _reference, _inputs, envelope = self.frozen_envelope()
        downgraded = copy.deepcopy(envelope)
        downgraded["version"] = "1.0.0"
        missing = copy.deepcopy(envelope)
        del missing["transport_enforcement_metadata"]["provider_binding_manifest_ref"]
        for document in (downgraded, missing):
            with self.subTest(version=document["version"]), self.assertRaisesRegex(EvaluationValidationError, "schema"):
                validate_baseline_envelope(fixture.inputs(), document, expected_protocol_ref=fixture.protocol_ref)

    def test_complete_v11_baseline_replays_in_a_fresh_process_without_provider_calls(self):
        fixture, reference, _inputs, envelope = self.frozen_envelope()
        envelope_ref = fixture.write("baseline/configured-envelope.json", envelope)
        result = run_baseline_session(self.root, envelope_ref=envelope_ref, expected_protocol_ref=fixture.protocol_ref,
            provider=self.provider, attempt_path="work/TASK-MR-ES-FROZEN-001/CONFIGURED", attempt_id="CONFIGURED-SYNTHETIC",
            receipt_id="CONFIGURED-SYNTHETIC-RECEIPT", utc_clock=lambda: "2026-08-24T12:00:00Z", schema_root=ROOT / "schemas")
        self.assertEqual(result["receipt"]["status"], "completed", result["receipt"]["reason"])
        self.assertTrue(result["replay_valid"], result["replay_error"])
        self.assertEqual(self.provider.credential.resolutions, 1)
        self.assertEqual(len(self.provider.transport.requests), 1)
        script = """import json,sys,subprocess
sys.path.insert(0,sys.argv[5])
from unittest.mock import patch
from research_workbench.execution.baseline_closeout import verify_baseline_receipt
from research_workbench.adapters.models.configured import ConfiguredProvider
from research_workbench.adapters.models.http import EnvironmentCredential,UrllibTransport
receipt=json.loads(sys.argv[2]); envelope=json.loads(sys.argv[3])
with patch.object(ConfiguredProvider,'generate',side_effect=AssertionError('Provider rerun')), \\
     patch.object(ConfiguredProvider,'capabilities',side_effect=AssertionError('Provider reobservation')), \\
     patch.object(EnvironmentCredential,'available',side_effect=AssertionError('Credential probe')), \\
     patch.object(EnvironmentCredential,'resolve',side_effect=AssertionError('Credential read')), \\
     patch.object(UrllibTransport,'send',side_effect=AssertionError('Network call')), \\
     patch.object(subprocess,'Popen',side_effect=AssertionError('Replay subprocess')):
    result=verify_baseline_receipt(sys.argv[1],receipt,expected_envelope_ref=envelope,schema_root=sys.argv[4])
print(result['status'])
"""
        process = subprocess.run([sys.executable, "-I", "-c", script, str(self.root), json.dumps(result["receipt_ref"]),
                                  json.dumps(envelope_ref), str(ROOT / "schemas"), str(ROOT / "src")],
                                 capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stdout.strip(), "completed")
        manifest = read_provider_binding_manifest(fixture.inputs(), reference).to_mapping()
        archived_source = self.root / manifest["implementation_refs"][0]["source_ref"]["path"]
        archived_source.write_bytes(archived_source.read_bytes() + b"\n# cold-replay drift\n")
        with self.assertRaisesRegex(EvaluationValidationError, "hash mismatch"):
            verify_baseline_receipt(self.root, result["receipt_ref"], expected_envelope_ref=envelope_ref, schema_root=ROOT / "schemas")
        self.assertEqual(self.provider.credential.resolutions, 1)
        self.assertEqual(len(self.provider.transport.requests), 1)


if __name__ == "__main__":
    unittest.main()
