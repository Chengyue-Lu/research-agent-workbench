# 审计采纳矩阵

状态：提案。这里记录审计内容如何进入或不进入项目，不是实时任务状态，也不授权修改 Stable
Architecture、Schema 或 [`TASKS.md`](../../../TASKS.md)。

## SATISFIED：既有正式防线

- Runtime 结束不等于 Task contract 满足，Task 满足也不等于 Research acceptance；
- Main State 不是第二数据库，Handoff 不是 Evidence/Claim 的自动接受通道；
- Runtime 不得批准 Claim、Method、权限放宽或 Human Gate；
- 不允许自动 Provider fallback；audit replay 不等于模型逐比特重放；
- ADR-0010 的 API-first isolated baseline 已完成，外部调查不重开 Gate F。

这些内容保留为回归不变量；除非代码或测试与其冲突，不为同一语义重复建立 ADR。

## ADOPT：直接进入后续设计输入

- 把首次 Provider 请求和每次 Tool Result 回注都视为独立数据出口边界；
- enforcement matrix 明确 `preventive / detective / advisory / unknown`，并绑定测试证据；
- 外部 Agent 生态按 delegation、context isolation、routing、checkpoint/recovery、human
  intervention、observability、concurrency、failure semantics 比较机制；
- 风险 claim 必须绑定 commit、blob、测试或来源指纹，并保留 scope 与限定。

## ADAPT：需要结合 RWB 契约改造

- M8-003 后定义 `Resolved Execution View`，它由 Task、Method Resolution、Resolved Capability
  Snapshot 与执行限制派生，Runtime 不能反向改 Method；
- Skill binding 改为条件引用：Skill 路径引用真实 Assignment；no-Skill/tool-only 路径不生成
  虚假空 Assignment；旧 v0.1.0 工件只读兼容；
- Architecture Hold 只暂停 Runtime/Router/fallback/multi-agent/复杂恢复扩张和 Execution 重接入，
  不暂停 M8、安全修复、测试、Trace、hash/ref、archive 与 file-only verification；
- Receipt 分开记录 requested/observed model、实际工具与副作用、Trace 完整度；普通执行漂移
  告警，evaluation/benchmark 漂移阻断；
- PR #23 中 base-state pin、原子 closeout、file-only verification、provenance 的思路仅作洁净
  重写输入，不能继承实现或任务状态。

## DEFER：有价值但不进入当前主线

- salvage recovery 的完整状态机与迁移 schema；
- native-agent、multi-agent、自动 Router/critic/retry 和新的 Provider fallback；
- 新风险代码体系、Capability Report 的扩展 schema；
- streaming、multimodal、server-side tools 与隐藏平台 session 的接入；
- 外部生态比较的实现移植。

这些事项只有形成独立 Task、owner、acceptance 和写范围后才能进入开发。

## REJECT：不得进入项目真值

- 按框架名称照搬 Agent 架构，或让 Persona 覆盖 Method；
- 隐式 Skill/Tool/Agent 激活、静默 Provider fallback、伪造空 Assignment；
- 未经出口授权回注本地 Tool Result，或持久化完整原始 transcript；
- 未执行扫描却记录 `sensitive_data_detected: false`；
- 把 summary 自动升级为 fact，把 `--from-state`/hash pin 描述为 recovery；
- PR #23 对 TASKS 的状态和验收重写，或整体 merge/rebase-merge/批量 cherry-pick 该分支；
- 把共享页 GPT 回复、匿名 user 消息、会议整理稿或个人 working paper 直接提升为 SSOT。

## 正式采纳路径

1. 本 workstream 只固定证据和 disposition；
2. 两位维护者审查 claim 与限定；
3. 影响边界、Schema 或治理的不变量进入独立 ADR/Task；
4. 代码实现从当时最新 `develop` 洁净创建，提供负面测试和 clean-checkout 证据；
5. 只有目标 SSOT 的合并 commit 能把提案变成正式规范或任务状态。
