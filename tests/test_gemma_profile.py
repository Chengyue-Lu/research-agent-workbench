"""Offline exact Gemma Text composition; no credential or service is inspected."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

from jsonschema import Draft202012Validator

from research_workbench.adapters.models import wire_codecs
from research_workbench.adapters.models.configured import build_profile_provider
from research_workbench.adapters.models.http import HttpResponse
from research_workbench.adapters.models.port import (
    Capability, CapabilityGap, ContentBlock, FinishReason, Message, ModelNotSupported, ModelRequest, ProviderError,
    ProviderErrorCategory, ResponseFormat, ToolDefinition,
)
from research_workbench.adapters.models.profile_configuration import load_profile_configurations
from research_workbench.adapters.models.provider_binding import read_provider_binding_manifest, stage_provider_binding
from research_workbench.evaluation.pins import EvaluationInputs


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/provider_profiles_gemma_v1"
PROFILE = Path("registry/providers/profiles/google-gemma-content-v1.json")


class SyntheticCredential:
    label = "env:RWB_GEMMA_SYNTHETIC_KEY"

    def __init__(self):
        self.resolutions = 0
        self.presence_checks = 0

    def available(self):
        self.presence_checks += 1
        raise AssertionError("offline Gemma must not probe credential presence")

    def resolve(self):
        self.resolutions += 1
        return "synthetic-gemma-offline-token"


class SyntheticTransport:
    def __init__(self, document):
        self.max_response_bytes = 65536
        self.document = document
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return HttpResponse(200, {}, json.dumps(self.document).encode())


class GemmaProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.profile_bytes = (ROOT / PROFILE).read_bytes()
        self.document = json.loads(self.profile_bytes)
        self.profile_path = self.root / PROFILE
        self.profile_path.parent.mkdir(parents=True)
        self.profile_path.write_bytes(self.profile_bytes)
        self.config_path = self.root / "config.json"
        self.config_path.write_bytes((FIXTURE / "positive.config.json").read_bytes())
        self.config = load_profile_configurations(self.config_path)[0]
        self.credential = SyntheticCredential()
        self.transport = SyntheticTransport(json.loads((FIXTURE / "positive.response.json").read_bytes()))

    def build(self):
        return build_profile_provider(self.config, root=self.root,
                                      credential=self.credential, transport=self.transport)

    def request(self):
        return ModelRequest("gemma-4-26b-a4b-it", (Message("user", (ContentBlock("text", "synthetic input"),)),),
                            max_output_tokens=32)

    def assert_no_outbound(self):
        self.assertEqual(self.credential.resolutions, 0)
        self.assertEqual(self.credential.presence_checks, 0)
        self.assertEqual(self.transport.requests, [])

    def test_profile_and_configs_are_schema_valid_lf_pinned_files(self):
        schema = json.loads((ROOT / "schemas/v0.1.0/provider-api-profile.schema.json").read_bytes())
        Draft202012Validator(schema).validate(self.document)
        config_schema = json.loads((ROOT / "schemas/v0.1.0/provider-adapters-v2.schema.json").read_bytes())
        self.assertNotIn(b"\r", self.profile_bytes)
        for name in ("positive.config.json", "disabled.config.json"):
            raw = (FIXTURE / name).read_bytes()
            self.assertNotIn(b"\r", raw)
            config = json.loads(raw)
            Draft202012Validator(config_schema).validate(config)
            self.assertEqual(config["adapters"][0]["profile_ref"], {
                "path": PROFILE.as_posix(), "sha256": hashlib.sha256(self.profile_bytes).hexdigest(),
            })

    def test_complete_factory_text_roundtrip_uses_actual_google_and_exact_off_control(self):
        provider = self.build()
        self.assert_no_outbound()
        self.assertEqual(provider.capabilities().supported, frozenset({Capability.TEXT}))
        self.assertEqual(provider.profile.document["identity"]["operator"], "Google")
        self.assertEqual(provider.profile.document["identity"]["model_publisher"], "Google")
        response = provider.generate(self.request())
        self.assertEqual((response.provider, response.model), ("google", "gemma-4-26b-a4b-it"))
        self.assertEqual(response.output[0].text, "synthetic ok")
        self.assertEqual(response.finish_reason, FinishReason.COMPLETE)
        # Missing thoughtsTokenCount is unavailable, even under an off request.
        self.assertEqual((response.usage.input_tokens, response.usage.output_tokens, response.usage.total_tokens), (5, None, None))
        self.assertEqual(self.credential.resolutions, 1)
        self.assertEqual(self.credential.presence_checks, 0)
        self.assertEqual(len(self.transport.requests), 1)
        sent = self.transport.requests[0]
        self.assertEqual(sent.url, "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent")
        self.assertEqual(json.loads(sent.body), {
            "contents": [{"role": "user", "parts": [{"text": "synthetic input"}]}],
            "generationConfig": {"thinkingConfig": {"thinkingLevel": "minimal"}, "maxOutputTokens": 32},
        })
        self.assertIn("x-goog-api-key", sent.headers)

    def test_tool_and_schema_are_gaps_before_credential(self):
        provider = self.build()
        schema = {"type": "object", "properties": {"answer": {"type": "string"}},
                  "required": ["answer"], "additionalProperties": False}
        requests = (
            replace(self.request(), tools=(ToolDefinition("synthetic_tool", "offline", schema, strict=False),)),
            replace(self.request(), response_format=ResponseFormat("json_schema", "answer", schema)),
            replace(self.request(), capability_requirements=frozenset({Capability.TOOLS})),
            replace(self.request(), capability_requirements=frozenset({Capability.STRUCTURED_OUTPUT})),
        )
        for request in requests:
            with self.subTest(request=request):
                with self.assertRaises(CapabilityGap) as caught:
                    provider.generate(request)
                self.assertTrue(set(caught.exception.gaps) & {Capability.TOOLS, Capability.STRUCTURED_OUTPUT})
                self.assert_no_outbound()

    def test_requested_model_drift_is_rejected_before_credential(self):
        provider = self.build()
        with self.assertRaises(ModelNotSupported):
            provider.generate(replace(self.request(), model="gemma-4-31b-it"))
        self.assert_no_outbound()

    def test_profile_file_model_drift_is_rejected_before_credential(self):
        provider = self.build()
        altered = copy.deepcopy(self.document)
        altered["model"]["requested_id"] = "gemma-4-31b-it"
        self.profile_path.write_bytes(json.dumps(altered).encode())
        with self.assertRaises(ProviderError) as caught:
            provider.generate(self.request())
        self.assertEqual(caught.exception.category, ProviderErrorCategory.INVALID_REQUEST)
        self.assert_no_outbound()

    def test_gemma_profile_cannot_apply_off_policy_to_other_models(self):
        for model in ("gemma-4-31b-it", "gemini-3.5-flash-lite", "gemini-2.5-flash-lite"):
            document = copy.deepcopy(self.document)
            document["model"]["requested_id"] = model
            with self.subTest(model=model), self.assertRaises(ProviderError):
                wire_codecs.encode_profile_request(replace(self.request(), model=model), document)

    def test_gemma_model_requires_its_declared_profile_and_text_ceiling(self):
        for change in ("profile", "capabilities", "provider", "mode"):
            document = copy.deepcopy(self.document)
            if change == "profile":
                document["profile_id"] = "different-profile"
            elif change == "capabilities":
                document["implementation"]["capabilities"] = ["text", "tools"]
            elif change == "provider":
                document["identity"]["provider"] = "openrouter"
            else:
                document["generation"]["mode"] = "nonthinking"
            with self.subTest(change=change), self.assertRaises(ProviderError):
                wire_codecs.encode_profile_request(self.request(), document)

    def test_native_control_registry_drift_is_rejected_before_credential(self):
        provider = self.build()
        changed = MappingProxyType({
            ("google", "gemini-generate-content", "gemma-4-26b-a4b-it", "standard"):
                MappingProxyType({"thinkingConfig": MappingProxyType({"thinkingLevel": "high"})}),
        })
        with patch.object(wire_codecs, "GEMMA_TEXT_PARAMETERS", changed), self.assertRaises(ValueError):
            provider.generate(self.request())
        self.assert_no_outbound()

    def test_other_gemini_payload_policy_is_unchanged(self):
        retired = json.loads((ROOT / "registry/providers/profiles/google-gemini-generate-content-v1.json").read_bytes())
        for model in ("gemini-2.0-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite"):
            document = copy.deepcopy(retired)
            document["model"]["requested_id"] = model
            payload = wire_codecs.encode_profile_request(replace(self.request(), model=model), document)
            self.assertEqual(payload["generationConfig"], {"maxOutputTokens": 32})

    def test_returned_thought_and_signature_remain_unsupported(self):
        for part in ({"text": "synthetic", "thought": True},
                     {"text": "synthetic", "thoughtSignature": "synthetic-signature"}):
            document = json.loads((FIXTURE / "positive.response.json").read_bytes())
            document["candidates"][0]["content"]["parts"] = [part]
            with self.subTest(part=part), self.assertRaises(ProviderError) as caught:
                wire_codecs.decode_profile_response(self.request(), document, self.document)
            self.assertEqual(caught.exception.category, ProviderErrorCategory.UNSUPPORTED)

    def test_observed_model_drift_is_not_relabelled(self):
        provider = self.build()
        self.transport.document["modelVersion"] = "gemma-4-31b-it"
        with self.assertRaises(ProviderError) as caught:
            provider.generate(self.request())
        self.assertEqual(caught.exception.category, ProviderErrorCategory.CONTRACT_VIOLATION)
        self.assertEqual(self.credential.resolutions, 1)

    def test_disabled_template_cannot_run_or_probe_credentials(self):
        self.config_path.write_bytes((FIXTURE / "disabled.config.json").read_bytes())
        self.config = load_profile_configurations(self.config_path)[0]
        with self.assertRaises(ProviderError):
            self.build()
        self.assert_no_outbound()

    def test_manifest_stages_and_independently_replays_exact_profile_and_control_source(self):
        provider = self.build()
        reference = stage_provider_binding(provider, root=self.root, destination="binding")
        replay = read_provider_binding_manifest(EvaluationInputs(self.root, ROOT / "schemas"), reference)
        self.assertEqual(replay.document["provider_identity"]["provider"], "google")
        self.assert_no_outbound()


if __name__ == "__main__":
    unittest.main()
