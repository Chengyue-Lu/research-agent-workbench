# 实现状态

状态：Current implementation authority
更新：2026-08-22

本页只回答“仓库现在实现到哪里”。实时任务状态由 [`TASKS.md`](TASKS.md) 维护，依赖方向由 [`ROADMAP.md`](ROADMAP.md) 维护。

## 成熟度

RWB 处于**内部技术 alpha**：核心文件契约、解析和确定性验证可供开发与集成试验使用；尚不构成面向普通研究者的完整产品，也不对科研结果作质量保证。

## 已实现

| 能力 | 当前覆盖 |
|---|---|
| 版本化对象 | Task、Assignment、Handoff、Evidence、Claim、Decision、Protocol、Receipt 等 Schema 与示例 |
| Method-aware control | 两个正式 Mode 的 16 个版本化 Action、hash-pinned Registry，以及八个按 Task 产生、provider-neutral 的 Method Resolution |
| 确定性验证 | Schema、引用、哈希、权限交集、Handoff lock、Claim 支持关系 |
| Task 解析 | Task + Agent Profile + 显式或 Registry Skill 的冻结 Assignment、权限交集与版本锁 |
| Skill 生命周期 | accepted Registry 的 active / legacy / deprecated 选择边界与精确版本 |
| 文件式连续性 | Main State、checkpoint、resume-check、受控 Handoff 与归档约定 |
| Execution Trace | Envelope、Index、append-only events、工具结果持久化与闭集校验 |
| Legacy execution bridge | 既有 Skill-bound Assignment 到 Trace / Receipt 的适配和恢复检查 |
| Provider seam | provider-neutral 的隔离会话接口、离线 probe 与合成 conformance 基础 |

## 受限或尚不可用

| 范围 | 限制 |
|---|---|
| Method-aware control migration | Mode v0.2 migration、Decision Authority、Resolved Execution View 与 Method Trace 仍在演进 |
| no-Skill Assignment | Task 契约允许空 `required_skills`，但 alpha CLI 尚不能将其解析为冻结 Assignment |
| End-to-end research run | 尚无面向普通用户的一键 Task-to-research 闭环；Runtime 集成由开发者显式接入 |
| 真实外部模型 | 仓库测试不证明各供应商真实账号、配额、工具调用或长期兼容性 |
| 科学有效性 | Validator 不评判方法适用、证据质量或 Claim 正确性 |
| Skill 价值 | 现有 Registry 条目不构成已证明的普适研究增益；新任务可优先 no-Skill / direct-tool |
| 发布 | 仓库缺少最终许可证选择，原创 Skill 许可状态仍阻断正式发布 |
| 产品体验 | 初始化、可视化、协作 UI、安装包和运维流程仍是开发者级别 |

## 支持边界

- 推荐路径：离线校验、no-Skill Task 契约验证、Mode Action/Method Resolution 引用、现有 Trace / Archive 验证、Adapter 开发。
- 兼容路径：旧 Skill-bound 工件可显式读取或回放，但不作为新任务默认模板。
- 实验路径：真实模型、外部工具和 MCP 接入需要具名授权、独立凭据管理和相应 Trace。

开始使用见[上手指南](GETTING_STARTED.md)，旧对象边界见[兼容性说明](compatibility/README.md)，当前工作项见[任务清单](TASKS.md)。
