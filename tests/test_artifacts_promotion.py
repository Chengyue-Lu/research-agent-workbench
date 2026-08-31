"""M4-002 fail-closed artifact promotion tests."""

from __future__ import annotations

import copy
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

import yaml

from research_workbench.artifacts import promotion
from research_workbench.artifacts.integrity import hash_file
from research_workbench.artifacts.promotion import check_promotion, execute_promotion
from research_workbench.cli import main
from research_workbench.contracts.common import ContractError
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.validation.document_kinds import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog


class PromotionFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.workspace = self.root / "work" / "M4-002" / "A-001"
        self.output = self.workspace / "outputs" / "result.txt"
        self.negative = self.workspace / "outputs" / "negative.txt"
        self.checker = self.workspace / "checks" / "checker.py"
        self.report_path = self.workspace / "checks" / "validation.yaml"
        self.output.parent.mkdir(parents=True)
        self.checker.parent.mkdir(parents=True)
        self.output.write_bytes(b"validated result\n")
        self.negative.write_bytes(b"validated null result\n")
        self.checker.write_text("def check(): return True\n", encoding="utf-8")
        self.report = self._report()
        self.record = self._record()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def ref(self, path: Path) -> dict[str, str]:
        return {"path": self.rel(path), "sha256": hash_file(path)}

    def _report(self) -> dict:
        report = {
            "schema_version": "0.1.0",
            "report_id": "M4-002-VALIDATION-A-001",
            "checker": {
                "checker_id": "fixture-byte-checker",
                "version": "1.0.0",
                "source_ref": self.ref(self.checker),
            },
            "subject_refs": [self.ref(self.output), self.ref(self.negative)],
            "status": "pass",
            "checks": [
                {
                    "code": "FIXTURE-BYTES-EXACT",
                    "status": "pass",
                    "detail": "Synthetic fixture bytes match their deterministic expectation.",
                }
            ],
            "scope": "Synthetic M4-002 structural fixture only.",
            "limitations": ["Does not establish scientific correctness."],
        }
        self.write_report(report)
        return report

    def write_report(self, report: dict) -> None:
        self.report_path.write_text(
            yaml.safe_dump(report, sort_keys=False), encoding="utf-8", newline="\n"
        )

    def repin_report(self, record: dict, report: dict | None = None) -> None:
        if report is not None:
            self.write_report(report)
        record["validation_report"] = self.ref(self.report_path)

    def _record(self) -> dict:
        return {
            "schema_version": "0.1.0",
            "promotion_id": "PROMOTION-M4-002-A-001",
            "source_workspace": "work/M4-002/A-001",
            "validation_report": self.ref(self.report_path),
            "operator": "huangyi",
            "recorded_at": "2026-08-31T09:00:00+08:00",
            "entries": [
                {
                    "artifact": self.ref(self.output),
                    "disposition": "promote",
                    "negative_result": False,
                    "target": "objects/M4-002/result.txt",
                },
                {
                    "artifact": self.ref(self.negative),
                    "disposition": "retain-in-work",
                    "negative_result": True,
                    "reason": "Retain validated negative result without publication semantics.",
                },
            ],
            "authority_boundaries": {
                "structural_eligibility_only": True,
                "claim_acceptance": False,
                "human_decision": False,
                "publication": False,
                "source_deletion": False,
            },
        }

    def write_record(self, record: dict, name: str = "promotion.yaml") -> Path:
        path = self.workspace / name
        path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8", newline="\n")
        return path

    def codes(self, record: dict) -> set[str]:
        return {risk.code for risk in check_promotion(self.root, record)}


class PromotionValidationTest(PromotionFixture):
    def test_valid_record_closes_report_checker_subjects_and_entries(self) -> None:
        self.assertEqual(infer_document_kind(self.record), "promotion_record")
        self.assertEqual(SchemaCatalog().validate("promotion_record", self.record), [])
        self.assertEqual(check_promotion(self.root, self.record), [])

    def test_backslash_paths_normalize_to_one_cross_host_identity(self) -> None:
        report = copy.deepcopy(self.report)
        report["checker"]["source_ref"]["path"] = report["checker"]["source_ref"][
            "path"
        ].replace("/", "\\")
        for subject in report["subject_refs"]:
            subject["path"] = subject["path"].replace("/", "\\")
        self.write_report(report)

        record = copy.deepcopy(self.record)
        record["source_workspace"] = record["source_workspace"].replace("/", "\\")
        record["validation_report"] = self.ref(self.report_path)
        record["validation_report"]["path"] = record["validation_report"]["path"].replace(
            "/", "\\"
        )
        for entry in record["entries"]:
            entry["artifact"]["path"] = entry["artifact"]["path"].replace("/", "\\")
            if "target" in entry:
                entry["target"] = entry["target"].replace("/", "\\")
        self.assertEqual(check_promotion(self.root, record), [])

    def test_cli_validate_accepts_exact_record(self) -> None:
        record_path = self.write_record(self.record)
        output = StringIO()
        with redirect_stdout(output):
            result = main(["promotion", "validate", str(record_path), "--root", str(self.root)])
        self.assertEqual(result, 0)
        self.assertIn("no blocking deterministic risks", output.getvalue())

    def test_report_pin_subject_set_and_checker_drift_fail_closed(self) -> None:
        with self.subTest("report pin"):
            self.report_path.write_text("changed after pin\n", encoding="utf-8")
            self.assertIn("ARTIFACT-HASH-MISMATCH", self.codes(self.record))

        self.write_report(self.report)
        self.repin_report(self.record)
        with self.subTest("checker pin"):
            self.checker.write_text("def check(): return False\n", encoding="utf-8")
            self.assertIn("ARTIFACT-HASH-MISMATCH", self.codes(self.record))

        self.checker.write_text("def check(): return True\n", encoding="utf-8")
        changed_report = copy.deepcopy(self.report)
        changed_report["checker"]["source_ref"] = self.ref(self.checker)
        changed_report["subject_refs"][0]["sha256"] = "0" * 64
        self.repin_report(self.record, changed_report)
        with self.subTest("subject hash"):
            codes = self.codes(self.record)
            self.assertIn("ARTIFACT-HASH-MISMATCH", codes)
            self.assertIn("ARTIFACT-NEGATIVE-DROPPED", codes)

    def test_missing_entry_bytes_and_malformed_reports_fail_closed(self) -> None:
        self.output.unlink()
        self.assertIn("REF-MISSING", self.codes(self.record))
        self.output.write_bytes(b"validated result\n")

        for content in ("[unterminated", "- not\n- an\n- object\n", "schema_version: 0.1.0\n"):
            with self.subTest(content=content):
                self.report_path.write_text(content, encoding="utf-8")
                self.repin_report(self.record)
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(self.record))

    def test_semantically_duplicate_report_subject_is_rejected_after_pin_normalization(self) -> None:
        report = copy.deepcopy(self.report)
        duplicate = self.ref(self.output)
        duplicate["sha256"] = f"sha256:{duplicate['sha256']}"
        report["subject_refs"][1] = duplicate
        self.repin_report(self.record, report)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(self.record))

    def test_extra_or_missing_entry_cannot_bypass_exact_subject_set(self) -> None:
        extra_path = self.workspace / "outputs" / "extra.txt"
        extra_path.write_bytes(b"not validated\n")
        extra = copy.deepcopy(self.record)
        extra["entries"].append(
            {
                "artifact": self.ref(extra_path),
                "disposition": "retain-in-work",
                "negative_result": False,
                "reason": "Extra entry must still be rejected.",
            }
        )
        missing = copy.deepcopy(self.record)
        missing["entries"].pop()
        self.assertIn("ARTIFACT-NEGATIVE-DROPPED", self.codes(extra))
        self.assertIn("ARTIFACT-NEGATIVE-DROPPED", self.codes(missing))

    def test_failed_report_is_not_promotion_eligible(self) -> None:
        failed = copy.deepcopy(self.report)
        failed["status"] = "fail"
        failed["checks"][0]["status"] = "fail"
        failed["checks"][0]["detail"] = "Synthetic check failed."
        self.repin_report(self.record, failed)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(self.record))

    def test_workspace_target_and_existing_target_boundaries_fail_closed(self) -> None:
        for workspace in ("work/M4-002", "work-copy/M4-002/A-001", "work/M4-002/A-001/outputs"):
            with self.subTest(workspace=workspace):
                record = copy.deepcopy(self.record)
                record["source_workspace"] = workspace
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

        for target in (
            "objects",
            "runs",
            "deliverables/candidates",
            "deliverables/accepted/result.txt",
            "objects-old/result.txt",
            "checks/result.txt",
        ):
            with self.subTest(target=target):
                record = copy.deepcopy(self.record)
                record["entries"][0]["target"] = target
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

        existing = self.root / "objects" / "M4-002" / "result.txt"
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b"must not be overwritten")
        self.assertIn("ARTIFACT-OVERWRITE", self.codes(self.record))

    def test_prefix_lookalike_entry_is_not_inside_workspace(self) -> None:
        lookalike = self.root / "work" / "M4-002" / "A-001-old" / "result.txt"
        lookalike.parent.mkdir(parents=True)
        lookalike.write_bytes(b"lookalike")
        report = copy.deepcopy(self.report)
        report["subject_refs"][0] = self.ref(lookalike)
        record = copy.deepcopy(self.record)
        record["entries"][0]["artifact"] = self.ref(lookalike)
        self.repin_report(record, report)
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

    def test_duplicate_artifact_and_target_identities_block(self) -> None:
        duplicate_artifact = copy.deepcopy(self.record)
        duplicate_artifact["entries"].append(
            {
                "artifact": self.ref(self.output),
                "disposition": "retain-in-work",
                "negative_result": False,
                "reason": "Duplicate path with a different disposition.",
            }
        )
        self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(duplicate_artifact))

        duplicate_target = copy.deepcopy(self.record)
        duplicate_target["entries"][1] = {
            "artifact": self.ref(self.negative),
            "disposition": "promote",
            "negative_result": True,
            "target": "objects/M4-002/result.txt",
        }
        self.assertIn("ARTIFACT-OVERWRITE", self.codes(duplicate_target))

    def test_authority_boundaries_are_fixed_and_cannot_claim_acceptance(self) -> None:
        for key in ("claim_acceptance", "human_decision", "publication", "source_deletion"):
            with self.subTest(key=key):
                record = copy.deepcopy(self.record)
                record["authority_boundaries"][key] = True
                self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(record))

    def test_mapping_models_reject_malformed_direct_callers(self) -> None:
        malformed_entries = (
            {},
            {"artifact": {}, "disposition": "promote", "negative_result": "no"},
        )
        for entry in malformed_entries:
            with self.subTest(entry=entry), self.assertRaises(ContractError):
                promotion.PromotionEntry.from_mapping(entry)

        for record in (
            {},
            {"validation_report": {}, "entries": []},
            {"validation_report": {}, "entries": ["not-an-object"]},
        ):
            with self.subTest(record=record), self.assertRaises(ContractError):
                promotion.PromotionRecord.from_mapping(record)

    def test_symlink_escape_blocks_source_and_target(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir(exist_ok=True)
        try:
            source_link = self.workspace / "outputs" / "outside-link"
            target_link = self.root / "objects" / "outside-link"
            target_link.parent.mkdir(parents=True)
            try:
                source_link.symlink_to(outside, target_is_directory=True)
                target_link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            outside_source = outside / "source.txt"
            outside_source.write_bytes(b"outside")
            source_record = copy.deepcopy(self.record)
            source_record["entries"][0]["artifact"] = {
                "path": self.rel(source_link / "source.txt"),
                "sha256": hash_file(outside_source),
            }
            self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(source_record))

            target_record = copy.deepcopy(self.record)
            target_record["entries"][0]["target"] = "objects/outside-link/result.txt"
            self.assertIn("ARTIFACT-PROMOTION-BYPASS", self.codes(target_record))
        finally:
            try:
                outside.rmdir()
            except OSError:
                pass


class PromotionExecutionTest(PromotionFixture):
    def test_execute_stages_publishes_without_overwrite_and_preserves_work(self) -> None:
        targets = execute_promotion(self.root, self.record)
        self.assertEqual(targets, ("objects/M4-002/result.txt",))
        self.assertEqual((self.root / targets[0]).read_bytes(), self.output.read_bytes())
        self.assertTrue(self.output.is_file())
        self.assertTrue(self.negative.is_file())
        self.assertFalse((self.root / "deliverables" / "accepted").exists())
        self.assertIn("ARTIFACT-OVERWRITE", self.codes(self.record))

    def test_cli_execute_reports_promoted_target(self) -> None:
        record_path = self.write_record(self.record)
        output = StringIO()
        with redirect_stdout(output):
            result = main(["promotion", "execute", str(record_path), "--root", str(self.root)])
        self.assertEqual(result, 0)
        self.assertIn("promoted: objects/M4-002/result.txt", output.getvalue())

    def test_all_validated_negative_results_may_be_explicitly_retained(self) -> None:
        record = copy.deepcopy(self.record)
        record["entries"][0] = {
            "artifact": self.ref(self.output),
            "disposition": "retain-in-work",
            "negative_result": False,
            "reason": "No formal copy requested.",
        }
        self.assertEqual(execute_promotion(self.root, record), ())
        self.assertFalse((self.root / "objects").exists())
        self.assertTrue(self.output.is_file())

    def test_source_race_and_partial_publish_roll_back(self) -> None:
        original_stage = promotion._stage_promotions

        def mutate_then_stage(root: Path, record):
            self.output.write_bytes(b"mutated between validation and staging\n")
            return original_stage(root, record)

        with mock.patch.object(promotion, "_stage_promotions", side_effect=mutate_then_stage):
            with self.assertRaises(ContractError):
                execute_promotion(self.root, self.record)
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())

        self.output.write_bytes(b"validated result\n")
        record = copy.deepcopy(self.record)
        record["entries"][1] = {
            "artifact": self.ref(self.negative),
            "disposition": "promote",
            "negative_result": True,
            "target": "runs/M4-002/negative.txt",
        }
        real_link = os.link
        calls = 0

        def fail_second_link(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise FileExistsError("simulated concurrent target")
            return real_link(source, target)

        with mock.patch.object(promotion.os, "link", side_effect=fail_second_link):
            with self.assertRaises(FileExistsError):
                execute_promotion(self.root, record)
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())
        self.assertFalse((self.root / "runs" / "M4-002" / "negative.txt").exists())
        self.assertTrue(self.output.is_file())
        self.assertTrue(self.negative.is_file())

    def test_initial_or_final_validation_risk_never_publishes(self) -> None:
        invalid = copy.deepcopy(self.record)
        invalid["entries"][0]["target"] = "deliverables/accepted/result.txt"
        with self.assertRaises(ContractError):
            execute_promotion(self.root, invalid)

        blocker = ContractRisk("ARTIFACT-HASH-MISMATCH", RiskLevel.BLOCK, "simulated final drift")
        with mock.patch.object(promotion, "check_promotion", side_effect=[[], [blocker]]):
            with self.assertRaises(ContractError):
                execute_promotion(self.root, self.record)
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())
        self.assertEqual(list((self.root / "objects").rglob("*.tmp")), [])

    def test_staged_byte_drift_and_pre_publish_target_race_block(self) -> None:
        original_stage = promotion._stage_promotions

        def corrupt_staging(root: Path, record):
            staged = original_stage(root, record)
            staged[0].temporary.write_bytes(b"tampered staged bytes")
            return staged

        with mock.patch.object(promotion, "_stage_promotions", side_effect=corrupt_staging):
            with self.assertRaises(ContractError):
                execute_promotion(self.root, self.record)

        target = self.root / "objects" / "M4-002" / "result.txt"
        calls = 0

        def create_target_on_final_check(root, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                target.write_bytes(b"appeared during final validation")
            return []

        with mock.patch.object(promotion, "check_promotion", side_effect=create_target_on_final_check):
            with self.assertRaises(ContractError):
                execute_promotion(self.root, self.record)
        self.assertEqual(target.read_bytes(), b"appeared during final validation")

    def test_staging_helper_cleans_earlier_temp_when_later_source_drifts(self) -> None:
        record = copy.deepcopy(self.record)
        record["entries"][1] = {
            "artifact": {
                "path": self.rel(self.negative),
                "sha256": "0" * 64,
            },
            "disposition": "promote",
            "negative_result": True,
            "target": "runs/M4-002/negative.txt",
        }
        parsed = promotion.PromotionRecord.from_mapping(record)
        with self.assertRaises(ContractError):
            promotion._stage_promotions(self.root, parsed)
        self.assertEqual(list(self.root.rglob("*.tmp")), [])
        self.assertFalse((self.root / "objects" / "M4-002" / "result.txt").exists())

    def test_concurrent_target_is_never_overwritten(self) -> None:
        target = self.root / "objects" / "M4-002" / "result.txt"
        original_publish = promotion._publish_staged

        def create_target_then_publish(staged):
            target.write_bytes(b"concurrent owner")
            original_publish(staged)

        with mock.patch.object(promotion, "_publish_staged", side_effect=create_target_then_publish):
            with self.assertRaises(FileExistsError):
                execute_promotion(self.root, self.record)
        self.assertEqual(target.read_bytes(), b"concurrent owner")
        self.assertTrue(self.output.is_file())

    def test_temp_cleanup_error_does_not_misreport_successful_publication(self) -> None:
        with mock.patch.object(promotion.Path, "unlink", side_effect=OSError("simulated cleanup")):
            targets = execute_promotion(self.root, self.record)
        self.assertEqual(targets, ("objects/M4-002/result.txt",))
        self.assertEqual((self.root / targets[0]).read_bytes(), b"validated result\n")


if __name__ == "__main__":
    unittest.main()
