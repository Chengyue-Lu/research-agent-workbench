# 第二轮架构审计吸收记录

日期：2026-08-20

状态：内部架构输入的吸收决定；不是外部项目事实核验报告

## 1. 输入边界

本轮输入来自[`second-round-audit/`](second-round-audit/README.md)归档的外部参照清单、RWB 改进
建议、Issue 草案和路线图。按本次任务要求，
没有重新访问或验证其中外部项目、论文、版本、发布日期或能力声明。因此这些外部条目不能成为
Runtime compatibility、产品能力或科研效果的正式证据。

正式吸收的是内部设计判断，而不是对任何外部项目的背书。

## 2. 直接吸收

- RWB 定位为 method-aware research control plane，而非另一个 Agent Runtime；
- 五平面稳定性方向：Integrity、Research State、Method、Capability/Strategy、Execution；
- `Method Resolution` 作为 Task 到 Execution 的 provider-neutral 中间语义；
- Mode/Protocol/Strategy/Skill/Tool/Capability 的正交边界；
- Research State 比 conversation/runtime state 生命周期更长；
- Failure、Unknown、Contradiction、Frontier 和 revisit condition 是正式研究资产候选；
- Trace 分为 Execution/Archive 与 Method decision 两层；
- Skill、Tool、Method 和 Strategy 采用 evaluation-driven、human-governed evolution；
- Plain/no-Skill/tool-only 永久保留为基线；
- Execution/API 在共享 Method/Capability/Trace 契约稳定后重新接入。

上述决定由 [ADR-0016](../decisions/0016-METHOD-AWARE-RESEARCH-CONTROL-PLANE.md) 固定，实施依赖见
[架构演进路线图](../ROADMAP.md)。

## 3. 延后

- 统一 Research Strategy 实现；
- 自动 source mining、Skill generation/repair/merge；
- 完整 Claim composition calculus；
- 外部 benchmark Adapter；
- 大规模 Research State 查询层或数据库。

这些方向只有在 Phase A–D 的真实消费者和 baseline 证据出现后才进入 Task。

## 4. 明确不吸收

- 端到端自动完成整个课题作为成功条件；
- 默认 tree search、tournament、debate 或多 Agent；
- 用 Blueprint 或固定阶段 DAG 统一不同研究模式；
- 自建大规模 Tool/MCP 仓库；
- 自动发现后直接准入 Skill/Tool/Method；
- 把报告集合或长期聊天当作 Research State。

## 5. 对审计草案的校正

- 评测 harness 对应草案 Issue 14，不是 Issue 11；
- M3-008 保留为可观察执行 Trace 基线，Method-aware Trace 使用后续独立 Task，避免覆盖已冻结边界；
- Mode v0.2 在完整 migration framework 前必须先有最小、可复现的 migration seam；
- 草案 PR 编号只是占位，不进入正式任务标识；
- 实时状态只写入 `TASKS.md`，不在路线图和审计材料复制维护。
