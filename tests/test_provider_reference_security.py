"""Synthetic response-side reference failures, without credentials or network."""

import json
import socket
import traceback
import unittest
from dataclasses import replace
from unittest import mock

from jsonschema import Draft202012Validator

from research_workbench.adapters.models import (
    Capability, ContentBlock, FinishReason, Message, ModelRequest, ModelResponse,
    OpenAIResponsesProvider, ProviderError, ProviderErrorCategory, ResponseFormat,
    ToolCall, ToolChoice, ToolDefinition,
)
from research_workbench.adapters.models.base import (
    validate_response_contract, validate_structured_response,
)
from research_workbench.adapters.models.http import HttpResponse


SENTINEL = "SYNTHETIC_REFERENCE_SCHEMA_PRIVATE"


def schema(*, missing=False):
    return {
        "type": "object",
        "properties": {"value": {"$ref": "#/$defs/value"}},
        "$defs": {} if missing else {"value": {"type": "string"}},
        "required": ["value"], "additionalProperties": False,
        "description": SENTINEL,
    }


class FakeCredential:
    def __init__(self):
        self.resolutions = 0

    def resolve(self):
        self.resolutions += 1
        return "synthetic-offline-credential"

    def available(self):
        raise AssertionError("credential presence checks are forbidden")


class FakeTransport:
    def __init__(self, *, tool=False, value="synthetic"):
        self.requests = []
        output = (
            [{"type": "function_call", "call_id": "synthetic-call", "name": "probe",
              "arguments": json.dumps({"value": value})}]
            if tool else
            [{"type": "message", "role": "assistant", "content": [
                {"type": "output_text", "text": json.dumps({"value": value})},
            ]}]
        )
        self.document = {
            "id": "synthetic-response", "model": "synthetic-model",
            "status": "completed", "output": output,
        }

    def send(self, request):
        self.requests.append(request)
        return HttpResponse(200, {}, json.dumps(self.document).encode())


def request(*, tool=False, missing=False):
    value = ModelRequest(
        "synthetic-model", (Message("user", (ContentBlock("text", "Synthetic only."),)),),
        max_output_tokens=32,
    )
    if tool:
        return replace(
            value, tools=(ToolDefinition("probe", "Synthetic only.", schema(missing=missing)),),
            tool_choice=ToolChoice("specific", "probe"),
        )
    return replace(value, response_format=ResponseFormat("json_schema", "probe", schema(missing=missing)))


class ProviderReferenceSecurityTests(unittest.TestCase):
    def setUp(self):
        for name in ("socket", "create_connection"):
            patcher = mock.patch.object(socket, name, side_effect=AssertionError("network is forbidden"))
            patcher.start()
            self.addCleanup(patcher.stop)

    def provider(self, *, tool=False, value="synthetic"):
        credential, transport = FakeCredential(), FakeTransport(tool=tool, value=value)
        provider = OpenAIResponsesProvider(
            model="synthetic-model", credential=credential, transport=transport,
            supported=frozenset({Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}),
        )
        return provider, credential, transport

    def assert_safe(self, error):
        self.assertEqual(ProviderErrorCategory.CONTRACT_VIOLATION, error.category)
        rendered = str(error) + repr(error) + "".join(traceback.format_exception(error))
        self.assertNotIn(SENTINEL, rendered)
        self.assertNotIn(SENTINEL, repr(vars(error)))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)

    def assert_missing_reference_rejected_after_response(self, *, tool):
        req = request(tool=tool, missing=True)
        Draft202012Validator.check_schema(req.tools[0].input_schema if tool else req.response_format.schema)
        provider, credential, transport = self.provider(tool=tool)
        with self.assertRaises(ProviderError) as caught:
            provider.generate(req)
        self.assert_safe(caught.exception)
        self.assertEqual(1, credential.resolutions)
        self.assertEqual(1, len(transport.requests))

    def test_missing_local_reference_structured_response_has_safe_typed_failure(self):
        self.assert_missing_reference_rejected_after_response(tool=False)

    def test_missing_local_reference_tool_arguments_have_safe_typed_failure(self):
        self.assert_missing_reference_rejected_after_response(tool=True)

    def test_missing_reference_does_not_inherit_caller_exception_context(self):
        for tool in (False, True):
            with self.subTest(tool=tool):
                req = request(tool=tool, missing=True)
                response = ModelResponse(
                    "synthetic-response", "openai", "synthetic-model",
                    () if tool else (ContentBlock("text", '{"value":"synthetic"}'),),
                    FinishReason.TOOL_CALL if tool else FinishReason.COMPLETE,
                    (ToolCall("synthetic-call", "probe", {"value": "synthetic"}),) if tool else (),
                )
                try:
                    raise RuntimeError(SENTINEL)
                except RuntimeError:
                    with self.assertRaises(ProviderError) as caught:
                        validate_response_contract(req, response)
                self.assert_safe(caught.exception)
                self.assertTrue(caught.exception.__suppress_context__)

    def test_resolved_local_reference_preserves_valid_structured_and_tool_responses(self):
        for tool in (False, True):
            with self.subTest(tool=tool):
                provider, credential, transport = self.provider(tool=tool)
                response = provider.generate(request(tool=tool))
                self.assertEqual(FinishReason.TOOL_CALL if tool else FinishReason.COMPLETE, response.finish_reason)
                self.assertEqual(1, credential.resolutions)
                self.assertEqual(1, len(transport.requests))

    def test_ordinary_schema_mismatch_preserves_contract_failure(self):
        for tool in (False, True):
            with self.subTest(tool=tool):
                provider, credential, transport = self.provider(tool=tool, value=7)
                with self.assertRaises(ProviderError) as caught:
                    provider.generate(request(tool=tool))
                self.assert_safe(caught.exception)
                self.assertNotIn("reference could not be resolved", str(caught.exception))
                self.assertEqual(1, credential.resolutions)
                self.assertEqual(1, len(transport.requests))

    def test_incomplete_structured_response_still_skips_complete_output_validation(self):
        req = request(missing=True)
        response = ModelResponse(
            "synthetic-response", "openai", "synthetic-model", (), FinishReason.LENGTH,
        )
        self.assertIs(response, validate_structured_response(req, response))


if __name__ == "__main__":
    unittest.main()
