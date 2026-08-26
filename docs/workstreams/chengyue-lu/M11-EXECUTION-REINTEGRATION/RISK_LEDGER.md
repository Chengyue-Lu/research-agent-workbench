# M11 Execution Reintegration 风险台账

| ID | 类型 | 风险 | 控制 | 状态 |
|---|---|---|---|---|
| M11-ORDER-001 | fact | 单 PR 中提前实现后继层，绕过 producer/consumer dependency review。 | 每层独立 commit/test/evidence；前层未闭合立即停止；最终按 DAG 逐 Task 验收。 | controlled; four ordered commits/layers and task-specific evidence |
| M11-BUNDLE-001 | fact | Runtime Bundle 复用全仓递归 validator，隐式读取 Evolution Registry。 | manifest-only exact closure；拒绝目录/root scan；import graph 与 source-import 负面测试。 | controlled; focused/repository/full unit tests pass, remote matrix CI pending |
| M11-SKILL-001 | fact | SkillReleaseProjection 或 Lifecycle 反向成为 no-Skill Core 前置。 | M11-001～004 zero-Skill Gate；M11-005/006 保持 PARKED。 | active |
| M11-AUTH-001 | fact | View/Host 从 Supply metadata 生成权限、fallback 或 Method authority。 | 最严 intersection；selection/permission/Claim/Gate/Human boundaries；fail closed。 | View/Host controlled by M11-002/003 focused/repository/full tests; remote matrix pending |
| M11-REBIND-001 | fact | Host 在冻结 View 内静默更换 Provider/Tool/Supply。 | exact pins；pre/post binding equality；失败只能报告 bounded diagnostic/re-resolution request。 | controlled by M11-003 focused/repository/full tests; remote matrix pending |
| M11-TOPIC5-001 | fact | Trace/Receipt 或 pause/error handling 被扩大为 Topic 5 recovery。 | M11 只报告 facts；不实现 Handoff/context/recovery/continuation semantics。 | controlled by schemas/source/negative/full tests; remote matrix pending |
| M11-RECEIPT-001 | fact | execution completion 被写成 Claim promotion、Human acceptance 或伪造 Skill Assignment。 | generic linkage 与 legacy replay 负面测试；科学/人类 authority 保留。 | controlled by M11-004 vertical/replay/full tests; remote matrix pending |
| M11-STAGE-001 | fact | module-level PR 被误解为合并 Task identity、人工豁免或放宽证据。 | 适用 canonical module-level rule；READY 入口、base-DONE 外部依赖、连通 DAG、四个独立 commit/slice/evidence 与最高 R2 review 均保留。 | controlled by governance tests and PR evidence |
| M11-CLOSURE-001 | fact | Runtime 丢失 multi-candidate Resolution 语义，或 Host/Trace/Receipt 只校验单对象 hash 而不校验 selected/actual closure。 | Runtime 只读取 selected closure但验证 selected 属于完整 candidate/comparison set；View/Host/Trace/Receipt 对 actual binding、Supply、provider/tool identity/count 与 Bundle lineage 交叉校核。 | controlled by focused adversarial tests; remote CI pending |
| M11-ENFORCEMENT-001 | fact | 将 Driver 自报后的 boundary violation 棋盘式检测描述成调用前预防。 | Host 报告明确区分 preventive controls（binding/freshness/Bundle integrity）与 detective controls（egress/effect/budget/artifact/output 等），且 `driver_claims_trusted=false`。 | controlled by schema/API/tests; stronger sandbox enforcement remains external |
