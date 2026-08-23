from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.adapters.models import (
    ApiSessionLimits,
    Capability,
    ClientTool,
    ContentBlock,
    FinishReason,
    IsolatedApiSessionRunner,
    Message,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderRegistry,
    ToolCall,
    ToolDefinition,
)
from research_workbench.artifacts.integrity import hash_file
from research_workbench.execution import (
    TraceReconstructionError,
    reconstruct_last_provider_request,
)
from research_workbench.observability.trace import AgentTraceRecorder, TRACE_INDEX_FILENAME


class ScriptedProvider:
    def __init__(self, *responses: ModelResponse) -> None:
        self.responses = list(responses)
        self.requests: list[ModelRequest] = []

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider="fake",
            adapter_version="0",
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
            models=("worker-model",),
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return self.responses.pop(0)


def _limits() -> ApiSessionLimits:
    return ApiSessionLimits(
        max_model_turns=4,
        max_tool_calls=2,
        max_parallel_tool_calls=2,
        max_tool_result_chars=2000,
        max_output_tokens_per_turn=500,
        max_seconds=30.0,
    )


def _recorder(attempt_dir: Path) -> AgentTraceRecorder:
    return AgentTraceRecorder(
        attempt_dir,
        task_id="REC-001",
        task_revision=1,
        attempt_id=attempt_dir.name,
        task_snapshot={"task_id": "REC-001", "revision": 1},
        accountable_owner="Huang Yi",
        actor_id=f"runtime-{attempt_dir.name}",
        runtime_identity="reconstruction-test",
        provider="fake",
        read_allowlist=("work/**",),
        write_scope=("work/**",),
        tool_allowlist=("lookup",),
    )


def lookup_tool() -> ClientTool:
    return ClientTool(
        definition=ToolDefinition(
            name="lookup",
            description="Look up one bounded record",
            input_schema={
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
                "additionalProperties": False,
            },
        ),
        execute=lambda arguments: {"id": arguments["id"], "title": "bounded record"},
    )


def _base_request() -> ModelRequest:
    return ModelRequest(
        model="worker-model",
        messages=(
            Message("system", (ContentBlock(kind="text", text="bounded fixture"),)),
            Message("user", (ContentBlock(kind="text", text="resolve the record"),)),
        ),
        tools=(
            ToolDefinition(
                name="lookup",
                description="Look up one bounded record",
                input_schema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"],
                    "additionalProperties": False,
                },
            ),
        ),
        max_output_tokens=500,
        capability_requirements=frozenset({Capability.TEXT}),
    )


class RequestReconstructionTests(unittest.TestCase):
    def test_round_trip_through_traced_session(self) -> None:
        provider = ScriptedProvider(
            ModelResponse(
                response_id="resp-1",
                provider="fake",
                model="worker-model",
                output=(ContentBlock(kind="text", text="calling tool"),),
                finish_reason=FinishReason.TOOL_CALL,
                tool_calls=(ToolCall("call-1", "lookup", {"id": "r-1"}),),
            ),
            ModelResponse(
                response_id="resp-2",
                provider="fake",
                model="worker-model",
                output=(ContentBlock(kind="text", text="resolved"),),
                finish_reason=FinishReason.COMPLETE,
            ),
        )
        registry = ProviderRegistry()
        registry.register("fake", provider)
        runner = IsolatedApiSessionRunner(registry, tools=(lookup_tool(),))

        with tempfile.TemporaryDirectory() as raw:
            attempt_dir = Path(raw) / "AT-REC-1"
            recorder = _recorder(attempt_dir)
            result = runner.run(
                provider_name="fake",
                request=_base_request(),
                limits=_limits(),
                event_sink=recorder,
            )
            recorder.seal()

            self.assertEqual(result.status.value, "completed")
            self.assertEqual(len(provider.requests), 2)

            reconstructed = reconstruct_last_provider_request(attempt_dir)
            # The reconstructed request is exactly what the provider received last:
            # the base request plus the assistant tool-call turn and the tool result.
            self.assertEqual(reconstructed.request, provider.requests[-1])
            self.assertTrue(reconstructed.message_id.startswith("MSG-"))
            self.assertIn("provider-request", reconstructed.message_path)
            self.assertEqual(len(reconstructed.request.messages), 4)
            self.assertEqual(reconstructed.request.messages[-1].role, "tool")

    def test_last_provider_request_wins(self) -> None:
        provider = ScriptedProvider(
            ModelResponse(
                response_id="resp-1",
                provider="fake",
                model="worker-model",
                output=(ContentBlock(kind="text", text="first"),),
                finish_reason=FinishReason.LENGTH,
            ),
        )
        registry = ProviderRegistry()
        registry.register("fake", provider)
        runner = IsolatedApiSessionRunner(registry, tools=(lookup_tool(),))

        with tempfile.TemporaryDirectory() as raw:
            attempt_dir = Path(raw) / "AT-REC-2"
            recorder = _recorder(attempt_dir)
            runner.run(
                provider_name="fake",
                request=_base_request(),
                limits=_limits(),
                event_sink=recorder,
            )
            recorder.seal()

            index = yaml.safe_load((attempt_dir / TRACE_INDEX_FILENAME).read_text(encoding="utf-8"))
            provider_requests = [
                entry for entry in index["messages"] if entry["kind"] == "provider-request"
            ]
            self.assertEqual(len(provider_requests), 1)

            reconstructed = reconstruct_last_provider_request(attempt_dir)
            self.assertEqual(reconstructed.request, provider.requests[-1])
            self.assertEqual(
                reconstructed.file_sha256,
                hash_file(attempt_dir / reconstructed.message_path),
            )

    def test_trace_without_provider_request_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            attempt_dir = Path(raw) / "AT-REC-3"
            recorder = _recorder(attempt_dir)
            recorder.seal()

            with self.assertRaises(TraceReconstructionError) as caught:
                reconstruct_last_provider_request(attempt_dir)
            self.assertIn("no provider-request", str(caught.exception))

    def test_tampered_message_file_is_rejected(self) -> None:
        provider = ScriptedProvider(
            ModelResponse(
                response_id="resp-1",
                provider="fake",
                model="worker-model",
                output=(ContentBlock(kind="text", text="done"),),
                finish_reason=FinishReason.COMPLETE,
            ),
        )
        registry = ProviderRegistry()
        registry.register("fake", provider)
        runner = IsolatedApiSessionRunner(registry, tools=(lookup_tool(),))

        with tempfile.TemporaryDirectory() as raw:
            attempt_dir = Path(raw) / "AT-REC-4"
            recorder = _recorder(attempt_dir)
            runner.run(
                provider_name="fake",
                request=_base_request(),
                limits=_limits(),
                event_sink=recorder,
            )
            recorder.seal()

            index_path = attempt_dir / TRACE_INDEX_FILENAME
            index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
            entry = [item for item in index["messages"] if item["kind"] == "provider-request"][0]
            message_path = attempt_dir / entry["path"]

            # Tamper with the body but repair the whole-file hash in the index:
            # the envelope content hash must still refuse the forgery.
            content = message_path.read_bytes()
            header, separator, body = content[4:].partition(b"---\n")
            forged = body.replace(b'"resolve the record"', b'"resolve the tampered record"')
            message_path.write_bytes(b"---\n" + header + separator + forged)
            entry["sha256"] = hash_file(message_path)
            index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")

            with self.assertRaises(TraceReconstructionError) as caught:
                reconstruct_last_provider_request(attempt_dir)
            self.assertIn("content hash mismatch", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
