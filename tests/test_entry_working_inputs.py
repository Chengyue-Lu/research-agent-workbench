"""Projection-only contracts; Root runs these tests before consumer integration."""
import copy
import hashlib
import json
import unittest
from collections.abc import Mapping
from pathlib import Path

from jsonschema import Draft202012Validator

from research_workbench.entry.working_inputs import (
    STOP_KINDS, WorkingInputError, project_working_input,
)

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    text = "讨论费用 budget 与 ledger 的研究问题；保留原文。\r\n"
    pin = {"path": "inputs/source.txt", "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    task = {
        "schema_version": "0.1.0", "task_id": "PROJECTION-001", "revision": 1,
        "goal": "Compare costs and budget assumptions; do not remove this user question.",
        "question_refs": ["Q-COST"], "active_modes": [], "agent_profile": "local-no-skill",
        "required_capabilities": [], "required_skills": [], "forbidden_skills": [],
        "input_refs": [pin], "write_scope": ["work/PROJECTION-001/**"],
        "required_outputs": [{"contract": "summary", "min_count": 1}],
        "permissions": {"filesystem": "worktree-write", "network": "forbidden",
                        "external_write": False, "allowed_roots": ["work/PROJECTION-001"]},
        "delegation": {"allowed": False, "sub_budget": {"max_turns": 1}},
        "budget": {"max_turns": 4, "max_output_tokens": 128, "max_seconds": 5},
        "atomic_boundary": "One cost discussion with pinned material.",
        "completion_checks": ["Return the requested comparison."],
        "safe_pause_conditions": ["legacy reserve exhausted"],
        "stop_conditions": ["legacy turn budget reached"], "stale_if": ["input changes"],
    }
    arguments = {"role": "main", "responsibilities": ["Compare the evidence; distinguish unknowns."],
                 "materials": [{**pin, "text": text}],
                 "stop_conditions": [{"kind": "cancelled", "condition": "Human cancels this work."}],
                 "necessary_decisions": [{"statement": "Method scope remains under human review.", "source_ref": pin}],
                 "counterevidence": [{"statement": "Cost evidence conflicts.", "source_ref": pin}]}
    return task, arguments


class _SelectiveTask(Mapping):
    """Trap accidental full serialization or access to economic metadata."""
    def __init__(self, task):
        self.task = task

    def __getitem__(self, key):
        if key in {"budget", "ledger", "policy", "caller_context"}:
            raise AssertionError("internal economic/control object accessed")
        return self.task[key]

    def __iter__(self):
        raise AssertionError("full Task iterated")

    def __len__(self):
        return len(self.task)


class WorkingInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = Draft202012Validator(json.loads(
            (ROOT / "schemas/v0.2.0/model-working-input.schema.json").read_text(encoding="utf-8")))

    def test_whitelist_preserves_user_cost_prose_and_exact_material_bytes(self):
        task, arguments = inputs()
        result = project_working_input(_SelectiveTask(task), **arguments)
        self.validator.validate(result)
        self.assertEqual(task["goal"], result["objective"]["goal"])
        self.assertEqual(arguments["materials"][0]["text"], result["materials"][0]["text"])
        self.assertEqual(task["input_refs"][0]["sha256"], result["materials"][0]["sha256"])
        self.assertEqual(task["permissions"], result["authority"]["permissions"])
        self.assertEqual({"allowed": False}, result["authority"]["delegation"])
        self.assertEqual(arguments["stop_conditions"], result["stop_conditions"])
        for key in ("task", "policy", "ledger", "budget", "caller_context"):
            self.assertNotIn(key, result)
        self.assertNotIn("legacy reserve exhausted", json.dumps(result))
        self.assertTrue(all(value is False for value in result["boundaries"].values()))

    def test_deterministic_projection_is_detached_from_source(self):
        task, arguments = inputs()
        before = copy.deepcopy((task, arguments))
        first = project_working_input(task, **arguments)
        second = project_working_input(task, **arguments)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        first["authority"]["permissions"]["allowed_roots"].append("extra")
        first["materials"][0]["text"] = "changed"
        self.assertEqual(before, (task, arguments))

    def test_economic_wrappers_are_not_model_fields(self):
        task, arguments = inputs()
        baseline = project_working_input(task, **arguments)
        task["budget"] = {"max_turns": 99999999}
        task["delegation"]["sub_budget"] = {"balance": 0, "held_tokens": 12}
        task["ledger"] = {"account_balance": 0, "internal_usage": "unknown"}
        task["policy"] = {"budget_ceiling": {"max_output_tokens": 1}}
        self.assertEqual(baseline, project_working_input(task, **arguments))

    def test_unknown_source_version_remains_unsupported(self):
        task, arguments = inputs()
        for version in ("0.2.0", "9.0.0", None, []):
            with self.subTest(version=version):
                task["schema_version"] = version
                with self.assertRaises(WorkingInputError):
                    project_working_input(task, **arguments)

    def test_stale_outside_duplicate_and_extra_snapshot_fields_are_rejected(self):
        task, arguments = inputs()
        changes = [
            [{**arguments["materials"][0], "text": "changed"}],
            [{**arguments["materials"][0], "path": "inputs/ungranted.txt"}],
            arguments["materials"] * 2,
            [{**arguments["materials"][0], "ledger": {"balance": 100}}],
            [{**arguments["materials"][0], "revision": 2}],
        ]
        for materials in changes:
            with self.subTest(materials=materials), self.assertRaises(WorkingInputError):
                project_working_input(task, **{**arguments, "materials": materials})

    def test_actual_stops_require_explicit_kind_without_keyword_filtering(self):
        task, arguments = inputs()
        for kind in STOP_KINDS:
            result = project_working_input(task, **{**arguments,
                "stop_conditions": [{"kind": kind, "condition": "Keep user cost discussion; no added quota."}]})
            self.validator.validate(result)
        for stops in ([], [{"kind": "balance-exhausted", "condition": "economic cap"}],
                      ["human cancelled"], [{"kind": [], "condition": "bad type"}]):
            with self.subTest(stops=stops), self.assertRaises(WorkingInputError):
                project_working_input(task, **{**arguments, "stop_conditions": stops})

    def test_decision_and_counterevidence_refs_cannot_expand_task_reads(self):
        task, arguments = inputs()
        record = {"statement": "ungranted evidence", "source_ref": {"path": "outside.txt", "sha256": "0" * 64}}
        for key in ("necessary_decisions", "counterevidence"):
            with self.subTest(key=key), self.assertRaises(WorkingInputError):
                project_working_input(task, **{**arguments, key: [record]})

    def test_projection_schema_rejects_economic_fields_and_authority_claims(self):
        task, arguments = inputs()
        result = project_working_input(task, **arguments)
        for key in ("budget", "ledger", "policy"):
            changed = copy.deepcopy(result)
            changed[key] = {}
            self.assertFalse(self.validator.is_valid(changed))
        for key in result["boundaries"]:
            changed = copy.deepcopy(result)
            changed["boundaries"][key] = True
            self.assertFalse(self.validator.is_valid(changed))

    def test_existing_task_schema_still_requires_legacy_budget(self):
        from research_workbench.validation.schemas import SchemaCatalog
        task, _ = inputs()
        catalog = SchemaCatalog(ROOT / "schemas", version="0.1.0")
        self.assertEqual([], catalog.validate("task_packet", task))
        del task["budget"]
        self.assertTrue(catalog.validate("task_packet", task))


if __name__ == "__main__":
    unittest.main()
