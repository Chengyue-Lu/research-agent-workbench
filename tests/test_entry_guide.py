import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research_workbench.adapters.models.port import (
    Capability, ContentBlock, FinishReason, ModelResponse, ProviderCapabilities,
    ProviderRegistry, ToolCall, Usage,
)
from research_workbench.entry.guide import ask_guide, build_guide_request
from research_workbench.entry.roles import EntryInputError
from research_workbench.tasks.models import FileReference


class OfflineGuideProvider:
    def capabilities(self):
        return ProviderCapabilities("offline-guide", "test-only", frozenset({Capability.TEXT}),
                                    models=("offline-model",), deployment="local")

    def generate(self, request):
        self.request = request
        return ModelResponse("guide-test", "offline-guide", "offline-model",
                             (ContentBlock("text", text="MainState is waiting."),), FinishReason.COMPLETE,
                             tool_calls=(ToolCall("unexpected", "write-state", {}),),
                             usage=Usage(input_tokens=None, output_tokens=9))


class EntryGuideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        state = {"schema_version": "0.1.0", "checkpoint_id": "CP-GUIDE", "continuity_status": "waiting",
                 "project_protocol_ref": "project-protocol.json", "current_questions": [], "pinned_constraints": [],
                 "accepted_decisions": [], "active_tasks": [], "recent_handoffs": [], "open_conflicts": [],
                 "open_risks": ["human review pending"], "next_actions": ["ask human"], "artifact_index_refs": [],
                 "machine_state_refs": [{"path": "not-approved.json", "sha256": "0" * 64}]}
        raw = json.dumps(state).encode("utf-8")
        (self.root / "main-state.json").write_bytes(raw)
        self.ref = FileReference("main-state.json", hashlib.sha256(raw).hexdigest())
        (self.root / "main-chat.txt").write_text("private old main history", encoding="utf-8")

    def test_guide_only_consumes_approved_snapshot_without_following_refs(self):
        request = build_guide_request(self.root, question="Why waiting?", main_state_ref=self.ref,
                                      model="offline-model")
        self.assertEqual((), request.tools)
        self.assertEqual(2, len(request.messages))
        payload = json.loads(request.messages[1].content[0].text)
        self.assertEqual(["main-state.json"], [item["path"] for item in payload["approved_inputs"]])
        self.assertNotIn("private old main history", request.messages[1].content[0].text)
        self.assertFalse((self.root / "not-approved.json").exists())

    def test_injected_call_returns_unknown_usage_and_does_not_write_or_execute_tools(self):
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        provider, registry = OfflineGuideProvider(), ProviderRegistry()
        registry.register("offline-guide", provider)
        response = ask_guide(self.root, providers=registry, provider_name="offline-guide",
                             question="Explain the checkpoint", main_state_ref=self.ref, model="offline-model")
        self.assertEqual(9, response.usage.output_tokens)
        self.assertIsNone(response.usage.input_tokens)
        self.assertEqual((), provider.request.tools)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.root.iterdir()})

    def test_bad_pin_and_invalid_mainstate_block_before_provider_call(self):
        with self.assertRaises(EntryInputError):
            build_guide_request(self.root, question="Explain", main_state_ref=FileReference(self.ref.path, "0" * 64),
                                model="offline-model")
        raw = b"{}"
        (self.root / "main-state.json").write_bytes(raw)
        with self.assertRaises(EntryInputError):
            build_guide_request(self.root, question="Explain", main_state_ref=FileReference(self.ref.path, hashlib.sha256(raw).hexdigest()),
                                model="offline-model")


if __name__ == "__main__":
    unittest.main()
