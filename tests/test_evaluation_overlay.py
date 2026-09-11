"""Complete synthetic pre-run lineage and adversarial A4/pairwise records."""

import copy
import unittest

from research_workbench.evaluation.comparability import validate_comparability
from research_workbench.evaluation.overlay import validate_overlay
from research_workbench.evaluation.pins import (
    EvaluationInputs,
    EvaluationValidationError,
)
from tests.system_evaluation_fixtures import AT, ROOT, OverlayFixtureMixin


class EvaluationOverlayTests(OverlayFixtureMixin, unittest.TestCase):
    def inputs(self):
        return EvaluationInputs(self.f.root, ROOT / "schemas")

    def overlay(self, document=None, verifier=lambda _evidence: True):
        return validate_overlay(
            self.inputs(),
            self.f.overlay if document is None else document,
            expected_protocol_ref=self.f.protocol_ref,
            expected_case_closure_ref=self.f.case_closure_ref,
            case_selection_frozen_at=AT,
            admission_verifier=verifier,
        )

    def pairwise(self, document=None):
        return validate_comparability(
            self.inputs(),
            self.f.pairwise if document is None else document,
            expected_protocol_ref=self.f.protocol_ref,
            expected_case_closure_ref=self.f.case_closure_ref,
            case_selection_frozen_at=AT,
            admission_verifier=lambda _evidence: True,
        )

    def test_pre_run_lineage_is_valid_but_not_actual_execution_or_admission_authority(
        self,
    ):
        seen = []
        result = self.overlay(verifier=lambda evidence: seen.append(evidence) is None)
        self.assertEqual(len(result), 1)
        self.assertEqual(seen[0]["evaluation_ref"], self.f.evaluation_ref)
        self.assertEqual(
            result[0]["snapshot"]["supply_identity"]["supply_kind"], "skill"
        )
        self.assertFalse(self.f.overlay["boundaries"]["execution_authority"])
        self.assertEqual(self.f.overlay["evidence_phase"], "pre-run-qualification")

    def test_status_strings_cannot_replace_external_admission_verification(self):
        for verifier in (None, lambda _evidence: False, lambda _evidence: 1):
            with (
                self.subTest(verifier=verifier),
                self.assertRaisesRegex(EvaluationValidationError, "external admission"),
            ):
                self.overlay(verifier=verifier)

    def test_outer_manifest_protocol_evaluation_and_task_pins_cannot_be_substituted(
        self,
    ):
        for key in (
            "protocol_ref",
            "manifest_ref",
            "task_ref",
            "admission_evaluation_ref",
        ):
            document = copy.deepcopy(self.f.overlay)
            document[key] = self.f.case_closure_ref
            with self.subTest(key=key), self.assertRaises(EvaluationValidationError):
                self.overlay(document)

    def test_human_decision_requires_named_actor_and_exact_candidate_metadata(self):
        for key, value in (("status", "proposed"), ("actor", "another reviewer")):
            document = copy.deepcopy(self.f.overlay)
            decision = self.f.doc(document["admission_decision_ref"]["path"])
            decision[key] = value
            document["admission_decision_ref"] = self.f.write(
                "evaluation/changed-decision.json", decision
            )
            with self.subTest(key=key), self.assertRaises(EvaluationValidationError):
                self.overlay(document)
        document = copy.deepcopy(self.f.overlay)
        document["accountable_human"] = "human"
        with self.assertRaisesRegex(EvaluationValidationError, "named"):
            self.overlay(document)
        document = copy.deepcopy(self.f.overlay)
        decision = self.f.doc(document["admission_decision_ref"]["path"])
        decision["metadata"]["skill_candidate_id"] = "other-candidate"
        document["admission_decision_ref"] = self.f.write(
            "evaluation/other-candidate.json", decision
        )
        with self.assertRaisesRegex(EvaluationValidationError, "candidate/Evaluation"):
            self.overlay(document)

    def test_projection_and_lifecycle_drift_do_not_self_authorize(self):
        for field, value in (
            (
                "admission",
                {"state": "pending", "decision_owner": "human", "reason": "pending"},
            ),
            (
                "runtime_eligibility",
                {
                    "state": "ineligible",
                    "eligibility_ref": "NONE",
                    "scopes": [],
                    "reason": "no",
                },
            ),
        ):
            document = copy.deepcopy(self.f.overlay)
            lifecycle = self.f.doc(document["lifecycle_ref"]["path"])
            lifecycle[field] = value
            document["lifecycle_ref"] = self.f.write(
                "accepted/changed-lifecycle.json", lifecycle
            )
            with self.assertRaisesRegex(EvaluationValidationError, "eligible"):
                self.overlay(document)
        document = copy.deepcopy(self.f.overlay)
        projection = self.f.doc(document["projection_ref"]["path"])
        projection["release"]["package_hash"] = "0" * 64
        document["projection_ref"] = self.f.write(
            "accepted/changed-projection.json", projection
        )
        with self.assertRaisesRegex(EvaluationValidationError, "Projection differs"):
            self.overlay(document)

    def test_case_eligibility_time_and_planned_evidence_cannot_be_fabricated(self):
        for key, value in (
            ("primary_confirmatory_eligible", False),
            ("overlap_status", "admission-overlap"),
            ("evidence_phase", "actual-execution"),
            ("checked_at", "2026-09-10T00:00:00Z"),
        ):
            document = copy.deepcopy(self.f.overlay)
            document[key] = value
            with self.subTest(key=key), self.assertRaises(EvaluationValidationError):
                self.overlay(document)

    def test_runtime_snapshot_bundle_view_interface_pins_fail_closed(self):
        for key in ("snapshot_ref", "bundle_ref", "view_ref", "interface_ref"):
            document = copy.deepcopy(self.f.overlay)
            document["runtime_bindings"][0][key]["sha256"] = "0" * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.overlay(document)

    def test_current_a3_a4_method_difference_is_package_effect(self):
        result = self.pairwise()
        self.assertEqual(result["status"], "skill-bearing-package")
        self.assertIn("methods", result["mismatches"])
        document = copy.deepcopy(self.f.pairwise)
        document["result"]["status"] = "exact-skill-only"
        document["result"]["interpretation"] = "skill-conditional-increment"
        with self.assertRaisesRegex(EvaluationValidationError, "pairwise result"):
            self.pairwise(document)

    def test_analysis_input_replays_the_exact_preregistered_comparison(self):
        prior = self.f.write("evaluation/preregistered-pairwise.json", self.f.pairwise)
        analysis = copy.deepcopy(self.f.pairwise)
        analysis.update(
            stage="analysis-input",
            preregistered_record_ref=prior,
            checked_at="2026-09-11T01:00:00Z",
        )
        self.assertEqual(self.pairwise(analysis)["status"], "skill-bearing-package")
        analysis["preregistered_record_ref"] = self.f.write(
            "evaluation/analysis-self.json", analysis
        )
        with self.assertRaisesRegex(EvaluationValidationError, "preregistration"):
            self.pairwise(analysis)

    def test_pairwise_cannot_replace_outer_case_arm_time_or_snapshot_set(self):
        for key, value in (
            ("manifest_ref", self.f.case_closure_ref),
            ("case_closure_ref", self.f.protocol_ref),
            ("checked_at", "2026-09-10T00:00:00Z"),
            ("a3_runtime_bindings", []),
        ):
            document = copy.deepcopy(self.f.pairwise)
            document[key] = value
            with self.subTest(key=key), self.assertRaises(EvaluationValidationError):
                self.pairwise(document)

    def test_overlay_requires_the_consumers_case_pin_and_freeze_time(self):
        for case_ref, frozen_at in (
            (None, None),
            (self.f.protocol_ref, AT),
            (self.f.case_closure_ref, "2026-09-11T01:00:00Z"),
        ):
            with (
                self.subTest(case_ref=case_ref, frozen_at=frozen_at),
                self.assertRaisesRegex(EvaluationValidationError, "externally frozen"),
            ):
                validate_overlay(
                    self.inputs(),
                    self.f.overlay,
                    expected_protocol_ref=self.f.protocol_ref,
                    expected_case_closure_ref=case_ref,
                    case_selection_frozen_at=frozen_at,
                    admission_verifier=lambda _evidence: True,
                )

    def test_full_view_binding_and_budget_must_equal_frozen_protocol(self):
        from research_workbench.evaluation.system_protocol import (
            validate_view_shared_conditions,
        )

        view = self.f.doc(self.f.overlay["runtime_bindings"][0]["view_ref"]["path"])
        manifest = self.f.doc(self.f.manifest_ref["path"])
        validate_view_shared_conditions(view, manifest, self.f.protocol)
        for component in ("provider", "adapter", "model", "runtime", "host"):
            for field in ("version", "content_hash"):
                changed = copy.deepcopy(view)
                changed["binding"][component][field] = (
                    "2" if field == "version" else "2" * 64
                )
                with (
                    self.subTest(component=component, field=field),
                    self.assertRaisesRegex(
                        EvaluationValidationError, "frozen execution binding"
                    ),
                ):
                    validate_view_shared_conditions(changed, manifest, self.f.protocol)
        view["effective_constraints"]["budget"]["max_seconds"] += 1
        with self.assertRaisesRegex(EvaluationValidationError, "frozen budget"):
            validate_view_shared_conditions(view, manifest, self.f.protocol)

    def test_comparison_keeps_output_and_completion_obligations(self):
        from research_workbench.evaluation.comparability import (
            comparison_surface,
            derive_comparability,
        )

        chains = self.overlay()
        chains[0]["view"] = self.f.doc(
            self.f.overlay["runtime_bindings"][0]["view_ref"]["path"]
        )
        surface = comparison_surface(chains)
        for field in (
            "profile_constraints",
            "required_outputs",
            "completion_checks",
            "safe_pause_conditions",
            "stop_conditions",
        ):
            changed = copy.deepcopy(chains)
            changed[0]["view"][field] = {"changed": True}
            result = derive_comparability(
                surface, comparison_surface(changed), admitted_skill_count=1
            )
            with self.subTest(field=field):
                self.assertEqual(result["status"], "skill-bearing-package")
                self.assertIn("execution_constraints", result["mismatches"])

    def test_promotion_provenance_requires_exact_endpoints(self):
        document = copy.deepcopy(self.f.overlay)
        provenance = {
            "candidate_binding": self.f.doc(self.f.manifest_ref["path"])["arms"][3][
                "skill_binding"
            ],
            "release_ref": document["release_ref"],
        }
        document["promotion_provenance_ref"] = self.f.write(
            "accepted/promotion.json", provenance
        )
        self.assertEqual(len(self.overlay(document)), 1)
        provenance["release_ref"] = document["lifecycle_ref"]
        document["promotion_provenance_ref"] = self.f.write(
            "accepted/wrong-promotion.json", provenance
        )
        with self.assertRaisesRegex(
            EvaluationValidationError, "promotion provenance endpoints"
        ):
            self.overlay(document)

    def test_coherently_rebuilt_view_cannot_change_the_frozen_model_version(self):
        from research_workbench.evaluation.pins import file_ref
        from research_workbench.execution import (
            load_runtime_bundle,
            produce_resolved_execution_view,
        )
        from research_workbench.execution.execution_view import PinnedExecutionInput

        document = copy.deepcopy(self.f.overlay)
        runtime = document["runtime_bindings"][0]
        view = self.f.doc(runtime["view_ref"]["path"])
        binding = self.f.doc(view["execution_binding_ref"]["path"])
        binding["model"]["version"] = "2.0.0"
        updated = self.f.write("a4/changed-binding.json", binding)
        pins = {
            key: PinnedExecutionInput(**file_ref(view[key + "_ref"]))
            for key in (
                "agent_profile",
                "data_policy",
                "host_policy",
                "execution_binding",
            )
        }
        pins["execution_binding"] = PinnedExecutionInput(**updated)
        bundle = load_runtime_bundle(
            runtime["bundle_ref"]["path"],
            project_root=self.f.root,
            schema_root=ROOT / "schemas",
        )
        rebuilt = produce_resolved_execution_view(
            bundle,
            **pins,
            execution_at=AT,
            view_id="COHERENT-OTHER-MODEL",
            expected_bundle_sha256=runtime["bundle_ref"]["sha256"],
            schema_root=ROOT / "schemas",
        )
        runtime["view_ref"] = self.f.write("a4/changed-view.json", rebuilt)
        with self.assertRaisesRegex(
            EvaluationValidationError, "frozen execution binding"
        ):
            self.overlay(document)
