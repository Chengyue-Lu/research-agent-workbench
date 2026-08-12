import unittest

from research_workbench.adapters.models import (
    Capability,
    CapabilityGap,
    ContentBlock,
    DataPolicy,
    DataPolicyGap,
    FinishReason,
    Message,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderRegistry,
    ResponseFormat,
    ToolDefinition,
)


class FakeTextProvider:
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider="fake",
            adapter_version="0",
            supported=frozenset({Capability.TEXT}),
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            response_id="fake-1",
            provider="fake",
            model=request.model,
            output=(ContentBlock(kind="text", text="ok"),),
            finish_reason=FinishReason.COMPLETE,
        )


def request_with_tools_and_schema() -> ModelRequest:
    return ModelRequest(
        model="fake-model",
        messages=(Message("user", (ContentBlock(kind="text", text="hello"),)),),
        tools=(
            ToolDefinition(
                name="lookup",
                description="look up a bounded record",
                input_schema={"type": "object", "properties": {}},
            ),
        ),
        response_format=ResponseFormat(
            kind="json_schema",
            name="record",
            schema={"type": "object", "properties": {"answer": {"type": "string"}}},
        ),
    )


class ProviderPortTests(unittest.TestCase):
    def test_registry_rejects_unsupported_capabilities_before_call(self) -> None:
        registry = ProviderRegistry()
        registry.register("fake", FakeTextProvider())
        with self.assertRaises(CapabilityGap) as caught:
            registry.require("fake", request_with_tools_and_schema())
        self.assertEqual(
            {Capability.TOOLS, Capability.STRUCTURED_OUTPUT},
            set(caught.exception.gaps),
        )

    def test_text_request_can_use_text_provider(self) -> None:
        registry = ProviderRegistry()
        registry.register("fake", FakeTextProvider())
        request = ModelRequest(
            model="fake-model",
            messages=(Message("user", (ContentBlock(kind="text", text="hello"),)),),
        )
        provider = registry.require("fake", request)
        self.assertEqual(FinishReason.COMPLETE, provider.generate(request).finish_reason)

    def test_duplicate_provider_name_is_rejected(self) -> None:
        registry = ProviderRegistry()
        registry.register("fake", FakeTextProvider())
        with self.assertRaises(ValueError):
            registry.register("fake", FakeTextProvider())

    def test_data_policy_is_checked_before_remote_call(self) -> None:
        registry = ProviderRegistry()
        registry.register("fake", FakeTextProvider())
        request = ModelRequest(
            model="fake-model",
            messages=(Message("user", (ContentBlock(kind="text", text="private"),)),),
            data_policy=DataPolicy(local_only=True),
        )
        with self.assertRaises(DataPolicyGap) as caught:
            registry.require("fake", request)
        self.assertEqual(("local_execution",), caught.exception.gaps)

    def test_explicit_capability_requirement_is_not_dropped(self) -> None:
        registry = ProviderRegistry()
        registry.register("fake", FakeTextProvider())
        request = ModelRequest(
            model="fake-model",
            messages=(Message("user", (ContentBlock(kind="text", text="hello"),)),),
            capability_requirements=frozenset({Capability.SERVER_TOOLS}),
        )
        with self.assertRaises(CapabilityGap) as caught:
            registry.require("fake", request)
        self.assertEqual((Capability.SERVER_TOOLS,), caught.exception.gaps)


if __name__ == "__main__":
    unittest.main()
