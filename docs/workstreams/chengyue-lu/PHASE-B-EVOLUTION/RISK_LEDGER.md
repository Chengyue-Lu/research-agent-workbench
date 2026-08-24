# Phase B Evolution Foundation 风险台账

| ID | 类型 | 风险 | 当前控制 | 状态 |
|---|---|---|---|---|
| PBE-DEMAND-001 | fact | Capability Requirement 若包含 available/gap、Provider 或具体 Tool/Skill，会把供给状态提前写回 Method。 | M9-001 Schema 只允许需求、边界和验证期望；负面测试拒绝 supply/routing 字段。 | controlled by implementation evidence |
| PBE-IDENTITY-001 | fact | Requirement ID 若解析到 active/latest 或可变 Registry，会静默改变旧 Method 的含义。 | immutable identity、exact path/hash index 与 published identity policy 共同阻断改写、移动或删除。 | controlled by governance and closure tests |
| PBE-NEED-EVIDENCE-001 | fact | 若把 trial/evaluation/promotion result 持续追加进 Skill Need，Need identity 会变成实验日志并随结果漂移。 | M9-002 Schema 只保存 criteria、required evidence classes 与 baseline/expected increment；实际结果字段被拒绝。 | controlled by schema and adversarial tests |
| PBE-SKILL-001 | fact | Skill Need、实际 evaluation result、candidate、accepted 与 runtime-eligible 若混成一个状态机会绕过证据准入。 | lifecycle v2 分离各轴；repository validator 只允许 exact current/evidence-ready/Human-accepted/runtime-eligible Skill Supply。 | controlled by lifecycle and supply tests |
| PBE-SUPPLY-AUTH-001 | fact | Supply Report 若能自选、排序或声明 fallback，会让 Provider/Adapter 事实报告变成隐藏 Router。 | Report Schema 拒绝 selection/routing/authority；Resolution 状态与 selection 由确定性 resolver 重算。 | controlled by schema and resolver tests |
| PBE-SNAPSHOT-001 | fact | Requirement 直接跳到 Snapshot 或 Snapshot 由单侧定义，可能隐藏供给比较、让 Method 选择 Provider，或让 Runtime 放宽 Method/permission/data/side-effect ceiling。 | Report→Resolution→Snapshot lineage、Authority Matrix 与 M9-006 A/B Gate 均为 hash-bound；三类边界漂移会阻断。 | controlled by closure and replacement tests |
| PBE-SNAPSHOT-DEPENDENCY-001 | fact | 用完整 Skill lifecycle 阻塞 Snapshot 会把 no-Skill/direct Tool/Adapter/Provider Core 与 Skill 准入错误耦合。 | 三条 Core fixture 独立覆盖 no-Skill、Tool、Adapter/Provider；Skill eligibility 作为回调与 repository extension 单独验证。 | controlled by split implementation |
| PBE-MIGRATION-001 | fact | 原位扩展 lifecycle 或 Registry identity 会改变历史 Assignment 解释。 | published identity append-only；Mode 与 lifecycle migration 均 exact-pin、可重放且有 append-stability 负面/正面测试。 | controlled by M9-006 replay gate |
| PBE-PROTOCOL-001 | inference | Protocol Profile 容易复制 Mode Action 并形成固定学科流程。 | 两个 bounded profile 的 closed Schema 拒绝 Action、Skill/Tool/Provider/Runtime 和 global-DAG 字段。 | controlled by profile tests |
| PBE-GATE-OVERCLAIM-001 | fact | deterministic Gate PASS 可能被误读为真实执行、Provider conformance 或 Skill 科研价值已经成立。 | Gate Schema 强制六项 authority/runtime/live/value assertions 为 false；实现文档保留显式限制。 | controlled by schema and documentation |
| PBE-EVAL-001 | fact | Schema/fixture 通过可能被误写成 Skill 或 Capability 的科研净收益，或让 lifecycle 膨胀为第二套评测框架。 | Phase B 只声称契约、状态和引用闭合；minimal Evaluation Manifest 可在 M9-002 后并行，完整 metrics/experiment 与净增量判断留给 Phase D。 | accepted limitation |
| PBE-HOLD-001 | fact | 把 Snapshot Core 接受误写成全面 Runtime/Recovery 解冻，会绕过 Research State、Failure/Attempt 与 Method Trace。 | Topic 4 只解冻 thin-layer Snapshot 消费与边界 enforcement；Topic 5 继续等待 Phase C minimum，且两组允许/禁止项显式列出。 | controlled by roadmap gate |
| PBE-SCOPE-001 | fact | 把 Execution View、Receipt、API/Runtime 或 Method Trace 纳入 Phase B 会重新形成跨线大爆炸。 | 非目标显式排除；共享 Snapshot 只冻结供给，不执行任务。 | controlled by scope |
| PBE-CONTEXT-001 | inference | Phase B 文档和候选材料较多，主 Agent 全量读取会造成上下文超载和错误引用。 | 按 Task 白名单读取；主上下文只保留契约、风险、索引和下一动作。 | controlled by process |
