import unittest
from pathlib import Path

from research_workbench.capability import AgentProfile, SkillManifest
from research_workbench.context import MainStatePacket
from research_workbench.io import load_document
from research_workbench.protocol import ProjectProtocol, ResearchMode
from research_workbench.tasks import AttemptRecord, HandoffPacket, TaskPacket


ROOT = Path(__file__).resolve().parents[1]


class ContractParsingTests(unittest.TestCase):
    def load(self, relative: str):
        return load_document(ROOT / relative)

    def test_project_protocol_and_modes_parse(self) -> None:
        protocol = ProjectProtocol.from_mapping(self.load("examples/project-protocol.yaml"))
        evidence_mode = ResearchMode.from_mapping(self.load("examples/modes/evidence-synthesis.yaml"))
        self.assertEqual("dual-mode-demo", protocol.project_id)
        self.assertIn("source_reported", evidence_mode.claim_allows)

    def test_profiles_and_skills_parse_without_provider_types(self) -> None:
        profile = AgentProfile.from_mapping(self.load("examples/profiles/evidence-scout.yaml"))
        skill = SkillManifest.from_mapping(self.load("examples/skills/literature-evidence-extraction.yaml"))
        self.assertEqual("evidence-scout", profile.agent_profile_id)
        self.assertEqual("literature-evidence-extraction", skill.skill_id)
        self.assertFalse(hasattr(profile, "provider"))

    def test_task_handoff_and_main_state_parse(self) -> None:
        task = TaskPacket.from_mapping(self.load("examples/task-evidence.yaml"))
        handoff = HandoffPacket.from_mapping(self.load("examples/handoff-evidence.yaml"))
        incomplete = HandoffPacket.from_mapping(self.load("examples/handoff-incomplete.yaml"))
        attempt = AttemptRecord.from_mapping(self.load("examples/attempt-evidence.yaml"))
        state = MainStatePacket.from_mapping(self.load("examples/main-state.yaml"))
        self.assertEqual(task.task_id, handoff.task_id)
        self.assertEqual("MS-0001", state.checkpoint_id)
        self.assertEqual(task.input_refs, handoff.input_lock)
        self.assertEqual("incomplete", incomplete.status)
        self.assertEqual(handoff.attempt_id, attempt.attempt_id)


if __name__ == "__main__":
    unittest.main()
