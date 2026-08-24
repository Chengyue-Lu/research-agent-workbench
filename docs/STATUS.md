# 实现状态

状态：Current implementation authority
更新：2026-08-24

本页只回答“仓库现在实现到哪里”。实时任务状态由 [`TASKS.md`](TASKS.md) 维护，依赖方向由 [`ROADMAP.md`](ROADMAP.md) 维护。

## 成熟度

RWB 处于**内部技术 alpha**：核心文件契约、解析和确定性验证可供开发与集成试验使用；尚不构成面向普通研究者的完整产品，也不对科研结果作质量保证。

Phase A / M8 Core Formalization 已在 `develop@ead1270` 完成契约收口。Phase B / M9-001～006 已在
阶段 PR #33 完成实现与本地验证，等待 R2 跨负责人审查和 CI 接受。这里的“完成”指需求、供给、
生命周期、Protocol、Snapshot 与 migration/replacement 契约闭合，不表示 Runtime 已消费这些对象。

## 已实现

| 能力 | 当前覆盖 |
|---|---|
| 版本化对象 | Task、Assignment、Handoff、Evidence、Claim、Decision、Protocol、Receipt 等 Schema 与示例 |
| Method-aware control | 两个正式 Mode 的 16 个逻辑 Action、跨 v0.1/v0.2 的 32 个版本化 Action 文档、hash-pinned Registry，以及八组 `diagnostic case → bounded TaskPacket → Method Resolution`；Resolution 继承 Action Gate/Artifact/stop/block 且不绑定供应实现 |
| Mode compatibility | v0.1/v0.2 Mode 并存，显式 v0.1→v0.2 迁移器与两个 exact-pin migration record；Registry 追加同 Action 新版本不改变旧 migration replay |
| Authority Rule Eligibility | v1 Matrix 与九个 hash-pinned eligibility record 只判断“假设 asserted facts 成立时 actor 是否匹配 operation rule”；不证明事实、不记录 Human approval、不授予 Permission、不提升 Claim、不执行决定 |
| Capability Requirement | 四个被八组 Method Resolution 复用的需求 ID 已成为不可变、hash-indexed 的需求侧契约；Task↔Method↔Requirement 引用可闭合，且契约拒绝 Provider/Model/Adapter、供给状态与 fallback |
| Skill Need / lifecycle v2 | 三个版本化 Need 只声明 gap、baseline、expected increment 与证据要求；lifecycle 将 intake、evaluation、Human admission、runtime eligibility、superseded/retired 分离，并以 append-stable migration 保留旧 Registry 解释 |
| Protocol Profile | 两个有界 PRISMA/V&V profile 只增加 method obligation 与 Gate/evidence expectation，不复制 Mode、不绑定 Skill/Tool/Provider，也不建立全局研究 DAG |
| Capability supply / Snapshot | Requirement→Supply Report→Resolution→Snapshot Core 支持 no-Skill、direct Tool 与 Adapter/Provider；Skill Supply 额外要求 lifecycle runtime eligibility，Snapshot 固定 exact supply/hash 与 permission/data-egress/side-effect 边界 |
| Phase B Gate | hash-bound Gate 固定 Task/Mode/Action/Method/Requirement、A/B Snapshot 与两类 migration；供给替换不能放宽边界或赋予 Runtime Method authority |
| 确定性验证 | Schema、引用、哈希、权限交集、Handoff lock、Claim 支持关系 |
| Task 解析 | Task + Agent Profile + 显式或 Registry Skill 的冻结 Assignment、权限交集与版本锁 |
| Legacy Skill 兼容 | accepted Registry 的 active / legacy / deprecated 历史选择边界与精确版本继续可验证；新绑定使用 lifecycle v2 eligibility |
| 文件式连续性 | Main State、checkpoint、resume-check、受控 Handoff 与归档约定 |
| Execution Trace | Envelope、Index、append-only events、工具结果持久化与闭集校验 |
| Legacy execution bridge | 既有 Skill-bound Assignment 到 Trace / Receipt 的适配和恢复检查 |
| Provider seam | provider-neutral 的隔离会话接口、离线 probe 与合成 conformance 基础 |

## 受限或尚不可用

| 范围 | 限制 |
|---|---|
| Method-aware control continuation | Capability binding 的 Runtime consumer 与 Method Trace 尚未实现；Snapshot 只冻结执行输入，Mode/lifecycle migration 不迁移历史 Resolution、Assignment、Receipt 或 Trace，Authority Rule Eligibility 也不执行决定 |
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
