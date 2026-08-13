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

### Output Skill

指导生成特定工件，例如 Evidence Matrix、V&V Report、Decision Brief。它不能改变内容所需的证据标准。

首版不强制在目录层面区分四类，但 Registry 必须记录 `kind`。

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
- Skill 指令总量超预算时必须拆任务，不能压缩成含混“大综合 Skill”；
- 频繁同时出现的一组 Skills 只有在真实数据证明稳定后才能形成 Bundle。
- Agent 只能读取本次选中 Skill 的 `SKILL.md` 和其中为当前步骤显式引用的 references；不得借 Skill 发现递归读取其他候选 Skill 或整个 reference 树。
- 对未选 Skill 只允许读取 Registry 元数据；需要比较正文时，应创建独立的 Skill 评估 Task，而不是在业务 Task 中临时展开。

## 8. 生命周期与供应链

Skill 状态：`draft → trial → accepted → deprecated → retired`。

进入 `accepted` 前需要：

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
| SKILL-MISSING | required Skill 不存在 | BLOCK |
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

- 两个子 Agent 的 required Skills 不同且实际加载记录可查；
- Resolver 能解释为什么选择/排除某个 Skill；
- Skill 不能扩大权限或 Claim ceiling；
- Skill 更新不会静默改变历史任务解释；
- 未加载的 Skills 不占用子 Agent 正文上下文；
- 相同 Task + Registry lock 得到相同候选集合；
- 删除某个低价值 Skill 不需要修改内核或 Agent Runtime。

## 13. 当前实现快照

截至 2026-08-13，`registry/skills/accepted.json` 是唯一可执行 Skill 索引；`.agents/skills` 中的三个原创 Skill 均由版本、来源路径、`SKILL.md` 内容哈希和整个 Skill 目录包哈希锁定。`.gitattributes` 固定可哈希文本为 LF，避免跨 Windows/Linux 的伪漂移。Resolver 默认要求 Task 显式列出 `required_skills`；自动最小覆盖只在调用方明确允许时启用，等价候选会返回 `SKILL-AMBIGUOUS` 而不是猜测。

外部来源继续保存在 `registry/skills/candidates.json`，不会因下载、发现或 `reference` 状态进入 accepted Registry。Codex 只在 dispatch 中显式调用本次 Assignment 的 `$skill-name`；未选择 Skill 的正文和 references 不进入任务上下文。

独立派生但尚未准入的实现放在 `skill-lab/candidates/`。该路径不是平台 Skill 发现路径，也不进入 accepted Registry；它用于保存短指令、确定性脚本、fixtures、内容/包哈希和 with/without 评估证据。首个包 `claim-preserving-rewrite` 只验证数字、引用、否定、证据强度、因果措辞与显式保护词等表层不变量，并明确不宣称语义或科学等价。

截至 2026-08-14，本侧下一工作不是扩大 accepted 数量，而是完成 Task-to-Skill 选择矩阵：先判断确定性工具/no-Skill 是否足够，再比较 accepted candidates；歧义时拆 Task 或进入 Human Gate。候选优先级、停止点和 API 工作流边界见 [Mode–Skill 工作流计划](../implementation/MODE_SKILL_WORKSTREAM_PLAN.md)。
