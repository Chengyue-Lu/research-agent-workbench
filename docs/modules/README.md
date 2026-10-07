# 模块文档索引

模块文件描述稳定职责、输入/输出接点、启用条件、风险和验收条件。它们不是固定科研流水线，也不是
需要逐一启动的 Agent 名单。应用职责可以合并会话；主 Agent 按有界任务决定 0..N 个子任务。

1. [最小科研内核](01-RESEARCH_KERNEL.md)
2. [项目协议与研究模式](02-PROTOCOL_AND_MODES.md)
3. [Agent 运行模型](03-AGENT_RUNTIME.md)
4. [Skill 系统与能力路由](04-SKILL_SYSTEM.md)
5. [Task 与 Handoff 契约](05-TASK_AND_HANDOFF.md)
6. [上下文治理](06-CONTEXT_GOVERNANCE.md)
7. [工件、Attempt Archive 与 Agent Trace](07-ARTIFACTS_AND_PROVENANCE.md)
8. [验证、风险与 Human Gate](08-VALIDATION_RISK_AND_GATES.md)
9. [运行时与工具适配](09-ADAPTERS_AND_INTEGRATIONS.md)
10. [观测、成本与评估](10-OBSERVABILITY_EVALUATION_COST.md)

模块之间只通过版本化契约连接。若一个模块必须读取另一个模块的内部会话或私有状态才能工作，应视为架构泄漏。

| 模块 | Producer → 主要产出 → Consumer | 何时启用 |
|---|---|---|
| 01 内核 | 研究执行者/人类 → 版本化研究对象 → Task、定位器、Human | 实际需要对应 Question/Method/Run/Evidence/Claim/Decision 时 |
| 02 协议与模式 | 协议/方法调用者 → Protocol、Task、Method、Requirement → 能力解析/执行 | 新需求或显式既有材料进入、方法义务触发时 |
| 03 Agent运行 | 启动调用者/执行者 → 有界执行与子结果 → 主接收者 | 本项工作需要AI执行，独立工作值得委派时 |
| 04 能力与Skill | 事实报告者/Resolver/可选Maintainer → selected closure/Release投影 → Bundle/执行 | 每次能力冻结；仅明确语义缺口和合法选择才使用Skill |
| 05 Task与交接 | Task producer/执行者 → Task、工件、Handoff → 执行者/接收者 | 有界任务；跨Agent、重试或接续时启用相应交接 |
| 06 上下文 | checkpoint writer/checker → Main State与恢复结果 → 新主会话/Human/只读Guide | 压力、阶段边界、等待、交接或状态查询时 |
| 07 工件与溯源 | recorder/来源接纳/promotion → Trace、sidecar、正式工件 → 定位/审计/接收 | 实际传递留痕；来源、复制、Claim回查、Run重建按Task启用 |
| 08 验证与Gate | validator/定向reviewer/人类 → 报告或Decision → 执行/接收/promotion | 确定性边界检查；明确语义风险或保留决定时 |
| 09 适配 | Adapter/Session/Tool → 供给事实、响应与实际执行事实 → Resolver/Host/closeout | 任务需要具体模型、工具或平台执行时 |
| 10 观测评价 | Runtime/评价Harness → usage、运行证据与盲评材料 → 接收者/人类评审 | 实际执行计量；独立批准的价值评价另行启用 |

每次AI调用需要职责指令与Task边界；Profile限制运行能力；Skill提供可选方法程序；会话只是临时
上下文。Guide是独立只读查询职责，其回答不自动回传主执行或写研究状态。完整逐跳接点见
[开发者架构地图](../DEVELOPER_ARCHITECTURE_MAP.md)。

工件与溯源的契约按职责分为
[Source Admission](../implementation/SOURCE_ADMISSION_CONTRACT.md)、
[Artifact Promotion](../implementation/ARTIFACT_PROMOTION_CONTRACT.md)、
[Claim evidence localization](../implementation/CLAIM_TRACE_CONTRACT.md) 与
[bounded Run reconstruction](../workstreams/huangyi/M4-RUN-RECONSTRUCTION/README.md)。这些入口分别说明
准入、提升、支持/反证/限制定位与 synthetic 重建的有界契约，不替代 Claim 接受或 Human Decision。

开发与贡献规则见[开发协作指南](../DEVELOPMENT.md)，跨模块关系见[总体架构](../ARCHITECTURE.md)，
当前实现覆盖见[实现状态](../STATUS.md)。演进历史保留在[历史与审计](../history/README.md)，不承担稳定模块入口。
