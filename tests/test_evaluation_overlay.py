"""Complete synthetic pre-run lineage and adversarial A4/pairwise records."""

import copy
import unittest

from research_workbench.evaluation.comparability import (
    admitted_skill_extension_count,
    validate_comparability,
)
from research_workbench.evaluation.overlay import validate_overlay
from research_workbench.evaluation.pins import (
    EvaluationInputs,
    EvaluationValidationError,
)
from tests.execution_fixtures import plain
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
        self.assertEqual(len(result), 2)
        self.assertEqual(
            {c["requirement"]["requirement_id"] for c in result},
            {"document-read", "research-contract-check"},
        )
        self.assertEqual(admitted_skill_extension_count(result), 1)
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
        self.assertNotIn("admitted-skill-extension-count", result["mismatches"])
        document = copy.deepcopy(self.f.pairwise)
        document["result"]["status"] = "exact-skill-only"
        document["result"]["interpretation"] = "skill-conditional-increment"
        with self.assertRaisesRegex(EvaluationValidationError, "pairwise result"):
            self.pairwise(document)

    def test_a4_requires_each_frozen_method_requirement_exactly_once(self):
        for mutation in ("missing", "duplicate", "extra-undeclared"):
            document = copy.deepcopy(self.f.overlay)
            if mutation == "missing":
                document["runtime_bindings"].pop()
            elif mutation == "duplicate":
                duplicate = copy.deepcopy(document["runtime_bindings"][0])
                duplicate["interface_ref"] = self.f.write(
                    "a4/duplicate-interface.json",
                    self.f.doc(duplicate["interface_ref"]["path"]),
                )
                document["runtime_bindings"].append(duplicate)
            else:
                # An extra qualified A3 slice cannot enter the A4 frozen Method.
                document["runtime_bindings"].append(
                    {
                        **self.f.pairwise["a3_runtime_bindings"][0],
                        "interface_ref": self.f.bindings["mode-no-skill"][
                            "interface_ref"
                        ],
                    }
                )
            expected = (
                "Requirement set.*exactly once"
                if mutation != "extra-undeclared"
                else "A4 Method.*frozen arm"
            )
            with (
                self.subTest(mutation=mutation),
                self.assertRaisesRegex(EvaluationValidationError, expected),
            ):
                self.overlay(document)

    def test_skill_count_deduplicates_exact_extension_identity_across_requirements(
        self,
    ):
        from research_workbench.evaluation.comparability import (
            comparison_surface,
            derive_comparability,
        )
        from research_workbench.evaluation.qualification import validate_qualification

        chains = plain(self.overlay())
        self.assertEqual(len(chains), 2)
        self.assertEqual(admitted_skill_extension_count(chains), 1)
        surface = comparison_surface(chains)
        self.assertEqual(
            derive_comparability(
                surface,
                surface,
                admitted_skill_count=admitted_skill_extension_count(chains),
            )["status"],
            "exact-skill-only",
        )
        for field, value in (
            ("component_ref", "another-skill"),
            ("version", "2.0.0"),
            ("content_hash", "sha256:" + "0" * 64),
            ("projection", "0" * 64),
        ):
            changed = copy.deepcopy(chains)
            identity = changed[1]["snapshot"]["supply_identity"]
            if field == "projection":
                identity["skill_release_projection_ref"]["content_hash"] = (
                    "sha256:" + value
                )
            else:
                identity["components"][0][field] = value
            with self.subTest(field=field):
                count = admitted_skill_extension_count(changed)
                self.assertEqual(count, 2)
                self.assertEqual(
                    derive_comparability(surface, surface, admitted_skill_count=count)[
                        "status"
                    ],
                    "not-comparable",
                )
        no_skill = validate_qualification(
            self.inputs(),
            self.f.qualification("mode-no-skill"),
            expected_protocol_ref=self.f.protocol_ref,
        )
        self.assertEqual(admitted_skill_extension_count(no_skill), 0)
        self.assertEqual(admitted_skill_extension_count([*chains, *no_skill]), 1)

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

    def _multi_task_comparison_inputs(self):
        """Extend qualified in-memory demand, not a multi-Task disk execution."""
        from unittest.mock import patch

        from research_workbench.evaluation.comparability import (
            _task_comparison_surface,
            comparison_surface,
        )
        from research_workbench.evaluation.qualification import (
            validate_requirement_closure,
        )

        captured = []

        def capture_surface(inputs, chains, manifest, *, task_ref):
            captured.append(plain(chains))
            return _task_comparison_surface(inputs, chains, manifest, task_ref=task_ref)

        # Observe the public validator's actual qualified Bundle/View chains;
        # every eligibility validator still runs before extending demand.
        with patch(
            "research_workbench.evaluation.comparability._task_comparison_surface",
            side_effect=capture_surface,
        ):
            expected = self.pairwise()
        a3 = captured[0]
        a4 = comparison_surface(self.overlay())
        manifest = self.f.doc(self.f.manifest_ref["path"])
        selected_arm = manifest["arms"][2]
        task = self.f.doc(self.f.task_ref["path"])
        task["task_id"] = "SECOND-FROZEN-TASK"
        second_task = self.f.write("evaluation/second-task.json", task)
        manifest["frozen_conditions"]["task_packet_refs"].append(second_task)
        method = copy.deepcopy(a3[0]["method_resolution"])
        method["resolution_id"] = "SECOND-FROZEN-METHOD"
        method["task_ref"] = {
            "task_id": task["task_id"],
            "revision": task["revision"],
            "sha256": second_task["sha256"],
        }
        second_method = self.f.write("evaluation/second-method.json", method)
        selected_arm["treatment_control"]["method_resolution_refs"].append(
            second_method
        )
        extra = copy.deepcopy(a3)
        for chain in extra:
            chain["snapshot"]["task_ref"] = self.f.c_ref(
                task["task_id"] + "@r1", second_task
            )
            chain["snapshot"]["method_resolution_ref"] = self.f.c_ref(
                method["resolution_id"] + "@r1", second_method
            )
            chain["task"] = copy.deepcopy(task)
            chain["method_resolution"] = copy.deepcopy(method)
        combined = [*extra, *a3]
        validate_requirement_closure(self.inputs(), combined, manifest, selected_arm)
        return expected, a3, a4, manifest, extra, combined

    def test_multi_task_composition_compares_the_complete_exact_overlay_task(self):
        from research_workbench.evaluation.comparability import (
            _task_comparison_surface,
            comparison_surface,
            derive_comparability,
        )

        expected, _a3, a4, manifest, _extra, combined = (
            self._multi_task_comparison_inputs()
        )
        self.assertEqual(
            derive_comparability(
                comparison_surface(combined), a4, admitted_skill_count=1
            )["status"],
            "not-comparable",
        )
        selected = _task_comparison_surface(
            self.inputs(), combined, manifest, task_ref=self.f.overlay["task_ref"]
        )
        self.assertEqual(
            derive_comparability(selected, a4, admitted_skill_count=1), expected
        )

    def test_task_comparison_rejects_incomplete_demand_and_substituted_task_pins(self):
        from research_workbench.evaluation.comparability import _task_comparison_surface
        from research_workbench.evaluation.qualification import (
            validate_requirement_closure,
        )

        _expected, a3, _a4, manifest, extra, combined = (
            self._multi_task_comparison_inputs()
        )
        selected_arm = manifest["arms"][2]
        # Case selection cannot excuse an incomplete selected Task, nor a
        # missing other Task in the whole-arm qualification that precedes it.
        with self.assertRaisesRegex(EvaluationValidationError, "Requirement set"):
            _task_comparison_surface(
                self.inputs(), [*extra, *a3[:-1]], manifest, task_ref=self.f.task_ref
            )
        with self.assertRaisesRegex(EvaluationValidationError, "Requirement set"):
            validate_requirement_closure(self.inputs(), a3, manifest, selected_arm)
        for key, value in (
            ("path", "evaluation/task-alias.json"),
            ("sha256", "0" * 64),
        ):
            wrong_pin = {**self.f.task_ref, key: value}
            with (
                self.subTest(pin_field=key),
                self.assertRaisesRegex(
                    EvaluationValidationError, "cover every qualified Task"
                ),
            ):
                _task_comparison_surface(
                    self.inputs(), combined, manifest, task_ref=wrong_pin
                )

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

        chains = plain(self.overlay())
        surface = comparison_surface(chains)
        for field in ("supported_inputs", "supported_outputs", "provided_capabilities"):
            changed = copy.deepcopy(chains)
            changed[0]["interface"][field] = ["other-contract"]
            result = derive_comparability(
                surface, comparison_surface(changed), admitted_skill_count=1
            )
            with self.subTest(interface_field=field):
                self.assertEqual(result["status"], "skill-bearing-package")
                self.assertEqual(result["mismatches"], ["interfaces"])
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
        self.assertEqual(len(self.overlay(document)), 2)
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
