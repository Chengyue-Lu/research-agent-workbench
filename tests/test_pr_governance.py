import importlib.util
import json
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

    def test_authority_protocol_is_r2(self) -> None:
        for path in (
            "src/research_workbench/protocol/authority.py",
            "registry/authority/decision-authority-matrix.yaml",
            "schemas/v0.1.0/decision-authority-matrix.schema.json",
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
