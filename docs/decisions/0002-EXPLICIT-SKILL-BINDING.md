# ADR-0002：受控任务显式绑定 Agent 与 Skill

状态：Accepted

日期：2026-08-13

## Context

Agent 角色、研究模式、Skill 和工具经常被混为一体。仅靠 Skill description 隐式匹配虽然灵活，但无法保证关键任务实际使用了哪个版本，也无法可靠控制上下文、权限和复现。

## Decision

Canonical Task 声明 required capabilities；Capability Resolver 选择 Agent Profile 和最小 Skill 集；Resolved Task 记录 Skill Assignment 和版本/哈希；Runtime Adapter 对受控任务显式调用 required Skills。

探索任务可以使用隐式 Skill 建议，但其输出不能直接升级正式 Claim。

## Consequences

优点：不同子 Agent 可使用不同 Skills；路由可解释；上下文可预算；历史结果可定位到 Skill 版本。

代价：需要维护 Registry、Resolver 和回归 eval；过度分类可能形成 Skill taxonomy 负担。

## Guardrails

- 默认最多两个主 Skill + 一个校验 Skill；
- Skill 不能扩大 Profile/Task 权限；
- manifest 冲突确定性阻断；
- Registry 增长而复用率低时触发删减评审。
