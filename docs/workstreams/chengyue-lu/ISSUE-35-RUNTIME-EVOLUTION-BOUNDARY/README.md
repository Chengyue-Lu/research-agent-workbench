# ISSUE-35 Runtime / Evolution Boundary

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 跨负责人审查：黄毅（GitHub `let778750-cpu`）
- Audit ID：`ISSUE-35`
- 风险：R2 authority / Runtime ownership / Skill admission
- 审计基线（历史）：`develop@aeca805e4dbb43b356c7f6da8c1262c9f6220569`
- 目标 base：`develop`
- 工作分支（历史）：`codex/issue-35-runtime-evolution-boundary`
- 状态：PR #36 已以 `b75900f` 合入 `develop` 并接受 ADR-0019；后续 M11-001～004 Core 已实现该
  no-Skill/direct-Tool Runtime 边界，M11-005/006 optional Skill extension 仍 PARKED
- 对应讨论：[Issue #35](https://github.com/Chengyue-Lu/research-agent-workbench/issues/35)
- 前置集成：[PR #33](https://github.com/Chengyue-Lu/research-agent-workbench/pull/33)

## 1. 风险触发与目标

PR #33 已把 Phase B 收口为 structural foundation，但现有 repository-wide consumer 仍会递归加载
`registry/`、`examples/` 并执行 Skill Need/Lifecycle/Gate 完整闭包。若把它当成 Topic 4 Runtime API，
Runtime 就会依赖 Skill Evolution 内部对象，no-Skill/direct Tool 也无法获得真正的最小部署闭包。

本 R2 workstream 冻结：Capability-first Runtime 内环、可选 Maintainer Evolution 外环、两个单向端口、
发布投影、consumer profiles 和双方 authority ceiling。实现结论由
[ADR-0019](../../../decisions/0019-OPTIONAL-MAINTAINER-SKILL-EVOLUTION-OUTER-LOOP.md) 承载。

## 2. 审计基线

以下矩阵固定 PR #36 设计时点，不提供当前 implementation maturity；当前覆盖见
[`STATUS.md`](../../../STATUS.md)，实时 Task 状态见 [`TASKS.md`](../../../TASKS.md)。

PR #33 最终 head `4d86c4b6d1c2acf94e87a833bfe38ba57a15ffbc` 与合并后的 `develop@aeca805`
具有相同 tree `de6ff063baa4667cd1cc383810cbf44656eeb85f`。本 workstream 不回滚或重开 PR #33，
只以前向 ADR 限定其 Runtime 解释范围。

| Compatibility Gate | `aeca805` 现状 | 本 workstream 决定 |
|---|---|---|
| Runtime 不依赖 Evolution | 未满足 | 定义独立 `runtime-bundle` profile |
| consumer 不递归扫描整仓 | 未满足 | future Runtime 只接受显式 closure manifest |
| no-Skill/direct Tool 零 Skill | 仅 structural replay | Topic 4 必须提供 supply-neutral Execution View |
| Skill Runtime 不解析完整 Lifecycle | 未满足 | 只消费 `SkillReleaseProjection` |
| gap/failure 不自动创建 Skill Need | 已满足 | 提升为 authority invariant |

这些结果不否定 PR #33 的 structural foundation，也不把 Issue #35 扩成 Runtime 重写。

## 3. 读写范围

允许读取：

- repository guidance、Development、Architecture、Roadmap；
- Skill System、Method/Capability/Need/Lifecycle implementation contracts；
- ADR-0013/0016、Phase B workstream、PR #33 最终差量；
- Issue #35 指向的 primary external references。

允许写入：

- `docs/ARCHITECTURE.md`、`docs/ROADMAP.md`；
- ADR、相关 module/implementation contract；
- 本 workstream、owner index 与 Phase B 的前向澄清注记。

禁止写入：

- `src/`、`schemas/`、`registry/`、`examples/`、fixtures 与 tests；
- `docs/TASKS.md`、`docs/STATUS.md`、M9 完成状态；
- 黄毅的 workstream 或任何其他本地 clone/worktree。

## 4. 决定产物

- ADR-0019：双环、单向端口、authority matrix、兼容边界与实施顺序；
- Stable Architecture / Skill System：Capability-first Runtime 的正向系统模型；
- Method/Capability/Need/Lifecycle contracts：`maintainer-full` 与 future `runtime-bundle` 的读取边界；
- Roadmap Topic 4 Core Gate 与独立 Skill Runtime Extension Gate：最小闭包、零 Skill、条件发布投影与
  frozen-view 要求；
- [Authority Basis](AUTHORITY_BASIS.md)、[Risk Ledger](RISK_LEDGER.md)与[Validation](VALIDATION.md)。

## 5. 外部证据使用边界

ADR 的 Kubernetes、OPA、OCI、TUF、in-toto 与 Toolformer 链接均为 2026-08-25 检索的 primary source，
只提供设计类比。未复制外部对象、术语或代码，也不以外部项目证明本项目的 authority 结论。规范真值
仍来自本仓库 ADR、契约及具名跨负责人审查。

## 6. PR #36 非目标与未证明内容（历史范围）

本 workstream 不实现或证明：

- Release Projection Schema/publisher、Runtime profile/consumer 或 Resolved Execution View；
- live Provider、真实账户/模型、API session 或 end-to-end execution；
- Skill 科研净增量、Trial/Evaluation/Human Decision 系统；
- telemetry、中央 Registry、数据库、自动安装/升级、routing/fallback 或本地自学习；
- PR #33 最终 GitHub CI/reviewDecision 的独立复核。

## 7. 接受 closeout

本分支只完成 docs-only R2 设计。Cross-owner architecture acceptance 已在
[PR #36 APPROVE](https://github.com/Chengyue-Lu/research-agent-workbench/pull/36#pullrequestreview-5012526099)
完成，绑定 `c09dd69d9a8f7d1c4f70c93e6909a61e72d52e79`。ADR-0019、decisions index、Authority Basis 与
workstream 状态已进入 Accepted state-sync。PR #36 合并前使用的 final governance Gate 为：

1. final diff 只包含预期的状态同步、PR metadata 同步与完整 Capability chain wording；
2. ADR、index、Authority Basis 与 workstream 状态一致；
3. Runtime owner 黄毅对 final state diff 完成具名 reconfirmation；
4. 最新 head GitHub CI 全绿。

PR #36 停止于文档边界；其后实现分为两条 lane：Runtime Bundle/Profile 是 Topic 4 Core 前置，稳定后 Core 可为
no-Skill、direct Tool、procedure 与 Adapter/Provider 独立实现 supply-neutral Resolved Execution View；Skill
Release Projection/Publisher 是可并行的独立 Extension，只 Gate Skill-bearing binding。Projection 缺失时
Skill new-binding fail closed，但不阻塞 Core。Capability Diagnostic/feedback bridge 保持 PARKED，等待
Phase C Failure/Trace 与 privacy 语义稳定。

## 8. Post-integration continuation

PR #36 的 state-sync、cross-owner reconfirmation 与 CI 已在合并前完成。后续 M11-001～004 已把
Runtime Bundle、supply-neutral View、Thin Host 与 generic closeout 实现为 bounded Core；这不等于 live
Provider 或 ordinary-user E2E。SkillReleaseProjection/publisher 与统一 Skill supply mapping 仍由
M11-005/006 保持 PARKED，只 Gate Skill new-binding。Capability Diagnostic/feedback bridge 也没有因此
自动启动。
