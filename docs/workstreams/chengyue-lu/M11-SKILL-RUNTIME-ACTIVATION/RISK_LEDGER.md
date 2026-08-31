# M11 Skill Runtime Activation Risk Ledger

| Risk ID | Type | Risk | Control | Status |
|---|---|---|---|---|
| M11-ACT-AUTH-001 | authority | READY 被误读为实现验收、真实 Skill 准入或 Runtime new-binding permission。 | 明确 READY 只恢复施工入口；DONE、Admission、Projection publication 与 Runtime qualification 各自保留独立 Gate。 | controlled by canonical wording and R2 review |
| M11-ACT-DAG-001 | governance | M11-006 从 PARKED 被独立偷渡为 DONE，或 implementation PR 缺 READY anchor。 | 本 PR 只激活 M11-005；后继 PR 必须证明从 M11-005 出发的连通 DAG、拓扑顺序及逐 Task commit/evidence。 | controlled by Governance v2 and PR evidence |
| M11-ACT-CORE-001 | architecture | optional Skill extension 反向成为 zero-Skill/direct Tool Core 前置。 | Core 已由 M11-001～004 独立闭合；activation 文档继续声明 projection 缺失只阻断 Skill candidate。 | controlled by unchanged Core contracts |
| M11-ACT-SCOPE-001 | contract | activation PR 借状态变化改写 Task identity、dependency、acceptance 或实现契约。 | 写入限于状态真值、派生导航、workstream 与 Attempt record；feature implementation 保持在独立 PR。 | controlled by status-only feature diff |
| M11-ACT-REVIEW-001 | process | 具名 owner 的启动决定被误作跨 owner 技术验收。 | activation 与 implementation review 分离；Runtime/View 相关最终 diff 仍需 cross-owner R2 review。 | open until activation PR review |
