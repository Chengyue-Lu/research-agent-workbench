import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.capability.catalog import (
    AcceptedSkillRegistry,
    filter_candidates,
    load_candidates,
)
from research_workbench.contracts import ContractError


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
            "rc-scientific-humanization": "reference",
            "rc-world-threads-entry": "rejected",
        }

        self.assertEqual(
            expected,
            {candidate_id: by_id[candidate_id]["status"] for candidate_id in expected},
        )


class RegistryContractErrorTests(unittest.TestCase):
    def test_accepted_registry_rejects_wrong_registry_kind(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / "accepted.json"
            index.write_text(
                json.dumps({"registry_kind": "skill_candidates", "entries": []}),
                encoding="utf-8",
            )
            with self.assertRaises(ContractError) as caught:
                AcceptedSkillRegistry.load(index, project_root=directory)
        self.assertEqual("registry_kind", caught.exception.field)

    def test_accepted_registry_rejects_entry_lacking_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / "accepted.json"
            document = {"registry_kind": "skill_accepted", "entries": [{"skill_id": "x"}]}
            index.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(ContractError) as caught:
                AcceptedSkillRegistry.load(index, project_root=directory)
        self.assertEqual("entries[0]", caught.exception.field)

    def test_require_reports_missing_skills_as_contract_error(self) -> None:
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        with self.assertRaises(ContractError) as caught:
            registry.require(["literature-evidence-extraction", "no-such-skill"])
        self.assertEqual("required_skills", caught.exception.field)
        self.assertIn("no-such-skill", str(caught.exception))

    def test_candidate_registry_rejects_wrong_registry_kind(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidates.json"
            path.write_text(json.dumps({"registry_kind": "skill_accepted"}), encoding="utf-8")
            with self.assertRaises(ContractError) as caught:
                load_candidates(path)
        self.assertEqual("registry_kind", caught.exception.field)


if __name__ == "__main__":
    unittest.main()
