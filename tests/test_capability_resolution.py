import copy
import json
import unittest
from pathlib import Path

from research_workbench.capability import (
    CapabilityRequirement,
    CapabilitySupplyReport,
    assess_supply,
    resolve_status,
)
from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog, validate_documents


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
                assess_supply(requirements[resolution["requirement_ref"]["requirement_id"]], reports[item["ref"]])
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
        for field in ("effective_permissions", "data_egress", "side_effects"):
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
        self.assertEqual("no-skill", report["supply_identity"]["supply_kind"])
        self.assertEqual("no-skill", snapshot["supply_identity"]["supply_kind"])
        self.assertNotIn("skill_lifecycle_ref", report["supply_identity"])
        self.assertNotIn("runtime_eligibility_ref", report["supply_identity"])
        self.assertFalse(snapshot["boundaries"]["method_decision"])

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
        assessment_a = assess_supply(requirement, report_a)
        assessment_b = assess_supply(requirement, report_b)
        self.assertEqual(("unsatisfied-gap", None), resolve_status([]))
        self.assertEqual(("satisfied", report_a.reference), resolve_status([assessment_a]))
        self.assertEqual(
            ("requires-decision", None), resolve_status([assessment_a, assessment_b])
        )

        excessive = copy.deepcopy(self.reports[REPORT_ROOT / "local-document-reader-a.yaml"])
        excessive["required_permissions"]["network"] = "approved-external-read"
        blocked = assess_supply(requirement, CapabilitySupplyReport.from_mapping(excessive))
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
        assessment = assess_supply(requirement, parsed)
        check = next(
            item for item in assessment.checks if item["check"] == "skill-runtime-eligibility"
        )
        self.assertEqual("unknown", check["status"])
        self.assertEqual(("unsatisfied-gap", None), resolve_status([assessment]))

        documents = copy.deepcopy(self.validation_documents)
        documents[REPORT_ROOT / "synthetic-skill.yaml"] = skill
        self.assertIn(
            "CAPABILITY-SKILL-SUPPLY-EXTENSION-PARKED",
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

    def test_resolution_hash_comparison_status_and_authority_drift_are_blocking(self) -> None:
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
            (
                lambda resolution: resolution["authority_basis"]["matrix_ref"].__setitem__(
                    "content_hash", "sha256:" + "0" * 64
                ),
                "CAPABILITY-RESOLUTION-AUTHORITY-MATRIX-HASH-MISMATCH",
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
                lambda snapshot: snapshot["effective_permissions"].__setitem__(
                    "filesystem", "forbidden"
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


if __name__ == "__main__":
    unittest.main()
