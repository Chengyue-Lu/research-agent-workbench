from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from research_workbench.validation import documents as documents_module


class ValidationHelperTests(unittest.TestCase):
    def test_recent_contract_kinds_are_inferred_without_registry_context(self) -> None:
        cases = (
            ({"profile": "runtime-bundle", "bundle_id": "B", "documents": []}, "runtime_bundle_manifest"),
            ({"binding_id": "B", "selected_supply_report_ref": {}, "host": {}}, "execution_binding"),
            ({"record_kind": "actual-execution-binding", "actual_binding": {}}, "execution_trace_fact"),
            ({"report_id": "H", "actual_binding": {}, "actual_facts": {}}, "execution_host_report"),
            ({"scope": "m11-core", "gate_id": "G", "paths": []}, "execution_core_gate"),
            ({"receipt_id": "R", "host_report_ref": {}, "view_ref": {}}, "generic_execution_receipt"),
            ({"policy_id": "P", "policy_kind": "host-policy", "permission_ceiling": {}}, "execution_policy"),
            ({"view_id": "V", "execution_binding_ref": {}, "effective_constraints": {}}, "resolved_execution_view"),
            ({"report_id": "A", "source_id": "S", "archive_signals": []}, "skill_archive_audit"),
            ({}, None),
        )
        for document, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(expected, documents_module.infer_document_kind(document))

    def test_datetime_hash_and_required_field_helpers_fail_closed(self) -> None:
        self.assertIsNone(documents_module._aware_datetime(None))
        self.assertIsNone(documents_module._aware_datetime("not-a-date"))
        self.assertIsNone(documents_module._aware_datetime("2026-01-01T00:00:00"))
        self.assertIsNotNone(documents_module._aware_datetime("2026-01-01T00:00:00Z"))

        path = Path("fixture.yaml")
        issues = documents_module._require_fields(path, {"present": True}, ("present", "missing"))
        self.assertEqual(["FIELD-MISSING"], [issue.code for issue in issues])
        issues = documents_module._validate_hashes(
            path,
            {
                "items": [
                    {"sha256": "REPLACE_WITH_SHA256"},
                    {"content_hash": "short"},
                    {"sha256": "a" * 64},
                ]
            },
        )
        self.assertEqual(
            {"HASH-PLACEHOLDER", "HASH-INVALID"}, {issue.code for issue in issues}
        )

    def test_document_dispatch_and_parse_boundaries_report_structured_issues(self) -> None:
        documents = {
            Path("scalar.yaml"): [],
            Path("unknown.yaml"): {"schema_version": "0.1.0"},
            Path("sources.yaml"): {
                "registry_kind": "skill_sources",
                "sources": ["ignored", {"source_id": 1}, {"source_id": "source-a"}],
            },
            Path("view.yaml"): {
                "schema_version": "0.1.0",
                "view_id": "V",
                "execution_binding_ref": {},
                "effective_constraints": {},
            },
        }
        issues = documents_module.validate_documents(documents)
        codes = {issue.code for issue in issues}
        self.assertLessEqual({"DOCUMENT-INVALID", "DOCUMENT-UNKNOWN", "SCHEMA-INVALID"}, codes)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            invalid = root / "invalid.yaml"
            invalid.write_text("not: [yaml", encoding="utf-8")
            loaded, issues = documents_module.load_and_validate((invalid,))
            self.assertEqual({}, loaded)
            self.assertEqual(["PARSE-ERROR"], [issue.code for issue in issues])

            valid = root / "valid.json"
            valid.write_text('{"schema_version":"0.1.0"}', encoding="utf-8")
            loaded, issues = documents_module.load_and_validate((valid,))
            self.assertIsNotNone(loaded.sha256_for(valid))
            self.assertIn("DOCUMENT-UNKNOWN", {issue.code for issue in issues})


if __name__ == "__main__":
    unittest.main()
