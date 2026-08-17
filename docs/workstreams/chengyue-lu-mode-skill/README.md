# 路诚钺 Mode–Skill 分支计划

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 分支：`agent/mode-skill-selection-baseline`
- 状态：Mode-derived 与 project-internal 两条 Skill Need 路线并行
- 日期：2026-08-18
- 目标节点：`K-MS-1 Mode–Skill Selection Baseline`

本目录是路诚钺当前分支的唯一专项计划入口。逐项状态仍以 [`docs/TASKS.md`](../../TASKS.md) 为准；稳定架构仍以 [`docs/ARCHITECTURE.md`](../../ARCHITECTURE.md) 和模块文档为准。本目录不建立第二套全局架构。

## 1. 当前任务

当前优先级调整为：

1. 先为 `evidence-synthesis` 与 `simulation` 建立可选 Action、失败、Artifact、机制和 Human Gate 地图；
2. 对每个 action 优先判断 Mode/Task/Tool/Human 是否足够，只有非平凡语义复用缺口才建立 Skill Need；
3. 外部候选和 GLM 采集结果只作为按 Need 检索的 reference inventory，不再直接形成重写清单；
4. 用 Mode-derived Need 反查 capability、Tool card、Skill 和 no-Skill 路由；
5. Mode 需求确认后才版本化修订或退役三个 0.1.0 Skill 原型；
6. 真实 Agent with/without 评估仍以前置 Attempt Archive/Trace validator 为条件。

与上述 Mode-derived 路线并行，为 Agent 交接、H2 转移、受控恢复和 Human Gate Brief 建立少量
project-internal Need 占位。它们先比较 Protocol/template/Tool 基线，不全局加载，也不改变 Mode。

“搜集 Skills”不等于下载、安装或准入。“外部 Tool”也不等于在本分支实现 Provider/API。路诚钺负责方法、能力词汇、选择规则、数据/副作用边界和 fixtures；黄毅负责 API session、认证、Provider/Tool Adapter 实现和执行端测试。

## 2. 当前基线

截至 2026-08-17：

- 正式 Mode：2 个，`evidence-synthesis`、`simulation`；
- accepted Registry 中仍有 3 个 0.1.0 原型，历史 Assignment 保持可解析；它们尚未证明真实方法增量，不作为新需求的默认答案；
- 三个 accepted Skills 当前均标记 `project-original-unlicensed`，M0-007 仍阻断对外发布；
- 候选 Registry：73 个；第二批 GLM Attempt 另有 14 个 Tool/MCP 和 6 个 Skill 元数据，均只作 reference inventory，未进入 Registry；
- 独立本地候选包：1 个，`claim-preserving-rewrite`；
- API 执行、真实模型调用和自动 Trace 捕获不属于本分支实现范围。

这些数量只描述库存，不是质量或进度指标。

## 3. 本目录

- [Skill 整理、独立重写与准入计划](SKILL_CURATION.md)
- [Mode Action Requirements](MODE_ACTION_REQUIREMENTS.md)
- [项目内生协议 Skill 规划](PROJECT_INTERNAL_SKILLS.md)
- [项目内生 Handoff Skill Need Dossiers](PROJECT_INTERNAL_SKILL_DOSSIERS.md)
- [Accepted Skill 重叠审计](ACCEPTED_SKILL_OVERLAP_AUDIT.md)
- [首轮四份 Skill 候选 Dossier（历史探索）](SKILL_CANDIDATE_DOSSIERS.md)
- [Skill 来源搜集、隔离与机器/人工筛选](SKILL_SOURCE_INTAKE.md)
- [一方 Skill 逐项筛选结论](FIRST_PARTY_SKILL_TRIAGE.md)
- [社区 Skill 人工筛选结论](COMMUNITY_SKILL_TRIAGE.md)
- [Mode–Skill–Tool 划分与调用计划](MODE_SKILL_TOOL_ROUTING.md)
- [Action-driven Tool Capability Cards](TOOL_CAPABILITY_CARDS.md)
- [Task–Mode–Action–Mechanism Routing Fixtures](TASK_MODE_ACTION_ROUTING_FIXTURES.md)
- [Skill 诊断性困难任务测试计划](DIAGNOSTIC_FORWARD_TESTING.md)
- [`claim-preserving-rewrite` Stage 1 诊断结果](STAGE1_DIAGNOSTIC_RESULTS.md)

实际 Skill 包不得在自身目录中复制本计划或增加 README/Changelog。Skill 包只保留 `SKILL.md`、必要的 `agents/openai.yaml`、`scripts/`、`references/` 和 `assets/`。

## 4. 实施阶段

| 阶段 | 工作 | 交付物 | 退出条件 |
|---|---|---|---|
| P0 计划冻结 | 固定库存、责任、来源和非目标 | 本目录、TASKS/导航更新 | 开发者能从本目录确定唯一下一动作 |
| P1 Mode action 推导 | 为两个正式 Mode 建立 Action–Failure–Artifact–Gate 地图 | `MODE_ACTION_REQUIREMENTS.md` | action 不形成全局 DAG，机制选择可解释 |
| P2 Need 与机制分配 | 每个 action 判定 Mode/Task/Tool/Skill Need/Human | Need specs、capability gaps | no-Skill 是正常结果；每个 Mode 首批 Need 不超过两个 |
| P3 路由与 Tool 卡 | 按 Need 完成路由 fixture 和 provider-neutral Tool capability cards | 路由表、Tool cards、6–8 个 fixtures | tool-only、Skill、blocked、Human Gate 均可解释 |
| P4 原型迁移 | 按 Mode action 重审三个 0.1.0 Skill | 新版本或 deprecation/migration Decision | 不原地改义，不因历史 accepted 默认保留 |
| P5 Trace 与对照评估 | 完成最小 Trace 后才做 no-Skill/direct-tool/compact trial | Trace、脱敏输出、盲评、Decision | 证据能区分机制增量，不自动 accepted |
| P6 节点评审 | 删除无增量价值机制并冻结 K-MS-1 | 评审 Decision、更新 Registry/TASKS | 到达停止点，不批量扩张 Mode/Skill/Tool |

P1–P4 可以先做离线文档、契约、迁移设计和 fixtures；P5 的任何真实效果宣称仍必须等待 M3-008。

Project-internal 路线与 P3/P4 并行：先为 `NEED-INT-COMPACT-HANDOFF` 和
`NEED-INT-AUDITED-TRANSFER` 建 direct baseline 与 failure fixture，最多同时维护两个 active Need；
其真实对照同样等待 M3-008，不成为全局默认 Skill bundle。

截至 M7-013，两项 direct baseline、compact dossier 和诊断 fixture 已完成，结论均为
`hold-no-skill`；project-internal 路线等待独立 Task family 与 M3-008 Trace 后再决定是否进入 M7-014。

截至 M7-002/003/008，五张 Tool cards 与八个路由 fixtures 也已完成并通过覆盖测试。P3 到达停止点；
当前唯一下一任务为 M7-004，按这些 action/route 版本化处理三个 0.1.0 Skill 原型。

## 5. 首批处理顺序

1. 完成两个正式 Mode 的 trigger/non-trigger/组合/no-Mode 决策卡。
2. 完成 `MODE_ACTION_REQUIREMENTS.md`，先确认 action 和机制分配，不创建 Skill 包。
3. 以 `need_id` 而非外部来源建立最多四个 Need dossier；每个 Mode 首批最多两个。
4. 只为已确认 action gap 建立 Tool capability card；具体 MCP/API 仍只是 Adapter 候选。
5. Mode/Need/Tool 路由稳定后，版本化迁移三个 0.1.0 Skill 原型。
6. 新的真实 forward test 等待 M3-008；此前的 candidate dossier 和 GLM 结果保留为历史/reference，不触发重写。
7. 并行为前两个 project-internal Need 建 compact dossier；Task/Schema/Tool 足够时记录 `no-Skill` 并停止。

## 6. 预期写入位置

进入具体 Task 后再创建对应路径，不预建空目录：

```text
skill-lab/candidates/<skill-id>/        # 非发现、非 accepted 的独立候选包
registry/skills/candidates/<skill>.yaml # 候选 manifest
registry/skills/candidates.json         # 候选索引和决定
registry/modes/                         # 仅在 Mode 通过准入后更新
examples/mode-skill-routing/            # 路由与 no-Skill/tool-only fixtures
work/<task>/<attempt>/                  # 实际评估的完整 Attempt Archive
```

首批 Tool capability card 保存在本专项文档中；在 Runtime 出现机器消费者前不创建 `registry/tools/`
或公共 Schema，具体 Adapter 仍由黄毅在独立范围内实现和验证。

## 7. 分支边界

允许修改：

- `.agents/skills/`、`skill-lab/candidates/`；
- Mode/Skill manifests、capability 词汇和 resolver 相关 fixtures/tests；
- Tool capability contract、调用策略和本地确定性脚本；
- Trace 的共享 Schema/validator，但需与黄毅确认接口影响；
- 本工作流文档与 TASKS/Changelog。

禁止修改：

- Provider Adapter、凭据、模型池和真实 API conformance；
- API session/tool loop、自动 fallback 或模型 Router；
- 未经审查的外部 Skill 原文和脚本；
- 为填满分类表而批量新增 Mode；
- 以更多 reviewer Agent 代替定义、确定性检查或人工 Gate。

## 8. K-MS-1 完成条件

1. 两个正式 Mode 有 trigger/non-trigger/组合/no-Mode fixtures；
2. 两个 Mode 的 Action–Failure–Artifact–Gate 与最小机制分配完成；
3. 每个 Mode 首批 Skill Need 不超过两个，且能解释 no-Skill/direct-tool 基线；
4. 至少 6 个 Task fixture 能给出 Mode、action、Tool、Skill Need/no-Skill、读取和 Handoff 选择理由；
5. 已确认 Tool gap 的数据出口、权限、副作用、失败和验证边界可在调用前判断；
6. 三个 0.1.0 Skill 原型有按 Mode action 得出的保留、拆分、降级或版本化迁移决定；
7. 没有新增正式 Mode、修改 API 执行实现或把文档/fixture PASS 宣称为科研价值；
8. 外部来源只通过 Need dossier 被引用，没有来源候选直接成为开发清单。
9. project-internal 候选有明确 direct baseline、project-only 边界和最多两个 active Need，且没有把强制 Protocol/Schema/Trace 规则降级成 Skill。

在项目 LICENSE 和候选来源许可未解决前，候选最高进入内部 `trial`，不能宣称可公开再分发。

达到这些条件后停止扩张并评审，不自动进入公开发布或大规模真实案例。
