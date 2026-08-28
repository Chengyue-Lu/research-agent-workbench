"""M4-001 source admission and provenance tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.cli import _document_reference_risks
from research_workbench.artifacts.admission import (
    build_admission_mapping,
    check_source_admission,
    path_cites_inbox,
    path_cites_raw,
    sidecar_path_for,
)
from research_workbench.artifacts.integrity import hash_bytes
from research_workbench.contracts.risks import RiskLevel
from research_workbench.io import load_document
from research_workbench.validation.documents import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog

CONTENT = b"sensor,reading\nA,1\nB,2\n"

ACQUISITION_ARGS = {
    "origin": {"uri": "https://example.org/datasets/synthetic-sensor-log"},
    "acquired_at": "2026-08-25T10:00:00+08:00",
    "operator": "huangyi",
    "license_or_data_use": "CC-BY-4.0 fixture",
    "parser_name": "csv-reader",
    "parser_version": "1.0.0",
    "sensitivity": "public-fixture",
    "egress_restriction": "no-restriction-fixture",
}


def _write_project(root: Path) -> None:
    (root / "sources" / "inbox").mkdir(parents=True, exist_ok=True)
    (root / "sources" / "raw").mkdir(parents=True, exist_ok=True)
    (root / "sources" / "inbox" / "log.csv").write_bytes(CONTENT)
    (root / "sources" / "raw" / "log.csv").write_bytes(CONTENT)


def _admission() -> dict:
    return build_admission_mapping(
        original_filename="log.csv",
        admitted_path="sources/raw/log.csv",
        content=CONTENT,
        **ACQUISITION_ARGS,
    )


class BuildAdmissionTest(unittest.TestCase):
    def test_deterministic_mapping_and_kind(self) -> None:
        mapping = _admission()
        self.assertEqual(mapping, _admission())
        self.assertEqual(infer_document_kind(mapping), "source_admission")
        self.assertEqual(sidecar_path_for("sources/raw/log.csv"), "sources/raw/log.csv.admission.yaml")

    def test_schema_valid(self) -> None:
        self.assertEqual(SchemaCatalog().validate("source_admission", _admission()), [])

    def test_rejects_inbox_admitted_path(self) -> None:
        with self.assertRaises(ValueError):
            build_admission_mapping(
                original_filename="log.csv",
                admitted_path="sources/inbox/log.csv",
                content=CONTENT,
                **ACQUISITION_ARGS,
            )

    def test_rejects_raw_prefix_lookalike(self) -> None:
        with self.assertRaises(ValueError):
            build_admission_mapping(
                original_filename="log.csv",
                admitted_path="sources/raw-copy/log.csv",
                content=CONTENT,
                **ACQUISITION_ARGS,
            )

    def test_requires_explicit_timestamp(self) -> None:
        args = dict(ACQUISITION_ARGS)
        args["acquired_at"] = "now"
        with self.assertRaises(ValueError):
            build_admission_mapping(
                original_filename="log.csv",
                admitted_path="sources/raw/log.csv",
                content=CONTENT,
                **args,
            )

    def test_requires_origin_locator(self) -> None:
        args = dict(ACQUISITION_ARGS)
        args["origin"] = {}
        with self.assertRaises(ValueError):
            build_admission_mapping(
                original_filename="log.csv",
                admitted_path="sources/raw/log.csv",
                content=CONTENT,
                **args,
            )


class InboxCitationTest(unittest.TestCase):
    def test_inbox_detection_uses_complete_segments(self) -> None:
        self.assertTrue(path_cites_inbox("sources/inbox/a.csv"))
        self.assertTrue(path_cites_inbox("projects/p/sources/inbox/a.csv"))
        self.assertFalse(path_cites_inbox("sources/inbox-old/a.csv"))
        self.assertFalse(path_cites_inbox("sources/raw/a.csv"))
        with self.assertRaises(ValueError):
            path_cites_inbox("../escape")

    def test_repository_reference_gate_blocks_unadmitted_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "sources" / "inbox" / "input.txt"
            inbox.parent.mkdir(parents=True)
            inbox.write_bytes(b"unadmitted")
            from research_workbench.artifacts.integrity import hash_bytes

            check_report = {
                "report_id": "REPORT-INBOX-NEGATIVE",
                "checker": {
                    "source_ref": {
                        "path": "sources/inbox/input.txt",
                        "sha256": hash_bytes(b"unadmitted"),
                    }
                },
                "checks": [],
            }
            risks = _document_reference_risks(check_report, root)
            self.assertTrue(
                any(r.code == "ARTIFACT-INBOX-CITED" and r.level == RiskLevel.BLOCK for r in risks)
            )


class RawReferenceAdmissionGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _write_project(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    @property
    def sidecar(self) -> Path:
        return self.root / "sources" / "raw" / "log.csv.admission.yaml"

    def _write_sidecar(self, data: dict) -> None:
        self.sidecar.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def _risks(self, sha256: str | None = None):
        check_report = {
            "report_id": "REPORT-RAW-REFERENCE",
            "checker": {
                "source_ref": {
                    "path": "sources/raw/log.csv",
                    "sha256": sha256 or hash_bytes(CONTENT),
                }
            },
            "checks": [],
        }
        return _document_reference_risks(check_report, self.root)

    def test_valid_raw_reference_requires_and_accepts_exact_sidecar(self) -> None:
        self._write_sidecar(_admission())
        self.assertEqual(self._risks(), [])
        self.assertTrue(path_cites_raw("projects/p/sources/raw/log.csv"))
        self.assertFalse(path_cites_raw("sources/raw-copy/log.csv"))

    def test_missing_sidecar_blocks(self) -> None:
        risks = self._risks()
        self.assertTrue(
            any(
                risk.code == "ARTIFACT-MISSING-PROVENANCE"
                and "lacks its admission sidecar" in risk.message
                for risk in risks
            )
        )

    def test_schema_invalid_sidecar_blocks(self) -> None:
        invalid = _admission()
        del invalid["acquisition"]["operator"]
        self._write_sidecar(invalid)
        risks = self._risks()
        self.assertTrue(
            any(
                risk.code == "ARTIFACT-MISSING-PROVENANCE"
                and "schema-invalid" in risk.message
                for risk in risks
            )
        )

    def test_wrong_admitted_path_blocks(self) -> None:
        admission = _admission()
        admission["admitted_path"] = "sources/raw/other.csv"
        self._write_sidecar(admission)
        risks = self._risks()
        self.assertTrue(
            any(
                risk.code == "ARTIFACT-MISSING-PROVENANCE"
                and "admission path mismatch" in risk.message
                for risk in risks
            )
        )

    def test_live_byte_drift_blocks_even_when_reference_tracks_mutation(self) -> None:
        self._write_sidecar(_admission())
        mutated = CONTENT + b"mutated\n"
        (self.root / "sources" / "raw" / "log.csv").write_bytes(mutated)
        risks = self._risks(hash_bytes(mutated))
        self.assertTrue(
            any(
                risk.code == "ARTIFACT-HASH-MISMATCH"
                and "admitted bytes differ" in risk.message
                for risk in risks
            )
        )

    def test_reference_and_admission_hash_mismatch_blocks(self) -> None:
        self._write_sidecar(_admission())
        risks = self._risks(hash_bytes(b"wrong reference pin"))
        self.assertTrue(
            any(
                risk.code == "ARTIFACT-HASH-MISMATCH"
                and "FileReference sha256 differs from admission sha256" in risk.message
                for risk in risks
            )
        )


class CheckAdmissionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _write_project(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _risks(self, data: dict):
        return check_source_admission(self.root, data)

    def test_passing_admission_has_no_block(self) -> None:
        self.assertEqual(self._risks(_admission()), [])

    def test_hash_mismatch_blocks(self) -> None:
        data = _admission()
        (self.root / "sources" / "raw" / "log.csv").write_bytes(CONTENT + b"mutated\n")
        risks = self._risks(data)
        self.assertTrue(
            any(r.code == "ARTIFACT-HASH-MISMATCH" and r.level == RiskLevel.BLOCK for r in risks)
        )

    def test_missing_origin_blocks(self) -> None:
        data = _admission()
        data["acquisition"]["origin"] = {}
        risks = self._risks(data)
        self.assertTrue(
            any(r.code == "ARTIFACT-MISSING-PROVENANCE" and r.level == RiskLevel.BLOCK for r in risks)
        )

    def test_unparseable_timestamp_blocks(self) -> None:
        data = _admission()
        data["acquisition"]["acquired_at"] = "yesterday"
        self.assertTrue(any(r.code == "ARTIFACT-MISSING-PROVENANCE" for r in self._risks(data)))

    def test_derivative_hash_mismatch_blocks(self) -> None:
        data = _admission()
        (self.root / "sources" / "raw" / "excerpt.txt").write_bytes(b"excerpt")
        from research_workbench.artifacts.integrity import hash_bytes

        data["derivatives"] = [
            {
                "path": "sources/raw/excerpt.txt",
                "sha256": hash_bytes(b"different"),
                "relation": "text-excerpt",
            }
        ]
        self.assertTrue(any(r.code == "ARTIFACT-HASH-MISMATCH" for r in self._risks(data)))

    def test_sidecar_roundtrip(self) -> None:
        sidecar = self.root / "sources" / "raw" / "log.csv.admission.yaml"
        sidecar.write_text(yaml.safe_dump(_admission(), sort_keys=False), encoding="utf-8")
        self.assertEqual(self._risks(load_document(sidecar)), [])


if __name__ == "__main__":
    unittest.main()
