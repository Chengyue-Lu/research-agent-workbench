import json
import unittest
from dataclasses import dataclass, replace

from research_workbench.adapters.models.conformance import run_provider_conformance
from research_workbench.adapters.models.http import HttpRequest, HttpResponse
from research_workbench.adapters.models.port import (
    Capability,
    CapabilityGap,
    ContentBlock,
    FinishReason,
    Message,
    ModelNotSupported,
    ModelRequest,
    ProviderError,
    ProviderErrorCategory,
    ProviderRegistry,
    ResponseFormat,
    ToolChoice,
    ToolDefinition,
)
from research_workbench.adapters.models.session import (
    ApiSessionLimits,
    ApiSessionStatus,
    ClientTool,
    IsolatedApiSessionRunner,
)
from research_workbench.adapters.models.zhipu_chat import (
    ZhipuChatCompletionsProvider,
)
from research_workbench.validation import SchemaCatalog


@dataclass
class StaticCredential:
    secret: str = "zhipu-test-secret"
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


def chat_response(
    content: str | None,
    *,
    model: str = "glm-5.3",
    finish_reason: str = "stop",
    message_extra: dict | None = None,
) -> HttpResponse:
    message = {"role": "assistant", "content": content}
    message.update(message_extra or {})
    return response(
        200,
        {
            "id": "zhipu-response-1",
            "created": 1_786_900_000,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 4,
                "total_tokens": 16,
                "prompt_tokens_details": {"cached_tokens": 3},
            },
        },
    )


def tool_response(
    *,
    call_id: str = "call-1",
    name: str = "lookup",
    arguments: str = '{"record_id":"R-1"}',
    reasoning_content: object = "private-reasoning-turn",
    tool_calls: list[dict[str, object]] | None = None,
) -> HttpResponse:
    calls = tool_calls
    if calls is None:
        calls = [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
        ]
    return chat_response(
        None,
        finish_reason="tool_calls",
        message_extra={
            "reasoning_content": reasoning_content,
            "tool_calls": calls,
        },
    )


def text_request(**changes) -> ModelRequest:
    values = {
        "model": "glm-5.3",
        "messages": (Message("user", (ContentBlock(kind="text", text="hello"),)),),
    }
    values.update(changes)
    return ModelRequest(**values)


def lookup_tool() -> ToolDefinition:
    return ToolDefinition(
        name="lookup",
        description="Read one bounded record",
        input_schema={
            "type": "object",
            "properties": {"record_id": {"type": "string"}},
            "required": ["record_id"],
            "additionalProperties": False,
        },
    )


ZHIPU_TOOL_CAPABILITIES = frozenset(
    {
        Capability.TEXT,
        Capability.TOOLS,
        Capability.STRUCTURED_OUTPUT,
        Capability.REASONING,
    }
)


def append_tool_result(
    request: ModelRequest,
    *,
    call_id: str = "call-1",
    name: str = "lookup",
    arguments: dict[str, object] | None = None,
    output: object = None,
    is_error: bool = False,
    result_data: dict[str, object] | None = None,
) -> ModelRequest:
    assistant = Message(
        "assistant",
        (
            ContentBlock(
                kind="tool_call",
                data={
                    "call_id": call_id,
                    "name": name,
                    "arguments": (
                        {"record_id": "R-1"} if arguments is None else arguments
                    ),
                },
            ),
        ),
    )
    data = (
        {
            "call_id": call_id,
            "name": name,
            "output": (
                {"record_id": "R-1", "value": 7} if output is None else output
            ),
            "is_error": is_error,
        }
        if result_data is None
        else result_data
    )
    result = Message("tool", (ContentBlock(kind="tool_result", data=data),))
    return replace(request, messages=(*request.messages, assistant, result))


class ZhipuChatCompletionsProviderTests(unittest.TestCase):
    def test_capabilities_are_conservative_and_zero_retry_is_explicit(self) -> None:
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
        )

        snapshot = provider.capabilities()

        self.assertEqual("zhipu", snapshot.provider)
        self.assertEqual(frozenset({Capability.TEXT}), snapshot.supported)
        self.assertNotIn(Capability.TOOLS, snapshot.supported)
        self.assertNotIn(Capability.REASONING, snapshot.supported)
        self.assertEqual(0, snapshot.limits["max_retries"])
        self.assertEqual("low", snapshot.limits["default_reasoning_effort"])
        self.assertEqual("auto-only", snapshot.limits["tool_choice"])
        self.assertEqual("single-active-attempt", snapshot.limits["session_scope"])
        with self.assertRaisesRegex(ValueError, "max_retries=0"):
            ZhipuChatCompletionsProvider(
                model="glm-5.3",
                credential=StaticCredential(),
                max_retries=1,
            )
        with self.assertRaisesRegex(ValueError, "standard API base URL"):
            ZhipuChatCompletionsProvider(
                model="glm-5.3",
                credential=StaticCredential(),
                base_url="https://open.bigmodel.cn/api/coding/paas/v4",
            )

    def test_text_request_uses_standard_endpoint_and_maps_usage(self) -> None:
        transport = ScriptedTransport(chat_response("answer"))
        credential = StaticCredential()
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=credential,
            transport=transport,
        )

        result = provider.generate(text_request(max_output_tokens=64, temperature=0.5))

        outbound = transport.requests[0]
        payload = json.loads(outbound.body)
        self.assertEqual(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            outbound.url,
        )
        self.assertEqual("Bearer zhipu-test-secret", outbound.headers["Authorization"])
        self.assertNotIn(credential.secret, repr(outbound))
        self.assertEqual("glm-5.3", payload["model"])
        self.assertEqual(
            [{"role": "user", "content": "hello"}],
            payload["messages"],
        )
        self.assertEqual(64, payload["max_tokens"])
        self.assertEqual(0.5, payload["temperature"])
        self.assertIs(payload["stream"], False)
        self.assertNotIn("tools", payload)
        self.assertEqual(
            {"type": "enabled", "clear_thinking": False}, payload["thinking"]
        )
        self.assertEqual("low", payload["reasoning_effort"])
        self.assertEqual("zhipu", result.provider)
        self.assertEqual("glm-5.3", result.model)
        self.assertEqual("answer", result.output[0].text)
        self.assertEqual(FinishReason.COMPLETE, result.finish_reason)
        self.assertEqual(12, result.usage.input_tokens)
        self.assertEqual(4, result.usage.output_tokens)
        self.assertEqual(3, result.usage.cached_input_tokens)
        self.assertIsNone(result.usage.provider_reported_cost)
        self.assertIsNone(result.usage.currency)
        self.assertEqual(16, result.provider_metadata["reported_total_tokens"])
        self.assertEqual(1, credential.resolve_count)

    def test_canonical_metadata_remains_local_and_is_not_transmitted(self) -> None:
        transport = ScriptedTransport(chat_response("answer"))
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=transport,
        )

        result = provider.generate(
            text_request(
                metadata={
                    "task_id": "TASK-GLM-001",
                    "execution_contract_id": "evidence-h2",
                }
            )
        )

        payload = json.loads(transport.requests[0].body)
        serialized = json.dumps(payload)
        self.assertNotIn("metadata", payload)
        self.assertNotIn("TASK-GLM-001", serialized)
        self.assertNotIn("evidence-h2", serialized)
        self.assertIn("remained local", result.warnings[0])

    def test_json_schema_uses_json_object_and_is_validated_locally(self) -> None:
        transport = ScriptedTransport(chat_response('{"n":7}'))
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.STRUCTURED_OUTPUT}),
        )
        request = text_request(
            response_format=ResponseFormat(
                kind="json_schema",
                name="number",
                schema={
                    "type": "object",
                    "properties": {"n": {"type": "integer"}},
                    "required": ["n"],
                    "additionalProperties": False,
                },
            )
        )

        result = provider.generate(request)

        payload = json.loads(transport.requests[0].body)
        self.assertEqual({"type": "json_object"}, payload["response_format"])
        self.assertNotIn("schema", payload["response_format"])
        self.assertEqual("system", payload["messages"][0]["role"])
        self.assertIn('"n":{"type":"integer"}', payload["messages"][0]["content"])
        self.assertIn(
            "Return exactly one JSON object", payload["messages"][0]["content"]
        )
        self.assertIn("validated locally", result.warnings[-1])

    def test_schema_violation_is_rejected_after_one_request(self) -> None:
        transport = ScriptedTransport(chat_response('{"n":"wrong"}'))
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.STRUCTURED_OUTPUT}),
        )
        request = text_request(
            response_format=ResponseFormat(
                kind="json_schema",
                name="number",
                schema={
                    "type": "object",
                    "properties": {"n": {"type": "integer"}},
                    "required": ["n"],
                },
            )
        )

        with self.assertRaises(ProviderError) as caught:
            provider.generate(request)

        self.assertEqual(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            caught.exception.category,
        )
        self.assertIn("failed local validation", str(caught.exception))
        self.assertEqual(1, len(transport.requests))

    def test_oversized_schema_instruction_is_blocked_before_secret_resolution(
        self,
    ) -> None:
        credential = StaticCredential()
        transport = ScriptedTransport()
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=credential,
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.STRUCTURED_OUTPUT}),
        )
        request = text_request(
            response_format=ResponseFormat(
                kind="json_schema",
                name="oversized",
                schema={"type": "object", "description": "界" * 6_000},
            )
        )

        with self.assertRaises(ProviderError) as caught:
            provider.generate(request)

        self.assertEqual(
            ProviderErrorCategory.INVALID_REQUEST, caught.exception.category
        )
        self.assertIn("bounded size", str(caught.exception))
        self.assertEqual(0, credential.resolve_count)
        self.assertEqual([], transport.requests)

    def test_response_model_mismatch_is_never_accepted_as_fallback(self) -> None:
        transport = ScriptedTransport(chat_response("answer", model="glm-5.2"))
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=transport,
        )

        with self.assertRaises(ProviderError) as caught:
            provider.generate(text_request())

        self.assertEqual(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            caught.exception.category,
        )
        self.assertIn("exact request", str(caught.exception))

    def test_request_model_mismatch_fails_before_secret_resolution(self) -> None:
        credential = StaticCredential()
        transport = ScriptedTransport()
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=credential,
            transport=transport,
        )

        with self.assertRaises(ModelNotSupported):
            provider.generate(text_request(model="glm-5.2"))

        self.assertEqual(0, credential.resolve_count)
        self.assertEqual([], transport.requests)

    def test_tools_and_reasoning_are_rejected_before_secret_resolution(self) -> None:
        tool = lookup_tool()
        for request in (
            text_request(tools=(tool,)),
            text_request(reasoning_effort="high"),
        ):
            with self.subTest(request=request):
                credential = StaticCredential()
                transport = ScriptedTransport()
                provider = ZhipuChatCompletionsProvider(
                    model="glm-5.3",
                    credential=credential,
                    transport=transport,
                )

                with self.assertRaises(CapabilityGap):
                    provider.generate(request)

                self.assertEqual(0, credential.resolve_count)
                self.assertEqual([], transport.requests)

    def test_tool_round_trip_replays_private_reasoning_and_clears_on_terminal(
        self,
    ) -> None:
        hidden = "private reasoning\nwith unicode 界 and exact spacing"
        raw_arguments = '{ "record_id" : "R-1" }'
        transport = ScriptedTransport(
            tool_response(arguments=raw_arguments, reasoning_content=hidden),
            chat_response('{"status":"complete"}'),
            chat_response("fresh attempt"),
        )
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=transport,
            supported=ZHIPU_TOOL_CAPABILITIES,
        )
        request = text_request(
            tools=(lookup_tool(),),
            reasoning_effort="high",
        )

        first = provider.generate(request)

        self.assertEqual(FinishReason.TOOL_CALL, first.finish_reason)
        self.assertEqual((), first.output)
        self.assertEqual(1, len(first.tool_calls))
        self.assertEqual("call-1", first.tool_calls[0].call_id)
        self.assertEqual("lookup", first.tool_calls[0].name)
        self.assertEqual({"record_id": "R-1"}, first.tool_calls[0].arguments)
        self.assertNotIn(hidden, repr(first))
        self.assertNotIn(hidden, repr(provider))
        self.assertNotIn(hidden, json.dumps(first.warnings))
        self.assertNotIn(hidden, json.dumps(first.provider_metadata))

        second = provider.generate(append_tool_result(request))

        first_payload = json.loads(transport.requests[0].body)
        second_payload = json.loads(transport.requests[1].body)
        self.assertEqual("auto", first_payload["tool_choice"])
        self.assertEqual("high", first_payload["reasoning_effort"])
        self.assertEqual(
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "description": "Read one bounded record",
                    "parameters": lookup_tool().input_schema,
                },
            },
            first_payload["tools"][0],
        )
        self.assertEqual(["user", "assistant", "tool"], [
            message["role"] for message in second_payload["messages"]
        ])
        assistant = second_payload["messages"][1]
        self.assertEqual(hidden, assistant["reasoning_content"])
        self.assertEqual(raw_arguments, assistant["tool_calls"][0]["function"]["arguments"])
        self.assertEqual("call-1", assistant["tool_calls"][0]["id"])
        tool_result = second_payload["messages"][2]
        self.assertEqual("call-1", tool_result["tool_call_id"])
        self.assertEqual(
            '{"record_id":"R-1","value":7}', tool_result["content"]
        )
        self.assertEqual(FinishReason.COMPLETE, second.finish_reason)
        self.assertIsNone(second.usage.provider_reported_cost)
        self.assertNotIn(hidden, repr(second))
        self.assertIn("continuation_active=False", repr(provider))

        fresh = provider.generate(text_request())
        self.assertEqual("fresh attempt", fresh.output[0].text)
        self.assertNotIn(hidden, transport.requests[2].body.decode("utf-8"))

    def test_shared_isolated_runner_executes_zhipu_client_tool_without_port_changes(
        self,
    ) -> None:
        transport = ScriptedTransport(
            tool_response(reasoning_content="runner-private-reasoning"),
            chat_response("done"),
        )
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=transport,
            supported=ZHIPU_TOOL_CAPABILITIES,
        )
        registry = ProviderRegistry()
        registry.register("zhipu-chat-completions", provider)
        executed: list[str] = []
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(
                ClientTool(
                    lookup_tool(),
                    lambda arguments: executed.append(str(arguments["record_id"]))
                    or {"record_id": arguments["record_id"], "value": 7},
                ),
            ),
        )

        result = runner.run(
            adapter_id="zhipu-chat-completions",
            request=text_request(tools=(lookup_tool(),)),
            limits=ApiSessionLimits(
                max_model_turns=3,
                max_tool_calls=2,
                max_parallel_tool_calls=1,
                max_tool_result_chars=512,
                max_output_tokens_per_turn=64,
                max_seconds=30,
                max_total_tokens=100,
            ),
            expected_capabilities=provider.capabilities(),
        )

        self.assertEqual(ApiSessionStatus.COMPLETED, result.status)
        self.assertEqual(["R-1"], executed)
        self.assertEqual(2, result.model_turns)
        self.assertEqual(1, result.tool_calls)
        self.assertIn("continuation_active=False", repr(provider))

    def test_two_tool_turns_replay_the_full_private_chain_in_order(self) -> None:
        first_hidden = "private reasoning turn one"
        second_hidden = "private reasoning turn two"
        transport = ScriptedTransport(
            tool_response(reasoning_content=first_hidden),
            tool_response(
                call_id="call-2",
                arguments='{ "record_id" : "R-2" }',
                reasoning_content=second_hidden,
            ),
            chat_response("done"),
        )
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=transport,
            supported=ZHIPU_TOOL_CAPABILITIES,
        )
        initial = text_request(tools=(lookup_tool(),))
        first_result = append_tool_result(initial)

        provider.generate(initial)
        provider.generate(first_result)
        terminal = provider.generate(
            append_tool_result(
                first_result,
                call_id="call-2",
                arguments={"record_id": "R-2"},
                output={"record_id": "R-2", "value": 9},
            )
        )

        payload = json.loads(transport.requests[2].body)
        assistants = [
            message
            for message in payload["messages"]
            if message["role"] == "assistant"
        ]
        self.assertEqual(
            [first_hidden, second_hidden],
            [message["reasoning_content"] for message in assistants],
        )
        self.assertEqual(
            ["call-1", "call-2"],
            [message["tool_calls"][0]["id"] for message in assistants],
        )
        self.assertEqual(FinishReason.COMPLETE, terminal.finish_reason)
        self.assertIn("continuation_active=False", repr(provider))
        self.assertNotIn(first_hidden, repr(terminal) + repr(provider))
        self.assertNotIn(second_hidden, repr(terminal) + repr(provider))

    def test_shared_runner_cost_ceiling_fails_closed_before_tool_execution(self) -> None:
        hidden = "cost-private-reasoning"
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=ScriptedTransport(
                tool_response(reasoning_content=hidden)
            ),
            supported=ZHIPU_TOOL_CAPABILITIES,
        )
        registry = ProviderRegistry()
        registry.register("zhipu-chat-completions", provider)
        executed: list[str] = []
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(
                ClientTool(
                    lookup_tool(),
                    lambda arguments: executed.append(str(arguments["record_id"])),
                ),
            ),
        )

        try:
            result = runner.run(
                adapter_id="zhipu-chat-completions",
                request=text_request(tools=(lookup_tool(),)),
                limits=ApiSessionLimits(
                    max_model_turns=3,
                    max_tool_calls=2,
                    max_parallel_tool_calls=1,
                    max_tool_result_chars=512,
                    max_output_tokens_per_turn=64,
                    max_seconds=30,
                    max_total_tokens=100,
                    max_provider_reported_cost=0.5,
                ),
                expected_capabilities=provider.capabilities(),
            )
            self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
            self.assertEqual("cost-usage-unavailable", result.stop_reason)
            self.assertEqual([], executed)
            self.assertIn("continuation_active=True", repr(provider))
            self.assertNotIn(hidden, repr(result) + repr(provider))
        finally:
            provider.discard_ephemeral_continuation()
        self.assertIn("continuation_active=False", repr(provider))

    def test_continuation_rejects_identity_transcript_and_result_drift_offline(
        self,
    ) -> None:
        cases = (
            ("assistant-call-id", {"call_id": "wrong"}, None),
            ("assistant-name", {"name": "other"}, None),
            ("assistant-arguments", {"arguments": {"record_id": "R-2"}}, None),
            (
                "result-call-id",
                {},
                {
                    "call_id": "wrong",
                    "name": "lookup",
                    "output": {"value": 7},
                    "is_error": False,
                },
            ),
            (
                "result-incomplete",
                {},
                {"call_id": "call-1", "output": {"value": 7}},
            ),
            (
                "result-extra-field",
                {},
                {
                    "call_id": "call-1",
                    "name": "lookup",
                    "output": {"value": 7},
                    "is_error": False,
                    "extra": "not-allowed",
                },
            ),
        )
        for label, assistant_changes, result_data in cases:
            with self.subTest(label=label):
                credential = StaticCredential()
                transport = ScriptedTransport(tool_response())
                provider = ZhipuChatCompletionsProvider(
                    model="glm-5.3",
                    credential=credential,
                    transport=transport,
                    supported=ZHIPU_TOOL_CAPABILITIES,
                )
                request = text_request(tools=(lookup_tool(),))
                provider.generate(request)
                continued = append_tool_result(
                    request,
                    call_id=str(assistant_changes.get("call_id", "call-1")),
                    name=str(assistant_changes.get("name", "lookup")),
                    arguments=assistant_changes.get(
                        "arguments", {"record_id": "R-1"}
                    ),
                    result_data=result_data,
                )

                with self.assertRaises(ProviderError) as caught:
                    provider.generate(continued)

                self.assertEqual(
                    ProviderErrorCategory.CONTRACT_VIOLATION,
                    caught.exception.category,
                )
                self.assertEqual(1, credential.resolve_count)
                self.assertEqual(1, len(transport.requests))
                self.assertIn("continuation_active=False", repr(provider))

    def test_discard_blocks_late_result_and_new_initial_request_cannot_interleave(
        self,
    ) -> None:
        hidden = "discard-only-private-reasoning"
        request = text_request(tools=(lookup_tool(),))

        for action in ("discard", "interleave"):
            with self.subTest(action=action):
                credential = StaticCredential()
                transport = ScriptedTransport(
                    tool_response(reasoning_content=hidden)
                )
                provider = ZhipuChatCompletionsProvider(
                    model="glm-5.3",
                    credential=credential,
                    transport=transport,
                    supported=ZHIPU_TOOL_CAPABILITIES,
                )
                provider.generate(request)
                if action == "discard":
                    provider.discard_ephemeral_continuation()
                    next_request = append_tool_result(request)
                else:
                    next_request = request

                with self.assertRaises(ProviderError) as caught:
                    provider.generate(next_request)

                self.assertEqual(
                    ProviderErrorCategory.CONTRACT_VIOLATION,
                    caught.exception.category,
                )
                self.assertEqual(1, credential.resolve_count)
                self.assertEqual(1, len(transport.requests))
                self.assertNotIn(hidden, repr(provider))
                self.assertIn("continuation_active=False", repr(provider))

    def test_malformed_tool_responses_are_rejected_and_private_state_is_purged(
        self,
    ) -> None:
        hidden = "malformed-response-private-reasoning"
        function_call = {
            "id": "call-1",
            "type": "function",
            "function": {
                "name": "lookup",
                "arguments": '{"record_id":"R-1"}',
            },
        }
        cases = (
            ("missing-reasoning", tool_response(reasoning_content=None)),
            (
                "parallel-calls",
                tool_response(
                    reasoning_content=hidden,
                    tool_calls=[function_call, {**function_call, "id": "call-2"}],
                ),
            ),
            (
                "mcp-call",
                tool_response(
                    reasoning_content=hidden,
                    tool_calls=[
                        {"id": "call-1", "type": "mcp", "mcp": {"name": "search"}}
                    ],
                ),
            ),
            (
                "non-json-arguments",
                tool_response(arguments="{not-json", reasoning_content=hidden),
            ),
            (
                "non-object-arguments",
                tool_response(arguments='["R-1"]', reasoning_content=hidden),
            ),
        )
        for label, provider_response in cases:
            with self.subTest(label=label):
                provider = ZhipuChatCompletionsProvider(
                    model="glm-5.3",
                    credential=StaticCredential(),
                    transport=ScriptedTransport(provider_response),
                    supported=ZHIPU_TOOL_CAPABILITIES,
                )

                with self.assertRaises(ProviderError) as caught:
                    provider.generate(text_request(tools=(lookup_tool(),)))

                self.assertEqual(
                    ProviderErrorCategory.CONTRACT_VIOLATION,
                    caught.exception.category,
                )
                self.assertNotIn(hidden, str(caught.exception))
                self.assertNotIn(hidden, repr(provider))
                self.assertIn("continuation_active=False", repr(provider))

    def test_private_continuation_byte_and_turn_caps_fail_closed(self) -> None:
        hidden = "private-size-canary-" * 20
        byte_transport = ScriptedTransport(
            tool_response(reasoning_content=hidden)
        )
        byte_provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=byte_transport,
            supported=ZHIPU_TOOL_CAPABILITIES,
            max_continuation_bytes=64,
        )

        with self.assertRaises(ProviderError) as byte_error:
            byte_provider.generate(text_request(tools=(lookup_tool(),)))

        self.assertIn("private-memory size", str(byte_error.exception))
        self.assertNotIn(hidden, str(byte_error.exception))
        self.assertIn("continuation_active=False", repr(byte_provider))

        turn_transport = ScriptedTransport(
            tool_response(reasoning_content="turn-one"),
            tool_response(
                call_id="call-2",
                arguments='{"record_id":"R-2"}',
                reasoning_content="turn-two",
            ),
        )
        turn_provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=turn_transport,
            supported=ZHIPU_TOOL_CAPABILITIES,
            max_continuation_turns=1,
        )
        request = text_request(tools=(lookup_tool(),))
        turn_provider.generate(request)

        with self.assertRaises(ProviderError) as turn_error:
            turn_provider.generate(append_tool_result(request))

        self.assertIn("tool-turn count", str(turn_error.exception))
        self.assertEqual(2, len(turn_transport.requests))
        self.assertIn("continuation_active=False", repr(turn_provider))

    def test_only_auto_tool_choice_and_glm_reasoning_efforts_are_accepted(
        self,
    ) -> None:
        for choice in (
            ToolChoice(kind="none"),
            ToolChoice(kind="required"),
            ToolChoice(kind="specific", name="lookup"),
        ):
            with self.subTest(choice=choice.kind):
                credential = StaticCredential()
                provider = ZhipuChatCompletionsProvider(
                    model="glm-5.3",
                    credential=credential,
                    transport=ScriptedTransport(),
                    supported=ZHIPU_TOOL_CAPABILITIES,
                )
                with self.assertRaises(ProviderError) as caught:
                    provider.generate(
                        text_request(tools=(lookup_tool(),), tool_choice=choice)
                    )
                self.assertEqual(
                    ProviderErrorCategory.UNSUPPORTED,
                    caught.exception.category,
                )
                self.assertEqual(0, credential.resolve_count)

        for effort in ("low", "high", "max"):
            with self.subTest(effort=effort):
                transport = ScriptedTransport(chat_response("answer"))
                provider = ZhipuChatCompletionsProvider(
                    model="glm-5.3",
                    credential=StaticCredential(),
                    transport=transport,
                    supported=ZHIPU_TOOL_CAPABILITIES,
                )
                provider.generate(text_request(reasoning_effort=effort))
                payload = json.loads(transport.requests[0].body)
                self.assertEqual(effort, payload["reasoning_effort"])
                self.assertEqual(
                    {"type": "enabled", "clear_thinking": False},
                    payload["thinking"],
                )

        credential = StaticCredential()
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=credential,
            transport=ScriptedTransport(),
            supported=ZHIPU_TOOL_CAPABILITIES,
        )
        with self.assertRaises(ProviderError) as caught:
            provider.generate(text_request(reasoning_effort="medium"))
        self.assertEqual(
            ProviderErrorCategory.INVALID_REQUEST,
            caught.exception.category,
        )
        self.assertEqual(0, credential.resolve_count)

    def test_reasoning_content_is_omitted_without_leaking_it(self) -> None:
        hidden = "private chain of thought"
        transport = ScriptedTransport(
            chat_response(
                "answer",
                message_extra={"reasoning_content": hidden},
            )
        )
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=transport,
        )

        result = provider.generate(text_request())

        rendered = repr(result) + repr(provider)
        self.assertNotIn(hidden, rendered)
        self.assertNotIn(hidden, json.dumps(result.provider_metadata))
        self.assertNotIn(hidden, json.dumps(result.warnings))
        self.assertNotIn("reasoning_content", result.provider_metadata)

    def test_retryable_api_error_is_reported_without_automatic_retry(self) -> None:
        transport = ScriptedTransport(
            response(429, {"error": {"code": "1302", "message": "slow down"}})
        )
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=transport,
        )

        with self.assertRaises(ProviderError) as caught:
            provider.generate(text_request())

        self.assertEqual(ProviderErrorCategory.RATE_LIMIT, caught.exception.category)
        self.assertTrue(caught.exception.retryable)
        self.assertEqual("1302", caught.exception.provider_code)
        self.assertEqual(1, len(transport.requests))

    def test_business_error_codes_preserve_context_safety_and_quota_meaning(
        self,
    ) -> None:
        cases = (
            (1120, ProviderErrorCategory.TRANSIENT, True),
            (1211, ProviderErrorCategory.UNSUPPORTED, False),
            (1261, ProviderErrorCategory.CONTEXT_LIMIT, False),
            (1301, ProviderErrorCategory.SAFETY_REFUSAL, False),
            (1304, ProviderErrorCategory.RATE_LIMIT, False),
            (1305, ProviderErrorCategory.TRANSIENT, True),
            (1309, ProviderErrorCategory.PERMISSION, False),
            (1311, ProviderErrorCategory.PERMISSION, False),
        )
        for code, category, retryable in cases:
            with self.subTest(code=code):
                transport = ScriptedTransport(
                    response(400, {"error": {"code": code, "message": "redacted"}})
                )
                provider = ZhipuChatCompletionsProvider(
                    model="glm-5.3",
                    credential=StaticCredential(),
                    transport=transport,
                )

                with self.assertRaises(ProviderError) as caught:
                    provider.generate(text_request())

                self.assertEqual(category, caught.exception.category)
                self.assertIs(retryable, caught.exception.retryable)
                self.assertEqual(str(code), caught.exception.provider_code)
                self.assertEqual(1, len(transport.requests))

    def test_sampling_controls_fail_before_secret_resolution(self) -> None:
        invalid_requests = (
            text_request(max_output_tokens=True),
            text_request(max_output_tokens=1.5),
            text_request(max_output_tokens=131_073),
            text_request(temperature=True),
            text_request(temperature=0.123),
            text_request(temperature=1.01),
        )
        for request in invalid_requests:
            with self.subTest(request=request):
                credential = StaticCredential()
                transport = ScriptedTransport()
                provider = ZhipuChatCompletionsProvider(
                    model="glm-5.3",
                    credential=credential,
                    transport=transport,
                )

                with self.assertRaises(ProviderError) as caught:
                    provider.generate(request)

                self.assertEqual(
                    ProviderErrorCategory.INVALID_REQUEST,
                    caught.exception.category,
                )
                self.assertEqual(0, credential.resolve_count)
                self.assertEqual([], transport.requests)

    def test_context_and_sensitive_finish_reasons_do_not_become_success_output(
        self,
    ) -> None:
        context_provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=ScriptedTransport(
                chat_response("partial", finish_reason="model_context_window_exceeded")
            ),
        )
        sensitive_body = "sensitive-body-must-not-propagate"
        sensitive_provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=ScriptedTransport(
                chat_response(sensitive_body, finish_reason="sensitive")
            ),
        )

        context_result = context_provider.generate(text_request())
        sensitive_result = sensitive_provider.generate(text_request())

        self.assertEqual(FinishReason.CONTEXT_LIMIT, context_result.finish_reason)
        self.assertEqual(FinishReason.REFUSAL, sensitive_result.finish_reason)
        self.assertEqual((), sensitive_result.output)
        self.assertNotIn(sensitive_body, repr(sensitive_result))

        tool_finish_provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=ScriptedTransport(
                chat_response(
                    "", finish_reason="tool_calls", message_extra={"tool_calls": []}
                )
            ),
        )
        with self.assertRaises(ProviderError) as caught:
            tool_finish_provider.generate(text_request())
        self.assertEqual(
            ProviderErrorCategory.CONTRACT_VIOLATION,
            caught.exception.category,
        )

    def test_invalid_cached_usage_names_the_nested_field(self) -> None:
        invalid = chat_response("answer")
        document = json.loads(invalid.body)
        document["usage"]["prompt_tokens_details"]["cached_tokens"] = 1.5
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=ScriptedTransport(response(200, document)),
        )

        with self.assertRaises(ProviderError) as caught:
            provider.generate(text_request())

        self.assertIn(
            "usage.prompt_tokens_details.cached_tokens",
            str(caught.exception),
        )

    def test_generic_conformance_emits_schema_valid_redacted_zhipu_report(self) -> None:
        transport = ScriptedTransport(
            chat_response("zhipu-private-body-canary"),
            chat_response('{"ok":true}'),
        )
        provider = ZhipuChatCompletionsProvider(
            model="glm-5.3",
            credential=StaticCredential(),
            transport=transport,
            supported=frozenset({Capability.TEXT, Capability.STRUCTURED_OUTPUT}),
        )

        report = run_provider_conformance(
            provider,
            adapter_id="zhipu-chat-completions",
            execution_context="offline-standard-api-fixture",
            checks=("text", "structured"),
            max_provider_invocations=2,
            max_output_tokens=64,
        )
        document = report.to_mapping()

        self.assertEqual("passed", report.status)
        self.assertEqual("zhipu", report.provider)
        self.assertEqual(("glm-5.3",), report.observed_models)
        self.assertEqual(
            [], SchemaCatalog().validate("provider_conformance_report", document)
        )
        serialized = json.dumps(document)
        self.assertNotIn("zhipu-private-body-canary", serialized)
        self.assertNotIn("zhipu-response-1", serialized)


if __name__ == "__main__":
    unittest.main()
