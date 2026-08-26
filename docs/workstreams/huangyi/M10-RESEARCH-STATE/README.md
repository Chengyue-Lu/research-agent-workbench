# M10 Research State & Verification Workstream

- 责任人（实现）：黄毅（GitHub 主名 `let778750-cpu`；昵称/界面名 `huangyi855`，同一账户）
- 必需审查人（Task owner，按 Issue #41 / PR #42 与 PR #40 的 Phase C workstream）：
  路诚钺（GitHub `Chengyue-Lu`）——M10-001..003 与 M3-009 的 owner、R2 审查与
  最终表示接受均由其承担；黄毅按 phaseC 执行规范承担跨负责人执行事实接口审查
- Tasks：`M10-001`、`M10-002`、`M10-003`、`M3-009`（一个 R2 Stage PR 原子闭合）
- 基线：`develop@6b16129`（PR #40 定义 bounded 任务、PR #42 规范化之后的 develop）
- 目标 base：`develop`
- 阶段分支：`agent/m10-research-state`
- Authority basis：[Issue #38](https://github.com/Chengyue-Lu/research-agent-workbench/issues/38)
  的 `R2 architecture review — ACCEPT`（授权 bounded implementation）
- 当前状态：实现完成——四个 candidate Schema、closure 校验、fresh actor 门与两个
  bounded case fixture；等待 R2 跨负责人审查
- 风险触发：R2——Research State meaning、Human Decision、Failure、Method Trace 与
  Topic 5 Gate 语义面

## 1. 目标

按 PR #40 冻结的 bounded 定义实现 Phase C 最小实现（见
[实现契约](../../../implementation/PHASE_C_RESEARCH_STATE_CONTRACT.md)）：

1. **M10-001**：最小 durable Research State composition candidate——exact ref/revision/
   pin 闭合、supersedes 单调 lineage、open item（unknown/assumption 轻量表示）；
2. **M10-002**：Attempt/Research Failure 语义与独立 lineage——learned_result/
   revisit_condition 强制、execution outcome 与 research failure 分离、from-State 引用；
3. **M10-003**：bounded continuity/verification Gate——两个 bounded case 的 staged 新进程
   fresh actor 只读 compact State + Method Trace + 约定路径文件，回避已知失败路径；
4. **M3-009**：Method Trace v0.1——ref-only 事件账本、六族事件闭集与必备 ref、
   sequence 连续性、与 Execution Trace 分层。

## 2. 非目标（与 Issue #38/PR #40 逐条对齐）

- 不建知识图谱、数据库、通用 workflow DAG；Frontier 保持 derived projection
  （本版未建独立对象）；
- 不改 `research-object`/`claim`/`decision` 既有 Schema identity；
- 不实现 Topic 5（Handoff/recovery/context rollover）、不实现 Runtime/Provider 任何
  内容（M11 范围）；
- 不自动 retry/reopen/replan、不自动 Skill Need/Claim promotion；
- Gate PASS 不等于 Phase C closeout，不等于 Topic 5 解冻。

## 3. 实现表示决策（bounded candidate，待 R2 接受）

| 概念 | 本版表示 | 理由 |
|---|---|---|
| Research State | 独立 `research_state` 文档（id/revision/supersede lineage + entries + open_items） | durable identity/revision/cross-Attempt 引用是真实需求 |
| Failure | 独立 `research_failure` 文档（learned/revisit 强制） | ROADMAP 明确 universal minimum |
| Unknown/Assumption | State 内 `open_items[]` 轻量 item | 无独立 lifecycle 证据（least-powerful） |
| Contradiction | 既有 Evidence–Claim counterevidence 关系 | kernel 已表达 |
| Frontier | 未实现独立对象 | derived projection 可由 open_items + revisit_refs 派生 |
| Human Decision | 独立 `human_decision_record`（可选挂 kernel Decision 对象） | provenance-bearing 需要独立 identity；不平行重建 Decision |
| Method Trace | 独立 `method_trace` 文档，ref-only 事件 | 与 Execution Trace 分层，防止后者继续膨胀 |

## 4. 与 Phase C workstream 分工的关系

PR #40 建立的 `chengyue-lu/PHASE-C-RESEARCH-STATE/` 声明实现分支为
`codex/phase-c-implementation`（路诚钺侧）。经黄毅与项目负责人确认（2026-08-26），
本轮由黄毅按本地 phaseC 执行规范在 `agent/m10-research-state` 实现，PR #40 workstream
的 planning authority（Issue #38 ACCEPT）不变；若路诚钺侧 codex 分支已存在重叠实现，
以本 PR 为审查基础由其裁定合并策略。

## 5. 证据

- [验证证据](VALIDATION.md)：全量测试、gate 输出、仓库校验、任务级对抗用例；
- [风险台账](RISK_LEDGER.md)：R2 语义风险与缓解；
- 实现契约：[PHASE_C_RESEARCH_STATE_CONTRACT](../../../implementation/PHASE_C_RESEARCH_STATE_CONTRACT.md)。

## 6. 停止条件

四个任务的验收证据齐备、CI 通过、路诚钺 R2 审查完成；任何需要放宽 Gate 语义、
改 accepted Schema identity 或提前实现 Topic 5 的发现登记风险台账并停止，不在本分支扩张。
