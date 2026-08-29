import copy
import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.capability import (
    CapabilityRequirement,
    CapabilitySupplyReport,
    assess_supply,
    resolve_status,
)
from research_workbench.io import load_document
from research_workbench.artifacts.integrity import hash_file
from research_workbench.validation import SchemaCatalog, validate_documents
from research_workbench.validation.capability_supply_registry import (
    validate_capability_supply_chain,
)
from research_workbench.validation.document_core import LoadedDocuments


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "examples/capability-resolution"
REPORT_ROOT = FIXTURE_ROOT / "supply-reports"
RESOLUTION_ROOT = FIXTURE_ROOT / "resolutions"
SNAPSHOT_ROOT = FIXTURE_ROOT / "snapshots"
CONFORMANCE_ROOT = FIXTURE_ROOT / "conformance"
METHOD_PATH = ROOT / "examples/method-resolutions/ROUTE-ES-FROZEN-001.yaml"
TASK_PATH = ROOT / "examples/method-resolution-tasks/TASK-MR-ES-FROZEN-001.yaml"
ACTION_INDEX = ROOT / "registry/modes/actions.json"
REQUIREMENT_INDEX = ROOT / "registry/capabilities/requirements.json"
REQUIREMENT_ROOT = ROOT / "registry/capabilities/requirements"
AUTHORITY_MATRIX = ROOT / "registry/authority/decision-authority-matrix.yaml"
MODE_ROOT = ROOT / "registry/modes"
EVALUATED_AT = "2026-08-24T00:00:01Z"


def verified_fixture_evidence(identity, reference, capability_id: str) -> str:
    artifact_ref = reference.get("artifact_ref", {})
    path = ROOT / str(artifact_ref.get("path", ""))
    if reference.get("artifact_kind") != "capability-conformance-evidence" or not path.is_file():
        return "unknown"
    artifact = load_document(path)
    if (
        hash_file(path)
        != str(artifact_ref.get("sha256", "")).removeprefix("sha256:").lower()
        or
        artifact.get("evidence_id") != reference.get("evidence_id")
        or artifact.get("implementation_ref") != identity.implementation_ref
        or artifact.get("implementation_version") != identity.implementation_version
        or capability_id not in artifact.get("capability_ids", [])
    ):
        return "fail"
    return "pass" if artifact.get("result") == "pass" else "fail"


class CapabilityResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = SchemaCatalog(ROOT / "schemas")
        cls.reports = {
            path: load_document(path) for path in sorted(REPORT_ROOT.glob("*.yaml"))
        }
        cls.resolutions = {
            path: load_document(path)
            for path in sorted(RESOLUTION_ROOT.glob("*.yaml"))
        }
        cls.snapshots = {
            path: load_document(path) for path in sorted(SNAPSHOT_ROOT.glob("*.yaml"))
        }
        cls.conformance = {
            path: load_document(path) for path in sorted(CONFORMANCE_ROOT.glob("*.json"))
        }
        cls.action_index = json.loads(ACTION_INDEX.read_text(encoding="utf-8"))
        cls.requirement_index = json.loads(REQUIREMENT_INDEX.read_text(encoding="utf-8"))
        cls.requirements = {
            path: load_document(path)
            for path in sorted(REQUIREMENT_ROOT.glob("*.yaml"))
        }
        cls.validation_documents = {
            **cls.reports,
            **cls.resolutions,
            **cls.snapshots,
            **cls.conformance,
            METHOD_PATH: load_document(METHOD_PATH),
            TASK_PATH: load_document(TASK_PATH),
            ACTION_INDEX: cls.action_index,
            **{
                ROOT / entry["document_path"]: load_document(ROOT / entry["document_path"])
                for entry in cls.action_index["entries"]
            },
            REQUIREMENT_INDEX: cls.requirement_index,
            **cls.requirements,
            AUTHORITY_MATRIX: load_document(AUTHORITY_MATRIX),
            **{
                path: load_document(path)
                for path in sorted([*MODE_ROOT.glob("*.yaml"), *MODE_ROOT.glob("v*/*.yaml")])
            },
        }

    def test_three_core_supply_paths_are_schema_valid(self) -> None:
        self.assertEqual(3, len(self.reports))
        self.assertEqual(3, len(self.resolutions))
        self.assertEqual(3, len(self.snapshots))
        for path, report in self.reports.items():
            with self.subTest(path=path.name):
                self.assertEqual([], self.catalog.validate("capability_supply_report", report))
                self.assertTrue(CapabilitySupplyReport.from_mapping(report).reference)
        for path, resolution in self.resolutions.items():
            with self.subTest(path=path.name):
                self.assertEqual([], self.catalog.validate("capability_resolution", resolution))
        for path, snapshot in self.snapshots.items():
            with self.subTest(path=path.name):
                self.assertEqual(
                    [], self.catalog.validate("resolved_capability_snapshot", snapshot)
                )
        for path, evidence in self.conformance.items():
            with self.subTest(path=path.name):
                self.assertEqual(
                    [], self.catalog.validate("capability_conformance_evidence", evidence)
                )

    def test_typed_live_high_level_evidence_is_expressible_and_hash_bound(self) -> None:
        report = copy.deepcopy(self.reports[REPORT_ROOT / "local-document-reader-a.yaml"])
        evidence = copy.deepcopy(
            self.conformance[CONFORMANCE_ROOT / "local-document-reader-a.json"]
        )
        report["report_id"] = "supply-live-document-reader"
        report["observation_scope"] = "deterministic-local"
        report["availability"] = {
            "status": "available",
            "scope": {
                "scope_kind": "local-environment",
                "scope_ref": "bounded-local-test",
            },
            "observed_at": "2026-08-24T00:00:01Z",
            "facts": ["A bounded local conformance run observed this implementation."],
        }
        evidence["evidence_kind"] = "local-conformance"
        evidence["evidence_id"] = "CONF-LIVE-DOCUMENT-READER"
        evidence["scope"] = {
            "scope_kind": "local-environment",
            "scope_ref": "bounded-local-test",
        }

        with tempfile.TemporaryDirectory() as temp:
            evidence_path = Path(temp) / "capability-evidence.json"
            report_path = Path(temp) / "supply-report.json"
            evidence_path.write_text(
                json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            report["conformance_evidence"] = [
                {
                    "evidence_id": evidence["evidence_id"],
                    "evidence_class": "live",
                    "artifact_kind": "capability-conformance-evidence",
                    "artifact_ref": {
                        "path": evidence_path.name,
                        "sha256": hash_file(evidence_path),
                    },
                }
            ]
            self.assertEqual(
                [], self.catalog.validate("capability_conformance_evidence", evidence)
            )
            self.assertEqual([], self.catalog.validate("capability_supply_report", report))
            self.assertEqual(
                [], validate_documents({evidence_path: evidence, report_path: report})
            )

            evidence_without_scope_ref = copy.deepcopy(evidence)
            evidence_without_scope_ref["scope"].pop("scope_ref")
            self.assertTrue(
                self.catalog.validate(
                    "capability_conformance_evidence", evidence_without_scope_ref
                )
            )
            report_without_scope_ref = copy.deepcopy(report)
            report_without_scope_ref["availability"]["scope"].pop("scope_ref")
            self.assertTrue(
                self.catalog.validate(
                    "capability_supply_report", report_without_scope_ref
                )
            )

            evidence["implementation_version"] = "2.0.0"
            evidence_path.write_text(
                json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            report["conformance_evidence"][0]["artifact_ref"]["sha256"] = hash_file(
                evidence_path
            )
            issues = validate_documents({evidence_path: evidence, report_path: report})
            self.assertIn(
                "CAPABILITY-SUPPLY-EVIDENCE-VERSION-MISMATCH",
                {issue.code for issue in issues},
            )

            evidence["implementation_version"] = "1.0.0"
            evidence["scope"]["scope_ref"] = "different-local-scope"
            evidence_path.write_text(
                json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            report["conformance_evidence"][0]["artifact_ref"]["sha256"] = hash_file(
                evidence_path
            )
            issues = validate_documents({evidence_path: evidence, report_path: report})
            self.assertIn(
                "CAPABILITY-SUPPLY-EVIDENCE-SCOPE-MISMATCH",
                {issue.code for issue in issues},
            )

            evidence["scope"]["scope_ref"] = "bounded-local-test"
            evidence["result"] = "fail"
            evidence_path.write_text(
                json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            report["conformance_evidence"][0]["artifact_ref"]["sha256"] = hash_file(
                evidence_path
            )
            failed_codes = {
                issue.code
                for issue in validate_documents({evidence_path: evidence, report_path: report})
            }
            self.assertIn("CAPABILITY-SUPPLY-EVIDENCE-RESULT-FAILED", failed_codes)

            evidence["result"] = "pass"
            evidence["evidence_id"] = "CONF-REWRITTEN-DOCUMENT-READER"
            evidence_path.write_text(
                json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            report["conformance_evidence"][0]["artifact_ref"]["sha256"] = hash_file(
                evidence_path
            )
            rewritten_codes = {
                issue.code
                for issue in validate_documents({evidence_path: evidence, report_path: report})
            }
            self.assertIn(
                "CAPABILITY-SUPPLY-EVIDENCE-IDENTITY-MISMATCH", rewritten_codes
            )

    def test_supply_resolution_snapshot_chain_is_closed_and_recomputed(self) -> None:
        self.assertEqual([], validate_documents(self.validation_documents))
        requirements = {
            document["requirement_id"]: CapabilityRequirement.from_mapping(document)
            for document in self.requirements.values()
        }
        reports = {
            parsed.reference: parsed
            for parsed in (
                CapabilitySupplyReport.from_mapping(document)
                for document in self.reports.values()
            )
        }
        for resolution in self.resolutions.values():
            assessments = [
                assess_supply(
                    requirements[resolution["requirement_ref"]["requirement_id"]],
                    reports[item["ref"]],
                    evaluated_at=resolution["evaluated_at"],
                    qualification=resolution["qualification"],
                    evidence_check=verified_fixture_evidence,
                )
                for item in resolution["candidate_supply_report_refs"]
            ]
            self.assertEqual(
                [assessment.to_mapping() for assessment in assessments],
                resolution["comparisons"],
            )
            self.assertEqual(
                (resolution["resolution_status"], resolution.get("selected_supply_report_ref")),
                resolve_status(assessments),
            )

    def test_replacement_keeps_method_requirement_and_ceilings_unchanged(self) -> None:
        resolution_a = self.resolutions[RESOLUTION_ROOT / "document-read-a.yaml"]
        resolution_b = self.resolutions[RESOLUTION_ROOT / "document-read-b.yaml"]
        snapshot_a = self.snapshots[SNAPSHOT_ROOT / "document-read-a.yaml"]
        snapshot_b = self.snapshots[SNAPSHOT_ROOT / "document-read-b.yaml"]
        self.assertEqual(resolution_a["method_resolution_ref"], resolution_b["method_resolution_ref"])
        self.assertEqual(resolution_a["requirement_ref"], resolution_b["requirement_ref"])
        self.assertEqual(snapshot_a["method_resolution_ref"], snapshot_b["method_resolution_ref"])
        self.assertEqual(snapshot_a["requirement_ref"], snapshot_b["requirement_ref"])
        self.assertNotEqual(snapshot_a["supply_identity"], snapshot_b["supply_identity"])
        for field in (
            "task_ref",
            "supply_required_permissions",
            "supply_data_egress",
            "supply_side_effects",
        ):
            self.assertEqual(snapshot_a[field], snapshot_b[field])
        method = load_document(METHOD_PATH)
        self.assertEqual("TASK-MR-ES-FROZEN-001", method["task_ref"]["task_id"])
        self.assertIn(
            "document-read",
            {
                value
                for decision in method["action_decisions"]
                for value in decision["capability_requirements"]
            },
        )

    def test_no_skill_path_is_first_class_and_creates_no_assignment(self) -> None:
        report = self.reports[REPORT_ROOT / "no-skill-contract-check.yaml"]
        snapshot = self.snapshots[SNAPSHOT_ROOT / "no-skill-contract-check.yaml"]
        self.assertEqual("procedure", report["supply_identity"]["supply_kind"])
        self.assertEqual("procedure", snapshot["supply_identity"]["supply_kind"])
        self.assertNotIn("skill_lifecycle_ref", report["supply_identity"])
        self.assertNotIn("runtime_eligibility_ref", report["supply_identity"])
        self.assertFalse(snapshot["boundaries"]["method_decision"])
        self.assertEqual("structural-replay", snapshot["qualification"])
        self.assertFalse(snapshot["boundaries"]["execution_input"])
        self.assertNotIn("execution_boundaries", snapshot)

        invalid_kind = copy.deepcopy(report)
        invalid_kind["supply_identity"]["supply_kind"] = "no-skill"
        self.assertTrue(self.catalog.validate("capability_supply_report", invalid_kind))

        invalid_lifecycle = copy.deepcopy(report)
        invalid_lifecycle["supply_identity"]["skill_lifecycle_ref"] = "fake@1.0.0"
        invalid_lifecycle["supply_identity"]["runtime_eligibility_ref"] = "ELIG-FAKE"
        self.assertTrue(
            self.catalog.validate("capability_supply_report", invalid_lifecycle)
        )

    def test_resolver_distinguishes_satisfied_gap_ambiguous_and_blocked(self) -> None:
        requirement = CapabilityRequirement.from_mapping(
            self.requirements[REQUIREMENT_ROOT / "document-read.yaml"]
        )
        report_a = CapabilitySupplyReport.from_mapping(
            self.reports[REPORT_ROOT / "local-document-reader-a.yaml"]
        )
        report_b = CapabilitySupplyReport.from_mapping(
            self.reports[REPORT_ROOT / "sandbox-document-reader-b.yaml"]
        )
        assessment_a = assess_supply(
            requirement,
            report_a,
            evaluated_at=EVALUATED_AT,
            evidence_check=verified_fixture_evidence,
        )
        assessment_b = assess_supply(
            requirement,
            report_b,
            evaluated_at=EVALUATED_AT,
            evidence_check=verified_fixture_evidence,
        )
        self.assertEqual(("gap", None), resolve_status([]))
        self.assertEqual(("satisfied", report_a.reference), resolve_status([assessment_a]))
        self.assertEqual(
            ("ambiguous", None), resolve_status([assessment_a, assessment_b])
        )

        excessive = copy.deepcopy(self.reports[REPORT_ROOT / "local-document-reader-a.yaml"])
        excessive["required_permissions"]["network"] = "search-and-fetch"
        blocked = assess_supply(
            requirement,
            CapabilitySupplyReport.from_mapping(excessive),
            evaluated_at=EVALUATED_AT,
            evidence_check=verified_fixture_evidence,
        )
        self.assertFalse(blocked.eligible)
        self.assertEqual(("blocked", None), resolve_status([blocked]))

    def test_skill_supply_stays_parked_until_lifecycle_runtime_eligibility(self) -> None:
        requirement = CapabilityRequirement.from_mapping(
            self.requirements[REQUIREMENT_ROOT / "document-read.yaml"]
        )
        skill = copy.deepcopy(self.reports[REPORT_ROOT / "local-document-reader-a.yaml"])
        skill["report_id"] = "supply-synthetic-skill"
        skill["supply_identity"] = {
            "supply_kind": "skill",
            "implementation_ref": "synthetic-skill",
            "implementation_version": "1.0.0",
            "content_hash": "sha256:" + "1" * 64,
            "components": [
                {
                    "component_kind": "skill",
                    "component_ref": "synthetic-skill",
                    "version": "1.0.0",
                    "content_hash": "sha256:" + "1" * 64,
                }
            ],
            "skill_lifecycle_ref": "synthetic-skill@1.0.0",
            "runtime_eligibility_ref": "ELIG-SYNTHETIC-SKILL",
        }
        parsed = CapabilitySupplyReport.from_mapping(skill)
        assessment = assess_supply(
            requirement,
            parsed,
            evaluated_at=EVALUATED_AT,
            evidence_check=lambda _identity, _evidence, _capability: "pass",
        )
        check = next(
            item for item in assessment.checks if item["check"] == "skill-runtime-eligibility"
        )
        self.assertEqual("not-applicable", check["status"])
        self.assertEqual(("satisfied", parsed.reference), resolve_status([assessment]))

        runtime_blocked = assess_supply(
            requirement,
            parsed,
            evaluated_at=EVALUATED_AT,
            qualification="runtime-execution",
            evidence_check=lambda _identity, _evidence, _capability: "pass",
        )
        runtime_skill_check = next(
            item
            for item in runtime_blocked.checks
            if item["check"] == "skill-runtime-eligibility"
        )
        self.assertEqual("unknown", runtime_skill_check["status"])
        self.assertEqual(("gap", None), resolve_status([runtime_blocked]))

        eligible = assess_supply(
            requirement,
            parsed,
            evaluated_at=EVALUATED_AT,
            qualification="runtime-execution",
            evidence_check=lambda _identity, _evidence, _capability: "pass",
            runtime_eligibility_check=lambda lifecycle_ref, eligibility_ref: (
                lifecycle_ref == "synthetic-skill@1.0.0"
                and eligibility_ref == "ELIG-SYNTHETIC-SKILL"
            ),
        )
        skill_check = next(
            item for item in eligible.checks if item["check"] == "skill-runtime-eligibility"
        )
        self.assertEqual("pass", skill_check["status"])
        # This synthetic fixture still cannot satisfy the independent Runtime
        # availability qualification even when lifecycle provenance is verified.
        self.assertEqual(("gap", None), resolve_status([eligible]))

        documents = copy.deepcopy(self.validation_documents)
        documents[REPORT_ROOT / "synthetic-skill.yaml"] = skill
        self.assertEqual([], self.catalog.validate("capability_supply_report", skill))
        self.assertNotIn(
            "CAPABILITY-SKILL-SUPPLY-NOT-ELIGIBLE",
            {issue.code for issue in validate_documents(documents)},
        )

    def test_report_schema_rejects_self_selection_routing_and_authority(self) -> None:
        source = next(iter(self.reports.values()))
        for key in (
            "selected",
            "selected_supply_report_ref",
            "fallback_order",
            "routing",
            "method_decision",
            "permission_grant",
            "claim_effects",
        ):
            with self.subTest(key=key):
                document = copy.deepcopy(source)
                document[key] = True
                self.assertTrue(self.catalog.validate("capability_supply_report", document))

    def test_resolution_hash_comparison_and_status_drift_are_blocking(self) -> None:
        source_path = RESOLUTION_ROOT / "document-read-a.yaml"
        mutations = (
            (
                lambda resolution: resolution["candidate_supply_report_refs"][0].__setitem__(
                    "content_hash", "sha256:" + "0" * 64
                ),
                "CAPABILITY-RESOLUTION-SUPPLY-HASH-MISMATCH",
            ),
            (
                lambda resolution: resolution["comparisons"][0]["checks"][0].__setitem__(
                    "status", "fail"
                ),
                "CAPABILITY-RESOLUTION-COMPARISON-DRIFT",
            ),
            (
                lambda resolution: resolution.__setitem__(
                    "selected_supply_report_ref", "supply-wrong@1.0.0"
                ),
                "CAPABILITY-RESOLUTION-SELECTION-DRIFT",
            ),
        )
        for mutate, expected in mutations:
            with self.subTest(expected=expected):
                documents = copy.deepcopy(self.validation_documents)
                mutate(documents[source_path])
                self.assertIn(expected, {issue.code for issue in validate_documents(documents)})

    def test_snapshot_lineage_supply_facts_and_evidence_drift_are_blocking(self) -> None:
        source_path = SNAPSHOT_ROOT / "document-read-a.yaml"
        mutations = (
            (
                lambda snapshot: snapshot["method_resolution_ref"].__setitem__(
                    "ref", "MR-WRONG@r1"
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-LINEAGE-DRIFT",
            ),
            (
                lambda snapshot: snapshot["supply_required_permissions"].__setitem__(
                    "filesystem", "read-only"
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-SUPPLY-FACT-DRIFT",
            ),
            (
                lambda snapshot: snapshot["conformance_evidence_refs"][0].__setitem__(
                    "sha256", "0" * 64
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-EVIDENCE-DRIFT",
            ),
        )
        for mutate, expected in mutations:
            with self.subTest(expected=expected):
                documents = copy.deepcopy(self.validation_documents)
                mutate(documents[source_path])
                self.assertIn(expected, {issue.code for issue in validate_documents(documents)})

    def test_failed_evidence_is_closed_but_structural_replay_ignores_wall_clock(self) -> None:
        evidence_path = CONFORMANCE_ROOT / "local-document-reader-a.json"
        report_path = REPORT_ROOT / "local-document-reader-a.yaml"
        resolution_path = RESOLUTION_ROOT / "document-read-a.yaml"

        failed = copy.deepcopy(self.validation_documents)
        failed[evidence_path]["result"] = "fail"
        failed_codes = {issue.code for issue in validate_documents(failed)}
        self.assertIn("CAPABILITY-RESOLUTION-COMPARISON-DRIFT", failed_codes)

        stale = copy.deepcopy(self.validation_documents)
        stale[report_path]["availability"]["valid_until"] = "2026-08-24T00:00:00Z"
        stale_codes = {issue.code for issue in validate_documents(stale)}
        self.assertNotIn("CAPABILITY-RESOLUTION-COMPARISON-DRIFT", stale_codes)
        self.assertEqual("structural-replay", stale[resolution_path]["qualification"])

    def test_structural_fixture_cannot_be_relabelled_as_runtime_execution(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        snapshot = documents[SNAPSHOT_ROOT / "document-read-a.yaml"]
        resolution = documents[RESOLUTION_ROOT / "document-read-a.yaml"]
        resolution["qualification"] = "runtime-execution"
        snapshot["qualification"] = "runtime-execution"
        snapshot["boundaries"]["execution_input"] = True
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("RESOLVED-CAPABILITY-SNAPSHOT-RUNTIME-EVIDENCE-INELIGIBLE", codes)

    def test_structural_snapshot_rejects_runtime_authority_and_boundary_injection(self) -> None:
        source = self.snapshots[SNAPSHOT_ROOT / "document-read-a.yaml"]
        for field, value in (
            (
                "permission_basis",
                {"kind": "structural-only", "task_permission_ceiling": {}},
            ),
            (
                "execution_boundaries",
                {
                    "effective_permissions": {
                        "filesystem": "workspace-write",
                        "network": "allowed",
                        "external_write": True,
                    },
                    "data_egress": {"policy": "forbidden", "allowed_payloads": [], "forbidden_payloads": ["x"]},
                    "side_effects": {"policy": "none", "allowed_effects": []},
                },
            ),
            (
                "authority_eligibility_ref",
                {
                    "ref": "FORGED@1.0.0",
                    "document_path": "examples/forged.yaml",
                    "content_hash": "sha256:" + "0" * 64,
                },
            ),
        ):
            with self.subTest(field=field):
                snapshot = copy.deepcopy(source)
                snapshot[field] = value
                self.assertTrue(self.catalog.validate("resolved_capability_snapshot", snapshot))

    def test_report_rejects_routing_credentials_and_self_reported_evidence_status(self) -> None:
        source = self.reports[REPORT_ROOT / "local-document-reader-a.yaml"]
        for key in ("fallback", "routing", "api_key", "credential", "price"):
            with self.subTest(key=key):
                report = copy.deepcopy(source)
                report[key] = "forbidden"
                self.assertTrue(self.catalog.validate("capability_supply_report", report))
        report = copy.deepcopy(source)
        report["conformance_evidence"][0]["status"] = "pass"
        self.assertTrue(self.catalog.validate("capability_supply_report", report))

    def test_low_level_provider_conformance_does_not_prove_document_read(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        report_path = REPORT_ROOT / "local-document-reader-a.yaml"
        report = documents[report_path]
        report["observation_scope"] = "live-observation"
        report["supply_identity"]["supply_kind"] = "adapter-provider"
        report["supply_identity"]["components"] = [
            {
                "component_kind": "adapter",
                "component_ref": "openai-synthetic",
                "version": "0.1.0",
                "content_hash": "sha256:" + "2" * 64,
            },
            {
                "component_kind": "provider",
                "component_ref": "openai",
                "version": "1.0.0",
                "content_hash": "sha256:" + "3" * 64,
            },
        ]
        evidence_path = ROOT / "examples/capability-resolution/conformance/provider-low-level.json"
        report["conformance_evidence"] = [
            {
                "evidence_id": "PCR-LOW-LEVEL",
                "evidence_class": "live",
                "artifact_kind": "provider-conformance-report",
                "artifact_ref": {
                    "path": "examples/capability-resolution/conformance/provider-low-level.json",
                    "sha256": "1" * 64,
                },
            }
        ]
        report["availability"] = {
            "status": "available",
            "scope": {
                "scope_kind": "provider-observation",
                "scope_ref": "PCR-LOW-LEVEL",
            },
            "observed_at": "2026-08-24T00:00:01Z",
            "facts": ["Bounded adapter probe only."],
        }
        documents[evidence_path] = {
            "schema_version": "0.1.0",
            "report_id": "PCR-LOW-LEVEL",
            "adapter_id": "openai-synthetic",
            "provider": "openai",
            "adapter_version": "0.1.0",
            "execution_context": "offline-test",
            "requested_model": "synthetic-model",
            "observed_models": ["synthetic-model-version"],
            "started_at": "2026-08-24T00:00:00Z",
            "finished_at": "2026-08-24T00:00:01Z",
            "status": "passed",
            "checks": [
                {
                    "check": "text",
                    "status": "passed",
                    "finish_reason": "complete",
                    "output_kinds": ["text"],
                    "tool_call_count": 0,
                    "warnings_count": 0,
                }
            ],
            "budget": {
                "max_provider_invocations": 1,
                "max_output_tokens_per_invocation": 64,
                "provider_invocations": 1,
                "successful_responses": 1,
                "elapsed_seconds": 1,
            },
            "privacy": {
                "fixed_synthetic_prompts_only": True,
                "credential_values_stored": False,
                "request_content_stored": False,
                "response_content_stored": False,
                "provider_response_ids_stored": False,
                "tool_arguments_stored": False,
            },
            "limitations": ["Low-level adapter behavior only."],
        }
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("CAPABILITY-RESOLUTION-COMPARISON-DRIFT", codes)
        self.assertNotIn("SCHEMA-INVALID", codes)
        self.assertNotIn("CAPABILITY-SUPPLY-EVIDENCE-IMPLEMENTATION-MISMATCH", codes)

        provider_mismatch = copy.deepcopy(documents)
        provider_mismatch[report_path]["supply_identity"]["components"][1][
            "component_ref"
        ] = "anthropic"
        provider_mismatch_codes = {
            issue.code for issue in validate_documents(provider_mismatch)
        }
        self.assertIn(
            "CAPABILITY-SUPPLY-EVIDENCE-IMPLEMENTATION-MISMATCH",
            provider_mismatch_codes,
        )

        failed = copy.deepcopy(documents)
        failed[evidence_path]["status"] = "failed"
        failed[evidence_path]["checks"][0]["status"] = "failed"
        failed[evidence_path]["checks"][0]["error_category"] = "unknown"
        failed_codes = {issue.code for issue in validate_documents(failed)}
        self.assertIn("CAPABILITY-SUPPLY-EVIDENCE-RESULT-FAILED", failed_codes)

    def test_supply_registry_adversarial_contract_and_evidence_matrix(self) -> None:
        report_path = REPORT_ROOT / "local-document-reader-a.yaml"
        evidence_path = CONFORMANCE_ROOT / "local-document-reader-a.json"
        cases = (
            (
                lambda documents: documents[report_path]["supply_identity"].__setitem__(
                    "components", "not-a-list"
                ),
                "CAPABILITY-SUPPLY-CONTRACT",
            ),
            (
                lambda documents: documents.__setitem__(
                    REPORT_ROOT / "duplicate.yaml", copy.deepcopy(documents[report_path])
                ),
                "CAPABILITY-SUPPLY-IDENTITY-DUPLICATE",
            ),
            (
                lambda documents: documents[report_path]["supply_identity"].__setitem__(
                    "supply_kind", "adapter-provider"
                ),
                "CAPABILITY-SUPPLY-COMPONENT-INCOMPLETE",
            ),
            (
                lambda documents: documents[report_path]["supply_identity"]["components"].append(
                    copy.deepcopy(documents[report_path]["supply_identity"]["components"][0])
                ),
                "CAPABILITY-SUPPLY-COMPONENT-DUPLICATE",
            ),
            (
                lambda documents: documents[report_path]["availability"]["scope"].__setitem__(
                    "scope_kind", "provider-observation"
                ),
                "CAPABILITY-SUPPLY-OBSERVATION-SCOPE-MISMATCH",
            ),
            (
                lambda documents: documents[report_path]["availability"].__setitem__(
                    "observed_at", "not-a-date"
                ),
                "CAPABILITY-SUPPLY-AVAILABILITY-TIME-INVALID",
            ),
            (
                lambda documents: documents[report_path]["conformance_evidence"].append(
                    copy.deepcopy(documents[report_path]["conformance_evidence"][0])
                ),
                "CAPABILITY-SUPPLY-EVIDENCE-DUPLICATE",
            ),
            (
                lambda documents: documents[report_path]["conformance_evidence"][0][
                    "artifact_ref"
                ].__setitem__("path", "examples/capability-resolution/conformance/missing.json"),
                "CAPABILITY-SUPPLY-EVIDENCE-MISSING",
            ),
            (
                lambda documents: documents[evidence_path]["capability_ids"].append(
                    "undeclared-capability"
                ),
                "CAPABILITY-SUPPLY-EVIDENCE-CAPABILITY-DRIFT",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                documents = copy.deepcopy(self.validation_documents)
                mutate(documents)
                codes = {
                    issue.code for issue in validate_capability_supply_chain(documents)
                }
                self.assertIn(expected, codes)

    def test_resolution_and_snapshot_registry_adversarial_matrix(self) -> None:
        resolution_path = RESOLUTION_ROOT / "document-read-a.yaml"
        snapshot_path = SNAPSHOT_ROOT / "document-read-a.yaml"
        method_path = METHOD_PATH
        cases = (
            (
                lambda documents: documents.__setitem__(
                    RESOLUTION_ROOT / "duplicate.yaml",
                    copy.deepcopy(documents[resolution_path]),
                ),
                "CAPABILITY-RESOLUTION-IDENTITY-DUPLICATE",
            ),
            (
                lambda documents: documents[resolution_path]["method_resolution_ref"].__setitem__(
                    "ref", "MR-WRONG@r1"
                ),
                "CAPABILITY-RESOLUTION-METHOD-IDENTITY-MISMATCH",
            ),
            (
                lambda documents: documents[resolution_path]["requirement_ref"].__setitem__(
                    "requirement_id", "wrong-requirement"
                ),
                "CAPABILITY-RESOLUTION-REQUIREMENT-IDENTITY-MISMATCH",
            ),
            (
                lambda documents: documents[REQUIREMENT_ROOT / "document-read.yaml"].__setitem__(
                    "constraints", "not-an-object"
                ),
                "CAPABILITY-REQUIREMENT-CONTRACT",
            ),
            (
                lambda documents: documents[method_path]["action_decisions"][0].__setitem__(
                    "capability_requirements", []
                ),
                "CAPABILITY-RESOLUTION-METHOD-REQUIREMENT-MISSING",
            ),
            (
                lambda documents: documents[resolution_path]["candidate_supply_report_refs"][0].__setitem__(
                    "ref", "supply-unknown@1.0.0"
                ),
                "CAPABILITY-RESOLUTION-SUPPLY-IDENTITY-MISSING",
            ),
            (
                lambda documents: documents[resolution_path]["candidate_supply_report_refs"].append(
                    copy.deepcopy(documents[resolution_path]["candidate_supply_report_refs"][0])
                ),
                "CAPABILITY-RESOLUTION-SUPPLY-DUPLICATE",
            ),
            (
                lambda documents: documents.__setitem__(
                    SNAPSHOT_ROOT / "duplicate.yaml", copy.deepcopy(documents[snapshot_path])
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-IDENTITY-DUPLICATE",
            ),
            (
                lambda documents: documents[snapshot_path]["resolution_ref"].__setitem__(
                    "document_path", "examples/capability-resolution/resolutions/missing.yaml"
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-RESOLUTION-MISSING",
            ),
            (
                lambda documents: documents[snapshot_path]["resolution_ref"].__setitem__(
                    "ref", "CR-WRONG@r1"
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-RESOLUTION-IDENTITY-MISMATCH",
            ),
            (
                lambda documents: documents[resolution_path].__setitem__(
                    "resolution_status", "blocked"
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-UNSATISFIED",
            ),
            (
                lambda documents: documents[snapshot_path].__setitem__(
                    "qualification", "runtime-execution"
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-QUALIFICATION-DRIFT",
            ),
            (
                lambda documents: documents[snapshot_path]["task_ref"].__setitem__(
                    "ref", "TASK-WRONG@r1"
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-TASK-IDENTITY-MISMATCH",
            ),
            (
                lambda documents: documents[snapshot_path]["selected_supply_report_ref"].__setitem__(
                    "document_path", "examples/capability-resolution/supply-reports/missing.yaml"
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-SUPPLY-MISSING",
            ),
            (
                lambda documents: documents[snapshot_path]["boundaries"].__setitem__(
                    "execution_input", True
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-STRUCTURAL-EXECUTION-FORBIDDEN",
            ),
            (
                lambda documents: (
                    documents[resolution_path].__setitem__("qualification", "unknown"),
                    documents[resolution_path].__setitem__(
                        "candidate_supply_report_refs", [None]
                    ),
                    documents[snapshot_path].__setitem__("qualification", "unknown"),
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-QUALIFICATION-UNKNOWN",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                documents = copy.deepcopy(self.validation_documents)
                mutate(documents)
                codes = {
                    issue.code for issue in validate_capability_supply_chain(documents)
                }
                self.assertIn(expected, codes)

    def test_supply_reference_evidence_and_cross_object_guard_matrix(self) -> None:
        report_path = REPORT_ROOT / "local-document-reader-a.yaml"
        report_b_path = REPORT_ROOT / "sandbox-document-reader-b.yaml"
        evidence_path = CONFORMANCE_ROOT / "local-document-reader-a.json"
        resolution_path = RESOLUTION_ROOT / "document-read-a.yaml"
        resolution_b_path = RESOLUTION_ROOT / "document-read-b.yaml"
        snapshot_path = SNAPSHOT_ROOT / "document-read-a.yaml"
        cases = (
            (
                lambda documents: documents[resolution_path].__setitem__(
                    "method_resolution_ref", "not-an-object"
                ),
                "CAPABILITY-RESOLUTION-METHOD-MISSING",
            ),
            (
                lambda documents: documents[resolution_path]["requirement_ref"].__setitem__(
                    "document_path", None
                ),
                "CAPABILITY-RESOLUTION-REQUIREMENT-MISSING",
            ),
            (
                lambda documents: documents[report_path]["conformance_evidence"][0].__setitem__(
                    "artifact_ref", "not-an-object"
                ),
                "CAPABILITY-RESOLUTION-COMPARISON-DRIFT",
            ),
            (
                lambda documents: documents[report_path]["conformance_evidence"][0][
                    "artifact_ref"
                ].__setitem__("path", None),
                "CAPABILITY-RESOLUTION-COMPARISON-DRIFT",
            ),
            (
                lambda documents: (
                    documents[report_path]["conformance_evidence"][0].__setitem__(
                        "artifact_kind", "capability-conformance-evidence"
                    ),
                    documents[report_path]["conformance_evidence"][0]["artifact_ref"].__setitem__(
                        "path", "examples/method-resolutions/ROUTE-ES-FROZEN-001.yaml"
                    ),
                    documents[report_path]["conformance_evidence"][0]["artifact_ref"].__setitem__(
                        "sha256", hash_file(METHOD_PATH)
                    ),
                ),
                "CAPABILITY-SUPPLY-EVIDENCE-KIND-MISMATCH",
            ),
            (
                lambda documents: documents[evidence_path].__setitem__(
                    "capability_ids", ["undeclared-capability"]
                ),
                "CAPABILITY-SUPPLY-EVIDENCE-CAPABILITY-DRIFT",
            ),
            (
                lambda documents: documents[report_path]["conformance_evidence"][0].__setitem__(
                    "evidence_class", "live"
                ),
                "CAPABILITY-SUPPLY-EVIDENCE-CLASS-MISMATCH",
            ),
            (
                lambda documents: documents[resolution_path]["candidate_supply_report_refs"][0].__setitem__(
                    "document_path", str(report_b_path.relative_to(ROOT)).replace("\\", "/")
                ),
                "CAPABILITY-RESOLUTION-SUPPLY-PATH-MISMATCH",
            ),
            (
                lambda documents: documents[METHOD_PATH]["task_ref"].__setitem__(
                    "task_id", "TASK-WRONG"
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-TASK-METHOD-LINEAGE-DRIFT",
            ),
            (
                lambda documents: documents[snapshot_path]["selected_supply_report_ref"].__setitem__(
                    "document_path", str(report_b_path.relative_to(ROOT)).replace("\\", "/")
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-SUPPLY-PATH-MISMATCH",
            ),
            (
                lambda documents: (
                    documents.__setitem__(
                        resolution_b_path, copy.deepcopy(documents[resolution_path])
                    ),
                    documents[snapshot_path]["resolution_ref"].__setitem__(
                        "document_path",
                        str(resolution_b_path.relative_to(ROOT)).replace("\\", "/"),
                    ),
                ),
                "RESOLVED-CAPABILITY-SNAPSHOT-RESOLUTION-PATH-MISMATCH",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                documents = copy.deepcopy(self.validation_documents)
                mutate(documents)
                codes = {
                    issue.code for issue in validate_capability_supply_chain(documents)
                }
                self.assertIn(expected, codes)

        hash_bound = LoadedDocuments()
        for path, document in copy.deepcopy(self.validation_documents).items():
            hash_bound.add(path, document, sha256=hash_file(path))
        hash_bound[report_path]["conformance_evidence"][0]["artifact_ref"]["sha256"] = (
            "0" * 64
        )
        codes = {issue.code for issue in validate_capability_supply_chain(hash_bound)}
        self.assertIn("CAPABILITY-SUPPLY-EVIDENCE-HASH-MISMATCH", codes)


if __name__ == "__main__":
    unittest.main()
