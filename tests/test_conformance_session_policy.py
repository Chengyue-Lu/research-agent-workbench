"""Synthetic Session policy invariants; no transport or credential use."""

import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from jsonschema import Draft202012Validator

from research_workbench.adapters.models.port import (
    Capability, ContentBlock, FinishReason, Message, ModelRequest, ModelResponse,
    ProviderCapabilities, ProviderError, ProviderErrorCategory, ProviderRegistry,
    ToolCall, ToolChoice, ToolDefinition, Usage,
)
from research_workbench.adapters.models.session import (
    ApiSessionLimits, ApiSessionStatus, ClientTool, IsolatedApiSessionRunner,
)
from research_workbench.adapters.models.session_policy import ConformanceSessionPolicy, validate_summary_event
from research_workbench.adapters.models.openai import OpenAIResponsesProvider
from research_workbench.adapters.models.http import HttpResponse
from research_workbench.observability.trace import AgentTraceRecorder


def policy():
    return ConformanceSessionPolicy(
        "synthetic-tool-text", "1.0.0", ToolChoice("specific", "probe"),
        ToolChoice("none"), "probe", 1, 2, 1,
    )


def definition():
    return ToolDefinition("probe", "Return one synthetic value", {
        "type": "object", "properties": {"value": {"type": "string"}},
        "required": ["value"], "additionalProperties": False,
    })


def request():
    return ModelRequest(
        "synthetic-model", (Message("user", (ContentBlock("text", text="probe"),)),),
        tools=(definition(),), tool_choice=ToolChoice("specific", "probe"),
        max_output_tokens=256,
    )


def limits(**changes):
    values = dict(
        max_model_turns=2, max_tool_calls=1, max_parallel_tool_calls=1,
        max_tool_result_chars=100, max_output_tokens_per_turn=64,
        max_seconds=30, max_total_tokens=100,
    )
    return ApiSessionLimits(**(values | changes))


def response(*, tool=True, calls=None, reason=None, text="ok", usage=None):
    return ModelResponse(
        "synthetic-id", "synthetic-provider", "synthetic-model",
        () if tool else (ContentBlock("text", text=text),),
        reason or (FinishReason.TOOL_CALL if tool else FinishReason.COMPLETE),
        tool_calls=(ToolCall("call-1", "probe", {"value": "probe"}),) if calls is None and tool else (calls or ()),
        usage=usage if usage is not None else Usage(5, 2),
    )


class FakeProvider:
    def __init__(self, *responses, before_send=None):
        self.responses = list(responses)
        self.requests = []
        self.before_send = before_send

    def capabilities(self):
        return ProviderCapabilities(
            "synthetic-provider", "1.0.0", frozenset({Capability.TEXT, Capability.TOOLS}),
            models=("synthetic-model",),
        )

    def generate(self, value):
        self.requests.append(value)
        if self.before_send:
            self.before_send(value)
        answer = self.responses.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class Sink:
    conformance_summary_version = "1.0.0"

    def __init__(self, fail=None):
        self.events = []
        self.fail = fail

    def record(self, kind, payload):
        if kind == self.fail:
            self.fail = None
            raise OSError("synthetic capture failure")
        self.events.append((kind, payload))


class ConformanceSessionPolicyTests(unittest.TestCase):
    def runner(self, provider, handler=None, side_effect="read-only", tool_definition=None, clock=lambda: 0):
        registry = ProviderRegistry()
        registry.register("synthetic", provider)
        self.executed = []

        def pure_handler(arguments):
            if arguments["value"] != "probe":
                raise ValueError("synthetic business assertion failed")
            self.executed.append(dict(arguments))
            return {"value": "probe"}

        return IsolatedApiSessionRunner(registry, tools=(ClientTool(
            tool_definition or definition(), handler or pure_handler, side_effect,
        ),), clock=clock)

    def run_policy(self, provider, *, handler=None, session_policy=None, session_limits=None, sink=None, cancelled=None, clock=lambda: 0):
        return self.runner(provider, handler=handler, clock=clock).run(
            provider_name="synthetic", request=request(), limits=session_limits or limits(),
            tool_choice_transition=session_policy or policy(), event_sink=sink,
            cancel_requested=cancelled,
        )

    def test_explicit_policy_runs_same_session_specific_tool_result_none(self):
        provider = FakeProvider(response(), response(tool=False))
        sink = Sink()
        result = self.run_policy(provider, sink=sink)
        self.assertEqual(ApiSessionStatus.COMPLETED, result.status)
        self.assertEqual((2, 1), (result.model_turns, result.tool_calls))
        self.assertEqual([ToolChoice("specific", "probe"), ToolChoice("none")], [r.tool_choice for r in provider.requests])
        first, second = provider.requests
        self.assertEqual(first.tools, second.tools)
        self.assertEqual(first.model, second.model)
        self.assertEqual(first.extensions, second.extensions)
        self.assertEqual(first.metadata, second.metadata)
        self.assertEqual(64, second.max_output_tokens)
        self.assertEqual(["user", "assistant", "tool"], [m.role for m in second.messages])
        self.assertEqual("call-1", second.messages[-1].content[0].data["call_id"])
        self.assertEqual({"value": "probe"}, second.messages[-1].content[0].data["output"])
        self.assertEqual([{"value": "probe"}], self.executed)
        requests = [p for kind, p in sink.events if kind == "request-summary"]
        self.assertEqual(policy().sha256, requests[0]["policy_sha256"])
        self.assertEqual(["specific-tool", "result-text"], [p["phase"] for p in requests])
        context = next(p for kind, p in sink.events if kind == "tool-context-summary")
        self.assertTrue(context["result_entered_context"])
        self.assertEqual("local-history", context["context_scope"])

    def test_default_specific_choice_is_retained_and_text_fails(self):
        provider = FakeProvider(response(), response(tool=False))
        result = self.runner(provider).run(provider_name="synthetic", request=request(), limits=limits())
        self.assertEqual(ApiSessionStatus.FAILED, result.status)
        self.assertEqual(["specific", "specific"], [r.tool_choice.kind for r in provider.requests])

    def test_actual_openai_codec_emits_specific_then_none_and_matching_result(self):
        class SyntheticCredential:
            label = "synthetic-only"

            def available(self):
                return True

            def resolve(self):
                return "synthetic-only"

        class MemoryTransport:
            def __init__(self):
                self.requests = []

            def send(self, value):
                self.requests.append(value)
                output = [{"type": "function_call", "call_id": "call-1", "name": "probe", "arguments": '{"value":"probe"}'}] if len(self.requests) == 1 else [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}]
                return HttpResponse(200, {}, json.dumps({
                    "id": "synthetic-id", "model": "synthetic-model", "status": "completed",
                    "output": output, "usage": {"input_tokens": 5, "output_tokens": 2},
                }).encode("utf-8"))

        transport = MemoryTransport()
        provider = OpenAIResponsesProvider(
            model="synthetic-model", credential=SyntheticCredential(), transport=transport,
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
        )
        result = self.run_policy(provider)
        self.assertEqual(ApiSessionStatus.COMPLETED, result.status)
        first, second = [json.loads(item.body) for item in transport.requests]
        self.assertEqual({"type": "function", "name": "probe"}, first["tool_choice"])
        self.assertEqual("none", second["tool_choice"])
        self.assertEqual(first["tools"], second["tools"])
        self.assertEqual(first["model"], second["model"])
        tool_result = next(item for item in second["input"] if item.get("type") == "function_call_output")
        self.assertEqual("call-1", tool_result["call_id"])
        self.assertEqual({"value": "probe"}, json.loads(tool_result["output"]))

    def test_policy_mapping_is_closed_copied_and_immutable(self):
        document = policy().to_mapping()
        rebuilt = ConformanceSessionPolicy.from_mapping(document)
        document["initial_choice"]["name"] = "changed"
        self.assertEqual("probe", rebuilt.initial_choice.name)
        self.assertEqual(policy().sha256, rebuilt.sha256)
        with self.assertRaises(FrozenInstanceError):
            rebuilt.expected_tool_name = "changed"
        for changed in (
            policy().to_mapping() | {"extra": True},
            policy().to_mapping() | {"version": "2.0.0"},
            policy().to_mapping() | {"expected_tool_calls": True},
            policy().to_mapping() | {"max_model_turns": 3},
            policy().to_mapping() | {"after_successful_tool_result": {"kind": "auto", "name": None}},
            policy().to_mapping() | {"initial_choice": {"kind": "specific", "name": "other"}},
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                ConformanceSessionPolicy.from_mapping(changed)

    def test_policy_schema_closed_fields_and_ceiling(self):
        path = Path(__file__).resolve().parents[1] / "schemas/v0.1.0/conformance-session-policy.schema.json"
        validator = Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))
        validator.validate(policy().to_mapping())
        for changed in ({"extra": 1}, {"max_tool_calls": 2}, {"expected_tool_calls": False}):
            self.assertTrue(list(validator.iter_errors(policy().to_mapping() | changed)))

    def test_request_and_result_mutable_json_are_defensively_frozen(self):
        original = request()
        provider = FakeProvider(response(), response(tool=False))

        def inspect(actual):
            original.tools[0].input_schema["properties"]["value"]["type"] = "integer"
            original.metadata["test"] = "changed"
            with self.assertRaises(TypeError):
                actual.tools[0].input_schema["properties"]["value"]["type"] = "integer"
            with self.assertRaises(TypeError):
                actual.metadata["test"] = "changed"
            if len(actual.messages) == 3:
                with self.assertRaises(TypeError):
                    actual.messages[-1].content[0].data["output"]["value"] = "changed"

        provider.before_send = inspect
        runner = self.runner(provider)
        result = runner.run(provider_name="synthetic", request=original, limits=limits(), tool_choice_transition=policy())
        self.assertEqual(ApiSessionStatus.COMPLETED, result.status)
        self.assertEqual("string", provider.requests[1].tools[0].input_schema["properties"]["value"]["type"])
        self.assertEqual({}, provider.requests[1].metadata)

    def test_broad_or_narrow_ceiling_mismatch_blocks_before_send(self):
        for changed in (
            {"max_model_turns": 3}, {"max_model_turns": 1}, {"max_tool_calls": 2},
            {"max_parallel_tool_calls": 2},
            {"allowed_tool_side_effects": frozenset({"read-only", "external-write"})},
        ):
            provider = FakeProvider(response())
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.run_policy(provider, session_limits=limits(**changed))
            self.assertEqual([], provider.requests)

    def test_nonfinite_or_noninteger_limits_block_before_send(self):
        for changed in (
            {"max_seconds": float("nan")}, {"max_seconds": float("inf")},
            {"max_model_turns": 2.0}, {"max_total_tokens": True},
            {"max_output_tokens_per_turn": 64.5},
            {"max_provider_reported_cost": float("nan")},
        ):
            provider = FakeProvider(response())
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.run_policy(provider, session_limits=limits(**changed))
            self.assertEqual([], provider.requests)

    def test_caller_limit_mutation_cannot_expand_frozen_deadline(self):
        selected = limits()
        state = {"clock": 0}

        def handler(arguments):
            object.__setattr__(selected, "max_seconds", 1000)
            state["clock"] = 31
            return {"value": "probe"}

        provider = FakeProvider(response())
        result = self.run_policy(provider, handler=handler, session_limits=selected, clock=lambda: state["clock"])
        self.assertEqual("wall-time-budget", result.stop_reason)
        self.assertEqual(1, len(provider.requests))

    def test_reflective_request_control_mutation_blocks_transition(self):
        provider = FakeProvider(response())

        def mutate(actual):
            dict.__setitem__(actual.metadata, "test", "tampered")

        provider.before_send = mutate
        result = self.run_policy(provider)
        self.assertEqual("conformance-session-request-drift", result.stop_reason)
        self.assertEqual([], self.executed)
        self.assertEqual(1, len(provider.requests))

    def test_capture_boundary_cancellation_blocks_send_and_tool(self):
        for target in ("request-summary", "tool-attempt-summary"):
            state = {"cancel": False}

            class CancellingSink(Sink):
                def record(self, kind, payload):
                    super().record(kind, payload)
                    if kind == target:
                        state["cancel"] = True

            provider = FakeProvider(response())
            result = self.run_policy(provider, sink=CancellingSink(), cancelled=lambda: state["cancel"])
            self.assertEqual("cancellation-requested", result.stop_reason)
            self.assertEqual([], self.executed)
            self.assertEqual(0 if target == "request-summary" else 1, len(provider.requests))
            self.assertEqual(0, result.tool_calls)

    def test_nonfinite_and_backwards_clock_fail_before_send(self):
        for observations in ((float("nan"), float("nan")), (5, 4)):
            provider = FakeProvider(response())
            times = iter(observations)
            result = self.run_policy(provider, clock=lambda: next(times))
            self.assertEqual("wall-time-clock-invalid", result.stop_reason)
            self.assertEqual([], provider.requests)

    def test_request_choice_and_extra_tool_mismatch_blocks(self):
        for changed in (
            replace(request(), tool_choice=ToolChoice("auto")),
            replace(request(), tools=(definition(), ToolDefinition("other", "other", {"type": "object"}))),
            replace(request(), messages=(Message("tool", (ContentBlock("tool_result", data={}),)),)),
            replace(request(), metadata={"Authorization": "Bearer synthetic-only"}),
            replace(request(), extensions={"native": {"auth": "synthetic-only"}}),
        ):
            provider = FakeProvider(response())
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.runner(provider).run(provider_name="synthetic", request=changed, limits=limits(), tool_choice_transition=policy())
            self.assertEqual([], provider.requests)

    def test_handler_definition_and_write_permission_mismatch_blocks(self):
        for changed in (
            {"side_effect": "external-write"},
            {"tool_definition": ToolDefinition("probe", "different description", {"type": "object"})},
        ):
            provider = FakeProvider(response())
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.runner(provider, **changed).run(provider_name="synthetic", request=request(), limits=limits(), tool_choice_transition=policy())
            self.assertEqual([], provider.requests)

    def test_wrong_multiple_empty_id_and_invalid_arguments_never_invoke_tool(self):
        for calls in (
            (ToolCall("call-1", "other", {"value": "probe"}),),
            (ToolCall("a", "probe", {"value": "probe"}), ToolCall("b", "probe", {"value": "probe"})),
            (ToolCall("", "probe", {"value": "probe"}),),
            (ToolCall("a", "probe", {"value": 4}),),
            (ToolCall("a", "probe", {"value": "probe"}, executed_by="provider"),),
        ):
            provider = FakeProvider(response(calls=calls))
            with self.subTest(calls=calls):
                result = self.run_policy(provider)
                self.assertEqual(ApiSessionStatus.FAILED, result.status)
                self.assertEqual([], self.executed)
                self.assertEqual(1, len(provider.requests))

    def test_handler_business_assertion_failure_does_not_transition(self):
        provider = FakeProvider(response(calls=(ToolCall("a", "probe", {"value": "wrong"}),)))
        sink = Sink()
        result = self.run_policy(provider, sink=sink)
        self.assertEqual(ApiSessionStatus.FAILED, result.status)
        self.assertEqual("conformance-tool-handler-failed", result.stop_reason)
        self.assertEqual(1, result.tool_calls)
        self.assertEqual(1, len(provider.requests))
        event = next(p for k, p in sink.events if k == "tool-result-summary")
        self.assertEqual("failed", event["status"])
        self.assertFalse(event["result_eligible_for_local_history"])
        self.assertFalse(any(k == "tool-context-summary" for k, _ in sink.events))

    def test_non_json_and_nan_tool_results_fail_without_transition(self):
        for output in (object(), float("nan")):
            provider = FakeProvider(response())
            result = self.run_policy(provider, handler=lambda arguments: output)
            self.assertEqual(ApiSessionStatus.FAILED, result.status)
            self.assertEqual(1, len(provider.requests))

    def test_oversize_time_and_cancelled_tool_result_never_enters_history(self):
        for stop in ("size", "time", "cancel"):
            state = {"clock": 0, "cancel": False}

            def handler(arguments):
                if stop == "time":
                    state["clock"] = 31
                if stop == "cancel":
                    state["cancel"] = True
                return "x" * (101 if stop == "size" else 1)

            provider = FakeProvider(response())
            sink = Sink()
            result = self.run_policy(provider, handler=handler, sink=sink,
                                     clock=lambda: state["clock"], cancelled=lambda: state["cancel"])
            self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
            self.assertEqual(1, len(provider.requests))
            self.assertFalse(next(p for k, p in sink.events if k == "tool-result-summary")["result_eligible_for_local_history"])
            self.assertFalse(any(k == "tool-context-summary" for k, _ in sink.events))

    def test_unknown_negative_boolean_usage_and_budget_stop_do_not_invoke_tool(self):
        for usage in (Usage(), Usage(-1, 2), Usage(True, 2), Usage(101, 2), Usage(5, 2, provider_reported_cost=float("nan"))):
            provider = FakeProvider(response(usage=usage))
            result = self.run_policy(provider)
            self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
            self.assertEqual([], self.executed)
            self.assertEqual(1, len(provider.requests))

    def test_unknown_usage_also_blocks_when_numeric_token_ceiling_not_set(self):
        provider = FakeProvider(response(usage=Usage()))
        result = self.run_policy(provider, session_limits=limits(max_total_tokens=None))
        self.assertEqual("token-usage-unavailable", result.stop_reason)
        self.assertEqual([], self.executed)

    def test_unknown_cost_with_explicit_cost_ceiling_blocks(self):
        provider = FakeProvider(response())
        result = self.run_policy(provider, session_limits=limits(max_provider_reported_cost=0.01))
        self.assertEqual("cost-usage-unavailable", result.stop_reason)
        self.assertEqual([], self.executed)

    def test_mutation_of_valid_policy_identity_during_handler_blocks_transition(self):
        selected = policy()

        def handler(arguments):
            object.__setattr__(selected, "policy_id", "other-policy")
            return {"value": "probe"}

        provider = FakeProvider(response())
        result = self.run_policy(provider, handler=handler, session_policy=selected)
        self.assertEqual("conformance-session-policy-drift", result.stop_reason)
        self.assertEqual(1, len(provider.requests))

    def test_terminal_failure_with_tool_does_not_invoke_handler(self):
        provider = FakeProvider(response(reason=FinishReason.ERROR))
        result = self.run_policy(provider)
        self.assertEqual(ApiSessionStatus.FAILED, result.status)
        self.assertEqual([], self.executed)

    def test_unadvertised_output_kind_fails_without_tool_execution(self):
        malformed = replace(response(), output=(ContentBlock("reasoning", text="opaque"),))
        provider = FakeProvider(malformed)
        result = self.run_policy(provider)
        self.assertEqual("conformance-output-kind-unsupported", result.stop_reason)
        self.assertEqual([], self.executed)

    def test_second_round_tool_is_rejected_without_third_turn_or_handler(self):
        provider = FakeProvider(response(), response())
        result = self.run_policy(provider)
        self.assertEqual(ApiSessionStatus.FAILED, result.status)
        self.assertEqual(1, result.tool_calls)
        self.assertEqual(2, len(provider.requests))
        self.assertEqual(1, len(self.executed))

    def test_second_round_non_success_and_empty_text_cannot_complete(self):
        for reason, text in ((FinishReason.LENGTH, "partial"), (FinishReason.REFUSAL, "no"), (FinishReason.ERROR, "error"), (FinishReason.COMPLETE, " ")):
            provider = FakeProvider(response(), response(tool=False, reason=reason, text=text))
            result = self.run_policy(provider)
            self.assertNotEqual(ApiSessionStatus.COMPLETED, result.status)
            self.assertEqual(2, len(provider.requests))

    def test_provider_failure_and_cancel_preserve_failed_send_events(self):
        for category in (ProviderErrorCategory.TRANSIENT, ProviderErrorCategory.CANCELLED):
            provider = FakeProvider(response(), ProviderError(category, "synthetic failure"))
            sink = Sink()
            result = self.run_policy(provider, sink=sink)
            self.assertNotEqual(ApiSessionStatus.COMPLETED, result.status)
            self.assertEqual(2, len(provider.requests))
            self.assertEqual(2, sum(k == "request-summary" for k, _ in sink.events))
            self.assertEqual(1, result.model_turns)  # Historical successful-response count is unchanged.

    def test_cancel_before_send_blocks_all_calls(self):
        provider = FakeProvider(response())
        result = self.run_policy(provider, cancelled=lambda: True)
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual([], provider.requests)

    def test_post_tool_capture_gap_blocks_transition(self):
        provider = FakeProvider(response())
        result = self.run_policy(provider, sink=Sink("tool-result-summary"))
        self.assertEqual("trace-capture-gap", result.stop_reason)
        self.assertEqual(1, len(provider.requests))

    def test_first_response_capture_gap_retains_verified_usage_without_tool_or_next_turn(self):
        first = response()
        provider = FakeProvider(first, response(tool=False))
        sink = Sink("response-summary")
        result = self.run_policy(provider, sink=sink)
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("trace-capture-gap", result.stop_reason)
        self.assertEqual((1, 0), (result.model_turns, result.tool_calls))
        self.assertEqual((5, 2, 7), (result.usage.input_tokens, result.usage.output_tokens, result.usage.total_tokens))
        self.assertEqual(first, result.final_response)
        self.assertEqual(1, len(provider.requests))
        self.assertEqual([], self.executed)
        self.assertFalse(any(kind.startswith("tool-") for kind, _ in sink.events))
        terminal = next(payload for kind, payload in sink.events if kind == "session-summary")
        self.assertEqual((1, 1, 0), (terminal["model_attempts"], terminal["successful_responses"], terminal["tool_invocations"]))

    def test_second_response_capture_gap_retains_both_verified_responses_and_no_extra_execution(self):
        second = response(tool=False)
        provider = FakeProvider(response(), second)

        class SecondResponseFailingSink(Sink):
            def record(self, kind, payload):
                if kind == "response-summary" and payload["model_attempt"] == 2:
                    raise OSError("synthetic second response capture failure")
                super().record(kind, payload)

        sink = SecondResponseFailingSink()
        result = self.run_policy(provider, sink=sink)
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("trace-capture-gap", result.stop_reason)
        self.assertEqual((2, 1), (result.model_turns, result.tool_calls))
        self.assertEqual((10, 4, 14), (result.usage.input_tokens, result.usage.output_tokens, result.usage.total_tokens))
        self.assertEqual(second, result.final_response)
        self.assertEqual(2, len(provider.requests))
        self.assertEqual([{"value": "probe"}], self.executed)
        self.assertEqual(["specific", "none"], [value.tool_choice.kind for value in provider.requests])
        self.assertEqual(1, sum(kind == "tool-attempt-summary" for kind, _ in sink.events))
        terminal = next(payload for kind, payload in sink.events if kind == "session-summary")
        self.assertEqual((2, 2, 1), (terminal["model_attempts"], terminal["successful_responses"], terminal["tool_invocations"]))
        for kind, payload in sink.events:
            validate_summary_event(kind, payload)

    def test_response_capture_error_message_is_not_retained_and_cannot_continue(self):
        marker = "SYNTHETIC-PRIVATE-CAPTURE-ERROR-MARKER"

        class PrivateErrorSink(Sink):
            def record(self, kind, payload):
                if kind == "response-summary":
                    raise OSError(marker)
                super().record(kind, payload)

        provider = FakeProvider(response(), response(tool=False))
        sink = PrivateErrorSink()
        result = self.run_policy(provider, sink=sink)
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("trace-capture-gap", result.stop_reason)
        self.assertEqual(7, result.usage.total_tokens)
        self.assertEqual(1, len(provider.requests))
        self.assertEqual([], self.executed)
        self.assertNotIn(marker, repr(result))
        self.assertNotIn(marker, json.dumps(sink.events))
        gap = next(payload for kind, payload in sink.events if kind == "capture-gap-summary")
        self.assertEqual("response-summary-capture-failed", gap["failure_code"])

    def test_response_capture_gap_retains_unknown_usage_without_filling_zero(self):
        provider = FakeProvider(response(usage=Usage()), response(tool=False))
        result = self.run_policy(provider, sink=Sink("response-summary"))
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("trace-capture-gap", result.stop_reason)
        self.assertEqual(1, result.model_turns)
        self.assertIsNone(result.usage.input_tokens)
        self.assertIsNone(result.usage.output_tokens)
        self.assertIsNone(result.usage.total_tokens)
        self.assertEqual(1, len(provider.requests))
        self.assertEqual([], self.executed)

    def test_persistent_response_and_stop_capture_failure_returns_all_usage_with_bounded_capture(self):
        marker = "SYNTHETIC-PRIVATE-PERSISTENT-CAPTURE-ERROR"
        for failed_turn in (1, 2):
            with self.subTest(failed_turn=failed_turn):
                class PersistentlyBrokenSink(Sink):
                    def __init__(self):
                        super().__init__()
                        self.attempts = []

                    def record(self, kind, payload):
                        self.attempts.append(kind)
                        if (kind == "response-summary" and payload["model_attempt"] == failed_turn
                            or kind in {"capture-gap-summary", "session-summary"}):
                            raise OSError(marker)
                        super().record(kind, payload)

                provider = FakeProvider(response(), response(tool=False))
                sink = PersistentlyBrokenSink()
                result = self.run_policy(provider, sink=sink)
                self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
                self.assertEqual("trace-capture-gap", result.stop_reason)
                self.assertEqual(failed_turn, result.model_turns)
                self.assertEqual(7 * failed_turn, result.usage.total_tokens)
                self.assertEqual(failed_turn, len(provider.requests))
                self.assertEqual(failed_turn - 1, len(self.executed))
                self.assertEqual(failed_turn - 1, result.tool_calls)
                self.assertEqual(1, sink.attempts.count("capture-gap-summary"))
                self.assertEqual(1, sink.attempts.count("session-summary"))
                self.assertIn("conformance-gap-summary-capture-failed", result.warnings)
                self.assertIn("conformance-stop-summary-capture-failed", result.warnings)
                self.assertNotIn(marker, repr(result))
                self.assertNotIn(marker, json.dumps(sink.events))

    def assert_capture_fault_contained(self, kind, *, turn=None, persistent=False):
        marker = "SYNTHETIC-PRIVATE-CAPTURE-FAULT"

        class FaultSink(Sink):
            def __init__(self):
                super().__init__()
                self.attempts = []
                self.failed = False

            def record(self, actual_kind, payload):
                self.attempts.append((actual_kind, dict(payload)))
                target = actual_kind == kind and (turn is None or payload.get("model_attempt") == turn)
                if (target and (not self.failed or persistent)
                    or persistent and self.failed and actual_kind in {"capture-gap-summary", "session-summary"}):
                    self.failed = True
                    raise OSError(marker)
                super().record(actual_kind, payload)

        first, second = response(), response(tool=False)
        provider = FakeProvider(first, second)
        sink = FaultSink()
        result = self.run_policy(provider, sink=sink)
        expected_responses = 0 if kind == "request-summary" and turn == 1 else 2 if kind == "session-summary" else 1
        expected_tools = int(kind not in {"tool-attempt-summary"} and not (kind == "request-summary" and turn == 1))
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("trace-capture-gap", result.stop_reason)
        self.assertEqual((expected_responses, expected_tools), (result.model_turns, result.tool_calls))
        self.assertEqual(expected_responses, len(provider.requests))
        self.assertEqual(expected_tools, len(self.executed))
        self.assertEqual(7 * expected_responses if expected_responses else None, result.usage.total_tokens)
        self.assertEqual(second if expected_responses == 2 else first if expected_responses else None, result.final_response)
        attempted_kinds = [actual_kind for actual_kind, _ in sink.attempts]
        self.assertEqual(1, attempted_kinds.count("capture-gap-summary"))
        self.assertEqual(1, attempted_kinds.count("session-summary"))
        self.assertNotIn(marker, repr(result))
        self.assertNotIn(marker, json.dumps(sink.attempts))
        for actual_kind, payload in sink.attempts:
            validate_summary_event(actual_kind, payload)
        if persistent:
            self.assertIn("conformance-gap-summary-capture-failed", result.warnings)
            self.assertIn("conformance-stop-summary-capture-failed", result.warnings)
        terminal = next(payload for actual_kind, payload in sink.attempts if actual_kind == "session-summary")
        self.assertEqual(expected_responses, terminal["model_attempts"])
        self.assertEqual(expected_responses, terminal["successful_responses"])
        self.assertEqual(expected_tools, terminal["tool_invocations"])
        expected_history = expected_tools == 1
        self.assertEqual(expected_history, terminal["local_tool_history_assembled"])
        self.assertEqual(int(kind == "session-summary"), terminal["tool_context_submission_attempts"])

    def test_request_summary_once_and_persistent_faults_stop_before_each_send(self):
        for turn in (1, 2):
            for persistent in (False, True):
                with self.subTest(turn=turn, persistent=persistent):
                    self.assert_capture_fault_contained("request-summary", turn=turn, persistent=persistent)

    def test_tool_attempt_summary_once_and_persistent_faults_do_not_invoke_handler(self):
        for persistent in (False, True):
            with self.subTest(persistent=persistent):
                self.assert_capture_fault_contained("tool-attempt-summary", persistent=persistent)

    def test_tool_context_summary_once_and_persistent_faults_retain_local_history_without_send(self):
        for persistent in (False, True):
            with self.subTest(persistent=persistent):
                self.assert_capture_fault_contained("tool-context-summary", persistent=persistent)

    def test_ordinary_terminal_summary_once_and_persistent_faults_preserve_both_responses(self):
        for persistent in (False, True):
            with self.subTest(persistent=persistent):
                self.assert_capture_fault_contained("session-summary", persistent=persistent)

    def test_terminal_capture_fault_preserves_unknown_usage_and_preexisting_provider_failure_facts(self):
        for unknown in (False, True):
            with self.subTest(unknown=unknown):
                first = response(usage=Usage()) if unknown else response()
                provider = FakeProvider(first, ProviderError(ProviderErrorCategory.TRANSIENT, "synthetic private provider error"))
                sink = Sink("session-summary")
                result = self.run_policy(provider, sink=sink)
                self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
                self.assertEqual("trace-capture-gap", result.stop_reason)
                self.assertEqual(1, result.model_turns)
                self.assertEqual(None if unknown else 7, result.usage.total_tokens)
                self.assertEqual(0 if unknown else 1, result.tool_calls)
                self.assertEqual(1 if unknown else 2, len(provider.requests))
                self.assertEqual(0 if unknown else 1, len(self.executed))
                self.assertEqual(first, result.final_response)
                gap = next(payload for kind, payload in sink.events if kind == "capture-gap-summary")
                self.assertEqual("session-summary-capture-failed", gap["failure_code"])

    def test_tool_context_callback_policy_drift_still_blocks_following_model(self):
        selected = policy()

        class DriftSink(Sink):
            def record(self, kind, payload):
                super().record(kind, payload)
                if kind == "tool-context-summary":
                    object.__setattr__(selected, "policy_id", "changed-after-tool-context")

        provider = FakeProvider(response(), response(tool=False))
        result = self.run_policy(provider, session_policy=selected, sink=DriftSink())
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("conformance-session-policy-drift", result.stop_reason)
        self.assertEqual((1, 1), (result.model_turns, result.tool_calls))
        self.assertEqual(7, result.usage.total_tokens)
        self.assertEqual(1, len(provider.requests))

    def test_persistent_tool_result_capture_fault_does_not_escape_stopping_summary(self):
        class BrokenResultSink(Sink):
            def __init__(self):
                super().__init__()
                self.attempts = []

            def record(self, kind, payload):
                self.attempts.append(kind)
                if kind in {"tool-result-summary", "capture-gap-summary", "session-summary"}:
                    raise OSError("synthetic persistent result capture failure")
                super().record(kind, payload)

        provider = FakeProvider(response(), response(tool=False))
        sink = BrokenResultSink()
        result = self.run_policy(provider, sink=sink)
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("trace-capture-gap", result.stop_reason)
        self.assertEqual((1, 1, 7), (result.model_turns, result.tool_calls, result.usage.total_tokens))
        self.assertEqual(1, len(provider.requests))
        self.assertEqual(1, len(self.executed))
        self.assertEqual(1, sink.attempts.count("capture-gap-summary"))
        self.assertEqual(1, sink.attempts.count("session-summary"))
        self.assertNotIn("tool-context-summary", sink.attempts)

    def test_generic_trace_sink_is_rejected_before_provider_use(self):
        provider = FakeProvider(response(), response(tool=False))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = AgentTraceRecorder(
                root / "work/SESSION-POLICY/AT-1", task_id="SESSION-POLICY",
                task_revision=1, attempt_id="AT-1", task_snapshot={"task_id": "SESSION-POLICY", "revision": 1},
                accountable_owner="Huang Yi", actor_id="synthetic-session-policy",
                runtime_identity="synthetic-session-policy", provider="synthetic-provider",
                read_allowlist=("inputs/**",), write_scope=("outputs/**",), tool_allowlist=("probe",),
            )
            marker = "SYNTHETIC-RAW-AUTH-INPUT-MARKER"
            private_request = replace(request(),
                messages=(Message("user", (ContentBlock("text", text=marker),)),),
                metadata={"Authorization": "Bearer " + marker},
            )
            with self.assertRaisesRegex(ValueError, "privacy summary sink"):
                self.runner(provider).run(
                    provider_name="synthetic", request=private_request, limits=limits(),
                    tool_choice_transition=policy(), event_sink=recorder,
                )
            self.assertEqual([], provider.requests)
            self.assertEqual([], self.executed)
            for artifact in recorder.attempt_dir.rglob("*"):
                if artifact.is_file():
                    self.assertNotIn(marker, artifact.read_text(encoding="utf-8"))

    def test_metadata_and_extensions_are_rejected_before_any_summary(self):
        for private_request in (
            replace(request(), metadata={"Authorization": "Bearer synthetic-only"}),
            replace(request(), extensions={"Authorization": "Bearer synthetic-only"}),
        ):
            sink = Sink()
            provider = FakeProvider(response())
            with self.assertRaisesRegex(ValueError, "empty metadata/extensions"):
                self.runner(provider).run(provider_name="synthetic", request=private_request, limits=limits(),
                                          tool_choice_transition=policy(), event_sink=sink)
            self.assertEqual([], provider.requests)
            self.assertEqual([], sink.events)

    def test_summary_events_are_closed_and_contain_only_detached_primitives(self):
        sink = Sink()
        provider = FakeProvider(response(), response(tool=False))
        self.run_policy(provider, sink=sink)
        for kind, payload in sink.events:
            validate_summary_event(kind, payload)
            with self.assertRaisesRegex(ValueError, "closed"):
                validate_summary_event(kind, payload | {"raw": "forbidden"})
            changed = payload | {"policy_id": request()}
            with self.assertRaisesRegex(ValueError, "primitive"):
                validate_summary_event(kind, changed)
            with self.assertRaisesRegex(ValueError, "version"):
                validate_summary_event(kind, payload | {"summary_version": "2.0.0"})

    def test_summary_sink_cannot_mutate_original_request_or_tool_result(self):
        original = request()
        original_tool_result = {"value": "probe"}
        provider = FakeProvider(response(), response(tool=False))

        class MutatingSink(Sink):
            def record(self, kind, payload):
                super().record(kind, payload)
                self.assert_detached(payload)
                if kind == "request-summary":
                    object.__setattr__(original.messages[0].content[0], "text", "changed caller input")
                    payload["tool_choice_kind"] = "auto"
                if kind == "tool-result-summary":
                    original_tool_result["large"] = "x" * 1000
                    payload["status"] = "failed"

            @staticmethod
            def assert_detached(value):
                if isinstance(value, dict):
                    for item in value.values():
                        MutatingSink.assert_detached(item)
                elif isinstance(value, list):
                    for item in value:
                        MutatingSink.assert_detached(item)
                elif type(value) not in {str, int, float, bool, type(None)}:
                    raise AssertionError("runtime object leaked to sink")

        runner = self.runner(provider, handler=lambda arguments: original_tool_result)
        result = runner.run(provider_name="synthetic", request=original, limits=limits(),
                            tool_choice_transition=policy(), event_sink=MutatingSink())
        self.assertEqual(ApiSessionStatus.COMPLETED, result.status)
        self.assertEqual("probe", provider.requests[0].messages[0].content[0].text)
        self.assertEqual("specific", provider.requests[0].tool_choice.kind)
        self.assertEqual({"value": "probe"}, provider.requests[1].messages[-1].content[0].data["output"])

    def test_provider_reflective_history_and_choice_mutation_fails_before_tool(self):
        for target in ("history", "choice"):
            provider = FakeProvider(response())

            def mutate(actual):
                if target == "history":
                    object.__setattr__(actual.messages[0].content[0], "text", "changed provider input")
                else:
                    object.__setattr__(actual.tool_choice, "kind", "auto")

            provider.before_send = mutate
            result = self.run_policy(provider)
            self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
            self.assertEqual([], self.executed)
            self.assertEqual(1, len(provider.requests))

    def test_handler_argument_mutation_prevents_transition(self):
        provider = FakeProvider(response())

        def handler(arguments):
            dict.__setitem__(arguments, "value", "changed")
            return {"value": "probe"}

        result = self.run_policy(provider, handler=handler)
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual(1, result.tool_calls)
        self.assertEqual(1, len(provider.requests))

    def test_tool_capture_time_and_cancel_are_rechecked_before_history_assembly(self):
        for stop in ("time", "cancel"):
            state = {"time": 0, "cancel": False}

            class StoppingSink(Sink):
                def record(self, kind, payload):
                    super().record(kind, payload)
                    if kind == "tool-result-summary":
                        if stop == "time":
                            state["time"] = 31
                        else:
                            state["cancel"] = True

            provider = FakeProvider(response())
            sink = StoppingSink()
            result = self.run_policy(provider, sink=sink, clock=lambda: state["time"], cancelled=lambda: state["cancel"])
            self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
            self.assertEqual(1, len(provider.requests))
            self.assertFalse(any(k == "tool-context-summary" for k, _ in sink.events))

    def test_summary_archive_contains_no_raw_content_auth_ids_or_derived_hashes(self):
        marker = "SYNTHETIC-PRIVATE-AUTH-RAW-ID-WARNING"
        original = replace(request(),
            messages=(Message("user", (ContentBlock("text", text=marker + "-input"),)),),
        )
        first = replace(response(), response_id=marker + "-response-id",
                        tool_calls=(ToolCall(marker + "-call-id", "probe", {"value": marker + "-arguments"}),),
                        warnings=(marker + "-warning",), provider_metadata={"auth": marker})
        second = replace(response(tool=False, text=marker + "-output"), provider_metadata={"auth": marker})
        provider = FakeProvider(first, second)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "summary.jsonl"

            class SummaryArchive(Sink):
                def record(self, kind, payload):
                    super().record(kind, payload)
                    with destination.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps({"kind": kind, "payload": payload}, ensure_ascii=False) + "\n")

            result = self.runner(provider, handler=lambda arguments: {"raw": marker + "-tool-output"}).run(
                provider_name="synthetic", request=original, limits=limits(),
                tool_choice_transition=policy(), event_sink=SummaryArchive(),
            )
            self.assertEqual(ApiSessionStatus.COMPLETED, result.status)
            stored = destination.read_text(encoding="utf-8")
            self.assertNotIn(marker, stored)
            self.assertNotIn("Bearer", stored)
            for forbidden in ("request_sha256", "response_sha256", "arguments_sha256", "result_sha256", "call_id", "response_id", "provider_metadata"):
                self.assertNotIn(forbidden, stored)
            self.assertIn("policy_sha256", stored)


if __name__ == "__main__":
    unittest.main()
