import hashlib
import importlib.util
import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "check_pr_governance.py"
SPEC = importlib.util.spec_from_file_location("check_pr_governance", SCRIPT)
assert SPEC and SPEC.loader
governance = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = governance
SPEC.loader.exec_module(governance)


def valid_body(
    *,
    pr_class: str = "feature",
    task_ids: str = "none",
    risk: str = "R0",
    owner: str = "@Chengyue-Lu",
    workstream: str = "none",
    shared_contract: str = "no",
    authority_impact: str = "no",
    authority_basis: str = "not applicable",
    adversarial_evidence: str = "not applicable",
) -> str:
    return f"""## 治理元数据

- **PR 类型**: {pr_class}
- **任务 ID**: {task_ids}
- **风险等级**: {risk}
- **责任人**: {owner}
- **工作流目录**: {workstream}

## 范围与非目标

有边界的修改；不改变未声明接口。

## 契约与权威影响

- **共享契约**: {shared_contract}
- **权威、权限或数据边界**: {authority_impact}

给出分类理由。

## TASKS 状态变更

none

## 验证证据

单元测试通过。

## 剩余风险与后续

none

## 权威依据

{authority_basis}

## 对抗性证据

{adversarial_evidence}
"""


BASE_TASKS = """# Tasks
| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M8-001 | DONE | Frozen | M0 | Existing acceptance |
| M8-002 | IN_PROGRESS | Action contract | M8-001 | Test it |
| M8-003 | PARKED | Resolution | M8-002 | Test that |
| M8-004 | READY | Migration | M8-001 | Migrate it |
| M8-005 | BLOCKED | Authority | M8-001 | Gate it |
"""


def codes(report: object, severity: str | None = None) -> set[str]:
    return {
        item.code
        for item in report.findings
        if severity is None or item.severity == severity
    }


class PullRequestBodyTests(unittest.TestCase):
    def test_minimal_r0_body_does_not_require_sha_reviewer_or_workstream(self) -> None:
        report = governance.GovernanceReport()
        metadata, sections, shared, authority = governance.validate_body(valid_body(), report)
        self.assertFalse(report.has_errors)
        self.assertEqual("none", metadata["Workstream"])
        self.assertEqual("none", metadata["Task ID(s)"])
        self.assertFalse(shared)
        self.assertFalse(authority)
        self.assertIn("Verification evidence", sections)

    def test_missing_required_section_is_a_finding(self) -> None:
        report = governance.GovernanceReport()
        governance.validate_body(valid_body().replace("单元测试通过。", ""), report)
        self.assertIn("SECTION-MISSING", codes(report, "ERROR"))

    def test_contract_flags_must_be_explicit(self) -> None:
        report = governance.GovernanceReport()
        governance.validate_body(valid_body(shared_contract="maybe"), report)
        self.assertIn("META-BOOLEAN", codes(report, "ERROR"))

    def test_unknown_owner_is_rejected(self) -> None:
        report = governance.GovernanceReport()
        governance.validate_body(valid_body(owner="@unknown"), report)
        self.assertIn("OWNER-UNKNOWN", codes(report, "ERROR"))


class RiskInferenceTests(unittest.TestCase):
    def test_test_only_change_is_r0(self) -> None:
        risk, reasons = governance.infer_minimum_risk(
            ["tests/test_widget.py"], shared_contract=False, authority_impact=False
        )
        self.assertEqual("R0", risk)
        self.assertEqual([], reasons)

    def test_schema_change_is_r1(self) -> None:
        risk, _ = governance.infer_minimum_risk(
            ["schemas/v0.1.0/task.schema.json"],
            shared_contract=False,
            authority_impact=False,
        )
        self.assertEqual("R1", risk)

    def test_architecture_change_is_r2(self) -> None:
        risk, _ = governance.infer_minimum_risk(
            ["docs/ARCHITECTURE.md"], shared_contract=False, authority_impact=False
        )
        self.assertEqual("R2", risk)

    def test_method_resolution_schema_is_r2_not_r1(self) -> None:
        risk, _ = governance.infer_minimum_risk(
            ["schemas/v0.1.0/method-resolution.schema.json"],
            shared_contract=False,
            authority_impact=False,
        )
        self.assertEqual("R2", risk)

    def test_capability_requirement_contract_surface_is_r2(self) -> None:
        for path in (
            "schemas/v0.1.0/capability-requirement.schema.json",
            "registry/capabilities/requirements.json",
            "registry/capabilities/requirements/document-read.yaml",
            "src/research_workbench/capability/requirements.py",
        ):
            with self.subTest(path=path):
                risk, _ = governance.infer_minimum_risk(
                    [path], shared_contract=False, authority_impact=False
                )
                self.assertEqual("R2", risk)

    def test_skill_need_contract_surface_is_r2(self) -> None:
        for path in (
            "schemas/v0.1.0/skill-need.schema.json",
            "registry/skill-needs.json",
            "registry/skill-needs/evidence-search-plan-1.0.0.yaml",
            "src/research_workbench/capability/skill_needs.py",
        ):
            with self.subTest(path=path):
                risk, _ = governance.infer_minimum_risk(
                    [path], shared_contract=False, authority_impact=False
                )
                self.assertEqual("R2", risk)

    def test_protocol_profile_contract_surface_is_r2(self) -> None:
        for path in (
            "schemas/v0.1.0/protocol-profile.schema.json",
            "registry/protocol-profiles.json",
            "registry/protocol-profiles/simulation-vv-assurance-1.0.0.yaml",
            "src/research_workbench/protocol/profiles.py",
        ):
            with self.subTest(path=path):
                risk, _ = governance.infer_minimum_risk(
                    [path], shared_contract=False, authority_impact=False
                )
                self.assertEqual("R2", risk)

    def test_capability_resolution_contract_surface_is_r2(self) -> None:
        for path in (
            "schemas/v0.1.0/capability-supply-report.schema.json",
            "schemas/v0.1.0/capability-resolution.schema.json",
            "schemas/v0.1.0/resolved-capability-snapshot.schema.json",
            "src/research_workbench/capability/supply.py",
            "examples/capability-resolution/snapshots/document-read-a.yaml",
        ):
            with self.subTest(path=path):
                risk, _ = governance.infer_minimum_risk(
                    [path], shared_contract=False, authority_impact=False
                )
                self.assertEqual("R2", risk)

    def test_phase_b_evolution_gate_is_r2(self) -> None:
        for path in (
            "schemas/v0.1.0/phase-b-evolution-gate.schema.json",
            "examples/capability-resolution/phase-b-evolution-gate.yaml",
        ):
            with self.subTest(path=path):
                risk, _ = governance.infer_minimum_risk(
                    [path], shared_contract=False, authority_impact=False
                )
                self.assertEqual("R2", risk)

    def test_skill_lifecycle_contract_surface_is_r2(self) -> None:
        for path in (
            "schemas/v0.1.0/skill-lifecycle-record.schema.json",
            "registry/skills/lifecycle-v2.json",
            "registry/skills/lifecycle/simulation-vv-0.1.0-lifecycle-1.0.0.yaml",
            "registry/skills/lifecycle-migrations/accepted-v1-to-lifecycle-v2.yaml",
            "src/research_workbench/capability/lifecycle.py",
        ):
            with self.subTest(path=path):
                risk, _ = governance.infer_minimum_risk(
                    [path], shared_contract=False, authority_impact=False
                )
                self.assertEqual("R2", risk)

    def test_authority_protocol_is_r2(self) -> None:
        for path in (
            "src/research_workbench/protocol/authority.py",
            "registry/authority/decision-authority-matrix.yaml",
            "schemas/v0.1.0/decision-authority-matrix.schema.json",
            "schemas/v0.1.0/authority-rule-eligibility.schema.json",
            "docs/implementation/DECISION_AUTHORITY.md",
        ):
            with self.subTest(path=path):
                risk, _ = governance.infer_minimum_risk(
                    [path], shared_contract=False, authority_impact=False
                )
                self.assertEqual("R2", risk)

    def test_implementation_docs_and_status_are_at_least_r1(self) -> None:
        for path in ("docs/implementation/METHOD_RESOLUTION.md", "docs/STATUS.md"):
            with self.subTest(path=path):
                risk, _ = governance.infer_minimum_risk(
                    [path], shared_contract=False, authority_impact=False
                )
                self.assertIn(risk, {"R1", "R2"})

    def test_declared_r0_is_automatically_upgraded(self) -> None:
        report = governance.GovernanceReport()
        effective = governance.resolve_effective_risk("R0", "R1", report)
        self.assertEqual("R1", effective)
        self.assertIn("RISK-AUTO-UPGRADE", codes(report, "WARNING"))

    def test_declared_r2_is_never_downgraded(self) -> None:
        report = governance.GovernanceReport()
        self.assertEqual("R2", governance.resolve_effective_risk("R2", "R0", report))


class RiskRequirementTests(unittest.TestCase):
    def test_r2_requires_authority_and_adversarial_sections(self) -> None:
        report = governance.GovernanceReport()
        governance.validate_risk_requirements(
            effective_risk="R2",
            sections={"Authority basis": "none", "Adversarial evidence": "n/a"},
            raw_task_ids="GOV-V2-001",
            report=report,
        )
        self.assertEqual(
            {"R2-AUTHORITY-BASIS", "R2-ADVERSARIAL-EVIDENCE"},
            codes(report, "ERROR"),
        )

    def test_r1_requires_task_or_audit_id(self) -> None:
        report = governance.GovernanceReport()
        governance.validate_risk_requirements(
            effective_risk="R1", sections={}, raw_task_ids="none", report=report
        )
        self.assertIn("TASK-ID-RISK", codes(report, "ERROR"))


class WorkstreamTests(unittest.TestCase):
    def test_r0_and_r1_can_omit_workstream(self) -> None:
        r0 = governance.GovernanceReport()
        governance.validate_workstream(
            raw_workstream="none", owner="Chengyue-Lu", effective_risk="R0", head_sha="x", report=r0
        )
        self.assertFalse(r0.has_errors)

        r1 = governance.GovernanceReport()
        governance.validate_workstream(
            raw_workstream="none", owner="Chengyue-Lu", effective_risk="R1", head_sha="x", report=r1
        )
        self.assertFalse(r1.has_errors)
        self.assertIn("WORKSTREAM-R1", codes(r1, "WARNING"))

    def test_r2_requires_workstream(self) -> None:
        report = governance.GovernanceReport()
        governance.validate_workstream(
            raw_workstream="none", owner="Chengyue-Lu", effective_risk="R2", head_sha="x", report=report
        )
        self.assertIn("WORKSTREAM-R2", codes(report, "ERROR"))

    @mock.patch.object(governance, "_read_blob", return_value="ok")
    def test_provided_workstream_must_match_owner(self, _: mock.Mock) -> None:
        report = governance.GovernanceReport()
        governance.validate_workstream(
            raw_workstream="docs/workstreams/huangyi/example",
            owner="Chengyue-Lu",
            effective_risk="R1",
            head_sha="x",
            report=report,
        )
        self.assertIn("WORKSTREAM-OWNER-MISMATCH", codes(report, "ERROR"))


class TopologyTests(unittest.TestCase):
    def check(self, **kwargs: str) -> object:
        report = governance.GovernanceReport()
        governance.validate_topology(report=report, **kwargs)
        return report

    def test_feature_to_develop_passes(self) -> None:
        report = self.check(
            base_ref="develop", head_ref="feature/x", base_repository="org/repo", head_repository="org/repo", pr_class="feature"
        )
        self.assertFalse(report.has_errors)

    def test_develop_to_main_release_passes(self) -> None:
        report = self.check(
            base_ref="main", head_ref="develop", base_repository="org/repo", head_repository="org/repo", pr_class="release"
        )
        self.assertFalse(report.has_errors)

    def test_feature_to_main_fails(self) -> None:
        report = self.check(
            base_ref="main", head_ref="feature/x", base_repository="org/repo", head_repository="org/repo", pr_class="feature"
        )
        self.assertIn("TOPOLOGY-MAIN-SOURCE", codes(report, "ERROR"))
        release_class = self.check(
            base_ref="main",
            head_ref="feature/x",
            base_repository="org/repo",
            head_repository="org/repo",
            pr_class="release",
        )
        self.assertEqual({"TOPOLOGY-MAIN-SOURCE"}, codes(release_class, "ERROR"))

    def test_develop_to_main_rejects_fork_and_wrong_class(self) -> None:
        fork = self.check(
            base_ref="main",
            head_ref="develop",
            base_repository="org/repo",
            head_repository="fork/repo",
            pr_class="release",
        )
        self.assertIn("TOPOLOGY-MAIN-SOURCE", codes(fork, "ERROR"))
        wrong_class = self.check(
            base_ref="main",
            head_ref="develop",
            base_repository="org/repo",
            head_repository="org/repo",
            pr_class="feature",
        )
        self.assertIn("TOPOLOGY-RELEASE-CLASS", codes(wrong_class, "ERROR"))

    def test_strict_curated_release_branch_shape_is_matched_and_dormant(self) -> None:
        report = governance.GovernanceReport()
        result = governance.validate_topology(
            base_ref="main",
            head_ref="release/v1.2.3",
            base_repository="org/repo",
            head_repository="org/repo",
            pr_class="release",
            report=report,
        )
        self.assertTrue(result.curated_release_attempt)
        self.assertTrue(result.curated_release_topology_matched)
        self.assertEqual({"TOPOLOGY-RELEASE-DORMANT"}, codes(report, "ERROR"))

    def test_release_version_repository_class_and_base_fail_closed(self) -> None:
        cases = (
            ({"base_ref": "main", "head_ref": "release/v1.2"}, "TOPOLOGY-RELEASE-BRANCH"),
            ({"base_ref": "main", "head_ref": "release/v01.2.3"}, "TOPOLOGY-RELEASE-BRANCH"),
            ({"base_ref": "main", "head_ref": "release/1.2.3"}, "TOPOLOGY-RELEASE-BRANCH"),
            ({"base_ref": "main", "head_ref": "release/v1.2.3/extra"}, "TOPOLOGY-RELEASE-BRANCH"),
            ({"base_ref": "main", "head_ref": "release/v1.2.3", "head_repository": "fork/repo"}, "TOPOLOGY-RELEASE-REPOSITORY"),
            ({"base_ref": "main", "head_ref": "release/v1.2.3", "pr_class": "feature"}, "TOPOLOGY-RELEASE-CLASS"),
            ({"base_ref": "develop", "head_ref": "release/v1.2.3"}, "TOPOLOGY-RELEASE-BASE"),
        )
        defaults = {
            "base_ref": "main",
            "head_ref": "release/v1.2.3",
            "base_repository": "org/repo",
            "head_repository": "org/repo",
            "pr_class": "release",
        }
        for overrides, expected_code in cases:
            with self.subTest(overrides=overrides):
                report = self.check(**(defaults | overrides))
                self.assertIn(expected_code, codes(report, "ERROR"))


class ReleaseTrustTopologyTests(unittest.TestCase):
    BASE_SHA = "a" * 40
    SOURCE_SHA = "b" * 40
    MANIFEST = b'{"schema_version":1}\n'

    def expectations(self, **overrides: str) -> dict[str, str]:
        values = {
            "expected_source_repository": "org/repo",
            "expected_source_ref": "develop",
            "expected_source_sha": self.SOURCE_SHA,
            "source_ci_run_id": "123456",
            "source_ci_workflow": "CI",
            "source_ci_repository": "org/repo",
            "source_ci_ref": "develop",
            "source_ci_sha": self.SOURCE_SHA,
            "source_ci_conclusion": "success",
            "source_ci_required_checks": json.dumps(
                {
                    "governance": "success",
                    "test (3.11)": "success",
                    "test (3.13)": "success",
                },
                sort_keys=True,
            ),
            "expected_parent_sha": self.BASE_SHA,
            "expected_manifest_sha256": hashlib.sha256(self.MANIFEST).hexdigest(),
        }
        values.update(overrides)
        return values

    def validate(
        self,
        *,
        expectations: dict[str, str] | None = None,
        merge_base_sha: str | None = None,
        release_root_parent_sha: str | None = None,
        release_history_has_merges: bool = False,
        source_commit_exists: bool = True,
        source_in_develop_history: bool = True,
        manifest_bytes: bytes | None = MANIFEST,
    ) -> tuple[bool, object]:
        report = governance.GovernanceReport()
        valid = governance.validate_curated_release_prerequisites(
            base_sha=self.BASE_SHA,
            base_repository="org/repo",
            head_repository="org/repo",
            merge_base_sha=merge_base_sha or self.BASE_SHA,
            release_root_parent_sha=(
                self.BASE_SHA
                if release_root_parent_sha is None
                else release_root_parent_sha
            ),
            release_history_has_merges=release_history_has_merges,
            expectations=self.expectations() if expectations is None else expectations,
            source_commit_exists=source_commit_exists,
            source_in_develop_history=source_in_develop_history,
            manifest_bytes=manifest_bytes,
            report=report,
        )
        return valid, report

    def test_valid_release_prerequisites_have_no_specific_failures(self) -> None:
        valid, report = self.validate()
        self.assertTrue(valid)
        self.assertFalse(report.has_errors, report.findings)

    def test_branch_name_alone_cannot_supply_trusted_expectations(self) -> None:
        valid, report = self.validate(expectations={})
        self.assertFalse(valid)
        self.assertEqual({"RELEASE-EXPECTATIONS-MISSING"}, codes(report, "ERROR"))

    def test_source_repository_ref_sha_history_and_ci_drift_fail_closed(self) -> None:
        cases = (
            (self.expectations(expected_source_repository="fork/repo"), {}, "RELEASE-SOURCE-REPOSITORY"),
            (self.expectations(source_ci_repository="fork/repo"), {}, "RELEASE-SOURCE-REPOSITORY"),
            (self.expectations(expected_source_ref="main"), {}, "RELEASE-SOURCE-REF"),
            (self.expectations(source_ci_ref="main"), {}, "RELEASE-SOURCE-REF"),
            (self.expectations(expected_source_sha="short"), {}, "RELEASE-SOURCE-SHA"),
            (self.expectations(source_ci_sha="c" * 40), {}, "RELEASE-SOURCE-CI"),
            (self.expectations(source_ci_run_id="0"), {}, "RELEASE-SOURCE-CI"),
            (self.expectations(source_ci_workflow="Other"), {}, "RELEASE-SOURCE-CI"),
            (self.expectations(source_ci_conclusion="failure"), {}, "RELEASE-SOURCE-CI"),
            (self.expectations(source_ci_required_checks="not-json"), {}, "RELEASE-SOURCE-CI"),
            (
                self.expectations(
                    source_ci_required_checks=json.dumps({"governance": "success"})
                ),
                {},
                "RELEASE-SOURCE-CI",
            ),
            (self.expectations(), {"source_commit_exists": False}, "RELEASE-SOURCE-HISTORY"),
            (self.expectations(), {"source_in_develop_history": False}, "RELEASE-SOURCE-HISTORY"),
        )
        for expectations, options, expected_code in cases:
            with self.subTest(expected_code=expected_code, options=options):
                valid, report = self.validate(expectations=expectations, **options)
                self.assertFalse(valid)
                self.assertIn(expected_code, codes(report, "ERROR"))

    def test_parent_and_manifest_drift_fail_closed(self) -> None:
        cases = (
            ({"expectations": self.expectations(expected_parent_sha="c" * 40)}, "RELEASE-PARENT-EXPECTATION"),
            ({"merge_base_sha": "c" * 40}, "RELEASE-PARENT-ANCESTRY"),
            ({"release_root_parent_sha": "c" * 40}, "RELEASE-PARENT-ANCESTRY"),
            ({"release_history_has_merges": True}, "RELEASE-PARENT-ANCESTRY"),
            ({"manifest_bytes": None}, "RELEASE-MANIFEST-PREREQUISITE"),
            ({"expectations": self.expectations(expected_manifest_sha256="0" * 64)}, "RELEASE-MANIFEST-PREREQUISITE"),
            ({"expectations": self.expectations(expected_manifest_sha256="invalid")}, "RELEASE-MANIFEST-PREREQUISITE"),
        )
        for options, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                valid, report = self.validate(**options)
                self.assertFalse(valid)
                self.assertIn(expected_code, codes(report, "ERROR"))

    def test_policy_shape_and_activation_cannot_be_weakened_by_data_only(self) -> None:
        cases = (
            ({**governance.CURATED_RELEASE_TOPOLOGY, "activation_state": "active"}, "RELEASE-POLICY-VALUE"),
            ({**governance.CURATED_RELEASE_TOPOLOGY, "unknown": True}, "RELEASE-POLICY-SHAPE"),
            ({**governance.CURATED_RELEASE_TOPOLOGY, "required_external_facts": []}, "RELEASE-POLICY-FACTS"),
        )
        for policy, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                report = governance.GovernanceReport()
                self.assertFalse(governance.validate_curated_release_policy(policy, report))
                self.assertIn(expected_code, codes(report, "ERROR"))

    def test_prerequisite_helper_revalidates_canonical_policy(self) -> None:
        weakened = {**governance.CURATED_RELEASE_TOPOLOGY, "source_ref": "feature/x"}
        report = governance.GovernanceReport()
        valid = governance.validate_curated_release_prerequisites(
            base_sha=self.BASE_SHA,
            base_repository="org/repo",
            head_repository="org/repo",
            merge_base_sha=self.BASE_SHA,
            release_root_parent_sha=self.BASE_SHA,
            release_history_has_merges=False,
            expectations=self.expectations(),
            source_commit_exists=True,
            source_in_develop_history=True,
            manifest_bytes=self.MANIFEST,
            report=report,
            release_policy=weakened,
        )
        self.assertFalse(valid)
        self.assertIn("RELEASE-POLICY-VALUE", codes(report, "ERROR"))

    def test_unknown_expectation_fields_are_rejected(self) -> None:
        valid, report = self.validate(
            expectations=self.expectations(author_controlled_claim="ignored")
        )
        self.assertFalse(valid)
        self.assertIn("RELEASE-EXPECTATIONS-UNKNOWN", codes(report, "ERROR"))


class ReleaseTrustIntegrationTests(unittest.TestCase):
    BASE_SHA = "a" * 40
    HEAD_SHA = "b" * 40
    SOURCE_SHA = "c" * 40
    MANIFEST = b'{"schema_version":1}\n'
    TASKS = """# Tasks
| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M14-001 | READY | Release trust seam | none | Remains dormant |
"""

    def release_event(self) -> dict[str, object]:
        return {
            "pull_request": {
                "base": {
                    "sha": self.BASE_SHA,
                    "ref": "main",
                    "repo": {"full_name": "org/repo"},
                },
                "head": {
                    "sha": self.HEAD_SHA,
                    "ref": "release/v1.2.3",
                    "repo": {"full_name": "org/repo"},
                },
                "body": valid_body(
                    pr_class="release",
                    task_ids="M14-001",
                    risk="R2",
                    workstream="docs/workstreams/chengyue-lu/M14-CURATED-RELEASE",
                    shared_contract="yes",
                    authority_impact="yes",
                    authority_basis="M14-001 and ADR-0021 define the dormant trust seam.",
                    adversarial_evidence="Branch-only, source, parent, manifest and activation bypasses are rejected.",
                ),
                "mergeable": True,
            }
        }

    def expectations(self) -> dict[str, str]:
        return {
            "expected_source_repository": "org/repo",
            "expected_source_ref": "develop",
            "expected_source_sha": self.SOURCE_SHA,
            "source_ci_run_id": "123456",
            "source_ci_workflow": "CI",
            "source_ci_repository": "org/repo",
            "source_ci_ref": "develop",
            "source_ci_sha": self.SOURCE_SHA,
            "source_ci_conclusion": "success",
            "source_ci_required_checks": json.dumps(
                {
                    "governance": "success",
                    "test (3.11)": "success",
                    "test (3.13)": "success",
                },
                sort_keys=True,
            ),
            "expected_parent_sha": self.BASE_SHA,
            "expected_manifest_sha256": hashlib.sha256(self.MANIFEST).hexdigest(),
        }

    def run_release(
        self,
        expectations: dict[str, str] | None,
        *,
        history_error: bool = False,
    ) -> object:
        def read_blob(_: str, path: str) -> str:
            return self.TASKS if path == "docs/TASKS.md" else "workstream evidence"

        with (
            mock.patch.object(governance, "_changed_paths", return_value=[]),
            mock.patch.object(governance, "_merge_base", return_value=self.BASE_SHA),
            mock.patch.object(
                governance,
                "_release_history",
                return_value=governance.ReleaseHistory(self.BASE_SHA, False),
                side_effect=(
                    governance.GovernanceError("history unavailable")
                    if history_error else None
                ),
            ),
            mock.patch.object(governance, "_commit_exists", return_value=True),
            mock.patch.object(governance, "_is_ancestor", return_value=True),
            mock.patch.object(
                governance,
                "_blob_exists",
                side_effect=lambda _commit, path: path == "RELEASE_MANIFEST.json",
            ),
            mock.patch.object(governance, "_read_blob_bytes", return_value=self.MANIFEST),
            mock.patch.object(governance, "_read_blob", side_effect=read_blob),
            mock.patch.object(governance, "_published_documents_at", return_value={}),
        ):
            if expectations is None:
                return governance.check_pull_request(self.release_event())
            return governance.check_pull_request(self.release_event(), release_expectations=expectations)

    def test_fully_valid_release_candidate_remains_dormant_and_r2(self) -> None:
        report = self.run_release(self.expectations())
        self.assertEqual({"TOPOLOGY-RELEASE-DORMANT"}, codes(report, "ERROR"))
        self.assertEqual("R2", report.effective_risk)
        self.assertIn(
            "curated release topology attempts are always governed as R2",
            report.risk_reasons,
        )

    def test_pr_body_or_branch_name_cannot_replace_trusted_expectations(self) -> None:
        report = self.run_release({})
        self.assertIn("RELEASE-EXPECTATIONS-MISSING", codes(report, "ERROR"))
        self.assertIn("TOPOLOGY-RELEASE-DORMANT", codes(report, "ERROR"))

    def test_process_environment_is_not_implicitly_trusted(self) -> None:
        environment = {
            "RWB_RELEASE_" + key.upper(): value
            for key, value in self.expectations().items()
        }
        with mock.patch.dict(os.environ, environment, clear=False):
            report = self.run_release(None)
        self.assertIn("RELEASE-EXPECTATIONS-MISSING", codes(report, "ERROR"))

    def test_release_trust_read_failure_is_blocking(self) -> None:
        report = self.run_release(self.expectations(), history_error=True)
        self.assertIn("RELEASE-TRUST-READ", codes(report, "ERROR"))

    def test_develop_to_main_check_remains_executable(self) -> None:
        event = self.release_event()
        pull_request = event["pull_request"]
        assert isinstance(pull_request, dict)
        head = pull_request["head"]
        assert isinstance(head, dict)
        head["ref"] = "develop"
        pull_request["body"] = valid_body(pr_class="release")

        with (
            mock.patch.object(governance, "_changed_paths", return_value=[]),
            mock.patch.object(governance, "_merge_base", return_value=self.BASE_SHA),
            mock.patch.object(governance, "_read_blob", return_value=BASE_TASKS),
            mock.patch.object(governance, "_blob_exists", return_value=False),
            mock.patch.object(governance, "_published_documents_at", return_value={}),
        ):
            report = governance.check_pull_request(event)
        self.assertFalse(report.has_errors, report.findings)


class TasksAuthorityTests(unittest.TestCase):
    def validate(
        self,
        head: str,
        *,
        pr_class: str = "feature",
        declared: set[str] | None = None,
        effective_risk: str = "R0",
        changed_paths: tuple[str, ...] = ("docs/TASKS.md",),
        verification_evidence: str | None = None,
    ) -> object:
        declared_ids = declared or set()
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=BASE_TASKS,
            head_text=head,
            pr_class=pr_class,
            changed_paths=changed_paths,
            declared_task_ids=declared_ids,
            effective_risk=effective_risk,
            verification_evidence=(
                verification_evidence
                if verification_evidence is not None
                else "verified " + " ".join(sorted(declared_ids))
            ),
            report=report,
        )
        return report

    def test_legal_feature_transitions_pass(self) -> None:
        cases = (
            ("M8-004 | READY", "M8-004 | IN_PROGRESS", {"M8-004"}),
            ("M8-002 | IN_PROGRESS", "M8-002 | DONE", {"M8-002"}),
            ("M8-005 | BLOCKED", "M8-005 | IN_PROGRESS", {"M8-005"}),
            ("M8-004 | READY", "M8-004 | DONE", {"M8-004"}),
        )
        for old, new, declared in cases:
            with self.subTest(new=new):
                report = self.validate(BASE_TASKS.replace(old, new), declared=declared)
                self.assertFalse(report.has_errors, report.findings)

    def test_combined_completion_and_dependency_activation_passes(self) -> None:
        head = BASE_TASKS.replace("M8-002 | IN_PROGRESS", "M8-002 | DONE").replace(
            "M8-003 | PARKED", "M8-003 | READY"
        )
        report = self.validate(head, declared={"M8-002", "M8-003"})
        self.assertFalse(report.has_errors, report.findings)

    def test_atomic_dependency_chain_can_complete_in_one_stage(self) -> None:
        base = """# Tasks
| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M8-001 | DONE | Foundation | M0 | Existing acceptance |
| M8-002 | READY | Action | M8-001 | Action evidence |
| M8-003 | PARKED | Resolution | M8-002 | Resolution evidence |
| M8-004 | PARKED | Migration | M8-003 | Migration evidence |
| M8-005 | PARKED | Authority | M8-004 | Authority evidence |
"""
        head = base.replace("M8-002 | READY", "M8-002 | DONE")
        for task_id in ("M8-003", "M8-004", "M8-005"):
            head = head.replace(f"{task_id} | PARKED", f"{task_id} | DONE")
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=base,
            head_text=head,
            pr_class="feature",
            changed_paths=("docs/TASKS.md",),
            declared_task_ids={"M8-002", "M8-003", "M8-004", "M8-005"},
            effective_risk="R2",
            verification_evidence="M8-002 pass; M8-003 pass; M8-004 pass; M8-005 pass",
            report=report,
        )
        self.assertFalse(report.has_errors, report.findings)
        self.assertIn("TASK-ATOMIC-COMPLETION", codes(report, "INFO"))

    def test_atomic_completion_fails_when_dependency_is_missing(self) -> None:
        base = BASE_TASKS.replace("M8-003 | PARKED", "M8-003 | PARKED").replace(
            "M8-002 | IN_PROGRESS", "M8-002 | PARKED"
        )
        head = base.replace("M8-003 | PARKED", "M8-003 | DONE")
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=base,
            head_text=head,
            pr_class="feature",
            changed_paths=("docs/TASKS.md",),
            declared_task_ids={"M8-003"},
            effective_risk="R2",
            verification_evidence="M8-003 pass",
            report=report,
        )
        self.assertIn("TASK-DEPENDENCY-NOT-DONE", codes(report, "ERROR"))

    def test_r2_connected_linear_stage_chain_passes(self) -> None:
        base = """# Tasks
| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M8-001 | DONE | Foundation | M0 | Existing acceptance |
| M8-002 | READY | Anchor | M8-001 | Anchor evidence |
| M8-003 | PARKED | Middle | M8-002 | Middle evidence |
| M8-004 | PARKED | Leaf | M8-003 | Leaf evidence |
"""
        head = base.replace("M8-002 | READY", "M8-002 | DONE")
        head = head.replace("M8-003 | PARKED", "M8-003 | DONE")
        head = head.replace("M8-004 | PARKED", "M8-004 | DONE")
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=base,
            head_text=head,
            pr_class="feature",
            changed_paths=("docs/TASKS.md",),
            declared_task_ids={"M8-002", "M8-003", "M8-004"},
            effective_risk="R2",
            verification_evidence="M8-002 anchor pass; M8-003 middle pass; M8-004 leaf pass",
            report=report,
        )
        self.assertFalse(report.has_errors, report.findings)

    def test_r2_branching_dag_reachable_from_anchor_passes(self) -> None:
        base = """# Tasks
| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M8-001 | DONE | Foundation | M0 | Existing acceptance |
| M8-002 | IN_PROGRESS | Anchor | M8-001 | Anchor evidence |
| M8-003 | PARKED | Left | M8-002 | Left evidence |
| M8-004 | PARKED | Right | M8-002 | Right evidence |
| M8-005 | PARKED | Join | M8-003, M8-004 | Join evidence |
"""
        head = base.replace("M8-002 | IN_PROGRESS", "M8-002 | DONE")
        for task_id in ("M8-003", "M8-004", "M8-005"):
            head = head.replace(f"{task_id} | PARKED", f"{task_id} | DONE")
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=base,
            head_text=head,
            pr_class="feature",
            changed_paths=("docs/TASKS.md",),
            declared_task_ids={"M8-002", "M8-003", "M8-004", "M8-005"},
            effective_risk="R2",
            verification_evidence="M8-002 pass; M8-003 pass; M8-004 pass; M8-005 pass",
            report=report,
        )
        self.assertFalse(report.has_errors, report.findings)

    def test_r1_parked_to_done_chain_fails(self) -> None:
        head = BASE_TASKS.replace("M8-002 | IN_PROGRESS", "M8-002 | DONE").replace(
            "M8-003 | PARKED", "M8-003 | DONE"
        )
        report = self.validate(
            head,
            declared={"M8-002", "M8-003"},
            effective_risk="R1",
        )
        self.assertIn("TASK-ATOMIC-RISK", codes(report, "ERROR"))
        self.assertIn("TASK-TRANSITION", codes(report, "ERROR"))

    def test_single_parked_completion_with_base_done_dependency_fails(self) -> None:
        base = BASE_TASKS.replace("M8-002 | IN_PROGRESS", "M8-002 | DONE")
        head = base.replace("M8-003 | PARKED", "M8-003 | DONE")
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=base,
            head_text=head,
            pr_class="feature",
            changed_paths=("docs/TASKS.md",),
            declared_task_ids={"M8-003"},
            effective_risk="R2",
            verification_evidence="M8-003 verified",
            report=report,
        )
        self.assertIn("TASK-ATOMIC-ANCHOR-MISSING", codes(report, "ERROR"))
        self.assertIn("TASK-ATOMIC-DISCONNECTED", codes(report, "ERROR"))

    def test_disconnected_parked_completion_component_fails(self) -> None:
        base = """# Tasks
| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M8-001 | DONE | Foundation | M0 | Existing acceptance |
| M8-002 | READY | Anchor | M8-001 | Anchor evidence |
| M8-003 | PARKED | Connected | M8-002 | Connected evidence |
| M9-999 | PARKED | Disconnected | M8-001 | Disconnected evidence |
"""
        head = base.replace("M8-002 | READY", "M8-002 | DONE")
        head = head.replace("M8-003 | PARKED", "M8-003 | DONE")
        head = head.replace("M9-999 | PARKED", "M9-999 | DONE")
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=base,
            head_text=head,
            pr_class="feature",
            changed_paths=("docs/TASKS.md",),
            declared_task_ids={"M8-002", "M8-003", "M9-999"},
            effective_risk="R2",
            verification_evidence="M8-002 pass; M8-003 pass; M9-999 pass",
            report=report,
        )
        self.assertIn("TASK-ATOMIC-DISCONNECTED", codes(report, "ERROR"))

    def test_atomic_completion_without_anchor_fails(self) -> None:
        base = """# Tasks
| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M8-001 | DONE | Foundation | M0 | Existing acceptance |
| M8-002 | PARKED | First | M8-001 | First evidence |
| M8-003 | PARKED | Second | M8-002 | Second evidence |
"""
        head = base.replace("M8-002 | PARKED", "M8-002 | DONE").replace(
            "M8-003 | PARKED", "M8-003 | DONE"
        )
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=base,
            head_text=head,
            pr_class="feature",
            changed_paths=("docs/TASKS.md",),
            declared_task_ids={"M8-002", "M8-003"},
            effective_risk="R2",
            verification_evidence="M8-002 pass; M8-003 pass",
            report=report,
        )
        self.assertIn("TASK-ATOMIC-ANCHOR-MISSING", codes(report, "ERROR"))

    def test_atomic_completion_with_undeclared_intermediate_fails(self) -> None:
        base = """# Tasks
| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M8-001 | DONE | Foundation | M0 | Existing acceptance |
| M8-002 | READY | Anchor | M8-001 | Anchor evidence |
| M8-003 | PARKED | Middle | M8-002 | Middle evidence |
| M8-004 | PARKED | Leaf | M8-003 | Leaf evidence |
"""
        head = base.replace("M8-002 | READY", "M8-002 | DONE")
        head = head.replace("M8-003 | PARKED", "M8-003 | DONE")
        head = head.replace("M8-004 | PARKED", "M8-004 | DONE")
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=base,
            head_text=head,
            pr_class="feature",
            changed_paths=("docs/TASKS.md",),
            declared_task_ids={"M8-002", "M8-004"},
            effective_risk="R2",
            verification_evidence="M8-002 pass; M8-003 pass; M8-004 pass",
            report=report,
        )
        self.assertIn("TASK-STATUS-UNDECLARED", codes(report, "ERROR"))

    def test_atomic_completion_missing_per_task_evidence_fails(self) -> None:
        head = BASE_TASKS.replace("M8-002 | IN_PROGRESS", "M8-002 | DONE").replace(
            "M8-003 | PARKED", "M8-003 | DONE"
        )
        report = self.validate(
            head,
            declared={"M8-002", "M8-003"},
            effective_risk="R2",
            verification_evidence="M8-002 anchor passed",
        )
        self.assertIn("TASK-DONE-EVIDENCE-MISSING", codes(report, "ERROR"))

    def test_atomic_completion_cyclic_dag_fails(self) -> None:
        base = """# Tasks
| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M8-001 | DONE | Foundation | M0 | Existing acceptance |
| M8-002 | READY | Anchor | M8-001 | Anchor evidence |
| M8-003 | PARKED | Cycle A | M8-002, M8-004 | A evidence |
| M8-004 | PARKED | Cycle B | M8-003 | B evidence |
"""
        head = base.replace("M8-002 | READY", "M8-002 | DONE")
        head = head.replace("M8-003 | PARKED", "M8-003 | DONE")
        head = head.replace("M8-004 | PARKED", "M8-004 | DONE")
        report = governance.GovernanceReport()
        governance.validate_task_changes(
            base_text=base,
            head_text=head,
            pr_class="feature",
            changed_paths=("docs/TASKS.md",),
            declared_task_ids={"M8-002", "M8-003", "M8-004"},
            effective_risk="R2",
            verification_evidence="M8-002 pass; M8-003 pass; M8-004 pass",
            report=report,
        )
        self.assertIn("TASK-DEPENDENCY-CYCLE", codes(report, "ERROR"))

    def test_each_completed_task_requires_named_evidence(self) -> None:
        head = BASE_TASKS.replace("M8-002 | IN_PROGRESS", "M8-002 | DONE")
        report = self.validate(
            head,
            declared={"M8-002"},
            verification_evidence="full suite passed",
        )
        self.assertIn("TASK-DONE-EVIDENCE-MISSING", codes(report, "ERROR"))

    def test_dependency_must_be_done_for_ready(self) -> None:
        report = self.validate(
            BASE_TASKS.replace("M8-003 | PARKED", "M8-003 | READY"),
            declared={"M8-003"},
        )
        self.assertIn("TASK-DEPENDENCY-NOT-DONE", codes(report, "ERROR"))

    def test_undeclared_status_change_fails(self) -> None:
        report = self.validate(BASE_TASKS.replace("M8-004 | READY", "M8-004 | DONE"))
        self.assertIn("TASK-STATUS-UNDECLARED", codes(report, "ERROR"))

    def test_done_task_is_immutable(self) -> None:
        report = self.validate(BASE_TASKS.replace("Existing acceptance", "Rewritten"), declared={"M8-001"})
        self.assertIn("TASK-DONE-IMMUTABLE", codes(report, "ERROR"))

    def test_feature_cannot_rewrite_acceptance(self) -> None:
        report = self.validate(BASE_TASKS.replace("Test it", "Changed acceptance"), declared={"M8-002"})
        self.assertIn("TASK-DEFINITION-REWRITE", codes(report, "ERROR"))

    def test_illegal_transition_fails(self) -> None:
        report = self.validate(
            BASE_TASKS.replace("M8-003 | PARKED", "M8-003 | IN_PROGRESS"),
            declared={"M8-003"},
        )
        self.assertIn("TASK-TRANSITION", codes(report, "ERROR"))

    def test_task_definition_must_match_declared_ids(self) -> None:
        changed = BASE_TASKS.replace("Action contract", "Revised contract")
        valid = self.validate(changed, pr_class="task-definition", declared={"M8-002"})
        self.assertFalse(valid.has_errors, valid.findings)
        invalid = self.validate(changed, pr_class="task-definition", declared={"M8-003"})
        self.assertIn("TASK-DECLARATION-CLOSURE", codes(invalid, "ERROR"))


class PolicyAndCodeownersTests(unittest.TestCase):
    def test_policy_has_three_by_three_model(self) -> None:
        policy = json.loads((ROOT / ".github" / "governance-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(["feature", "task-definition", "release"], policy["pr_classes"])
        self.assertEqual(["R0", "R1", "R2"], policy["risk_order"])
        self.assertEqual(["INFO", "WARNING", "ERROR"], policy["finding_severities"])

    def test_curated_release_policy_is_strict_declarative_and_dormant(self) -> None:
        policy = json.loads((ROOT / ".github" / "governance-policy.json").read_text(encoding="utf-8"))
        release = policy["curated_release_topology"]
        self.assertEqual("dormant", release["activation_state"])
        self.assertEqual("M14-005", release["activation_task"])
        self.assertEqual("main", release["base_ref"])
        self.assertEqual("develop", release["source_ref"])
        self.assertEqual("trusted-caller-attestation", release["expectations_source"])
        self.assertTrue(release["same_repository"])
        report = governance.GovernanceReport()
        self.assertTrue(governance.validate_curated_release_policy(release, report))
        self.assertFalse(report.has_errors, report.findings)

    def test_curated_release_required_checks_exist_in_ci_workflow(self) -> None:
        policy = json.loads(
            (ROOT / ".github" / "governance-policy.json").read_text(encoding="utf-8")
        )
        required_checks = set(
            policy["curated_release_topology"]["source_ci_required_checks"]
        )
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        actual_checks = {"governance"}
        actual_checks.update(
            match.group(1)
            for match in re.finditer(r"(?m)^\s{4}name:\s*(.+?)\s*$", workflow)
        )
        self.assertLessEqual(required_checks, actual_checks)

    def test_published_identity_policy_declares_all_protected_kinds(self) -> None:
        policy = json.loads((ROOT / ".github" / "governance-policy.json").read_text(encoding="utf-8"))
        declarations = {
            item["kind"]: tuple(item["identity_fields"])
            for item in policy["published_identities"]
        }
        self.assertEqual(
            {
                "mode-action": ("action_id", "version"),
                "research-mode": ("mode_id", "version"),
                "decision-authority-matrix": ("matrix_id", "version"),
                "research-mode-migration": ("migration_id", "migration_version"),
                "capability-requirement": ("requirement_id",),
                "skill-need": ("need_id", "version"),
                "protocol-profile": ("profile_id", "version"),
                "skill-lifecycle-record": ("lifecycle_id", "lifecycle_version"),
                "skill-lifecycle-migration": ("migration_id", "migration_version"),
                "skill-release-projection": ("projection_id", "projection_version"),
            },
            declarations,
        )

    def test_versioned_research_mode_directory_is_protected(self) -> None:
        self.assertEqual(
            ("research-mode", ("mode_id", "version")),
            governance._published_identity_spec(
                "registry/modes/v0.2.0/simulation.yaml"
            ),
        )

    def test_codeowners_has_no_global_wildcard_and_keeps_sensitive_paths(self) -> None:
        lines = [
            line.strip()
            for line in (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertFalse(any(line.split()[0] == "*" for line in lines))
        patterns = {line.split()[0] for line in lines}
        self.assertTrue({"/.github/", "/docs/ARCHITECTURE.md", "/schemas/", "/registry/"} <= patterns)

    def test_template_omits_machine_known_and_retired_fields(self) -> None:
        template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
        self.assertNotIn("基线 SHA", template)
        self.assertNotIn("跨负责人审查人", template)
        self.assertNotIn("task-closeout", template)
        for required in ("风险等级", "共享契约", "权威依据", "对抗性证据"):
            self.assertIn(required, template)

    def test_pr25_rollout_is_retained_and_marked_superseded(self) -> None:
        rollout = (
            ROOT
            / "docs/workstreams/huangyi/execution-runtime-recovery-audit/GITHUB_GOVERNANCE_ROLLOUT.md"
        ).read_text(encoding="utf-8")
        self.assertIn("superseded", rollout.lower())
        self.assertIn("不改写历史事实", rollout)


class PublishedActionIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = {
            "entries": [
                {
                    "action_id": "ES-A1",
                    "version": "1.0.0",
                    "mode_ref": "evidence-synthesis@0.1.0",
                    "document_path": "registry/modes/actions/evidence-synthesis/ES-A1.yaml",
                    "content_hash": "sha256:" + "a" * 64,
                }
            ]
        }

    def validate(self, head: dict) -> object:
        report = governance.GovernanceReport()
        governance.validate_mode_action_registry_history(self.base, head, report)
        return report

    def test_existing_action_entry_is_append_only(self) -> None:
        head = json.loads(json.dumps(self.base))
        head["entries"].append(
            {
                "action_id": "ES-A1",
                "version": "1.1.0",
                "mode_ref": "evidence-synthesis@0.1.0",
                "document_path": "registry/modes/actions/evidence-synthesis/ES-A1-1.1.0.yaml",
                "content_hash": "sha256:" + "b" * 64,
            }
        )
        self.assertFalse(self.validate(head).has_errors)

    def test_same_identity_cannot_change_hash(self) -> None:
        head = json.loads(json.dumps(self.base))
        head["entries"][0]["content_hash"] = "sha256:" + "b" * 64
        self.assertIn("ACTION-IDENTITY-MUTATED", codes(self.validate(head), "ERROR"))

    def test_published_identity_cannot_be_removed(self) -> None:
        self.assertIn(
            "ACTION-IDENTITY-REMOVED",
            codes(self.validate({"entries": []}), "ERROR"),
        )


class PublishedDocumentIdentityTests(unittest.TestCase):
    CASES = {
        "registry/modes/actions/simulation/SIM-A3.yaml": (
            "mode-action",
            "action_id: SIM-A3\nversion: 2.0.0\nsummary: original\n",
            "action_id: SIM-A3\nversion: 2.1.0\nsummary: appended\n",
        ),
        "registry/modes/simulation.yaml": (
            "research-mode",
            "mode_id: simulation\nversion: 0.2.0\nsummary: original\n",
            "mode_id: simulation\nversion: 0.3.0\nsummary: appended\n",
        ),
        "registry/authority/decision-authority-matrix.yaml": (
            "decision-authority-matrix",
            "matrix_id: default\nversion: 1.0.0\nsummary: original\n",
            "matrix_id: default\nversion: 1.1.0\nsummary: appended\n",
        ),
        "registry/modes/migrations/simulation-v01-v02.yaml": (
            "research-mode-migration",
            "migration_id: simulation-v01-v02\nmigration_version: 1.0.0\nsummary: original\n",
            "migration_id: simulation-v01-v02\nmigration_version: 1.1.0\nsummary: appended\n",
        ),
        "registry/capabilities/requirements/document-read.yaml": (
            "capability-requirement",
            "requirement_id: document-read\nsummary: original\n",
            "requirement_id: document-read-v2\nsummary: appended\n",
        ),
        "registry/skill-needs/evidence-search-plan-1.0.0.yaml": (
            "skill-need",
            "need_id: evidence-search-plan\nversion: 1.0.0\nsummary: original\n",
            "need_id: evidence-search-plan\nversion: 1.1.0\nsummary: appended\n",
        ),
        "registry/protocol-profiles/simulation-vv-assurance-1.0.0.yaml": (
            "protocol-profile",
            "profile_id: simulation-vv-assurance\nversion: 1.0.0\nsummary: original\n",
            "profile_id: simulation-vv-assurance\nversion: 1.1.0\nsummary: appended\n",
        ),
        "registry/skills/lifecycle/simulation-vv-0.1.0-lifecycle-1.0.0.yaml": (
            "skill-lifecycle-record",
            "lifecycle_id: simulation-vv\nlifecycle_version: 1.0.0\nsummary: original\n",
            "lifecycle_id: simulation-vv\nlifecycle_version: 1.1.0\nsummary: appended\n",
        ),
        "registry/skills/lifecycle-migrations/accepted-v1-to-lifecycle-v2.yaml": (
            "skill-lifecycle-migration",
            "migration_id: accepted-v1-to-lifecycle-v2\nmigration_version: 1.0.0\nsummary: original\n",
            "migration_id: accepted-v1-to-lifecycle-v2\nmigration_version: 1.1.0\nsummary: appended\n",
        ),
        "registry/skills/release-projections/synthetic-skill-1.0.0.yaml": (
            "skill-release-projection",
            "projection_id: synthetic-skill-1.0.0\nprojection_version: 1.0.0\nsummary: original\n",
            "projection_id: synthetic-skill-1.0.0\nprojection_version: 1.1.0\nsummary: appended\n",
        ),
    }

    def test_same_version_rewrite_fails_for_every_published_kind(self) -> None:
        for path, (kind, original, _) in self.CASES.items():
            with self.subTest(kind=kind):
                report = governance.GovernanceReport()
                governance.validate_published_identity_history(
                    {path: original},
                    {path: original.replace("original", "rewritten")},
                    report,
                )
                self.assertIn("PUBLISHED-IDENTITY-MUTATED", codes(report, "ERROR"))

    def test_new_version_append_preserves_old_identity(self) -> None:
        for path, (kind, original, appended) in self.CASES.items():
            with self.subTest(kind=kind):
                suffix = ".json" if path.endswith(".json") else ".yaml"
                appended_path = path.removesuffix(suffix) + "-next" + suffix
                report = governance.GovernanceReport()
                governance.validate_published_identity_history(
                    {path: original},
                    {path: original, appended_path: appended},
                    report,
                )
                self.assertFalse(report.has_errors, report.findings)

    def assert_move_out_fails(self, protected_path: str, content: str, archive_path: str) -> None:
        report = governance.GovernanceReport()
        governance.validate_published_identity_history(
            {protected_path: content},
            {archive_path: content},
            report,
        )
        self.assertIn("PUBLISHED-IDENTITY-REMOVED", codes(report, "ERROR"))

    def test_research_mode_move_outside_registry_fails(self) -> None:
        _, content, _ = self.CASES["registry/modes/simulation.yaml"]
        self.assert_move_out_fails(
            "registry/modes/simulation.yaml",
            content,
            "archive/simulation.yaml",
        )

    def test_versioned_research_mode_move_outside_registry_fails(self) -> None:
        content = "mode_id: simulation\nversion: 0.2.0\nsummary: original\n"
        self.assert_move_out_fails(
            "registry/modes/v0.2.0/simulation.yaml",
            content,
            "archive/v0.2.0/simulation.yaml",
        )

    def test_authority_matrix_move_outside_registry_fails(self) -> None:
        path = "registry/authority/decision-authority-matrix.yaml"
        _, content, _ = self.CASES[path]
        self.assert_move_out_fails(path, content, "archive/decision-authority-matrix.yaml")

    def test_migration_move_outside_registry_fails(self) -> None:
        path = "registry/modes/migrations/simulation-v01-v02.yaml"
        _, content, _ = self.CASES[path]
        self.assert_move_out_fails(path, content, "archive/simulation-v01-v02.yaml")

    def test_action_move_outside_protected_tree_fails(self) -> None:
        path = "registry/modes/actions/simulation/SIM-A3.yaml"
        _, content, _ = self.CASES[path]
        self.assert_move_out_fails(path, content, "archive/SIM-A3.yaml")

    def test_published_action_deletion_fails(self) -> None:
        path = "registry/modes/actions/simulation/SIM-A3.yaml"
        _, content, _ = self.CASES[path]
        report = governance.GovernanceReport()
        governance.validate_published_identity_history({path: content}, {}, report)
        self.assertIn("PUBLISHED-IDENTITY-REMOVED", codes(report, "ERROR"))

    def test_same_identity_relocation_inside_protected_tree_fails(self) -> None:
        path = "registry/modes/simulation.yaml"
        _, content, _ = self.CASES[path]
        report = governance.GovernanceReport()
        governance.validate_published_identity_history(
            {path: content},
            {"registry/modes/simulation-relocated.yaml": content},
            report,
        )
        self.assertIn("PUBLISHED-IDENTITY-MUTATED", codes(report, "ERROR"))

    def test_new_version_append_with_old_path_retained_passes(self) -> None:
        path = "registry/modes/simulation.yaml"
        _, original, appended = self.CASES[path]
        report = governance.GovernanceReport()
        governance.validate_published_identity_history(
            {path: original},
            {
                path: original,
                "registry/modes/simulation-v0.3.yaml": appended,
            },
            report,
        )
        self.assertFalse(report.has_errors, report.findings)

    def test_unrelated_archive_file_addition_passes(self) -> None:
        path = "registry/modes/simulation.yaml"
        _, content, _ = self.CASES[path]
        report = governance.GovernanceReport()
        governance.validate_published_identity_history(
            {path: content},
            {
                path: content,
                "archive/notes.yaml": "summary: unrelated archive material\n",
            },
            report,
        )
        self.assertFalse(report.has_errors, report.findings)


class PublishedIdentityIntegrationTests(unittest.TestCase):
    def test_move_out_is_detected_when_changed_path_is_not_published(self) -> None:
        base_path = "registry/modes/simulation.yaml"
        content = "mode_id: simulation\nversion: 0.2.0\nsummary: original\n"
        event = {
            "pull_request": {
                "base": {
                    "sha": "a" * 40,
                    "ref": "develop",
                    "repo": {"full_name": "org/repo"},
                },
                "head": {
                    "sha": "b" * 40,
                    "ref": "feature/move-out",
                    "repo": {"full_name": "org/repo"},
                },
                "body": valid_body(),
                "mergeable": True,
            }
        }
        with (
            mock.patch.object(governance, "_changed_paths", return_value=["archive/simulation.yaml"]),
            mock.patch.object(governance, "_merge_base", return_value="a" * 40),
            mock.patch.object(governance, "_read_blob", return_value=BASE_TASKS),
            mock.patch.object(
                governance,
                "_published_documents_at",
                side_effect=[{base_path: content}, {}],
            ) as published_documents,
        ):
            report = governance.check_pull_request(event)

        self.assertEqual(2, published_documents.call_count)
        self.assertIn("PUBLISHED-IDENTITY-REMOVED", codes(report, "ERROR"))


if __name__ == "__main__":
    unittest.main()
