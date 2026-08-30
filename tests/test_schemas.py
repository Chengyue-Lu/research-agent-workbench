import unittest
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]


class VersionedSchemaTests(unittest.TestCase):
    def test_all_seven_research_object_types_have_valid_positive_fixtures(self) -> None:
        catalog = SchemaCatalog(ROOT / "schemas")
        paths = sorted((ROOT / "examples" / "objects").rglob("*.yaml"))
        self.assertGreaterEqual(len(paths), 7)
        for path in paths:
            with self.subTest(path=path.name):
                self.assertEqual([], catalog.validate("research_object", load_document(path)))

    def test_all_seven_research_object_types_reject_negative_fixtures(self) -> None:
        catalog = SchemaCatalog(ROOT / "schemas")
        paths = sorted((ROOT / "tests" / "fixtures" / "invalid" / "objects").glob("*.json"))
        self.assertEqual(7, len(paths))
        for path in paths:
            with self.subTest(path=path.name):
                self.assertTrue(catalog.validate("research_object", load_document(path)))

    def test_contract_schema_catalog_is_complete(self) -> None:
        catalog = SchemaCatalog(ROOT / "schemas")
        self.assertEqual(
            {
                "agent_profile",
                "agent_trace_actors",
                "agent_trace_envelope",
                "agent_trace_event",
                "agent_trace_index",
                "attempt",
                "attempt_completion_manifest",
                "capability_requirement",
                "capability_requirement_index",
                "capability_conformance_evidence",
                "capability_resolution",
                "capability_supply_report",
                "context_snapshot",
                "deterministic_check_report",
                "decision_authority_matrix",
                "authority_rule_eligibility",
                "evaluation_manifest",
                "execution_receipt",
                "execution_binding",
                "execution_trace_fact",
                "execution_host_report",
                "execution_core_gate",
                "execution_policy",
                "handoff_packet",
                "generic_execution_receipt",
                "handoff_transfer_audit",
                "handoff_transfer_manifest",
                "main_state",
                "method_resolution",
                "method_trace",
                "mode_action",
                "mode_action_registry",
                "phase_b_evolution_gate",
                "phase_c_gate_manifest",
                "phase_c_gate_report",
                "project_protocol",
                "protocol_profile",
                "protocol_profile_index",
                "provider_conformance_report",
                "research_mode",
                "research_mode_migration",
                "research_object",
                "research_attempt_lineage",
                "research_failure",
                "research_state",
                "resolved_capability_snapshot",
                "resolved_execution_view",
                "runtime_bundle_manifest",
                "skill_manifest",
                "skill_assignment",
                "skill_archive_audit",
                "skill_evaluation",
                "skill_lifecycle_index",
                "skill_lifecycle_migration",
                "skill_lifecycle_record",
                "skill_release_projection",
                "skill_release_projection_index",
                "skill_need",
                "skill_need_index",
                "source_admission",
                "task_packet",
            },
            set(catalog.document_kinds),
        )


if __name__ == "__main__":
    unittest.main()
