# Skill 整理、独立重写与准入计划

## 1. “明确可用”的定义

候选只有同时满足下列条件，才进入独立重写或 trial 准备：

1. 解决一个可复用、可举例的具体研究动作，而不是泛化的“深入思考”或全流程代理；
2. trigger、non-trigger、缺输入和停止条件可以写成 fixtures；
3. 输入、输出、Claim ceiling 和 Human Gate 明确；
4. 相比确定性 Tool 或普通 Task 指令有潜在增量价值；
5. 所需 Tool、权限、网络、数据出口和副作用可以在执行前判断；
6. 有确定性 checker、可复核 artifact 或有界人工判据；
7. Skill 正文足够短，并能通过渐进披露把长参考和脚本移出上下文；
8. 来源、许可、哈希和重写 lineage 明确；
9. 删除它不会要求改科研内核或执行 Runtime。

缺少任一硬条件时，状态保持 `discovered/reference/triage/quarantine/rejected`，不能因为“看起来完整”进入 accepted。

仓库当前没有项目 LICENSE，现有原创 Skills 也标记为 `project-original-unlicensed`。在 M0-007 关闭前，新候选最多进入内部 `trial`；“独立重写”不能绕过来源许可或项目发布许可。

## 2. 来源与许可

来源优先级：

1. 仓库现有 accepted Skills 和本地候选的真实失败/使用记录；
2. 用户提供、已固定哈希的归档和已有 Candidate Registry；
3. 官方 Skill 格式与工具文档，只用于接口和结构规范；
4. 有明确版本、许可证和维护状态的开源 Skill/方法实现；
5. 论文或工具文档中的方法要求，用于独立实现 checker 或流程。

每次新增来源先做 metadata-first intake：记录 locator、revision/hash、license、入口数量、脚本/二进制/安装/网络/凭据/删除信号，再决定是否读取正文。允许把固定版本的代表性目录批量下载到忽略 Git 的隔离区，以降低单一来源和单次模型判断偏差；禁止批量安装、执行、导入或直接注册整个 Skill 仓库。统一流程与首批快照见[Skill 来源搜集、隔离与筛选](SKILL_SOURCE_INTAKE.md)。

未知许可或禁止复制时：

- 只记录它暴露的问题、输入/输出需求和风险模式；
- 从本项目 Task/Mode/Artifact 契约重新写独立规格；
- 不复制句子、示例、脚本结构或资源文件；
- lineage 标记 `requirements-derived` 或 `reference-only`，不能写成 vendored；
- 无法证明独立性时保持 reference，不进入可执行候选。

## 3. 独立重写标准

每个实际 Skill 包遵循：

```text
<skill-id>/
├── SKILL.md
├── agents/openai.yaml          # 需要平台 UI 元数据时
├── scripts/                    # 仅放重复、脆弱或需确定性的操作
├── references/                 # 只在当前步骤需要时读取
└── assets/                     # 输出使用，不加载为指令
```

约束：

- 名称使用小写字母、数字和连字符，优先采用动词/动作导向名称；
- `description` 同时说明能力、触发场景和明确不适用场景；
- `SKILL.md` 使用祈使式，保留核心流程，目标远低于 500 行；
- Skill 包内不创建 README、安装指南、Changelog 或重复说明；
- references 只保持一层，由 `SKILL.md` 说明何时读取；
- scripts 必须实际运行测试，不能让 Agent 重复生成同一脆弱代码；
- `agents/openai.yaml` 必须与 `SKILL.md` 同步；
- Skill 不授予工具或权限，只声明 required/optional Tool capabilities；
- 外部工具失败必须暴露 capability gap，不允许 Skill 静默换服务或上传数据；
- 重写后使用新内容/包哈希，旧 Assignment 不自动迁移。

“润色外部 Skill 文案”不是独立重写。独立候选必须能从本项目的 Task、Mode、Tool 和输出契约解释每条核心指令。

## 4. 每个候选的工件链

```text
source intake
  → triage memo
  → rewrite specification
  → isolated candidate package
  → trigger/non-trigger/boundary/adversarial fixtures
  → deterministic reports
  → baseline/with-Skill forward test
  → blind human review
  → reject / retain-reference / continue-trial / accept Decision
```

最小 dossier：

- candidate/source ID、revision/hash、license；
- 问题定义、适用/不适用 Mode、capabilities；
- 与现有 Skill、Tool 和基础 Task 指令的重叠；
- required/optional Tools、数据出口与副作用；
- context cost 和需要按需读取的 references；
- 成功、non-trigger、缺输入、边界和恶意输入案例；
- checker/人工 criteria；
- 保留、拆分、降级或删除条件。

## 5. accepted Skills 先行审计

首轮结果保存在 [Accepted Skill 重叠审计](ACCEPTED_SKILL_OVERLAP_AUDIT.md)，但 ADR-0013
之后这些结论只作为输入。`literature-evidence-extraction` 与 `simulation-vv` 不再直接
修补，而是先映射到 [Mode Action Requirements](MODE_ACTION_REQUIREMENTS.md)；
`handoff-integrity` 的 Tool/Trace/H2 迁移方向保持不变。

| Skill | 当前判断 | 本轮必须回答 | 可能结果 |
|---|---|---|---|
| `literature-evidence-extraction` | 边界清楚，最可能继续保留 | bounded extraction 与 search/synthesis 的非触发是否稳定；Transfer Manifest 是否应仅由 H2 触发 | retain 或缩短 Handoff 步骤 |
| `simulation-vv` | 有明确方法价值 | `simulation` 与尚未准入的 `engineering-validation` 标签如何处理；checker 与方法指令的增量分别是什么 | retain/revise，或拆出确定性 Tool |
| `handoff-integrity` | 最可能与确定性 CLI 重复 | 直接运行 checker 是否已经覆盖普通任务；语义 Skill 仅在 H2 是否有价值 | deprecate Skill wrapper、保留 Tool；或缩为风险触发 integrity Skill |

审计必须包含 no-Skill/direct-tool 基线。accepted 不是永久状态；若只剩脚本调用说明，应优先把脚本作为 Tool/checker，而不是保留一个上下文 Skill。

## 6. 首批候选队列

四份来源候选判断保存在[首轮 Skill 候选 Dossier](SKILL_CANDIDATE_DOSSIERS.md)，作为历史
探索与 reference。当前选择 0 个来源候选直接重写；后续 dossier 以 `need_id` 为主键，
汇总多个来源、真实失败、Tool 基线与学科变体。

| 优先级 | 候选/来源 | 本轮动作 | 不做什么 |
|---|---|---|---|
| P0 | `rwb-claim-preserving-rewrite` | 探索性三臂 Stage 1 已暂定 `revise-compact`；修复 checker 后只复验 CPD-02/03，再决定 continue-trial/retain-reference/reject | compact 在 2 个区分案优于 full；不把单次合成测试或表层 checker 当作语义等价证明 |
| P0 | `rc-papercheck` + citation-management/backward-traceability 问题模式 | 独立设计最小 `citation-claim-integrity`；优先确定性 citation/claim locator | 不复制未知许可脚本，不把科学正确性变成 PASS |
| P1 | `rc-giiisp-paper-search-apis` | 只定义 provider-neutral `literature-search` Tool capability 和结果归一化/失败语义 | 不绑定单一服务，不在本分支实现凭据/API |
| P2 | `rc-experiment-design` | 保持 triage，等待真实 experiment Task 与统计方法审查 | 不先建空 experiment Mode 或自动接受功效结论 |
| P2 | scientific image generation | 仅保留 figure spec、lineage、quality gate 需求 | 不执行硬编码 HTTP、外部上传或修复脚本 |
| reference | skill-critic/thesis-audit 等 | 只借用 trigger cases、coverage denominator 等评估结构 | 不引入常驻 critic/supervisor |

首批最多同时维护两个新 candidate packages。只有一个候选通过下一 Gate，也视为正常结果。

## 7. 评估与准入

结构校验顺序：

1. Skill package/frontmatter/manifest/hash；
2. trigger/non-trigger/permission/tool/data fixtures；
3. scripts 的真实确定性测试；
4. resolver 的 selected/rejected/no-Skill 解释；
5. 同一 Task/input/model/config 的 baseline/compact-contract/full-Skill 困难任务诊断；必要时再做 direct-tool/full-Skill 配对；
6. 盲评、错误类型、人工修正时间、上下文和协调成本；
7. 人工 Decision；
8. 独立更新 accepted Registry。

只有真实 forward test 才能支持增量价值。fixture PASS、模型自评、另一个 reviewer Agent 同意或格式更完整都不能自动准入。

简单样例只用于结构和 checker 冒烟，不作为价值证据。高密度 Claim、对抗压力、混合边界、分层预算和停止条件见[路诚钺 Skill 诊断性困难任务测试计划](DIAGNOSTIC_FORWARD_TESTING.md)。三臂诊断不会替代正式配对契约；Registry 证据仍记录为共享 baseline 的独立 pair。

## 8. 停止和删除条件

- Skill 与普通 Task 指令或确定性 Tool 无可区分增益；
- non-trigger 经常误触发；
- required Tools 在目标环境中不可用，且没有合法 fallback；
- 上下文、审阅或修正成本超过错误减少；
- 方法结论依赖未批准假设或特定 Provider 隐式行为；
- 许可、数据出口或脚本风险无法关闭；
- 只有泄漏预期答案或增加 reviewer 层数才表现良好。

满足停止条件时优先 reject、retain-reference、拆分或退回 Tool，不为保住候选扩大流程。
