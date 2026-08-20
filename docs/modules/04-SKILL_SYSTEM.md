# 模块 04：Skill 系统与能力路由

## 1. 目标

让不同子 Agent 按任务使用不同 Skills，并使选择过程可解释、可版本化、可复现、可限制。Skill 是可复用工作方法，不是 Agent 本身，也不是任意工具权限的来源。

## 2. Skill 分层

### Method Skill

表达研究活动中的方法，例如证据提取、收敛检查、敏感性分析、反例搜索。

### Integrity Skill

表达引用审计、Claim—Evidence 检查、复现清单、数据边界检查等横切质量工作。

### Tool Skill

指导 Agent 使用某个工具或连接器完成稳定流程，例如 Zotero 读取、DVC Run 定位、Quarto 构建。工具本身仍由 MCP/CLI/API 提供。

“流程可复用”本身不足以形成 Tool-use Skill。只有 direct Tool + Task instruction/template 基线不足，
并存在跨任务、非平凡、可复用的语义判断缺口时，Method Resolution 才可产生 Tool-use Skill Need。
API/MCP/CLI 的普通调用说明、参数映射和环境配置优先属于 Tool Capability Card、Adapter documentation、
Task template 或 deterministic checker。

### Output Skill

指导生成特定工件，例如 Evidence Matrix、V&V Report、Decision Brief。它不能改变内容所需的证据标准。

首版不强制在目录层面区分四类，但 Registry 必须记录 `kind`。

### 适用范围轴

`kind` 描述 Skill 做什么；Need 来源另有一条正交的适用范围轴：

- `mode-derived`：由 Research Mode action 的非平凡语义缺口产生；
- `project-internal`：只为本项目的 Assignment、Handoff、恢复或 Human Gate 准备等协议动作服务。

项目内生不构成第五种 `kind`，也不意味着全局加载。权限、受控读取、交互留痕、字段格式和 hash
校验仍分别属于 Project Protocol、Task/Profile、Schema/template 和 Tool/checker。只有这些基线不足
以处理可复用语义判断时，才建立 project-internal Skill Need。候选阶段不借
`applies_to_modes: [all]` 伪造 Mode 适用性；是否增加最小 `scope` 元数据需另行通过 Schema 决策。

## 3. Skill Manifest

除平台需要的 `SKILL.md` 外，项目维护可机器读取的元数据：

```yaml
skill_id: literature-evidence-extraction
version: 0.1.0
kind: method
description: Extracts citable evidence records from bounded scientific sources.
capabilities: [evidence-search, evidence-extraction, citation-location]
applies_to_modes: [evidence-synthesis, experiment, theory]
excludes:
  - final causal interpretation
required_tools: [document-read]
optional_tools: [web-search, zotero-read]
permission_ceiling:
  filesystem: worktree-write
  external_write: forbidden
  allowed_roots: [work]
input_contracts: [question-ref, source-boundary]
output_contracts: [evidence-record, handoff-packet]
context_cost:
  metadata: low
  instructions: medium
  references: on-demand
incompatible_with: []
verification:
  deterministic: [citation-locator, source-hash]
source:
  origin: repository
  content_hash: "..."
```

`description` 用于发现，不能作为完整路由依据。关键字段由 Registry Validator 检查。

## 4. Capability Resolver

长期解析分两步：Method Resolution 先产生 `Skill Need` 或 `Capability Requirement`，Capability
Resolver 再绑定具体 Skill/Tool/Adapter Snapshot。当前 Resolver 直接从 Task/Profile/Mode 处理
Skill Assignment，是兼容期执行视图，不应被解释为完整方法路由。

正式 Skill Need 至少需要 trigger/non-trigger、semantic gap、no-Skill/direct-tool baseline、
expected increment、trial 前证据和已知 domain variants。一个 Need 可对应多个 candidate；没有
候选时保持 gap，不自动生成 accepted Skill。

输入：

- Task 类型和目标；
- Active Research Modes；
- required outputs；
- 风险级别；
- 数据边界；
- Agent Profile 权限与工具能力；
- token/context/时间预算；
- 平台已安装 Skills 与版本。

处理顺序：

1. 读取 Skill 元数据，不加载所有正文；
2. 应用硬过滤：权限、数据边界、工具、输入/输出契约、Mode 排除；
3. 满足 Task 的 `required_capabilities`；
4. 在候选中选择上下文成本最低的最小覆盖集；
5. 检查依赖、冲突和版本；
6. 若存在多个等价候选，按项目偏好或人工选择，不由角色名称猜测；
7. 生成 `Skill Assignment` 并冻结版本/哈希；
8. Runtime Adapter 以显式调用方式交给子 Agent。

## 5. Skill Assignment

```yaml
assignment_id: SA-0042
task_id: EVID-001
agent_profile: evidence-scout@0.1.0
required:
  - skill_id: literature-evidence-extraction
    version: 0.1.0
    content_hash: "sha256:..."
optional: []
forbidden:
  - final-synthesis
resolved_tools: [document-read, web-search]
effective_permissions:
  filesystem: worktree-write
  external_write: forbidden
  allowed_roots: [work/EVID-001]
resolution_reason:
  - covers all required capabilities
  - satisfies source and citation output contracts
```

## 6. 显式调用策略

Codex 等平台可以根据 description 隐式激活 Skill，但本项目分三档：

- `exploratory`：允许隐式建议，结果不得直接升级正式 Claim；
- `controlled`：Task Packet 明确列出 required Skills，Runtime 必须显式调用；
- `regulated/high-risk`：除显式调用外，还必须记录版本、哈希、工具与验证输出。

这样既保留灵活性，又不把可复现任务交给不可观察的隐式匹配。

## 7. 上下文预算

- 主 Agent 只看 name、description、capabilities、cost 和 compatibility 元数据；
- 子 Agent 只加载本次 required/optional Skills；
- Skill 正文采用渐进披露：`SKILL.md` 保持可执行，长参考进入 `references/`，脚本进入 `scripts/`；
- 一个任务默认最多两个主 Skill和一个校验 Skill；
- project-internal Skill 计入同一上限，默认最多选择一个，不获得额外槽位；
- Skill 指令总量超预算时必须拆任务，不能压缩成含混“大综合 Skill”；
- 频繁同时出现的一组 Skills 只有在真实数据证明稳定后才能形成 Bundle。
- Agent 只能读取本次选中 Skill 的 `SKILL.md` 和其中为当前步骤显式引用的 references；不得借 Skill 发现递归读取其他候选 Skill 或整个 reference 树。
- 对未选 Skill 只允许读取 Registry 元数据；需要比较正文时，应创建独立的 Skill 评估 Task，而不是在业务 Task 中临时展开。

## 8. 发现、评测、准入与运行资格

Skill 治理不是单一状态机，至少包含四个正交维度：

| 维度 | 回答的问题 | 当前/候选词汇示例 |
|---|---|---|
| Source / Intake State | 来源材料处于库存的什么位置 | `reference / candidate / rejected` |
| Evaluation State | 候选经过了什么验证 | `untested / trial / evaluated / shadow` |
| Admission Decision | 人类是否批准其进入项目 Registry | `accepted / rejected / pending` |
| Runtime Lifecycle / Eligibility | 哪些已准入版本可用于新 Assignment 或仅供回放 | `active / superseded / legacy / deprecated / retired` |

这些词汇不是本阶段新增的正式 enum；Phase B 再冻结转换规则。尤其 `accepted` 是准入决定，不与
runtime lifecycle 混成同一轴。进入 accepted Registry 前需要：

- 明确 trigger 和 non-trigger；
- 输入/输出契约；
- 至少一个成功与一个失败/越界案例；
- 权限、外部数据和工具依赖说明；
- 确定性验证或人工检查方法；
- 上下文成本记录；
- 来源、许可证和内容哈希。

外部 Skill 默认不可信。引入前检查脚本、命令、网络行为、数据上传、提示注入面和许可证。Skill 更新会使旧 Assignment 保持旧版本，不自动重解释历史结果。

## 9. 指令冲突

优先级按实际平台规则执行，但项目逻辑必须满足：

1. 系统/开发者/用户和权限策略；
2. Project Protocol 与 Human Decision；
3. Task Packet；
4. Agent Profile；
5. Skill 指令；
6. Skill 参考材料。

Skill 若要求超出上层边界的动作，Resolver 必须阻断或裁剪，而不是交给模型自行协调。Skill 之间冲突时不依赖“模型理解”，应由 manifest 的 `incompatible_with`、契约冲突或人工决定处理。

## 10. 预警代码

| 代码 | 含义 | 默认等级 |
|---|---|---|
| SKILL-MISSING | 已冻结 Skill binding 不存在；正式 no-Skill/direct-tool 不适用 | BLOCK |
| SKILL-VERSION-DRIFT | 执行版本与 Assignment 不一致 | BLOCK |
| SKILL-CONTEXT-FLOOD | Skill 总上下文超预算 | WARN/BLOCK |
| SKILL-CONFLICT | Skills 或输出契约冲突 | BLOCK |
| SKILL-PERMISSION-ESCALATION | Skill 请求超出权限 | BLOCK |
| SKILL-IMPLICIT-CRITICAL | 关键任务仅靠隐式激活 | BLOCK |
| SKILL-SUPPLY-CHAIN | 来源、脚本或许可证未验证 | HUMAN |
| SKILL-TAXONOMY-GROWTH | Registry 增长但实际复用低 | WARN |
| SKILL-STALE-EVAL | 版本更新后无回归评估 | WARN |

## 11. 首批 Skills

### literature-evidence-extraction

从限定来源提取可定位 Evidence；分开原文事实、Agent 推断和建议；保留页码/段落/DOI/URL、来源版本和冲突证据。

### simulation-vv

检查仿真模型、输入版本、参数范围、数值收敛、敏感性、基准比较和 Claim ceiling；不判断模型是否代表真实世界。

### handoff-integrity

验证必需输出、工件引用、限制、未完成项、输入版本和 Skill lock。它应优先实现为确定性脚本；只有语义项才由 Skill 补充。

## 12. 验收条件

- frozen Skill binding（如有）的实际加载记录可查，no-Skill/direct-tool 不伪造 Skill lock；
- Resolver 能解释为什么选择/排除某个 Skill；
- Skill 不能扩大权限或 Claim ceiling；
- Skill 更新不会静默改变历史任务解释；
- 未加载的 Skills 不占用子 Agent 正文上下文；
- 相同 Task + Registry lock 得到相同候选集合；
- 删除某个低价值 Skill 不需要修改内核或 Agent Runtime。

## 13. 当前实现快照

`registry/skills/accepted.json` 是 accepted Skill 的唯一索引；条目的 `status: accepted` 保存准入历史，`lifecycle: active | legacy | deprecated` 单独控制新分配资格。`.agents/skills` 中的包由版本、来源路径、`SKILL.md` 内容哈希和整个目录包哈希锁定；`.gitattributes` 固定可哈希文本为 LF，避免跨 Windows/Linux 的伪漂移。

Task 的 `required_skills` 支持 `skill-id` 或精确 `skill-id@semver`。新 Assignment 默认只选择唯一 active 版本并归一化为精确 Skill lock；historical replay 必须显式声明且带精确版本，禁止 auto-select。相同 ID 可保存多个历史版本，但最多一个 active。详细决定见 [ADR-0015](../decisions/0015-SKILL-LIFECYCLE-AND-EXACT-VERSION.md)。

外部来源继续保存在 `registry/skills/candidates.json`，不会因下载、发现或 `reference` 状态进入 accepted Registry。Codex 只在 dispatch 中显式调用本次 Assignment 的 `$skill-name`；未选择 Skill 的正文和 references 不进入任务上下文。

独立派生但尚未准入的实现放在 `skill-lab/candidates/`。该路径不是平台 Skill 发现路径，也不进入 accepted Registry；它用于保存短指令、确定性脚本、fixtures、内容/包哈希和 with/without 评估证据。首个包 `claim-preserving-rewrite` 只验证数字、引用、否定、证据强度、因果措辞与显式保护词等表层不变量，并明确不宣称语义或科学等价。

截至 2026-08-17，Skill Need 已形成 Mode-derived 与 project-internal 两条历史规划路线；两者都
先比较 Protocol/Task/template/Tool/no-Skill 基线。外部候选只作按 Need 检索的参考库存，项目内生
候选不进入 Registry/Runtime。K-MS-1 原计划现为历史证据；下一步不是继续写 Skill，而是按
[ADR-0016](../decisions/0016-METHOD-AWARE-RESEARCH-CONTROL-PLANE.md)先正式化 Mode Action 与
Method Resolution。

截至 2026-08-19，三个 `0.1.0` 原型均不再 active：literature/simulation 为 legacy，handoff wrapper 为 deprecated。新任务因此不会从 accepted Registry 自动或显式加载它们；旧示例只通过精确版本和显式 historical replay 重新解析。当前 active 数量为零不构成缺失修复任务。
