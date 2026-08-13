# 完整实施计划

版本：0.6

状态：执行中

日期：2026-08-14

## 1. 实施总则

实施顺序遵循“先证明科研工件和能力绑定有价值，再增加运行时便利性”。每个里程碑都必须产生可以独立使用的垂直结果，并带有删除条件。

本计划是软件交付顺序，不是研究项目必须遵循的工作流。

## 2. 技术基线

当前已接受的首版基线：

- Python 3.11+；
- `pyproject.toml` 单包结构；
- 标准库 `dataclasses` 和 `typing.Protocol` 表达内部对象与端口；
- YAML 作为主要人类编辑格式，JSON 作为交换/校验格式；
- `argparse` 提供本地 CLI；
- `unittest` 提供首轮测试；
- PyYAML、jsonschema 与 RFC3339 validator 是当前运行依赖；
- SHA-256 和 Git 提供首版版本/内容引用；
- `.agents/skills` 提供跨平台 Skill 布局，纯 API fresh session 提供可移植执行基线；
- `.codex/agents` 是已有的可选 Codex 映射，不代表最终平台选择；
- 无数据库、无服务端、无常驻进程。

技术选型见 [ADR-0004](../decisions/0004-MINIMAL-DEPENDENCY-M1.md)。当前使用 Draft 2020-12 JSON Schema；属性测试出现明确复杂度后再评估 Pydantic 或 Hypothesis。

模型 API 采用能力协商式中立端口，见 [ADR-0003](../decisions/0003-PROVIDER-NEUTRAL-MODEL-PORT.md)。M1 冻结端口和能力/错误语义；后续已按用户明确需求提前完成 OpenAI、Anthropic、Gemini 的首个离线薄 Adapter 切片，见 [ADR-0007](../decisions/0007-THIN-PROVIDER-ADAPTERS.md) 与 [多提供商模型 API 实施计划](PROVIDER_ADAPTER_PLAN.md)。这不改变 M1“不调用真实 API”的退出边界，也不等于 live conformance。

## 3. 里程碑总览

| 里程碑 | 目标 | 核心证据 |
|---|---|---|
| M0 | 架构与仓库基线 | 文档、任务、独立仓库 |
| M1 | 契约与确定性验证 | CLI 可验证最小对象、Task、Handoff |
| M2 | 不同 Agent—Skill 绑定 | 两个 Profile + 两个 Skill 隔离执行 |
| M3 | 上下文与预警垂直切片 | checkpoint/rollover 恢复与边界预警 |
| M4 | 工件、Run 与可复现性 | Claim 可定位、Run 可重建 |
| M5 | 两个真实案例与删减 | 与单 Agent 基线的净收益数据 |
| M6 | API-first 执行与按需扩展 | 显式模型槽、隔离 API 会话、可选平台适配 |
| M7 | Mode–Skill 选择与协调成本 | 模式决策卡、Skill 选择矩阵、受控读取与分级 Handoff |

## 4. M0：架构与项目基线

### 目标

冻结产品边界、模块关系、Agent—Skill 分离和首批任务，不写运行时业务代码。

### 交付物

- Project Charter；
- 总体架构及 10 个模块计划；
- 实施、迁移、测试和目录规划；
- ADR：原生运行时优先、Skill 显式绑定；
- Task backlog；
- 独立私有 GitHub 仓库。

### 退出条件

- 文档内部链接通过检查；
- 不存在“先造通用 Supervisor/数据库”的隐含前置；
- 首个垂直切片明确为 evidence 与 simulation 两类不同 Skill；
- M1 任务都有输入、输出和验收。

## 5. M1：契约与确定性验证器

### 目标

在不调用任何 LLM 或 Agent 的情况下，创建、读取、验证和追踪最小工件。

### 实现内容

1. 初始化 Python 包、CLI 和测试框架。
2. 实现核心对象模型：Question、Hypothesis、Method、Run、Evidence、Claim、Decision。
3. 实现 Project Protocol、Mode Pack、Agent Profile、Skill Manifest、Task、Handoff、Main State。
4. 输出版本化 JSON Schemas。
5. 实现稳定 ID、revision、SHA-256 和引用解析。
6. 实现 CLI：

```text
rwb init <project>
rwb validate <path-or-project>
rwb task resolve <task>
rwb handoff validate <handoff>
rwb claim trace <claim-id>
rwb context checkpoint
```

7. 实现最小风险检查：stale input、missing output、write overlap、skill mismatch、claim ceiling、hash mismatch。

### 明确不做

- 不启动子 Agent；
- 不连接网络、Zotero、DVC 或模型 API；
- 不实现完整事件溯源或数据库；
- 不做 LLM 语义评分。

### 退出条件

- 示例 Project/Task/Handoff 可通过 CLI；
- 篡改输入、Skill 版本或 Evidence 后能确定性失败；
- `structurally_valid` 与科学结论明确区分；
- Windows 和至少一个 CI 环境可运行测试；
- 核心模型不含平台特有字段。

## 6. M2：Agent Profile 与 Skill 路由

### 目标

证明不同子 Agent 可以使用不同 Skills，且主 Agent不需要加载全部 Skill 或任务过程。

### 实现内容

1. 建立 Skill Registry 与 Resolver。
2. 消费 provider-neutral 执行接口；具体 Model Port、模型槽和隔离 API Session 由黄毅维护。
3. 创建 Agent Profiles：
   - `coordinator`
   - `evidence-scout`
   - `simulation-auditor`
   - `targeted-reviewer`
4. 创建首批 Skills：
   - `literature-evidence-extraction`
   - `simulation-vv`
   - `handoff-integrity`（优先脚本化）
5. 生成与运行时无关的最小执行输入、内容允许集和 Handoff 等级；执行工作流负责映射到 API 或可选平台。
6. 以 Task Packet 显式点名 required Skills。
7. 记录 Skill lock、实际工具、Provider/Model、Runtime snapshot（若有）和 Handoff。

截至 2026-08-14，Registry、Profiles、Skills、显式绑定和 Codex 可选映射均已有确定性契约；API 工作已达到 `K-API-1` 并由黄毅继续维护。路诚钺尚缺 Mode 决策卡、Task-to-Skill 选择矩阵、accepted Skill 边界审计和真实增量价值，因此 M2 尚未退出。

### 路由测试矩阵

| Task | Profile | 必需 Skill | 不应加载 |
|---|---|---|---|
| bounded evidence extraction | evidence-scout | literature-evidence-extraction | simulation-vv |
| simulation convergence audit | simulation-auditor | simulation-vv | final-synthesis |
| citation overreach review | targeted-reviewer | citation-audit 或 evidence Skill 的 review 入口 | simulation-run |

### 退出条件

- 至少两类 Task 得到不同、可解释的 Skill 选择；真实执行可由外部执行工作流提供；
- required Skill 缺失或版本漂移会阻断；
- 主 Agent只读取 Handoff 与索引即可决定下一步；
- 子 Agent不能越过 Profile/Task 权限；
- Resolver 的选择理由可解释且可重放；
- 没有自建全局 Scheduler；API Runner 只在单个 Attempt 内执行有界循环。

## 7. M3：上下文与预警垂直切片

### 目标

验证主 Agent克制、子 Agent压缩容忍和主动 rollover。

截至 2026-08-14，已实现 Context Snapshot、Execution Receipt、规范化 Main State digest，以及 `context assess/checkpoint/resume-check` 和 `execution assess`。Transfer Manifest/Audit 能支持高风险或压缩后的 H2 交接，但普通任务改以 H1 Compact Handoff 为默认；后续必须比较两者的实际遗漏、回查、返工与审阅成本。所有 H1/H2 Agent 间可见传递都进入 Attempt Archive，完整 Trace 与主上下文加载解耦。真实执行、用量和执行端捕获由黄毅提供；路诚钺负责实名 actor、读取边界、Handoff/Trace 分级与结果评估，见 [ADR-0008](../decisions/0008-HANDOFF-TRANSFER-AUDIT.md)、[ADR-0009](../decisions/0009-FILE-FIRST-CONTINUITY-AND-SAFE-PAUSE.md)、[ADR-0011](../decisions/0011-RISK-TIERED-HANDOFF-AND-CONTROLLED-READS.md)与[ADR-0012](../decisions/0012-NAMED-OWNERSHIP-AND-REPLAYABLE-AGENT-TRACE.md)。

### 实现内容

- Main State Packet 生成与验证；
- context pressure 代理指标；
- checkpoint 与 resume check；
- 新会话恢复演练；
- Handoff loss、summary distortion、stale、Skill context flood 预警，以及 Transfer Manifest/Audit；
- delegation fanout、review loop 与 write race 检查；
- 敏感 trace 关闭/脱敏策略。

### 实验

对同一任务分别运行：

1. 主 Agent直接读取全部材料；
2. 子 Agent执行但自由文本汇总；
3. 子 Agent + Skill Assignment + Handoff + Main State。

比较主上下文材料量、恢复成功率、限制遗漏、返工和 token。

### 退出条件

- 主会话主动 rollover 后能从文件恢复；
- 删除子 Agent会话不影响正式结果；
- 自动/人工模拟压缩不丢失 Task 已完成义务；
- 至少一种上下文预警能真实改变行动；
- 未产生新的常驻 continuity 服务。

## 8. M4：工件、Run 与可复现性

### 目标

把 Skill 产出连接到 Evidence、Run、Claim 和 Decision，验证从结论向源头回溯。

### 实现内容

- sources inbox/raw 接纳清单；
- work → objects/runs promotion；
- Claim graph 与 counterevidence；
- Run manifest、环境、代码、参数和输出引用；
- 可选 DVC 适配的技术 spike（只有真实大文件时）；
- release subset 与 Human Decision。

### 退出条件

- 一条文献 Claim 可定位到来源位置；
- 一条 simulation Claim 可定位到代码、参数、环境和输出；
- 输入修改后依赖 Claim 标记 stale；
- 失败 Run 和反证保留；
- 不依赖聊天记录进行重建。

## 9. M5：两个真实案例与删减

### 目标

判断框架是否比单 Agent 更有价值，并主动删除控制成本高于收益的部分。

### 案例建议

1. 证据综合案例：有明确检索边界、可定位来源和冲突证据。
2. 理论 + 仿真案例：有假设、模型、参数扫描和 Claim ceiling。

### 对照

- 单 Agent 基线；
- 单 Agent + Skills；
- 主 Agent + 不同 Skill 子 Agent。

### 退出条件

- 关键错误/遗漏或上下文负担至少一项明显改善；
- 协调与校核成本不长期超过三分之一；
- 至少删除/降级一个未产生价值的字段、预警、Gate 或 Skill；
- 研究者愿意在下一任务继续使用；
- 若净收益不足，明确停止而不是增加 Agent。

## 10. M6：API 执行与谨慎扩展（黄毅维护）

核心科研能力仍应在 M5 通过后按需求扩展；但为保证平台可替换性，API-first 执行缝已按明确需求提前实现：

- Zotero/PaperQA2 Tool Adapter；
- DVC 或 MLflow；
- Quarto/Jupyter 报告；
- Codex/OpenCode/Claude Code/Agents SDK 等可选 Runtime Adapter；
- 轻量可视界面。

新增项必须有真实消费者、预算、测试和退出条件。不得一次引入两个功能重叠的重量级工具。

当前已完成三家非流式 Adapter、ToolChoice、本地工具参数校验、延迟凭据解析、非秘密配置探测、脱敏 live conformance runner，以及 `explicit-slot-only` Model Pool 和有硬预算的 fresh API tool-loop runner。不会继续铺更多提供商或构建复杂 Router。

截至 2026-08-14，黄毅维护 Provider Adapter、Task-to-API、live conformance、执行端 Agent Trace 捕获和 API 专用测试。路诚钺只维护冻结的 Mode、Skill Assignment、内容允许集、输出/Handoff/Trace 契约和评估接口；M6 不阻塞路诚钺的里程碑。

## 11. M7：Mode–Skill 选择基线

路诚钺的下一关键节点为 `K-MS-1`：先冻结实名 actor、Attempt Archive 与 Agent Trace fixture，再用现有 `evidence-synthesis` 与 `simulation` 建立 Mode 决策卡、6 个边界 Task fixtures、Task-to-Skill 选择矩阵、三个 accepted Skills 的适用性审计、一个 triage candidate 的去留决定，以及 H0/H1/H2 和内容读取成本对照。

完成后暂停评审。不得为了“覆盖完整”批量新增 Mode/Skill，也不得在本分支修改 API 执行实现。详细阶段和停止点见 [Mode–Skill 工作流计划](MODE_SKILL_WORKSTREAM_PLAN.md)。

## 12. 开发分支与提交策略

- 默认分支 `main` 保持可读、可验证；
- 每个里程碑或小型垂直切片使用 `agent/<description>` 分支；
- Schema 变更与实现同时提交；
- 核心契约变更先更新 ADR；
- 不把生成的运行数据、原始论文或敏感项目工件提交到框架仓库；
- 里程碑结束创建版本标签，早期使用 `v0.x`。

## 13. 停止和回退条件

暂停扩展并重新评审，如果：

- 控制代码增长快于科研能力；
- 主 Agent仍需读取全部历史；
- Skills 常被全部加载或路由不可解释；
- 多 Agent 主要产出是相互校核；
- 使用者频繁绕开 Task/Handoff；
- Runtime Adapter 变成第二个 Agent 平台；
- 关键质量指标无改善；
- 项目主要成果持续只是架构文档。

回退优先级：减少 Skills → 减少 reviewer → 合并/删除预警 → 回退单 Agent + 工件 → 停止运行时开发，仅保留可复用规范。
