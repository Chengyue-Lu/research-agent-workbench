import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research_workbench.entry.intake import compile_control_draft, persist_control_draft
from research_workbench.entry.roles import EntryInputError
from research_workbench.io import load_document


def control_documents():
    protocol = {"schema_version": "0.1.0", "project_id": "bounded-project", "question_refs": [],
                "active_modes": [], "claim_ceiling": ["unresolved"], "required_human_gates": ["claim-acceptance"],
                "budgets": {"max_parallel_subagents": 0, "max_delegation_depth": 0, "coordination_cost_ratio_warn": 0.2},
                "context_policy": {"proactive_checkpoint": True, "main_raw_material": "on-demand"},
                "data_boundary": {"local_only": True, "external_upload_requires_approval": True}}
    task = {"schema_version": "0.1.0", "task_id": "CONTROL-TEST", "goal": "Bounded formatting",
            "question_refs": [], "active_modes": [], "required_capabilities": [], "required_skills": [],
            "forbidden_skills": [], "agent_profile": "local-role", "input_refs": [], "write_scope": ["work/**"],
            "required_outputs": ["summary"], "permissions": {"filesystem": "worktree-write", "network": "forbidden",
                "external_write": False, "allowed_roots": ["work"]}, "delegation": {"allowed": False},
            "budget": {"max_turns": 2, "max_output_tokens": 128}, "atomic_boundary": "One draft",
            "completion_checks": ["schema validation"], "safe_pause_conditions": ["unknown"],
            "stop_conditions": ["complete"], "stale_if": []}
    return protocol, task


class EntryIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.protocol, self.task = control_documents()
        self.payload = {"protocol": copy.deepcopy(self.protocol), "task": copy.deepcopy(self.task),
                        "unknowns": ["human scientific acceptance remains unknown"]}

    def compile(self, payload=None):
        return compile_control_draft(self.root, response=payload or self.payload,
                                     protocol_ceiling=self.protocol, task_ceiling=self.task)

    def test_publish_exact_draft_files_and_preserve_unknown_without_approval(self):
        draft = self.compile()
        with self.assertRaises(TypeError):
            draft.task["goal"] = "changed"
        refs = persist_control_draft(self.root, directory="drafts/first", draft=draft)
        for ref in refs:
            self.assertEqual(ref.sha256, hashlib.sha256((self.root / ref.path).read_bytes()).hexdigest())
        manifest = json.loads((self.root / "drafts/first/draft.json").read_text(encoding="utf-8"))
        self.assertEqual("draft", manifest["status"])
        self.assertEqual(list(draft.unknowns), manifest["unknowns"])
        with self.assertRaises(FileExistsError):
            persist_control_draft(self.root, directory="drafts/first", draft=draft)

    def test_model_cannot_expand_human_boundaries(self):
        changes = [lambda p: p["task"]["permissions"].update(network="allowed"),
                   lambda p: p["task"]["budget"].update(max_output_tokens=129),
                   lambda p: p["task"].update(write_scope=["elsewhere/**"]),
                   lambda p: p["task"]["delegation"].update(allowed=True),
                   lambda p: p["protocol"]["data_boundary"].update(local_only=False),
                   lambda p: p["protocol"].update(required_human_gates=[]),
                   lambda p: p["protocol"].update(claim_ceiling=["validated"]),
                   lambda p: p["task"].update(stop_conditions=["different stop"]),
                   lambda p: p["task"].update(revision=2)]
        for change in changes:
            payload = copy.deepcopy(self.payload)
            change(payload)
            with self.subTest(payload=payload), self.assertRaises(EntryInputError):
                self.compile(payload)

    def test_missing_schema_fields_and_duplicate_json_keys_fail(self):
        payload = copy.deepcopy(self.payload)
        del payload["task"]["stop_conditions"]
        with self.assertRaises(EntryInputError):
            self.compile(payload)
        with self.assertRaises(EntryInputError):
            compile_control_draft(self.root, response='{"unknowns":[],"unknowns":[]}',
                                  protocol_ceiling=self.protocol, task_ceiling=self.task)

    def test_method_pin_is_computed_from_published_task_bytes(self):
        method = load_document(Path(__file__).resolve().parents[1] / "examples/method-resolutions/ROUTE-NO-MODE-FORMAT-007.yaml")
        method["task_ref"] = {"task_id": self.task["task_id"], "revision": 1, "sha256": "invented"}
        payload = copy.deepcopy(self.payload)
        payload["method"] = method
        refs = persist_control_draft(self.root, directory="method-draft", draft=self.compile(payload))
        task_ref = next(ref for ref in refs if ref.path.endswith("/task.json"))
        published = json.loads((self.root / "method-draft/method.json").read_text(encoding="utf-8"))
        self.assertEqual(task_ref.sha256, published["task_ref"]["sha256"])

    def test_method_version_ref_matches_existing_protocol_mode_id(self):
        self.protocol["active_modes"] = ["evidence-synthesis"]
        self.task["active_modes"] = ["evidence-synthesis"]
        payload = {"protocol": copy.deepcopy(self.protocol), "task": copy.deepcopy(self.task), "unknowns": []}
        method = load_document(Path(__file__).resolve().parents[1] / "examples/method-resolutions/ROUTE-NO-MODE-FORMAT-007.yaml")
        method["task_ref"] = {"task_id": self.task["task_id"], "revision": 1}
        method["mode_resolution"].update(status="selected", selected_mode_refs=["evidence-synthesis@0.2.0"])
        payload["method"] = method
        self.assertEqual("evidence-synthesis@0.2.0", self.compile(payload).method["mode_resolution"]["selected_mode_refs"][0])
        method["mode_resolution"]["selected_mode_refs"] = ["simulation@0.2.0"]
        with self.assertRaisesRegex(EntryInputError, "Method modes"):
            self.compile(payload)

    def test_pin_drift_before_publication_and_root_escape_do_not_publish(self):
        raw = b"frozen"
        (self.root / "source.txt").write_bytes(raw)
        ref = {"path": "source.txt", "sha256": hashlib.sha256(raw).hexdigest()}
        self.task["input_refs"] = [ref]
        self.payload["task"]["input_refs"] = [ref]
        draft = self.compile()
        (self.root / "source.txt").write_text("changed", encoding="utf-8")
        with self.assertRaises(EntryInputError):
            persist_control_draft(self.root, directory="changed-draft", draft=draft)
        self.assertFalse((self.root / "changed-draft").exists())
        with self.assertRaises(ValueError):
            persist_control_draft(self.root, directory="../outside", draft=draft)

    def test_optional_requirement_is_validated_and_cannot_enable_data_egress(self):
        requirement = {"schema_version": "0.1.0", "requirement_id": "bounded-read", "objective": "Read bounded data",
                       "applies_when": ["explicit input"], "not_applicable_when": ["missing input"],
                       "required_inputs": ["source"], "required_outputs": ["summary"], "required_artifacts": ["summary"],
                       "constraints": {"permission_ceiling": {"filesystem": "read-only", "network": "forbidden", "external_write": False},
                           "data_egress": {"policy": "forbidden", "allowed_payloads": [], "forbidden_payloads": ["raw-source"]},
                           "side_effects": {"policy": "none", "allowed_effects": []}},
                       "verification_expectations": {"deterministic": ["pins"], "semantic": [], "human": []},
                       "unsatisfied_requirement": {"method_contract": "unchanged", "supply_binding": "prohibited", "next_stage": "capability-resolution"}}
        payload = copy.deepcopy(self.payload)
        payload["requirements"] = [requirement]
        draft = self.compile(payload)
        self.assertEqual("bounded-read", draft.requirements[0]["requirement_id"])
        requirement["constraints"]["data_egress"].update(policy="allowlisted-only", allowed_payloads=["raw-source"])
        with self.assertRaisesRegex(EntryInputError, "data egress"):
            self.compile(payload)


if __name__ == "__main__":
    unittest.main()
