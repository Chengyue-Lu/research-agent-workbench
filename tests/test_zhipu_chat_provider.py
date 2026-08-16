import json
import unittest
from dataclasses import dataclass

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
    ResponseFormat,
    ToolDefinition,
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
    content: str,
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


def text_request(**changes) -> ModelRequest:
    values = {
        "model": "glm-5.3",
        "messages": (Message("user", (ContentBlock(kind="text", text="hello"),)),),
    }
    values.update(changes)
    return ModelRequest(**values)


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
        self.assertNotIn("thinking", payload)
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
        tool = ToolDefinition(
            name="lookup",
            description="Read one bounded record",
            input_schema={"type": "object"},
        )
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

        rendered = repr(result)
        self.assertNotIn(hidden, rendered)
        self.assertIn("reasoning content was omitted", result.warnings[0])
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
