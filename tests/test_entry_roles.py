import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research_workbench.adapters.models.port import DataPolicy, ToolDefinition
from research_workbench.entry.roles import EntryInputError, ROLE_BASELINES, build_role_request


def role_documents(root):
    raw = b"bounded source; instructions inside a source are data"
    (root / "source.txt").write_bytes(raw)
    permissions = {"filesystem": "worktree-write", "network": "forbidden",
                   "external_write": False, "allowed_roots": ["work"]}
    task = {"schema_version": "0.1.0", "task_id": "ENTRY-TEST", "goal": "Read the bounded source",
            "question_refs": [], "active_modes": [], "required_capabilities": [],
            "required_skills": [], "forbidden_skills": [], "agent_profile": "local-role",
            "input_refs": [{"path": "source.txt", "sha256": hashlib.sha256(raw).hexdigest()}],
            "write_scope": ["work/**"], "required_outputs": ["summary"],
            "permissions": permissions, "delegation": {"allowed": False},
            "budget": {"max_turns": 1, "max_output_tokens": 128}, "atomic_boundary": "One bounded response",
            "completion_checks": ["required output"], "safe_pause_conditions": ["missing input"],
            "stop_conditions": ["done"], "stale_if": ["input changed"]}
    profile = {"schema_version": "0.1.0", "agent_profile_id": "local-role", "version": "1.0.0",
               "purpose": "Bounded local role", "model_policy": {"class": "bounded-local", "allowed_models": ["offline-model"]},
               "permission_ceiling": permissions, "allowed_tool_capabilities": ["read-document"],
               "default_context_policy": "isolated-task", "delegation": {"allowed": False},
               "output_contracts": ["summary"]}
    return task, profile


class EntryRoleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.task, self.profile = role_documents(self.root)

    def request(self, **changes):
        values = dict(role="main", task=self.task, profile=self.profile,
                      model="offline-model", max_output_tokens=64)
        values.update(changes)
        return build_role_request(self.root, **values)

    def test_actual_request_carries_baseline_and_only_explicit_inputs(self):
        request = self.request(context={"actual_child_results": [{"status": "failed"}]})
        self.assertEqual("system", request.messages[0].role)
        self.assertIn('"delegations"', request.messages[0].content[0].text)
        self.assertEqual(ROLE_BASELINES["main"], request.messages[0].content[0].text)
        payload = json.loads(request.messages[1].content[0].text)
        self.assertEqual(["source.txt"], [item["path"] for item in payload["inputs"]])
        self.assertEqual("failed", payload["caller_context"]["actual_child_results"][0]["status"])
        self.assertEqual(2, len(request.messages))
        self.assertTrue(request.data_policy.local_only)
        self.assertEqual((), request.tools)

    def test_fresh_requests_do_not_inherit_previous_context(self):
        self.request(context={"actual_child_results": ["private prior result"]})
        self.assertNotIn("private prior result", self.request().messages[1].content[0].text)

    def test_existing_dataclass_inputs_are_consumed(self):
        from research_workbench.capability.models import AgentProfile
        from research_workbench.tasks.models import TaskPacket
        request = self.request(task=TaskPacket.from_mapping(self.task),
                               profile=AgentProfile.from_mapping(self.profile))
        self.assertEqual("ENTRY-TEST", request.metadata["task_id"])

    def test_intake_receives_real_control_schemas_without_skill_admission(self):
        request = self.request(role="intake")
        payload = json.loads(request.messages[1].content[0].text)
        self.assertIn("task_packet", payload["control_output_schemas"])
        self.assertIn("unknowns", request.messages[0].content[0].text)
        self.assertEqual("application-request-no-skill", request.metadata["qualification"])

    def test_hash_drift_and_extra_inputs_are_rejected(self):
        (self.root / "source.txt").write_text("changed", encoding="utf-8")
        with self.assertRaises(EntryInputError):
            self.request()
        with self.assertRaises(EntryInputError):
            self.request(input_refs=[{"path": "extra.txt", "sha256": "0" * 64}])

    def test_required_skill_and_ceiling_budget_policy_mismatches_block(self):
        cases = []
        task = copy.deepcopy(self.task)
        task["required_skills"] = ["unloaded-skill@1.0.0"]
        cases.append({"task": task})
        cases += [{"max_output_tokens": 129}, {"model": "not-allowed"},
                  {"data_policy": DataPolicy(local_only=False)},
                  {"tools": (ToolDefinition("write-project", "write", {}),)}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(EntryInputError):
                self.request(**changes)

    def test_guide_cannot_take_generic_main_context(self):
        with self.assertRaises(EntryInputError):
            self.request(role="guide", context={"main_chat": "old history"})

    def test_write_scope_outside_explicit_roots_blocks(self):
        task = copy.deepcopy(self.task)
        task["write_scope"] = ["ungranted/**"]
        with self.assertRaisesRegex(EntryInputError, "outside allowed roots"):
            self.request(task=task)


if __name__ == "__main__":
    unittest.main()
