from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from research_workbench.artifacts.integrity import (
    ReferenceStatus,
    check_file_reference,
    hash_bytes,
    hash_directory,
)
from research_workbench.capability import (
    AgentProfile,
    CapabilityRequirement,
    CapabilityRequirementSet,
    CapabilitySupplyReport,
    SkillManifest,
    assess_supply,
    resolve_task,
)
from research_workbench.capability import requirements as requirement_module
from research_workbench.capability import supply as supply_module
from research_workbench.contracts.common import ContractError
from research_workbench.io import load_document
from research_workbench.protocol import (
    DecisionAuthorityMatrix,
    evaluate_authority_rule_eligibility,
)
from research_workbench.tasks import FileReference, HandoffPacket, TaskPacket
from research_workbench.validation import (
    check_claim_ceiling,
    check_handoff_against_task,
    check_references,
    check_write_scope_overlap,
)


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "registry/authority/decision-authority-matrix.yaml"
ELIGIBILITY_PATH = ROOT / "examples/decision-authority/eligible-resolver-action-commit.yaml"
REQUIREMENT_PATH = ROOT / "registry/capabilities/requirements/document-read.yaml"
SUPPLY_PATH = ROOT / "examples/capability-resolution/supply-reports/local-document-reader-a.yaml"


class CriticalIntegrityBranchTests(unittest.TestCase):
    def test_reference_statuses_and_hash_guards_are_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "input.txt"
            target.write_bytes(b"stable")
            valid = FileReference("input.txt", hash_bytes(b"stable"))
            self.assertTrue(check_file_reference(root, valid).valid)
            self.assertEqual(
                ReferenceStatus.HASH_MISMATCH,
                check_file_reference(root, FileReference("input.txt", "0" * 64)).status,
            )
            self.assertEqual(
                ReferenceStatus.MISSING,
                check_file_reference(root, FileReference("missing.txt", "0" * 64)).status,
            )
            self.assertEqual(
                ReferenceStatus.OUTSIDE_ROOT,
                check_file_reference(root, FileReference("../outside.txt", "0" * 64)).status,
            )
            with self.assertRaises(FileNotFoundError):
                hash_directory(root / "not-a-directory")

    def test_directory_hash_refuses_symlinked_package_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.txt"
            link = root / "linked.txt"
            source.write_text("payload", encoding="utf-8")
            try:
                link.symlink_to(source)
            except OSError as exc:  # pragma: no cover - Windows privilege fallback
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaisesRegex(ValueError, "symlinked package file"):
                hash_directory(root)


class CriticalAuthorityBranchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = load_document(MATRIX_PATH)
        cls.eligibility = load_document(ELIGIBILITY_PATH)
        cls.matrix_hash = hashlib.sha256(MATRIX_PATH.read_bytes()).hexdigest()

    def _reject(self, mutate) -> None:
        document = copy.deepcopy(self.matrix)
        mutate(document)
        with self.assertRaises(ContractError):
            DecisionAuthorityMatrix.from_mapping(document)

    def test_matrix_parser_rejects_every_frozen_boundary_drift(self) -> None:
        cases = {
            "rule-human-gate-type": lambda doc: doc["entries"][0]["rules"][0].update(
                human_gate_required="false"
            ),
            "empty-rules": lambda doc: doc["entries"][0].update(rules=[]),
            "duplicate-rule": lambda doc: doc["entries"][0]["rules"].append(
                copy.deepcopy(doc["entries"][0]["rules"][0])
            ),
            "schema-version": lambda doc: doc.update(schema_version="9.9.9"),
            "matrix-identity": lambda doc: doc.update(matrix_id="other-matrix"),
            "authority-classes": lambda doc: doc.update(authority_classes=["agent"]),
            "duplicate-entry": lambda doc: doc["entries"].append(
                copy.deepcopy(doc["entries"][0])
            ),
            "missing-kind": lambda doc: doc["entries"].pop(),
            "missing-proposal": lambda doc: doc["entries"][0].update(
                rules=[
                    rule
                    for rule in doc["entries"][0]["rules"]
                    if not (rule["operation"] == "propose" and rule["actor_class"] == "agent")
                ]
            ),
            "effect-drift": lambda doc: doc["entries"][0]["rules"][0].update(effect="binding-decision"),
            "agent-operation": lambda doc: doc["entries"][0]["rules"][0].update(
                operation="validate", effect="structural-validation"
            ),
            "resolver-operation": lambda doc: next(
                rule
                for rule in doc["entries"][0]["rules"]
                if rule["actor_class"] == "deterministic-resolver"
            ).update(operation="propose", effect="non-binding-proposal"),
            "gate-flag": lambda doc: doc["entries"][0]["rules"][0].update(
                human_gate_required=True
            ),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                self._reject(mutate)

    def test_eligibility_exact_matrix_identity_path_and_kind_are_closed(self) -> None:
        cases = {
            "ref": (lambda doc: doc["matrix_ref"].update(ref="other@1.0.0"), "AUTHORITY-MATRIX-REF-MISMATCH"),
            "path": (lambda doc: doc["matrix_ref"].update(document_path="other.yaml"), "AUTHORITY-MATRIX-PATH-MISMATCH"),
            "kind": (lambda doc: doc.update(decision_kind="unknown-kind"), "AUTHORITY-DECISION-KIND-UNKNOWN"),
        }
        for name, (mutate, code) in cases.items():
            with self.subTest(case=name):
                eligibility = copy.deepcopy(self.eligibility)
                mutate(eligibility)
                result = evaluate_authority_rule_eligibility(
                    eligibility, self.matrix, matrix_content_hash=self.matrix_hash
                )
                self.assertEqual(code, result["code"])


class FakeCatalog:
    def __init__(self, errors_for: str | None = None) -> None:
        self.errors_for = errors_for

    def validate(self, kind: str, document: object) -> list[SimpleNamespace]:
        if kind == self.errors_for:
            return [SimpleNamespace(pointer="/", message="synthetic schema failure")]
        return []


class CriticalCapabilityBranchTests(unittest.TestCase):
    def _load_index(
        self,
        root: Path,
        index: object,
        *,
        document: object | None = None,
        errors_for: str | None = None,
        absolute: bool = False,
    ) -> CapabilityRequirementSet:
        index_path = root / "index.yaml"
        document_path = root / "requirement.yaml"
        document_path.write_bytes(b"requirement")
        path = index_path if absolute else Path("index.yaml")
        with (
            mock.patch.object(requirement_module, "load_document", return_value=index),
            mock.patch.object(
                requirement_module,
                "load_document_bytes",
                return_value=(load_document(REQUIREMENT_PATH) if document is None else document),
            ),
            mock.patch(
                "research_workbench.validation.schemas.SchemaCatalog",
                return_value=FakeCatalog(errors_for),
            ),
        ):
            return CapabilityRequirementSet.load(path, project_root=root)

    def _entry(self, *, digest: str | None = None) -> dict[str, str]:
        return {
            "requirement_id": "document-read",
            "document_path": "requirement.yaml",
            "content_hash": digest or hash_bytes(b"requirement"),
        }

    def test_requirement_loader_remains_closed_if_schema_layer_misses_bad_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = {"registry_kind": "capability_requirement_index", "entries": [self._entry()]}
            self.assertEqual(
                "document-read",
                self._load_index(root, copy.deepcopy(base), absolute=True).entries[0].requirement_id,
            )
            cases = [
                ({"registry_kind": "wrong", "entries": []}, None, None, "not a Capability"),
                (copy.deepcopy(base), None, "capability_requirement_index", "index schema invalid"),
                ({"registry_kind": "capability_requirement_index", "entries": None}, None, None, "no entries list"),
                ({"registry_kind": "capability_requirement_index", "entries": ["bad"]}, None, None, "not an object"),
                ({"registry_kind": "capability_requirement_index", "entries": [self._entry(), self._entry()]}, None, None, "duplicate Capability Requirement identity"),
                ({"registry_kind": "capability_requirement_index", "entries": [self._entry(), {**self._entry(), "requirement_id": "other"}]}, None, None, "duplicate Capability Requirement path"),
                ({"registry_kind": "capability_requirement_index", "entries": [{**self._entry(), "document_path": "missing.yaml"}]}, None, None, "missing or escapes root"),
                ({"registry_kind": "capability_requirement_index", "entries": [self._entry(digest="0" * 64)]}, None, None, "content drift"),
                (copy.deepcopy(base), [], None, "not an object"),
                (copy.deepcopy(base), load_document(REQUIREMENT_PATH), "capability_requirement", "schema invalid"),
                (copy.deepcopy(base), {**load_document(REQUIREMENT_PATH), "requirement_id": "other"}, None, "identity mismatch"),
            ]
            for index, document, errors_for, message in cases:
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError, message):
                        self._load_index(
                            root,
                            index,
                            document=document,
                            errors_for=errors_for,
                        )

    def test_requirement_selection_and_boolean_ceiling_fail_closed(self) -> None:
        requirement = load_document(REQUIREMENT_PATH)
        requirement["constraints"]["permission_ceiling"]["external_write"] = "false"
        with self.assertRaises(ContractError):
            CapabilityRequirement.from_mapping(requirement)
        requirement_set = CapabilityRequirementSet.load(project_root=ROOT)
        with self.assertRaisesRegex(ValueError, "selected more than once"):
            requirement_set.require(["document-read", "document-read"])
        with self.assertRaisesRegex(ValueError, "not indexed"):
            requirement_set.require(["unknown-capability"])

    def test_supply_identity_and_qualification_fail_closed(self) -> None:
        raw = load_document(SUPPLY_PATH)
        identity = raw["supply_identity"]
        cases = [
            (lambda value: value.update(components="bad"), ContractError),
            (lambda value: value.update(components=["bad"]), ContractError),
            (lambda value: value.update(skill_lifecycle_ref=1), ContractError),
            (lambda value: value.update(runtime_eligibility_ref=1), ContractError),
            (lambda value: value.update(supply_kind="unknown"), ContractError),
            (lambda value: value.update(supply_kind="skill"), ContractError),
            (lambda value: value.update(skill_lifecycle_ref="LIFE@1"), ContractError),
        ]
        for mutate, error in cases:
            with self.subTest(mutate=mutate):
                changed = copy.deepcopy(identity)
                changed.pop("skill_lifecycle_ref", None)
                changed.pop("runtime_eligibility_ref", None)
                mutate(changed)
                with self.assertRaises(error):
                    supply_module.SupplyIdentity.from_mapping(changed)
        non_skill = copy.deepcopy(identity)
        non_skill["skill_lifecycle_ref"] = "LIFE@1"
        non_skill["runtime_eligibility_ref"] = "ELIG@1"
        with self.assertRaises(ContractError):
            supply_module.SupplyIdentity.from_mapping(non_skill)

        requirement = CapabilityRequirement.from_mapping(load_document(REQUIREMENT_PATH))
        report = CapabilitySupplyReport.from_mapping(raw)
        with self.assertRaisesRegex(ValueError, "unknown capability qualification"):
            assess_supply(requirement, report, qualification="unknown")
        unavailable = replace(report, availability={"status": "unavailable", "scope": {"scope_kind": "local"}})
        unknown = replace(report, availability={"status": "unknown", "scope": {"scope_kind": "local"}})
        self.assertFalse(assess_supply(requirement, unavailable).eligible)
        self.assertFalse(assess_supply(requirement, unknown, qualification="runtime-execution").eligible)

    def test_supply_ceiling_and_availability_branch_matrix_is_explicit(self) -> None:
        requirement_raw = load_document(REQUIREMENT_PATH)
        requirement_raw["constraints"]["data_egress"] = {
            "policy": "allowlisted-only",
            "allowed_payloads": ["abstract"],
            "forbidden_payloads": ["private-full-text"],
        }
        requirement_raw["constraints"]["side_effects"] = {
            "policy": "none",
            "allowed_effects": [],
        }
        requirement = CapabilityRequirement.from_mapping(requirement_raw)
        report_raw = load_document(SUPPLY_PATH)
        report_raw["observation_scope"] = "deterministic-local"
        report_raw["data_egress_behavior"] = {
            "policy": "allowlisted-only",
            "allowed_payloads": ["abstract"],
            "forbidden_payloads": [],
        }
        report_raw["side_effects"] = {"policy": "none", "allowed_effects": []}
        report_raw["availability"] = {
            "status": "available",
            "scope": {"scope_kind": "local-environment"},
        }
        report = CapabilitySupplyReport.from_mapping(report_raw)
        structural = assess_supply(requirement, report)
        runtime = assess_supply(requirement, report, qualification="runtime-execution")
        self.assertEqual("pass", structural.checks[8]["status"])
        self.assertEqual("pass", runtime.checks[8]["status"])

        exceeded = copy.deepcopy(report_raw)
        exceeded["data_egress_behavior"]["allowed_payloads"] = ["full-text"]
        assessment = assess_supply(
            requirement, CapabilitySupplyReport.from_mapping(exceeded)
        )
        self.assertEqual("fail", assessment.checks[5]["status"])
        unavailable = replace(
            report,
            availability={"status": "unavailable", "scope": {"scope_kind": "local"}},
        )
        self.assertEqual("fail", assess_supply(requirement, unavailable).checks[8]["status"])


class CriticalRelationshipBranchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        cls.handoff = HandoffPacket.from_mapping(load_document(ROOT / "examples/handoff-evidence.yaml"))
        cls.profile = AgentProfile.from_mapping(load_document(ROOT / "examples/profiles/evidence-scout.yaml"))
        cls.skill = SkillManifest.from_mapping(
            load_document(ROOT / "examples/skills/literature-evidence-extraction.yaml")
        )

    def test_handoff_status_assignment_and_file_boundaries_fail_closed(self) -> None:
        assignment = resolve_task(self.task, self.profile, [self.skill])
        cases = [
            replace(self.handoff, task_id="OTHER"),
            replace(self.handoff, skill_lock=()),
            replace(self.handoff, input_lock=()),
            replace(self.handoff, artifact_refs=()),
            replace(self.handoff, status="safe-paused", unresolved=(), recommended_next_actions=()),
            replace(self.handoff, status="waiting", human_decision_required=False),
        ]
        for handoff in cases:
            with self.subTest(status=handoff.status, task=handoff.task_id):
                self.assertTrue(check_handoff_against_task(self.task, handoff))
        for changed_assignment in (
            replace(assignment, task_id="OTHER"),
            replace(assignment, agent_profile="other@1.0.0"),
            replace(assignment, skill_lock=()),
        ):
            with self.subTest(assignment=changed_assignment):
                self.assertTrue(
                    check_handoff_against_task(
                        self.task, self.handoff, assignment=changed_assignment
                    )
                )
        self.assertTrue(
            check_handoff_against_task(
                self.task,
                replace(self.handoff, skill_assignment_ref=None),
                assignment=assignment,
            )
        )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing_files = replace(
                self.handoff,
                skill_assignment_ref="missing-assignment.yaml",
                artifact_refs=("missing-artifact.yaml",),
                transfer_manifest_ref="missing-transfer.yaml",
            )
            codes = {
                risk.code
                for risk in check_handoff_against_task(
                    self.task, missing_files, project_root=root
                )
            }
            self.assertLessEqual(
                {"HANDOFF-ASSIGNMENT-MISSING", "HANDOFF-MISSING-OUTPUT", "HANDOFF-TRANSFER-MANIFEST-MISSING"},
                codes,
            )

    def test_reference_scope_and_claim_edges_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            codes = {
                risk.code
                for risk in check_references(
                    root,
                    [
                        FileReference("missing.txt", "0" * 64),
                        FileReference("../outside.txt", "0" * 64),
                    ],
                )
            }
            self.assertEqual({"REF-MISSING", "REF-OUTSIDE-ROOT"}, codes)
        empty_anchor = replace(self.task, task_id="EMPTY", write_scope=("**",))
        risks = check_write_scope_overlap([self.task, empty_anchor])
        self.assertEqual(["TASK-WRITE-OVERLAP"], [risk.code for risk in risks])
        protocol = load_document(ROOT / "examples/project-protocol.yaml")
        from research_workbench.protocol import ProjectProtocol

        parsed = ProjectProtocol.from_mapping(protocol)
        self.assertEqual([], check_claim_ceiling(parsed, "unresolved"))
        self.assertEqual([], check_claim_ceiling(parsed, parsed.claim_ceiling[0]))


if __name__ == "__main__":
    unittest.main()
