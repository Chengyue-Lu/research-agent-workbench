from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from research_workbench.adapters.models import (
    Capability,
    ContentBlock,
    DataPolicy,
    FinishReason,
    Message,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderError,
    ResponseFormat,
    ToolCall,
    ToolChoice,
    ToolDefinition,
)
from research_workbench.adapters.models import base as base_module
from research_workbench.adapters.models import http as http_module
from research_workbench.adapters import CodexRuntimeAdapter
from research_workbench.capability import AcceptedSkillRegistry, AgentProfile, resolve_task_from_registry
from research_workbench.io import load_document
from research_workbench.tasks import TaskPacket


ROOT = Path(__file__).resolve().parents[1]


def _tool(name: str = "lookup") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="bounded lookup",
        input_schema={
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
            "additionalProperties": False,
        },
    )


def _request(**changes: object) -> ModelRequest:
    values = {
        "model": "model-a",
        "messages": (Message("user", (ContentBlock("text", text="hello"),)),),
    }
    values.update(changes)
    return ModelRequest(**values)


def _snapshot(**changes: object) -> ProviderCapabilities:
    values = {
        "provider": "test",
        "adapter_version": "1",
        "supported": frozenset(Capability),
        "models": ("model-a",),
        "deployment": "remote",
        "regions": frozenset({"us"}),
        "data_controls": frozenset({"zero_data_retention", "training_opt_out"}),
    }
    values.update(changes)
    return ProviderCapabilities(**values)


class ProviderPreflightBranchTests(unittest.TestCase):
    def test_capability_and_preflight_invalid_matrix_is_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            base_module.validate_adapter_capabilities(
                frozenset({Capability.TEXT, Capability.STREAMING}),
                frozenset({Capability.TEXT}),
                "test",
            )
        with self.assertRaises(ValueError):
            base_module.validate_adapter_capabilities(frozenset(), frozenset(), "test")

        bad_schema = {"type": "not-a-json-schema-type"}
        cases = (
            (_request(model="other"), _snapshot()),
            (_request(capability_requirements=frozenset({Capability.STREAMING})), _snapshot(supported=frozenset({Capability.TEXT}))),
            (_request(data_policy=DataPolicy(local_only=True)), _snapshot()),
            (_request(messages=()), _snapshot()),
            (_request(response_format=ResponseFormat(kind="xml")), _snapshot()),
            (_request(response_format=ResponseFormat(kind="json_schema")), _snapshot()),
            (_request(response_format=ResponseFormat(kind="json_schema", name="bad", schema=bad_schema)), _snapshot()),
            (_request(tool_choice=ToolChoice("sometimes")), _snapshot()),
            (_request(tools=(_tool(),), tool_choice=ToolChoice("specific")), _snapshot()),
            (_request(tools=(_tool(),), tool_choice=ToolChoice("specific", "other")), _snapshot()),
            (_request(tools=(_tool(),), tool_choice=ToolChoice("none", "lookup")), _snapshot()),
            (_request(tool_choice=ToolChoice("required")), _snapshot()),
            (_request(max_output_tokens=0), _snapshot()),
            (_request(temperature=3), _snapshot()),
            (_request(tools=(replace(_tool(), name=""),)), _snapshot()),
            (_request(tools=(_tool(), _tool())), _snapshot()),
            (_request(tools=(replace(_tool(), input_schema=bad_schema),)), _snapshot()),
            (_request(messages=(Message("unknown", (ContentBlock("text", text="x"),)),)), _snapshot()),
            (_request(messages=(Message("user", ()),)), _snapshot()),
            (_request(messages=(Message("user", (ContentBlock("text"),)),)), _snapshot()),
            (_request(messages=(Message("assistant", (ContentBlock("tool_call", data=None),)),)), _snapshot()),
            (_request(messages=(Message("assistant", (ContentBlock("tool_call", data={"call_id": "", "name": "lookup", "arguments": {}}),)),)), _snapshot()),
            (_request(messages=(Message("assistant", (ContentBlock("tool_call", data={"call_id": "1", "name": "lookup", "arguments": []}),)),)), _snapshot()),
            (_request(messages=(Message("tool", (ContentBlock("tool_result", data={"call_id": ""}),)),)), _snapshot()),
        )
        for request, snapshot in cases:
            with self.subTest(request=request):
                with self.assertRaises((ProviderError, ValueError)):
                    base_module.preflight(request, snapshot)

    def test_extensions_error_categories_and_response_contract_are_explicit(self) -> None:
        self.assertEqual({}, base_module.provider_extension(_request(), "test"))
        with self.assertRaises(ProviderError):
            base_module.provider_extension(_request(extensions={"other": {}}), "test")
        with self.assertRaises(ProviderError):
            base_module.provider_extension(_request(extensions={"test": "bad"}), "test")
        expected = {
            401: ("authentication", False),
            403: ("permission", False),
            429: ("rate_limit", True),
            408: ("transient", True),
            500: ("transient", True),
            400: ("invalid_request", False),
            200: ("unknown", False),
        }
        for status, result in expected.items():
            category, retryable = base_module.generic_error_category(status)
            self.assertEqual(result, (category.value, retryable))

        tool = _tool()
        request = _request(tools=(tool,))
        response = ModelResponse("r", "test", "model-a", (), FinishReason.COMPLETE)
        self.assertIs(response, base_module.validate_response_contract(request, response))
        bad_calls = (
            (ToolCall("1", "lookup", {"id": "a"}), ToolCall("1", "lookup", {"id": "b"})),
            (ToolCall("1", "other", {}),),
            (ToolCall("1", "lookup", {}),),
        )
        for calls in bad_calls:
            with self.assertRaises(ProviderError):
                base_module.validate_response_contract(replace(request, tool_choice=ToolChoice("required")), replace(response, tool_calls=calls))
        with self.assertRaises(ProviderError):
            base_module.validate_response_contract(
                replace(request, tool_choice=ToolChoice("none")),
                replace(response, tool_calls=(ToolCall("1", "lookup", {"id": "a"}),)),
            )
        with self.assertRaises(ProviderError):
            base_module.validate_response_contract(
                replace(request, tool_choice=ToolChoice("required")), response
            )
        with self.assertRaises(ProviderError):
            base_module.validate_response_contract(
                replace(request, tool_choice=ToolChoice("specific", "lookup"), tools=(tool, _tool("other"))),
                replace(response, tool_calls=(ToolCall("1", "other", {"id": "a"}),)),
            )
        with self.assertRaises(ProviderError):
            base_module.validate_response_contract(
                request, replace(response, finish_reason=FinishReason.TOOL_CALL)
            )

        structured = _request(response_format=ResponseFormat(
            "json_schema", "result", {"type": "object", "required": ["value"], "properties": {"value": {"type": "string"}}}
        ))
        for text in ("not-json", '{"value": 1}'):
            with self.assertRaises(ProviderError):
                base_module.validate_structured_response(
                    structured,
                    replace(response, output=(ContentBlock("text", text=text),)),
                )
        self.assertEqual("value", base_module.text_from_output("value"))
        self.assertEqual('{"value":1}', base_module.text_from_output({"value": 1}))
        with self.assertRaises(ProviderError):
            base_module.reject_unknown_extension_keys({"bad": True}, provider="test", allowed=frozenset())
        with self.assertRaises(ProviderError):
            base_module.require_object([], provider="test", field="item")
        with self.assertRaises(ProviderError):
            base_module.require_list({}, provider="test", field="items")


class HttpTransportBranchTests(unittest.TestCase):
    def test_credentials_json_and_bounded_transport_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            http_module.EnvironmentCredential("bad-name")
        credential = http_module.EnvironmentCredential("RWB_TEST_SECRET")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(credential.available())
            with self.assertRaises(http_module.CredentialUnavailable):
                credential.resolve()
        with mock.patch.dict(os.environ, {"RWB_TEST_SECRET": "secret"}, clear=True):
            self.assertTrue(credential.available())
            self.assertEqual("secret", credential.resolve())
        with self.assertRaises(ValueError):
            http_module.decode_json_object(b"not-json", provider="test")
        with self.assertRaises(ValueError):
            http_module.decode_json_object(b"[]", provider="test")
        self.assertEqual({"a": 1}, http_module.decode_json_object(b'{"a":1}', provider="test"))
        with self.assertRaises(ValueError):
            http_module.UrllibTransport(max_response_bytes=0)
        transport = http_module.UrllibTransport(max_response_bytes=3)
        request = http_module.HttpRequest("POST", "http://example.test", {}, b"")
        with self.assertRaises(http_module.HttpTransportError):
            transport.send(request)
        oversized = SimpleNamespace(read=lambda _size: b"four")
        with self.assertRaises(http_module.HttpTransportError):
            transport._read_bounded(oversized)


class CodexAdapterBranchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        cls.profile = AgentProfile.from_mapping(load_document(ROOT / "registry/agents/evidence-scout.yaml"))
        cls.registry = AcceptedSkillRegistry.load(project_root=ROOT)
        cls.assignment = resolve_task_from_registry(
            cls.task, cls.profile, cls.registry, resolution_purpose="historical-replay"
        )

    def test_capability_probe_and_layout_diagnostics_are_content_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter = CodexRuntimeAdapter(root, platform_version="test")
            self.assertEqual(("missing .codex/agents", "missing .agents/skills"), adapter.validate_project_layout())
            self.assertIsNone(adapter.capabilities().max_concurrent_threads)

            agent_root = root / ".codex/agents"
            skill_root = root / ".agents/skills/empty"
            agent_root.mkdir(parents=True)
            skill_root.mkdir(parents=True)
            (root / ".codex/config.toml").write_text(
                "[agents]\nmax_concurrent_threads_per_session = 3\n", encoding="utf-8"
            )
            (agent_root / "bad.toml").write_text("not = [valid", encoding="utf-8")
            (skill_root / "SKILL.md").write_bytes(b"")
            issues = adapter.validate_project_layout()
            self.assertTrue(any("invalid TOML" in item for item in issues))
            self.assertTrue(any("empty Skill" in item for item in issues))
            self.assertEqual(3, adapter.capabilities().max_concurrent_threads)

    def test_agent_and_skill_binding_reject_missing_duplicate_and_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agent_root = root / ".codex/agents"
            agent_root.mkdir(parents=True)
            adapter = CodexRuntimeAdapter(root)
            with self.assertRaisesRegex(ValueError, "expected one"):
                adapter.resolve_agent(self.profile)
            valid = (
                'name = "evidence_scout"\n'
                'description = "bounded"\n'
                'developer_instructions = "follow task"\n'
            )
            (agent_root / "a.toml").write_text(valid, encoding="utf-8")
            (agent_root / "b.toml").write_text(valid, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "found 2"):
                adapter.resolve_agent(self.profile)
            (agent_root / "b.toml").unlink()
            (agent_root / "a.toml").write_text(
                'name = "evidence_scout"\ndescription = ""\ndeveloper_instructions = "x"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "lacks required field"):
                adapter.resolve_agent(self.profile)

            lock = self.assignment.skill_lock[0]
            for changed, message in (
                (replace(lock, source_locator=None), "no source locator"),
                (replace(lock, source_locator="missing/SKILL.md"), "missing or outside"),
            ):
                with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                    adapter.resolve_skills(replace(self.assignment, skill_lock=(changed,)))

            source = root / str(lock.source_locator)
            source.parent.mkdir(parents=True)
            source.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source drift"):
                adapter.resolve_skills(self.assignment)
            shutil.copytree(
                ROOT / ".agents/skills/literature-evidence-extraction",
                source.parent,
                dirs_exist_ok=True,
            )
            drifted_package = replace(lock, package_hash="0" * 64)
            with self.assertRaisesRegex(ValueError, "package drift"):
                adapter.resolve_skills(replace(self.assignment, skill_lock=(drifted_package,)))


if __name__ == "__main__":
    unittest.main()
