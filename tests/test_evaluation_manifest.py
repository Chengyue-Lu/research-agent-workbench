"""M5-003 evaluation manifest tests."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from research_workbench.evaluation.manifest import (
    FIXED_METRIC_SET,
    PHASE_D_ARMS,
    check_arm_map_and_arms,
    check_evaluation_manifest,
    check_evidence_classes,
    check_frozen_conditions,
    check_metric_set,
)
from research_workbench.io import load_document
from research_workbench.validation.documents import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "evals" / "manifests" / "EVAL-MANIFEST-M5-003-001.yaml"


def _manifest() -> dict:
    return load_document(FIXTURE)


class FixedVocabularyTest(unittest.TestCase):
    def test_thirteen_fixed_metrics(self) -> None:
        self.assertEqual(len(FIXED_METRIC_SET), 13)
        self.assertEqual(
            {metric.direction for metric in FIXED_METRIC_SET},
            {"lower-is-better"},
        )

    def test_fixture_metric_set_is_verbatim(self) -> None:
        self.assertEqual(check_metric_set(_manifest()["metric_set"]), [])


class MetricSetDriftTest(unittest.TestCase):
    def test_missing_metric_is_rejected(self) -> None:
        metrics = [dict(item) for item in _manifest()["metric_set"]]
        removed = metrics.pop(0)
        drifts = check_metric_set(metrics)
        self.assertTrue(any(removed["metric_id"] in drift for drift in drifts))

    def test_definition_drift_is_rejected(self) -> None:
        metrics = [dict(item) for item in _manifest()["metric_set"]]
        metrics[0]["definition"] = "A vaguer definition."
        self.assertNotEqual(check_metric_set(metrics), [])

    def test_extra_metric_is_rejected(self) -> None:
        metrics = [dict(item) for item in _manifest()["metric_set"]]
        metrics.append(
            {
                "metric_id": "vibes",
                "definition": "Feels good.",
                "unit": "count",
                "direction": "higher-is-better",
            }
        )
        self.assertTrue(any("outside the fixed vocabulary" in drift for drift in check_metric_set(metrics)))


class ArmMapTest(unittest.TestCase):
    def test_fixture_arms_are_consistent(self) -> None:
        self.assertEqual(check_arm_map_and_arms(_manifest()), [])

    def test_unknown_phase_d_arm_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["arm_map"]["lightweight"] = " turbo-agent "
        problems = check_arm_map_and_arms(manifest)
        self.assertTrue(any("arm_map.lightweight" in problem for problem in problems))

    def test_unconfigured_referenced_arm_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["arms"] = [arm for arm in manifest["arms"] if arm["arm_id"] != "plain-agent-tool"]
        problems = check_arm_map_and_arms(manifest)
        self.assertTrue(any("unconfigured arm" in problem for problem in problems))

    def test_unreferenced_configured_arm_is_allowed(self) -> None:
        # four-arm expressibility: a manifest may configure the full Phase D
        # comparison even though the M5 vocabulary maps only three arms
        manifest = _manifest()
        problems = check_arm_map_and_arms(manifest)
        self.assertEqual(problems, [])
        configured = {arm["arm_id"] for arm in manifest["arms"]}
        self.assertEqual(configured, set(PHASE_D_ARMS))


class FrozenConditionsTest(unittest.TestCase):
    def test_single_pool_passes(self) -> None:
        self.assertEqual(check_frozen_conditions(_manifest()), [])

    def test_diverging_pools_are_rejected(self) -> None:
        manifest = _manifest()
        manifest["arms"][0]["model_pool_ref"]["path"] = "registry/models/other.yaml"
        problems = check_frozen_conditions(manifest)
        self.assertTrue(any("one frozen pool" in problem for problem in problems))

    def test_missing_pools_are_rejected(self) -> None:
        manifest = _manifest()
        for arm in manifest["arms"]:
            arm.pop("model_pool_ref")
        problems = check_frozen_conditions(manifest)
        self.assertTrue(any("not frozen" in problem for problem in problems))


class EvidenceClassesTest(unittest.TestCase):
    def test_fixture_declares_evidence_classes(self) -> None:
        self.assertEqual(check_evidence_classes(_manifest()), [])

    def test_missing_evidence_classes_is_rejected(self) -> None:
        manifest = _manifest()
        del manifest["frozen_conditions"]["evidence_classes"]
        problems = check_evaluation_manifest(manifest)
        self.assertTrue(any("evidence_classes" in problem for problem in problems))

    def test_empty_evidence_classes_fails_schema(self) -> None:
        manifest = _manifest()
        manifest["frozen_conditions"]["evidence_classes"] = []
        self.assertNotEqual(
            SchemaCatalog().validate("evaluation_manifest", manifest), []
        )


class SchemaAndKindTest(unittest.TestCase):
    def test_schema_valid_and_kind_inferred(self) -> None:
        manifest = _manifest()
        self.assertEqual(infer_document_kind(manifest), "evaluation_manifest")
        self.assertEqual(SchemaCatalog().validate("evaluation_manifest", manifest), [])

    def test_candidate_skill_arm_requires_evaluation_ref(self) -> None:
        manifest = _manifest()
        for arm in manifest["arms"]:
            if arm["arm_id"] == "mode-candidate-skill":
                arm.pop("skill_evaluation_ref")
        errors = SchemaCatalog().validate("evaluation_manifest", manifest)
        self.assertNotEqual(errors, [])


class CrossValidationTest(unittest.TestCase):
    def test_validate_documents_catches_drift(self) -> None:
        from research_workbench.validation.documents import validate_documents

        manifest = _manifest()
        manifest["metric_set"][0]["definition"] = "Drifted."
        issues = validate_documents({Path("examples/evals/manifests/x.yaml"): manifest})
        self.assertTrue(
            any(issue.code == "EVAL-MANIFEST-INVALID" and "definition drift" in issue.message for issue in issues)
        )

    def test_validate_documents_passes_clean_fixture(self) -> None:
        from research_workbench.validation.documents import validate_documents

        issues = validate_documents({FIXTURE: _manifest()})
        self.assertEqual(
            [issue for issue in issues if issue.code == "EVAL-MANIFEST-INVALID"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
