from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from research_workbench.artifacts.integrity import hash_file
from research_workbench.evaluation import skill_evaluation as evaluation_module


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class SkillEvaluationHelperTests(unittest.TestCase):
    def test_file_reference_validation_is_exact_and_root_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.txt"
            source.write_text("bounded", encoding="utf-8")
            valid = {"path": source.name, "sha256": hash_file(source)}
            self.assertEqual([], evaluation_module._check_file_ref(root, valid, "source"))

            cases = (
                ({}, "EVAL-REF-INVALID"),
                ({"path": "../outside", "sha256": "0" * 64}, "EVAL-REF-OUTSIDE"),
                ({"path": "missing", "sha256": "0" * 64}, "EVAL-REF-MISSING"),
                ({"path": source.name, "sha256": "0" * 64}, "EVAL-REF-HASH"),
            )
            for reference, code in cases:
                with self.subTest(code=code):
                    risks = evaluation_module._check_file_ref(root, reference, "source")
                    self.assertEqual([code], [risk.code for risk in risks])

    def test_candidate_registry_pin_detects_missing_invalid_unpinned_and_drift(self) -> None:
        document = {
            "candidate_id": "candidate-a",
            "skill_source_ref": {"path": "skill/SKILL.md", "sha256": "a" * 64},
            "skill_package_hash": "b" * 64,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            risks = evaluation_module._check_candidate_pin(document, root, "missing.json")
            self.assertEqual("EVAL-CANDIDATE-REGISTRY-MISSING", risks[0].code)

            registry = root / "candidates.json"
            registry.write_text("not-json", encoding="utf-8")
            risks = evaluation_module._check_candidate_pin(document, root, registry)
            self.assertEqual("EVAL-CANDIDATE-REGISTRY-INVALID", risks[0].code)

            _write_json(registry, {"registry_kind": "skill_candidates", "candidates": []})
            risks = evaluation_module._check_candidate_pin(document, root, registry)
            self.assertEqual("EVAL-CANDIDATE-UNPINNED", risks[0].code)

            _write_json(
                registry,
                {
                    "registry_kind": "skill_candidates",
                    "candidates": [
                        {
                            "candidate_id": "candidate-a",
                            "source_path": "other/SKILL.md",
                            "content_hash": "c" * 64,
                            "package_hash": "d" * 64,
                        }
                    ],
                },
            )
            risks = evaluation_module._check_candidate_pin(document, root, registry)
            self.assertEqual("EVAL-CANDIDATE-PIN-DRIFT", risks[0].code)
            self.assertIn("source_path", risks[0].message)
            self.assertIn("content_hash", risks[0].message)
            self.assertIn("package_hash", risks[0].message)

    def test_human_decision_must_be_valid_and_bind_all_admission_fields(self) -> None:
        evaluation = {
            "evaluation_id": "EVAL-1",
            "candidate_id": "candidate-a",
            "admission": {"outcome": "accept"},
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            risks = evaluation_module._check_human_decision(evaluation, root, "missing.json")
            self.assertEqual("EVAL-DECISION-MISSING", risks[0].code)

            decision = root / "decision.json"
            _write_json(decision, {"object_type": "claim"})
            risks = evaluation_module._check_human_decision(evaluation, root, decision.name)
            self.assertEqual("EVAL-DECISION-INVALID", risks[0].code)

            valid = {
                "schema_version": "0.1.0",
                "object_type": "decision",
                "object_id": "D-1",
                "revision": 1,
                "status": "accepted",
                "decision": "Admit the candidate.",
                "scope": ["candidate-a"],
                "reason_refs": ["EVAL-1"],
                "actor": "human-reviewer",
                "timestamp": "2026-08-28T00:00:00Z",
                "metadata": {
                    "skill_evaluation_id": "EVAL-1",
                    "skill_candidate_id": "candidate-a",
                    "decision_owner": "human",
                    "skill_admission_outcome": "accept",
                },
            }
            _write_json(decision, valid)
            self.assertEqual([], evaluation_module._check_human_decision(evaluation, root, decision.name))

            valid["metadata"]["decision_owner"] = "agent"
            _write_json(decision, valid)
            risks = evaluation_module._check_human_decision(evaluation, root, decision.name)
            self.assertEqual("EVAL-DECISION-DRIFT", risks[0].code)
            self.assertIn("decision_owner", risks[0].message)

    def test_paired_input_measurement_rejects_missing_and_non_text_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task = root / "task.txt"
            source = root / "source.txt"
            task.write_text("abc", encoding="utf-8")
            source.write_text("defg", encoding="utf-8")
            case = {
                "task_contract_ref": {"path": task.name},
                "input_ref": {"path": source.name},
            }
            self.assertEqual(7, evaluation_module._paired_input_characters(root, case))
            self.assertIsNone(evaluation_module._paired_input_characters(root, {}))

            source.write_bytes(b"\xff\xfe\x00")
            self.assertIsNone(evaluation_module._paired_input_characters(root, case))
            self.assertEqual({}, evaluation_module._mapping(None))
            self.assertEqual("abcd", evaluation_module._normalized_hash("sha256:ABCD"))

    def test_live_evaluation_reports_missing_protocol_case_review_and_admission_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill_dir = root / "skill"
            skill_dir.mkdir()
            skill_source = skill_dir / "SKILL.md"
            skill_source.write_text("bounded skill", encoding="utf-8")
            document = {
                "evaluation_id": "EVAL-ADVERSARIAL",
                "candidate_id": "candidate-a",
                "skill_id": "skill-a",
                "evaluation_scope": "live-forward-test",
                "skill_source_ref": {
                    "path": "skill/SKILL.md",
                    "sha256": hash_file(skill_source),
                },
                "skill_package_hash": "0" * 64,
                "project_protocol_ref": {},
                "model_config_ref": {},
                "protocol": {
                    "required_case_kinds": ["required-kind"],
                    "minimum_live_cases": 3,
                    "required_review_criteria": ["quality"],
                },
                "cases": [
                    {
                        "case_id": "CASE",
                        "case_kind": "other-kind",
                        "arms": {"baseline": {}, "with_skill": {}},
                        "review": {
                            "status": "completed",
                            "reviewer_kind": "agent",
                            "reviewer_independent": False,
                            "blinded": False,
                            "order_revealed_after_scoring": False,
                            "criteria": [],
                        },
                    },
                    {
                        "case_id": "CASE",
                        "case_kind": "other-kind",
                        "arms": {"baseline": {}, "with_skill": {}},
                        "review": {"status": "pending"},
                    },
                ],
                "admission": {
                    "status": "human-decided",
                    "decision_ref": "missing-decision.yaml",
                },
            }
            assessment = evaluation_module.assess_skill_evaluation(document, root=root)
            codes = {risk.code for risk in assessment.risks}
            self.assertLessEqual(
                {
                    "EVAL-SKILL-PACKAGE-DRIFT",
                    "EVAL-LIVE-CASE-COUNT",
                    "EVAL-CASE-DUPLICATE",
                    "EVAL-WITH-SKILL-CHECK",
                    "EVAL-BASELINE-CONTAMINATED",
                    "EVAL-SKILL-NOT-LOADED",
                    "EVAL-CONTEXT-UNMEASURED",
                    "EVAL-REVIEW-PENDING",
                    "EVAL-HUMAN-REVIEW-MISSING",
                    "EVAL-REVIEW-NOT-INDEPENDENT",
                    "EVAL-REVIEW-UNBLINDED",
                    "EVAL-REVIEW-CRITERIA",
                    "EVAL-STATUS-OVERCLAIM",
                    "EVAL-DECISION-MISSING",
                },
                codes,
            )

    def test_receipt_loader_rejects_missing_scalar_and_schema_invalid_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = {
                "execution_receipt_ref": "missing.yaml",
            }
            self.assertEqual(
                "EVAL-RECEIPT-MISSING",
                evaluation_module._load_receipt(
                    root,
                    base,
                    "CASE",
                    "baseline",
                    evaluation={},
                    project_protocol=None,
                )[2][0].code,
            )
            scalar = root / "scalar.yaml"
            scalar.write_text("[]\n", encoding="utf-8")
            base["execution_receipt_ref"] = scalar.name
            self.assertEqual(
                "EVAL-RECEIPT-INVALID",
                evaluation_module._load_receipt(
                    root,
                    base,
                    "CASE",
                    "baseline",
                    evaluation={},
                    project_protocol=None,
                )[2][0].code,
            )
            invalid = root / "invalid.yaml"
            invalid.write_text("{}\n", encoding="utf-8")
            base["execution_receipt_ref"] = invalid.name
            self.assertEqual(
                "EVAL-RECEIPT-INVALID",
                evaluation_module._load_receipt(
                    root,
                    base,
                    "CASE",
                    "baseline",
                    evaluation={},
                    project_protocol=None,
                )[2][0].code,
            )


if __name__ == "__main__":
    unittest.main()
