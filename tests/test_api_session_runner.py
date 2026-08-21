import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

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
    ProviderErrorCategory,
    ProviderRegistry,
    ToolCall,
    ToolDefinition,
    Usage,
)
from research_workbench.observability.trace import AgentTraceRecorder, validate_attempt_trace
from research_workbench.execution import run_traced_session


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


class FailingProvider(ScriptedProvider):
    """Plays scripted responses, then raises one fixed ProviderError."""

    def __init__(self, error: ProviderError, *responses: ModelResponse) -> None:
        super().__init__(*responses)
        self.error = error

    def generate(self, request: ModelRequest) -> ModelResponse:
        if self.responses:
            return super().generate(request)
        self.requests.append(request)
        raise self.error


class RecordingSink:
    def __init__(self, fail_once_on: str | None = None) -> None:
        self.events: list[tuple[str, object]] = []
        self.fail_once_on = fail_once_on

    def record(self, kind: str, payload) -> None:
        if self.fail_once_on == kind:
            self.fail_once_on = None
            raise OSError(f"injected {kind} persistence failure")
        self.events.append((kind, payload))


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
    def trace_recorder(self, root: Path) -> AgentTraceRecorder:
        return AgentTraceRecorder(
            root / "work/SESSION-TRACE/AT-0001",
            task_id="SESSION-TRACE",
            task_revision=1,
            attempt_id="AT-0001",
            task_snapshot={"task_id": "SESSION-TRACE", "revision": 1},
            accountable_owner="Huang Yi",
            actor_id="runtime-session-test",
            runtime_identity="isolated-api-session-test",
            provider="fake",
            read_allowlist=("inputs/**",),
            write_scope=("outputs/**",),
            tool_allowlist=("lookup",),
        )

    def test_real_trace_sink_captures_tool_loop_before_context_delivery(self) -> None:
        provider = ScriptedProvider(
            response(
                "r1",
                FinishReason.TOOL_CALL,
                tool_calls=(ToolCall("call-1", "lookup", {"id": "A"}),),
            ),
            response("r2", FinishReason.COMPLETE, text="done"),
        )
        registry = ProviderRegistry()
        registry.register("worker", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {"value": 7}),),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = self.trace_recorder(root)
            result = runner.run(
                provider_name="worker",
                request=request(),
                limits=limits(),
                event_sink=recorder,
            )
            recorder.seal(result.status.value)
            validation = validate_attempt_trace(root, recorder.attempt_dir)
            self.assertFalse(validation.blocked, validation.risks)
            events = [
                json.loads(line)
                for line in (recorder.attempt_dir / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            tool_results = [
                event
                for event in events
                if event["event_type"] == "tool-call"
                and event["payload"]["status"] == "succeeded"
            ]
            self.assertEqual(1, len(tool_results))
            self.assertTrue(tool_results[0]["payload"]["result_entered_context"])
            self.assertEqual(1, len(list((recorder.attempt_dir / "tool-events").iterdir())))

    def test_traced_wrapper_creates_archive_before_provider_and_seals_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt_dir = root / "work/SESSION-TRACE/AT-WRAPPED"

            class InspectingProvider(ScriptedProvider):
                def generate(self, request: ModelRequest) -> ModelResponse:
                    self.assert_archive_exists()
                    return super().generate(request)

                @staticmethod
                def assert_archive_exists() -> None:
                    for name in ("TASK.yaml", "ACTORS.yaml", "INDEX.yaml", "events.jsonl"):
                        if not (attempt_dir / name).exists():
                            raise AssertionError(f"missing pre-provider Trace artifact: {name}")

            provider = InspectingProvider(
                response("r1", FinishReason.COMPLETE, text="done")
            )
            registry = ProviderRegistry()
            registry.register("worker", provider)
            runner = IsolatedApiSessionRunner(
                registry,
                tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
            )
            result = run_traced_session(
                root=root,
                attempt_dir=attempt_dir,
                task_id="SESSION-TRACE",
                task_revision=1,
                attempt_id="AT-WRAPPED",
                task_snapshot={"task_id": "SESSION-TRACE", "revision": 1},
                accountable_owner="Huang Yi",
                agent_profile_id="evidence-scout",
                provider_name="worker",
                request=request(),
                limits=limits(),
                session_runner=runner,
                read_allowlist=("inputs/**",),
                write_scope=("outputs/**",),
                tool_allowlist=("lookup",),
            )
            self.assertEqual(ApiSessionStatus.COMPLETED, result.session.status)
            self.assertEqual("work/SESSION-TRACE/AT-WRAPPED/INDEX.yaml", result.trace_ref.path)
            self.assertFalse(validate_attempt_trace(root, attempt_dir).blocked)

    def test_traced_wrapper_blocks_request_capture_failure_before_provider(self) -> None:
        provider = ScriptedProvider(response("r1", FinishReason.COMPLETE, text="done"))
        registry = ProviderRegistry()
        registry.register("worker", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )
        original_record = AgentTraceRecorder.record

        def fail_request_capture(self, kind, payload):
            if kind == "provider-request":
                raise OSError("injected request capture failure")
            return original_record(self, kind, payload)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attempt_dir = root / "work/SESSION-TRACE/AT-CAPTURE-FAIL"
            with patch.object(AgentTraceRecorder, "record", new=fail_request_capture):
                with self.assertRaises(OSError):
                    run_traced_session(
                        root=root,
                        attempt_dir=attempt_dir,
                        task_id="SESSION-TRACE",
                        task_revision=1,
                        attempt_id="AT-CAPTURE-FAIL",
                        task_snapshot={"task_id": "SESSION-TRACE", "revision": 1},
                        accountable_owner="Huang Yi",
                        agent_profile_id="evidence-scout",
                        provider_name="worker",
                        request=request(),
                        limits=limits(),
                        session_runner=runner,
                        read_allowlist=("inputs/**",),
                        write_scope=("outputs/**",),
                        tool_allowlist=("lookup",),
                    )
            self.assertEqual([], provider.requests)
            index = yaml.safe_load((attempt_dir / "INDEX.yaml").read_text(encoding="utf-8"))
            self.assertEqual("blocked", index["attempt_status"])
            self.assertEqual("frozen", index["trace_status"])

    def test_traced_wrapper_requires_owner_and_project_bounded_attempt(self) -> None:
        registry = ProviderRegistry()
        registry.register("worker", ScriptedProvider())
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            arguments = {
                "root": root,
                "attempt_dir": root / "work/A",
                "task_id": "T",
                "task_revision": 1,
                "attempt_id": "A",
                "task_snapshot": {"task_id": "T", "revision": 1},
                "accountable_owner": "",
                "agent_profile_id": "profile",
                "provider_name": "worker",
                "request": request(),
                "limits": limits(),
                "session_runner": runner,
                "read_allowlist": (),
                "write_scope": (),
                "tool_allowlist": ("lookup",),
            }
            with self.assertRaisesRegex(ValueError, "accountable_owner"):
                run_traced_session(**arguments)
            arguments["accountable_owner"] = "Huang Yi"
            arguments["attempt_dir"] = root.parent / "outside-attempt"
            with self.assertRaisesRegex(ValueError, "project root"):
                run_traced_session(**arguments)

    def test_oversized_tool_result_is_not_falsely_marked_as_delivered(self) -> None:
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
            tools=(ClientTool(lookup_definition(), lambda arguments: "too-large"),),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = self.trace_recorder(root)
            result = runner.run(
                provider_name="worker",
                request=request(),
                limits=limits(max_tool_result_chars=2),
                event_sink=recorder,
            )
            recorder.seal(result.status.value)
            self.assertEqual("tool-result-size-budget", result.stop_reason)
            events = [
                json.loads(line)
                for line in (recorder.attempt_dir / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            result_event = next(
                event
                for event in events
                if event["event_type"] == "tool-call"
                and event["payload"]["status"] == "succeeded"
            )
            self.assertFalse(result_event["payload"]["result_entered_context"])
            self.assertNotIn("result_ref", result_event["payload"])
            self.assertFalse(validate_attempt_trace(root, recorder.attempt_dir).blocked)

    def test_request_capture_failure_blocks_before_provider_call(self) -> None:
        provider = ScriptedProvider(response("r1", FinishReason.COMPLETE, text="done"))
        registry = ProviderRegistry()
        registry.register("worker", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )
        with self.assertRaises(OSError):
            runner.run(
                provider_name="worker",
                request=request(),
                limits=limits(),
                event_sink=RecordingSink("provider-request"),
            )
        self.assertEqual([], provider.requests)

    def test_post_provider_capture_failure_records_gap_and_safe_pauses(self) -> None:
        provider = ScriptedProvider(response("r1", FinishReason.COMPLETE, text="done"))
        registry = ProviderRegistry()
        registry.register("worker", provider)
        sink = RecordingSink("provider-response")
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )
        result = runner.run(
            provider_name="worker",
            request=request(),
            limits=limits(),
            event_sink=sink,
        )
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("trace-capture-gap", result.stop_reason)
        self.assertEqual(1, len(provider.requests))
        self.assertEqual(
            ["provider-request", "capture-gap", "session-status"],
            [kind for kind, _ in sink.events],
        )

    def test_capture_gap_failure_propagates_and_forbids_closeout(self) -> None:
        class BrokenSink:
            def record(self, kind: str, payload) -> None:
                if kind in {"provider-response", "capture-gap"}:
                    raise OSError("trace storage unavailable")

        provider = ScriptedProvider(response("r1", FinishReason.COMPLETE, text="done"))
        registry = ProviderRegistry()
        registry.register("worker", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )
        with self.assertRaises(OSError):
            runner.run(
                provider_name="worker",
                request=request(),
                limits=limits(),
                event_sink=BrokenSink(),
            )
        self.assertEqual(1, len(provider.requests))

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

    def test_cancellation_before_first_turn_makes_no_provider_call(self) -> None:
        provider = ScriptedProvider(response("r1", FinishReason.COMPLETE, text="done"))
        registry = ProviderRegistry()
        registry.register("worker", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )
        result = runner.run(
            provider_name="worker",
            request=request(),
            limits=limits(),
            cancel_requested=lambda: True,
        )
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("cancellation-requested", result.stop_reason)
        self.assertEqual([], provider.requests)

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

    def test_provider_error_fails_session_and_preserves_partial_state(self) -> None:
        provider = FailingProvider(
            ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "fake returned invalid JSON for structured output",
            ),
            response(
                "r1",
                FinishReason.TOOL_CALL,
                tool_calls=(ToolCall("call-1", "lookup", {"id": "A"}),),
            ),
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

        self.assertEqual(ApiSessionStatus.FAILED, result.status)
        self.assertEqual("provider-error:contract_violation", result.stop_reason)
        self.assertEqual(1, result.model_turns)
        self.assertEqual(1, result.tool_calls)
        self.assertEqual(["A"], seen)
        self.assertTrue(any("contract_violation" in warning for warning in result.warnings))

    def test_provider_cancellation_is_a_safe_pause_not_a_failure(self) -> None:
        provider = FailingProvider(
            ProviderError(ProviderErrorCategory.CANCELLED, "cancelled by deadline")
        )
        registry = ProviderRegistry()
        registry.register("worker", provider)
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )
        result = runner.run(provider_name="worker", request=request(), limits=limits())
        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.status)
        self.assertEqual("provider-cancelled", result.stop_reason)

    def test_unexpected_provider_exception_is_bounded_and_content_free(self) -> None:
        class ExplodingProvider(ScriptedProvider):
            def generate(self, request: ModelRequest) -> ModelResponse:
                self.requests.append(request)
                raise RuntimeError("sensitive provider response must not escape")

        provider = ExplodingProvider()
        registry = ProviderRegistry()
        registry.register("worker", provider)
        sink = RecordingSink()
        runner = IsolatedApiSessionRunner(
            registry,
            tools=(ClientTool(lookup_definition(), lambda arguments: {}),),
        )
        result = runner.run(
            provider_name="worker",
            request=request(),
            limits=limits(),
            event_sink=sink,
        )
        self.assertEqual(ApiSessionStatus.FAILED, result.status)
        self.assertEqual("provider-exception:RuntimeError", result.stop_reason)
        self.assertNotIn("sensitive provider response", str(result.warnings))
        self.assertEqual(
            ["provider-request", "session-status"],
            [kind for kind, _ in sink.events],
        )


if __name__ == "__main__":
    unittest.main()
