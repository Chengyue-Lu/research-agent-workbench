"""The M6-004 evidence package is hash-pinned by its INDEX; drift fails CI."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file

from support import ROOT

EVIDENCE_DIR = ROOT / "docs/implementation/evidence/M6-004"
INDEX_PATH = EVIDENCE_DIR / "INDEX.yaml"


class EvidenceIndexTests(unittest.TestCase):
    def test_every_indexed_artifact_matches_its_pinned_hash(self) -> None:
        document = yaml.safe_load(INDEX_PATH.read_text(encoding="utf-8"))
        artifacts = document["artifacts"]
        self.assertGreaterEqual(len(artifacts), 10, artifacts)
        for entry in artifacts:
            path = EVIDENCE_DIR / entry["path"]
            self.assertTrue(
                path.is_file(),
                f"INDEX lists {entry['path']} but the file is missing",
            )
            self.assertEqual(
                entry["sha256"],
                hash_file(path),
                f"{entry['path']} drifted from its pinned hash",
            )

    def test_the_index_lists_every_committed_artifact(self) -> None:
        document = yaml.safe_load(INDEX_PATH.read_text(encoding="utf-8"))
        listed = {entry["path"] for entry in document["artifacts"]}
        on_disk = {
            path.relative_to(EVIDENCE_DIR).as_posix()
            for path in EVIDENCE_DIR.rglob("*")
            if path.is_file() and path.name != "INDEX.yaml"
        }
        self.assertEqual(set(), on_disk - listed, "unindexed evidence files exist")


if __name__ == "__main__":
    unittest.main()
