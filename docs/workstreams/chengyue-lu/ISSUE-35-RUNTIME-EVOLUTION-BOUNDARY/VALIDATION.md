# ISSUE-35 Validation and Adversarial Evidence

状态：PR 基线确定性验证通过；本轮 docs-only blocker 修复的静态与独立架构复审通过；R2 final review 尚未完成

## 1. Deterministic checks

| 检查 | 结果 | 证据 |
|---|---|---|
| 当前 blocker 修复的 `git diff --check` | PASS | exit 0，无 whitespace error |
| 当前 blocker 修复的 focused documentation/governance tests | PASS | 76 passed in 0.96s；在无需等待 Python 校核的提醒前已完成 |
| PR 基线 `e4c8105` 的完整 `python -m pytest -q` | PASS | 429 passed、3 skipped in 176.27s |
| PR 基线 `e4c8105` 的 repository validation | PASS | `validated=154 errors=0 warnings=0` |
| 当前 blocker 修复的 changed-path allowlist | PASS | 仅 `docs/`；`src/`、`schemas/`、`registry/`、`examples/`、tests、TASKS、STATUS 均无 diff |

环境说明：系统 Python 存在指向另一个旧 clone 的 editable install，且 shell 中没有 `rwb` console script。
直接执行完整 pytest 会在 collection 阶段导入旧源码，因此不构成本 worktree 的有效结果。复验通过在同一
Python 进程中把当前 worktree `src` 置于 import 首位；repository validation 也通过当前 worktree 的
`research_workbench.cli:main` 等价调用执行。未修改外部 clone 或全局 Python 安装。

本轮是纯文档 authority/dependency 修复，不等待新的全量 Python 校核；全量与 repository validation 结果
明确保留为 PR 基线证据。当前修复以静态 diff、changed-path allowlist、十项架构自检和独立只读复审为
主要证据。上述 PASS 不证明 Runtime、live Provider、Skill 科研增量或 Human Admission 已实现。

## 2. Adversarial review matrix

| 绕过尝试 | 预期结果 | 文档证据 | 审计结果 |
|---|---|---|---|
| 删除/不部署 Need、Candidate、Evaluation、Lifecycle 后运行 no-Skill/direct Tool | 概念 Runtime 主链仍闭合 | ADR-0019 Runtime inner loop；Capability consumer profiles | PASS（架构闭包） |
| 把当前 repository-wide loader 称为 Runtime API | 拒绝；只允许 `maintainer-full` 定性 | Capability Resolution contract；Phase B clarification | PASS |
| 由 gap/failure 自动创建 Skill Need | 拒绝；最多产生 local bounded Diagnostic | ADR authority matrix；Skill Need contract | PASS |
| Runtime 为使用 Skill 直接解析完整 Lifecycle | 拒绝；只允许 exact-pin Release Projection | Lifecycle contract；ADR published port | PASS |
| 用 eligibility/Snapshot/Release metadata 扩大权限 | 拒绝；metadata 仅为 ceiling，最终由 Execution View 收紧 | Authority Basis；Architecture | PASS |
| Execution Host 在 frozen Snapshot 内将 Supply A 换为 B | 拒绝；Host 只能请求 re-resolution，Resolver 必须生成 new Resolution/Snapshot/View | ADR authority matrix；Authority Basis；Architecture | PASS（架构边界） |
| SkillReleaseProjection 缺失时推进 no-Skill/direct Tool Core | 允许；Projection 只 Gate Skill new-binding | ADR implementation order；Roadmap split Gate | PASS（依赖闭包） |
| Registry/Release 更新改变正在运行的 Snapshot | 拒绝；必须产生新 Resolution/Snapshot/View | ADR Snapshot boundary；Roadmap Topic 4 Gate | PASS |
| v0.1 Method→Need 不再可重放 | 拒绝；保留 `maintainer-full` 与原 Schema/fixture | Method contract；diff allowlist；repository validation | PASS |

## 3. Architecture self-check

| 问题 | 当前答案 |
|---|---|
| 唯一 Capability supply selection owner | Research Control / Capability Resolver |
| Host 能否在 frozen Snapshot 内 rebind Supply | 否；只能执行 exact frozen input 或请求 re-resolution |
| Supply 失效是否需要新链 | 是；new Resolution → Snapshot revision → Resolved Execution View |
| no-Skill/direct Tool 能否在没有 Projection 时进入 Topic 4 Core | 能；Core 只以前置 Runtime Bundle/Profile 闭合 |
| Projection Gate 范围 | 只 Gate Skill-bearing Runtime path |
| Projection 缺失时 Skill new-binding | fail closed，且不回退完整 Lifecycle |
| Runtime bundle 是否读取 Evolution 对象 | 否；不读取 Need/Candidate/Evaluation/Lifecycle |
| CapabilityDiagnostic 当前定位 | future、local-by-default、optional seam；不自动上传或生成 Need |
| docs-only 范围 | 仅 `docs/`；不修改 src/Schema/Registry/fixture/tests/TASKS/STATUS |
| ADR-0019 状态 | `Proposed`；与当前 CHANGES_REQUESTED 后待 final review 的 R2 状态一致 |

## 4. Deferred executable evidence

以下必须由后续实现 PR 变成自动测试，本 docs-only PR 不伪造结果：

- Runtime import graph 不包含 Skill Need/Candidate/Evaluation/Lifecycle；
- explicit closure manifest 不使用目录输入或 `rglob(registry, examples)`；
- 无关、损坏的 Evolution Registry 文档不影响 Runtime bundle；
- no-Skill/direct Tool 在零 Skill refs 下生成合法 Resolved Execution View；
- Skill projection 缺失、stale、scope mismatch 或 digest mismatch 时 fail closed；
- Release/Registry 更新不改变已冻结 Snapshot/View；
- Execution Host 无 Supply reselect/rebind/automatic fallback capability，失败只能产生 re-resolution request；
- no-Skill/direct Tool/procedure/Adapter-Provider Core 在 Projection 完全缺席时仍可生成 View；
- gap/Diagnostic 路径没有 Need/Candidate/Promotion write capability。
