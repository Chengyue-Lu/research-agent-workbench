# M5 真实案例与删减 Workstream（分阶段）

- 责任人：黄毅（GitHub 主名 `let778750-cpu`；昵称/界面名 `huangyi855`，同一账户）
- 必需审查人：路诚钺（GitHub `Chengyue-Lu`）
- Tasks：本阶段仅 `M5-003`（对照框架与固定指标表）；`M5-001/002/004/005` 不推进、
  TASKS 状态不变
- 基线：`develop@4ce83bcf286feb085f4807df40f110ca98057c0c`（M4 合并后另行记录新基线）
- 目标 base：`develop`
- 阶段分支：`agent/m5-evaluation-baseline`（M4 Stage PR 合并后创建）
- 当前状态：规划完成，等待 M4-001..004 DONE 后开工
- 风险触发：评估口径属共享语义（Phase D 对齐）；M5-003 产出将被 M5-004/005 与
  Phase D Evaluation Manifest 消费

## 1. 分阶段口径（黄毅 2026-08-25 确认）

本阶段只推进 M5-003：建立单 Agent/轻量/多 Agent 对照框架并固定指标与评估表。
不选定真实案例、不运行案例、不做删减决定。理由：M5 存在三个内生人工 Gate，
在维护者提供并批准案例边界之前，任何"完成"都不符合仓库的诚实完成语义。

各任务解锁条件：

| Task | 当前状态 | 解锁条件 |
|---|---|---|
| M5-001 | BLOCKED | 人类维护者提供并批准证据综合案例边界（问题、来源、数据边界） |
| M5-002 | BLOCKED | 人类维护者提供并批准理论+仿真案例边界（模型、参数、Claim ceiling） |
| M5-004 | READY | M5-001..003 DONE，plus 一条被授权的真实执行路径（M6 live conformance 解锁，或人工运行+文件化记录） |
| M5-005 | READY | M5-004 产出数据完整；具名维护者做出至少一项保留/删除/停止决定 |

## 2. M5-003 依赖的显式声明

TASKS.md 中 M5-003 依赖列写作 `M2..M4`（里程碑级简写，治理脚本不逐项展开校验）。
本 workstream 显式声明真实前置为：

```text
M2-001（Skill Registry 与 Resolver，DONE）
M2-002（Agent Profiles，DONE）
M2-005（handoff-integrity 检查，DONE）
M4-001..004（工件与复现，本阶段完成）
```

不列入：M2-003/M2-004（PARKED legacy Skill，非对照框架前置）、M4-005（DVC spike，
PARKED）。此声明供 PR 审查与后续 task-definition 决策参考；TASKS.md 依赖列不在本
workstream 修改。

## 3. 三臂 ↔ 四臂映射（M5-003 实现时固定）

M5-003 验收写"单 Agent/轻量/多 Agent 对照"，[ROADMAP](../../../ROADMAP.md) Phase D
写四臂对照（Plain Agent / Plain Agent+Tool / Mode+no-Skill/direct-tool /
Mode+candidate Skill）。两套口径在 M5-003 的 Evaluation Manifest 契约中正式映射，
不得各自演化。计划映射：

| M5-003 臂 | Phase D 臂 | 说明 |
|---|---|---|
| 单 Agent | Plain Agent | 无工具、无 Mode 约束的裸模型基线 |
| 轻量 | Plain Agent+Tool 或 Mode+no-Skill/direct-tool | 按案例 Task 的 Method Resolution 结果落位 |
| 多 Agent | Mode+candidate Skill（或 Mode+no-Skill 多 Profile） | 按当时 Skill lifecycle 状态声明实际臂位 |

最终映射以实现时的契约文档为准，并经路诚钺审查（Phase D 口径属其维护的
评估语义边界）。

## 4. 指标口径

固定指标合并两个来源，实现时逐一落位：

- ROADMAP Phase D：method violation、Claim overreach、provenance error、
  counterevidence omission、human correction distance、rework、context、cost、
  completion time；
- 执行恢复审计/调研笔记（Phase B dev plan C1）：遗漏率、返工率、回查率、
  H2 抽样失真率、级联率。

复用既有 `skill-evaluation.schema.json` 与 `evaluation/skill_evaluation.py` 扩展，
不建平行评估框架。

## 5. 非目标

- 不运行真实案例、不采集真实成本数据（M5-004）；
- 不做里程碑删减决定（M5-005）；
- 不建完整 benchmark/metric/experiment framework（Phase D 范围）；
- 不把评估结果写回 Skill Need（Need 只声明 criteria，不保存结果）；
- 不修改 TASKS.md 任务定义/依赖/验收列；状态列变更遵循仓库惯例。

## 6. 证据

实现开始后在本目录补 VALIDATION.md 与（若触发）RISK_LEDGER.md。
