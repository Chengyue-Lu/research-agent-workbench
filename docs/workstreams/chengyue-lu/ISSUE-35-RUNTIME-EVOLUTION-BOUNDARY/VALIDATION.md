# ISSUE-35 Validation and Adversarial Evidence

状态：本地确定性验证通过；R2 human review 尚未完成

## 1. Deterministic checks

| 检查 | 结果 | 证据 |
|---|---|---|
| `git diff --check` | PASS | exit 0，无 whitespace error |
| `python -m pytest tests/test_documentation.py tests/test_pr_governance.py` | PASS | 76 passed in 1.87s |
| 完整 `python -m pytest -q`，显式优先使用当前 worktree `src` | PASS | 429 passed、3 skipped in 176.27s |
| `rwb validate examples registry` 的当前 worktree module 等价入口 | PASS | `validated=154 errors=0 warnings=0` |
| changed-path allowlist | PASS | 仅 `docs/`；`src/`、`schemas/`、`registry/`、`examples/`、tests、TASKS、STATUS 均无 diff |

环境说明：系统 Python 存在指向另一个旧 clone 的 editable install，且 shell 中没有 `rwb` console script。
直接执行完整 pytest 会在 collection 阶段导入旧源码，因此不构成本 worktree 的有效结果。复验通过在同一
Python 进程中把当前 worktree `src` 置于 import 首位；repository validation 也通过当前 worktree 的
`research_workbench.cli:main` 等价调用执行。未修改外部 clone 或全局 Python 安装。

上述 PASS 只证明文档、引用、治理和既有仓库结构未回归，不证明 Runtime、live Provider、Skill 科研
增量或 Human Admission 已实现。

## 2. Adversarial review matrix

| 绕过尝试 | 预期结果 | 文档证据 | 审计结果 |
|---|---|---|---|
| 删除/不部署 Need、Candidate、Evaluation、Lifecycle 后运行 no-Skill/direct Tool | 概念 Runtime 主链仍闭合 | ADR-0019 Runtime inner loop；Capability consumer profiles | PASS（架构闭包） |
| 把当前 repository-wide loader 称为 Runtime API | 拒绝；只允许 `maintainer-full` 定性 | Capability Resolution contract；Phase B clarification | PASS |
| 由 gap/failure 自动创建 Skill Need | 拒绝；最多产生 local bounded Diagnostic | ADR authority matrix；Skill Need contract | PASS |
| Runtime 为使用 Skill 直接解析完整 Lifecycle | 拒绝；只允许 exact-pin Release Projection | Lifecycle contract；ADR published port | PASS |
| 用 eligibility/Snapshot/Release metadata 扩大权限 | 拒绝；metadata 仅为 ceiling，最终由 Execution View 收紧 | Authority Basis；Architecture | PASS |
| Registry/Release 更新改变正在运行的 Snapshot | 拒绝；必须产生新 Resolution/Snapshot/View | ADR Snapshot boundary；Roadmap Topic 4 Gate | PASS |
| v0.1 Method→Need 不再可重放 | 拒绝；保留 `maintainer-full` 与原 Schema/fixture | Method contract；diff allowlist；repository validation | PASS |

## 3. Deferred executable evidence

以下必须由后续实现 PR 变成自动测试，本 docs-only PR 不伪造结果：

- Runtime import graph 不包含 Skill Need/Candidate/Evaluation/Lifecycle；
- explicit closure manifest 不使用目录输入或 `rglob(registry, examples)`；
- 无关、损坏的 Evolution Registry 文档不影响 Runtime bundle；
- no-Skill/direct Tool 在零 Skill refs 下生成合法 Resolved Execution View；
- Skill projection 缺失、stale、scope mismatch 或 digest mismatch 时 fail closed；
- Release/Registry 更新不改变已冻结 Snapshot/View；
- gap/Diagnostic 路径没有 Need/Candidate/Promotion write capability。
