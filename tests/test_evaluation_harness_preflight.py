"""Independent preflight inputs, trusted clocks and non-authority outcomes."""

import copy
from contextlib import ExitStack
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch

from research_workbench.evaluation.harness_preflight import (
    compile_harness_preflight,
    produce_a3_qualification,
    validate_harness_preflight,
)
from research_workbench.evaluation.pins import EvaluationValidationError
from tests.harness_fixtures import HarnessFixtureMixin
from tests.system_evaluation_fixtures import AT


class HarnessPreflightTests(HarnessFixtureMixin, unittest.TestCase):
    def validate(self, record, **overrides):
        args = {
            **self.f.plan_context(),
            "expected_plan_ref": self.f.plan_ref,
            "expected_preflight_checked_at": AT,
            "admission_verifier": lambda _: True,
        }
        return validate_harness_preflight(self.f.inputs(), record, **(args | overrides))

    def test_frozen_inputs_recompute_without_producing_a2_or_execution(self):
        with ExitStack() as stack:
            for target in (
                "research_workbench.execution.baseline_envelope.produce_a2_qualification",
                "research_workbench.execution.baseline.run_baseline_session",
                "research_workbench.execution.host.execute_frozen_view",
            ):
                stack.enter_context(
                    patch(
                        target,
                        side_effect=AssertionError(
                            "preflight may not produce A2 or execute"
                        ),
                    )
                )
            result = self.f.preflight()
            self.assertEqual(result, self.validate(result))
        self.assertTrue(
            all(c["primary_confirmatory_eligible"] for c in result["cases"])
        )
        self.assertTrue(
            all(
                c["comparison"]["status"] == "skill-bearing-package"
                for c in result["cases"]
            )
        )
        self.assertTrue(all(not c["pilot_primary_eligible"] for c in result["cases"]))
        self.assertFalse(any(result["boundaries"].values()))
        self.assertNotIn("primary_confirmatory_eligible", self.f.plan["blocks"][-1])

    def test_a3_producer_only_assembles_supplied_resolver_bindings(self):
        result = produce_a3_qualification(
            self.f.inputs(),
            protocol_ref=self.f.protocol_ref,
            qualification_id="HARNESS-A3",
            preflight_checked_at=AT,
            bindings=self.f.a3["bindings"],
        )
        self.assertEqual(result, self.f.a3)
        bindings = copy.deepcopy(self.f.a3["bindings"])
        bindings.pop()
        with self.assertRaises(EvaluationValidationError):
            produce_a3_qualification(
                self.f.inputs(),
                protocol_ref=self.f.protocol_ref,
                qualification_id="bad",
                preflight_checked_at=AT,
                bindings=bindings,
            )

    def test_admission_authority_must_be_supplied_and_accept_exact_evidence(self):
        for verifier in (None, lambda _: False):
            with (
                self.subTest(verifier=verifier),
                self.assertRaises(EvaluationValidationError),
            ):
                self.f.preflight(admission_verifier=verifier)
        seen = []
        result = self.f.preflight(
            admission_verifier=lambda evidence: seen.append(evidence) or True
        )
        self.assertTrue(seen)
        self.assertNotIn("admission_verifier", result["request"])

    def test_time_is_explicit_and_replay_cannot_trust_a_self_selected_clock(self):
        args = self.f.preflight_args()
        args.pop("preflight_checked_at")
        with self.assertRaises(TypeError):
            compile_harness_preflight(self.f.inputs(), **args)
        from research_workbench.evaluation.qualification import validate_qualification

        chains = validate_qualification(
            self.f.inputs(), self.f.a2, expected_protocol_ref=self.f.protocol_ref
        )
        expires = min(
            datetime.fromisoformat(
                c["selected_supply_report"]["availability"]["valid_until"]
            )
            for c in chains
        )
        for value in (
            "invalid",
            "2000-01-01T00:00:00Z",
            (expires + timedelta(seconds=1)).isoformat(),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(EvaluationValidationError),
            ):
                self.f.preflight(preflight_checked_at=value)
        result = self.f.preflight()
        with self.assertRaisesRegex(EvaluationValidationError, "outer plan/time"):
            self.validate(result, expected_preflight_checked_at="2026-01-01T00:00:00Z")
        with self.assertRaisesRegex(EvaluationValidationError, "outer plan/time"):
            self.validate(result, expected_plan_ref=self.f.protocol_ref)

    def test_qualification_arm_producer_snapshot_and_timestamp_cannot_be_substituted(
        self,
    ):
        for kind, change in [
            ("a2", {"arm_id": "mode-no-skill"}),
            ("a2", {"producer": "evaluation-harness"}),
            ("a3", {"checked_at": "2099-01-01T00:00:00Z"}),
        ]:
            record = copy.deepcopy(getattr(self.f, kind))
            record.update(change)
            ref = self.f.write("harness/bad-qualification.json", record)
            with (
                self.subTest(kind=kind, change=change),
                self.assertRaises(EvaluationValidationError),
            ):
                self.f.preflight(**{kind + "_qualification_ref": ref})
        record = copy.deepcopy(self.f.a3)
        record["bindings"][0]["runtime_snapshot_ref"] = record["bindings"][0][
            "frozen_snapshot_ref"
        ]
        ref = self.f.write("harness/structural-qualification.json", record)
        with self.assertRaises(EvaluationValidationError):
            self.f.preflight(a3_qualification_ref=ref)

    def test_case_coverage_and_duplicate_or_unknown_records_are_rejected(self):
        for bindings in (
            self.f.case_bindings[:1],
            self.f.case_bindings * 2,
            [dict(self.f.case_bindings[0], case_id="wrong"), self.f.case_bindings[1]],
        ):
            with (
                self.subTest(bindings=bindings),
                self.assertRaisesRegex(
                    EvaluationValidationError, "cover unique planned cases"
                ),
            ):
                self.f.preflight(case_bindings=bindings)
        with self.assertRaises(EvaluationValidationError):
            self.f.preflight(preflight_id="")

    def test_overlay_task_overlap_and_time_must_match_outer_context(self):
        for change in (
            {"task_ref": self.f.protocol_ref},
            {"admission_overlap_assessment_ref": self.f.case_closure_ref},
            {"checked_at": "2099-01-01T00:00:00Z"},
        ):
            overlay = copy.deepcopy(self.f.overlay)
            overlay.update(change)
            ref = self.f.write("harness/bad-overlay.json", overlay)
            bindings = [dict(b, a4_overlay_ref=ref) for b in self.f.case_bindings]
            with (
                self.subTest(change=change),
                self.assertRaises(EvaluationValidationError),
            ):
                self.f.preflight(case_bindings=bindings)

    def test_pairwise_cannot_upgrade_or_replace_qualification_stage_and_time(self):
        for change in (
            {"a3_qualification_ref": self.f.a2_ref},
            {"a4_overlay_ref": self.f.plan_ref},
            {"checked_at": "2099-01-01T00:00:00Z"},
            {
                "stage": "analysis-input",
                "preregistered_record_ref": self.f.pairwise_ref,
            },
        ):
            record = copy.deepcopy(self.f.pairwise)
            record.update(change)
            ref = self.f.write("harness/bad-pairwise.json", record)
            bindings = [dict(b, pairwise_ref=ref) for b in self.f.case_bindings]
            with (
                self.subTest(change=change),
                self.assertRaises(EvaluationValidationError),
            ):
                self.f.preflight(case_bindings=bindings)
        record = copy.deepcopy(self.f.pairwise)
        record["result"].update(
            status="exact-skill-only",
            interpretation="skill-conditional-increment",
            mismatches=[],
        )
        ref = self.f.write("harness/bad-pairwise.json", record)
        with self.assertRaises(EvaluationValidationError):
            self.f.preflight(
                case_bindings=[dict(b, pairwise_ref=ref) for b in self.f.case_bindings]
            )

    def test_preflight_results_and_validator_pins_are_not_self_attested(self):
        original = self.f.preflight()
        for change in (
            lambda r: r["cases"][0].update(primary_confirmatory_eligible=False),
            lambda r: r["cases"][0]["comparison"].update(status="exact-skill-only"),
            lambda r: r["validator"].update(schemas_sha256="0" * 64),
            lambda r: r["request"].update(admission_verifier=True),
            lambda r: r["boundaries"].update(actual_execution=True),
        ):
            result = copy.deepcopy(original)
            change(result)
            with self.assertRaises(EvaluationValidationError):
                self.validate(result)

    def test_dependent_input_and_schema_drift_cannot_hide_in_a_saved_record(self):
        result = self.f.preflight()
        (self.f.root / self.f.a2_ref["path"]).write_text("{}")
        with self.assertRaises(EvaluationValidationError):
            self.validate(result)

    def test_validator_drift_during_callback_is_rejected(self):
        from research_workbench.evaluation import harness_preflight

        original = harness_preflight.validator_identity
        calls = []

        def identity(inputs):
            value = original(inputs)
            if calls:
                value["version"] = "drift"
            calls.append(1)
            return value

        with (
            patch.object(harness_preflight, "validator_identity", side_effect=identity),
            self.assertRaisesRegex(EvaluationValidationError, "validator changed"),
        ):
            self.f.preflight()

    def test_confirmatory_phase_never_overrides_admission_overlap(self):
        self.f.refreeze_overlap("admission-overlap")
        self.assertTrue(
            any(b["phase"] == "confirmatory" for b in self.f.plan["blocks"])
        )
        result = self.f.preflight()
        self.assertEqual(result["overlap"]["overlap_status"], "admission-overlap")
        self.assertTrue(
            all(not case["primary_confirmatory_eligible"] for case in result["cases"])
        )
        result["cases"][0]["primary_confirmatory_eligible"] = True
        with self.assertRaises(EvaluationValidationError):
            self.validate(result)

    def test_unresolved_oracle_blocks_the_complete_preflight(self):
        self.f.refreeze_overlap("unresolved")
        with self.assertRaisesRegex(EvaluationValidationError, "overlap is unresolved"):
            self.f.preflight()
