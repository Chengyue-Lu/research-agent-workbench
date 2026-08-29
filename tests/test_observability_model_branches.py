from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
import unittest

from research_workbench.contracts import ContractError
from research_workbench.io import load_document
from research_workbench.observability import models as models_module
from research_workbench.protocol import ProjectProtocol


ROOT = Path(__file__).resolve().parents[1]


class ObservabilityModelBranchTests(unittest.TestCase):
    def test_optional_usage_values_reject_bool_negative_and_wrong_types(self) -> None:
        self.assertIsNone(models_module._optional_non_negative_int({}, "value"))
        self.assertEqual(2, models_module._optional_non_negative_int({"value": 2}, "value"))
        self.assertEqual(2.5, models_module._optional_non_negative_number({"value": 2.5}, "value"))
        for value in (True, -1, "1"):
            with self.subTest(value=value), self.assertRaises(ContractError):
                models_module._optional_non_negative_int({"value": value}, "value")
        for value in (True, -0.1, "1"):
            with self.subTest(value=value), self.assertRaises(ContractError):
                models_module._optional_non_negative_number({"value": value}, "value")

    def test_runtime_model_usage_and_trace_contracts_fail_closed(self) -> None:
        with self.assertRaises(ContractError):
            models_module.ExecutionRuntime.from_mapping(
                {
                    "name": "runtime",
                    "version": "1",
                    "adapter_version": "1",
                    "capability_snapshot_ref": "../outside.yaml",
                }
            )
        for data in (
            {"provider": "p", "model": "m"},
            {"provider": "p", "model": "m", "requests": 1, "provider_reported_cost": 1.0},
            {"provider": "p", "model": "m", "requests": 1, "currency": "USD"},
        ):
            with self.assertRaises(ContractError):
                models_module.ModelUsageRecord.from_mapping(data)
        usage = models_module.ModelUsageRecord.from_mapping(
            {
                "provider": "p",
                "model": "m",
                "requests": 1,
                "input_tokens": 2,
                "output_tokens": 3,
                "cached_input_tokens": 1,
                "reasoning_tokens": 1,
                "provider_reported_cost": 0.1,
                "currency": "USD",
            }
        )
        self.assertEqual("USD", usage.currency)

        for data in (
            {"mode": "unknown", "external": False, "sensitive_data_detected": False, "redactions_applied": 0},
            {"mode": "minimal", "external": "no", "sensitive_data_detected": False, "redactions_applied": 0},
            {"mode": "minimal", "external": False, "sensitive_data_detected": False},
        ):
            with self.assertRaises(ContractError):
                models_module.TracePolicyRecord.from_mapping(data)

    def test_coordination_ratios_cover_tokens_seconds_zero_and_unknown(self) -> None:
        base = {
            "delegated_attempts": 0,
            "handoff_count": 0,
            "review_rounds": 0,
            "max_parallel_observed": 0,
        }
        with self.assertRaises(ContractError):
            models_module.CoordinationUsage.from_mapping({})
        self.assertEqual(
            (0.25, "tokens"),
            models_module.CoordinationUsage.from_mapping(
                {**base, "coordination_tokens": 1, "execution_tokens": 3}
            ).cost_ratio,
        )
        self.assertEqual(
            (0.0, "tokens"),
            models_module.CoordinationUsage.from_mapping(
                {**base, "coordination_tokens": 0, "execution_tokens": 0}
            ).cost_ratio,
        )
        self.assertEqual(
            (0.25, "seconds"),
            models_module.CoordinationUsage.from_mapping(
                {**base, "coordination_seconds": 1, "execution_seconds": 3}
            ).cost_ratio,
        )
        self.assertEqual(
            (None, None), models_module.CoordinationUsage.from_mapping(base).cost_ratio
        )

    def test_execution_receipt_rejects_lifecycle_usage_reference_and_time_drift(self) -> None:
        base = load_document(ROOT / "examples" / "observability" / "execution-evidence-contract.yaml")
        self.assertIsNotNone(models_module.ExecutionReceipt.from_mapping(base))
        mutations = (
            ("execution_kind", "unknown"),
            ("task_revision", 0),
            ("status", "unknown"),
            ("completion_claim", "task-complete"),
            ("model_usage_status", "unknown"),
            ("trace_ref", "not-a-reference"),
            ("attempt_ref", "../outside.yaml"),
            ("output_refs", ["same", "same"]),
            ("finished_at", "2020-01-01T00:00:00Z"),
        )
        for field, value in mutations:
            changed = copy.deepcopy(base)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                models_module.ExecutionReceipt.from_mapping(changed)

        changed = copy.deepcopy(base)
        changed["status"] = "failed"
        changed["completion_claim"] = "contract-satisfied"
        with self.assertRaises(ContractError):
            models_module.ExecutionReceipt.from_mapping(changed)
        changed = copy.deepcopy(base)
        changed["model_usage_status"] = "not-applicable"
        changed["model_usage"] = [{"provider": "p", "model": "m", "requests": 1}]
        with self.assertRaises(ContractError):
            models_module.ExecutionReceipt.from_mapping(changed)
        changed = copy.deepcopy(base)
        changed["model_usage_status"] = "measured"
        changed["model_usage"] = []
        with self.assertRaises(ContractError):
            models_module.ExecutionReceipt.from_mapping(changed)

    def test_receipt_reference_validator_reports_missing_inputs_without_replay(self) -> None:
        receipt = models_module.ExecutionReceipt.from_mapping(
            load_document(ROOT / "examples" / "observability" / "execution-evidence-contract.yaml")
        )
        protocol = ProjectProtocol.from_mapping(
            load_document(ROOT / "examples" / "project-protocol.yaml")
        )
        missing = replace(
            receipt,
            attempt_ref="missing-attempt.yaml",
            skill_assignment_ref="missing-assignment.yaml",
            agent_profile_ref="missing-profile.yaml",
            context_snapshot_ref="missing-context.yaml",
            output_refs=("missing-output.txt",),
            validation_refs=("missing-validation.yaml",),
            trace_ref=None,
        )
        risks = models_module.check_execution_receipt(missing, protocol, root=ROOT)
        codes = {risk.code for risk in risks}
        self.assertIn("REF-MISSING", codes)
        self.assertIn("RECEIPT-MACHINE-VALIDATION-MISSING", codes)

        paused = replace(
            missing,
            status="safe-paused",
            completion_claim="none",
            context_snapshot_ref=None,
            output_refs=(),
            validation_refs=(),
        )
        paused_codes = {
            risk.code
            for risk in models_module.check_execution_receipt(paused, protocol, root=ROOT)
        }
        self.assertIn("RECEIPT-SAFE-PAUSE-CONTEXT-MISSING", paused_codes)


if __name__ == "__main__":
    unittest.main()
