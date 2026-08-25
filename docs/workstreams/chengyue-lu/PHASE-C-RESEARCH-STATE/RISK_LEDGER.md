# Phase C Research State & Verification 风险台账

| ID | 类型 | 风险 | 控制 | 状态 |
|---|---|---|---|---|
| PCRS-IDENTITY-001 | fact | 原位扩写 v0.1 Attempt/Decision/Trace 会改变旧工件解释。 | Phase C 使用新版本 Schema；旧 fixtures 继续跑 compatibility regression。 | controlled by versioned contract |
| PCRS-ONTOLOGY-001 | inference | 为 Unknown、Contradiction、Assumption、Frontier 各建对象会膨胀为知识图谱。 | Unknown/Assumption 为 State item，Contradiction 为 relation，Frontier derived；只有失败案例证明需要独立 lifecycle 才升级。 | controlled by representation tests |
| PCRS-FAILURE-001 | fact | Attempt `failed`、异常文本或 negative Evidence 可能冒充 durable Research Failure。 | Failure 强制 learned result、revisit condition、source Attempt 与独立 Evidence refs。 | controlled by schema and semantic validator |
| PCRS-LINEAGE-001 | fact | predecessor Attempt 与 from-State 混同会伪造一对一 State transition。 | 三种关系使用不同字段与负面/多对一 fixtures；不按时间戳推断。 | controlled by lineage suite |
| PCRS-REOPEN-001 | fact | revisit condition 或 reopen ref 可能被 Runtime 当成 retry/replan 授权。 | 契约与 validator 明确 refs 仅解释，不产生控制权限；无自动执行 API。 | controlled by authority regression |
| PCRS-DECISION-001 | fact | Authority eligibility 可能被误写成人类批准或 State effect。 | actual Human Decision 单独记录 actor/provenance/scope/refs/effect；eligibility wrong-kind fixture 必须失败。 | controlled by Decision tests |
| PCRS-SCIENCE-001 | fact | 结构 validator 可能越权声明 support/contradict 的科学真实性。 | 只验证 ref/hash/type/relation shape；Human rubric 独立。 | accepted limitation |
| PCRS-TRACE-001 | fact | 把 Method Trace 塞入 Execution Trace 会混淆科研轨迹与 operational events。 | 独立 ref-only contract；Execution Trace 不改。 | controlled by module/schema separation |
| PCRS-BINDING-001 | fact | selected Snapshot 被误作 actual supply binding。 | gap-only 与 coverage-complete 两个互斥状态；没有 accepted producer 时 captured 必须 fail closed。 | controlled by adversarial fixture |
| PCRS-SESSION-001 | fact | session/thread/runtime identity 被当作 durable State。 | State identity/revision 独立，schema 禁止 session fields，fresh-process case 不提供 session history。 | controlled by schema/isolation tests |
| PCRS-GATE-001 | fact | Schema happy path 被误报为 Phase C 或 Topic 5 完成。 | Gate 同时要求 negative suite、两案 fresh process、read log、private oracle 和具名 Human/R2 review。 | pending R2 closeout |
| PCRS-TOPIC5-001 | fact | Phase C 合并被解释为自动批准 recovery/salvage/multi-Agent。 | closeout 只允许 Topic 5 重新进入设计审查；实现仍冻结。 | controlled by docs and status |
