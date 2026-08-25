"""M4-002 work-to-object promotion tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research_workbench.artifacts.integrity import hash_bytes, hash_file
from research_workbench.artifacts.promotion import check_promotion, execute_promotion
from research_workbench.contracts.common import ContractError
from research_workbench.contracts.risks import RiskLevel
from research_workbench.validation.documents import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog

METRICS = b"metric,value\nmse,0.25\n"
NEGATIVE = b"The mediator hypothesis found no supporting signal in the fixture.\n"

VALIDATION_REPORT = {
    "schema_version": "0.1.0",
    "report_id": "VAL-SIM-001-A-001",
    "checker": {
        "checker_id": "promotion-gate",
        "version": "1.0.0",
        "source_ref": {"path": "checkers/promotion-gate.md", "sha256": "0" * 64},
    },
    "subject_refs": [
        {"path": "work/SIM-001/A-001/outputs/metrics.csv", "sha256": ""},
        {"path": "work/SIM-001/A-001/outputs/negative-findings.md", "sha256": ""},
    ],
    "status": "pass",
    "checks": [
        {"code": "structure", "status": "pass", "detail": "both artifacts parse"},
    ],
    "scope": "SIM-001 attempt A-001 outputs",
    "limitations": ["structural check only"],
}


def _write_project(root: Path) -> None:
    outputs = root / "work" / "SIM-001" / "A-001" / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "metrics.csv").write_bytes(METRICS)
    (outputs / "negative-findings.md").write_bytes(NEGATIVE)
    checks = root / "work" / "SIM-001" / "A-001" / "checks"
    checks.mkdir(parents=True, exist_ok=True)
    report = dict(VALIDATION_REPORT)
    report["subject_refs"] = [
        {
            "path": "work/SIM-001/A-001/outputs/metrics.csv",
            "sha256": hash_bytes(METRICS),
        },
        {
            "path": "work/SIM-001/A-001/outputs/negative-findings.md",
            "sha256": hash_bytes(NEGATIVE),
        },
    ]
    import yaml

    (checks / "VAL-SIM-001-A-001.yaml").write_text(
        yaml.safe_dump(report, sort_keys=False), encoding="utf-8"
    )
    checkers = root / "checkers"
    checkers.mkdir(parents=True, exist_ok=True)
    (checkers / "promotion-gate.md").write_text("promotion gate stub\n", encoding="utf-8")
    report["checker"]["source_ref"]["sha256"] = hash_file(checkers / "promotion-gate.md")


def _record(root: Path, entries: list[dict], **overrides) -> dict:
    record = {
        "schema_version": "0.1.0",
        "promotion_id": "PR-SIM-001-A-001",
        "source_workspace": "work/SIM-001/A-001",
        "validation_report": {
            "path": "work/SIM-001/A-001/checks/VAL-SIM-001-A-001.yaml",
            "sha256": hash_file(root / "work" / "SIM-001" / "A-001" / "checks" / "VAL-SIM-001-A-001.yaml"),
        },
        "decided_by": "huangyi",
        "decided_at": "2026-08-25T12:00:00+08:00",
        "entries": entries,
    }
    record.update(overrides)
    return record


def _standard_entries(root: Path) -> list[dict]:
    return [
        {
            "artifact": {
                "path": "work/SIM-001/A-001/outputs/metrics.csv",
                "sha256": hash_file(root / "work" / "SIM-001" / "A-001" / "outputs" / "metrics.csv"),
            },
            "disposition": "promoted",
            "negative_result": False,
            "target": "objects/evidence/METRICS-SIM-001.csv",
        },
        {
            "artifact": {
                "path": "work/SIM-001/A-001/outputs/negative-findings.md",
                "sha256": hash_file(root / "work" / "SIM-001" / "A-001" / "outputs" / "negative-findings.md"),
            },
            "disposition": "retained-in-work",
            "negative_result": True,
            "reason": "negative finding retained for revisit; not promoted this round",
        },
    ]


class PromotionCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _write_project(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _risks(self, record: dict):
        return check_promotion(self.root, record)

    def test_valid_record_passes_and_infers_kind(self) -> None:
        record = _record(self.root, _standard_entries(self.root))
        self.assertEqual(self._risks(record), [])
        self.assertEqual(infer_document_kind(record), "promotion_record")
        self.assertEqual(SchemaCatalog().validate("promotion_record", record), [])

    def test_non_passing_report_blocks(self) -> None:
        import yaml

        report_path = self.root / "work" / "SIM-001" / "A-001" / "checks" / "VAL-SIM-001-A-001.yaml"
        report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
        report["status"] = "fail"
        report_path.write_text(yaml.safe_dump(report, sort_keys=False), encoding="utf-8")
        record = _record(self.root, _standard_entries(self.root))
        risks = self._risks(record)
        self.assertTrue(any(r.code == "ARTIFACT-PROMOTION-BYPASS" and r.level == RiskLevel.BLOCK for r in risks))

    def test_workspace_outside_work_blocks(self) -> None:
        record = _record(self.root, _standard_entries(self.root), source_workspace="sources/raw")
        self.assertTrue(
            any(r.code == "ARTIFACT-PROMOTION-BYPASS" for r in self._risks(record))
        )

    def test_uncovered_negative_result_blocks(self) -> None:
        entries = [_standard_entries(self.root)[0]]
        record = _record(self.root, entries)
        risks = self._risks(record)
        self.assertTrue(
            any(
                r.code == "ARTIFACT-NEGATIVE-DROPPED" and r.level == RiskLevel.BLOCK
                for r in risks
            )
        )

    def test_existing_target_blocks(self) -> None:
        target = self.root / "objects" / "evidence" / "METRICS-SIM-001.csv"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(METRICS)
        record = _record(self.root, _standard_entries(self.root))
        self.assertTrue(any(r.code == "ARTIFACT-OVERWRITE" for r in self._risks(record)))

    def test_target_outside_promotable_roots_blocks(self) -> None:
        entries = _standard_entries(self.root)
        entries[0]["target"] = "sources/raw/metrics.csv"
        record = _record(self.root, entries)
        self.assertTrue(
            any(
                r.code == "ARTIFACT-PROMOTION-BYPASS" and "target" in r.message
                for r in self._risks(record)
            )
        )

    def test_artifact_hash_drift_blocks(self) -> None:
        entries = _standard_entries(self.root)
        entries[0]["artifact"]["sha256"] = "0" * 64
        record = _record(self.root, entries)
        self.assertTrue(any(r.code == "ARTIFACT-HASH-MISMATCH" for r in self._risks(record)))

    def test_schema_requires_reason_for_retained(self) -> None:
        entries = _standard_entries(self.root)
        del entries[1]["reason"]
        record = _record(self.root, entries)
        self.assertNotEqual(SchemaCatalog().validate("promotion_record", record), [])


class PromotionExecuteTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _write_project(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_execute_copies_only_promoted(self) -> None:
        record = _record(self.root, _standard_entries(self.root))
        copied = execute_promotion(self.root, record)
        self.assertEqual(copied, ["objects/evidence/METRICS-SIM-001.csv"])
        target = self.root / "objects" / "evidence" / "METRICS-SIM-001.csv"
        self.assertEqual(target.read_bytes(), METRICS)
        self.assertTrue(
            (self.root / "work" / "SIM-001" / "A-001" / "outputs" / "negative-findings.md").is_file()
        )

    def test_execute_refuses_after_target_created(self) -> None:
        record = _record(self.root, _standard_entries(self.root))
        execute_promotion(self.root, record)
        with self.assertRaises(ContractError):
            execute_promotion(self.root, record)


if __name__ == "__main__":
    unittest.main()
