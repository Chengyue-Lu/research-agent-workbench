from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from research_workbench.capability import AgentProfile, SkillManifest
from research_workbench.capability import resolver as resolver_module
from research_workbench.contracts import PermissionPolicy
from research_workbench.io import load_document
from research_workbench.tasks import TaskPacket


ROOT = Path(__file__).resolve().parents[1]


class CapabilityResolverBranchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.task = TaskPacket.from_mapping(load_document(ROOT / "examples" / "task-evidence.yaml"))
        cls.profile = AgentProfile.from_mapping(
            load_document(ROOT / "examples" / "profiles" / "evidence-scout.yaml")
        )
        cls.skill = SkillManifest.from_mapping(
            load_document(ROOT / "examples" / "skills" / "literature-evidence-extraction.yaml")
        )

    def test_required_skill_selector_matrix_rejects_ambiguity_duplicates_and_conflicts(self) -> None:
        other_version = replace(self.skill, version="0.2.0")
        cases = (
            (("bad@latest",), (self.skill,), "SKILL-SELECTOR-INVALID"),
            (("missing@1.0.0",), (self.skill,), "SKILL-MISSING"),
            ((self.skill.skill_id,), (self.skill, other_version), "SKILL-VERSION-AMBIGUOUS"),
            ((f"{self.skill.skill_id}@{self.skill.version}",) * 2, (self.skill,), "SKILL-DUPLICATE"),
            ((f"{self.skill.skill_id}@{self.skill.version}", f"{other_version.skill_id}@{other_version.version}"), (self.skill, other_version), "SKILL-VERSION-CONFLICT"),
        )
        for references, skills, code in cases:
            task = replace(self.task, required_skills=references)
            selected, risks = resolver_module._match_required_skills(task, skills)
            with self.subTest(code=code):
                self.assertIn(code, {risk.code for risk in risks})
                if code != "SKILL-DUPLICATE":
                    self.assertLessEqual(len(selected), 1)

    def test_permission_ordering_roots_and_external_write_are_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            resolver_module._narrowest(("unknown",), {"allowed": 1}, "network")
        self.assertEqual(
            "unspecified",
            resolver_module._narrowest(("unspecified",), {"allowed": 1}, "network"),
        )
        ceiling = PermissionPolicy(
            "worktree-write", "search-and-fetch", True, ("work",)
        )
        self.assertTrue(
            resolver_module.permission_policy_covers(
                ceiling,
                PermissionPolicy("read-only", "forbidden", False, ("work/task",)),
            )
        )
        rejected = (
            PermissionPolicy("unknown", "forbidden", False, ()),
            PermissionPolicy("worktree-write", "unknown", False, ()),
            PermissionPolicy("external-write", "forbidden", False, ()),
            PermissionPolicy("read-only", "allowed", False, ()),
            PermissionPolicy("read-only", "forbidden", False, ("outside",)),
        )
        for required in rejected:
            with self.subTest(required=required):
                self.assertFalse(resolver_module.permission_policy_covers(ceiling, required))
        self.assertFalse(
            resolver_module.permission_policy_covers(
                PermissionPolicy("worktree-write", "search-and-fetch", True, ()),
                PermissionPolicy("read-only", "forbidden", False, ("work",)),
            )
        )
        self.assertFalse(
            resolver_module.permission_policy_covers(
                PermissionPolicy("worktree-write", "search-and-fetch", False, ()),
                PermissionPolicy("read-only", "forbidden", True, ()),
            )
        )

    def test_effective_permission_intersection_keeps_only_nested_shared_roots(self) -> None:
        task = replace(
            self.task,
            permissions=PermissionPolicy(
                "worktree-write", "search-and-fetch", False, ("work", "cache")
            ),
        )
        profile = replace(
            self.profile,
            permission_ceiling=PermissionPolicy(
                "worktree-write", "allowed", True, ("work/task", "other")
            ),
        )
        skill = replace(
            self.skill,
            permission_ceiling=PermissionPolicy(
                "worktree-write", "search-and-fetch", True, ("work",)
            ),
        )
        effective = resolver_module._effective_permissions(task, profile, (skill,))
        self.assertEqual(("work/task",), effective.allowed_roots)
        self.assertEqual("search-and-fetch", effective.network)
        self.assertFalse(effective.external_write)


if __name__ == "__main__":
    unittest.main()
