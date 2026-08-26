# M5 Evaluation Baseline Workstream（分阶段）

- 责任人（实现）：黄毅（GitHub 主名 `let778750-cpu`；昵称/界面名 `huangyi855`，同一账户）
- 必需审查人（Task owner，按 Issue #41 / PR #42 NORMALIZATION_MATRIX）：路诚钺
  （GitHub `Chengyue-Lu`）——M5-001～005 owner 为路诚钺，Human decisions R2
- Tasks：本阶段仅 `M5-003`（最小 Evaluation Manifest 与 baseline harness）；
  `M5-001/002/004/005` 不推进、TASKS 状态不变
- 基线：`develop@6b16129`（Issue #41 M-series 规范化合入后）
- 目标 base：`develop`
- 阶段分支：`agent/m5-evaluation-baseline`（从 `develop@6b16129` 独立切出——规范化后
  M5-003 依赖仅为 M9-002，与 M4 PR #39 解耦）
- 当前状态：M5-003 按规范化后的新定义实现完成——Evaluation Manifest 契约（含
  evidence classes 冻结与四臂可表达）、13 项固定指标词表、fixture 与 19 项测试
- 风险触发：评估口径属共享语义（Phase D 对齐）；M5-003 产出将被 M5-004/005 与
  Phase D Evaluation Manifest 消费

## 1. 分阶段口径（黄毅 2026-08-25 确认，与 #42 规范化一致）

本阶段只推进 M5-003。不选定真实案例、不运行案例、不做删减决定：M5-001/002 是人工
案例 Gate（#42 矩阵判定 KEEP BLOCKED），M5-004 依赖 M4-001..004 + M5-001/002/003，
M5-005 链在 M5-004 后。在维护者提供并批准案例边界之前，任何“完成”都不符合仓库的
诚实完成语义。

| Task | 当前状态 | 解锁条件 |
|---|---|---|
| M5-001 | BLOCKED | 人类维护者提供并批准证据综合案例边界（问题、来源、数据边界） |
| M5-002 | BLOCKED | 人类维护者提供并批准理论+仿真案例边界（模型、参数、Claim ceiling） |
| M5-004 | BLOCKED | M4-001..004 + M5-001..003 DONE，plus 一条被授权的真实执行路径 |
| M5-005 | BLOCKED | M5-004 产出数据完整；具名维护者做出至少一项保留/删除/停止决定 |

## 2. 依赖口径变化记录

- 旧定义（本 workstream 早期版本声明）：M5-003 依赖写作 `M2..M4`（里程碑级简写，
  治理脚本不展开校验），当时真实前置显式声明为 M2-001/002/005 + M4-001..004；
- Issue #41 / PR #42 规范化后：M5-003 依赖正式精化为 **M9-002**（DONE），验收新增
  “冻结……指标与 evidence classes”与四臂可表达要求。本分支按新定义实现，
  不再捆绑 M4 产物（fixture 仅引用 develop 既有文件）。

## 3. 三臂 ↔ 四臂映射（随 manifest 逐实验声明）

M5-003 的“单 Agent/轻量/多 Agent”三臂在 manifest 的 `arm_map` 中映射到 Phase D 四臂
词表；映射是每个 manifest 的一部分而非全局常量，两套口径不得各自演化。manifest 可
配置未被三臂映射引用的第四臂（如 mode-no-skill）以表达完整四臂对照——这正是新验收
“可表达 plain Agent、Tool、Mode no-Skill/direct-tool 与 candidate Skill 对照”的实现方式。

fixture 落位：single-agent→plain-agent；lightweight→plain-agent-tool；
multi-agent→mode-candidate-skill；另配置 mode-no-skill 臂表达完整四臂。

## 4. 指标口径

13 项固定指标词表（`FIXED_METRIC_SET` 单点定义，manifest 逐字复现，缺失/漂移/自造
阻断）：ROADMAP Phase D 九项（method violation、Claim overreach、provenance error、
counterevidence omission、human correction distance、context、cost、completion time 等）
合并执行恢复审计五项（遗漏率、返工、回查、H2 抽样失真、级联）。复用既有
`skill-evaluation` Schema 承载 Skill 配对证据（mode-candidate-skill 臂引用之），
不建平行评估框架、不在 lifecycle 内重建 benchmark framework。

## 5. evidence classes 冻结

`frozen_conditions.evidence_classes`（非空、去重、≥1 项）声明每次对照运行必须留下的
证据类别（fixture 示例：deterministic-check-report、execution-receipt、
claim-object-with-counterevidence、run-manifest、human-correction-log）。它与 Skill Need
本体内的 required evidence classes 语义对齐但不复制：Need 声明的是未来 trial/promotion
证据要求，manifest 冻结的是本次对照实验的证据条件，且不保存 trial 结果。

## 6. 非目标

- 不运行真实案例、不采集成本数据（M5-004）；
- 不做删减决定（M5-005）；
- 不建完整 benchmark/metric/experiment framework（Phase D 范围）；
- 不把评估结果写回 Skill Need；
- 不修改 TASKS.md 任务定义列；状态列变更遵循仓库惯例（本 PR：M5-003 READY→DONE）。

## 7. 证据

- 实现契约：[EVALUATION_MANIFEST_CONTRACT](../../../implementation/EVALUATION_MANIFEST_CONTRACT.md)；
- fixture：`examples/evals/manifests/EVAL-MANIFEST-M5-003-001.yaml`（`rwb eval check`
  输出 "fixed vocabulary verified (13 metrics)"，无阻断风险；四臂 + evidence classes）；
- 测试：`tests/test_evaluation_manifest.py` 19 项（词表漂移、臂映射、四臂允许、
  evidence classes 必填/非空、冻结池、schema 条件、交叉校验）；
- 仓库校验：`rwb validate examples registry` → validated=155 errors=0 warnings=0
  （develop 基线 154 + manifest fixture）。
