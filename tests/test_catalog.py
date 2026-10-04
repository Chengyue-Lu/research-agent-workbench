import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.capability.catalog import filter_candidates, load_candidates


class CandidateCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def _load_candidates(self, records: list[dict]) -> list[dict]:
        path = self.root / "candidates.json"
        path.write_text(
            json.dumps({"registry_kind": "skill_candidates", "candidates": records}),
            encoding="utf-8",
        )
        return load_candidates(path)

    def test_quarantine_candidates_cannot_be_confused_with_trial(self) -> None:
        records = [
            {"candidate_id": "quarantined-skill", "status": "quarantine"},
            {"candidate_id": "trial-skill", "status": "trial"},
        ]
        candidates = self._load_candidates(records)

        quarantined = filter_candidates(candidates, status="quarantine")
        trial = filter_candidates(candidates, status="trial")

        self.assertEqual(["quarantined-skill"], [item["candidate_id"] for item in quarantined])
        self.assertEqual(["trial-skill"], [item["candidate_id"] for item in trial])
        self.assertEqual(records, candidates)

    def test_mode_filter_is_metadata_only(self) -> None:
        records = [
            {
                "candidate_id": "experiment-design",
                "status": "quarantine",
                "applicable_modes": ["experiment"],
                "capabilities": ["experiment-design"],
                "source_path": "missing-skill/SKILL.md",
            },
            {
                "candidate_id": "simulation-design",
                "applicable_modes": ["simulation"],
                "capabilities": ["experiment-design"],
            },
            {
                "candidate_id": "experiment-observer",
                "applicable_modes": ["experiment"],
                "capabilities": ["observation"],
            },
        ]
        candidates = self._load_candidates(records)
        source_path = self.root / candidates[0]["source_path"]
        self.assertFalse(source_path.exists())

        experiment = filter_candidates(candidates, mode="experiment", capability="experiment-design")

        self.assertEqual(["experiment-design"], [item["candidate_id"] for item in experiment])
        self.assertEqual("quarantine", experiment[0]["status"])
        self.assertEqual(records, candidates)
        self.assertFalse(source_path.exists())


if __name__ == "__main__":
    unittest.main()
