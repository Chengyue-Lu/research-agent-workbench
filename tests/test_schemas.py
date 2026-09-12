import unittest
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog
from research_workbench.validation.schemas import _check_schema_bytes

ROOT = Path(__file__).resolve().parents[1]


class SchemaReuseTests(unittest.TestCase):
    def setUp(self):
        _check_schema_bytes.cache_clear()
        self.addCleanup(_check_schema_bytes.cache_clear)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'v0.1.0'
        self.directory.mkdir()
        self.path = self.directory / 'example.schema.json'
        self.schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
                       '$id': 'https://example.invalid/example', 'x-rwb-document-kind': 'example',
                       'type': 'object', 'properties': {'value': {'type': 'integer'}}, 'required': ['value']}
        self.raw = json.dumps(self.schema).encode()
        self.path.write_bytes(self.raw)

    def test_schema_lifecycle_reuses_bytes_but_rechecks_changed_inputs_and_invalid_schemas(self):
        """Schema lifecycle: reuse, changed bytes, invalid schema, restore, rename, remove."""
        with patch.object(Draft202012Validator, 'check_schema', wraps=Draft202012Validator.check_schema) as check:
            with self.subTest(checkpoint='identical bytes'):
                first = SchemaCatalog(self.root)
                second = SchemaCatalog(self.root)
                self.assertEqual(1, check.call_count)
                self.assertEqual([], first.validate('example', {'value': 1}))
                self.assertTrue(second.validate('example', {'value': 'wrong'}))
            with self.subTest(checkpoint='different bytes with same size and timestamp'):
                timestamp = self.path.stat()
                changed = self.raw.replace(b'"integer"', b'"string" ')
                self.assertEqual(len(self.raw), len(changed))
                self.path.write_bytes(changed)
                os.utime(self.path, ns=(timestamp.st_atime_ns, timestamp.st_mtime_ns))
                current = SchemaCatalog(self.root)
                self.assertEqual(2, check.call_count)
                self.assertTrue(current.validate('example', {'value': 1}))
                self.assertEqual([], current.validate('example', {'value': 'now valid'}))
            with self.subTest(checkpoint='invalid schema is never cached as success'):
                self.path.write_text(json.dumps({**self.schema, 'type': 17}))
                for _ in range(2):
                    with self.assertRaises(SchemaError): SchemaCatalog(self.root)
                self.assertEqual(4, check.call_count)
            with self.subTest(checkpoint='restore then rename'):
                self.path.write_bytes(self.raw)
                self.path.rename(self.directory / 'renamed.schema.json')
                restored = SchemaCatalog(self.root)
                self.assertEqual(('renamed',), restored.names)
                self.assertEqual([], restored.validate('example', {'value': 1}))
                self.assertEqual(4, check.call_count)
            with self.subTest(checkpoint='remove from inventory'):
                (self.directory / 'renamed.schema.json').unlink()
                self.assertEqual((), SchemaCatalog(self.root).names)
                with self.assertRaises(KeyError): SchemaCatalog(self.root).schema('renamed')

    def test_catalog_mutation_and_checker_change_cannot_poison_reused_self_checks(self):
        original = SchemaCatalog(self.root)
        original.schema('example')['properties']['value']['type'] = 'string'
        fresh = SchemaCatalog(self.root)
        self.assertTrue(original.validate('example', {'value': 1}))
        self.assertEqual([], fresh.validate('example', {'value': 1}))
        with patch.object(Draft202012Validator, 'check_schema', side_effect=SchemaError('new checker rejects')) as check:
            for _ in range(2):
                with self.assertRaisesRegex(SchemaError, 'new checker rejects'): SchemaCatalog(self.root)
            self.assertEqual(2, check.call_count)
        self.assertEqual([], SchemaCatalog(self.root).validate('example', {'value': 1}))

    def test_catalog_roots_and_reads_remain_independent_after_a_cache_hit(self):
        SchemaCatalog(self.root)
        other = self.root / 'other'
        (other / 'v0.1.0').mkdir(parents=True)
        path = other / 'v0.1.0/other.schema.json'
        path.write_bytes(self.raw)
        self.assertEqual(('other',), SchemaCatalog(other).names)
        self.path.write_text('invalid JSON')
        with self.assertRaises(json.JSONDecodeError): SchemaCatalog(self.root)
        self.assertEqual([], SchemaCatalog(other).validate('example', {'value': 1}))
        self.path.write_text('[]')
        with self.assertRaisesRegex(SchemaError, 'must be an object'): SchemaCatalog(self.root)
        self.path.write_text(json.dumps({'type': 'object'}))
        with self.assertRaisesRegex(SchemaError, 'lacks \\$id'): SchemaCatalog(self.root)


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
                "a3_a4_pairwise_comparability",
                "a4_execution_qualification",
                "admission_evidence_overlap",
                "agent_profile",
                "agent_trace_actors",
                "agent_trace_envelope",
                "agent_trace_event",
                "agent_trace_index",
                "arm_execution_qualification",
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
                "evaluation_case_closure",
                "evaluation_manifest",
                "evaluation_measurement",
                "evaluation_provider_interface",
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
                "promotion_execution_receipt",
                "claim_evidence_map",
                "promotion_record",
                "promotion_validation_authority_registry",
                "promotion_validation_execution",
                "promotion_validation_host_receipt",
                "promotion_validation_policy",
                "protocol_profile",
                "protocol_profile_index",
                "provider_conformance_report",
                "research_mode",
                "runtime_resource_manifest",
                "research_mode_migration",
                "research_object",
                "research_attempt_lineage",
                "research_failure",
                "research_state",
                "resolved_capability_snapshot",
                "resolved_execution_view",
                "runtime_bundle_manifest",
                "run_reconstruction_environment",
                "run_reconstruction_manifest",
                "run_reconstruction_report",
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
                "system_evaluation_protocol",
                "task_packet",
            },
            set(catalog.document_kinds),
        )


if __name__ == "__main__":
    unittest.main()
