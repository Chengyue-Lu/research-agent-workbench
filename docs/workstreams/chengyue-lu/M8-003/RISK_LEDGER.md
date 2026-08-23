# M8-003 风险台账

| ID | 类型 | 风险与边界 | 处置 | 状态 |
|---|---|---|---|---|
| M8R-DAG-001 | inference | Resolution 被扩成固定全局流程或 Blueprint，会固化学科思维。 | 每个 Resolution 只选择当前 Task 的必要 Action/机制；不建立全局 Resolution Registry。 | controlled |
| M8R-BIND-001 | fact | 在 Resolution 写入 Provider/Model/Runtime/具体 Tool 或 Skill，会形成第二 Router。 | Schema additionalProperties fail-closed，只有抽象 Capability 与 Skill Need；实现 binding 延后。 | controlled |
| M8R-NOSKILL-001 | fact | 把 no-Skill 伪装成空 Assignment 会恢复 legacy Skill coupling。 | `no-skill` 是正式 disposition；Schema 不含 Assignment 字段。 | controlled |
| M8R-ACTION-001 | fact | Resolution 引用 Action 但不固定内容，会在 Action 更新后失去历史解释。 | formal `action_ref` 必须同时固定 Registry content hash。 | controlled |
| M8R-CLOSURE-001 | fact | 顶层 Need/Gate/block 与 action decision 不一致会产生两个事实源。 | validator 要求三组集合精确闭合并覆盖 drift 负面测试。 | controlled |
| M8R-SEMANTIC-001 | fact | 机器只能验证 obligation 结构和引用，不能判断其科学上是否满足。 | assessment 明确 deterministic/semantic/human/unavailable；不自动接受结果。 | controlled |
| M8R-TASKREF-001 | limitation | 八个诊断 case 没有完整冻结 Task Packet，因此 fixture task_ref 只有 ID/revision。 | 正式受控执行要求后续 Task snapshot/hash；本节点不伪造 Task bytes。 | accepted limitation |
| M8R-XLINE-001 | fact | 直接把 Resolution 塞进 Assignment/Receipt 会跨越 owner 和 Architecture Hold。 | Resolved Execution View 进入节点审查后的独立共享接口 Task。 | deferred |
| M8R-STACK-001 | fact | 两条活动分支与两个 PR 会把一个连续契约节点拆成重复审查和易漂移的交付单元。 | 原 M8-002 与 M8-003 历史合流到单一活动分支；旧分支与 PR #26 只保留为历史证据。 | controlled |
| M8R-GOV2-001 | fact | 隔离开发时 M8-003 曾从 PARKED 直接显示 IN_PROGRESS，不能原样成为 Governance v2 merge snapshot。 | 当前 feature diff 已收束为 M8-002 READY→DONE、M8-003 PARKED→READY；M8-003 completion 留给后续合法推进。 | controlled |
| M8R-RISK-001 | fact | Method Resolution 决定机制、Claim/Gate 控制条件，不能只按普通 Schema 视为 R1。 | Governance v2 将该 Schema/path 归为 R2；要求 authority basis、adversarial evidence、workstream/Risk Ledger 与 cross-owner review。 | controlled |
