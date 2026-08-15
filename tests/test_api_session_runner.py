import unittest
from dataclasses import FrozenInstanceError

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
    ProviderError,
    ProviderRegistry,
    ToolCall,
    ToolDefinition,
    Usage,
)


class ScriptedProvider:
    def __init__(
        self,
        *responses: ModelResponse,
        deployment: str = "remote",
        provider_identity: str = "fake",
        adapter_version: str = "0",
    ) -> None:
        self.responses = list(responses)
        self.requests: list[ModelRequest] = []
        self.deployment = deployment
        self.provider_identity = provider_identity
        self.adapter_version = adapter_version

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.provider_identity,
            adapter_version=self.adapter_version,
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
    model: str = "worker-model",
    provider: str = "fake",
) -> ModelResponse:
    output = (ContentBlock(kind="text", text=text),) if text else ()
    return ModelResponse(
        response_id=response_id,
        provider=provider,
        model=model,
        output=output,
        finish_reason=reason,
        tool_calls=tool_calls,
        usage=usage,
    )


class ApiSessionRunnerTests(unittest.TestCase):
    def test_session_limits_reject_non_finite_or_non_integer_ceilings(self) -> None:
        cases = (
            {"max_seconds": float("nan")},
            {"max_seconds": float("inf")},
            {"max_model_turns": 1.5},
            {"max_total_tokens": True},
            {"max_provider_reported_cost": float("nan")},
            {"max_provider_reported_cost": float("inf")},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                limits(**overrides)

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
        self.assertEqual(0, result.tool_failure_count)
        self.assertEqual((), result.tool_failures)
        self.assertEqual(["A"], seen)
        self.assertEqual(64, provider.requests[0].max_output_tokens)
        self.assertEqual(1, len(provider.requests[0].messages))
        self.assertEqual(3, len(provider.requests[1].messages))
        tool_message = provider.requests[1].messages[-1]
        self.assertEqual("tool", tool_message.role)
        self.assertEqual("call-1", tool_message.content[0].data["call_id"])

    def test_adapter_lookup_id_is_distinct_from_canonical_provider_identity(self) -> None:
        provider = ScriptedProvider(
            response(
                "r-canonical-provider",
                FinishReason.COMPLETE,
                text="done",
                provider="anthropic",
            ),
            provider_identity="anthropic",
        )
        approved = provider.capabilities()
        registry = ProviderRegistry()
        registry.register("anthropic-messages", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )

        result = runner.run(
            adapter_id="anthropic-messages",
            request=request(),
            limits=limits(),
            expected_capabilities=approved,
        )

        self.assertEqual(ApiSessionStatus.COMPLETED, result.status)
        self.assertEqual("anthropic", result.provider)
        self.assertEqual(1, len(provider.requests))

    def test_approved_capability_snapshot_drift_blocks_before_provider_call(self) -> None:
        provider = ScriptedProvider(
            response("r-never-called", FinishReason.COMPLETE),
            provider_identity="anthropic",
        )
        approved = provider.capabilities()
        provider.adapter_version = "drifted-version"
        registry = ProviderRegistry()
        registry.register("anthropic-messages", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )

        with self.assertRaises(ProviderError) as raised:
            runner.run(
                adapter_id="anthropic-messages",
                request=request(),
                limits=limits(),
                expected_capabilities=approved,
            )

        self.assertEqual("contract_violation", raised.exception.category)
        self.assertEqual([], provider.requests)

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

    def test_wall_time_exhaustion_prevents_starting_the_next_serial_tool(self) -> None:
        now = [0.0]
        executed: list[str] = []
        provider = ScriptedProvider(
            response(
                "r-wall-tools",
                FinishReason.TOOL_CALL,
                tool_calls=(
                    ToolCall("c1", "lookup", {"id": "first"}),
                    ToolCall("c2", "lookup", {"id": "second"}),
                ),
            )
        )
        registry = ProviderRegistry()
        registry.register("worker", provider)

        def execute(arguments):
            executed.append(str(arguments["id"]))
            now[0] = 2.0
            return {"ok": True}

        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), execute),),
            clock=lambda: now[0],
        )

        result = runner.run(
            provider_name="worker",
            request=request(),
            limits=limits(
                max_seconds=1,
                max_tool_calls=2,
                max_parallel_tool_calls=2,
            ),
        )

        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("wall-time-budget", result.stop_reason)
        self.assertEqual(["first"], executed)
        self.assertEqual(1, result.tool_calls)

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
        self.assertEqual(1, result.tool_calls)

    def test_token_usage_guard_pauses_when_usage_is_unavailable(self) -> None:
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

    def test_tool_failure_summary_survives_in_session_result(self) -> None:
        provider = ScriptedProvider(
            response(
                "r1",
                FinishReason.TOOL_CALL,
                tool_calls=(ToolCall("call-1", "lookup", {"id": "A"}),),
            ),
            response("r2", FinishReason.COMPLETE, text="handled"),
        )
        registry = ProviderRegistry()
        registry.register("worker", provider)

        def fail_lookup(arguments):
            raise LookupError("sensitive source detail")

        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), fail_lookup),),
        )

        result = runner.run(provider_name="worker", request=request(), limits=limits())

        self.assertEqual(ApiSessionStatus.COMPLETED, result.status)
        self.assertEqual(1, result.tool_failure_count)
        failure = result.tool_failures[0]
        self.assertEqual("lookup", failure.tool_name)
        self.assertEqual(1, failure.call_number)
        self.assertEqual("LookupError", failure.error_type)
        self.assertNotIn("sensitive source detail", repr(result.tool_failures))
        with self.assertRaises(FrozenInstanceError):
            failure.error_type = "ChangedError"

    def test_provider_reported_model_mismatch_blocks_before_tool_execution(self) -> None:
        provider = ScriptedProvider(
            response(
                "r1",
                FinishReason.TOOL_CALL,
                tool_calls=(ToolCall("call-wrong-model", "lookup", {"id": "A"}),),
                model="unexpected-model",
            )
        )
        registry = ProviderRegistry()
        registry.register("worker", provider)
        seen: list[str] = []
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(
                ClientTool(
                    lookup_definition(),
                    lambda arguments: seen.append(str(arguments["id"])),
                ),
            ),
        )

        result = runner.run(provider_name="worker", request=request(), limits=limits())

        self.assertEqual(ApiSessionStatus.FAILED, result.status)
        self.assertEqual("model-identity-mismatch", result.stop_reason)
        self.assertEqual(("unexpected-model",), result.observed_models)
        self.assertEqual([], seen)
        self.assertEqual(1, len(provider.requests))

    def test_provider_response_identity_mismatch_is_a_contract_violation(self) -> None:
        executed: list[str] = []
        provider = ScriptedProvider(
            response(
                "r-provider-mismatch",
                FinishReason.TOOL_CALL,
                tool_calls=(ToolCall("call-provider-mismatch", "lookup", {"id": "A"}),),
                provider="unexpected-provider",
            ),
            provider_identity="anthropic",
        )
        approved = provider.capabilities()
        registry = ProviderRegistry()
        registry.register("anthropic-messages", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(
                ClientTool(
                    lookup_definition(),
                    lambda arguments: executed.append(str(arguments["id"])),
                ),
            ),
        )

        with self.assertRaises(ProviderError) as raised:
            runner.run(
                adapter_id="anthropic-messages",
                request=request(),
                limits=limits(),
                expected_capabilities=approved,
            )

        self.assertEqual("contract_violation", raised.exception.category)
        self.assertEqual([], executed)
        self.assertEqual(1, len(provider.requests))

    def test_empty_tool_call_id_is_rejected_before_handler_execution(self) -> None:
        executed: list[str] = []
        provider = ScriptedProvider(
            response(
                "r-empty-call-id",
                FinishReason.TOOL_CALL,
                tool_calls=(ToolCall("", "lookup", {"id": "bounded"}),),
            )
        )
        registry = ProviderRegistry()
        registry.register("worker", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(
                ClientTool(
                    lookup_definition(),
                    lambda arguments: executed.append(str(arguments["id"])),
                ),
            ),
        )

        with self.assertRaises(ProviderError):
            runner.run(provider_name="worker", request=request(), limits=limits())

        self.assertEqual([], executed)
        self.assertEqual(1, len(provider.requests))

    def test_invalid_provider_usage_is_a_contract_violation_before_budget_aggregation(self) -> None:
        cases = (
            Usage(input_tokens=-1, output_tokens=1),
            Usage(input_tokens=True, output_tokens=1),
            Usage(input_tokens=1, output_tokens=1, provider_reported_cost=-0.1, currency="USD"),
            Usage(input_tokens=1, output_tokens=1, provider_reported_cost=0.1),
        )
        for index, bad_usage in enumerate(cases):
            with self.subTest(index=index):
                provider = ScriptedProvider(
                    response("bad-usage", FinishReason.COMPLETE, text="done", usage=bad_usage)
                )
                registry = ProviderRegistry()
                registry.register("worker", provider)
                runner = IsolatedApiSessionRunner(
                    registry,
                    tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
                )

                with self.assertRaises(ProviderError) as raised:
                    runner.run(provider_name="worker", request=request(), limits=limits())

                self.assertEqual("contract_violation", raised.exception.category)
                self.assertEqual(1, len(provider.requests))

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
