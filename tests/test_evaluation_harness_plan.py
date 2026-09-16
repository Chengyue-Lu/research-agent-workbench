"""Frozen schedules, input isolation and coherent tampering counterexamples."""

import copy
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from research_workbench.evaluation.harness_plan import (
    compile_harness_plan,
    validate_harness_plan,
)
from research_workbench.evaluation.pins import EvaluationValidationError, digest
from research_workbench.validation.document_kinds import infer_document_kind
from tests.harness_fixtures import HarnessFixtureMixin
from tests.system_evaluation_fixtures import AT, ROOT


class HarnessPlanTests(HarnessFixtureMixin, unittest.TestCase):
    def reject_plan(self, document, **context):
        with self.assertRaises(EvaluationValidationError):
            validate_harness_plan(
                self.f.inputs(), document, **(self.f.plan_context() | context)
            )

    def test_plan_is_nonexecuting_canonical_and_replays(self):
        plan = self.f.compile_plan(public_cases=list(reversed(self.f.public_cases)))
        self.assertEqual(plan, self.f.plan)
        self.assertEqual(infer_document_kind(plan), "evaluation_harness_plan")
        self.assertEqual(
            plan, validate_harness_plan(self.f.inputs(), plan, **self.f.plan_context())
        )
        self.assertEqual(
            len(plan["blocks"]), 8
        )  # two cases, one pilot and three confirmatory replicates
        slots = [
            slot
            for b in plan["blocks"]
            for a in b["arms"]
            for slot in a["attempt_slots"]
        ]
        self.assertEqual(len(slots), 64)
        self.assertEqual(len({s["attempt_id"] for s in slots}), len(slots))
        self.assertEqual(len({s["session_id"] for s in slots}), len(slots))
        self.assertFalse(any(plan["boundaries"].values()))
        self.assertNotIn("primary_confirmatory_eligible", json.dumps(plan))
        other = self.f.compile_plan(run_id="SYNTHETIC-RUN-2")
        self.assertNotEqual(
            plan["blocks"][0]["arms"][0]["attempt_slots"],
            other["blocks"][0]["arms"][0]["attempt_slots"],
        )

    def test_permutation_has_stable_cross_process_vector(self):
        expected = [a["arm_id"] for a in self.f.plan["blocks"][0]["arms"]]
        # Fixed vector pins algorithm behavior, not just two copies of this implementation.
        self.assertEqual(
            expected,
            [
                "plain-agent-tool",
                "plain-agent",
                "mode-no-skill",
                "mode-candidate-skill",
            ],
        )
        code = """import json,sys
from research_workbench.evaluation.pins import EvaluationInputs
from research_workbench.evaluation.harness_plan import compile_harness_plan
request=json.loads(sys.argv[3])
print(json.dumps(compile_harness_plan(EvaluationInputs(sys.argv[1],sys.argv[2]),**request),sort_keys=True))"""
        for seed in ("7", "991"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            result = subprocess.check_output(
                [
                    sys.executable,
                    "-c",
                    code,
                    str(self.f.root),
                    str(ROOT / "schemas"),
                    json.dumps(self.f.plan["request"]),
                ],
                env=env,
                text=True,
            )
            self.assertEqual(json.loads(result), self.f.plan)

    def test_phase_is_not_eligibility_and_unknown_authority_fields_fail(self):
        for container, key, value in (
            ("root", "primary_confirmatory_eligible", True),
            ("block", "primary_confirmatory_eligible", True),
            ("root", "actual_execution", True),
            ("request", "arm_override", {}),
        ):
            candidate = copy.deepcopy(self.f.plan)
            target = (
                candidate
                if container == "root"
                else (
                    candidate["request"]
                    if container == "request"
                    else candidate["blocks"][-1]
                )
            )
            target[key] = value
            self.reject_plan(candidate)

    def test_schedule_and_retry_tampering_cannot_rewrite_derived_plan(self):
        for mutation in (
            lambda p: p["blocks"][0]["arms"].reverse(),
            lambda p: p["blocks"].pop(),
            lambda p: p["blocks"][0].update(phase="confirmatory"),
            lambda p: p["blocks"][0]["arms"][0]["attempt_slots"][1].update(
                activation="initial"
            ),
            lambda p: p["design"]["randomization"].update(seed=900),
            lambda p: p["cases"][0].update(public_payload_sha256="0" * 64),
            lambda p: p["blocks"][0]["arms"][0]["attempt_slots"].reverse(),
        ):
            candidate = copy.deepcopy(self.f.plan)
            mutation(candidate)
            self.reject_plan(candidate)

    def test_outer_protocol_case_time_and_run_are_independent(self):
        for key, value in (
            ("expected_protocol_ref", self.f.case_closure_ref),
            ("expected_case_closure_ref", self.f.protocol_ref),
            ("case_selection_frozen_at", "2026-09-09T00:00:00Z"),
            ("expected_run_id", "other"),
        ):
            self.reject_plan(self.f.plan, **{key: value})

    def test_bad_requests_case_sets_and_freeze_order_fail(self):
        for change in (
            {"plan_id": ""},
            {"run_id": False},
            {"case_selection_frozen_at": "2000-01-01T00:00:00Z"},
            {"public_cases": self.f.public_cases[:1]},
            {"public_cases": self.f.public_cases * 2},
        ):
            with (
                self.subTest(change=change),
                self.assertRaises(EvaluationValidationError),
            ):
                self.f.compile_plan(**change)

    def test_input_pin_drift_is_detected_even_after_cache_fill(self):
        inputs = self.f.inputs()
        validate_harness_plan(inputs, self.f.plan, **self.f.plan_context())
        ref = self.f.public_cases[0]["public_payload_ref"]
        (self.f.root / ref["path"]).write_text("{}")
        with self.assertRaises(EvaluationValidationError):
            validate_harness_plan(inputs, self.f.plan, **self.f.plan_context())

    def test_case_commitment_and_formal_input_substitution_fail(self):
        self.f.case_closure["cases"][0]["task"]["identity"] = "changed"
        self.f.case_closure_ref = self.f.write(
            "evaluation/case-closure.json", self.f.case_closure
        )
        with self.assertRaisesRegex(EvaluationValidationError, "case commitment"):
            self.f.compile_plan()
        self.f.freeze_case()
        with self.assertRaisesRegex(EvaluationValidationError, "Task identity"):
            self.f.compile_plan()

    def test_missing_public_case_input_and_private_alias_are_rejected(self):
        case = self.f.case_closure["cases"][0]
        # Coherently re-pin a missing public input; H1 compares it to the case commitment.
        case["formal_inputs"][0]["ref"] = self.f.public_input_ref
        self.f.freeze_case()
        with self.assertRaisesRegex(
            EvaluationValidationError, "differs from frozen case inputs"
        ):
            self.f.compile_plan()
        # Alias an already exposed byte sequence as private, even under a different path.
        original = self.f.doc(self.f.public_cases[0]["public_payload_ref"]["path"])[
            "input_refs"
        ][0]
        case["formal_inputs"][0]["ref"] = original
        case["private_oracle"]["ref"] = self.f.raw(
            "private-alias.txt", (self.f.root / original["path"]).read_bytes()
        )
        self.f.freeze_case()
        with self.assertRaisesRegex(
            EvaluationValidationError, "private evaluation artifact"
        ):
            self.f.compile_plan()

    def test_unknown_case_scope_count_and_unresolved_inputs_fail(self):
        for mutate, match in (
            (lambda c: c.update(scope="admission"), "comparison case closure"),
            (lambda c: c["cases"].pop(), "case count"),
            (
                lambda c: c["cases"][0].update(task_kind="opaque-task-contract"),
                "formal Task",
            ),
            (
                lambda c: c["cases"][0].update(formal_inputs=[]),
                "resolved formal inputs",
            ),
        ):
            saved = copy.deepcopy(self.f.case_closure)
            mutate(self.f.case_closure)
            if match == "resolved formal inputs":
                self.f.freeze_case()
            else:
                self.f.case_closure_ref = self.f.write(
                    "evaluation/case-closure.json", self.f.case_closure
                )
            with (
                self.subTest(match=match),
                self.assertRaisesRegex(EvaluationValidationError, match),
            ):
                self.f.compile_plan()
            self.f.case_closure = saved
            self.f.freeze_case()

    def test_plan_inventory_is_bounded_before_allocation(self):
        with (
            patch(
                "research_workbench.evaluation.harness_plan.MAX_PLANNED_ATTEMPTS", 63
            ),
            self.assertRaisesRegex(EvaluationValidationError, "bounded attempt"),
        ):
            self.f.compile_plan()
