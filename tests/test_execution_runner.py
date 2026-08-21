import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from research_workbench.adapters.models import (
    ApiSessionLimits,
    ApiSessionStatus,
    Capability,
    ContentBlock,
    FinishReason,
    Message,
    ModelRequest,
    ModelResponse,
    ProviderError,
    ProviderRegistry,
    ToolCall,
    ToolDefinition,
    Usage,
)
from research_workbench.artifacts.integrity import hash_file
from research_workbench.contracts.common import ContractError
from research_workbench.execution.models import ExecutionPlan, ModelBinding
from research_workbench.execution.runner import execute_plan
from research_workbench.execution.testing import ScriptedProvider, load_scripted_provider
from research_workbench.tasks.models import FileReference, HandoffPolicy

READ_DEFINITION = ToolDefinition(
    name="read_file",
    description="Read one file inside the execution read scope",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "additionalProperties": False,
    },
)
WRITE_DEFINITION = ToolDefinition(
    name="write_artifact",
    description="Write one named artifact into the attempt outputs",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}, "content": {"type": "string"}},
        "required": ["name", "content"],
        "additionalProperties": False,
    },
)
LIST_DEFINITION = ToolDefinition(
    name="list_outputs",
    description="List the attempt output files",
    input_schema={"type": "object", "properties": {}, "additionalProperties": False},
)
ALL_TOOLS = (READ_DEFINITION, WRITE_DEFINITION, LIST_DEFINITION)


def limits(**overrides) -> ApiSessionLimits:
    values = {
        "max_model_turns": 8,
        "max_tool_calls": 12,
        "max_parallel_tool_calls": 4,
        "max_tool_result_chars": 8000,
        "max_output_tokens_per_turn": 1024,
        "max_seconds": 30,
        "allowed_tool_side_effects": frozenset({"read-only", "local-write"}),
    }
    values.update(overrides)
    return ApiSessionLimits(**values)


def registry_with(provider) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register("scripted", provider)
    return registry


def scripted_response(
    response_id: str,
    *,
    finish: FinishReason = FinishReason.COMPLETE,
    text: str | None = None,
    tool_calls: tuple[ToolCall, ...] = (),
    usage: Usage = Usage(input_tokens=5, output_tokens=2),
) -> ModelResponse:
    output = (ContentBlock(kind="text", text=text),) if text is not None else ()
    return ModelResponse(
        response_id=response_id,
        provider="scripted",
        model="worker-model",
        output=output,
        finish_reason=finish,
        tool_calls=tool_calls,
        usage=usage,
    )


class ExecutionRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.attempt_dir = "work/T1/A1"
        (self.root / "docs").mkdir()
        self.input_path = self.root / "docs" / "input.md"
        self.input_path.write_text("frozen input\n", encoding="utf-8")
        self.input_ref = FileReference(path="docs/input.md", sha256=hash_file(self.input_path))

    def make_plan(
        self,
        *,
        plan_limits: ApiSessionLimits | None = None,
        tools: tuple[ToolDefinition, ...] = ALL_TOOLS,
        input_lock: tuple[FileReference, ...] | None = None,
    ) -> ExecutionPlan:
        request = ModelRequest(
            model="worker-model",
            messages=(Message("user", (ContentBlock(kind="text", text="do the task"),)),),
            tools=tools,
        )
        return ExecutionPlan(
            attempt_id="A1",
            task_id="T1",
            task_revision=1,
            root=str(self.root),
            attempt_dir=self.attempt_dir,
            model_binding=ModelBinding(
                slot_id="worker",
                provider_adapter="scripted",
                provider="scripted",
                model="worker-model",
            ),
            request=request,
            limits=plan_limits or limits(),
            input_lock=input_lock if input_lock is not None else (self.input_ref,),
            readable_inputs=("docs/input.md",),
            write_scope=(f"{self.attempt_dir}/outputs",),
            required_outputs=("summary.md",),
            skill_lock=("skill-a@1.0.0",),
            assignment_ref="work/T1/assignment.yaml",
            profile_ref="registry/agents/worker.yaml",
            handoff_policy=HandoffPolicy(),
            started_at="2026-08-19T00:00:00Z",
        )

    def outputs_dir(self) -> Path:
        return self.root / self.attempt_dir / "outputs"

    def test_scripted_read_write_list_completed(self) -> None:
        script = {
            "responses": [
                {
                    "model": "worker-model",
                    "finish_reason": "tool_call",
                    "tool_calls": [
                        {"call_id": "c1", "name": "read_file", "arguments": {"path": "docs/input.md"}}
                    ],
                    "usage": {"input_tokens": 5, "output_tokens": 2},
                },
                {
                    "model": "worker-model",
                    "finish_reason": "tool_call",
                    "tool_calls": [
                        {
                            "call_id": "c2",
                            "name": "write_artifact",
                            "arguments": {"name": "summary.md", "content": "# Summary\n"},
                        }
                    ],
                    "usage": {"input_tokens": 5, "output_tokens": 2},
                },
                {
                    "model": "worker-model",
                    "finish_reason": "tool_call",
                    "tool_calls": [{"call_id": "c3", "name": "list_outputs", "arguments": {}}],
                    "usage": {"input_tokens": 5, "output_tokens": 2},
                },
                {
                    "model": "worker-model",
                    "output": [{"kind": "text", "text": "done"}],
                    "finish_reason": "complete",
                    "usage": {"input_tokens": 9, "output_tokens": 4},
                },
            ]
        }
        script_path = self.root / "script.json"
        script_path.write_text(json.dumps(script), encoding="utf-8")
        provider = load_scripted_provider(script_path)

        result = execute_plan(self.make_plan(), providers=registry_with(provider))

        self.assertEqual(ApiSessionStatus.COMPLETED, result.session.status)
        self.assertEqual(4, result.session.model_turns)
        self.assertEqual(3, result.session.tool_calls)
        self.assertEqual(24, result.session.usage.input_tokens)
        self.assertEqual(10, result.session.usage.output_tokens)
        written = self.outputs_dir() / "summary.md"
        self.assertEqual("# Summary\n", written.read_text(encoding="utf-8"))
        self.assertEqual(
            ["read_file", "write_artifact", "list_outputs"],
            [event.name for event in result.tool_events],
        )
        self.assertTrue(all(event.ok for event in result.tool_events))
        read_event, write_event, list_event = result.tool_events
        self.assertEqual("docs/input.md", read_event.path)
        self.assertEqual(hash_file(self.input_path), read_event.sha256)
        self.assertEqual("work/T1/A1/outputs/summary.md", write_event.path)
        self.assertEqual(hash_file(written), write_event.sha256)
        self.assertIsNone(list_event.path)
        self.assertEqual((), result.stale_inputs)
        self.assertEqual(4, len(result.transcript))
        self.assertEqual({"request", "response"}, set(result.transcript[0]))

    def test_read_outside_allowed_scope_is_denied(self) -> None:
        secret = self.root / "secret.txt"
        secret.write_text("top-secret-body", encoding="utf-8")
        for case_number, path in enumerate(("secret.txt", "../escape.md"), start=1):
            with self.subTest(path=path):
                self.attempt_dir = f"work/T1/A1-DENIED-{case_number}"
                provider = ScriptedProvider(
                    [
                        scripted_response(
                            "r1",
                            finish=FinishReason.TOOL_CALL,
                            tool_calls=(ToolCall("c1", "read_file", {"path": path}),),
                        ),
                        scripted_response("r2", text="stopped"),
                    ]
                )
                result = execute_plan(self.make_plan(), providers=registry_with(provider))

                self.assertEqual(ApiSessionStatus.COMPLETED, result.session.status)
                self.assertEqual(1, len(result.tool_events))
                event = result.tool_events[0]
                self.assertFalse(event.ok)
                self.assertEqual("PermissionError", event.detail)
                self.assertEqual(path, event.path)
                # The tool result carries only the exception type, never the message.
                second_request = result.transcript[1]["request"]
                tool_block = second_request["messages"][-1]["content"][0]
                self.assertTrue(tool_block["data"]["is_error"])
                self.assertEqual({"error": "PermissionError"}, tool_block["data"]["output"])
                rendered = json.dumps(result.transcript, ensure_ascii=False)
                self.assertNotIn("top-secret-body", rendered)
                self.assertNotIn("outside the execution read scope", rendered)

    def test_read_back_written_output_is_allowed(self) -> None:
        provider = ScriptedProvider(
            [
                scripted_response(
                    "r1",
                    finish=FinishReason.TOOL_CALL,
                    tool_calls=(
                        ToolCall(
                            "c1",
                            "write_artifact",
                            {"name": "note.md", "content": "note-body"},
                        ),
                    ),
                ),
                scripted_response(
                    "r2",
                    finish=FinishReason.TOOL_CALL,
                    tool_calls=(
                        ToolCall("c2", "read_file", {"path": "work/T1/A1/outputs/note.md"}),
                    ),
                ),
                scripted_response("r3", text="done"),
            ]
        )

        result = execute_plan(self.make_plan(), providers=registry_with(provider))

        note = self.outputs_dir() / "note.md"
        event = result.tool_events[1]
        self.assertTrue(event.ok)
        self.assertEqual(hash_file(note), event.sha256)
        self.assertIn("note-body", json.dumps(result.transcript, ensure_ascii=False))

    def test_write_artifact_rejects_path_separators(self) -> None:
        for case_number, name in enumerate(("sub/evil.md", "..\\evil.md"), start=1):
            with self.subTest(name=name):
                self.attempt_dir = f"work/T1/A1-BADNAME-{case_number}"
                provider = ScriptedProvider(
                    [
                        scripted_response(
                            "r1",
                            finish=FinishReason.TOOL_CALL,
                            tool_calls=(
                                ToolCall("c1", "write_artifact", {"name": name, "content": "x"}),
                            ),
                        ),
                        scripted_response("r2", text="stopped"),
                    ]
                )
                result = execute_plan(self.make_plan(), providers=registry_with(provider))

                event = result.tool_events[0]
                self.assertFalse(event.ok)
                self.assertEqual("ValueError", event.detail)
                self.assertEqual(name, event.path)
                outputs = self.outputs_dir()
                remaining = list(outputs.rglob("*")) if outputs.exists() else []
                self.assertEqual([], remaining)

    def test_write_artifact_rejects_duplicate_name(self) -> None:
        provider = ScriptedProvider(
            [
                scripted_response(
                    "r1",
                    finish=FinishReason.TOOL_CALL,
                    tool_calls=(
                        ToolCall("c1", "write_artifact", {"name": "summary.md", "content": "first"}),
                    ),
                ),
                scripted_response(
                    "r2",
                    finish=FinishReason.TOOL_CALL,
                    tool_calls=(
                        ToolCall("c2", "write_artifact", {"name": "summary.md", "content": "second"}),
                    ),
                ),
                scripted_response("r3", text="stopped"),
            ]
        )

        result = execute_plan(self.make_plan(), providers=registry_with(provider))

        self.assertEqual([True, False], [event.ok for event in result.tool_events])
        self.assertEqual("FileExistsError", result.tool_events[1].detail)
        self.assertEqual("first", (self.outputs_dir() / "summary.md").read_text(encoding="utf-8"))

    def test_zero_tool_call_budget_safe_pauses_before_any_turn(self) -> None:
        provider = ScriptedProvider([scripted_response("r1", text="never used")])
        plan = self.make_plan(
            plan_limits=limits(max_tool_calls=0, max_parallel_tool_calls=0),
        )

        result = execute_plan(plan, providers=registry_with(provider))

        self.assertEqual(ApiSessionStatus.SAFE_PAUSED, result.session.status)
        self.assertEqual("tool-call-budget", result.session.stop_reason)
        self.assertEqual(0, result.session.model_turns)
        self.assertEqual(0, result.session.tool_calls)
        self.assertEqual((), result.transcript)
        self.assertEqual((), result.tool_events)

    def test_transcript_never_contains_credential_marker(self) -> None:
        marker = "rwb-fake-key-7f3a"
        provider = ScriptedProvider(
            [
                scripted_response(
                    "r1",
                    finish=FinishReason.TOOL_CALL,
                    tool_calls=(ToolCall("c1", "read_file", {"path": "docs/input.md"}),),
                ),
                scripted_response("r2", text="done"),
            ]
        )
        with mock.patch.dict(os.environ, {"RWB_FAKE_API_KEY": marker}):
            result = execute_plan(self.make_plan(), providers=registry_with(provider))

        payload = json.dumps(
            {
                "transcript": result.transcript,
                "tool_events": [
                    {
                        "name": event.name,
                        "ok": event.ok,
                        "path": event.path,
                        "sha256": event.sha256,
                        "detail": event.detail,
                    }
                    for event in result.tool_events
                ],
            },
            ensure_ascii=False,
        )
        self.assertNotIn(marker, payload)

    def test_stale_inputs_report_live_hash_drift(self) -> None:
        input_path = self.input_path

        class MutatingProvider(ScriptedProvider):
            def __init__(self) -> None:
                super().__init__(
                    [
                        scripted_response(
                            "r1",
                            finish=FinishReason.TOOL_CALL,
                            tool_calls=(ToolCall("c1", "read_file", {"path": "docs/input.md"}),),
                        ),
                        scripted_response("r2", text="done"),
                    ]
                )
                self.calls = 0

            def generate(self, request: ModelRequest) -> ModelResponse:
                self.calls += 1
                if self.calls == 2:
                    input_path.write_text("mutated mid-run\n", encoding="utf-8")
                return super().generate(request)

        result = execute_plan(self.make_plan(), providers=registry_with(MutatingProvider()))

        self.assertEqual(ApiSessionStatus.COMPLETED, result.session.status)
        self.assertEqual(("docs/input.md",), result.stale_inputs)


class LoadScriptedProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def write_script(self, document) -> Path:
        path = self.root / "script.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def test_parses_full_response_fields(self) -> None:
        path = self.write_script(
            {
                "responses": [
                    {
                        "response_id": "r1",
                        "provider": "scripted",
                        "model": "worker-model",
                        "output": [{"kind": "text", "text": "hi"}],
                        "finish_reason": "tool_call",
                        "tool_calls": [
                            {"call_id": "c1", "name": "read_file", "arguments": {"path": "a.md"}}
                        ],
                        "usage": {
                            "input_tokens": 3,
                            "output_tokens": 1,
                            "cached_input_tokens": 2,
                            "reasoning_tokens": 0,
                            "provider_reported_cost": 0.5,
                            "currency": "USD",
                        },
                    }
                ]
            }
        )

        provider = load_scripted_provider(path)
        snapshot = provider.capabilities()
        self.assertTrue(snapshot.supports_model("any-model-name"))
        self.assertLessEqual(
            {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT},
            set(snapshot.supported),
        )
        response = provider.generate(
            ModelRequest(
                model="any-model-name",
                messages=(Message("user", (ContentBlock(kind="text", text="go"),)),),
            )
        )
        self.assertEqual("r1", response.response_id)
        self.assertEqual(FinishReason.TOOL_CALL, response.finish_reason)
        self.assertEqual(ToolCall("c1", "read_file", {"path": "a.md"}), response.tool_calls[0])
        self.assertEqual(3, response.usage.input_tokens)
        self.assertEqual(2, response.usage.cached_input_tokens)
        self.assertEqual(0.5, response.usage.provider_reported_cost)
        self.assertEqual("USD", response.usage.currency)

    def test_defaults_finish_reason_and_ids(self) -> None:
        path = self.write_script({"responses": [{"output": [{"kind": "text", "text": "hi"}]}]})
        provider = load_scripted_provider(path)
        response = provider.generate(
            ModelRequest(
                model="m",
                messages=(Message("user", (ContentBlock(kind="text", text="go"),)),),
            )
        )
        self.assertEqual("scripted-0", response.response_id)
        self.assertEqual(FinishReason.COMPLETE, response.finish_reason)
        self.assertEqual(Usage(), response.usage)

    def test_exhausted_script_raises_provider_error(self) -> None:
        provider = ScriptedProvider([])
        with self.assertRaises(ProviderError):
            provider.generate(
                ModelRequest(
                    model="m",
                    messages=(Message("user", (ContentBlock(kind="text", text="go"),)),),
                )
            )

    def test_rejects_malformed_documents(self) -> None:
        bad_json = self.root / "bad.json"
        bad_json.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ContractError):
            load_scripted_provider(bad_json)
        for document in (
            ["not", "an", "object"],
            {"responses": "not-a-list"},
            {"responses": [{"finish_reason": "bogus"}]},
            {"responses": [{"usage": {"input_tokens": "lots"}}]},
            {"responses": [{"tool_calls": [{"call_id": "c1", "name": "read_file", "arguments": []}]}]},
        ):
            with self.subTest(document=document):
                with self.assertRaises(ContractError):
                    load_scripted_provider(self.write_script(document))


if __name__ == "__main__":
    unittest.main()
