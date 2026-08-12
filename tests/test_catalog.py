import unittest
from pathlib import Path

from research_workbench.capability.catalog import filter_candidates, load_candidates


ROOT = Path(__file__).resolve().parents[1]


class CandidateCatalogTests(unittest.TestCase):
    def test_quarantine_candidate_cannot_be_confused_with_trial(self) -> None:
        candidates = load_candidates(ROOT / "registry" / "skills" / "candidates.json")
        quarantined = filter_candidates(candidates, status="quarantine")
        self.assertEqual(["rc-sci-employee-deep-research"], [item["candidate_id"] for item in quarantined])

    def test_mode_filter_is_metadata_only(self) -> None:
        candidates = load_candidates(ROOT / "registry" / "skills" / "candidates.json")
        experiment = filter_candidates(candidates, mode="experiment", capability="experiment-design")
        self.assertEqual(["rc-experiment-design"], [item["candidate_id"] for item in experiment])


if __name__ == "__main__":
    unittest.main()
