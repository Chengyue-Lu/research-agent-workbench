"""M5-006 held-out closure: identity OR hash, gaps, timing and independent replay."""

import copy
import unittest

from research_workbench.evaluation.overlap import derive_overlap, validate_overlap
from research_workbench.evaluation.pins import (
    EvaluationInputs,
    EvaluationValidationError,
    digest,
)
from tests.system_evaluation_fixtures import AT, ROOT, OverlapFixtureMixin


class EvaluationOverlapTests(OverlapFixtureMixin, unittest.TestCase):
    def inputs(self):
        return EvaluationInputs(self.f.root, ROOT / "schemas")

    def validate(self, document, **kwargs):
        return validate_overlap(
            self.inputs(),
            document,
            expected_protocol_ref=self.f.protocol_ref,
            expected_case_closure_ref=kwargs.get("case_ref", self.f.case_closure_ref),
            case_selection_frozen_at=kwargs.get("frozen_at", AT),
        )

    def test_complete_held_out_record_is_independently_reproduced(self):
        result = self.validate(self.f.assessment())
        self.assertEqual(result["overlap_status"], "held-out")
        self.assertTrue(result["primary_confirmatory_eligible"])
        self.assertEqual(result["overlap_refs"], [])

    def test_every_overlap_axis_uses_identity_or_content_hash(self):
        for field, axis in (
            ("case", "case"),
            ("task", "task"),
            ("formal_inputs", "formal-input"),
            ("private_oracle", "private-oracle"),
        ):
            with self.subTest(axis=axis):
                comparison = copy.deepcopy(self.f.case_closure)
                comparison["cases"][0][field] = copy.deepcopy(
                    self.f.admission_closure["cases"][0][field]
                )
                # The case commitment is updated too: the counterexample is a
                # coherent overlap, not just a broken hash reference.
                case = comparison["cases"][0]
                if field == "case":
                    comparison["cases"][0] = copy.deepcopy(
                        self.f.admission_closure["cases"][0]
                    )
                else:
                    case_doc = {
                        "case_id": case["case"]["identity"],
                        **{k: v for k, v in case.items() if k != "case"},
                    }
                    case["case"]["ref"] = self.f.write(
                        f"cases/overlap-{axis}.json", case_doc
                    )
                _left, _right, result = derive_overlap(
                    self.inputs(), self.f.admission_closure, comparison
                )
                self.assertTrue(
                    any(item["category"] == axis for item in result["overlap_refs"])
                )
                self.assertFalse(result["primary_confirmatory_eligible"])

    def test_same_hash_under_different_input_identity_is_overlap(self):
        comparison = copy.deepcopy(self.f.case_closure)
        other = comparison["cases"][0]["formal_inputs"][0]
        admission = self.f.admission_closure["cases"][0]["formal_inputs"][0]
        other["ref"] = self.f.raw(
            "cases/copied-input.txt",
            (self.f.root / admission["ref"]["path"]).read_bytes(),
        )
        case = comparison["cases"][0]
        case["case"]["ref"] = self.f.write(
            "cases/copied-input-case.json",
            {
                "case_id": case["case"]["identity"],
                **{k: v for k, v in case.items() if k != "case"},
            },
        )
        _, _, result = derive_overlap(
            self.inputs(), self.f.admission_closure, comparison
        )
        self.assertIn(
            {
                "category": "formal-input",
                "admission_identity": admission["identity"],
                "comparison_identity": other["identity"],
                "by": "hash",
            },
            result["overlap_refs"],
        )
        self.assertEqual(result["overlap_status"], "admission-overlap")

    def test_absent_unknown_or_opaque_identity_is_never_held_out(self):
        for field in ("task", "private_oracle", "checker", "human_adjudication"):
            for state in ("absent", "unknown"):
                with self.subTest(field=field, state=state):
                    admission = copy.deepcopy(self.f.admission_closure)
                    admission["cases"][0][field] = {
                        "state": state,
                        "identity": None,
                        "ref": None,
                        "reason": "No comparable evidence.",
                    }
                    _, _, result = derive_overlap(
                        self.inputs(), admission, self.f.case_closure
                    )
                    self.assertEqual(result["overlap_status"], "unresolved")
                    self.assertTrue(result["unresolved_reasons"])
        admission = copy.deepcopy(self.f.admission_closure)
        admission["cases"][0]["task_kind"] = "opaque-task-contract"
        self.assertEqual(
            derive_overlap(self.inputs(), admission, self.f.case_closure)[2][
                "overlap_status"
            ],
            "unresolved",
        )

    def test_absent_oracle_can_be_valid_record_but_is_ineligible(self):
        self.f.admission_closure["cases"][0]["private_oracle"] = {
            "state": "absent",
            "identity": None,
            "ref": None,
            "reason": "Legacy oracle was not captured.",
        }
        result = self.validate(self.f.assessment())
        self.assertFalse(result["primary_confirmatory_eligible"])
        self.assertEqual(result["overlap_status"], "unresolved")

    def test_uncaptured_admission_task_or_input_cannot_be_primary_evidence(self):
        original = copy.deepcopy(self.f.admission_closure)
        for field in ("task", "formal_inputs"):
            self.f.admission_closure = copy.deepcopy(original)
            subject = {
                "state": "unknown",
                "identity": None,
                "ref": None,
                "reason": "Admission source was not captured.",
            }
            self.f.admission_closure["cases"][0][field] = (
                [subject] if field == "formal_inputs" else subject
            )
            with self.subTest(field=field):
                result = self.validate(self.f.assessment())
                self.assertFalse(result["primary_confirmatory_eligible"])
                self.assertEqual(result["overlap_status"], "unresolved")

    def test_missing_or_drifted_private_oracle_is_retained_as_gap(self):
        path = (
            self.f.root
            / self.f.admission_closure["cases"][0]["private_oracle"]["ref"]["path"]
        )
        for content in (b"rewritten oracle", None):
            if content is None:
                path.unlink()
            else:
                path.write_bytes(content)
            result = self.validate(self.f.assessment())
            self.assertEqual(result["overlap_status"], "unresolved")

    def test_unknown_comparison_task_and_empty_formal_inputs_remain_ineligible(self):
        case = self.f.case_closure["cases"][0]
        case["task"] = {
            "state": "unknown",
            "identity": None,
            "ref": None,
            "reason": "Formal comparison Task not captured.",
        }
        case["formal_inputs"] = []
        self.f.case_closure_ref = self.f.write(
            "evaluation/incomplete-cases.json", self.f.case_closure
        )
        result = self.validate(self.f.assessment())
        self.assertEqual(result["overlap_status"], "unresolved")
        self.assertFalse(result["primary_confirmatory_eligible"])
        self.assertTrue(
            any(
                "formal input closure absent" in gap
                for gap in result["unresolved_reasons"]
            )
        )

    def test_case_commitment_cannot_substitute_its_oracle(self):
        original = self.f.admission_closure["cases"][0]["private_oracle"]
        original["ref"] = self.f.raw("cases/replacement-oracle.txt", b"replacement")
        result = self.validate(self.f.assessment())
        self.assertEqual(result["overlap_status"], "unresolved")
        self.assertTrue(
            any("substitution" in reason for reason in result["unresolved_reasons"])
        )

    def test_timing_case_pin_validator_pin_and_derived_bool_cannot_be_self_attested(
        self,
    ):
        document = self.f.assessment()
        for field, value in (
            ("primary_confirmatory_eligible", False),
            ("overlap_status", "admission-overlap"),
            ("checked_at", "2026-09-12T00:00:00Z"),
        ):
            mutated = copy.deepcopy(document)
            mutated["assessment_result"][field] = value
            with (
                self.subTest(field=field),
                self.assertRaises(EvaluationValidationError),
            ):
                self.validate(mutated)
        for key in ("entrypoint_ref", "dependency_refs"):
            mutated = copy.deepcopy(document)
            pin = mutated["assessment_result"]["validator"][key]
            (pin[0] if isinstance(pin, list) else pin)["sha256"] = "0" * 64
            with self.assertRaisesRegex(EvaluationValidationError, "validator"):
                self.validate(mutated)
        with self.assertRaisesRegex(EvaluationValidationError, "case selection"):
            self.validate(document, case_ref=self.f.protocol_ref)
        with self.assertRaisesRegex(EvaluationValidationError, "freeze order"):
            self.validate(document, frozen_at="2026-09-10T00:00:00Z")

    def test_input_subjects_and_digests_are_recomputed(self):
        document = self.f.assessment()
        for key in ("admission_closure_sha256", "input_digest"):
            mutated = copy.deepcopy(document)
            mutated["comparison_input_closure"][key] = "0" * 64
            with self.assertRaises(EvaluationValidationError):
                self.validate(mutated)
        mutated = copy.deepcopy(document)
        mutated["comparison_input_closure"]["admission_subjects"]["case"] = []
        with self.assertRaisesRegex(EvaluationValidationError, "subjects"):
            self.validate(mutated)

    def test_assessment_cannot_drop_admission_case_or_replace_evaluation(self):
        document = self.f.assessment()
        for key, value in (
            ("candidate_id", "OTHER"),
            ("skill_id", "OTHER"),
            ("skill_evaluation_ref", self.f.protocol_ref),
        ):
            mutated = copy.deepcopy(document)
            mutated["admission_case_closure"][key] = value
            with self.assertRaises(EvaluationValidationError):
                self.validate(mutated)
        mutated = copy.deepcopy(document)
        mutated["admission_case_closure"]["closure"]["cases"] *= 2
        mutated["comparison_input_closure"]["admission_closure_sha256"] = digest(
            mutated["admission_case_closure"]
        )
        with self.assertRaises(EvaluationValidationError):
            self.validate(mutated)

    def test_coherent_assessment_rewrite_cannot_replace_frozen_admission_provenance(
        self,
    ):
        document = self.f.assessment()
        # Change all author-controlled declarations, including the case file and
        # all result digests, while retaining the consumer's frozen Protocol.
        changed = copy.deepcopy(self.f.admission_closure)
        changed["closure_id"] = "FORGED-ADMISSION-CLOSURE"
        document["admission_case_closure"]["closure"] = changed
        document["comparison_input_closure"]["admission_closure_sha256"] = digest(
            document["admission_case_closure"]
        )
        with self.assertRaisesRegex(
            EvaluationValidationError, "externally frozen Protocol"
        ):
            self.validate(document)
        self.f.protocol["admission_case_closure_ref"] = None
        self.f.protocol_ref = self.f.write("evaluation/protocol.json", self.f.protocol)
        document["comparison_input_closure"]["protocol_ref"] = self.f.protocol_ref
        with self.assertRaisesRegex(EvaluationValidationError, "independently pin"):
            self.validate(document)
