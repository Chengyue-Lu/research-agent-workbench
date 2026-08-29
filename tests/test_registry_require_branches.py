from __future__ import annotations

from pathlib import Path
import unittest

from research_workbench.capability.catalog import (
    AcceptedSkillRegistry,
    SkillRegistrySelectionError,
    filter_candidates,
    load_candidates,
)
from research_workbench.capability.skill_needs import SkillNeedSet
from research_workbench.protocol.profiles import ProtocolProfileSet


ROOT = Path(__file__).resolve().parents[1]


class RegistryRequireBranchTests(unittest.TestCase):
    def test_skill_need_and_protocol_profile_require_are_exact_and_unique(self) -> None:
        needs = SkillNeedSet.load(ROOT / "registry" / "skill-needs.json", project_root=ROOT)
        need_ref = needs.entries[0].need_ref
        self.assertEqual(need_ref, needs.require(need_ref)[0].need_ref)
        for references in ((need_ref, need_ref), ("missing@1.0.0",)):
            with self.assertRaises(ValueError):
                needs.require(references)

        profiles = ProtocolProfileSet.load(
            ROOT / "registry" / "protocol-profiles.json", project_root=ROOT
        )
        profile_ref = profiles.entries[0].profile_ref
        self.assertEqual(profile_ref, profiles.require(profile_ref)[0].reference)
        for references in ((profile_ref, profile_ref), ("missing@1.0.0",)):
            with self.assertRaises(ValueError):
                profiles.require(references)

    def test_accepted_skill_selection_rejects_purpose_selector_missing_and_duplicate(self) -> None:
        registry = AcceptedSkillRegistry.load(
            ROOT / "registry" / "skills" / "accepted.json", project_root=ROOT
        )
        entry = registry.entries[0]
        exact_ref = f"{entry.skill_id}@{entry.version}"
        selected = registry.require(exact_ref, purpose="historical-replay")[0]
        self.assertEqual(exact_ref, f"{selected.skill_id}@{selected.version}")
        cases = (
            ((exact_ref,), "unsupported", ValueError),
            (("bad@latest",), "new-assignment", SkillRegistrySelectionError),
            ((entry.skill_id,), "historical-replay", SkillRegistrySelectionError),
            (("missing@1.0.0",), "new-assignment", SkillRegistrySelectionError),
            ((exact_ref, exact_ref), "historical-replay", SkillRegistrySelectionError),
            ((exact_ref,), "new-assignment", SkillRegistrySelectionError),
        )
        for references, purpose, error in cases:
            with self.subTest(purpose=purpose, references=references), self.assertRaises(error):
                registry.require(references, purpose=purpose)

    def test_candidate_filters_compose_without_mutating_registry_entries(self) -> None:
        candidates = load_candidates(ROOT / "registry" / "skills" / "candidates.json")
        first = candidates[0]
        filtered = filter_candidates(
            candidates,
            status=first.get("status"),
            mode=(first.get("mode_ids") or [None])[0],
            capability=(first.get("capabilities") or [None])[0],
        )
        self.assertIsInstance(filtered, list)
        self.assertTrue(all(item in candidates for item in filtered))


if __name__ == "__main__":
    unittest.main()
