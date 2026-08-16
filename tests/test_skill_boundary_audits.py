import shutil
import tempfile
import unittest
from pathlib import Path

from research_workbench.capability import AcceptedSkillRegistry
from research_workbench.contracts import RiskLevel
from research_workbench.io import load_document
from research_workbench.protocol import ResearchModeRegistry
from research_workbench.selection import assess_skill_boundary_audit
from research_workbench.validation import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]


class SkillBoundaryAuditTests(unittest.TestCase):
    def test_all_three_accepted_skills_have_complete_boundary_audits(self) -> None:
        registry = AcceptedSkillRegistry.load(project_root=ROOT)
        paths = sorted((ROOT / "registry/skills/audits").glob("*.yaml"))
        self.assertEqual({entry.skill_id for entry in registry.entries}, {path.stem for path in paths})
        outcomes = {}
        for path in paths:
            document = load_document(path)
            self.assertEqual([], SchemaCatalog().validate("skill_boundary_audit", document))
            risks = assess_skill_boundary_audit(document, registry=registry, root=ROOT)
            self.assertFalse([risk for risk in risks if risk.level == RiskLevel.BLOCK], risks)
            outcomes[path.stem] = document["outcome"]
        self.assertEqual("retain-with-boundary-fix", outcomes["literature-evidence-extraction"])
        self.assertEqual("retain-with-boundary-fix", outcomes["simulation-vv"])
        self.assertEqual("retain-deterministic-first", outcomes["handoff-integrity"])

    def test_accepted_skill_mode_labels_are_formally_registered(self) -> None:
        modes = ResearchModeRegistry.load(project_root=ROOT)
        accepted = AcceptedSkillRegistry.load(project_root=ROOT)
        registered = {entry.mode_id for entry in modes.entries}
        for entry in accepted.entries:
            self.assertLessEqual(set(entry.manifest.applies_to_modes), registered)

    def test_manifest_only_drift_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "registry", root / "registry")
            shutil.copytree(ROOT / ".agents", root / ".agents")
            manifest = root / "registry/skills/accepted/simulation-vv.yaml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "accepted manifest drift"):
                AcceptedSkillRegistry.load(project_root=root)


if __name__ == "__main__":
    unittest.main()
