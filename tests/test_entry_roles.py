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
        self.assertEqual("main", payload["role"])
        self.assertEqual(["source.txt"], [item["path"] for item in payload["inputs"]])
        self.assertEqual("failed", payload["caller_context"]["actual_child_results"][0]["status"])
        self.assertEqual(2, len(request.messages))
        self.assertTrue(request.data_policy.local_only)
        self.assertEqual((), request.tools)

    def test_verified_input_snapshot_and_baseline_explain_existing_read(self):
        request = self.request()
        baseline = request.messages[0].content[0].text
        user_text = request.messages[1].content[0].text
        payload = json.loads(user_text)
        raw = (self.root / "source.txt").read_bytes()
        expected_hash = hashlib.sha256(raw).hexdigest()
        self.assertEqual([{"path": "source.txt", "sha256": expected_hash,
                           "revision": None, "text": raw.decode("utf-8")}], payload["inputs"])
        self.assertEqual(self.task["input_refs"][0]["sha256"], expected_hash)
        self.assertEqual(hashlib.sha256(user_text.encode("utf-8")).hexdigest(),
                         request.metadata["input_snapshot_sha256"])
        self.assertEqual(hashlib.sha256(baseline.encode("utf-8")).hexdigest(),
                         request.metadata["baseline_sha256"])
        for role, role_baseline in ROLE_BASELINES.items():
            with self.subTest(role=role):
                self.assertIn("caller actually read from Task.input_refs", role_baseline)
                self.assertIn("verified against its SHA-256", role_baseline)
                self.assertIn("decoded from those same UTF-8 bytes", role_baseline)
                self.assertIn("pinned revisions are checked when present", role_baseline)
                self.assertIn("Use inputs[].text as already read input", role_baseline)
                self.assertIn("no independent file open or local file tool", role_baseline)
                self.assertIn("no additional file access, automatic reference traversal or write authority", role_baseline)
                self.assertIn("A list of refs does not mean those files have been opened", role_baseline)
                self.assertIn("only to payload.inputs, not arbitrary caller_context", role_baseline)

    def test_driver_publication_baseline_is_conditional_and_pending(self):
        publication = {"publisher": "SessionExecutionDriver", "status": "pending",
                       "output_path": "work/role.json", "output_contract": "summary",
                       "boundaries": {"permission_grant": False, "publication_complete": False}}
        request = self.request(context={"driver_output_publication": publication})
        payload = json.loads(request.messages[1].content[0].text)
        baseline = request.messages[0].content[0].text
        self.assertEqual(publication, payload["caller_context"]["driver_output_publication"])
        self.assertEqual((), request.tools)
        self.assertIn("Only when caller_context provides driver_output_publication", baseline)
        self.assertIn("pending metadata, not permission or completed publication", baseline)
        self.assertIn("A missing file-write tool does not by itself block returning that text", baseline)
        self.assertIn("Do not claim publication success without a real Receipt", baseline)
        self.assertIn("actual permission or I/O failures still require stopping", baseline)
        self.assertIn("Without this record, assume no Driver publication", baseline)
        self.assertIn("unequal strings alone establish neither permission nor failure", baseline)
        self.assertIsNone(json.loads(self.request().messages[1].content[0].text)["caller_context"])

    def test_fresh_requests_do_not_inherit_previous_context(self):
        self.request(context={"actual_child_results": ["private prior result"]})
        self.assertNotIn("private prior result", self.request().messages[1].content[0].text)

    def test_consuming_main_identity_is_visible_with_reused_child_profile(self):
        parent = copy.deepcopy(self.task)
        parent["task_id"] = "ENTRY-PARENT"
        child = copy.deepcopy(self.task)
        child["task_id"] = "ENTRY-REVIEW-CHILD"
        child_request = self.request(role="child", task=child,
            context={"phase": "plan-or-execute", "child_results": []})
        # Only request assembly is exercised here; no Handoff admission or
        # scientific independence is claimed by this supplied context fixture.
        supplied = {"phase": "consume-child-results", "child_results": [{
            "task_id": child["task_id"], "summary": "Child Task observation.",
            "disposition": "complete"}]}
        original = copy.deepcopy(supplied)
        request = self.request(role="main", task=parent, context=supplied)
        payload = json.loads(request.messages[1].content[0].text)
        child_payload = json.loads(child_request.messages[1].content[0].text)
        self.assertEqual("main", payload["role"])
        self.assertEqual("child", child_payload["role"])
        self.assertEqual(parent["task_id"], payload["task"]["task_id"])
        self.assertEqual(child["task_id"], child_payload["task"]["task_id"])
        self.assertEqual(payload["profile"], child_payload["profile"])
        self.assertEqual("consume-child-results", payload["caller_context"]["phase"])
        self.assertEqual(child["task_id"], payload["caller_context"]["child_results"][0]["task_id"])
        self.assertEqual(original, payload["caller_context"])
        self.assertEqual(original, supplied)
        self.assertEqual(2, len(request.messages))
        self.assertEqual((), request.tools)
        self.assertIn("are not your own previous response", request.messages[0].content[0].text)
        self.assertIn("same Profile does not identify the same Task or API session", request.messages[0].content[0].text)
        self.assertIn("do not establish scientific independence", request.messages[0].content[0].text)
        self.assertIn("Further delegation remains your decision", request.messages[0].content[0].text)
        self.assertIsNone(json.loads(self.request().messages[1].content[0].text)["caller_context"])

    def test_child_receives_own_task_snapshot_without_delegation_or_prior_results(self):
        task = copy.deepcopy(self.task)
        task["delegation"] = {"allowed": False, "max_depth": 0, "max_parallel": 0}
        request = self.request(role="child", task=task,
                               context={"phase": "plan-or-execute", "child_results": []})
        payload = json.loads(request.messages[1].content[0].text)
        self.assertEqual("child", payload["role"])
        self.assertFalse(payload["task"]["delegation"]["allowed"])
        self.assertEqual([], payload["caller_context"]["child_results"])
        self.assertEqual((self.root / "source.txt").read_bytes().decode("utf-8"),
                         payload["inputs"][0]["text"])
        self.assertIn("does not prohibit executing this Task directly", request.messages[0].content[0].text)
        self.assertEqual("child", request.metadata["entry_role"])

    def test_existing_dataclass_inputs_are_consumed(self):
        from research_workbench.capability.models import AgentProfile
        from research_workbench.tasks.models import TaskPacket
        request = self.request(task=TaskPacket.from_mapping(self.task),
                               profile=AgentProfile.from_mapping(self.profile))
        self.assertEqual("ENTRY-TEST", request.metadata["task_id"])

    def test_intake_receives_real_control_schemas_without_skill_admission(self):
        request = self.request(role="intake")
        payload = json.loads(request.messages[1].content[0].text)
        self.assertEqual("intake", payload["role"])
        self.assertIn("task_packet", payload["control_output_schemas"])
        self.assertIn("unknowns", request.messages[0].content[0].text)
        self.assertIsNone(payload["caller_context"])
        self.assertIn("intake uses its own draft compiler", request.messages[0].content[0].text)
        self.assertEqual("application-request-no-skill", request.metadata["qualification"])

    def test_main_receives_child_contract_and_only_actual_profile_identity(self):
        request = self.request(role="main")
        payload = json.loads(request.messages[1].content[0].text)
        schema = payload["delegation_output_schemas"]["task_packet"]
        self.assertIn("forbidden_skills", schema["required"])
        self.assertIn("common", payload["delegation_output_schemas"])
        self.assertEqual([self.profile["agent_profile_id"]], payload["available_agent_profiles"])

    def test_hash_drift_and_extra_inputs_are_rejected(self):
        (self.root / "source.txt").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(EntryInputError, "input hash mismatch"):
            self.request()
        with self.assertRaisesRegex(EntryInputError, "outside Task exact read set"):
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

    def test_visible_guide_identity_keeps_read_only_request_without_main_context(self):
        guide_task = copy.deepcopy(self.task)
        guide_task["permissions"]["filesystem"] = "read-only"
        request = self.request(role="guide", task=guide_task)
        payload = json.loads(request.messages[1].content[0].text)
        self.assertEqual("guide", payload["role"])
        self.assertEqual((), request.tools)
        self.assertIsNone(payload["caller_context"])
        self.assertIsNone(payload["caller_instructions"])
        self.assertNotIn("delegation_output_schemas", payload)
        self.assertNotIn("control_output_schemas", payload)
        self.assertEqual(ROLE_BASELINES["guide"], request.messages[0].content[0].text)

    def test_write_scope_outside_explicit_roots_blocks(self):
        task = copy.deepcopy(self.task)
        task["write_scope"] = ["ungranted/**"]
        with self.assertRaisesRegex(EntryInputError, "outside allowed roots"):
            self.request(task=task)


if __name__ == "__main__":
    unittest.main()
