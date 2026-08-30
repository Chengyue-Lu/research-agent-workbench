"""M5-003 evaluation manifest and baseline harness tests."""

from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import yaml

from research_workbench.cli import main
from research_workbench.evaluation.manifest import (
    FIXED_METRIC_SET,
    PHASE_D_ARMS,
    check_evaluation_manifest,
    check_evidence_classes,
    check_frozen_conditions,
    check_metric_set,
    check_reference_closure,
    check_snapshot_treatment_semantics,
    check_treatment_arms,
    check_treatment_bindings,
    compile_baseline_plan,
)
from research_workbench.io import load_document
from research_workbench.validation.documents import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "evals" / "manifests" / "EVAL-MANIFEST-M5-003-001.yaml"


def _manifest() -> dict:
    return load_document(FIXTURE)


def _schema_errors(document: dict):
    return SchemaCatalog().validate("evaluation_manifest", document)


def _arm(document: dict, arm_id: str) -> dict:
    return next(arm for arm in document["arms"] if arm["arm_id"] == arm_id)


def _run_plan(document: dict) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as directory:
        manifest_path = Path(directory) / "manifest.yaml"
        manifest_path.write_text(
            yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
        )
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(
                ["eval", "plan", str(manifest_path), "--root", str(ROOT)]
            )
    return exit_code, output.getvalue()


class FixedVocabularyTest(unittest.TestCase):
    def test_thirteen_fixed_metrics(self) -> None:
        self.assertEqual(len(FIXED_METRIC_SET), 13)
        self.assertEqual({metric.direction for metric in FIXED_METRIC_SET}, {"lower-is-better"})

    def test_fixture_metric_set_is_verbatim(self) -> None:
        self.assertEqual(check_metric_set(_manifest()["metric_set"]), [])

    def test_missing_metric_is_rejected(self) -> None:
        metrics = copy.deepcopy(_manifest()["metric_set"])
        removed = metrics.pop(0)
        self.assertTrue(any(removed["metric_id"] in item for item in check_metric_set(metrics)))

    def test_definition_drift_is_rejected(self) -> None:
        metrics = copy.deepcopy(_manifest()["metric_set"])
        metrics[0]["definition"] = "A vaguer definition."
        self.assertNotEqual(check_metric_set(metrics), [])

    def test_extra_metric_is_rejected(self) -> None:
        metrics = copy.deepcopy(_manifest()["metric_set"])
        metrics.append(
            {
                "metric_id": "vibes",
                "definition": "Feels good.",
                "unit": "count",
                "direction": "higher-is-better",
            }
        )
        self.assertTrue(any("outside the fixed vocabulary" in item for item in check_metric_set(metrics)))


class CanonicalTreatmentArmTest(unittest.TestCase):
    def test_fixture_contains_each_phase_d_treatment_once(self) -> None:
        manifest = _manifest()
        self.assertNotIn("arm_map", manifest)
        self.assertEqual(check_treatment_arms(manifest), [])
        self.assertEqual({arm["arm_id"] for arm in manifest["arms"]}, set(PHASE_D_ARMS))

    def test_duplicate_arm_id_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["arms"][-1]["arm_id"] = "plain-agent"
        problems = check_treatment_arms(manifest)
        self.assertTrue(any("duplicate" in item for item in problems))
        self.assertTrue(any("missing" in item for item in problems))

    def test_missing_phase_d_treatment_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["arms"].pop()
        self.assertTrue(any("missing" in item for item in check_treatment_arms(manifest)))
        self.assertNotEqual(_schema_errors(manifest), [])

    def test_legacy_coordination_arm_map_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["arm_map"] = {"single-agent": "plain-agent"}
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(any("arm_map is forbidden" in item for item in check_treatment_arms(manifest)))


class SharedControlledConditionsTest(unittest.TestCase):
    def test_fixture_freezes_complete_shared_conditions(self) -> None:
        self.assertEqual(check_frozen_conditions(_manifest()), [])

    def test_exact_model_id_is_required(self) -> None:
        manifest = _manifest()
        del manifest["frozen_conditions"]["model"]["model_id"]
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(any("exact model_id" in item for item in check_frozen_conditions(manifest)))

    def test_different_task_set_per_arm_is_rejected(self) -> None:
        manifest = _manifest()
        _arm(manifest, "plain-agent")["task_packet_refs"] = [
            {"path": "other-task.yaml", "sha256": "0" * 64}
        ]
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(any("task_packet_refs" in item for item in check_frozen_conditions(manifest)))

    def test_different_exact_model_per_arm_is_rejected(self) -> None:
        manifest = _manifest()
        _arm(manifest, "plain-agent-tool")["model"] = {
            "slot_id": "worker",
            "provider_adapter": "other",
            "model_id": "other-model",
        }
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(any("model" in item for item in check_frozen_conditions(manifest)))

    def test_different_budget_per_arm_is_rejected(self) -> None:
        manifest = _manifest()
        _arm(manifest, "mode-no-skill")["budget"] = {"max_turns": 99}
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(any("budget" in item for item in check_frozen_conditions(manifest)))

    def test_different_context_per_arm_is_rejected(self) -> None:
        manifest = _manifest()
        _arm(manifest, "mode-candidate-skill")["context"] = {"max_input_tokens": 99}
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(any("context" in item for item in check_frozen_conditions(manifest)))

    def test_budget_and_context_are_required(self) -> None:
        for key in ("budget", "context"):
            with self.subTest(key=key):
                manifest = _manifest()
                del manifest["frozen_conditions"][key]
                self.assertNotEqual(_schema_errors(manifest), [])


class TreatmentBindingTest(unittest.TestCase):
    def test_fixture_treatments_are_exact(self) -> None:
        self.assertEqual(check_treatment_bindings(_manifest()), [])

    def test_plain_arms_suppress_and_mode_arms_freeze_control(self) -> None:
        manifest = _manifest()
        self.assertEqual(
            _arm(manifest, "plain-agent")["treatment_control"]["mode_method_control"],
            "suppressed",
        )
        self.assertEqual(
            _arm(manifest, "plain-agent-tool")["treatment_control"]["mode_method_control"],
            "suppressed",
        )
        for arm_id in ("mode-no-skill", "mode-candidate-skill"):
            with self.subTest(arm_id=arm_id):
                control = _arm(manifest, arm_id)["treatment_control"]
                self.assertEqual(control["mode_method_control"], "exact")
                self.assertEqual(control["mode_refs"], ["evidence-synthesis@0.1.0"])
                self.assertEqual(len(control["method_resolution_refs"]), 1)

    def test_plain_arm_cannot_claim_mode_method_control(self) -> None:
        manifest = _manifest()
        _arm(manifest, "plain-agent")["treatment_control"] = {
            "mode_method_control": "exact",
            "mode_refs": ["evidence-synthesis@0.1.0"],
            "method_resolution_refs": copy.deepcopy(
                _arm(manifest, "mode-no-skill")["treatment_control"][
                    "method_resolution_refs"
                ]
            ),
        }
        self.assertTrue(
            any("suppressed" in item for item in check_treatment_bindings(manifest))
        )

    def test_mode_arm_requires_exact_control_refs(self) -> None:
        manifest = _manifest()
        del _arm(manifest, "mode-no-skill")["treatment_control"][
            "method_resolution_refs"
        ]
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(
            any(
                "method_resolution_refs" in item
                for item in check_treatment_bindings(manifest)
            )
        )

    def test_plain_agent_tool_requires_snapshot(self) -> None:
        manifest = _manifest()
        _arm(manifest, "plain-agent-tool").pop("capability_snapshot_refs")
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(any("plain-agent-tool" in item for item in check_treatment_bindings(manifest)))

    def test_mode_no_skill_requires_snapshot(self) -> None:
        manifest = _manifest()
        _arm(manifest, "mode-no-skill").pop("capability_snapshot_refs")
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(any("mode-no-skill" in item for item in check_treatment_bindings(manifest)))

    def test_candidate_skill_requires_exact_binding(self) -> None:
        manifest = _manifest()
        _arm(manifest, "mode-candidate-skill").pop("skill_binding")
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(any("exact skill_binding" in item for item in check_treatment_bindings(manifest)))

    def test_candidate_skill_requires_evaluation_evidence(self) -> None:
        manifest = _manifest()
        _arm(manifest, "mode-candidate-skill").pop("skill_evaluation_ref")
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(any("skill_evaluation_ref" in item for item in check_treatment_bindings(manifest)))

    def test_plain_agent_cannot_smuggle_tool_snapshot(self) -> None:
        manifest = _manifest()
        _arm(manifest, "plain-agent")["capability_snapshot_refs"] = copy.deepcopy(
            _arm(manifest, "plain-agent-tool")["capability_snapshot_refs"]
        )
        self.assertNotEqual(_schema_errors(manifest), [])
        self.assertTrue(any("plain-agent" in item for item in check_treatment_bindings(manifest)))

    def test_reference_closure_matches_frozen_task_and_skill_evidence(self) -> None:
        self.assertEqual(check_reference_closure(ROOT, _manifest()), [])

    def test_snapshot_for_different_task_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["frozen_conditions"]["task_packet_refs"] = [
            {
                "path": "examples/quickstart/task-no-skill.yaml",
                "sha256": "62920ee816005668346067bbb397ef036a2258a555a6c057e010be98c74b51a1",
            }
        ]
        self.assertTrue(any("outside frozen_conditions" in item for item in check_reference_closure(ROOT, manifest)))

    def test_plain_agent_tool_rejects_non_tool_snapshot(self) -> None:
        manifest = _manifest()
        _arm(manifest, "plain-agent-tool")["capability_snapshot_refs"] = [
            {
                "path": "examples/capability-resolution/snapshots/no-skill-contract-check.yaml",
                "sha256": "30b177db7f0d9d76d87ec7623056f19554495f707f160ac22671b5f9a659544c",
            }
        ]
        self.assertTrue(
            any(
                "exact Tool supply" in item
                for item in check_reference_closure(ROOT, manifest)
            )
        )

    def test_mode_no_skill_rejects_skill_supply(self) -> None:
        snapshot = {
            "supply_identity": {
                "supply_kind": "tool",
                "components": [
                    {"component_kind": "skill", "component_ref": "hidden-skill"}
                ],
            }
        }
        self.assertTrue(
            any(
                "must not expose Skill" in item
                for item in check_snapshot_treatment_semantics(
                    "mode-no-skill", snapshot
                )
            )
        )

    def test_mode_control_must_match_pinned_method_resolution(self) -> None:
        manifest = _manifest()
        _arm(manifest, "mode-candidate-skill")["treatment_control"]["mode_refs"] = [
            "simulation@0.1.0"
        ]
        problems = check_reference_closure(ROOT, manifest)
        self.assertTrue(any("frozen Task active_modes" in item for item in problems))
        self.assertTrue(any("pinned Method Resolution" in item for item in problems))

    def test_skill_binding_must_match_pinned_evaluation(self) -> None:
        manifest = _manifest()
        _arm(manifest, "mode-candidate-skill")["skill_binding"]["skill_id"] = "other-skill"
        self.assertTrue(any("skill_id" in item for item in check_reference_closure(ROOT, manifest)))

    def test_model_adapter_must_match_pinned_pool_slot(self) -> None:
        manifest = _manifest()
        manifest["frozen_conditions"]["model"]["provider_adapter"] = "other-adapter"
        self.assertTrue(
            any("provider_adapter" in item for item in check_reference_closure(ROOT, manifest))
        )


class EvidenceClassesTest(unittest.TestCase):
    def test_fixture_declares_evidence_classes(self) -> None:
        self.assertEqual(check_evidence_classes(_manifest()), [])

    def test_missing_evidence_classes_is_rejected(self) -> None:
        manifest = _manifest()
        del manifest["frozen_conditions"]["evidence_classes"]
        self.assertTrue(any("evidence_classes" in item for item in check_evaluation_manifest(manifest)))

    def test_empty_evidence_classes_fails_schema(self) -> None:
        manifest = _manifest()
        manifest["frozen_conditions"]["evidence_classes"] = []
        self.assertNotEqual(_schema_errors(manifest), [])


class BaselineHarnessTest(unittest.TestCase):
    def test_plan_is_deterministic_and_canonical(self) -> None:
        first = compile_baseline_plan(_manifest())
        second = compile_baseline_plan(_manifest())
        self.assertEqual(first, second)
        self.assertEqual([arm["arm_id"] for arm in first["arms"]], list(PHASE_D_ARMS))

    def test_every_arm_uses_same_frozen_condition_digest(self) -> None:
        plan = compile_baseline_plan(_manifest())
        digest = plan["frozen_conditions_sha256"]
        self.assertEqual({arm["frozen_conditions_sha256"] for arm in plan["arms"]}, {digest})
        self.assertEqual(plan["frozen_conditions"], _manifest()["frozen_conditions"])

    def test_invalid_manifest_cannot_compile(self) -> None:
        manifest = _manifest()
        manifest["arms"].pop()
        with self.assertRaises(ValueError):
            compile_baseline_plan(manifest)

    def test_eval_plan_uses_exact_reference_closure(self) -> None:
        exit_code, output = _run_plan(_manifest())
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output)["status"], "compiled-not-executed")

    def test_eval_plan_rejects_missing_reference(self) -> None:
        manifest = _manifest()
        manifest["frozen_conditions"]["task_packet_refs"][0] = {
            "path": "examples/missing-task.yaml",
            "sha256": "0" * 64,
        }
        exit_code, output = _run_plan(manifest)
        self.assertEqual(exit_code, 1)
        self.assertIn("REF-MISSING", output)
        self.assertNotIn("compiled-not-executed", output)

    def test_eval_plan_rejects_hash_drift(self) -> None:
        manifest = _manifest()
        manifest["frozen_conditions"]["task_packet_refs"][0]["sha256"] = "0" * 64
        exit_code, output = _run_plan(manifest)
        self.assertEqual(exit_code, 1)
        self.assertIn("REF-HASH-MISMATCH", output)
        self.assertNotIn("compiled-not-executed", output)


class SchemaAndCrossValidationTest(unittest.TestCase):
    def test_schema_valid_and_kind_inferred(self) -> None:
        manifest = _manifest()
        self.assertEqual(infer_document_kind(manifest), "evaluation_manifest")
        self.assertEqual(_schema_errors(manifest), [])

    def test_validate_documents_catches_drift(self) -> None:
        from research_workbench.validation.documents import validate_documents

        manifest = _manifest()
        manifest["arms"].pop()
        issues = validate_documents({Path("examples/evals/manifests/x.yaml"): manifest})
        self.assertTrue(any(issue.code == "EVAL-MANIFEST-INVALID" for issue in issues))

    def test_validate_documents_passes_clean_fixture(self) -> None:
        from research_workbench.validation.documents import validate_documents

        issues = validate_documents({FIXTURE: _manifest()})
        self.assertEqual(
            [issue for issue in issues if issue.code == "EVAL-MANIFEST-INVALID"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
