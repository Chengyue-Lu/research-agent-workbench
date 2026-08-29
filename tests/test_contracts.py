import copy
import unittest
from pathlib import Path

from research_workbench.capability import AgentProfile, SkillManifest
from research_workbench.context import MainStatePacket
from research_workbench.contracts import ContractError, PermissionPolicy
from research_workbench.contracts.common import (
    mapping_tuple,
    mapping_value,
    optional_string,
    parse_skill_reference,
    require_relative_path,
    require_string,
    string_tuple,
)
from research_workbench.io import load_document
from research_workbench.protocol import MethodResolution, ModeAction, ProjectProtocol, ResearchMode
from research_workbench.tasks import (
    AttemptRecord,
    DelegationPolicy,
    FileReference,
    HandoffPacket,
    HandoffPolicy,
    TaskBudget,
    TaskPacket,
)


ROOT = Path(__file__).resolve().parents[1]


class ContractParsingTests(unittest.TestCase):
    def load(self, relative: str):
        return load_document(ROOT / relative)

    def test_project_protocol_and_modes_parse(self) -> None:
        protocol = ProjectProtocol.from_mapping(self.load("examples/project-protocol.yaml"))
        evidence_mode = ResearchMode.from_mapping(self.load("examples/modes/evidence-synthesis.yaml"))
        self.assertEqual("dual-mode-demo", protocol.project_id)
        self.assertIn("source_reported", evidence_mode.claim_allows)
        self.assertEqual("0.2.0", evidence_mode.version)
        self.assertEqual(8, len(evidence_mode.action_refs))
        self.assertEqual((), evidence_mode.recommended_skill_capabilities)

    def test_mode_action_parses_as_a_first_class_contract(self) -> None:
        action = ModeAction.from_mapping(
            self.load("registry/modes/actions/evidence-synthesis/ES-A4.yaml")
        )
        self.assertEqual("ES-A4@1.0.0", action.reference)
        self.assertEqual("evidence-synthesis@0.1.0", action.mode_ref)
        self.assertIn("evidence-record", action.required_artifacts)

    def test_method_resolution_parses_without_execution_bindings(self) -> None:
        resolution = MethodResolution.from_mapping(
            self.load("examples/method-resolutions/ROUTE-SIM-CONVERGENCE-005.yaml")
        )
        self.assertEqual("MR-ROUTE-SIM-CONVERGENCE-005", resolution.resolution_id)
        self.assertEqual("skill-need", resolution.skill_disposition.status)
        self.assertEqual("proceed", resolution.resolution_status)
        self.assertEqual(64, len(resolution.task_ref.sha256))
        self.assertFalse(hasattr(resolution, "provider"))

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

    def test_common_contract_primitives_reject_invalid_types_and_paths(self) -> None:
        calls = (
            lambda: parse_skill_reference("bad@latest"),
            lambda: require_string({"value": ""}, "value"),
            lambda: optional_string({"value": 1}, "value"),
            lambda: string_tuple({"value": [""]}, "value"),
            lambda: mapping_value({"value": []}, "value"),
            lambda: mapping_tuple({"value": [1]}, "value"),
            lambda: require_relative_path("/absolute", "path"),
            lambda: require_relative_path("../escape", "path"),
            lambda: PermissionPolicy.from_mapping({"external_write": "unknown"}),
            lambda: PermissionPolicy.from_mapping({"external_write": 1}),
            lambda: PermissionPolicy.from_mapping({"allowed_roots": ["../outside"]}),
            lambda: PermissionPolicy.from_mapping({"filesystem": 1, "network": []}),
        )
        for index, call in enumerate(calls):
            with self.subTest(index=index), self.assertRaises(ContractError):
                call()

    def test_task_contract_models_reject_invalid_budget_delegation_and_lifecycle_fields(self) -> None:
        invalid_calls = (
            lambda: FileReference.from_mapping({"path": "a", "sha256": "bad"}),
            lambda: FileReference.from_mapping({"path": "a", "sha256": "0" * 64, "revision": 0}),
            lambda: DelegationPolicy.from_mapping({"allowed": "yes"}),
            lambda: DelegationPolicy.from_mapping({"allowed": True, "max_depth": -1}),
            lambda: DelegationPolicy.from_mapping({"allowed": True, "max_parallel": -1}),
            lambda: DelegationPolicy.from_mapping({"allowed": False, "max_depth": 1}),
            lambda: DelegationPolicy.from_mapping({"allowed": True, "sub_budget": []}),
            lambda: TaskBudget.from_mapping({"max_turns": 0}),
            lambda: HandoffPolicy.from_mapping({"require_transfer_manifest": "yes"}),
            lambda: HandoffPolicy.from_mapping({"semantic_review": "sometimes"}),
            lambda: HandoffPolicy.from_mapping({"minimum_semantic_samples": True}),
        )
        for index, call in enumerate(invalid_calls):
            with self.subTest(index=index), self.assertRaises(ContractError):
                call()

        task = self.load("examples/task-evidence.yaml")
        for field, value in (("required_outputs", [1]), ("revision", 0)):
            changed = copy.deepcopy(task)
            changed[field] = value
            with self.subTest(task_field=field), self.assertRaises(ContractError):
                TaskPacket.from_mapping(changed)

        attempt = self.load("examples/attempt-evidence.yaml")
        for field, value in (
            ("task_revision", 0),
            ("trace_ref", "bad"),
            ("failure", []),
            ("status", "unknown"),
        ):
            changed = copy.deepcopy(attempt)
            changed[field] = value
            with self.subTest(attempt_field=field), self.assertRaises(ContractError):
                AttemptRecord.from_mapping(changed)

        handoff = self.load("examples/handoff-evidence.yaml")
        changed = copy.deepcopy(handoff)
        changed["status"] = "running"
        with self.assertRaises(ContractError):
            HandoffPacket.from_mapping(changed)
        changed = copy.deepcopy(handoff)
        changed["runtime_metadata_ref"] = "../outside"
        with self.assertRaises(ContractError):
            HandoffPacket.from_mapping(changed)


if __name__ == "__main__":
    unittest.main()
