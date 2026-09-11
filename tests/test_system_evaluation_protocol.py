"""M5-006 protocol/qualification contracts, including attempted substitutions."""

import copy
import tempfile
import unittest
from pathlib import Path

from research_workbench.evaluation.pins import (
    EvaluationInputs,
    EvaluationValidationError,
    digest,
    timestamp,
)
from research_workbench.evaluation.qualification import (
    ceilings_narrow,
    validate_qualification,
)
from research_workbench.evaluation.system_protocol import (
    validate_measurement,
    validate_protocol,
)
from tests.system_evaluation_fixtures import ROOT, ProtocolFixtureMixin, record


class SystemProtocolTests(ProtocolFixtureMixin, unittest.TestCase):
    def inputs(self):
        return EvaluationInputs(self.f.root, ROOT / "schemas")

    def test_protocol_and_both_arm_qualifications_close(self):
        protocol = validate_protocol(self.inputs(), self.f.protocol_ref)
        self.assertEqual(protocol["rules"]["primary"]["contrast"], "A4-A2")
        self.assertFalse(protocol["rules"]["integrity_compensable"])
        for arm_id in ("plain-agent-tool", "mode-no-skill"):
            result = validate_qualification(
                self.inputs(),
                self.f.qualification(arm_id),
                expected_protocol_ref=self.f.protocol_ref,
            )
            self.assertEqual(
                result[0]["snapshot"]["qualification"], "runtime-execution"
            )

    def test_protocol_refuses_unregistered_design_and_interpretation_drift(self):
        changes = [
            (("rules", "primary", "contrast"), "A4-A3"),
            (("rules", "integrity_compensable"), True),
            (("rules", "weighted_aggregate_score"), True),
            (("rules", "unknown_is_zero"), True),
            (("design", "stopping", "completed_blocks"), 5),
            (("design", "replicates_per_case"), 0),
            (("design", "retry", "max_retries"), 1),
            (("design", "pilot_primary_eligible"), True),
            (("design", "analysis", "reveal_after"), "before-review"),
            (("design", "analysis", "confidence_level"), 1),
            (("design", "randomization", "seed"), -1),
            (("execution_bindings",), []),
            (("mode_documents",), []),
            (("action_documents",), []),
        ]
        for keys, value in changes:
            with self.subTest(keys=keys):
                document = copy.deepcopy(self.f.protocol)
                target = document
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                ref = self.f.write("evaluation/mutated-protocol.json", document)
                with self.assertRaises(EvaluationValidationError):
                    validate_protocol(self.inputs(), ref)

    def test_protocol_rechecks_decision_and_reference_bytes(self):
        path = self.f.root / self.f.protocol["decision_ref"]["path"]
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(EvaluationValidationError, "hash mismatch"):
            validate_protocol(self.inputs(), self.f.protocol_ref)

    def test_qualifications_reject_producer_and_outer_pin_substitution(self):
        for key, value in (
            ("producer", "evaluation-harness"),
            ("protocol_ref", self.f.manifest_ref),
            ("manifest_ref", self.f.protocol_ref),
            ("checked_at", "2026-09-10T00:00:00Z"),
            ("qualified", False),
            ("bindings", []),
        ):
            with self.subTest(key=key):
                document = self.f.qualification()
                document[key] = value
                with self.assertRaises(EvaluationValidationError):
                    validate_qualification(
                        self.inputs(),
                        document,
                        expected_protocol_ref=self.f.protocol_ref,
                    )

    def test_structural_snapshot_is_never_execution_evidence(self):
        for arm_id in ("plain-agent-tool", "mode-no-skill"):
            document = self.f.qualification(arm_id)
            document["bindings"][0]["runtime_snapshot_ref"] = document["bindings"][0][
                "frozen_snapshot_ref"
            ]
            with self.assertRaisesRegex(EvaluationValidationError, "runtime-execution"):
                validate_qualification(
                    self.inputs(), document, expected_protocol_ref=self.f.protocol_ref
                )

    def test_frozen_binding_interface_components_and_implementation_cannot_be_replaced(
        self,
    ):
        for key in (
            "frozen_snapshot_ref",
            "implementation_ref",
            "interface_ref",
            "component_refs",
        ):
            with self.subTest(key=key):
                document = self.f.qualification()
                replacement = self.f.qualification("mode-no-skill")["bindings"][0][key]
                document["bindings"][0][key] = replacement
                with self.assertRaises(EvaluationValidationError):
                    validate_qualification(
                        self.inputs(),
                        document,
                        expected_protocol_ref=self.f.protocol_ref,
                    )

    def test_implementation_drift_blocks_even_when_record_is_unchanged(self):
        path = (
            self.f.root
            / self.f.bindings["plain-agent-tool"]["implementation_ref"]["path"]
        )
        path.write_bytes(b"different implementation")
        with self.assertRaisesRegex(EvaluationValidationError, "hash mismatch"):
            validate_qualification(
                self.inputs(),
                self.f.qualification(),
                expected_protocol_ref=self.f.protocol_ref,
            )

    def test_unknown_fields_and_missing_pins_fail_closed(self):
        for key in ("task_completion", "runtime_input", "supply_selection"):
            document = self.f.qualification()
            document[key] = True
            with self.assertRaises(EvaluationValidationError):
                validate_qualification(
                    self.inputs(), document, expected_protocol_ref=self.f.protocol_ref
                )

    def test_ceiling_comparison_covers_roots_egress_and_side_effects(self):
        original = self.f.doc(self.f.runtime_refs["plain-agent-tool"]["path"])
        self.assertTrue(ceilings_narrow(original, original))
        for key, field, value in (
            ("supply_required_permissions", "filesystem", "workspace-write"),
            ("supply_required_permissions", "network", "allowed"),
            ("supply_required_permissions", "external_write", True),
            ("supply_data_egress", "allowed_payloads", ["secret"]),
            ("supply_data_egress", "policy", "allowlisted-only"),
            ("supply_data_egress", "forbidden_payloads", []),
            ("supply_side_effects", "allowed_effects", ["external-write"]),
        ):
            with self.subTest(field=field):
                modified = copy.deepcopy(original)
                modified[key][field] = value
                self.assertFalse(ceilings_narrow(original, modified))
        original["supply_required_permissions"]["allowed_roots"] = ["work/project"]
        narrowed = copy.deepcopy(original)
        narrowed["supply_required_permissions"]["allowed_roots"] = [
            "work/project/result"
        ]
        self.assertTrue(ceilings_narrow(original, narrowed))
        for roots in (["work/project-other"], ["work"], ["work/project/../private"]):
            narrowed["supply_required_permissions"]["allowed_roots"] = roots
            self.assertFalse(ceilings_narrow(original, narrowed))
        narrowed["supply_required_permissions"].pop("allowed_roots")
        self.assertFalse(ceilings_narrow(original, narrowed))

    def test_measurement_statuses_preserve_missingness(self):
        evidence = self.f.raw("evaluation/cost.txt", b"Synthetic measured cost 1")
        for status in ("measured", "estimated", "unavailable", "not-applicable"):
            document = record(
                "evaluation_measurement",
                "measurement_id",
                "MEASUREMENT",
                protocol_ref=self.f.protocol_ref,
                case_id="CASE",
                arm_id="plain-agent",
                metric_id="cost",
                status=status,
                unit="USD",
                value=1 if status in {"measured", "estimated"} else None,
                reason="Synthetic evidence",
                evidence_refs=[evidence] if status in {"measured", "estimated"} else [],
                estimation_method="Synthetic estimate"
                if status == "estimated"
                else None,
            )
            self.assertEqual(
                validate_measurement(
                    self.inputs(), document, expected_protocol_ref=self.f.protocol_ref
                )["status"],
                status,
            )
            if status in {"unavailable", "not-applicable"}:
                document["value"] = 0
                with self.assertRaises(EvaluationValidationError):
                    validate_measurement(
                        self.inputs(),
                        document,
                        expected_protocol_ref=self.f.protocol_ref,
                    )

    def test_pin_reader_rejects_traversal_missing_malformed_and_hash_drift(self):
        inputs = self.inputs()
        for path in (
            "../outside",
            "C:/outside",
            "/outside",
            "folder\\file",
            "missing",
            "",
        ):
            with self.subTest(path=path), self.assertRaises(EvaluationValidationError):
                inputs.read_bytes({"path": path, "sha256": "0" * 64})
        for content in (b"[", b"null", b"[]"):
            ref = self.f.raw("evaluation/bad.json", content)
            with self.assertRaises(EvaluationValidationError):
                inputs.read(ref)
        with self.assertRaises(EvaluationValidationError):
            timestamp("2026-09-11")
        with self.assertRaises(EvaluationValidationError):
            timestamp("not-a-time")
        self.assertEqual(digest({"a": 1, "b": 2}), digest({"b": 2, "a": 1}))

    def test_cached_protocol_is_copied_and_rechecks_every_reference(self):
        inputs = self.inputs()
        first = validate_protocol(inputs, self.f.protocol_ref)
        first["rules"]["primary"]["contrast"] = "tampered"
        second = validate_protocol(inputs, self.f.protocol_ref)
        self.assertEqual(second["rules"]["primary"]["contrast"], "A4-A2")
        manifest = inputs.manifest(self.f.manifest_ref)
        manifest["manifest_id"] = "tampered"
        self.assertNotEqual(
            inputs.manifest(self.f.manifest_ref)["manifest_id"], "tampered"
        )
        path = self.f.root / self.f.protocol["decision_ref"]["path"]
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(EvaluationValidationError, "hash mismatch"):
            validate_protocol(inputs, self.f.protocol_ref)

    def test_schema_changes_after_loading_are_not_hidden_by_validation_cache(self):
        import shutil

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "schemas", root / "schemas")
            inputs = EvaluationInputs(self.f.root, root / "schemas")
            inputs.validate("system_evaluation_protocol", self.f.protocol)
            path = root / "schemas/v0.1.0/system-evaluation-protocol.schema.json"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(EvaluationValidationError, "Schema bytes"):
                inputs.recheck()

    def test_full_binding_must_match_manifest_identities(self):
        for component, field in (
            ("model", "ref"),
            ("model", "slot"),
            ("adapter", "ref"),
            ("host", "ref"),
            ("runtime", "ref"),
        ):
            document = copy.deepcopy(self.f.protocol)
            document["execution_binding"][component][field] = "substituted"
            ref = self.f.write("evaluation/binding-drift.json", document)
            with (
                self.subTest(component=component, field=field),
                self.assertRaisesRegex(EvaluationValidationError, "frozen .* mismatch"),
            ):
                validate_protocol(self.inputs(), ref)

    def test_arm_identity_is_independent_of_manifest_array_order(self):
        manifest = self.f.doc(self.f.manifest_ref["path"])
        manifest["arms"] = list(reversed(manifest["arms"]))
        self.f.protocol["manifest_ref"] = self.f.write(
            "evaluation/reordered-manifest.json", manifest
        )
        ref = self.f.write("evaluation/reordered-protocol.json", self.f.protocol)
        self.assertEqual(
            validate_protocol(self.inputs(), ref)["rules"]["primary"]["contrast"],
            "A4-A2",
        )

    def test_measurement_units_ranges_estimates_and_nonfinite_values(self):
        evidence = self.f.raw("evaluation/value.txt", b"synthetic metric evidence")
        document = record(
            "evaluation_measurement",
            "measurement_id",
            "M5-METRIC",
            protocol_ref=self.f.protocol_ref,
            case_id="CASE",
            arm_id="plain-agent",
            metric_id="cost",
            status="measured",
            unit="JPY",
            value=1,
            reason="synthetic",
            evidence_refs=[evidence],
            estimation_method=None,
        )
        inputs = self.inputs()
        validate_measurement(
            inputs, document, expected_protocol_ref=self.f.protocol_ref
        )
        for changes in (
            {"unit": "minutes"},
            {"value": float("nan")},
            {"value": float("inf")},
            {"metric_id": "omission-rate", "unit": "ratio", "value": 1.1},
            {"metric_id": "rework-count", "unit": "count", "value": 1.5},
            {"status": "estimated"},
            {"evidence_refs": []},
            {"protocol_ref": self.f.manifest_ref},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(EvaluationValidationError),
            ):
                validate_measurement(
                    inputs,
                    {**document, **changes},
                    expected_protocol_ref=self.f.protocol_ref,
                )
        for changes in (
            {"metric_id": "omission-rate", "unit": "ratio", "value": 1},
            {"metric_id": "rework-count", "unit": "count", "value": 2},
            {"metric_id": "rework-count", "unit": "count", "value": 10**400},
            {"metric_id": "context-loaded", "unit": "tokens", "value": 4},
        ):
            validate_measurement(
                inputs,
                {**document, **changes},
                expected_protocol_ref=self.f.protocol_ref,
            )
