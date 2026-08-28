from __future__ import annotations

import copy
from pathlib import Path
import unittest

from research_workbench.context import models as models_module
from research_workbench.contracts import ContractError
from research_workbench.io import load_document


ROOT = Path(__file__).resolve().parents[1]


class ContextModelBranchTests(unittest.TestCase):
    def test_primitive_threshold_policy_budget_and_assessment_guards(self) -> None:
        for value in (True, -1, "1"):
            with self.assertRaises(ContractError):
                models_module._non_negative_int(value, "value")
        with self.assertRaises(ContractError):
            models_module._unique_strings(("same", "same"), "values")
        with self.assertRaises(ContractError):
            models_module.ContextThreshold.from_mapping({"warn": 2, "rollover": 1}, "threshold")

        valid_policy = {
            "proactive_checkpoint": True,
            "main_raw_material": "forbidden",
            "thresholds": models_module.DEFAULT_CONTEXT_THRESHOLDS,
        }
        for mutation in (
            {"proactive_checkpoint": "yes"},
            {"main_raw_material": "always"},
            {"thresholds": {**models_module.DEFAULT_CONTEXT_THRESHOLDS, "unknown": {"warn": 1, "rollover": 2}}},
            {"thresholds": {}},
        ):
            document = copy.deepcopy(valid_policy)
            document.update(mutation)
            with self.assertRaises(ContractError):
                models_module.ContextPolicySnapshot.from_mapping(document)
        with self.assertRaises(ContractError):
            models_module.ContextPolicySnapshot.from_project_policy(
                {"proactive_checkpoint": True, "main_raw_material": "forbidden", "pressure_thresholds": {"unknown": {}}}
            )
        first_metric = next(iter(models_module.THRESHOLDED_CONTEXT_METRICS))
        with self.assertRaises(ContractError):
            models_module.ContextPolicySnapshot.from_project_policy(
                {"proactive_checkpoint": True, "main_raw_material": "forbidden", "pressure_thresholds": {first_metric: []}}
            )

        for budget in (
            {"status": "unknown"},
            {"status": "unavailable", "unit": "tokens"},
            {"status": "measured", "unit": "bytes", "remaining": 1, "next_atomic_cost": 1, "closeout_cost": 1, "safety_margin": 1},
        ):
            with self.assertRaises(ContractError):
                models_module.ContextBudgetEstimate.from_mapping(budget)
        with self.assertRaises(ContractError):
            models_module.ContextAssessment.from_mapping(
                {"level": "unknown", "triggered_rules": [], "required_actions": []}
            )
        with self.assertRaises(ContractError):
            models_module.ContextAssessment.from_mapping(
                {"level": "warn", "triggered_rules": ["same", "same"], "required_actions": []}
            )

    def test_active_task_and_main_state_identity_references_are_strict(self) -> None:
        for active in (
            {"task_id": "T", "status": "unknown"},
            {"task_id": "T", "status": "active", "expected_handoff": "../outside"},
        ):
            with self.assertRaises(ContractError):
                models_module.ActiveTaskState.from_mapping(active)

        base = load_document(ROOT / "examples" / "main-state.yaml")
        self.assertIsNotNone(models_module.MainStatePacket.from_mapping(base))
        mutations = []
        changed = copy.deepcopy(base); changed["continuity_status"] = "unknown"; mutations.append(changed)
        changed = copy.deepcopy(base); changed["artifact_index_refs"] = ["../outside"]; mutations.append(changed)
        changed = copy.deepcopy(base); changed.pop("machine_state_refs"); mutations.append(changed)
        changed = copy.deepcopy(base); changed["machine_state_refs"] = []; mutations.append(changed)
        changed = copy.deepcopy(base); changed["machine_state_refs"] = [base["machine_state_refs"][0]] * 2; mutations.append(changed)
        changed = copy.deepcopy(base); changed["checkpoint_digest"] = "BAD"; mutations.append(changed)
        changed = copy.deepcopy(base); changed["git_head"] = "not-a-git-id"; mutations.append(changed)
        for index, document in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(ContractError):
                models_module.MainStatePacket.from_mapping(document)

    def test_assessment_exercises_pressure_raw_material_compaction_and_hidden_state(self) -> None:
        policy = models_module.ContextPolicySnapshot.from_mapping(
            {
                "proactive_checkpoint": True,
                "main_raw_material": "on-demand",
                "thresholds": models_module.DEFAULT_CONTEXT_THRESHOLDS,
            }
        )
        metric = next(iter(models_module.THRESHOLDED_CONTEXT_METRICS))
        metrics = {
            metric: policy.thresholds[metric].rollover,
            "raw_material_chars": 1,
            "compaction_events": 1,
            "hidden_decisions": 1,
        }
        assessment = models_module.assess_context(
            scope="main",
            metrics=metrics,
            unknown_metrics=(),
            handoff_ready=None,
            context_budget=models_module.ContextBudgetEstimate("unavailable"),
            policy=policy,
        )
        self.assertEqual("block", assessment.level)
        self.assertLessEqual(
            {
                "CTX-MAIN-RAW-MATERIAL-ON-DEMAND",
                "CTX-AUTO-COMPACTION",
                "CTX-HIDDEN-STATE",
                "CTX-NEXT-AWU-COST-UNKNOWN",
            },
            set(assessment.triggered_rules),
        )

        base = load_document(ROOT / "examples" / "observability" / "context-main-warn.yaml")
        base["owner_ref"] = "TASK"
        base["handoff_audit_ref"] = "handoff/audit.yaml"
        snapshot = models_module.ContextSnapshot.from_mapping(base)
        rendered = snapshot.to_mapping()
        self.assertEqual("TASK", rendered["owner_ref"])
        self.assertEqual("handoff/audit.yaml", rendered["handoff_audit_ref"])


if __name__ == "__main__":
    unittest.main()
