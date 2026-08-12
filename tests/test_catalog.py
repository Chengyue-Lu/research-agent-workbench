import unittest
from pathlib import Path

from research_workbench.capability.catalog import filter_candidates, load_candidates


ROOT = Path(__file__).resolve().parents[1]


class CandidateCatalogTests(unittest.TestCase):
    def test_quarantine_candidates_cannot_be_confused_with_trial(self) -> None:
        candidates = load_candidates(ROOT / "registry" / "skills" / "candidates.json")
        quarantined = filter_candidates(candidates, status="quarantine")
        self.assertEqual(
            [
                "rc-sci-employee-deep-research",
                "rc-giiisp-scientific-image-generation",
            ],
            [item["candidate_id"] for item in quarantined],
        )

    def test_mode_filter_is_metadata_only(self) -> None:
        candidates = load_candidates(ROOT / "registry" / "skills" / "candidates.json")
        experiment = filter_candidates(candidates, mode="experiment", capability="experiment-design")
        self.assertEqual(["rc-experiment-design"], [item["candidate_id"] for item in experiment])

    def test_user_archive_has_one_pinned_candidate_per_skill_entrypoint(self) -> None:
        candidates = load_candidates(ROOT / "registry" / "skills" / "candidates.json")
        archive_candidates = [
            item
            for item in candidates
            if item["source_id"] == "research-copilot-archive-1.0.0"
        ]
        paths = [item["source_path"] for item in archive_candidates]

        self.assertEqual(18, len(archive_candidates))
        self.assertEqual(18, len(set(paths)))
        self.assertTrue(all(path.endswith("/SKILL.md") for path in paths))
        self.assertTrue(all(item.get("content_hash", "").startswith("sha256:") for item in archive_candidates))

    def test_new_archive_candidates_have_explicit_non_executable_decisions(self) -> None:
        candidates = load_candidates(ROOT / "registry" / "skills" / "candidates.json")
        by_id = {item["candidate_id"]: item for item in candidates}
        expected = {
            "rc-giiisp-scientific-image-generation": "quarantine",
            "rc-manim-agent": "reference",
            "rc-mcp-criticagent": "reference",
            "rc-practical-course-producer": "rejected",
            "rc-scientific-humanization": "triage",
            "rc-world-threads-entry": "rejected",
        }

        self.assertEqual(
            expected,
            {candidate_id: by_id[candidate_id]["status"] for candidate_id in expected},
        )


if __name__ == "__main__":
    unittest.main()
