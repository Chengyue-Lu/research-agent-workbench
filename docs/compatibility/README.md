# 兼容性说明

本页记录已接受系统与早期工件之间的显式兼容边界。兼容支持用于读取、验证和迁移，不定义新任务的推荐路径。

## Skill-bound v0.1 工件

- 早期 Task、Assignment 和 Handoff 可以引用冻结的 Skill 版本；
- accepted Registry 中部分条目处于 `legacy` 或 `deprecated` 生命周期，只允许精确历史解析；
- CLI 的 `--historical-replay` 只用于具名旧工件的精确回放，禁止静默 fallback；
- 新 Task 可使用 no-Skill、直接工具或后续 Method Resolution，不应复制旧 Skill ID 作为默认示例。

## Mode 与 Method

Research Mode v0.1 中的直接 Skill recommendation 是兼容字段。已接受架构以 Mode Action 和 Method Resolution 分离“要做的研究动作”与“用什么执行能力”；在正式迁移器可用前，旧字段保持可读但不扩展其语义。

## Execution Trace

文件权威 Trace Core 是执行事实的规范表示。Legacy execution adapter 可把既有 Skill-bound Attempt / Receipt 桥接到该表示；它不把旧 Skill 路由升级为 Method 决策，也不产生科学正确性结论。

## 迁移规则

1. 保留原始工件、版本、路径和内容哈希；
2. 显式声明来源版本、目标版本和迁移器身份；
3. 不覆盖原文件，不静默补造执行或方法事实；
4. 迁移失败时保留 blocked 状态和可审计风险；
5. 新的 happy-path 示例只使用当前支持且推荐的语义。

开发过程和迁移证据见[历史与审计](../history/README.md)，当前实现覆盖见[实现状态](../STATUS.md)。
