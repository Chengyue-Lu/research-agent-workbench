"""Offline configuration-to-HTTP composition and fail-before-Key checks."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from research_workbench.adapters.models.configured import build_profile_provider
from research_workbench.adapters.models.http import HttpResponse
from research_workbench.adapters.models.port import (
    Capability,
    ContentBlock,
    DataPolicy,
    Message,
    ModelRequest,
    ProviderError,
    ResponseFormat,
    ToolChoice,
    ToolDefinition,
)
from research_workbench.adapters.models.profile_configuration import ProviderAdapterConfigV2


ROOT = Path(__file__).resolve().parents[1]


class SyntheticCredential:
    def __init__(self, name: str) -> None:
        self.name = name
        self.resolutions = 0
        self.presence_checks = 0

    @property
    def label(self) -> str:
        return f"env:{self.name}"

    def available(self) -> bool:
        self.presence_checks += 1
        raise AssertionError("construction must not probe credential presence")

    def resolve(self) -> str:
        self.resolutions += 1
        return "synthetic-offline-key"


class SyntheticTransport:
    def __init__(self, document: dict[str, object], status: int = 200) -> None:
        self.max_response_bytes = 8388608
        self.document = document
        self.status = status
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return HttpResponse(self.status, {}, json.dumps(self.document).encode())


def _response(profile: dict[str, object]) -> dict[str, object]:
    model = profile["model"]["requested_id"]
    family = profile["protocol"]["family"]
    if family == "responses":
        return {"id": "synthetic-response", "model": model, "status": "completed",
                "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "ok"}]}],
                "usage": {"input_tokens": 1, "output_tokens": 1}}
    if family == "chat-completions":
        return {"id": "synthetic-response", "model": model,
                "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
    if family == "anthropic-messages":
        return {"id": "synthetic-response", "model": model, "type": "message", "role": "assistant", "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1}}
    return {"modelVersion": model, "responseId": "synthetic-response",
            "candidates": [{"finishReason": "STOP", "content": {"role": "model", "parts": [{"text": "ok"}]}}],
            "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1}}


class ConfiguredProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def build(self, vendor: str = "deepseek", *, enabled: bool = True, credential_name: str = "SYNTHETIC_API_KEY"):
        # These consumers exercise the retained retired/blocked profiles;
        # the independent minimal text profiles have their own tests.
        retained = {"google": "google-gemini-generate-content-v1.json",
                    "siliconflow": "siliconflow-chat-completions-v1.json",
                    "openrouter": "openrouter-chat-completions-v1.json"}
        paths = ([ROOT / "registry/providers/profiles" / retained[vendor]]
                 if vendor in retained else
                 sorted((ROOT / "registry/providers/profiles").glob(f"{vendor}-*.json")))
        self.assertEqual(len(paths), 1)
        document = json.loads(paths[0].read_text(encoding="utf-8"))
        path = self.root / "profile.json"
        raw = json.dumps(document, ensure_ascii=False).encode()
        path.write_bytes(raw)
        self.profile_path = path
        config = ProviderAdapterConfigV2.from_mapping({
            "adapter_id": "synthetic-profile", "enabled": enabled,
            "profile_ref": {"path": "profile.json", "sha256": hashlib.sha256(raw).hexdigest()},
            "model_selector": {"kind": "literal", "value": document["model"]["requested_id"]},
            "credential_source": {"kind": "environment", "name": "SYNTHETIC_API_KEY"},
            "capabilities": list(document["implementation"]["capabilities"]),
            "transport": {"timeout_seconds": 10, "max_response_bytes": 8388608, "redirect_policy": "deny", "retry_policy": "none"},
            "conformance_ref": None,
        })
        self.credential = SyntheticCredential(credential_name)
        self.transport = SyntheticTransport(_response(document))
        return build_profile_provider(config, root=self.root, credential=self.credential, transport=self.transport)

    def request(self, provider):
        return ModelRequest(provider.model, (Message("user", (ContentBlock("text", "synthetic"),)),), max_output_tokens=32)

    def assert_no_outbound(self) -> None:
        self.assertEqual(self.credential.resolutions, 0)
        self.assertEqual(self.credential.presence_checks, 0)
        self.assertEqual(self.transport.requests, [])

    def test_construction_is_late_credential_and_deeply_immutable(self) -> None:
        provider = self.build()
        self.assert_no_outbound()
        self.assertEqual(provider.capabilities().provider, "deepseek")
        with self.assertRaises(TypeError):
            provider.resolved_config["transport"]["timeout_seconds"] = 1
        descriptor = provider.binding_descriptor()
        descriptor["profile"]["endpoint"]["origin"] = "https://changed.invalid"
        self.assertEqual(provider.profile.document["endpoint"]["origin"], "https://api.deepseek.com")
        self.assertNotIn("synthetic-offline-key", repr(provider))

    def test_actual_registry_profiles_roundtrip_with_real_vendor_identity(self) -> None:
        for vendor in ("openai", "anthropic", "deepseek", "alibaba-dashscope", "zhipu", "moonshot", "minimax", "bytedance-ark"):
            with self.subTest(vendor=vendor):
                provider = self.build(vendor)
                response = provider.generate(self.request(provider))
                self.assertEqual(response.provider, vendor)
                self.assertEqual(response.model, provider.model)
                self.assertEqual(response.output[0].text, "ok")
                self.assertEqual(self.credential.resolutions, 1)
                self.assertEqual(self.credential.presence_checks, 0)
                self.assertEqual(len(self.transport.requests), 1)
                if vendor == "deepseek":
                    payload = json.loads(self.transport.requests[0].body)
                    self.assertEqual(payload["reasoning"], {"effort": "none"})
                    self.assertEqual(self.transport.requests[0].url, "https://api.deepseek.com/responses")

    def test_known_unclosed_vendor_profiles_cannot_become_runnable(self) -> None:
        for vendor in ("openrouter", "siliconflow", "google"):
            with self.subTest(vendor=vendor), self.assertRaises((ValueError, ProviderError)):
                self.build(vendor)
            self.assert_no_outbound()

    def test_disabled_configuration_rejected_without_key(self) -> None:
        with self.assertRaises(ProviderError):
            self.build(enabled=False)
        self.assert_no_outbound()

    def test_different_credential_reference_rejected_without_value(self) -> None:
        with self.assertRaises(ProviderError) as caught:
            self.build(credential_name="UNEXPECTED_REFERENCE")
        self.assertNotIn("UNEXPECTED_REFERENCE", str(caught.exception))
        self.assert_no_outbound()

    def test_profile_file_drift_rejected_before_credential(self) -> None:
        provider = self.build()
        document = json.loads(self.profile_path.read_bytes())
        document["endpoint"]["origin"] = "https://different.invalid"
        self.profile_path.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaises((ValueError, ProviderError)):
            provider.generate(self.request(provider))
        self.assert_no_outbound()

    def test_transport_options_drift_rejected_before_credential(self) -> None:
        provider = self.build()
        self.transport.max_response_bytes = 1
        with self.assertRaises(ValueError):
            provider.generate(self.request(provider))
        self.assert_no_outbound()

    def test_callable_swap_rejected_before_credential(self) -> None:
        provider = self.build()
        import research_workbench.adapters.models.wire_codecs as codecs
        with patch.object(codecs, "encode_profile_request", lambda *_: {}), self.assertRaises(ValueError):
            provider.generate(self.request(provider))
        self.assert_no_outbound()

    def test_request_admission_before_credential(self) -> None:
        provider = self.build()
        request = self.request(provider)
        bad_requests = (
            replace(request, model="another-model"),
            replace(request, max_output_tokens=None),
            replace(request, max_output_tokens=257),
            replace(request, data_policy=DataPolicy(local_only=True)),
            replace(request, data_policy=DataPolicy(training_opt_out_required=True)),
            replace(request, capability_requirements=frozenset({Capability.STREAMING})),
            replace(request, messages=(Message("developer", (ContentBlock("text", "synthetic"),)),)),
            replace(request, extensions={"deepseek": {"raw": {}}}),
            replace(request, reasoning_effort="high"),
            replace(request, response_format=ResponseFormat("json_schema", "probe", {"type": "object", "const": {}})),
            replace(request, tools=(ToolDefinition("probe", "synthetic", {"type": "object", "properties": {}, "required": [], "additionalProperties": False}),)),
        )
        for bad in bad_requests:
            with self.subTest(request=bad), self.assertRaises((ValueError, ProviderError)):
                provider.generate(bad)
            self.assert_no_outbound()

    def test_observed_model_drift_does_not_rebind_or_retry(self) -> None:
        provider = self.build()
        self.transport.document["model"] = "another-model"
        with self.assertRaises(ProviderError):
            provider.generate(self.request(provider))
        self.assertEqual(self.credential.resolutions, 1)
        self.assertEqual(len(self.transport.requests), 1)

    def test_deepseek_schema_uses_native_shape_and_local_validation(self) -> None:
        provider = self.build()
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}},
                  "required": ["ok"], "additionalProperties": False}
        request = replace(self.request(provider), response_format=ResponseFormat("json_schema", "probe", schema))
        self.transport.document["output"][0]["content"][0]["text"] = '{"ok":true}'
        response = provider.generate(request)
        self.assertEqual(json.loads(response.output[0].text), {"ok": True})
        payload = json.loads(self.transport.requests[0].body)
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        # The frozen DeepSeek reference defines name/schema and no strict
        # member. Native schema shape plus local validation is the claim.
        self.assertNotIn("strict", payload["text"]["format"])
        self.assertEqual(self.credential.resolutions, 1)

    def test_deepseek_specific_local_tool_without_claiming_remote_strict(self) -> None:
        provider = self.build()
        schema = {"type": "object", "properties": {"value": {"type": "string"}},
                  "required": ["value"], "additionalProperties": False}
        tool = ToolDefinition("probe", "synthetic pure probe", schema, strict=False)
        request = replace(self.request(provider), tools=(tool,), tool_choice=ToolChoice("specific", "probe"))
        self.transport.document["output"] = [{"type": "function_call", "id": "synthetic-item", "call_id": "synthetic-call",
                                                "name": "probe", "arguments": '{"value":"probe"}'}]
        response = provider.generate(request)
        self.assertEqual(dict(response.tool_calls[0].arguments), {"value": "probe"})
        payload = json.loads(self.transport.requests[0].body)
        self.assertEqual(payload["tool_choice"], {"type": "function", "name": "probe"})
        self.assertNotIn("strict", payload["tools"][0])
        self.assertEqual(len(self.transport.requests), 1)

    def test_malformed_tool_json_does_not_attach_response_or_auth_content(self) -> None:
        provider = self.build()
        tool = ToolDefinition("probe", "synthetic pure probe", {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, strict=False)
        request = replace(self.request(provider), tools=(tool,), tool_choice=ToolChoice("specific", "probe"))
        self.transport.document["output"] = [{"type": "function_call", "id": "synthetic-item", "call_id": "synthetic-call",
                                                "name": "probe", "arguments": "synthetic-offline-key"}]
        with self.assertRaises(ProviderError) as caught:
            provider.generate(request)
        self.assertNotIn("synthetic-offline-key", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)
        self.assertEqual(len(self.transport.requests), 1)

    def test_invalid_request_schema_error_does_not_attach_raw_schema(self) -> None:
        provider = self.build()
        schema = {"type": "synthetic-private-schema-marker"}
        request = replace(self.request(provider), response_format=ResponseFormat("json_schema", "probe", schema))
        with self.assertRaises(ProviderError) as caught:
            provider.generate(request)
        self.assertNotIn("synthetic-private-schema-marker", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)
        self.assert_no_outbound()

    def test_provider_http_error_is_safe_and_has_no_retry(self) -> None:
        provider = self.build()
        self.transport.status = 429
        self.transport.document = {"error": {"message": "synthetic-offline-key", "code": "synthetic-offline-key"}}
        with self.assertRaises(ProviderError) as caught:
            provider.generate(self.request(provider))
        self.assertNotIn("synthetic-offline-key", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)
        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(len(self.transport.requests), 1)


if __name__ == "__main__":
    unittest.main()
