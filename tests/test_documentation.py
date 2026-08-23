import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
INTERNAL_MILESTONE = re.compile(r"\b(?:K-[A-Z0-9-]+|M\d+-\d+)\b")

FIRST_CONTACT_SURFACES = (
    ROOT / "README.md",
    ROOT / "docs" / "PROJECT_CHARTER.md",
    ROOT / "docs" / "ARCHITECTURE.md",
    ROOT / "docs" / "GETTING_STARTED.md",
)

STABLE_EXAMPLE_MODULES = (
    ROOT / "docs" / "modules" / "02-PROTOCOL_AND_MODES.md",
    ROOT / "docs" / "modules" / "04-SKILL_SYSTEM.md",
    ROOT / "docs" / "modules" / "05-TASK_AND_HANDOFF.md",
)


class DocumentationTests(unittest.TestCase):
    def test_internal_markdown_links_resolve(self) -> None:
        missing: list[str] = []
        for document in [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]:
            text = document.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK.findall(text):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                relative = target.split("#", 1)[0]
                if relative and not (document.parent / relative).resolve().exists():
                    missing.append(f"{document.relative_to(ROOT)} -> {target}")
        self.assertEqual([], missing)

    def test_first_contact_surfaces_do_not_own_internal_milestones(self) -> None:
        leaked: list[str] = []
        for document in FIRST_CONTACT_SURFACES:
            if INTERNAL_MILESTONE.search(document.read_text(encoding="utf-8")):
                leaked.append(str(document.relative_to(ROOT)))
        self.assertEqual([], leaked)

    def test_getting_started_uses_recommended_not_replay_path(self) -> None:
        text = (ROOT / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")
        self.assertNotIn("--historical-replay", text)

    def test_stable_examples_do_not_use_retired_skill_packages(self) -> None:
        retired_ids = (
            "literature-evidence-extraction@0.1.0",
            "simulation-vv@0.1.0",
            "handoff-integrity@0.1.0",
        )
        leaked: list[str] = []
        for document in STABLE_EXAMPLE_MODULES:
            text = document.read_text(encoding="utf-8")
            if any(skill_id in text for skill_id in retired_ids):
                leaked.append(str(document.relative_to(ROOT)))
        self.assertEqual([], leaked)

    def test_document_surface_authorities_exist(self) -> None:
        required = (
            ROOT / "docs" / "STATUS.md",
            ROOT / "docs" / "TASKS.md",
            ROOT / "docs" / "decisions" / "README.md",
            ROOT / "docs" / "implementation" / "README.md",
            ROOT / "docs" / "compatibility" / "README.md",
            ROOT / "docs" / "history" / "README.md",
            ROOT / "docs" / "workstreams" / "README.md",
            ROOT / "docs" / "workstreams" / "huangyi" / "README.md",
            ROOT / ".github" / "CODEOWNERS",
            ROOT / ".github" / "pull_request_template.md",
            ROOT / ".github" / "scripts" / "check_pr_governance.py",
        )
        self.assertEqual([], [str(path.relative_to(ROOT)) for path in required if not path.is_file()])

    def test_execution_runtime_audit_keeps_private_sources_out_of_git(self) -> None:
        audit = (
            ROOT
            / "docs"
            / "workstreams"
            / "huangyi"
            / "execution-runtime-recovery-audit"
        )
        required = (
            "README.md",
            "SOURCE_MANIFEST.md",
            "CLAIM_LEDGER.md",
            "ADOPTION.md",
            "RECOVERY_GATE_PROPOSAL.md",
            "GITHUB_GOVERNANCE_ROLLOUT.md",
        )
        self.assertEqual([], [name for name in required if not (audit / name).is_file()])
        combined = "\n".join(
            (audit / name).read_text(encoding="utf-8") for name in required
        )
        self.assertIsNone(re.search(r"\b[A-Za-z]:[\\/]", combined))
        self.assertFalse((audit / "RWB_4-5部分恢复开发风险审计.md").exists())

    def test_recovery_gate_separates_authority_from_implementation_evidence(self) -> None:
        proposal = (
            ROOT
            / "docs"
            / "workstreams"
            / "huangyi"
            / "execution-runtime-recovery-audit"
            / "RECOVERY_GATE_PROPOSAL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("架构权威", proposal)
        self.assertIn("固定基线实现证明", proposal)
        self.assertIn("accepted", proposal)
        self.assertIn("missing", proposal)
        self.assertIn("不能写成 runtime-enforced guarantee", proposal)

    def test_no_skill_path_requires_execution_view_without_assignment(self) -> None:
        proposal = (
            ROOT
            / "docs"
            / "workstreams"
            / "huangyi"
            / "execution-runtime-recovery-audit"
            / "RECOVERY_GATE_PROPOSAL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("三者都必须有 Resolved Execution View", proposal)
        self.assertIn("前两者不得引用或生成 Skill Assignment", proposal)

    def test_adr_numbers_are_unique(self) -> None:
        numbers: list[str] = []
        for path in (ROOT / "docs" / "decisions").glob("[0-9][0-9][0-9][0-9]-*.md"):
            numbers.append(path.name[:4])
        self.assertEqual(len(numbers), len(set(numbers)))


if __name__ == "__main__":
    unittest.main()
