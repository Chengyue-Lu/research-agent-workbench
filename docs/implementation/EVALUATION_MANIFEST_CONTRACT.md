# Evaluation Manifest Contract (M5-003)

状态：Active implementation contract（M5-003；分阶段口径内本阶段唯一实现任务）

更新：2026-08-25

## 1. 目的与边界

为 M5 的"单 Agent / 轻量 / 多 Agent 对照"与 ROADMAP Phase D 的四臂对照
（Plain Agent / Plain Agent+Tool / Mode+no-Skill/direct-tool / Mode+candidate Skill）
提供统一的冻结实验条件契约，并固定指标评估表。

本契约只固定**比较条件与指标词表**，不记录任何实际运行结果（结果属于 M5-004 与
Phase D 的 Evaluation Record 范畴），不授权 live 运行，不把结果写回 Skill Need。

与 `skill-evaluation`（Skill 准入的 paired-same-input 证据）的关系：两者是不同对象。
Skill Evaluation 是某个候选 Skill 的配对证据；Evaluation Manifest 是系统级对照实验的
冻结条件框架。mode-candidate-skill 臂通过 `skill_evaluation_ref` 消费前者作为配置证据，
不复制其协议。

## 2. 契约内容

Schema：`schemas/v0.1.0/evaluation-manifest.schema.json`（document kind
`evaluation_manifest`）。

- **arm_map**：M5 三臂（`single-agent` / `lightweight` / `multi-agent`）各自映射到
  Phase D 四臂词表之一。映射是 manifest 的一部分，两套口径不得各自演化；
- **arms**：每个被引用的 Phase D 臂给出 `task_packet_refs`（fileRef）、
  `model_pool_ref`（fileRef，全部臂必须指向同一冻结池）、可选
  `capability_snapshot_ref` / `skill_evaluation_ref` / `budget`；
  `mode-candidate-skill` 臂必须携带 `skill_evaluation_ref`；
- **metric_set**：必须逐字复现 13 项固定指标词表（见 §3），缺失、定义漂移、单位或
  方向漂移、自造指标均阻断（`EVAL-MANIFEST-INVALID`）；
- **frozen_conditions**：`host`、`context_policy_ref`、`data_policy_ref`（fileRef）
  与 notes；
- **status**：`planned / armed / completed / superseded`。

CLI：`rwb eval check <manifest> [--root]` 执行 schema + 词表 + 臂映射 + 冻结条件 +
活引用校验；`rwb validate` 对仓库内 manifest 执行同样的交叉校验。

## 3. 固定指标词表（13 项）

| metric_id | 语义 | unit | direction | 来源 |
|---|---|---|---|---|
| method-violation | 违反冻结 Method Resolution 义务的步骤数 | count | lower-is-better | Phase D |
| claim-overreach | 超出 Claim ceiling 的声明数 | count | lower-is-better | Phase D |
| provenance-error | 溯源链未通过确定性检查的输出数 | count | lower-is-better | Phase D |
| counterevidence-omission | 丢弃已知反证的次数 | count | lower-is-better | Phase D |
| human-correction-distance | 人工修正次数 | count | lower-is-better | Phase D |
| omission-rate | 必需事实未浮现比例 | ratio | lower-is-better | 审计（遗漏率） |
| rework-count | 重做/再生工作单元数 | count | lower-is-better | 审计（返工率） |
| lookup-count | 已交付材料回查次数 | count | lower-is-better | 审计（回查率） |
| h2-distortion-rate | H2 压缩交接抽样失真比例 | ratio | lower-is-better | 审计（失真率） |
| cascade-rate | 错误向后级联比例 | ratio | lower-is-better | 审计（级联率） |
| context-loaded | 加载上下文总量 | characters-or-tokens | lower-is-better | Phase D |
| cost | 货币成本 | currency | lower-is-better | Phase D |
| completion-time | 完成墙钟时间 | minutes | lower-is-better | Phase D |

词表在 `src/research_workbench/evaluation/manifest.py` 的 `FIXED_METRIC_SET` 单点
定义；schema 与校验共同保证 manifest 逐字一致。

## 4. 非目标

- 不运行真实案例、不采集成本数据（M5-004，等待案例边界与授权执行路径）；
- 不做里程碑删减决定（M5-005，具名维护者决定）；
- 不建完整 benchmark/metric/experiment framework（Phase D 范围）；
- 不记录 trial/evaluation 实际结果，不写回 Skill Need；
- 不修改 TASKS.md 任务定义列（M5-003 依赖列保持 `M2..M4` 原文；真实前置的显式
  声明由 [workstream](../workstreams/huangyi/M5-EVALUATION-BASELINE/README.md) 承担）。

## 5. 示例与测试

- 示例：`examples/evals/manifests/EVAL-MANIFEST-M5-003-001.yaml`（fixture-only，
  三臂映射 plain-agent / plain-agent-tool / mode-candidate-skill，引用真实
  task packet、model pool、Skill Evaluation fixture 与 project protocol）；
- 测试：`tests/test_evaluation_manifest.py`（16 项）——词表缺失/定义漂移/自造指标、
  臂映射非法值/未配置臂/未引用臂、多池/无池拒绝、candidate-skill 臂缺证据被
  schema 拒绝、交叉校验漂移捕获、干净 fixture 通过。
