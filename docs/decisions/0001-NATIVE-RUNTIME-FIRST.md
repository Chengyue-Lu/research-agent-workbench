# ADR-0001：优先使用原生 Agent 运行时

状态：Accepted

日期：2026-08-13

## Context

Codex、Claude Code 等平台已经提供子 Agent、线程、模型、权限、工具和 Skills。旧方案继续建设 External Supervisor、会话连续性数据库和固定 DAG，会把资源投入到重复控制面，并产生新的状态、恢复和校核问题。

## Decision

首版只实现平台中立契约和 Runtime Adapter。并发、线程生命周期、模型执行和基础权限交给平台原生能力。Codex 为首个 Adapter。

只有真实案例证明需要跨平台批处理、长期服务或可重复大规模评估时，才通过新 ADR 评估 Agents SDK、LangGraph 或其他编程式运行时。

## Consequences

优点：实现小、跟随上游能力、减少重复状态、快速验证科研价值。

代价：平台能力存在差异和漂移，需要 capability snapshot 与 contract tests；部分约束只能由 Task/Skill/Validator 保证。

## Rejected

- 自建通用 Supervisor；
- 固定研究 DAG；
- 以数据库保存完整会话；
- 为多平台统一而先造最低公分母运行时。
