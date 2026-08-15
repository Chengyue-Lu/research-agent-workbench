# 路诚钺 Mode–Skill 分支计划

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 分支：`agent/mode-skill-selection-baseline`
- 状态：开发准备
- 日期：2026-08-15
- 目标节点：`K-MS-1 Mode–Skill Selection Baseline`

本目录是路诚钺当前分支的唯一专项计划入口。逐项状态仍以 [`docs/TASKS.md`](../../TASKS.md) 为准；稳定架构仍以 [`docs/ARCHITECTURE.md`](../../ARCHITECTURE.md) 和模块文档为准。本目录不建立第二套全局架构。

## 1. 当前任务

当前优先级调整为：

1. 先审计、整理并在必要时独立重写少量明确可用的 Skills；
2. 再用真实候选反推 Mode 边界、capability 词汇和 Skill 显式调用规则；
3. 同时定义这些 Skills 需要的外部 Tool 能力与调用边界；
4. 在开始真实 Agent with/without 评估前补齐 Attempt Archive/Trace validator；
5. 到达 `K-MS-1` 后暂停，做保留、拆分、降级和删除评审。

“搜集 Skills”不等于下载、安装或准入。“外部 Tool”也不等于在本分支实现 Provider/API。路诚钺负责方法、能力词汇、选择规则、数据/副作用边界和 fixtures；黄毅负责 API session、认证、Provider/Tool Adapter 实现和执行端测试。

## 2. 当前基线

截至 2026-08-15：

- 正式 Mode：2 个，`evidence-synthesis`、`simulation`；
- accepted Skills：3 个，`literature-evidence-extraction`、`simulation-vv`、`handoff-integrity`；
- 三个 accepted Skills 当前均标记 `project-original-unlicensed`，M0-007 仍阻断对外发布；
- 外部候选：24 个，其中 triage 4、discovered 2、reference 12、quarantine 2、rejected 4；
- 独立本地候选包：1 个，`claim-preserving-rewrite`；
- API 执行、真实模型调用和自动 Trace 捕获不属于本分支实现范围。

这些数量只描述库存，不是质量或进度指标。

## 3. 本目录

- [Skill 整理、独立重写与准入计划](SKILL_CURATION.md)
- [Mode–Skill–Tool 划分与调用计划](MODE_SKILL_TOOL_ROUTING.md)

实际 Skill 包不得在自身目录中复制本计划或增加 README/Changelog。Skill 包只保留 `SKILL.md`、必要的 `agents/openai.yaml`、`scripts/`、`references/` 和 `assets/`。

## 4. 实施阶段

| 阶段 | 工作 | 交付物 | 退出条件 |
|---|---|---|---|
| P0 计划冻结 | 固定库存、责任、来源和非目标 | 本目录、TASKS/导航更新 | 开发者能从本目录确定唯一下一动作 |
| P1 accepted 审计 | 审核 3 个 accepted Skills 的 trigger、non-trigger、工具、上下文和删除条件 | 3 份边界审计或等价 fixtures | 每个 Skill 有 retain/revise/deprecate 结论 |
| P2 候选整理/重写 | 只推进最多 2 个高价值候选，不复制未知许可实现 | 隔离 candidate package、lineage、checks、fixtures | 至少 1 个候选得到 reject/retain-reference/continue-trial 决定 |
| P3 Mode/Tool 路由 | 完成 Mode 决策卡、Tool capability cards 和 Skill 调用矩阵 | 路由表、capability 词汇、6–8 个 Task fixtures | no-Skill、tool-only、Skill、blocked、Human Gate 均可解释 |
| P4 Trace 前置 | 实现 M3-007/008 的最小 Envelope/Index/Event fixture 与 validator | 可回放 Attempt fixture | forward test 不再只依赖聊天或 Worklog |
| P5 对照评估 | 对选定候选做 baseline/with-Skill 与 H0/H1/H2 对照 | 脱敏输出、checks、Receipt/Trace、盲评、Decision | 证据足以支持保留、修改或停止，不自动 accepted |
| P6 节点评审 | 删除无增量价值机制并冻结 K-MS-1 | 评审 Decision、更新 Registry/TASKS | 到达停止点，不批量扩张 Mode/Skill/Tool |

P1–P3 可以先做离线文档、契约和 fixtures；P4 必须在任何声称“真实 Agent 效果”的 P5 之前完成。

## 5. 首批处理顺序

1. 审计三个 accepted Skills，特别检验 `handoff-integrity` 是否应退回确定性 Tool，而不是常驻 Skill。
2. 继续 `claim-preserving-rewrite` 的 adversarial 与 with/without 准备。
3. 从 `rc-papercheck`、K-Dense citation-management 和 backward-traceability 的问题定义中独立设计最小 `citation-claim-integrity` 候选；许可不明时不复制正文或脚本。
4. 从 `rc-giiisp-paper-search-apis` 只抽取 provider-neutral 的 `literature-search` Tool contract；在证明 Agent 工作流有增量价值前不创建搜索“大 Skill”。
5. `experiment-design` 等待 experiment Mode 的真实案例和方法审查；科学绘图继续隔离，只定义后续 Tool/Output 契约。

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

Tool capability card 的存放位置和 Schema 在首张卡完成后决定；没有真实消费者前不新建空 `registry/tools/`。

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
2. 三个 accepted Skills 完成 retain/revise/deprecate 审计；
3. 至少一个候选得到证据化去留决定，最多推进两个候选包；
4. 至少 6 个 Task fixture 能给出 Mode、capability、Tool、Skill/no-Skill、读取和 Handoff 选择理由；
5. 外部 Tool 的数据出口、权限、副作用、失败和验证边界可在调用前判断；
6. 实际 Agent 评估有完整 Attempt Trace，但主 Agent 默认只读取索引和 Handoff；
7. 没有修改 API 执行实现，没有把 fixture PASS 宣称为科研价值；
8. 至少删除、降级或合并一项没有净价值的 Skill/规则/字段，或形成可审计的“暂不删除”理由。

在项目 LICENSE 和候选来源许可未解决前，候选最高进入内部 `trial`，不能宣称可公开再分发。

达到这些条件后停止扩张并评审，不自动进入公开发布或大规模真实案例。
