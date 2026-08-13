# ADR-0005：Handoff 引用完整 Skill Assignment

状态：Accepted

日期：2026-08-13

## Context

Task Handoff 原先只保存便于阅读的 `skill_id@version` 字符串。Skill 内容、Registry 或来源路径可能在版本号不变时漂移；仅靠该字符串无法恢复实际执行的内容哈希、有效权限、工具集合和 Registry 快照，也无法证明主 Agent 接收的 Handoff 与本次解析结果一致。

## Decision

Skill Assignment 作为独立、可校验的正式工件，包含 Task revision、Agent Profile、`SKILL.md` 内容哈希、整个 Skill 包哈希、来源路径、工具、权限交集与 Registry digest。Attempt 和 Handoff 增加 repository-relative `skill_assignment_ref`；`skill_lock` 继续作为冗余的人类可读摘要。

受控任务的 Handoff 校验同时读取 Assignment，检查 Task identity 与完整 Skill lock。旧 fixture 可暂时不含引用以保持 `0.1.0` 兼容，但不得作为新的受控执行证明。

## Consequences

优点：主 Agent 无需读取子 Agent 对话即可恢复执行边界；Skill 同版本内容漂移和 Registry split-brain 可以阻断；Runtime Adapter 仍不拥有权威状态。

代价：每次受控执行需要先持久化一个小型 Assignment 文件；Handoff 与 Assignment 之间增加一条必须维护的引用。

## Guardrails

- Assignment 使用稳定内容生成确定性 ID；
- Assignment 引用必须位于项目根内并通过 Schema；
- Handoff 的人类可读 Skill lock 必须与 Assignment 完全一致；
- Assignment pass 只证明执行契约一致，不证明科学正确性；
- 不把 Runtime 原始会话或 provider 私有状态写入 canonical Assignment。
