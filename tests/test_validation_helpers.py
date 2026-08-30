from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from research_workbench.artifacts.integrity import hash_bytes
from research_workbench.validation import capability_supply_registry
from research_workbench.validation import documents as documents_module


class ValidationHelperTests(unittest.TestCase):
    def test_research_state_registry_does_not_cycle_through_gate_imports(self) -> None:
        from research_workbench import cli

        self.assertTrue(callable(cli.main))

    @staticmethod
    def _loaded(entries: dict[str, object]) -> documents_module.LoadedDocuments:
        documents = documents_module.LoadedDocuments()
        for relative, document in entries.items():
            documents.add(Path(relative), document, sha256=hash_bytes(relative.encode()))
        return documents

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
        self.assertIsNone(capability_supply_registry._aware_datetime(None))
        self.assertIsNone(capability_supply_registry._aware_datetime("not-a-date"))
        self.assertIsNone(capability_supply_registry._aware_datetime("2026-01-01T00:00:00"))
        self.assertIsNotNone(
            capability_supply_registry._aware_datetime("2026-01-01T00:00:00Z")
        )

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

    def test_registry_and_mode_action_adversarial_categories_are_reported(self) -> None:
        path = Path("registry.yaml")
        source = {"source_id": "S"}
        issues = documents_module._validate_registry(
            path,
            {"sources": ["bad", source, source]},
            "skill_sources",
            set(),
        )
        candidate = {
            "candidate_id": "C",
            "source_id": "UNKNOWN",
            "status": "accepted",
        }
        issues += documents_module._validate_registry(
            path,
            {"candidates": ["bad", candidate, candidate]},
            "skill_candidates",
            {"S"},
        )
        accepted = {
            "skill_id": "skill",
            "version": "1.0.0",
            "status": "wrong",
            "lifecycle": "invalid",
        }
        active = {**accepted, "status": "accepted", "lifecycle": "active"}
        issues += documents_module._validate_registry(
            path,
            {"entries": ["bad", accepted, accepted, active, active]},
            "skill_accepted",
            set(),
        )
        adapter = {"adapter_id": "A"}
        issues += documents_module._validate_registry(
            path,
            {"adapters": ["bad", adapter, adapter]},
            "provider_adapters",
            set(),
        )
        issues += documents_module._validate_registry(
            path, {"registry_kind": "model_pool", "models": "invalid"}, "model_pool", set()
        )

        action = {
            "action_id": "A",
            "version": "1.0.0",
            "mode_ref": "MISSING@1.0.0",
            "claim_effects": {
                "may_support": ["supported"],
                "cannot_alone_support": ["supported"],
            },
        }
        registry = {
            "registry_kind": "mode_action_registry",
            "entries": [
                "bad",
                {
                    "action_id": "A",
                    "version": "1.0.0",
                    "mode_ref": "OTHER@1.0.0",
                    "document_path": "wrong.yaml",
                    "content_hash": "0" * 64,
                },
                {"action_id": "A", "version": "1.0.0"},
                {"action_id": "MISSING", "version": "1.0.0"},
            ],
        }
        documents = self._loaded(
            {
                "registry/actions.json": registry,
                "actions/a.yaml": action,
                "archive/a.yaml": action,
            }
        )
        issues += documents_module._validate_mode_action_registry(documents)
        codes = {issue.code for issue in issues}
        self.assertLessEqual(
            {
                "SOURCE-INVALID",
                "SOURCE-DUPLICATE",
                "CANDIDATE-INVALID",
                "CANDIDATE-DUPLICATE",
                "SOURCE-UNKNOWN",
                "CANDIDATE-UNPINNED",
                "ACCEPTED-INVALID",
                "ACCEPTED-DUPLICATE",
                "ACCEPTED-STATUS",
                "ACCEPTED-LIFECYCLE",
                "ACCEPTED-ACTIVE-DUPLICATE",
                "PROVIDER-ADAPTER-INVALID",
                "PROVIDER-ADAPTER-DUPLICATE",
                "MODEL-POOL-INVALID",
                "MODE-ACTION-DUPLICATE",
                "MODE-ACTION-REGISTRY-DUPLICATE",
                "MODE-ACTION-DOCUMENT-MISSING",
                "MODE-ACTION-PATH-MISMATCH",
                "MODE-ACTION-MODE-MISMATCH",
                "MODE-ACTION-HASH-MISMATCH",
            },
            codes,
        )

    def test_requirement_and_skill_need_closed_set_adversarial_matrix(self) -> None:
        requirement = {
            "requirement_id": "OTHER",
            "constraints": {},
            "unsatisfied_requirement": {},
        }
        requirement_index = {
            "registry_kind": "capability_requirement_index",
            "entries": [
                "bad",
                {"requirement_id": "REQ", "document_path": "requirements/req.yaml", "content_hash": "0" * 64},
                {"requirement_id": "REQ", "document_path": "requirements/other.yaml"},
                {"requirement_id": "OTHER-2", "document_path": "requirements/req.yaml"},
                {"requirement_id": "MISSING", "document_path": "requirements/missing.yaml"},
                {"requirement_id": "WRONG", "document_path": "requirements/wrong.yaml"},
            ],
        }
        need = {
            "need_ref": "OTHER@1.0.0",
            "need_id": "OTHER",
            "version": "1.0.0",
            "semantic_gap": {},
            "mode_refs": ["UNKNOWN-MODE@1.0.0"],
            "origin_actions": [
                {"action_ref": "UNKNOWN-A@1.0.0"},
                {"action_ref": "UNKNOWN-A@1.0.0"},
            ],
            "baseline": {"capability_requirement_refs": ["UNKNOWN-REQ"]},
            "evaluation_requirements": {
                "required_evidence_classes": [
                    {"evidence_class_id": "E"},
                    {"evidence_class_id": "E"},
                    "bad",
                ],
                "criteria": [
                    {"criterion_id": "C", "evidence_class_refs": ["MISSING"]},
                    {"criterion_id": "C", "evidence_class_refs": []},
                    "bad",
                ],
            },
            "domain_scope": {
                "variants": [
                    {"variant_id": "V"},
                    {"variant_id": "V"},
                    "bad",
                ]
            },
        }
        need_index = {
            "registry_kind": "skill_need_index",
            "entries": [
                "bad",
                {"need_ref": "N@1.0.0", "need_id": "N", "version": "1.0.0", "document_path": "needs/n.yaml", "content_hash": "0" * 64},
                {"need_ref": "N@1.0.0", "need_id": "N2", "version": "1.0.0", "document_path": "needs/n2.yaml"},
                {"need_ref": "N2@1.0.0", "need_id": "N", "version": "1.0.0", "document_path": "needs/n3.yaml"},
                {"need_ref": "N3@1.0.0", "need_id": "N3", "version": "1.0.0", "document_path": "needs/n.yaml"},
                {"need_ref": "MISSING@1.0.0", "need_id": "MISSING", "version": "1.0.0", "document_path": "needs/missing.yaml"},
                {"need_ref": "WRONG@1.0.0", "need_id": "WRONG", "version": "1.0.0", "document_path": "needs/wrong.yaml"},
            ],
        }
        documents = self._loaded(
            {
                "registry/requirements.json": requirement_index,
                "requirements/req.yaml": requirement,
                "requirements/wrong.yaml": {"schema_version": "0.1.0"},
                "registry/needs.json": need_index,
                "needs/n.yaml": need,
                "needs/wrong.yaml": {"schema_version": "0.1.0"},
                "modes/m.yaml": {"mode_id": "M", "version": "1.0.0", "claim_rules": {}},
                "registry/actions.json": {
                    "registry_kind": "mode_action_registry",
                    "entries": [{"action_id": "KNOWN", "version": "1.0.0", "mode_ref": "M@1.0.0"}],
                },
            }
        )
        issues = documents_module._validate_capability_requirement_set(documents)
        issues += documents_module._validate_skill_need_set(documents)
        codes = {issue.code for issue in issues}
        self.assertLessEqual(
            {
                "CAPABILITY-REQUIREMENT-IDENTITY-DUPLICATE",
                "CAPABILITY-REQUIREMENT-PATH-DUPLICATE",
                "CAPABILITY-REQUIREMENT-DOCUMENT-MISSING",
                "CAPABILITY-REQUIREMENT-DOCUMENT-KIND",
                "CAPABILITY-REQUIREMENT-IDENTITY-MISMATCH",
                "CAPABILITY-REQUIREMENT-HASH-MISMATCH",
                "SKILL-NEED-REFERENCE-DUPLICATE",
                "SKILL-NEED-IDENTITY-DUPLICATE",
                "SKILL-NEED-PATH-DUPLICATE",
                "SKILL-NEED-DOCUMENT-MISSING",
                "SKILL-NEED-DOCUMENT-KIND",
                "SKILL-NEED-IDENTITY-MISMATCH",
                "SKILL-NEED-HASH-MISMATCH",
                "SKILL-NEED-MODE-MISSING",
                "SKILL-NEED-ACTION-DUPLICATE",
                "SKILL-NEED-ACTION-MISSING",
                "SKILL-NEED-CAPABILITY-REQUIREMENT-MISSING",
                "SKILL-NEED-EVIDENCE-CLASS-DUPLICATE",
                "SKILL-NEED-CRITERION-DUPLICATE",
                "SKILL-NEED-EVIDENCE-CLASS-MISSING",
                "SKILL-NEED-DOMAIN-VARIANT-DUPLICATE",
            },
            codes,
        )

    def test_protocol_profile_closed_set_adversarial_matrix(self) -> None:
        profile = {
            "profile_id": "OTHER",
            "version": "1.0.0",
            "method_standard": {},
            "method_obligations": [
                "bad",
                {
                    "obligation_id": "O",
                    "applies_to_action_refs": ["UNKNOWN-A@1.0.0"],
                    "evidence_expectation_refs": ["UNKNOWN-E"],
                    "gate_expectation_refs": ["UNKNOWN-G"],
                },
                {"obligation_id": "O", "applies_to_action_refs": []},
            ],
            "compatible_mode_refs": ["UNKNOWN-MODE@1.0.0"],
            "scoped_actions": [
                "bad",
                {"action_ref": "UNKNOWN-A@1.0.0"},
                {"action_ref": "UNKNOWN-A@1.0.0"},
            ],
            "evidence_expectations": ["bad", {"expectation_id": "E"}, {"expectation_id": "E"}],
            "gate_expectations": ["bad", {"gate_ref": "G"}, {"gate_ref": "G"}],
        }
        index = {
            "registry_kind": "protocol_profile_index",
            "entries": [
                "bad",
                {"profile_ref": "P@1.0.0", "profile_id": "P", "version": "1.0.0", "document_path": "profiles/p.yaml", "content_hash": "0" * 64},
                {"profile_ref": "P@1.0.0", "profile_id": "P2", "version": "1.0.0", "document_path": "profiles/p2.yaml"},
                {"profile_ref": "P2@1.0.0", "profile_id": "P", "version": "1.0.0", "document_path": "profiles/p3.yaml"},
                {"profile_ref": "P3@1.0.0", "profile_id": "P3", "version": "1.0.0", "document_path": "profiles/p.yaml"},
                {"profile_ref": "MISSING@1.0.0", "profile_id": "MISSING", "version": "1.0.0", "document_path": "profiles/missing.yaml"},
                {"profile_ref": "WRONG@1.0.0", "profile_id": "WRONG", "version": "1.0.0", "document_path": "profiles/wrong.yaml"},
            ],
        }
        documents = self._loaded(
            {
                "registry/profiles.json": index,
                "profiles/p.yaml": profile,
                "profiles/wrong.yaml": {"schema_version": "0.1.0"},
                "modes/m.yaml": {"mode_id": "M", "version": "1.0.0", "claim_rules": {}},
                "registry/actions.json": {
                    "registry_kind": "mode_action_registry",
                    "entries": [{"action_id": "KNOWN", "version": "1.0.0", "mode_ref": "M@1.0.0"}],
                },
            }
        )
        codes = {
            issue.code
            for issue in documents_module._validate_protocol_profile_set(documents)
        }
        self.assertLessEqual(
            {
                "PROTOCOL-PROFILE-REFERENCE-DUPLICATE",
                "PROTOCOL-PROFILE-IDENTITY-DUPLICATE",
                "PROTOCOL-PROFILE-PATH-DUPLICATE",
                "PROTOCOL-PROFILE-DOCUMENT-MISSING",
                "PROTOCOL-PROFILE-DOCUMENT-KIND",
                "PROTOCOL-PROFILE-IDENTITY-MISMATCH",
                "PROTOCOL-PROFILE-HASH-MISMATCH",
                "PROTOCOL-PROFILE-MODE-MISSING",
                "PROTOCOL-PROFILE-ACTION-DUPLICATE",
                "PROTOCOL-PROFILE-ACTION-MISSING",
                "PROTOCOL-PROFILE-EVIDENCE-DUPLICATE",
                "PROTOCOL-PROFILE-GATE-DUPLICATE",
                "PROTOCOL-PROFILE-OBLIGATION-DUPLICATE",
                "PROTOCOL-PROFILE-OBLIGATION-EVIDENCE-MISSING",
                "PROTOCOL-PROFILE-OBLIGATION-GATE-MISSING",
            },
            codes,
        )

    def test_integrity_index_cardinality_and_entry_shape_fail_closed(self) -> None:
        requirement_index = {"registry_kind": "capability_requirement_index", "entries": []}
        requirement_issues = documents_module._validate_capability_requirement_set(
            {
                Path("requirements-a.json"): requirement_index,
                Path("requirements-b.json"): requirement_index,
            }
        )
        self.assertIn(
            "CAPABILITY-REQUIREMENT-INDEX-DUPLICATE",
            {issue.code for issue in requirement_issues},
        )
        self.assertEqual(
            {},
            documents_module._capability_requirement_entries(
                {
                    Path("requirements-a.json"): requirement_index,
                    Path("requirements-b.json"): requirement_index,
                }
            ),
        )
        self.assertEqual(
            {},
            documents_module._capability_requirement_entries(
                {
                    Path("requirements.json"): {
                        "registry_kind": "capability_requirement_index",
                        "entries": ["bad", {"requirement_id": 1}],
                    }
                }
            ),
        )

        need_index = {"registry_kind": "skill_need_index", "entries": []}
        need_issues = documents_module._validate_skill_need_set(
            {Path("needs-a.json"): need_index, Path("needs-b.json"): need_index}
        )
        self.assertIn("SKILL-NEED-INDEX-DUPLICATE", {issue.code for issue in need_issues})
        self.assertEqual(
            {},
            documents_module._skill_need_entries(
                {
                    Path("needs.json"): {
                        "registry_kind": "skill_need_index",
                        "entries": ["bad", {"need_ref": 1}],
                    }
                }
            ),
        )

        profile = {
            "profile_id": "P",
            "version": "1.0.0",
            "method_standard": {},
            "method_obligations": [],
        }
        missing_issues = documents_module._validate_protocol_profile_set(
            {Path("profiles/p.yaml"): profile}
        )
        self.assertIn(
            "PROTOCOL-PROFILE-INDEX-MISSING",
            {issue.code for issue in missing_issues},
        )
        profile_index = {"registry_kind": "protocol_profile_index", "entries": []}
        duplicate_issues = documents_module._validate_protocol_profile_set(
            {
                Path("profiles-a.json"): profile_index,
                Path("profiles-b.json"): profile_index,
            }
        )
        self.assertIn(
            "PROTOCOL-PROFILE-INDEX-DUPLICATE",
            {issue.code for issue in duplicate_issues},
        )
        self.assertEqual(
            [],
            documents_module._validate_protocol_profile_set(
                {
                    Path("profiles.json"): {
                        "registry_kind": "protocol_profile_index",
                        "entries": ["bad", {"profile_ref": 1}],
                    }
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
