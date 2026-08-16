import unittest

from research_workbench.adapters.models import (
    ApiSessionLimits,
    ApiSessionStatus,
    Capability,
    ClientTool,
    ContentBlock,
    DataPolicy,
    DataPolicyGap,
    FinishReason,
    IsolatedApiSessionRunner,
    Message,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderRegistry,
    ToolCall,
    ToolDefinition,
    Usage,
)


class ScriptedProvider:
    def __init__(self, *responses: ModelResponse, deployment: str = "remote") -> None:
        self.responses = list(responses)
        self.requests: list[ModelRequest] = []
        self.deployment = deployment

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider="fake",
            adapter_version="0",
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
            models=("worker-model",),
            deployment=self.deployment,
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected provider call")
        return self.responses.pop(0)


def lookup_definition() -> ToolDefinition:
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


def request(*, local_only: bool = False) -> ModelRequest:
    return ModelRequest(
        model="worker-model",
        messages=(Message("user", (ContentBlock(kind="text", text="bounded task"),)),),
        tools=(lookup_definition(),),
        max_output_tokens=999,
        data_policy=DataPolicy(local_only=local_only),
    )


def limits(**overrides) -> ApiSessionLimits:
    values = {
        "max_model_turns": 3,
        "max_tool_calls": 2,
        "max_parallel_tool_calls": 1,
        "max_tool_result_chars": 100,
        "max_output_tokens_per_turn": 64,
        "max_seconds": 30,
        "max_total_tokens": 100,
    }
    values.update(overrides)
    return ApiSessionLimits(**values)


def response(
    response_id: str,
    reason: FinishReason,
    *,
    tool_calls: tuple[ToolCall, ...] = (),
    text: str = "",
    usage: Usage = Usage(input_tokens=5, output_tokens=2),
) -> ModelResponse:
    output = (ContentBlock(kind="text", text=text),) if text else ()
    return ModelResponse(
        response_id=response_id,
        provider="fake",
        model="worker-model",
        output=output,
        finish_reason=reason,
        tool_calls=tool_calls,
        usage=usage,
    )


class ApiSessionRunnerTests(unittest.TestCase):
    def test_runs_bounded_tool_loop_in_fresh_message_history(self) -> None:
        provider = ScriptedProvider(
            response(
                "r1",
                FinishReason.TOOL_CALL,
                tool_calls=(ToolCall("call-1", "lookup", {"id": "A"}),),
            ),
            response("r2", FinishReason.COMPLETE, text="done", usage=Usage(input_tokens=8, output_tokens=3)),
        )
        registry = ProviderRegistry()
        registry.register("worker", provider)
        seen: list[str] = []
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(
                ClientTool(
                    lookup_definition(),
                    lambda arguments: seen.append(str(arguments["id"])) or {"value": 7},
                ),
            ),
        )

        result = runner.run(provider_name="worker", request=request(), limits=limits())

        self.assertEqual(ApiSessionStatus.COMPLETED, result.status)
        self.assertEqual(2, result.model_turns)
        self.assertEqual(1, result.tool_calls)
        self.assertEqual(18, result.usage.total_tokens)
        self.assertEqual(["A"], seen)
        self.assertEqual(64, provider.requests[0].max_output_tokens)
        self.assertEqual(1, len(provider.requests[0].messages))
        self.assertEqual(3, len(provider.requests[1].messages))
        tool_message = provider.requests[1].messages[-1]
        self.assertEqual("tool", tool_message.role)
        self.assertEqual("call-1", tool_message.content[0].data["call_id"])

    def test_tool_budget_pauses_before_any_tool_side_effect(self) -> None:
        calls = (
            ToolCall("call-1", "lookup", {"id": "A"}),
            ToolCall("call-2", "lookup", {"id": "B"}),
        )
        provider = ScriptedProvider(response("r1", FinishReason.TOOL_CALL, tool_calls=calls))
        registry = ProviderRegistry()
        registry.register("worker", provider)
        executed: list[str] = []
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: executed.append("ran")),),
        )

        result = runner.run(
            provider_name="worker",
            request=request(),
            limits=limits(max_tool_calls=1, max_parallel_tool_calls=2),
        )

        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("tool-call-budget", result.stop_reason)
        self.assertEqual([], executed)

    def test_read_only_fan_out_within_cap_executes_every_call_in_order(self) -> None:
        calls = (
            ToolCall("call-1", "lookup", {"id": "A"}),
            ToolCall("call-2", "lookup", {"id": "B"}),
        )
        provider = ScriptedProvider(
            response("r1", FinishReason.TOOL_CALL, tool_calls=calls),
            response("r2", FinishReason.COMPLETE, text="done"),
        )
        registry = ProviderRegistry()
        registry.register("worker", provider)
        executed: list[str] = []
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(
                ClientTool(
                    lookup_definition(),
                    lambda arguments: executed.append(str(arguments["id"])) or {"value": 1},
                ),
            ),
        )

        result = runner.run(
            provider_name="worker",
            request=request(),
            limits=limits(max_parallel_tool_calls=2),
        )

        self.assertEqual(ApiSessionStatus.COMPLETED, result.status)
        self.assertEqual(2, result.tool_calls)
        # Fan-out is permitted, never concurrent: calls execute one by one in
        # the order the model issued them.
        self.assertEqual(["A", "B"], executed)
        tool_message = provider.requests[1].messages[-1]
        self.assertEqual("tool", tool_message.role)
        self.assertEqual(
            ("call-1", "call-2"),
            tuple(block.data["call_id"] for block in tool_message.content),
        )

    def test_side_effecting_turn_stays_serial_even_with_parallel_cap(self) -> None:
        write = ToolDefinition(
            name="write",
            description="Write one bounded record",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "integer"}},
                "required": ["value"],
                "additionalProperties": False,
            },
        )
        calls = (
            ToolCall("call-1", "lookup", {"id": "A"}),
            ToolCall("call-2", "write", {"value": 1}),
        )
        provider = ScriptedProvider(
            response("r1", FinishReason.TOOL_CALL, tool_calls=calls)
        )
        registry = ProviderRegistry()
        registry.register("worker", provider)
        executed: list[str] = []
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(
                ClientTool(
                    lookup_definition(),
                    lambda arguments: executed.append("lookup") or {"value": 1},
                ),
                ClientTool(
                    write,
                    lambda arguments: executed.append("write") or {"value": 1},
                    side_effect="local-write",
                ),
            ),
        )
        model_request = ModelRequest(
            model="worker-model",
            messages=(Message("user", (ContentBlock(kind="text", text="bounded task"),)),),
            tools=(lookup_definition(), write),
            max_output_tokens=999,
        )

        result = runner.run(
            provider_name="worker",
            request=model_request,
            limits=limits(
                max_parallel_tool_calls=2,
                allowed_tool_side_effects=frozenset({"read-only", "local-write"}),
            ),
        )

        # A turn mixing read-only and side-effecting tools may not fan out:
        # it pauses before any tool side effect.
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("parallel-tool-budget", result.stop_reason)
        self.assertEqual([], executed)

    def test_oversized_tool_result_is_not_silently_truncated(self) -> None:
        provider = ScriptedProvider(
            response(
                "r1",
                FinishReason.TOOL_CALL,
                tool_calls=(ToolCall("call-1", "lookup", {"id": "A"}),),
            )
        )
        registry = ProviderRegistry()
        registry.register("worker", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: "x" * 20),),
        )
        result = runner.run(
            provider_name="worker",
            request=request(),
            limits=limits(max_tool_result_chars=10),
        )
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("tool-result-size-budget", result.stop_reason)
        self.assertEqual(1, result.model_turns)

    def test_hard_token_budget_requires_usage(self) -> None:
        provider = ScriptedProvider(
            response("r1", FinishReason.COMPLETE, text="done", usage=Usage())
        )
        registry = ProviderRegistry()
        registry.register("worker", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )
        result = runner.run(provider_name="worker", request=request(), limits=limits())
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("token-usage-unavailable", result.stop_reason)

    def test_data_policy_blocks_before_provider_call(self) -> None:
        provider = ScriptedProvider(response("r1", FinishReason.COMPLETE, text="done"))
        registry = ProviderRegistry()
        registry.register("worker", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )
        with self.assertRaises(DataPolicyGap):
            runner.run(provider_name="worker", request=request(local_only=True), limits=limits())
        self.assertEqual([], provider.requests)

    def test_runner_does_not_fall_back_to_another_provider(self) -> None:
        registry = ProviderRegistry()
        registry.register("worker", ScriptedProvider(response("r1", FinishReason.COMPLETE)))
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )
        with self.assertRaises(KeyError):
            runner.run(provider_name="missing", request=request(), limits=limits())

    def test_disallowed_external_write_tool_is_blocked_before_model_call(self) -> None:
        provider = ScriptedProvider(response("r1", FinishReason.COMPLETE))
        registry = ProviderRegistry()
        registry.register("worker", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(
                ClientTool(
                    lookup_definition(),
                    lambda arguments: {},
                    side_effect="external-write",
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "side-effect"):
            runner.run(provider_name="worker", request=request(), limits=limits())
        self.assertEqual([], provider.requests)


if __name__ == "__main__":
    unittest.main()
