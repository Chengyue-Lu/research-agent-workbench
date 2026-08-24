# Phase B Evolution Foundation 风险台账

| ID | 类型 | 风险 | 当前控制 | 状态 |
|---|---|---|---|---|
| PBE-DEMAND-001 | fact | Capability Requirement 若包含 available/gap、Provider 或具体 Tool/Skill，会把供给状态提前写回 Method。 | M9-001 Schema additionalProperties=false；对抗测试拒绝 supply/binding/routing 字段；供给结果由 Snapshot/Resolver 单独表达。 | controlled by implementation evidence |
| PBE-IDENTITY-001 | fact | 裸 Requirement ID 若解析到 active/latest 或可变 Registry，会静默改变旧 Method 的含义。 | 四个 M8 ID 直接映射到唯一不可变文档；index 固定 path/hash；published identity policy 禁止同 ID 改写、移动或删除。 | controlled by governance and closure tests |
| PBE-SKILL-001 | fact | Skill Need、candidate、accepted 与 active 若混成一个状态机会绕过证据准入。 | M9-002/003 分离 Need identity、intake、evaluation、admission 和 runtime eligibility。 | open until M9-003 |
| PBE-SNAPSHOT-001 | fact | Snapshot 若由单侧定义，可能让 Method 选择 Provider，或让 Runtime 放宽 Method/permission/data ceiling。 | M9-005 作为跨负责人共享 R2 接口，先冻结 producer/consumer 与 authority，再实现。 | open until M9-005 |
| PBE-MIGRATION-001 | fact | 原位扩展 lifecycle 或 Registry identity 会改变历史 Assignment 解释。 | published identity append-only；语义变化升版；迁移显式、hash-bound、可重放。 | open until M9-003/006 |
| PBE-PROTOCOL-001 | inference | Protocol Profile 容易复制 Mode Action 并形成固定学科流程。 | 只用两个有界 profile 证明标准约束增量；Mode/Protocol/Strategy 保持正交。 | open until M9-004 |
| PBE-EVAL-001 | fact | Schema/fixture 通过可能被误写成 Skill 或 Capability 的科研净收益。 | Phase B 只声称契约与迁移闭合；净增量由 Phase D forward evaluation 决定。 | accepted limitation |
| PBE-SCOPE-001 | fact | 把 Execution View、Receipt、API/Runtime 或 Method Trace 纳入 Phase B 会重新形成跨线大爆炸。 | 非目标显式排除；共享 Snapshot 只冻结供给，不执行任务。 | controlled by scope |
| PBE-CONTEXT-001 | inference | Phase B 文档和候选材料较多，主 Agent 全量读取会造成上下文超载和错误引用。 | 按 Task 白名单读取；主上下文只保留契约、风险、索引和下一动作。 | controlled by process |
