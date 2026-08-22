# 模块文档索引

模块文件描述职责、核心契约、实现边界、风险和验收条件。它们不是一条固定的科研流水线。

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

实名维护与贡献规则见[开发协作指南](../DEVELOPMENT.md)，跨模块关系见[总体架构](../ARCHITECTURE.md)，
当前实现覆盖见[实现状态](../STATUS.md)。演进历史保留在[历史与审计](../history/README.md)，不承担稳定模块入口。
