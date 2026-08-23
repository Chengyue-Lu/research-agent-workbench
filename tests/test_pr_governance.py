import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "check_pr_governance.py"
SPEC = importlib.util.spec_from_file_location("check_pr_governance", SCRIPT)
assert SPEC and SPEC.loader
governance = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = governance
SPEC.loader.exec_module(governance)


BASE_SHA = "a" * 40


def valid_body(pr_class: str = "feature") -> str:
    return f"""## 治理元数据

- **PR 类型**: {pr_class}
- **任务 ID**: AUDIT-EXEC-RUNTIME-001
- **工作流目录**: docs/workstreams/huangyi/execution-runtime-recovery-audit
- **责任人**: @let778750-cpu
- **跨负责人审查人**: @Chengyue-Lu
- **基线 SHA**: {BASE_SHA}

## 范围与非目标

有边界的文档变更；不实现运行时功能。

## 契约与权限影响

无——审计材料被明确标记为非规范性材料。

## TASKS 状态变更

本 PR 不修改 TASKS。

## 风险台账

见已提交的主张台账。

## 验证证据

已完成单元测试与干净检出验证。

## 收尾与历史记录

工作流 README 记录了收尾条件。
"""


def legacy_english_body(pr_class: str = "feature") -> str:
    body = valid_body(pr_class)
    replacements = {
        "治理元数据": "Governance metadata",
        "PR 类型": "PR class",
        "任务 ID": "Task ID(s)",
        "工作流目录": "Workstream",
        "责任人": "Accountable owner",
        "跨负责人审查人": "Cross-owner reviewer",
        "基线 SHA": "Base SHA",
        "范围与非目标": "Scope and non-goals",
        "契约与权限影响": "Contract and authority impact",
        "TASKS 状态变更": "TASKS transition",
        "风险台账": "Risk ledger",
        "验证证据": "Verification evidence",
        "收尾与历史记录": "Closeout and history",
    }
    for chinese, english in replacements.items():
        body = body.replace(chinese, english)
    return body


BASE_TASKS = """# Tasks
| ID | 状态 | 任务 | 验收 |
|---|---|---|---|
| M1-001 | DONE | Frozen | Existing acceptance |
| M8-002 | READY | Action contract | Test it |
| M8-003 | PARKED | Resolution | Test that |
"""


class PullRequestBodyTests(unittest.TestCase):
    def test_valid_body_is_parsed(self) -> None:
        metadata = governance.validate_body(valid_body(), BASE_SHA)
        self.assertEqual("let778750-cpu", metadata["Accountable owner"])
        self.assertEqual("Chengyue-Lu", metadata["Cross-owner reviewer"])

    def test_legacy_english_body_is_still_parsed(self) -> None:
        metadata = governance.validate_body(legacy_english_body(), BASE_SHA)
        self.assertEqual("feature", metadata["PR class"])

    def test_missing_section_fails(self) -> None:
        with self.assertRaisesRegex(governance.GovernanceError, "missing or empty"):
            governance.validate_body(
                valid_body().replace("已完成单元测试与干净检出验证。", ""),
                BASE_SHA,
            )

    def test_wrong_base_sha_fails(self) -> None:
        with self.assertRaisesRegex(governance.GovernanceError, "does not match"):
            governance.validate_body(valid_body(), "b" * 40)

    def test_same_owner_and_reviewer_fails(self) -> None:
        body = valid_body().replace("@Chengyue-Lu", "@let778750-cpu")
        with self.assertRaisesRegex(governance.GovernanceError, "cross-owner"):
            governance.validate_body(body, BASE_SHA)


class TopologyTests(unittest.TestCase):
    def test_develop_to_main_release_passes(self) -> None:
        governance.validate_topology(
            base_ref="main",
            head_ref="develop",
            base_repository="org/repo",
            head_repository="org/repo",
            pr_class="release",
        )

    def test_feature_to_main_fails(self) -> None:
        with self.assertRaisesRegex(governance.GovernanceError, "main accepts only"):
            governance.validate_topology(
                base_ref="main",
                head_ref="feature/x",
                base_repository="org/repo",
                head_repository="org/repo",
                pr_class="feature",
            )

    def test_release_to_develop_fails(self) -> None:
        with self.assertRaisesRegex(governance.GovernanceError, "must target main"):
            governance.validate_topology(
                base_ref="develop",
                head_ref="feature/x",
                base_repository="org/repo",
                head_repository="org/repo",
                pr_class="release",
            )


class TasksAuthorityTests(unittest.TestCase):
    def validate(
        self,
        head: str,
        *,
        pr_class: str = "feature",
        labels: set[str] | None = None,
        changed_paths: tuple[str, ...] = ("docs/TASKS.md",),
        declared: set[str] | None = None,
    ) -> None:
        governance.validate_task_changes(
            base_text=BASE_TASKS,
            head_text=head,
            pr_class=pr_class,
            labels=labels or set(),
            changed_paths=changed_paths,
            declared_task_ids=declared or {"M8-002"},
            base_ref="develop",
        )

    def test_feature_may_change_non_done_status(self) -> None:
        self.validate(BASE_TASKS.replace("M8-002 | READY", "M8-002 | IN_PROGRESS"))

    def test_feature_must_declare_changed_task(self) -> None:
        with self.assertRaisesRegex(governance.GovernanceError, "must be declared"):
            self.validate(
                BASE_TASKS.replace("M8-003 | PARKED", "M8-003 | READY"),
                declared={"M8-002"},
            )

    def test_feature_cannot_set_done(self) -> None:
        with self.assertRaisesRegex(governance.GovernanceError, "cannot set DONE"):
            self.validate(BASE_TASKS.replace("M8-002 | READY", "M8-002 | DONE"))

    def test_feature_cannot_rewrite_acceptance(self) -> None:
        with self.assertRaisesRegex(governance.GovernanceError, "cannot redefine"):
            self.validate(BASE_TASKS.replace("Action contract", "Changed requirement"))

    def test_completed_row_is_immutable(self) -> None:
        with self.assertRaisesRegex(governance.GovernanceError, "completed TASKS row"):
            self.validate(BASE_TASKS.replace("Existing acceptance", "Rewritten"))

    def test_closeout_requires_label(self) -> None:
        with self.assertRaisesRegex(governance.GovernanceError, "requires"):
            self.validate(
                BASE_TASKS.replace("M8-002 | READY", "M8-002 | DONE"),
                pr_class="task-closeout",
            )

    def test_docs_only_closeout_passes(self) -> None:
        self.validate(
            BASE_TASKS.replace("M8-002 | READY", "M8-002 | DONE"),
            pr_class="task-closeout",
            labels={"governance/task-closeout"},
            changed_paths=(
                "docs/TASKS.md",
                "docs/history/2026-08-23-M8-002.md",
                "docs/workstreams/chengyue-lu/M8-002/README.md",
            ),
            declared={"M8-002"},
        )

    def test_task_definition_cannot_complete_task(self) -> None:
        with self.assertRaisesRegex(governance.GovernanceError, "cannot set DONE"):
            self.validate(
                BASE_TASKS.replace("M8-002 | READY", "M8-002 | DONE"),
                pr_class="task-definition",
                labels={"governance/task-definition"},
            )

    def test_task_definition_cannot_remove_task(self) -> None:
        without_m8_003 = BASE_TASKS.replace(
            "| M8-003 | PARKED | Resolution | Test that |\n", ""
        )
        with self.assertRaisesRegex(governance.GovernanceError, "TASKS row removed"):
            self.validate(
                without_m8_003,
                pr_class="task-definition",
                labels={"governance/task-definition"},
            )

    def test_task_definition_may_insert_before_done_row(self) -> None:
        inserted = BASE_TASKS.replace(
            "| M1-001 | DONE",
            "| M0-999 | READY | New task | New acceptance |\n| M1-001 | DONE",
        )
        self.validate(
            inserted,
            pr_class="task-definition",
            labels={"governance/task-definition"},
        )

    def test_duplicate_task_id_fails(self) -> None:
        duplicate = BASE_TASKS + "| M8-002 | READY | Duplicate | Nope |\n"
        with self.assertRaisesRegex(governance.GovernanceError, "duplicate"):
            self.validate(duplicate)


if __name__ == "__main__":
    unittest.main()
