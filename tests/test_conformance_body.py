"""Pure fixed-body admission; synthetic values only, no auth/header inspection."""

from dataclasses import replace
import json
from pathlib import Path
import traceback
import unittest

from research_workbench.adapters.models.conformance_body import (
    ConformanceBodyError, ConformanceBodyPolicy, PHASES, SCHEMA_PROMPT, TOOL_PROMPT,
    policy_pin, prepare_body_admission, revalidate_body_admission, result_schema, tool_schema,
    validate_encoded_body, validated_response_context,
)
from research_workbench.adapters.models.port import (
    ContentBlock, DataPolicy, FinishReason, Message, ModelRequest, ModelResponse,
    ResponseFormat, ToolCall, ToolChoice, ToolDefinition,
)
from research_workbench.adapters.models.wire_codecs import encode_profile_request


def synthetic_request(phase="specific-tool", *, call_id="actual-synthetic-call", texts=()):
    definition = ToolDefinition("add_ints", "Add two synthetic integers.", tool_schema(), strict=False)
    user = Message("user", (ContentBlock("text", text=TOOL_PROMPT),))
    if phase == "specific-tool":
        return ModelRequest("deepseek-flash", (user,), tools=(definition,),
            tool_choice=ToolChoice("specific", "add_ints"), max_output_tokens=32)
    if phase == "result-text":
        assistant = Message("assistant", tuple(ContentBlock("text", text=text) for text in texts) + (
            ContentBlock("tool_call", data={"call_id": call_id, "name": "add_ints", "arguments": {"a": 3, "b": 4}}),))
        result = Message("tool", (ContentBlock("tool_result", data={"call_id": call_id, "name": "add_ints", "output": 7, "is_error": False}),))
        return ModelRequest("deepseek-flash", (user, assistant, result), tools=(definition,),
            tool_choice=ToolChoice("none"), max_output_tokens=32)
    return ModelRequest("deepseek-flash", (Message("user", (ContentBlock("text", text=SCHEMA_PROMPT),)),),
        response_format=ResponseFormat("json_schema", "sum", result_schema()), max_output_tokens=32)


def admission_state(admission):
    return (admission.phase, admission.policy_state, admission.model_request, admission.request_state,
            admission.expected_body, admission.expected_call_id, admission.expected_assistant_text)


class ConformanceBodyTests(unittest.TestCase):
    def setUp(self):
        self.policy = ConformanceBodyPolicy(max_output_tokens=32)
        path = Path(__file__).resolve().parents[1] / "registry/providers/profiles/deepseek-responses-v1.json"
        self.profile = json.loads(path.read_text(encoding="utf-8"))

    def admit(self, phase="specific-tool", request=None, *, call_id=None, texts=()):
        return prepare_body_admission(self.policy, phase, request or synthetic_request(phase),
                                      expected_call_id=call_id, expected_assistant_text=texts)

    def test_actual_codec_three_phases_and_validated_assistant_text(self):
        response = ModelResponse("synthetic-id", "deepseek", "deepseek-flash",
            (ContentBlock("text", text="Adding the two integers."),), FinishReason.TOOL_CALL,
            (ToolCall("actual-synthetic-call", "add_ints", {"a": 3, "b": 4}),))
        call_id, texts = validated_response_context(response)
        for phase in PHASES:
            request = synthetic_request(phase, call_id=call_id, texts=texts)
            admission = self.admit(phase, request, call_id=call_id if phase == "result-text" else None,
                                   texts=texts if phase == "result-text" else ())
            actual = json.dumps(encode_profile_request(request, self.profile), ensure_ascii=False).encode()
            validate_encoded_body(self.policy, admission, admission_state(admission), actual)
            self.assertLessEqual(len(actual), 4096)
            self.assertEqual(json.loads(actual)["reasoning"], {"effort": "none"})
            self.assertNotIn(call_id, repr(admission))

    def test_policy_is_explicit_frozen_exact_family_and_output_bound(self):
        for options in ({"model": "other"}, {"protocol_family": "chat-completions"}, {"mode": "thinking"},
                        {"provider": "other"}, {"max_output_tokens": True}, {"max_output_tokens": 257},
                        {"max_body_bytes": 4097}, {"max_body_bytes": 0}):
            with self.subTest(options=options), self.assertRaises(ConformanceBodyError):
                ConformanceBodyPolicy(**options)
        with self.assertRaises(AttributeError):
            self.policy.model = "other"

    def test_valid_tool_argument_order_does_not_change_semantics(self):
        request = synthetic_request("result-text")
        request.messages[1].content[0].data["arguments"] = {"b": 4, "a": 3}
        admission = self.admit("result-text", request, call_id="actual-synthetic-call")
        body = json.dumps(encode_profile_request(request, self.profile)).encode()
        validate_encoded_body(self.policy, admission, admission_state(admission), body)

    def test_wrong_model_choice_output_prompt_extensions_and_data_policy_refuse(self):
        request = synthetic_request()
        variants = [replace(request, model="other"), replace(request, tool_choice=ToolChoice("auto")),
            replace(request, max_output_tokens=256), replace(request, max_output_tokens=True),
            replace(request, temperature=0), replace(request, reasoning_effort="none"),
            replace(request, extensions={"secret": "SYNTHETIC-PRIVATE"}), replace(request, metadata={"extra": "x"}),
            replace(request, data_policy=DataPolicy(local_only=True)), replace(request, data_policy=DataPolicy(local_only=0)),
            replace(request, messages=(Message("user", (ContentBlock("text", text="different"),)),)),
            replace(request, messages=(Message("user", (ContentBlock("image", data={}),)),)),
            replace(request, messages=tuple([request.messages[0]] * 9))]
        for variant in variants:
            with self.subTest(variant=variant.model), self.assertRaises(ConformanceBodyError):
                self.admit(request=variant)

    def test_tool_and_enum_schema_dialect_are_closed(self):
        request = synthetic_request()
        for change in ({"name": "other"}, {"strict": True}, {"description": "changed"},
                       {"input_schema": {**tool_schema(), "$ref": "private"}},
                       {"input_schema": {"type": "object"}}):
            with self.subTest(change=change), self.assertRaises(ConformanceBodyError):
                self.admit(request=replace(request, tools=(replace(request.tools[0], **change),)))
        structured = synthetic_request("structured")
        for format in (ResponseFormat("text"), ResponseFormat("json_schema", "sum", {**result_schema(), "extra": True}),
                       ResponseFormat("json_schema", "sum", {"type": "object", "properties": {"sum": {"const": 7}}})):
            with self.assertRaises(ConformanceBodyError):
                self.admit("structured", replace(structured, response_format=format))

    def test_real_call_id_result_and_response_text_bound_and_drift(self):
        request = synthetic_request("result-text", texts=("Bound first response text.",))
        self.admit("result-text", request, call_id="actual-synthetic-call", texts=("Bound first response text.",))
        for call_id, texts in (("replaced-call", ("Bound first response text.",)),
                              ("actual-synthetic-call", ("new arbitrary text",)), (None, ())):
            with self.assertRaises(ConformanceBodyError):
                self.admit("result-text", request, call_id=call_id, texts=texts)
        request.messages[2].content[0].data["output"] = 8
        with self.assertRaises(ConformanceBodyError):
            self.admit("result-text", request, call_id="actual-synthetic-call", texts=("Bound first response text.",))
        response = ModelResponse("synthetic-id", "deepseek", "deepseek-flash", (ContentBlock("text", text="x" * 129),),
            FinishReason.TOOL_CALL, (ToolCall("actual-synthetic-call", "add_ints", {"a": 3, "b": 4}),))
        with self.assertRaises(ConformanceBodyError):
            validated_response_context(response)

    def test_encoded_body_closed_flags_input_cap_and_duplicate_json(self):
        admission = self.admit()
        state = admission_state(admission)
        original = json.loads(admission.expected_body)
        changes = ({"model": "other"}, {"reasoning": {"effort": "low"}}, {"max_output_tokens": 257},
                   {"previous_response_id": "undeclared"}, {"stream": False}, {"input": []},
                   {"tools": []}, {"tool_choice": "auto"}, {"temperature": 0})
        for update in changes:
            with self.subTest(update=update), self.assertRaises(ConformanceBodyError):
                validate_encoded_body(self.policy, admission, state, json.dumps({**original, **update}).encode())
        for raw in (admission.expected_body + b" " * 4096, b'{"model":"x","model":"x"}', b"{", b"[]", b'{"x":NaN}'):
            with self.assertRaises(ConformanceBodyError):
                validate_encoded_body(self.policy, admission, state, raw)

    def test_request_policy_and_private_admission_mutation_are_rechecked(self):
        request = synthetic_request()
        admission = self.admit(request=request)
        state = admission_state(admission)
        request.tools[0].input_schema["properties"]["a"]["enum"][0] = 4
        with self.assertRaises(ConformanceBodyError):
            revalidate_body_admission(self.policy, admission, state)
        request.tools[0].input_schema["properties"]["a"]["enum"][0] = 3
        object.__setattr__(admission, "expected_body", b"{}")
        with self.assertRaises(ConformanceBodyError):
            validate_encoded_body(self.policy, admission, state, b"{}")
        object.__setattr__(self.policy, "max_body_bytes", 2048)
        self.assertNotEqual(admission.policy_state, policy_pin(self.policy))

    def test_failure_keeps_no_raw_marker_or_exception_chain(self):
        marker = "SYNTHETIC-PRIVATE-BODY"
        try:
            raise RuntimeError(marker)
        except RuntimeError:
            with self.assertRaises(ConformanceBodyError) as caught:
                self.admit(request=replace(synthetic_request(), model=marker))
        error = caught.exception
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertNotIn(marker, str(error) + repr(error) + "".join(traceback.format_exception(error)))


if __name__ == "__main__":
    unittest.main()
