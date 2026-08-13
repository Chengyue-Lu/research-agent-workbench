import json
import unittest
from dataclasses import dataclass

from research_workbench.adapters.models import (
    AnthropicMessagesProvider,
    Capability,
    ContentBlock,
    FinishReason,
    GeminiGenerateContentProvider,
    HttpRequest,
    HttpResponse,
    Message,
    ModelNotSupported,
    ModelRequest,
    OpenAIResponsesProvider,
    ProviderError,
    ProviderErrorCategory,
    ResponseFormat,
    ToolChoice,
    ToolDefinition,
)


@dataclass
class StaticCredential:
    secret: str = "super-secret-test-token"
    resolve_count: int = 0

    @property
    def label(self) -> str:
        return "test:static"

    def available(self) -> bool:
        return True

    def resolve(self) -> str:
        self.resolve_count += 1
        return self.secret


class ScriptedTransport:
    def __init__(self, *responses: HttpResponse) -> None:
        self.responses = list(responses)
        self.requests: list[HttpRequest] = []

    def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected outbound request")
        return self.responses.pop(0)


def response(status: int, document: dict) -> HttpResponse:
    return HttpResponse(
        status_code=status,
        headers={"content-type": "application/json"},
        body=json.dumps(document).encode("utf-8"),
    )


def text_request(model: str, text: str = "hello") -> ModelRequest:
    return ModelRequest(
        model=model,
        messages=(Message("user", (ContentBlock(kind="text", text=text),)),),
    )


def lookup_tool() -> ToolDefinition:
    return ToolDefinition(
        name="lookup",
        description="Look up one bounded record",
        input_schema={
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
            "additionalProperties": False,
        },
    )


class TransportSafetyTests(unittest.TestCase):
    def test_request_repr_suppresses_secret_headers_and_research_body(self) -> None:
        request = HttpRequest(
            method="POST",
            url="https://example.invalid/v1",
            headers={"Authorization": "Bearer super-secret-test-token"},
            body=b"private research material",
        )
        rendered = repr(request)
        self.assertNotIn("super-secret", rendered)
        self.assertNotIn("private research", rendered)
        self.assertIn("example.invalid", rendered)
        response_value = HttpResponse(
            status_code=200,
            headers={"set-cookie": "sensitive-response-value"},
            body=b"sensitive response body",
        )
        response_repr = repr(response_value)
        self.assertNotIn("sensitive-response", response_repr)
        self.assertNotIn("sensitive response", response_repr)

    def test_adapter_rejects_claiming_unimplemented_capability(self) -> None:
        with self.assertRaises(ValueError):
            OpenAIResponsesProvider(
                model="test-model",
                credential=StaticCredential(),
                supported=frozenset({Capability.TEXT, Capability.STREAMING}),
            )


class OpenAIAdapterTests(unittest.TestCase):
    def test_text_request_disables_storage_and_maps_usage(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "id": "resp_1",
                    "model": "test-model-2026",
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "answer"}],
                        }
                    ],
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 4,
                        "input_tokens_details": {"cached_tokens": 3},
                        "output_tokens_details": {"reasoning_tokens": 2},
                    },
                },
            )
        )
        credential = StaticCredential()
        provider = OpenAIResponsesProvider(
            model="test-model",
            credential=credential,
            transport=transport,
        )

        result = provider.generate(text_request("test-model"))

        payload = json.loads(transport.requests[0].body)
        self.assertIs(payload["store"], False)
        self.assertEqual("Bearer super-secret-test-token", transport.requests[0].headers["Authorization"])
        self.assertNotIn(credential.secret, repr(transport.requests[0]))
        self.assertEqual("answer", result.output[0].text)
        self.assertEqual(FinishReason.COMPLETE, result.finish_reason)
        self.assertEqual(10, result.usage.input_tokens)
        self.assertEqual(3, result.usage.cached_input_tokens)
        self.assertEqual(2, result.usage.reasoning_tokens)

    def test_tool_schema_and_tool_call_are_normalized(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "id": "resp_tools",
                    "status": "completed",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_1",
                            "name": "lookup",
                            "arguments": "{\"id\":\"A-1\"}",
                        }
                    ],
                    "usage": {"input_tokens": 2, "output_tokens": 1},
                },
            )
        )
        provider = OpenAIResponsesProvider(
            model="test-model",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
        )
        request = ModelRequest(
            model="test-model",
            messages=(Message("user", (ContentBlock(kind="text", text="find A-1"),)),),
            tools=(lookup_tool(),),
            tool_choice=ToolChoice(kind="specific", name="lookup"),
        )

        result = provider.generate(request)

        payload = json.loads(transport.requests[0].body)
        self.assertEqual("function", payload["tools"][0]["type"])
        self.assertIs(payload["tools"][0]["strict"], True)
        self.assertEqual(
            {"type": "function", "name": "lookup"},
            payload["tool_choice"],
        )
        self.assertEqual(FinishReason.TOOL_CALL, result.finish_reason)
        self.assertEqual({"id": "A-1"}, result.tool_calls[0].arguments)
        self.assertEqual("client", result.tool_calls[0].executed_by)

    def test_tool_arguments_are_locally_validated_before_execution(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "id": "resp_invalid_tool",
                    "status": "completed",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_invalid",
                            "name": "lookup",
                            "arguments": "{\"id\":7}",
                        }
                    ],
                },
            )
        )
        provider = OpenAIResponsesProvider(
            model="test-model",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
        )
        request = ModelRequest(
            model="test-model",
            messages=(Message("user", (ContentBlock(kind="text", text="find"),)),),
            tools=(lookup_tool(),),
            tool_choice=ToolChoice(kind="specific", name="lookup"),
        )
        with self.assertRaises(ProviderError) as caught:
            provider.generate(request)
        self.assertEqual(ProviderErrorCategory.CONTRACT_VIOLATION, caught.exception.category)
        self.assertIn("failed local validation", str(caught.exception))

    def test_tool_result_is_sent_as_function_call_output(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "id": "resp_2",
                    "status": "completed",
                    "output": [
                        {"type": "message", "content": [{"type": "output_text", "text": "done"}]}
                    ],
                },
            )
        )
        provider = OpenAIResponsesProvider(
            model="test-model",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
        )
        request = ModelRequest(
            model="test-model",
            messages=(
                Message(
                    "assistant",
                    (
                        ContentBlock(
                            kind="tool_call",
                            data={"call_id": "call_1", "name": "lookup", "arguments": {"id": "A-1"}},
                        ),
                    ),
                ),
                Message(
                    "tool",
                    (ContentBlock(kind="tool_result", data={"call_id": "call_1", "output": {"ok": True}}),),
                ),
            ),
        )

        provider.generate(request)

        items = json.loads(transport.requests[0].body)["input"]
        self.assertEqual("function_call", items[0]["type"])
        self.assertEqual("function_call_output", items[1]["type"])
        self.assertEqual('{"ok":true}', items[1]["output"])

    def test_structured_output_is_locally_validated(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "id": "resp_bad_schema",
                    "status": "completed",
                    "output": [
                        {"type": "message", "content": [{"type": "output_text", "text": "{\"n\":\"bad\"}"}]}
                    ],
                },
            )
        )
        provider = OpenAIResponsesProvider(
            model="test-model",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.STRUCTURED_OUTPUT}),
        )
        request = ModelRequest(
            model="test-model",
            messages=(Message("user", (ContentBlock(kind="text", text="number"),)),),
            response_format=ResponseFormat(
                kind="json_schema",
                name="number",
                schema={"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]},
            ),
        )

        with self.assertRaises(ProviderError) as caught:
            provider.generate(request)
        self.assertEqual(ProviderErrorCategory.CONTRACT_VIOLATION, caught.exception.category)
        payload = json.loads(transport.requests[0].body)
        self.assertEqual("json_schema", payload["text"]["format"]["type"])

    def test_rate_limit_is_normalized_without_retry(self) -> None:
        transport = ScriptedTransport(
            response(429, {"error": {"type": "rate_limit_error", "message": "slow down"}})
        )
        provider = OpenAIResponsesProvider(
            model="test-model", credential=StaticCredential(), transport=transport
        )
        with self.assertRaises(ProviderError) as caught:
            provider.generate(text_request("test-model"))
        self.assertEqual(ProviderErrorCategory.RATE_LIMIT, caught.exception.category)
        self.assertTrue(caught.exception.retryable)
        self.assertEqual(1, len(transport.requests))

    def test_model_mismatch_fails_before_credential_resolution(self) -> None:
        credential = StaticCredential()
        transport = ScriptedTransport()
        provider = OpenAIResponsesProvider(
            model="configured", credential=credential, transport=transport
        )
        with self.assertRaises(ModelNotSupported):
            provider.generate(text_request("different"))
        self.assertEqual(0, credential.resolve_count)
        self.assertEqual([], transport.requests)


class AnthropicAdapterTests(unittest.TestCase):
    def test_system_is_hoisted_and_required_max_tokens_default_is_visible(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "id": "msg_1",
                    "model": "claude-test",
                    "content": [{"type": "text", "text": "answer"}],
                    "stop_reason": "end_turn",
                    "usage": {
                        "input_tokens": 8,
                        "output_tokens": 2,
                        "cache_read_input_tokens": 3,
                    },
                },
            )
        )
        provider = AnthropicMessagesProvider(
            model="claude-test",
            credential=StaticCredential(),
            transport=transport,
            default_max_output_tokens=777,
        )
        request = ModelRequest(
            model="claude-test",
            messages=(
                Message("system", (ContentBlock(kind="text", text="bounded researcher"),)),
                Message("user", (ContentBlock(kind="text", text="hello"),)),
            ),
        )

        result = provider.generate(request)

        payload = json.loads(transport.requests[0].body)
        self.assertEqual("bounded researcher", payload["system"])
        self.assertEqual(777, payload["max_tokens"])
        self.assertIn("applied explicit default 777", result.warnings[0])
        self.assertEqual(3, result.usage.cached_input_tokens)

    def test_tool_use_and_pause_turn_remain_distinct(self) -> None:
        tool_transport = ScriptedTransport(
            response(
                200,
                {
                    "id": "msg_tool",
                    "content": [
                        {"type": "tool_use", "id": "toolu_1", "name": "lookup", "input": {"id": "A"}}
                    ],
                    "stop_reason": "tool_use",
                    "usage": {"input_tokens": 4, "output_tokens": 2},
                },
            )
        )
        provider = AnthropicMessagesProvider(
            model="claude-test",
            credential=StaticCredential(),
            transport=tool_transport,
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
        )
        request = ModelRequest(
            model="claude-test",
            messages=(Message("user", (ContentBlock(kind="text", text="lookup"),)),),
            tools=(lookup_tool(),),
            tool_choice=ToolChoice(kind="specific", name="lookup"),
            max_output_tokens=100,
        )
        result = provider.generate(request)
        tool_choice = json.loads(tool_transport.requests[0].body)["tool_choice"]
        self.assertEqual({"type": "tool", "name": "lookup"}, tool_choice)
        self.assertEqual(FinishReason.TOOL_CALL, result.finish_reason)
        self.assertEqual("toolu_1", result.tool_calls[0].call_id)

        pause_transport = ScriptedTransport(
            response(
                200,
                {
                    "id": "msg_pause",
                    "content": [{"type": "text", "text": "partial"}],
                    "stop_reason": "pause_turn",
                    "usage": {},
                },
            )
        )
        paused = AnthropicMessagesProvider(
            model="claude-test", credential=StaticCredential(), transport=pause_transport
        ).generate(text_request("claude-test"))
        self.assertEqual(FinishReason.PAUSED, paused.finish_reason)

    def test_tool_result_is_correlated_to_tool_use(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "id": "msg_done",
                    "content": [{"type": "text", "text": "done"}],
                    "stop_reason": "end_turn",
                    "usage": {},
                },
            )
        )
        provider = AnthropicMessagesProvider(
            model="claude-test",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
        )
        request = ModelRequest(
            model="claude-test",
            messages=(
                Message(
                    "assistant",
                    (
                        ContentBlock(
                            kind="tool_call",
                            data={"call_id": "toolu_1", "name": "lookup", "arguments": {"id": "A"}},
                        ),
                    ),
                ),
                Message(
                    "tool",
                    (
                        ContentBlock(
                            kind="tool_result",
                            data={"call_id": "toolu_1", "output": {"value": 1}},
                        ),
                    ),
                ),
            ),
        )
        provider.generate(request)
        messages = json.loads(transport.requests[0].body)["messages"]
        self.assertEqual("tool_use", messages[0]["content"][0]["type"])
        self.assertEqual("toolu_1", messages[1]["content"][0]["tool_use_id"])

    def test_temperature_above_provider_range_is_rejected_before_call(self) -> None:
        transport = ScriptedTransport()
        credential = StaticCredential()
        provider = AnthropicMessagesProvider(
            model="claude-test", credential=credential, transport=transport
        )
        request = ModelRequest(
            model="claude-test",
            messages=(Message("user", (ContentBlock(kind="text", text="hello"),)),),
            temperature=1.5,
        )
        with self.assertRaises(ProviderError) as caught:
            provider.generate(request)
        self.assertEqual(ProviderErrorCategory.INVALID_REQUEST, caught.exception.category)
        self.assertEqual(0, credential.resolve_count)

    def test_structured_output_uses_output_config_and_local_validation(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "id": "msg_structured",
                    "content": [{"type": "text", "text": "{\"answer\":7}"}],
                    "stop_reason": "end_turn",
                    "usage": {},
                },
            )
        )
        provider = AnthropicMessagesProvider(
            model="claude-test",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.STRUCTURED_OUTPUT}),
        )
        request = ModelRequest(
            model="claude-test",
            messages=(Message("user", (ContentBlock(kind="text", text="number"),)),),
            response_format=ResponseFormat(
                kind="json_schema",
                name="answer",
                schema={
                    "type": "object",
                    "properties": {"answer": {"type": "integer"}},
                    "required": ["answer"],
                },
            ),
        )
        result = provider.generate(request)
        payload = json.loads(transport.requests[0].body)
        self.assertEqual("json_schema", payload["output_config"]["format"]["type"])
        self.assertEqual(FinishReason.COMPLETE, result.finish_reason)


class GeminiAdapterTests(unittest.TestCase):
    def test_text_request_maps_system_usage_and_stop(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "responseId": "gem_1",
                    "modelVersion": "gemini-test-001",
                    "candidates": [
                        {
                            "content": {"role": "model", "parts": [{"text": "answer"}]},
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 7,
                        "candidatesTokenCount": 2,
                        "cachedContentTokenCount": 1,
                    },
                },
            )
        )
        provider = GeminiGenerateContentProvider(
            model="gemini-test", credential=StaticCredential(), transport=transport
        )
        request = ModelRequest(
            model="gemini-test",
            messages=(
                Message("developer", (ContentBlock(kind="text", text="bounded researcher"),)),
                Message("user", (ContentBlock(kind="text", text="hello"),)),
            ),
        )
        result = provider.generate(request)
        payload = json.loads(transport.requests[0].body)
        self.assertEqual("bounded researcher", payload["systemInstruction"]["parts"][0]["text"])
        self.assertTrue(transport.requests[0].url.endswith("/models/gemini-test:generateContent"))
        self.assertEqual(FinishReason.COMPLETE, result.finish_reason)
        self.assertEqual(1, result.usage.cached_input_tokens)

    def test_parallel_function_calls_and_missing_ids_are_explicit(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "responseId": "gem_tools",
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"functionCall": {"name": "lookup", "args": {"id": "A"}}},
                                    {"functionCall": {"id": "call_b", "name": "lookup", "args": {"id": "B"}}},
                                ]
                            },
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {},
                },
            )
        )
        provider = GeminiGenerateContentProvider(
            model="gemini-test",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.TOOLS, Capability.PARALLEL_TOOLS}),
        )
        request = ModelRequest(
            model="gemini-test",
            messages=(Message("user", (ContentBlock(kind="text", text="find A and B"),)),),
            tools=(lookup_tool(),),
            tool_choice=ToolChoice(kind="specific", name="lookup"),
            capability_requirements=frozenset({Capability.PARALLEL_TOOLS}),
        )
        result = provider.generate(request)
        payload = json.loads(transport.requests[0].body)
        declaration = payload["tools"][0]["functionDeclarations"][0]
        self.assertIn("parametersJsonSchema", declaration)
        self.assertEqual(
            {"mode": "ANY", "allowedFunctionNames": ["lookup"]},
            payload["toolConfig"]["functionCallingConfig"],
        )
        self.assertEqual(FinishReason.TOOL_CALL, result.finish_reason)
        self.assertEqual(2, len(result.tool_calls))
        self.assertEqual("gemini-gem_tools-0", result.tool_calls[0].call_id)
        self.assertIn("synthesized", result.warnings[0])

    def test_parallel_response_is_contract_violation_when_not_claimed(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "responseId": "gem_bad_parallel",
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"functionCall": {"name": "lookup", "args": {}}},
                                    {"functionCall": {"name": "lookup", "args": {}}},
                                ]
                            },
                            "finishReason": "STOP",
                        }
                    ],
                },
            )
        )
        provider = GeminiGenerateContentProvider(
            model="gemini-test",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
        )
        request = ModelRequest(
            model="gemini-test",
            messages=(Message("user", (ContentBlock(kind="text", text="find"),)),),
            tools=(lookup_tool(),),
        )
        with self.assertRaises(ProviderError) as caught:
            provider.generate(request)
        self.assertEqual(ProviderErrorCategory.CONTRACT_VIOLATION, caught.exception.category)

    def test_function_result_uses_prior_call_name(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "responseId": "gem_done",
                    "candidates": [
                        {"content": {"parts": [{"text": "done"}]}, "finishReason": "STOP"}
                    ],
                },
            )
        )
        provider = GeminiGenerateContentProvider(
            model="gemini-test",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
        )
        request = ModelRequest(
            model="gemini-test",
            messages=(
                Message(
                    "assistant",
                    (
                        ContentBlock(
                            kind="tool_call",
                            data={"call_id": "call_a", "name": "lookup", "arguments": {"id": "A"}},
                        ),
                    ),
                ),
                Message(
                    "tool",
                    (ContentBlock(kind="tool_result", data={"call_id": "call_a", "output": {"value": 1}}),),
                ),
            ),
        )
        provider.generate(request)
        contents = json.loads(transport.requests[0].body)["contents"]
        function_response = contents[1]["parts"][0]["functionResponse"]
        self.assertEqual("lookup", function_response["name"])
        self.assertEqual({"value": 1}, function_response["response"])

    def test_prompt_block_is_mapped_to_refusal(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "responseId": "gem_blocked",
                    "candidates": [],
                    "promptFeedback": {"blockReason": "SAFETY"},
                    "usageMetadata": {"promptTokenCount": 3},
                },
            )
        )
        provider = GeminiGenerateContentProvider(
            model="gemini-test", credential=StaticCredential(), transport=transport
        )
        result = provider.generate(text_request("gemini-test"))
        self.assertEqual(FinishReason.REFUSAL, result.finish_reason)

    def test_specific_tool_choice_must_name_a_declared_tool_before_call(self) -> None:
        transport = ScriptedTransport()
        credential = StaticCredential()
        provider = GeminiGenerateContentProvider(
            model="gemini-test",
            credential=credential,
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
        )
        request = ModelRequest(
            model="gemini-test",
            messages=(Message("user", (ContentBlock(kind="text", text="find"),)),),
            tools=(lookup_tool(),),
            tool_choice=ToolChoice(kind="specific", name="missing"),
        )
        with self.assertRaises(ProviderError) as caught:
            provider.generate(request)
        self.assertEqual(ProviderErrorCategory.INVALID_REQUEST, caught.exception.category)
        self.assertEqual(0, credential.resolve_count)
        self.assertEqual([], transport.requests)

    def test_resource_exhausted_is_normalized_as_rate_limit(self) -> None:
        transport = ScriptedTransport(
            response(
                429,
                {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota"}},
            )
        )
        provider = GeminiGenerateContentProvider(
            model="gemini-test", credential=StaticCredential(), transport=transport
        )
        with self.assertRaises(ProviderError) as caught:
            provider.generate(text_request("gemini-test"))
        self.assertEqual(ProviderErrorCategory.RATE_LIMIT, caught.exception.category)
        self.assertTrue(caught.exception.retryable)

    def test_structured_output_uses_generation_config_and_local_validation(self) -> None:
        transport = ScriptedTransport(
            response(
                200,
                {
                    "responseId": "gem_structured",
                    "candidates": [
                        {
                            "content": {"parts": [{"text": "{\"answer\":7}"}]},
                            "finishReason": "STOP",
                        }
                    ],
                },
            )
        )
        provider = GeminiGenerateContentProvider(
            model="gemini-test",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.STRUCTURED_OUTPUT}),
        )
        request = ModelRequest(
            model="gemini-test",
            messages=(Message("user", (ContentBlock(kind="text", text="number"),)),),
            response_format=ResponseFormat(
                kind="json_schema",
                name="answer",
                schema={
                    "type": "object",
                    "properties": {"answer": {"type": "integer"}},
                    "required": ["answer"],
                },
            ),
        )
        result = provider.generate(request)
        generation = json.loads(transport.requests[0].body)["generationConfig"]
        self.assertEqual("application/json", generation["responseMimeType"])
        self.assertEqual("object", generation["responseJsonSchema"]["type"])
        self.assertEqual(FinishReason.COMPLETE, result.finish_reason)


if __name__ == "__main__":
    unittest.main()
