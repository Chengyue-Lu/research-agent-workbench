"""Independent expected context and shared-gate attacks; no live ports or grants."""
import copy
import dataclasses
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_workbench.evaluation.live_inputs import LiveEvaluationInputs
from research_workbench.evaluation.live_preflight import (
    FrozenLiveContext, LivePreflightVerifiers, VerifiedBudgetCheckpoint,
    compile_live_preflight, validate_live_preflight,
)
from research_workbench.evaluation.pins import EvaluationInputs, EvaluationValidationError
from tests.live_preflight_fixtures import LivePreflightFixture, TOKEN_CEILING
from tests.system_evaluation_fixtures import AT, ROOT


class LivePreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.template = LivePreflightFixture(Path(temporary.name)).build_live()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.f = copy.deepcopy(self.template)
        self.f.root = Path(temporary.name)
        shutil.copytree(self.template.root, self.f.root, dirs_exist_ok=True)

    def compile(self, **overrides):
        return compile_live_preflight(self.f.live_inputs(), **self.f.arguments(**overrides))

    def reject(self, pattern=None, **overrides):
        with self.assertRaisesRegex(EvaluationValidationError, pattern or "."):
            self.compile(**overrides)

    def test_shared_m6_qualification_h1_overlay_pairwise_and_recomputation(self):
        # The compiler must consume the preexisting M6 record, never produce A2.
        with patch("research_workbench.execution.baseline_envelope.produce_a2_qualification",
                   side_effect=AssertionError("preflight invoked A2 producer")):
            result = self.compile()
            reloaded = self.f.write("live/preflight.json", result)
            inputs = self.f.live_inputs()
            checked = validate_live_preflight(inputs, inputs.read(reloaded, "evaluation_live_preflight"),
                context=self.f.context(), expected_checked_at=AT, verifiers=self.f.verifiers())
        self.assertEqual(result, checked)
        self.assertEqual(result["purpose"], "live-pilot")
        self.assertEqual(result["validator"]["version"], "2.0.0")
        self.assertIn("research_workbench/evaluation/live_preflight.py", result["validator"]["sources"])
        self.assertIn("v0.2.0/evaluation-live-preflight.schema.json", self.f.live_inputs().schema_identity())
        self.assertEqual(result["checkpoint"]["known_total_tokens"], 1744)
        self.assertEqual(len(result["cases"]), 2)
        self.assertFalse(any(result["boundaries"].values()))
        self.assertTrue(all(not c["primary_confirmatory_eligible"] and not c["pilot_primary_eligible"]
                            for c in result["cases"]))

    def test_old_default_and_h2_cannot_load_or_relabel_new_record(self):
        result = self.compile()
        with self.assertRaises(KeyError):
            EvaluationInputs(self.f.root, ROOT / "schemas").validate("evaluation_live_preflight", result)
        result["record_kind"] = "evaluation_harness_preflight"
        with self.assertRaises(EvaluationValidationError):
            self.f.live_inputs().validate("evaluation_harness_preflight", result)

    def test_new_record_cannot_change_purpose_version_or_authority(self):
        original = self.compile()
        for key, value in (("purpose", "synthetic-contract-proof"), ("version", "1.0.0"),
                           ("schema_version", "0.1.0"),
                           ("boundaries", original["boundaries"] | {"execution_authority": True})):
            with self.subTest(key=key), self.assertRaises(EvaluationValidationError):
                self.f.live_inputs().validate("evaluation_live_preflight", original | {key: value})

    def test_independently_derived_unresolved_overlap_stops_before_a4(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = LivePreflightFixture(Path(directory)).build_live(overlap_state="unresolved")
            self.assertEqual(fixture.overlap["assessment_result"]["overlap_status"], "unresolved")
            with self.assertRaisesRegex(EvaluationValidationError, "live overlap is unresolved"):
                compile_live_preflight(fixture.live_inputs(), **fixture.arguments())

    def test_context_refs_are_copied_immutable_and_never_adopt_report_context(self):
        context = self.f.context()
        original = context.value()
        self.f.scope["provider_config_ref"]["sha256"] = "f" * 64
        self.assertEqual(context.value(), original)
        with self.assertRaises(TypeError):
            context.provider_config_ref["sha256"] = "f" * 64
        with self.assertRaises(dataclasses.FrozenInstanceError):
            context.run_id = "other"

    def test_external_reference_and_run_identity_substitution(self):
        original = self.f.context()
        for name in ("protocol_ref", "scope_ref", "plan_ref", "case_closure_ref", "provider_config_ref",
                     "provider_applicability_ref", "windows_context_ref", "budget_checkpoint_ref", "authorization_ref"):
            ref = dict(getattr(original, name))
            alias = self.f.raw("alias/" + name + ".json", (self.f.root / ref["path"]).read_bytes())
            with self.subTest(name=name):
                self.reject(context=dataclasses.replace(original, **{name: alias}))
        self.reject(context=dataclasses.replace(original, run_id="other-run"))
        self.reject(context=dataclasses.replace(original, source_commit="f" * 40))
        self.reject(context=dataclasses.replace(original, cumulative_token_ceiling=TOKEN_CEILING + 1))

    def test_missing_verifiers_and_truthy_file_flags_do_not_supply_authority(self):
        with self.assertRaises(EvaluationValidationError):
            LivePreflightVerifiers(None, None, None, None)
        for role in ("authorization", "applicability", "admission"):
            with self.subTest(role=role):
                self.reject(verifiers=self.f.verifiers(**{role: lambda _: False}))
        for value in ("approved", 1, {"approved": True}):
            with self.subTest(value=value):
                self.reject(verifiers=self.f.verifiers(authorization=lambda _, value=value: value))

    def test_self_declared_qualified_approved_flags_are_not_accepted(self):
        # Hash consistency of flags alone does not furnish an external callback.
        self.assertFalse(self.f.doc(self.f.authorization_ref["path"])["approved"])
        self.assertFalse(self.f.doc(self.f.scope["provider_applicability_ref"]["path"])["qualified"])
        self.reject(verifiers=self.f.verifiers(authorization=lambda _: False))
        self.reject(verifiers=self.f.verifiers(applicability=lambda _: False))

    def test_external_callback_failure_diagnostics_have_no_original_payload(self):
        def fail(_):
            raise RuntimeError("secret-payload-fixture")
        for role in ("authorization", "applicability", "budget_checkpoint", "admission"):
            with self.subTest(role=role):
                with self.assertRaises(EvaluationValidationError) as captured:
                    self.compile(verifiers=self.f.verifiers(**{role: fail}))
                self.assertNotIn("secret-payload-fixture", str(captured.exception))
                self.assertIsNone(captured.exception.__context__)
                self.assertIsNone(captured.exception.__cause__)

    def test_external_callback_cannot_mutate_frozen_inputs_by_argument_alias(self):
        def authorize(argument):
            argument["scope"]["budget"]["prior_tokens"] = 0
            argument["context"]["run_id"] = "other"
            return True
        result = self.compile(verifiers=self.f.verifiers(authorization=authorize))
        self.assertEqual(result["checkpoint"]["known_total_tokens"], 1744)
        self.assertEqual(result["context"]["run_id"], "FIXTURE-LIVE-RUN")

    def test_typed_checkpoint_actual_totals_limits_completeness_and_ref_required(self):
        ref = self.f.scope["budget_checkpoint_ref"]
        for snapshot in (True, {"known_total_tokens": 1744},
            VerifiedBudgetCheckpoint(ref, 7, 0, TOKEN_CEILING, True),
            VerifiedBudgetCheckpoint(ref, 1744, 1, TOKEN_CEILING, True),
            VerifiedBudgetCheckpoint(ref, 1744, 0, TOKEN_CEILING, False),
            VerifiedBudgetCheckpoint(ref, 1744, 0, TOKEN_CEILING - 1, True),
            VerifiedBudgetCheckpoint(ref, 1744, 0, TOKEN_CEILING + 1, True),
            VerifiedBudgetCheckpoint({"path": "other.json", "sha256": ref["sha256"]},
                                     1744, 0, TOKEN_CEILING, True)):
            with self.subTest(snapshot=repr(snapshot)):
                self.reject(verifiers=self.f.verifiers(budget_checkpoint=lambda _, s=snapshot: s))

    def test_budget_dto_rejects_bool_negative_and_nonexplicit_completeness(self):
        ref = self.f.scope["budget_checkpoint_ref"]
        for fields in ((True, 0, TOKEN_CEILING, True), (-1, 0, TOKEN_CEILING, True),
                       (1744, 0, TOKEN_CEILING, "true")):
            with self.subTest(fields=fields), self.assertRaises(EvaluationValidationError):
                VerifiedBudgetCheckpoint(ref, *fields)

    def test_fixture_checkpoint_reader_rejects_changed_temporary_journal(self):
        with self.f.journal() as journal:
            journal.start_attempt(repair_refreeze_confirmed=True)
            journal.reserve(input_upper_tokens=2, output_upper_tokens=1)
        self.reject("budget checkpoint verifier failed")

    def test_report_context_and_expected_time_are_external(self):
        result = self.compile()
        result["context"]["run_id"] = "other-run"
        with self.assertRaisesRegex(EvaluationValidationError, "external context/time"):
            validate_live_preflight(self.f.live_inputs(), result, context=self.f.context(),
                expected_checked_at=AT, verifiers=self.f.verifiers())
        result["context"]["run_id"] = "FIXTURE-LIVE-RUN"
        with self.assertRaisesRegex(EvaluationValidationError, "external context/time"):
            validate_live_preflight(self.f.live_inputs(), result, context=self.f.context(),
                expected_checked_at="2026-09-11T00:01:00Z", verifiers=self.f.verifiers())

    def test_case_bindings_must_cover_exactly_one_of_each_case(self):
        for bindings in (self.f.case_bindings[:1], self.f.case_bindings + self.f.case_bindings[:1],
                         self.f.case_bindings + [{**self.f.case_bindings[0], "case_id": "other"}]):
            with self.subTest(bindings=bindings):
                self.reject("unique planned cases", case_bindings=bindings)

    def test_a2_must_remain_m6_produced_correct_arm(self):
        self.reject("qualification arm/time", a2_qualification_ref=self.f.a3_ref)
        document = copy.deepcopy(self.f.a2)
        document["producer"] = "evaluation-harness"
        self.reject("producer ownership mismatch", a2_qualification_ref=self.f.write("live/bad-a2.json", document))

    def test_future_qualification_and_expired_scope_stop_preflight(self):
        document = copy.deepcopy(self.f.a2)
        document["checked_at"] = "2026-09-11T00:01:00Z"
        self.reject("qualification arm/time", a2_qualification_ref=self.f.write("live/future-a2.json", document))
        # A trusted callback cannot make an expired input window usable.
        self.reject("expired or inconsistent", checked_at="2026-09-12T00:00:00Z",
            verifiers=self.f.verifiers(authorization=lambda _: True, applicability=lambda _: True,
                budget_checkpoint=lambda _: VerifiedBudgetCheckpoint(
                    self.f.scope["budget_checkpoint_ref"], 1744, 0, TOKEN_CEILING, True)))

    def test_overlay_task_and_overlap_refs_cannot_be_substituted(self):
        for key in ("task_ref", "admission_overlap_assessment_ref"):
            document = copy.deepcopy(self.f.overlay)
            document[key] = {"path": "other.json", "sha256": "f" * 64}
            ref = self.f.write("live/bad-overlay.json", document)
            with self.subTest(key=key):
                self.reject("Task/overlap", case_bindings=[{**b, "a4_overlay_ref": ref} for b in self.f.case_bindings])

    def test_pairwise_stage_qualification_and_time_cannot_be_substituted(self):
        for key, value in (("stage", "post-run"), ("a3_qualification_ref", self.f.a2_ref),
                           ("checked_at", "2026-09-11T00:01:00Z")):
            document = copy.deepcopy(self.f.pairwise)
            document[key] = value
            ref = self.f.write("live/bad-pairwise.json", document)
            with self.subTest(key=key):
                self.reject(case_bindings=[{**b, "pairwise_ref": ref} for b in self.f.case_bindings])

    def test_callback_byte_drift_is_detected_before_shared_gate_consumption(self):
        def authorize(_):
            (self.f.root / self.f.scope["provider_config_ref"]["path"]).write_bytes(b"changed")
            return True
        self.reject(verifiers=self.f.verifiers(authorization=authorize))

    def test_changed_comparison_and_eligibility_cannot_pass_independent_readback(self):
        result = self.compile()
        result["cases"][0]["comparison"]["comparison_digest"] = "f" * 64
        with self.assertRaisesRegex(EvaluationValidationError, "independent recomputation"):
            validate_live_preflight(self.f.live_inputs(), result, context=self.f.context(),
                expected_checked_at=AT, verifiers=self.f.verifiers())
        result["cases"][0]["primary_confirmatory_eligible"] = True
        with self.assertRaisesRegex(EvaluationValidationError, "live schema"):
            self.f.live_inputs().validate("evaluation_live_preflight", result)

    def test_request_is_closed_finite_json_without_callback_or_port_input(self):
        self.reject(preflight_id="")
        self.reject(case_bindings=[{**b, "provider": "not-a-port"} for b in self.f.case_bindings])
        self.reject(case_bindings=[{**self.f.case_bindings[0], "case_id": float("nan")}])
        self.reject(context=None)
        self.reject(verifiers=None)
        with self.assertRaises(EvaluationValidationError):
            FrozenLiveContext(**(self.f.context().value() | {"cumulative_token_ceiling": True}))

    def test_v2_schema_drift_during_external_verification_stops_preflight(self):
        schemas = self.f.root / "test-schemas"
        shutil.copytree(ROOT / "schemas", schemas)
        inputs = LiveEvaluationInputs(self.f.root, schemas, cumulative_token_ceiling=TOKEN_CEILING)

        def authorize(_):
            path = schemas / "v0.2.0/evaluation-live-preflight.schema.json"
            path.write_bytes(path.read_bytes() + b"\n")
            return True

        with self.assertRaisesRegex(EvaluationValidationError, "Schema bytes changed"):
            compile_live_preflight(inputs, **self.f.arguments(
                verifiers=self.f.verifiers(authorization=authorize)))

    def test_new_process_recomputation_uses_external_context_and_preserves_inputs(self):
        record = self.compile()
        record_ref = self.f.write("live/preflight.json", record)
        # Separate caller-owned fixture authority, never recovered from the report.
        trusted_ref = self.f.write("live/test-authority.json", {
            "context": self.f.context().value(), "admission_pins": self.f.admission_pins,
            "preflight_ref": record_ref})
        before = {p.relative_to(self.f.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.f.root.rglob("*") if p.is_file()}
        script = """
import json,sys
from pathlib import Path
from research_workbench.evaluation.live_preflight import FrozenLiveContext,validate_live_preflight
from research_workbench.evaluation.live_inputs import LiveEvaluationInputs
from tests.live_preflight_fixtures import LivePreflightFixture,TOKEN_CEILING
from tests.system_evaluation_fixtures import ROOT
root=Path(sys.argv[1])
expected=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
context=FrozenLiveContext(**expected['context'])
fixture=LivePreflightFixture(root)
fixture.trusted_context=context.value()
fixture.admission_pins=expected['admission_pins']
inputs=LiveEvaluationInputs(root,ROOT/'schemas',cumulative_token_ceiling=TOKEN_CEILING)
record=inputs.read(expected['preflight_ref'],'evaluation_live_preflight')
actual=validate_live_preflight(inputs,record,context=context,expected_checked_at=sys.argv[3],verifiers=fixture.verifiers())
print(json.dumps({'purpose':actual['purpose'],'actual_execution':actual['boundaries']['actual_execution']}))
"""
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT)))
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", script,
            str(self.f.root), str(self.f.root / trusted_ref["path"]), AT], cwd=self.f.root,
            env=environment, capture_output=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"purpose": "live-pilot", "actual_execution": False})
        after = {p.relative_to(self.f.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.f.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
