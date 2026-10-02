"""Synthetic offline wire contracts; no vendor/remote conformance claim."""

from __future__ import annotations

import copy
import json
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

from research_workbench.adapters.models.port import (
    Capability, CapabilityGap, ContentBlock, DataPolicy, DataPolicyGap, FinishReason, Message, ModelNotSupported,
    ModelRequest, ProviderError, ResponseFormat, ToolChoice, ToolDefinition,
)
from research_workbench.adapters.models.wire_codecs import (
    CODEC_VERSION, NATIVE_MODEL_REGISTRY, NATIVE_PARAMETER_REGISTRY,
    decode_profile_response, encode_profile_request,
)
from research_workbench.adapters.models.profile_configuration import ProviderApiProfile


FAMILIES = {
    "responses": ("openai", "text_responses.json"),
    "chat-completions": ("openai", "text_chat.json"),
    "anthropic-messages": ("anthropic", "text_messages.json"),
    "gemini-generate-content": ("google", "text_gemini.json"),
}
SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}},
          "required": ["ok"], "additionalProperties": False}
TOOL_SCHEMA = {"type": "object", "properties": {"value": {"type": "string", "enum": ["probe"]}},
               "required": ["value"], "additionalProperties": False}
TOOL = ToolDefinition("echo", "Return the synthetic value.", TOOL_SCHEMA, strict=False)


def profile(family: str, provider: str | None = None, *, beta: bool = False) -> dict:
    provider = provider or FAMILIES[family][0]
    nonthinking = provider == "deepseek"
    return {
        "schema_version": "0.1.0", "record_kind": "provider_api_profile", "version": "1.0.0",
        "profile_id": "synthetic-offline", "identity": {"provider": provider},
        "protocol": {"family": family, "revision": "1.0.0"},
        "endpoint": {"origin": "https://synthetic.example.test", "base_path": "/beta" if beta else "",
                     "operation_path": "/fixture", "api_version": None},
        "auth": {"kind": "api-key-header"},
        "model": {"requested_id": "deepseek-flash" if nonthinking else "synthetic-model"},
        "generation": {"mode": "nonthinking" if nonthinking else "standard",
                       "parameter_profile_id": f"{family}:parameters:v1",
                       "continuation_policy": "local-messages-only"},
        "mapping": {f"{kind}_policy_id": f"{family}:{kind}:v1" for kind in ("role", "tool", "schema", "usage", "finish", "error")},
        "implementation": {"adapter_version": "1.0.0", "codec_version": CODEC_VERSION,
                           "capabilities": ["text", "tools", "structured_output", "parallel_tools"]},
    }


def request(**changes) -> ModelRequest:
    value = ModelRequest("synthetic-model", (Message("system", (ContentBlock("text", text="Synthetic only."),)),
                         Message("user", (ContentBlock("text", text="Return OK."),))), max_output_tokens=64)
    return replace(value, **changes)


def fixture(family: str) -> dict:
    return json.loads((Path(__file__).with_name("fixtures") / "profile_wire_codecs" / FAMILIES[family][1]).read_text(encoding="utf-8"))


def tool_response(family: str) -> dict:
    value = fixture(family)
    if family == "responses":
        value["output"] = [{"type": "function_call", "status": "completed", "call_id": "call-1",
                            "name": "echo", "arguments": '{"value":"probe"}'}]
    elif family == "chat-completions":
        value["choices"][0].update(finish_reason="tool_calls", message={"role": "assistant", "content": None,
            "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "echo", "arguments": '{"value":"probe"}'}}]})
    elif family == "anthropic-messages":
        value.update(stop_reason="tool_use", content=[{"type": "tool_use", "id": "call-1", "name": "echo", "input": {"value": "probe"}}])
    else:
        value["candidates"][0]["content"]["parts"] = [{"functionCall": {"id": "call-1", "name": "echo", "args": {"value": "probe"}}}]
    return value


def freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze(item) for item in value)
    return value


class ProfileWireCodecTests(unittest.TestCase):
    def test_four_text_request_shapes_and_actual_provider_identity(self):
        for family, (provider, _) in FAMILIES.items():
            with self.subTest(family=family):
                selected, req = profile(family), request()
                payload = encode_profile_request(req, selected)
                if family == "responses":
                    self.assertEqual(payload["input"][0], {"role": "system", "content": "Synthetic only."})
                    self.assertIs(payload["store"], False)
                    self.assertEqual(payload["max_output_tokens"], 64)
                elif family == "chat-completions":
                    self.assertEqual(payload["messages"][1], {"role": "user", "content": "Return OK."})
                    self.assertEqual(payload["max_completion_tokens"], 64)
                elif family == "anthropic-messages":
                    self.assertEqual(payload["system"], [{"type": "text", "text": "Synthetic only."}])
                    self.assertEqual(payload["max_tokens"], 64)
                else:
                    self.assertEqual(payload["systemInstruction"], {"parts": [{"text": "Synthetic only."}]})
                    self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 64)
                actual = decode_profile_response(req, fixture(family), selected)
                self.assertEqual((actual.provider, actual.model, actual.finish_reason), (provider, "synthetic-model", FinishReason.COMPLETE))
                self.assertEqual(actual.output[0].text, "OK")

    def test_compatible_operator_identity_never_becomes_openai(self):
        for provider in ("alibaba-dashscope", "zhipu", "moonshot", "minimax", "siliconflow", "bytedance-ark"):
            with self.subTest(provider=provider):
                selected = profile("chat-completions", provider)
                self.assertEqual(encode_profile_request(request(), selected)["model"], "synthetic-model")
                self.assertEqual(decode_profile_response(request(), fixture("chat-completions"), selected).provider, provider)

    def test_deepseek_native_nonthinking_controls_and_supported_fields(self):
        for family in ("responses", "chat-completions"):
            with self.subTest(family=family):
                selected = profile(family, "deepseek")
                req = request(model="deepseek-flash")
                payload = encode_profile_request(req, selected)
                self.assertEqual(payload["reasoning" if family == "responses" else "thinking"],
                                 {"effort": "none"} if family == "responses" else {"type": "disabled"})
                self.assertNotIn("metadata", payload)
                if family == "responses":
                    self.assertNotIn("store", payload)
                else:
                    self.assertEqual(payload["max_tokens"], 64)
                self.assertEqual(decode_profile_response(req, fixture(family), selected).provider, "deepseek")

    def test_specific_tool_and_result_roundtrip_each_protocol(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                selected = profile(family)
                first = request(tools=(TOOL,), tool_choice=ToolChoice("specific", "echo"))
                payload = encode_profile_request(first, selected)
                if family == "responses":
                    self.assertEqual(payload["tool_choice"], {"type": "function", "name": "echo"})
                elif family == "chat-completions":
                    self.assertEqual(payload["tool_choice"], {"type": "function", "function": {"name": "echo"}})
                elif family == "anthropic-messages":
                    self.assertEqual(payload["tool_choice"], {"type": "tool", "name": "echo"})
                else:
                    self.assertEqual(payload["toolConfig"]["functionCallingConfig"], {"mode": "ANY", "allowedFunctionNames": ["echo"]})
                decoded = decode_profile_response(first, tool_response(family), selected)
                self.assertEqual(decoded.finish_reason, FinishReason.TOOL_CALL)
                call = decoded.tool_calls[0]
                history = (*first.messages, Message("assistant", (ContentBlock("tool_call", data={
                    "call_id": call.call_id, "name": call.name, "arguments": call.arguments}),)),
                    Message("tool", (ContentBlock("tool_result", data={"call_id": call.call_id, "name": call.name,
                                                                        "output": {"value": "probe"}, "is_error": False}),)))
                second = replace(first, messages=history, tool_choice=ToolChoice("none"))
                next_payload = encode_profile_request(second, selected)
                if family == "responses":
                    self.assertEqual(next_payload["input"][-1], {"type": "function_call_output", "call_id": "call-1", "output": '{"value":"probe"}'})
                elif family == "chat-completions":
                    self.assertEqual(next_payload["messages"][-1], {"role": "tool", "tool_call_id": "call-1", "content": '{"value":"probe"}'})
                elif family == "anthropic-messages":
                    self.assertEqual(next_payload["messages"][-1]["content"][0]["tool_use_id"], "call-1")
                else:
                    self.assertEqual(next_payload["contents"][-1]["parts"][0]["functionResponse"],
                                     {"id": "call-1", "name": "echo", "response": {"value": "probe"}})
                self.assertEqual(decode_profile_response(second, fixture(family), selected).finish_reason, FinishReason.COMPLETE)

    def test_schema_output_locations_and_local_validation(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                req, selected = request(response_format=ResponseFormat("json_schema", "ok", SCHEMA)), profile(family)
                payload = encode_profile_request(req, selected)
                location = (payload["text"]["format"]["schema"] if family == "responses" else
                            payload["response_format"]["json_schema"]["schema"] if family == "chat-completions" else
                            payload["output_config"]["format"]["schema"] if family == "anthropic-messages" else
                            payload["generationConfig"]["responseJsonSchema"])
                self.assertEqual(location, SCHEMA)
                raw = fixture(family)
                if family == "responses": raw["output"][0]["content"][0]["text"] = '{"ok":true}'
                elif family == "chat-completions": raw["choices"][0]["message"]["content"] = '{"ok":true}'
                elif family == "anthropic-messages": raw["content"][0]["text"] = '{"ok":true}'
                else: raw["candidates"][0]["content"]["parts"][0]["text"] = '{"ok":true}'
                self.assertEqual(decode_profile_response(req, raw, selected).finish_reason, FinishReason.COMPLETE)
                if family == "responses": raw["output"][0]["content"][0]["text"] = '{"ok":"true"}'
                elif family == "chat-completions": raw["choices"][0]["message"]["content"] = '{"ok":"true"}'
                elif family == "anthropic-messages": raw["content"][0]["text"] = '{"ok":"true"}'
                else: raw["candidates"][0]["content"]["parts"][0]["text"] = '{"ok":"true"}'
                with self.assertRaises(ProviderError): decode_profile_response(req, raw, selected)

    def test_strict_tool_support_is_exact_and_not_silently_dropped(self):
        req = request(tools=(replace(TOOL, strict=True),))
        for family in ("responses", "chat-completions", "anthropic-messages"):
            self.assertIn("strict", json.dumps(encode_profile_request(req, profile(family))))
        for family, provider in (("responses", "deepseek"), ("chat-completions", "deepseek"),
                                 ("gemini-generate-content", "google"), ("chat-completions", "minimax")):
            with self.subTest(family=family, provider=provider):
                selected = profile(family, provider)
                with self.assertRaises(ProviderError): encode_profile_request(replace(req, model=selected["model"]["requested_id"]), selected)
        beta = encode_profile_request(replace(req, model="deepseek-flash"), profile("chat-completions", "deepseek", beta=True))
        self.assertIs(beta["tools"][0]["function"]["strict"], True)
        with self.assertRaises(ProviderError): encode_profile_request(request(model="deepseek-flash", tools=(TOOL,)), profile("chat-completions", "deepseek", beta=True))

    def test_deepseek_schema_policy_and_developer_roles(self):
        req = request(model="deepseek-flash", response_format=ResponseFormat("json_schema", "ok", SCHEMA))
        response_payload = encode_profile_request(req, profile("responses", "deepseek"))
        self.assertNotIn("strict", response_payload["text"]["format"])
        with self.assertRaises(ProviderError): encode_profile_request(req, profile("chat-completions", "deepseek"))
        developer = request(messages=(Message("developer", (ContentBlock("text", text="Privileged instruction."),)),
                                      Message("user", (ContentBlock("text", text="OK"),))))
        for family, provider in (("responses", "deepseek"), ("chat-completions", "deepseek"),
                                 ("anthropic-messages", "anthropic"), ("gemini-generate-content", "google")):
            with self.subTest(family=family):
                selected = profile(family, provider)
                with self.assertRaises(ProviderError): encode_profile_request(replace(developer, model=selected["model"]["requested_id"]), selected)
        self.assertEqual(encode_profile_request(developer, profile("responses"))["input"][0]["role"], "developer")

    def test_unknown_profile_request_modes_policies_and_capabilities_rejected(self):
        for field, value in (("mode", "thinking"), ("parameter_profile_id", "dynamic-code"), ("continuation_policy", "provider-state")):
            selected = profile("responses")
            selected["generation"][field] = value
            with self.subTest(field=field):
                with self.assertRaises(ProviderError): encode_profile_request(request(), selected)
        selected = profile("responses")
        selected["mapping"]["schema_policy_id"] = "guessed-schema-v2"
        with self.assertRaises(ProviderError): encode_profile_request(request(), selected)
        selected["mapping"]["schema_policy_id"] = []
        with self.assertRaises(ProviderError): encode_profile_request(request(), selected)
        with self.assertRaises(ModelNotSupported): encode_profile_request(request(model="other-model"), profile("responses"))
        for req in (request(reasoning_effort="none"), request(extensions={"openai": {"native_payload": {}}}),
                    request(metadata={"user_id": "synthetic"}), request(messages=(Message("user", (ContentBlock("image"),)),))):
            with self.assertRaises((ProviderError, CapabilityGap)): encode_profile_request(req, profile("responses"))
        with self.assertRaises(ProviderError): encode_profile_request(request(), profile("chat-completions", "openrouter"))

    def test_const_and_unclosed_schema_keywords_rejected_before_encoding(self):
        for schema in ({"type": "object", "properties": {"ok": {"const": True}}, "required": ["ok"], "additionalProperties": False},
                       {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": [], "additionalProperties": False},
                       {**SCHEMA, "additionalProperties": True}):
            with self.subTest(schema=schema):
                with self.assertRaises(ProviderError): encode_profile_request(request(response_format=ResponseFormat("json_schema", "ok", schema)), profile("responses"))

    def test_unsafe_response_states_do_not_authorize_tools(self):
        req = request(tools=(TOOL,))
        for status in ("failed", "cancelled", "queued", "in_progress", "incomplete"):
            raw = tool_response("responses")
            raw["status"] = status
            if status == "incomplete": raw["incomplete_details"] = {"reason": "max_output_tokens"}
            with self.subTest(status=status):
                with self.assertRaises(ProviderError): decode_profile_response(req, raw, profile("responses"))
        for family in ("chat-completions", "anthropic-messages", "gemini-generate-content"):
            raw = tool_response(family)
            if family == "chat-completions": raw["choices"][0]["finish_reason"] = "length"
            elif family == "anthropic-messages": raw["stop_reason"] = "pause_turn"
            else: raw["candidates"][0]["finishReason"] = "SAFETY"
            with self.subTest(family=family):
                with self.assertRaises(ProviderError): decode_profile_response(req, raw, profile(family))

    def test_stops_refusals_and_context_limits_are_not_flattened(self):
        for reason, expected in (("pause_turn", FinishReason.PAUSED), ("refusal", FinishReason.REFUSAL),
                                 ("model_context_window_exceeded", FinishReason.CONTEXT_LIMIT), ("max_tokens", FinishReason.LENGTH)):
            raw = fixture("anthropic-messages")
            raw["stop_reason"] = reason
            self.assertEqual(decode_profile_response(request(), raw, profile("anthropic-messages")).finish_reason, expected)
        raw = fixture("responses")
        raw.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
        self.assertEqual(decode_profile_response(request(), raw, profile("responses")).finish_reason, FinishReason.LENGTH)
        raw = fixture("gemini-generate-content")
        raw.update(candidates=[], promptFeedback={"blockReason": "SAFETY"})
        self.assertEqual(decode_profile_response(request(), raw, profile("gemini-generate-content")).finish_reason, FinishReason.REFUSAL)

    def test_reasoning_and_signatures_are_not_captured_or_guessed(self):
        marker = "synthetic-private-reasoning"
        for family in FAMILIES:
            raw = fixture(family)
            if family == "responses": raw["output"].append({"type": "reasoning", "content": marker})
            elif family == "chat-completions": raw["choices"][0]["message"]["reasoning_content"] = marker
            elif family == "anthropic-messages": raw["content"].append({"type": "thinking", "thinking": marker})
            else: raw["candidates"][0]["content"]["parts"][0]["thoughtSignature"] = marker
            with self.subTest(family=family):
                with self.assertRaises(ProviderError) as caught: decode_profile_response(request(), raw, profile(family))
                self.assertNotIn(marker, str(caught.exception))

    def test_usage_components_unknowns_and_actual_model_preserved(self):
        for family in FAMILIES:
            actual = decode_profile_response(request(), fixture(family), profile(family))
            self.assertEqual(actual.usage.cached_input_tokens, 4)
            self.assertEqual(actual.usage.total_tokens, 17 if family == "anthropic-messages" else 15)
            self.assertIsNone(actual.usage.provider_reported_cost)
            raw = fixture(family)
            raw.pop("usageMetadata" if family == "gemini-generate-content" else "usage")
            self.assertIsNone(decode_profile_response(request(), raw, profile(family)).usage.total_tokens)
            key = "modelVersion" if family == "gemini-generate-content" else "model"
            raw[key] = "actual-revision-2"
            self.assertEqual(decode_profile_response(request(), raw, profile(family)).model, "actual-revision-2")
            raw.pop(key)
            with self.assertRaises(ProviderError): decode_profile_response(request(), raw, profile(family))
        raw = fixture("anthropic-messages")
        raw["usage"].pop("cache_creation_input_tokens")
        self.assertIsNone(decode_profile_response(request(), raw, profile("anthropic-messages")).usage.input_tokens)
        raw = fixture("gemini-generate-content")
        raw["usageMetadata"]["thoughtsTokenCount"] = 5
        raw["usageMetadata"]["totalTokenCount"] = 20
        result = decode_profile_response(request(), raw, profile("gemini-generate-content"))
        self.assertEqual((result.usage.output_tokens, result.usage.reasoning_tokens, result.usage.total_tokens), (8, 5, 20))

    def test_bad_usage_and_cost_never_turn_into_zero(self):
        for bad in (True, -1, "12"):
            raw = fixture("responses")
            raw["usage"]["input_tokens"] = bad
            with self.assertRaises(ProviderError): decode_profile_response(request(), raw, profile("responses"))
        for bad in (True, -0.1, float("nan"), "unknown"):
            raw = fixture("chat-completions")
            raw["usage"]["cost"] = bad
            with self.assertRaises(ProviderError): decode_profile_response(request(), raw, profile("chat-completions"))
        raw = fixture("chat-completions")
        raw["usage"].update(cost=0.002, currency="USD")
        self.assertEqual(decode_profile_response(request(), raw, profile("chat-completions")).usage.provider_reported_cost, 0.002)

    def test_tool_arguments_ids_and_parallel_preflight(self):
        req = request(tools=(TOOL,))
        for arguments in ('{"value":"wrong"}', '{"value":"probe","extra":1}', '{"value":NaN}',
                          '{"value":"wrong","value":"probe"}', '[]', 'not-json'):
            raw = tool_response("responses")
            raw["output"][0]["arguments"] = arguments
            with self.subTest(arguments=arguments):
                with self.assertRaises(ProviderError): decode_profile_response(req, raw, profile("responses"))
        raw = tool_response("responses")
        raw["output"].append(copy.deepcopy(raw["output"][0]))
        with self.assertRaises(ProviderError): decode_profile_response(req, raw, profile("responses"))
        raw["output"][1]["call_id"] = "call-2"
        selected = profile("responses")
        selected["implementation"]["capabilities"].remove("parallel_tools")
        with self.assertRaises(ProviderError): decode_profile_response(req, raw, selected)
        self.assertEqual(len(decode_profile_response(req, raw, profile("responses")).tool_calls), 2)
        with self.assertRaises(ProviderError): decode_profile_response(replace(req, tool_choice=ToolChoice("none")), raw, profile("responses"))

    def test_history_unpaired_calls_errors_and_deep_frozen_profile(self):
        orphan = request(tools=(TOOL,), messages=(Message("tool", (ContentBlock("tool_result", data={"call_id": "unknown", "output": "probe"}),)),))
        with self.assertRaises(ProviderError): encode_profile_request(orphan, profile("responses"))
        unanswered = request(tools=(TOOL,), messages=(Message("assistant", (ContentBlock("tool_call", data={"call_id": "x", "name": "echo", "arguments": {"value": "probe"}}),)),))
        with self.assertRaises(ProviderError): encode_profile_request(unanswered, profile("responses"))
        intervening = replace(unanswered, messages=(*unanswered.messages,
            Message("user", (ContentBlock("text", text="Interrupt before results"),)),
            Message("tool", (ContentBlock("tool_result", data={"call_id": "x", "output": "probe"}),))))
        with self.assertRaises(ProviderError): encode_profile_request(intervening, profile("responses"))
        original = profile("responses")
        before = copy.deepcopy(original)
        frozen = freeze(original)
        first, second = encode_profile_request(request(), frozen), encode_profile_request(request(), frozen)
        first["input"][0]["content"] = "mutated local output"
        self.assertEqual(second["input"][0]["content"], "Synthetic only.")
        self.assertEqual(original, before)

    def test_actual_profile_parser_to_wire_path_and_explicit_gaps(self):
        base = Path(__file__).with_name("fixtures") / "provider_profile_configuration" / "vendors"
        unsupported = {"siliconflow", "openrouter"}
        controls = {"alibaba-dashscope": ("enable_thinking", False),
                    "zhipu": ("thinking", {"type": "disabled"}),
                    "moonshot": ("thinking", {"type": "disabled"}),
                    "deepseek": ("reasoning", {"effort": "none"}),
                    "minimax": ("reasoning", {"effort": "none"}),
                    "bytedance-ark": ("thinking", {"type": "disabled"})}
        paths = sorted(base.glob("*/positive.profile.json"))
        self.assertEqual({path.parent.name for path in paths},
                         {"alibaba-dashscope", "anthropic", "bytedance-ark", "deepseek", "google", "minimax",
                          "moonshot", "openai", "openrouter", "siliconflow", "zhipu"})
        accepted = set()
        for path in paths:
            parsed = ProviderApiProfile.from_mapping(json.loads(path.read_text(encoding="utf-8")))
            family = parsed.document["protocol"]["family"]
            req = request(model=parsed.document["model"]["requested_id"])
            with self.subTest(provider=parsed.provider):
                if parsed.provider in unsupported:
                    with self.assertRaises(ProviderError): encode_profile_request(req, parsed.document)
                    continue
                payload = encode_profile_request(req, parsed.document)
                accepted.add(parsed.provider)
                if parsed.provider in controls:
                    key, expected = controls[parsed.provider]
                    self.assertEqual(payload[key], expected)
                raw = fixture(family)
                raw["modelVersion" if family == "gemini-generate-content" else "model"] = req.model
                actual = decode_profile_response(req, raw, parsed.document)
                self.assertEqual((actual.provider, actual.model), (parsed.provider, req.model))
        self.assertEqual(len(accepted), 9)

    def test_actual_deepseek_profile_schema_and_local_tool_subset(self):
        path = Path(__file__).with_name("fixtures") / "provider_profile_configuration" / "vendors" / "deepseek" / "positive.profile.json"
        parsed = ProviderApiProfile.from_mapping(json.loads(path.read_text(encoding="utf-8")))
        req = request(model=parsed.document["model"]["requested_id"], tools=(TOOL,), tool_choice=ToolChoice("specific", "echo"))
        payload = encode_profile_request(req, parsed.document)
        self.assertEqual(payload["tool_choice"], {"type": "function", "name": "echo"})
        self.assertNotIn("strict", payload["tools"][0])
        raw = tool_response("responses")
        raw["model"] = req.model
        self.assertEqual(decode_profile_response(req, raw, parsed.document).provider, "deepseek")
        with self.assertRaises(ProviderError): encode_profile_request(replace(req, tools=(replace(TOOL, strict=True),)), parsed.document)

    def test_native_nonthinking_registry_is_exact_model_bound(self):
        self.assertEqual(set(NATIVE_PARAMETER_REGISTRY), set(NATIVE_MODEL_REGISTRY))
        for (provider, family, mode), fields in NATIVE_PARAMETER_REGISTRY.items():
            selected = profile(family, provider)
            selected["generation"]["mode"] = mode
            selected["model"]["requested_id"] = next(iter(NATIVE_MODEL_REGISTRY[(provider, family, mode)]))
            req = request(model=selected["model"]["requested_id"])
            with self.subTest(provider=provider, family=family):
                payload = encode_profile_request(req, freeze(selected))
                self.assertEqual(freeze({key: payload[key] for key in fields}), fields)
                self.assertEqual(payload["model"], req.model)
                selected["model"]["requested_id"] = "unverified-or-forced-thinking-model"
                with self.assertRaises(ProviderError):
                    encode_profile_request(replace(req, model=selected["model"]["requested_id"]), selected)

    def test_minimax_and_moonshot_choice_subsets_are_not_openai_aliases(self):
        for provider, family, model in (("minimax", "responses", "MiniMax-M3"),
                                        ("moonshot", "chat-completions", "kimi-k2.6")):
            selected = profile(family, provider)
            selected["generation"]["mode"] = "nonthinking"
            selected["model"]["requested_id"] = model
            for kind in ("auto", "none"):
                payload = encode_profile_request(request(model=model, tools=(TOOL,), tool_choice=ToolChoice(kind)), selected)
                self.assertEqual(payload["tool_choice"], kind)
            for kind in ("required", "specific"):
                with self.assertRaises(ProviderError):
                    encode_profile_request(request(model=model, tools=(TOOL,), tool_choice=ToolChoice(kind, "echo" if kind == "specific" else None)), selected)
            if provider == "minimax":
                self.assertNotIn("store", payload)
            else:
                with self.assertRaises(ProviderError): encode_profile_request(request(model=model, temperature=0.6), selected)

    def test_hard_data_policy_is_preserved_without_fabricated_account_evidence(self):
        for policy in (DataPolicy(local_only=True), DataPolicy(zero_data_retention_required=True),
                       DataPolicy(training_opt_out_required=True), DataPolicy(allowed_regions=("EU",))):
            req = request(data_policy=policy)
            with self.assertRaises(DataPolicyGap): encode_profile_request(req, profile("responses"))
            self.assertIs(req.data_policy, policy)

    def test_codec_version_and_provisional_policy_ids_reject(self):
        for version in (None, "0.1.0", "future"):
            selected = profile("responses")
            selected["implementation"]["codec_version"] = version
            with self.assertRaises(ProviderError): encode_profile_request(request(), selected)
        selected = profile("responses")
        selected["mapping"]["role_policy_id"] = "native-v1"
        with self.assertRaises(ProviderError): encode_profile_request(request(), selected)

    def test_usage_nullable_details_and_total_reconciliation(self):
        for family, fields in (("responses", ("input_tokens_details", "output_tokens_details")),
                               ("chat-completions", ("prompt_tokens_details", "completion_tokens_details"))):
            raw = fixture(family)
            raw["usage"].update({field: None for field in fields})
            result = decode_profile_response(request(), raw, profile(family))
            self.assertIsNone(result.usage.cached_input_tokens)
            self.assertIsNone(result.usage.reasoning_tokens)
            for malformed in (False, 0, [], "not-an-object"):
                raw["usage"][fields[0]] = malformed
                with self.assertRaises(ProviderError): decode_profile_response(request(), raw, profile(family))
        for family in FAMILIES:
            raw = fixture(family)
            usage = raw["usageMetadata" if family == "gemini-generate-content" else "usage"]
            total_key = "totalTokenCount" if family == "gemini-generate-content" else "total_tokens"
            for bad in (True, -1, 999):
                usage[total_key] = bad
                with self.assertRaises(ProviderError): decode_profile_response(request(), raw, profile(family))

    def test_unknown_or_malformed_stops_and_wrong_output_roles_reject(self):
        for family in FAMILIES:
            for reason in (None, "new-terminal-state", [], {}):
                raw = fixture(family)
                if family == "responses":
                    raw.update(status="incomplete", incomplete_details={"reason": reason})
                elif family == "chat-completions": raw["choices"][0]["finish_reason"] = reason
                elif family == "anthropic-messages": raw["stop_reason"] = reason
                else: raw["candidates"][0]["finishReason"] = reason
                with self.subTest(family=family, reason=reason):
                    with self.assertRaises(ProviderError): decode_profile_response(request(), raw, profile(family))
        raw = fixture("responses")
        raw["output"][0]["role"] = "user"
        with self.assertRaises(ProviderError): decode_profile_response(request(), raw, profile("responses"))
        raw = fixture("gemini-generate-content")
        raw["candidates"][0]["content"]["role"] = "user"
        with self.assertRaises(ProviderError): decode_profile_response(request(), raw, profile("gemini-generate-content"))

    def test_parameter_types_and_compatible_schema_strict_are_explicit(self):
        for req in (request(max_output_tokens=True), request(max_output_tokens=2.5), request(temperature=True), request(temperature="0.2")):
            with self.assertRaises(ProviderError): encode_profile_request(req, profile("responses"))
        selected = profile("chat-completions", "alibaba-dashscope")
        payload = encode_profile_request(request(response_format=ResponseFormat("json_schema", "ok", SCHEMA)), selected)
        self.assertNotIn("strict", payload["response_format"]["json_schema"])

    def test_decoder_rejects_undeclared_profile_tools_before_returning_calls(self):
        selected = profile("responses")
        selected["implementation"]["capabilities"] = ["text"]
        with self.assertRaises(CapabilityGap):
            decode_profile_response(request(tools=(TOOL,)), tool_response("responses"), selected)

    def test_parse_failures_keep_no_raw_exception_context_or_cause(self):
        marker = "wire-diagnostic-synthetic-marker"
        for family in ("responses", "chat-completions"):
            for argument in (marker + '{"invalid":', '{"value":"probe","value":"' + marker + '"}',
                             '{"value":NaN,"other":"' + marker + '"}'):
                raw = tool_response(family)
                if family == "responses": raw["output"][0]["arguments"] = argument
                else: raw["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = argument
                with self.subTest(family=family, kind=argument[:12]):
                    with self.assertRaises(ProviderError) as caught:
                        decode_profile_response(request(tools=(TOOL,)), raw, profile(family))
                    self.assertIsNone(caught.exception.__cause__)
                    self.assertIsNone(caught.exception.__context__)
                    self.assertNotIn(marker, str(caught.exception))
        selected = profile("responses")
        selected["implementation"]["capabilities"] = [marker]
        with self.assertRaises(ProviderError) as caught: encode_profile_request(request(), selected)
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)
        self.assertNotIn(marker, str(caught.exception))

    def test_delegated_schema_parse_errors_are_sanitized_at_codec_boundary(self):
        marker = "wire-schema-synthetic-marker"
        malformed = {"type": marker}
        for req in (request(response_format=ResponseFormat("json_schema", "ok", malformed)),
                    request(tools=(replace(TOOL, input_schema=malformed),))):
            with self.assertRaises(ProviderError) as caught: encode_profile_request(req, profile("responses"))
            self.assertIsNone(caught.exception.__cause__)
            self.assertIsNone(caught.exception.__context__)
            self.assertNotIn(marker, str(caught.exception))

    def test_structured_output_rejects_nonfinite_json_and_duplicate_members(self):
        marker = "wire-schema-synthetic-marker"
        schema = {"type": "object", "properties": {"value": {"type": "number"}},
                  "required": ["value"], "additionalProperties": False}
        req = request(response_format=ResponseFormat("json_schema", "value", schema))
        for text in ('{"value":NaN}', '{"value":Infinity}', '{"value":1,"value":2}'):
            raw = fixture("responses")
            raw["output"][0]["content"][0]["text"] = text
            with self.assertRaises(ProviderError) as caught: decode_profile_response(req, raw, profile("responses"))
            self.assertIsNone(caught.exception.__cause__)
            self.assertIsNone(caught.exception.__context__)
        req = request(response_format=ResponseFormat("json_schema", "ok", SCHEMA))
        for family in FAMILIES:
            raw = fixture(family)
            if family == "responses": raw["output"][0]["content"][0]["text"] = marker + "{"
            elif family == "chat-completions": raw["choices"][0]["message"]["content"] = marker + "{"
            elif family == "anthropic-messages": raw["content"][0]["text"] = marker + "{"
            else: raw["candidates"][0]["content"]["parts"][0]["text"] = marker + "{"
            with self.assertRaises(ProviderError) as caught: decode_profile_response(req, raw, profile(family))
            self.assertIsNone(caught.exception.__cause__)
            self.assertIsNone(caught.exception.__context__)
            self.assertNotIn(marker, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
