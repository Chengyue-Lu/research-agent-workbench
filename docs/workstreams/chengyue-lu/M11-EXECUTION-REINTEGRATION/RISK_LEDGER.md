# M11 Execution Reintegration 风险台账

| ID | 类型 | 风险 | 控制 | 状态 |
|---|---|---|---|---|
| M11-ORDER-001 | fact | 单 PR 中提前实现后继层，绕过 producer/consumer dependency review。 | 每层独立 commit/test/evidence；前层未闭合立即停止；最终按 DAG 逐 Task 验收。 | active |
| M11-BUNDLE-001 | fact | Runtime Bundle 复用全仓递归 validator，隐式读取 Evolution Registry。 | manifest-only exact closure；拒绝目录/root scan；import graph 负面测试。 | active |
| M11-SKILL-001 | fact | SkillReleaseProjection 或 Lifecycle 反向成为 no-Skill Core 前置。 | M11-001～004 zero-Skill Gate；M11-005/006 保持 PARKED。 | active |
| M11-AUTH-001 | fact | View/Host 从 Supply metadata 生成权限、fallback 或 Method authority。 | 最严 intersection；selection/permission/Claim/Gate/Human negative tests；fail closed。 | active |
| M11-REBIND-001 | fact | Host 在冻结 View 内静默更换 Provider/Tool/Supply。 | exact pins；失败只能报告 bounded diagnostic/re-resolution request。 | active |
| M11-TOPIC5-001 | fact | Trace/Receipt 或 pause/error handling 被扩大为 Topic 5 recovery。 | M11 只报告 facts；不实现 Handoff/context/recovery/continuation semantics。 | active |
| M11-RECEIPT-001 | fact | execution completion 被写成 Claim promotion、Human acceptance 或伪造 Skill Assignment。 | generic linkage 与 legacy replay 负面测试；科学/人类 authority 保留。 | active |
| M11-STAGE-001 | fact | 单 PR 组织被误解为修改 Task 定义或放宽证据。 | PR 明示具名指令与原 DAG；Task definition/acceptance 不变；每个 DONE Task 仍需具名证据。 | active |
