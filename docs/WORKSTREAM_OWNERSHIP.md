# 工作流职责与接口边界

状态：实施基线

日期：2026-08-14

## 1. 当前分工

项目继续共享同一套文件契约，但开发责任分为两个工作流。分工只决定谁维护什么，不改变系统对具体模型、Provider 或 Agent 平台保持中立的原则。

| 工作流 | 主要负责 | 不负责 |
|---|---|---|
| Mode–Skill 工作流（本侧） | Research Mode 语义、模式组合与准入；能力词汇；Skill 发现、筛选、派生、评估、准入和退役；Resolver 的选择理由；受控读取与 Handoff 成本策略；模式/Skill fixtures、方法审计和文档 | Provider SDK、认证、HTTP transport、模型槽实现、API session loop、live API conformance、Task-to-API 编译和 API 专用测试 |
| API Execution 工作流（同伴侧） | Provider Adapter、模型能力协商、模型槽、隔离 API session、工具调用循环、Task-to-API 编译、执行关闭事务、真实账户/模型 conformance 和 API 测试 | 决定研究模式是否合理、替研究者批准 Claim、擅自准入 Skill、改变 Mode/Skill 语义或降低 Human Gate |
| 共享接口 | Task Packet、Resolved Task/Skill Assignment、Handoff Packet、Execution Receipt、Capability/Data Policy 词汇、错误和停止状态 | 任一工作流单方面改变接口后要求另一侧追随 |

共享接口变更必须满足：先写 ADR 或接口提案；给出迁移影响；由两个工作流确认 owner；再修改 Schema 或实现。我们这一侧不再以修复 API CI、增加 Provider 或执行真实 API 调用作为完成条件。

## 2. Mode–Skill 工作流的权威文件

- `docs/modules/02-PROTOCOL_AND_MODES.md`
- `docs/modules/04-SKILL_SYSTEM.md`
- `docs/implementation/MODE_SKILL_WORKSTREAM_PLAN.md`
- `docs/implementation/SKILL_CANDIDATE_PIPELINE.md`
- `docs/implementation/SKILL_EVALUATION_PROTOCOL.md`
- `registry/modes/`
- `registry/skills/`
- `.agents/skills/` 与 `skill-lab/candidates/`
- 与 Mode、Skill 选择、受控读取和 Handoff 成本有关的 fixtures、评估报告和文档

`src/research_workbench/adapters/models/`、`registry/providers/`、`registry/models/` 及 API conformance/test 文件由 API Execution 工作流维护。本侧可以读取已发布的接口和脱敏结果来完成 Skill 评估，但不在本工作流分支上修改它们。

## 3. 协作交付接口

Mode–Skill 工作流向 API Execution 工作流提供：

1. 已解析 Task 或稳定的 Task fixture；
2. active Mode、能力要求和 Claim ceiling；
3. 冻结的 Agent Profile 与 Skill Assignment；
4. 内容读取允许集、工具权限和写入范围；
5. 输出契约、Handoff 等级、停止条件和失败语义。

API Execution 工作流返回：

1. Attempt 和实际执行身份；
2. 正式输出或失败/安全暂停工件；
3. 实际读取、工具和副作用的边界偏差；
4. Handoff Packet，以及任务要求时的 Manifest/Audit/Receipt；
5. 可供 Mode–Skill 评估使用的用量、耗时和错误分类，不返回凭据或完整敏感 trace。

Mode–Skill 工作流只根据这些正式工件决定 Skill 是否有增量价值。不能把 API 调用成功、模型自评或格式通过当成 Skill 准入证据。

## 4. 分支与写入纪律

- `main` 保存双方已确认的接口和文档基线。
- Mode–Skill 实现使用 `agent/mode-skill-*` 分支；API 工作流使用自己的独立分支命名。
- 同一时间只有接口 owner 修改共享 Schema、`cli.py` 或同一 Registry 索引。
- 并行任务必须声明独占写入路径；无法隔离写入的工作应串行完成。
- Handoff 必须给出基线提交、实际修改路径、验证证据、未证明内容和唯一下一动作。

## 5. 冲突处理

若 API 执行方便性与 Mode/Skill 方法边界冲突，采取更严格边界并请求人工决定。API 工作流不得因为某 Provider 不支持而静默删除 Skill 要求；Mode–Skill 工作流也不得为获得理想评估结果要求 API 侧绕过预算、数据或工具限制。
