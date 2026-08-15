import copy
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from research_workbench.adapters.models import (
    AnthropicMessagesProvider,
    Capability,
    ContentBlock,
    FinishReason,
    Message,
    ModelRequest,
    ModelResponse,
    ProviderAdapterConfig,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCategory,
    ResponseFormat,
    ToolCall,
    Usage,
    build_live_provider,
    conformance_plan,
    run_provider_conformance,
)
from research_workbench.adapters.models.base import validate_structured_response
from research_workbench.adapters.models.conformance import _request_for
from research_workbench.validation import SchemaCatalog


class SyntheticProvider:
    def __init__(self, *, failure: ProviderError | None = None) -> None:
        self.failure = failure
        self.requests: list[ModelRequest] = []

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider="openai",
            adapter_version="0.1.0",
            supported=frozenset(
                {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
            ),
            models=("synthetic-model",),
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        if request.tools:
            self.assert_specific_probe(request)
            return ModelResponse(
                response_id="provider-response-id-must-not-be-retained",
                provider="openai",
                model="synthetic-model-version",
                output=(),
                finish_reason=FinishReason.TOOL_CALL,
                tool_calls=(
                    ToolCall(
                        call_id="provider-call-id-must-not-be-retained",
                        name="rwb_conformance_echo",
                        arguments={"value": "probe"},
                    ),
                ),
                usage=Usage(input_tokens=9, output_tokens=2),
            )
        if request.response_format.kind == "json_schema":
            text = '{"ok":true}'
        else:
            text = "response-content-must-not-be-retained"
        return ModelResponse(
            response_id="provider-response-id-must-not-be-retained",
            provider="openai",
            model="synthetic-model-version",
            output=(ContentBlock(kind="text", text=text),),
            finish_reason=FinishReason.COMPLETE,
            usage=Usage(input_tokens=7, output_tokens=2, cached_input_tokens=1),
        )

    def assert_specific_probe(self, request: ModelRequest) -> None:
        if request.tool_choice.kind != "specific":
            raise AssertionError("tool conformance request must force a specific tool")
        if request.tool_choice.name != "rwb_conformance_echo":
            raise AssertionError("unexpected conformance tool")


def config(*, enabled: bool = False) -> ProviderAdapterConfig:
    return ProviderAdapterConfig(
        adapter_id="anthropic-test",
        provider="anthropic",
        enabled=enabled,
        base_url="https://api.anthropic.com/v1",
        credential_env="ANTHROPIC_API_KEY",
        model_env="RWB_ANTHROPIC_MODEL",
        capabilities=frozenset(
            {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
        ),
        live_conformance="pending",
    )


class ConformancePlanTests(unittest.TestCase):
    def test_dry_run_plan_reads_no_environment_and_sends_no_network(self) -> None:
        plan = conformance_plan(config())
        self.assertEqual("dry-run", plan["mode"])
        self.assertIs(plan["environment_read"], False)
        self.assertEqual(0, plan["network_requests"])
        self.assertEqual(["text", "structured", "tools"], plan["checks"])
        self.assertIs(plan["adapter_enabled"], False)

    def test_budget_rejects_more_checks_than_invocations(self) -> None:
        with self.assertRaises(ValueError):
            conformance_plan(
                config(),
                checks=("text", "structured"),
                max_provider_invocations=1,
            )

    def test_live_factory_resolves_model_but_defers_missing_credential(self) -> None:
        with patch.dict("os.environ", {"RWB_ANTHROPIC_MODEL": "claude-synthetic"}, clear=True):
            provider = build_live_provider(config(enabled=True))
        self.assertIsInstance(provider, AnthropicMessagesProvider)
        self.assertEqual(("claude-synthetic",), provider.capabilities().models)


class ConformanceRunnerTests(unittest.TestCase):
    def test_passing_report_is_schema_valid_and_content_redacted(self) -> None:
        provider = SyntheticProvider()
        times = iter(
            [
                datetime(2026, 8, 13, 3, 0, tzinfo=timezone.utc),
                datetime(2026, 8, 13, 3, 0, 1, tzinfo=timezone.utc),
            ]
        )
        ticks = iter([10.0, 11.25])
        report = run_provider_conformance(
            provider,
            adapter_id="openai-synthetic",
            execution_context="offline-test-fixture",
            checks=("text", "structured", "tools"),
            max_provider_invocations=3,
            max_output_tokens=64,
            now=lambda: next(times),
            monotonic=lambda: next(ticks),
        )
        document = report.to_mapping()
        self.assertEqual("passed", report.status)
        self.assertEqual(3, report.budget.provider_invocations)
        self.assertEqual(3, report.budget.successful_responses)
        self.assertEqual(["passed", "passed", "passed"], [item.status for item in report.checks])
        self.assertEqual([], SchemaCatalog().validate("provider_conformance_report", document))
        serialized = json.dumps(document)
        self.assertNotIn("response-content-must-not-be-retained", serialized)
        self.assertNotIn("provider-response-id-must-not-be-retained", serialized)
        self.assertNotIn("provider-call-id-must-not-be-retained", serialized)
        self.assertNotIn('"value": "probe"', serialized)
        self.assertIs(document["privacy"]["response_content_stored"], False)
        unsafe = copy.deepcopy(document)
        unsafe["privacy"]["response_content_stored"] = True
        self.assertTrue(SchemaCatalog().validate("provider_conformance_report", unsafe))

    def test_first_provider_error_stops_remaining_checks_and_hides_message(self) -> None:
        provider = SyntheticProvider(
            failure=ProviderError(
                ProviderErrorCategory.AUTHENTICATION,
                "sensitive-provider-message-must-not-be-retained",
                status_code=401,
            )
        )
        report = run_provider_conformance(
            provider,
            adapter_id="openai-synthetic",
            execution_context="offline-test-fixture",
            checks=("text", "structured", "tools"),
            max_provider_invocations=3,
            max_output_tokens=64,
        )
        document = report.to_mapping()
        self.assertEqual("failed", report.status)
        self.assertEqual(1, report.budget.provider_invocations)
        self.assertEqual(0, report.budget.successful_responses)
        self.assertEqual(["failed", "not-run", "not-run"], [item.status for item in report.checks])
        self.assertEqual("authentication", report.checks[0].error_category)
        self.assertNotIn("sensitive-provider-message", json.dumps(document))
        self.assertEqual([], SchemaCatalog().validate("provider_conformance_report", document))


class StructuredOutputNormalizationTests(unittest.TestCase):
    """The port enforces structured output with LOCAL schema validation;
    a markdown fence around otherwise-conforming JSON is a transport quirk."""

    SCHEMA = {
        "type": "object",
        "properties": {"ok": {"const": True}},
        "required": ["ok"],
        "additionalProperties": False,
    }

    def _request(self):
        return ModelRequest(
            model="m",
            messages=(Message("user", (ContentBlock(kind="text", text="x"),)),),
            response_format=ResponseFormat(kind="json_schema", name="s", schema=self.SCHEMA),
        )

    def _response(self, text):
        return ModelResponse(
            response_id="r",
            provider="p",
            model="m",
            output=(ContentBlock(kind="text", text=text),),
            finish_reason=FinishReason.COMPLETE,
        )

    def test_fenced_conforming_json_passes(self) -> None:
        fenced = "```json" + "\n" + '{"ok": true}' + "\n" + "```"
        validate_structured_response(self._request(), self._response(fenced))

    def test_bare_conforming_json_passes(self) -> None:
        validate_structured_response(self._request(), self._response('{"ok": true}'))

    def test_fenced_non_conforming_json_still_fails(self) -> None:
        fenced = "```json" + "\n" + '{"nope": 1}' + "\n" + "```"
        with self.assertRaises(ProviderError):
            validate_structured_response(self._request(), self._response(fenced))

    def test_prose_still_fails(self) -> None:
        with self.assertRaises(ProviderError):
            validate_structured_response(self._request(), self._response("no json at all"))

    def test_structured_probe_embeds_the_schema_in_the_prompt(self) -> None:
        request = _request_for("structured", "probe-model", 64)
        text = "".join(
            block.text or "" for block in request.messages[-1].content if block.kind == "text"
        )
        self.assertIn('"ok"', text)
        self.assertIn("no markdown", text)


if __name__ == "__main__":
    unittest.main()
