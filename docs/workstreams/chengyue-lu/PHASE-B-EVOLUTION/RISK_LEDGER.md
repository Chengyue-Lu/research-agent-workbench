# Phase B Evolution Foundation 风险台账

| ID | 类型 | 风险 | 当前控制 | 状态 |
|---|---|---|---|---|
| PBE-DEMAND-001 | fact | Capability Requirement 若包含 available/gap、Provider 或具体 Tool/Skill，会把供给状态提前写回 Method。 | M9-001 只允许需求、边界和验证期望；供给事实与选择分别留给 Supply Report 和 Capability Resolution。 | open until M9-001 |
| PBE-IDENTITY-001 | fact | Requirement ID 若解析到 active/latest 或可变 Registry，会静默改变旧 Method 的含义。 | M9-001 必须使用 immutable identity 与 exact path/hash closure；同 identity 的改写、移动或删除由 published identity policy 阻断。 | open until M9-001 |
| PBE-NEED-EVIDENCE-001 | fact | 若把 trial/evaluation/promotion result 持续追加进 Skill Need，Need identity 会变成实验日志并随结果漂移。 | M9-002 只保存 criteria、required evidence classes 与 baseline/expected increment；实际结果进入独立 Evaluation/Trial Record，lifecycle 只引用。 | open until M9-002/003 |
| PBE-SKILL-001 | fact | Skill Need、实际 evaluation result、candidate、accepted 与 runtime-eligible 若混成一个状态机会绕过证据准入。 | M9-002/003 分离 Need identity、Evaluation/Trial Record refs、intake、evaluation state、admission 和 runtime eligibility；Skill Supply Extension 只接受 runtime-eligible Skill。 | open until M9-003/005 |
| PBE-SUPPLY-AUTH-001 | fact | Supply Report 若能自选、排序或声明 fallback，会让 Provider/Adapter 事实报告变成隐藏 Router。 | Report 只陈述 identity/capability/I-O/边界/conformance/availability/limitations；选择与 gap/ambiguity/blocked 只由受 Authority ceiling 约束的 Capability Resolution 表达。 | open until M9-005 |
| PBE-SNAPSHOT-001 | fact | Requirement 直接跳到 Snapshot 或 Snapshot 由单侧定义，可能隐藏供给比较、让 Method 选择 Provider，或让 Runtime 放宽 Method/permission/data/side-effect ceiling。 | M9-005 显式拆成 Report→Resolution→Snapshot，并作为跨负责人共享 R2 接口先冻结 producer/consumer、authority 与 ceiling。 | open until M9-005 |
| PBE-SNAPSHOT-DEPENDENCY-001 | fact | 用完整 Skill lifecycle 阻塞 Snapshot 会把 no-Skill/direct Tool/Adapter/Provider Core 与 Skill 准入错误耦合。 | Snapshot Core 只依赖 M9-001/M8-005；Skill Supply Extension 单独等待 M9-003 runtime eligibility。 | open until M9-005 |
| PBE-MIGRATION-001 | fact | 原位扩展 lifecycle 或 Registry identity 会改变历史 Assignment 解释。 | published identity append-only；语义变化升版；迁移显式、hash-bound、可重放。 | open until M9-003/006 |
| PBE-PROTOCOL-001 | inference | Protocol Profile 容易复制 Mode Action 并形成固定学科流程。 | 只用两个有界 profile 证明标准约束增量；Mode/Protocol/Strategy 保持正交。 | open until M9-004 |
| PBE-EVAL-001 | fact | Schema/fixture 通过可能被误写成 Skill 或 Capability 的科研净收益，或让 lifecycle 膨胀为第二套评测框架。 | Phase B 只声称契约、状态和引用闭合；minimal Evaluation Manifest 可在 M9-002 后并行，完整 metrics/experiment 与净增量判断留给 Phase D。 | accepted limitation |
| PBE-HOLD-001 | fact | 把 Snapshot Core 接受误写成全面 Runtime/Recovery 解冻，会绕过 Research State、Failure/Attempt 与 Method Trace。 | Topic 4 只解冻 thin-layer Snapshot 消费与边界 enforcement；Topic 5 继续等待 Phase C minimum，且两组允许/禁止项显式列出。 | controlled by roadmap gate |
| PBE-SCOPE-001 | fact | 把 Execution View、Receipt、API/Runtime 或 Method Trace 纳入 Phase B 会重新形成跨线大爆炸。 | 非目标显式排除；共享 Snapshot 只冻结供给，不执行任务。 | controlled by scope |
| PBE-CONTEXT-001 | inference | Phase B 文档和候选材料较多，主 Agent 全量读取会造成上下文超载和错误引用。 | 按 Task 白名单读取；主上下文只保留契约、风险、索引和下一动作。 | controlled by process |
