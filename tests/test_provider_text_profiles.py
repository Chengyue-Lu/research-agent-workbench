"""Exact SiliconFlow/OpenRouter Text fixtures; zero real credentials or services."""

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
    Capability, CapabilityGap, ContentBlock, DataPolicy, DataPolicyGap, FinishReason,
    Message, ModelNotSupported, ModelRequest, ProviderError, ProviderErrorCategory,
    ResponseFormat, ToolDefinition,
)
from research_workbench.adapters.models.profile_configuration import (
    ProfileConfigurationError, ProviderAdapterConfigV2, ProviderApiProfile,
    load_profile_configurations, resolve_profile_configuration,
)
from research_workbench.evaluation.pins import EvaluationValidationError


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/provider_text_profiles_v1"
VENDORS = ("siliconflow", "openrouter")
SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}},
          "required": ["answer"], "additionalProperties": False}


class SyntheticCredential:
    def __init__(self, vendor):
        self.label = "env:RWB_" + vendor.upper() + "_SYNTHETIC_KEY"
        self.resolutions = 0
        self.presence_checks = 0

    def available(self):
        self.presence_checks += 1
        raise AssertionError("offline fixture must not inspect credential presence")

    def resolve(self):
        self.resolutions += 1
        return "synthetic-text-offline-token"


class SyntheticTransport:
    def __init__(self, document):
        self.max_response_bytes = 65536
        self.document = document
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return HttpResponse(200, {}, json.dumps(self.document).encode())


class ProviderTextProfileTests(unittest.TestCase):
    def prepare(self, vendor, *, enabled=True):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.vendor = vendor
        self.relative = Path(f"registry/providers/profiles/{vendor}-chat-completions-text-v1.json")
        self.raw_profile = (ROOT / self.relative).read_bytes()
        self.document = json.loads(self.raw_profile)
        self.profile_path = self.root / self.relative
        self.profile_path.parent.mkdir(parents=True)
        self.profile_path.write_bytes(self.raw_profile)
        config_name = "positive.config.json" if enabled else "disabled.config.json"
        config_path = self.root / "config.json"
        config_path.write_bytes((FIXTURES / vendor / config_name).read_bytes())
        self.config = load_profile_configurations(config_path)[0]
        self.credential = SyntheticCredential(vendor)
        self.response = json.loads((FIXTURES / vendor / "positive.response.json").read_bytes())
        self.transport = SyntheticTransport(self.response)
        self.request = ModelRequest(self.document["model"]["requested_id"],
                                    (Message("user", (ContentBlock("text", "synthetic input"),)),),
                                    max_output_tokens=32)

    def build(self):
        return build_profile_provider(self.config, root=self.root,
                                      credential=self.credential, transport=self.transport)

    def assert_no_outbound(self):
        self.assertEqual(self.credential.resolutions, 0)
        self.assertEqual(self.credential.presence_checks, 0)
        self.assertEqual(self.transport.requests, [])

    def stage_changed_profile(self, document):
        raw = (json.dumps(document, indent=2) + "\n").encode()
        self.profile_path.write_bytes(raw)
        config = self.config.to_mapping()
        config["profile_ref"]["sha256"] = hashlib.sha256(raw).hexdigest()
        config["model_selector"]["value"] = document["model"]["requested_id"]
        self.config = ProviderAdapterConfigV2.from_mapping(config)

    def test_profiles_and_independent_configs_are_closed_schema_valid_and_lf_pinned(self):
        profile_schema = json.loads((ROOT / "schemas/v0.1.0/provider-api-profile.schema.json").read_bytes())
        config_schema = json.loads((ROOT / "schemas/v0.1.0/provider-adapters-v2.schema.json").read_bytes())
        for vendor in VENDORS:
            with self.subTest(vendor=vendor):
                self.prepare(vendor)
                self.assertNotIn(b"\r", self.raw_profile)
                Draft202012Validator(profile_schema).validate(self.document)
                ProviderApiProfile.from_mapping(self.document)
                self.assertEqual(self.document["generation"]["mode"], "standard")
                self.assertEqual(self.document["implementation"]["capabilities"], ["text"])
                self.assertFalse(any(gap.startswith("blocking:") for gap in self.document["implementation"]["known_gaps"]))
                for name, enabled in (("positive.config.json", True), ("disabled.config.json", False)):
                    raw = (FIXTURES / vendor / name).read_bytes()
                    self.assertNotIn(b"\r", raw)
                    config = json.loads(raw)
                    Draft202012Validator(config_schema).validate(config)
                    self.assertIs(config["adapters"][0]["enabled"], enabled)
                    self.assertEqual(config["adapters"][0]["profile_ref"], {
                        "path": self.relative.as_posix(), "sha256": hashlib.sha256(self.raw_profile).hexdigest()})

    def test_complete_config_factory_text_roundtrip_uses_actual_vendor_and_fixed_policy(self):
        for vendor in VENDORS:
            with self.subTest(vendor=vendor):
                self.prepare(vendor)
                provider = self.build()
                self.assert_no_outbound()
                self.assertEqual(provider.capabilities().supported, frozenset({Capability.TEXT}))
                self.assertEqual(provider.capabilities().regions, frozenset())
                self.assertEqual(provider.capabilities().data_controls, frozenset())
                response = provider.generate(self.request)
                self.assertEqual((response.provider, response.model), (vendor, self.request.model))
                self.assertEqual(response.output[0].text, "synthetic ok")
                self.assertEqual(response.finish_reason, FinishReason.COMPLETE)
                self.assertEqual((response.usage.input_tokens, response.usage.output_tokens, response.usage.total_tokens), (5, 2, 7))
                self.assertIsNone(response.usage.provider_reported_cost)
                sent = self.transport.requests[0]
                expected = {"model": self.request.model, "messages": [{"role": "user", "content": "synthetic input"}], "stream": False}
                if vendor == "openrouter":
                    expected.update(max_completion_tokens=32, provider={"only": ["openai"], "allow_fallbacks": False, "require_parameters": True})
                    self.assertEqual(sent.url, "https://openrouter.ai/api/v1/chat/completions")
                    self.assertEqual(response.provider_metadata["gateway"], {"operator": "OpenRouter", "requested_upstream": "openai", "reported_upstream": "openai", "physical_endpoint": None, "deployment_region": None})
                else:
                    expected["max_tokens"] = 32
                    self.assertEqual(sent.url, "https://api.siliconflow.cn/v1/chat/completions")
                    self.assertNotIn("gateway", response.provider_metadata)
                self.assertEqual(json.loads(sent.body), expected)
                self.assertEqual(self.credential.resolutions, 1)
                self.assertEqual(self.credential.presence_checks, 0)
                self.assertEqual(len(self.transport.requests), 1)

    def test_disabled_configs_cannot_construct_or_probe_credentials(self):
        for vendor in VENDORS:
            with self.subTest(vendor=vendor):
                self.prepare(vendor, enabled=False)
                with self.assertRaises(ProviderError):
                    self.build()
                self.assert_no_outbound()

    def test_tools_schema_and_hard_data_policy_are_gaps_before_credential(self):
        for vendor in VENDORS:
            self.prepare(vendor)
            provider = self.build()
            for req in (replace(self.request, tools=(ToolDefinition("synthetic_tool", "offline", SCHEMA, strict=False),)),
                        replace(self.request, response_format=ResponseFormat("json_schema", "answer", SCHEMA)),
                        replace(self.request, capability_requirements=frozenset({Capability.TOOLS})),
                        replace(self.request, capability_requirements=frozenset({Capability.STRUCTURED_OUTPUT}))):
                with self.subTest(vendor=vendor, request=req), self.assertRaises(CapabilityGap):
                    provider.generate(req)
                self.assert_no_outbound()
            for policy in (DataPolicy(allowed_regions=("CN",)), DataPolicy(training_opt_out_required=True),
                           DataPolicy(zero_data_retention_required=True), DataPolicy(local_only=True)):
                with self.subTest(vendor=vendor, policy=policy), self.assertRaises(DataPolicyGap):
                    provider.generate(replace(self.request, data_policy=policy))
                self.assert_no_outbound()

    def test_requested_model_and_extensions_cannot_replace_exact_binding_or_policy(self):
        for vendor in VENDORS:
            self.prepare(vendor)
            provider = self.build()
            with self.subTest(vendor=vendor), self.assertRaises(ModelNotSupported):
                provider.generate(replace(self.request, model="different-model"))
            self.assert_no_outbound()
            for changes in ({"extensions": {vendor: {"provider": {"only": ["azure"], "allow_fallbacks": True}}}},
                            {"extensions": {vendor: {"enable_thinking": True}}},
                            {"reasoning_effort": "high"}, {"metadata": {"route": "override"}}):
                with self.subTest(vendor=vendor, changes=changes), self.assertRaises((ProviderError, CapabilityGap)):
                    provider.generate(replace(self.request, **changes))
                self.assert_no_outbound()

    def test_profile_model_provider_mode_and_text_ceiling_cannot_drift(self):
        for vendor in VENDORS:
            for field in ("profile", "provider", "model", "mode", "capabilities"):
                self.prepare(vendor)
                document = copy.deepcopy(self.document)
                if field == "profile":
                    document["profile_id"] = "different-profile"
                elif field == "provider":
                    document["identity"]["provider"] = "openai"
                elif field == "model":
                    document["model"].update(requested_id="different-model", allowed_observed_ids=["different-model"])
                elif field == "mode":
                    document["generation"]["mode"] = "nonthinking"
                else:
                    document["implementation"]["capabilities"] = ["text", "tools"]
                with self.subTest(vendor=vendor, field=field), self.assertRaises((ProviderError, ProfileConfigurationError)):
                    self.stage_changed_profile(document)
                    self.build().generate(replace(self.request, model=document["model"]["requested_id"]))
                self.assert_no_outbound()

    def test_original_blocked_profiles_remain_non_executable(self):
        for vendor in VENDORS:
            self.prepare(vendor)
            relative = Path(f"registry/providers/profiles/{vendor}-chat-completions-v1.json")
            raw = (ROOT / relative).read_bytes()
            document = json.loads(raw)
            self.assertTrue(any(gap.startswith("blocking:") for gap in document["implementation"]["known_gaps"]))
            target = self.root / relative
            target.write_bytes(raw)
            config = self.config.to_mapping()
            config["profile_ref"] = {"path": relative.as_posix(), "sha256": hashlib.sha256(raw).hexdigest()}
            config["model_selector"]["value"] = document["model"]["requested_id"]
            self.config = ProviderAdapterConfigV2.from_mapping(config)
            with self.subTest(vendor=vendor), self.assertRaises(ProfileConfigurationError):
                resolve_profile_configuration(self.config, root=self.root)
            with self.assertRaises(ProfileConfigurationError):
                self.build()
            self.assert_no_outbound()

    def test_reasoning_tool_server_and_wrong_model_responses_are_rejected(self):
        for vendor in VENDORS:
            for field in ("reasoning_content", "reasoning", "reasoning_details", "tool_calls", "server_content", "model"):
                self.prepare(vendor)
                provider = self.build()
                message = self.response["choices"][0]["message"]
                if field == "model":
                    self.response["model"] = "different-model"
                elif field == "tool_calls":
                    message[field] = [{"id": "synthetic-call", "type": "function", "function": {"name": "synthetic_tool", "arguments": "{}"}}]
                    self.response["choices"][0]["finish_reason"] = "tool_calls"
                elif field == "server_content":
                    message["content"] = [{"type": "server_tool", "text": "synthetic"}]
                else:
                    message[field] = "synthetic hidden continuation"
                with self.subTest(vendor=vendor, field=field), self.assertRaises(ProviderError):
                    provider.generate(self.request)
                self.assertEqual(self.credential.resolutions, 1)
                self.assertEqual(self.credential.presence_checks, 0)
                self.assertEqual(len(self.transport.requests), 1)

    def test_length_preserves_partial_text_and_existing_usage(self):
        for vendor in VENDORS:
            with self.subTest(vendor=vendor):
                self.prepare(vendor)
                self.response["choices"][0]["finish_reason"] = "length"
                response = self.build().generate(self.request)
                self.assertEqual(response.finish_reason, FinishReason.LENGTH)
                self.assertEqual(response.output[0].text, "synthetic ok")
                self.assertEqual(response.usage.total_tokens, 7)

    def test_openrouter_reported_upstream_is_bounded_observation_and_missing_is_unknown(self):
        for reported in (None, "openai", "OpenAI"):
            self.prepare("openrouter")
            if reported is None:
                del self.response["provider"]
            else:
                self.response["provider"] = reported
            with self.subTest(reported=reported):
                response = self.build().generate(self.request)
                self.assertEqual(response.provider, "openrouter")
                gateway = response.provider_metadata["gateway"]
                self.assertEqual(gateway["reported_upstream"], None if reported is None else "openai")
                self.assertIsNone(gateway["physical_endpoint"])
                self.assertIsNone(gateway["deployment_region"])
        for reported in ("Azure", "unknown-provider", {"name": "OpenAI"}):
            self.prepare("openrouter")
            self.response["provider"] = reported
            with self.subTest(reported=reported), self.assertRaises(ProviderError) as caught:
                self.build().generate(self.request)
            self.assertEqual(caught.exception.category, ProviderErrorCategory.CONTRACT_VIOLATION)

    def test_fixed_parameter_registry_runtime_drift_is_rejected_before_credential(self):
        self.prepare("openrouter")
        provider = self.build()
        changed = MappingProxyType({("openrouter", "chat-completions", "openai/gpt-4.1-mini", "standard"):
                                    MappingProxyType({"provider": {"only": ["azure"], "allow_fallbacks": True}})})
        with patch.object(wire_codecs, "STANDARD_TEXT_PARAMETERS", changed), self.assertRaises(EvaluationValidationError):
            provider.generate(self.request)
        self.assert_no_outbound()

    def test_fixed_parameter_registry_cannot_be_patched_before_construction(self):
        self.prepare("openrouter")
        changed = MappingProxyType({("openrouter", "chat-completions", "openai/gpt-4.1-mini", "standard"):
                                    MappingProxyType({"provider": {"only": ["azure"], "allow_fallbacks": True}})})
        with patch.object(wire_codecs, "STANDARD_TEXT_PARAMETERS", changed), self.assertRaises(EvaluationValidationError):
            self.build()
        self.assert_no_outbound()

    def test_profile_bytes_cannot_change_after_factory_freeze(self):
        for vendor in VENDORS:
            self.prepare(vendor)
            provider = self.build()
            self.profile_path.write_bytes(self.raw_profile + b"\n")
            with self.subTest(vendor=vendor), self.assertRaises(ProviderError) as caught:
                provider.generate(self.request)
            self.assertEqual(caught.exception.category, ProviderErrorCategory.INVALID_REQUEST)
            self.assert_no_outbound()


if __name__ == "__main__":
    unittest.main()
