"""M4-001 source admission and provenance tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research_workbench.artifacts.admission import (
    build_admission_mapping,
    check_source_admission,
    path_cites_inbox,
    sidecar_path_for,
)
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


def _admission(root: Path) -> dict:
    return build_admission_mapping(
        original_filename="log.csv",
        admitted_path="sources/raw/log.csv",
        content=CONTENT,
        **ACQUISITION_ARGS,
    )


class BuildAdmissionTest(unittest.TestCase):
    def test_deterministic_mapping_and_kind(self) -> None:
        mapping = _admission(Path("."))
        again = _admission(Path("."))
        self.assertEqual(mapping, again)
        self.assertEqual(infer_document_kind(mapping), "source_admission")
        self.assertEqual(sidecar_path_for("sources/raw/log.csv"), "sources/raw/log.csv.admission.yaml")

    def test_schema_valid(self) -> None:
        self.assertEqual(SchemaCatalog().validate("source_admission", _admission(Path("."))), [])

    def test_rejects_inbox_admitted_path(self) -> None:
        with self.assertRaises(ValueError):
            build_admission_mapping(
                original_filename="log.csv",
                admitted_path="sources/inbox/log.csv",
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
    def test_inbox_detection(self) -> None:
        self.assertTrue(path_cites_inbox("sources/inbox/a.csv"))
        self.assertTrue(path_cites_inbox("projects/p/sources/inbox/a.csv"))
        self.assertFalse(path_cites_inbox("sources/raw/a.csv"))
        with self.assertRaises(ValueError):
            path_cites_inbox("../escape")


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
        self.assertEqual(self._risks(_admission(self.root)), [])

    def test_hash_mismatch_blocks(self) -> None:
        data = _admission(self.root)
        (self.root / "sources" / "raw" / "log.csv").write_bytes(CONTENT + b"mutated\n")
        risks = self._risks(data)
        self.assertTrue(any(r.code == "ARTIFACT-HASH-MISMATCH" and r.level == RiskLevel.BLOCK for r in risks))

    def test_missing_origin_blocks(self) -> None:
        data = _admission(self.root)
        data["acquisition"]["origin"] = {}
        risks = self._risks(data)
        self.assertTrue(any(r.code == "ARTIFACT-MISSING-PROVENANCE" and r.level == RiskLevel.BLOCK for r in risks))

    def test_unparseable_timestamp_blocks(self) -> None:
        data = _admission(self.root)
        data["acquisition"]["acquired_at"] = "yesterday"
        risks = self._risks(data)
        self.assertTrue(any(r.code == "ARTIFACT-MISSING-PROVENANCE" for r in risks))

    def test_derivative_hash_mismatch_blocks(self) -> None:
        data = _admission(self.root)
        (self.root / "sources" / "raw" / "excerpt.txt").write_bytes(b"excerpt")
        from research_workbench.artifacts.integrity import hash_bytes

        data["derivatives"] = [
            {"path": "sources/raw/excerpt.txt", "sha256": hash_bytes(b"different"), "relation": "text-excerpt"}
        ]
        risks = self._risks(data)
        self.assertTrue(any(r.code == "ARTIFACT-HASH-MISMATCH" for r in risks))

    def test_sidecar_roundtrip(self) -> None:
        sidecar = self.root / "sources" / "raw" / "log.csv.admission.yaml"
        sidecar.write_text(
            "\n".join(f"{key}: {value}" for key, value in []) or "", encoding="utf-8"
        )
        import yaml

        sidecar.write_text(yaml.safe_dump(_admission(self.root), sort_keys=False), encoding="utf-8")
        reloaded = load_document(sidecar)
        self.assertEqual(self._risks(reloaded), [])


if __name__ == "__main__":
    unittest.main()
