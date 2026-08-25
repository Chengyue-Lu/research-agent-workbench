# 架构演进路线图

状态：方向与依赖基线；不记录逐项实时状态

更新：2026-08-25

逐项状态和唯一下一任务只在 [`TASKS.md`](TASKS.md) 更新。本文件说明依赖顺序、阶段 Gate 与
停止条件，不是工期承诺，也不是研究项目必须遵循的固定流程。

## 1. 总体顺序

| Phase | 目标 | 主要产物 | 启动条件 |
|---|---|---|---|
| A — Core Formalization | 把 Mode-first 方法论变成正式语义 | Mode Action、Method Resolution、Mode v0.2、Decision Authority | ADR-0013/0016 |
| B — Evolution Foundation | 支持可迁移、可评测的能力演化 | Skill Need、Lifecycle v2、Migration、Protocol、Resolved Capability Snapshot | Phase A 稳定接口 |
| C — Research State & Verification | 保存跨 Runtime 的研究意义 | State/Frontier、Failure、Evidence–Claim relation、Method Trace | A；部分依赖 B |
| D — Evaluation Loop | 证明新增机制的净增量 | Evaluation Manifest、baseline harness、method/skill metrics | A；minimal Manifest 在 M9-002 稳定后并行启动 |
| E — Strategy & Governed Evolution | 有界吸收新策略和外部候选 | Strategy interface、candidate pipeline、merge/prune/promotion | B+C+D |
| F — Execution Reintegration | 让 Runtime 消费冻结科研契约 | M11 Core：runtime bundle、supply-neutral resolved execution、Thin Host、Trace/Receipt integration；可选 Skill supply：release projection、统一 View semantic mapping | ADR-0019；M9-005 Core；Phase C minimum 再解除 Topic 5；release projection 不 Gate Topic 4 Core |

Phase 不是一条科研 DAG。它只表示框架接口的构建依赖；真实 Task 仍按 Mode/Action 选择路径。

### 1.1 Phase / Topic 与 M Task

本文件只回答 Phase 的 macro maturity、Topic responsibility、architecture Gate 以及为什么某类工作允许或
冻结。日常施工的 status、hard dependency、owner、scope、negative acceptance 与 evidence 只由
[`TASKS.md`](TASKS.md) 的 M Task 控制：

```text
Phase = when / macro Gate
Topic = responsibility navigation
M Task = what to build / branch / PR / CI identity
```

一个 Phase 聚合多个 M Task，一个 M Task 可以跨多个 Topic。ROADMAP 中出现但 TASKS 中没有 ID 的近期
工作不能直接实现；必须先建立 docs-only `task-definition`。若两者对当前施工顺序表述冲突，TASKS 控制
implementation scheduling，ROADMAP 的 architecture freeze 仍是上限，Task 必须据此标为 BLOCKED/PARKED。

## 2. Phase A：Core Formalization

1. 把两个正式 Mode 的 Action Catalog 转成版本化、可引用文档；
2. 新增 provider-neutral `Method Resolution`；
3. 将八个既有 routing fixture 无损转换为正式 Resolution fixture；
4. 建立 Research Mode v0.2，移除直接 Skill recommendation；
5. 冻结 Mode/Action/Mechanism/Skill/Tool/Claim/permission 的 Decision Authority；
6. 明确稳定 Core invariants 与 replaceable implementation boundary。

停止 Gate：

- `Task → Method Resolution → Execution` 成为明确接口；
- no-Skill、tool-only、Human Gate、split、blocked 都能正式表达；
- 新 Mode 不再隐式携带 Skill；
- 在 Gate 通过前不新增 accepted Skill 或正式 Mode。

### Phase A 收口判定（2026-08-24）

**PASS — Core contract closure。** M8-001～005 已在 PR #30 接受 R2 跨负责人审查，并以
`develop@ead1270` 形成集成边界：Mode Action、Task-bound Method Resolution、Research Mode v0.2
migration 与 Authority Rule Eligibility 均有版本化对象、确定性验证和正反 fixture。

这里的 `Task → Method Resolution → Execution` Gate 指稳定的输出/消费接口已经明确：Method
Resolution 只产生需求、Gate、blocked 与最小机制语义，供后续 Capability / Execution 层消费；它不表示
Capability binding、Resolved Execution View、Receipt migration 或 Runtime consumer 已实现。后者继续属于
Phase B/F，不能反向写成 Phase A 未完成，也不能借 Phase A 收口宣称端到端执行闭环。

## 3. Phase B：Evolution Foundation

Phase B 保持“需求语义先于供给绑定”的顺序：

1. `Capability Requirement` 先成为 provider-neutral 的需求侧契约，不表达 available/gap 或具体供给；
2. 具名 Maintainer 可在独立 triage 后把可复用语义缺口发布为版本化 `Skill Need`，定义 gap、
   direct/no-Skill baseline、预期增量、evaluation criteria、
   required evidence classes 与 domain scope/variants；它不累积实际 trial/evaluation/promotion 结果；
3. lifecycle v2 分离 intake、evaluation state、admission 与 runtime eligibility，引用 baseline/trial/
   evaluation record/decision 和 promotion evidence；完整 benchmark/metric/experiment framework 留在 Phase D；
4. Protocol Profile 独立表达 PRISMA、V&V 或项目方法标准的适用性、method obligations 与 Gate/evidence
   expectations，不复制 Mode Action、不固定研究 DAG，也不绑定 Skill/Tool/Provider；
5. M9-005 建立显式供给缝：`Capability Requirement → Capability Supply Report(s) → Capability Resolution
   → Resolved Capability Snapshot`。Report 只陈述 supply identity、实现版本/hash、能力、I/O、权限、
   data-egress、副作用、typed conformance artifact、scoped availability 与限制，不拥有选择、fallback、Method、Claim 或
   Human Gate authority；Resolution 比较零个或多个 Report 并给出 satisfied/gap/ambiguous/blocked；
   Snapshot 区分不具执行资格的 `structural-replay` 与具有非 fixture typed-evidence 资格、仍待 Topic 4
   完成最终执行准入的 `runtime-execution`；
6. migration 保持 append-only 和显式调用。Phase A 的 Mode v0.1→v0.2 是首个已完成 exemplar，Phase B
   不重造通用 migration framework，只在新增对象确有版本迁移需求时扩展。

`Capability Requirement` 是 Runtime 主链的需求入口；它只有在具名 Maintainer 独立 triage 后才可形成
`Skill Need`，capability gap/failure 不自动完成该转换。两者可在冻结共同引用语义后顺序推进；M9-004
Protocol Profile
与 M9-002/003 并行，不阻塞 M9-005。M9-005 的 Snapshot Core 只依赖 M9-001 与 M8 Decision Authority，
先覆盖 Method no-Skill 对应的 procedure、direct Tool、Adapter/Provider supply facts 的 structural replay；
fixture 不得声明 final effective boundary 或 execution eligibility。Skill 作为合法供给候选的扩展额外等待
M9-003，并且新绑定还必须解析独立 evidence 与 Human decision。Resolved Capability Snapshot 涉及
Method 与 Provider 两侧，必须跨负责人审查：路诚钺维护需求词汇、Resolution/Snapshot authority ceiling
与 provider-neutral fixture，黄毅维护 Adapter/Provider 的真实供给映射与 conformance。Phase B 不接管
API/Runtime 实现。

停止 Gate：至少一个 fixture 在 Task、Mode、Action、Method Resolution 与 Capability Requirement 均不变时，
将 Supply A/Snapshot A 替换为 Supply B/Snapshot B；permission、data-egress 与 side-effect ceiling 不放宽，
Runtime 不获得 Method authority，旧研究对象仍可解释和重放。

### Phase B 实现判定（2026-08-25）

**IMPLEMENTED AS STRUCTURAL CONTRACT。** M9-001～006 已形成 Requirement、Need、lifecycle v2、两个
bounded Protocol Profile、typed Report→Resolution→两级 Snapshot、repository-wide structural consumer 与
Skill Supply
Extension。M9-006 Gate 固定同一 Task/Mode/Action/Method/Requirement，并证明 Supply A→B 只改变 exact
supply，三类 Supply boundary facts 保持一致；Research Mode 与 Skill lifecycle
migration 均保持 exact-pin replay。

此判定不证明 live Provider 可用、Skill 科研净收益、Human Decision 或真实执行。当前三条 fixture 都是
`structural-replay`；Topic 4 thin consumer 只能接受未来完整验证的 `runtime-execution` Snapshot。Topic 5
仍保持冻结。

### Topic 4 thin-layer Architecture Hold

以下四项是 Phase B 已接受的供给侧前置契约：

- Capability Requirement；
- Capability Supply Report；
- Capability Resolution boundary；
- Resolved Capability Snapshot Core。

依据 [ADR-0019](decisions/0019-OPTIONAL-MAINTAINER-SKILL-EVOLUTION-OUTER-LOOP.md)，Topic 4 将 Core 与可选
Skill Runtime Extension 拆成两条依赖。

**Topic 4 Core Gate**：

- `runtime-bundle` 使用显式 closure manifest，不接受目录输入，不递归扫描 `registry/examples`，import
  graph 不包含 Skill Need、Candidate、Evaluation 或 Lifecycle validator；
- no-Skill、direct Tool、procedure 与 Adapter/Provider 可以在零 Skill、零 Evolution Registry 情况下形成
  Resolved Execution View；
- 供给更新创建新的 Resolution/Snapshot/View，不能改变运行中的冻结输入；gap/failure 不自动创建 Skill Need。

Topic 4 的 implementation vocabulary 已落到 M11：M11-001 Runtime Bundle/Profile → M11-002
supply-neutral Resolved Execution View → M11-003 Thin Execution Host → M11-004 generic Trace/Receipt Core
Gate。M9-005 accepted contracts 允许 M11-001 READY；Core 按依赖推进 no-Skill/direct Tool/procedure/
Adapter-Provider 路径，不等待 SkillReleaseProjection。四层是可独立验收的 producer/consumer contracts，
按一 dependency layer 一 feature PR 推进，不使用 R2 atomic completion 跨层合并。

**Skill Runtime Extension Gate**：

- M11-005 SkillReleaseProjection 只发布不可变、exact hash-pinned 的 Skill Release；
- Projection contract 被接受且 exact-pin validation 可用后，才启用 Skill-bearing binding；
- 投影未实现、缺失、stale 或不匹配时，Skill new-binding fail closed，且不得回退读取完整 Lifecycle；
- M11-006 由 View/Capability semantic owner 将 eligible Skill supply 映射进统一、supply-kind-neutral 的
  Resolved Execution View；不建立 Skill-specific Runtime seam。它可在明确需求出现后与 Topic 4 Core
  分层推进，不阻塞任何非 Skill Core 路径；M11-005/006 当前均 PARKED。

解冻范围只包括 Topic 4 的上游 Research Control / View producer 冻结 external hash pin、执行时 freshness、
精确 Provider/Adapter/Model/Runtime/Host binding，以及 Task/Profile/DataPolicy/Host policy 与 selected supply
ceilings 的最终收紧交集；仅在 Skill Extension 存在时加入可选 Skill/Assignment。Execution Host 只消费
schema-valid、closure-valid 的 `runtime-execution` Snapshot 与 exact frozen View、报告 actual execution facts，
并执行 permission/data-egress/side-effect boundary。它不得重新选择 Supply、在当前 View 内 rebind 或执行
automatic fallback；model auto-routing、multi-Agent orchestration、critic voting、hidden routing，以及
Runtime 修改 Method、Claim 或 Gate 继续禁止。

## 4. Phase C：Research State 与 Verification

Phase C 的唯一 implementation chain 是：

```text
M10-001 minimal Research State
→ M10-002 Attempt / Research Failure
→ M3-009 Method Trace v0.1
→ M10-003 bounded verification Gate
```

最小起步对象为 Question、Evidence、Claim、Unknown、Contradiction、Assumption、Decision、Attempt、
Failure 和 Frontier item。Failure 至少记录 learned result 与 revisit condition。M4-001～004 是 provenance/
promotion/reproduction supporting Tasks，不替代上述 Phase C closeout chain。

Method Trace 在 M3-008 可观察执行 Trace 之上增加：Mode proposed/resolved、Action selected、Mechanism
selected/rejected、Capability resolved、actual capability/supply binding、Human Gate、Evidence change、
Claim promotion/rejection、safe pause、failure 与 reopen condition。M3-009 等待 M9-005；在 Snapshot
contract 稳定前不得自建临时 Capability-resolved event schema。

不一次建设统一知识图谱。先用 evidence-synthesis 与 simulation 两个真实案例证明 compact index、
跨 Runtime 恢复和 reviewer-facing verification 有用。

Topic 5 继续冻结，直到 minimal Research State、Failure/Attempt semantics 与 Method Trace v0.1 均完成。
该 Gate 通过后才恢复 Handoff、context rollover、safe pause、recovery 与 salvage/clean recovery 的后续
扩展；M9-005 或 Topic 4 的解冻不能替代 Phase C 的状态与失败语义。

Topic membership 按 Task objective 判断：只有改变 Handoff、context rollover、safe pause、recovery、
salvage/clean recovery 或 continuation semantics 的 Task 才属于 Topic 5。M11-003/004 仅实现 Topic 4
Thin Host、actual fact reporting 和通用 observability closure；使用 Trace/Receipt 不使其成为 Topic 5
Task，也不绕过上述 freeze。

## 5. Phase D：Evaluation Loop

正式比较至少包含：

1. Plain Agent；
2. Plain Agent + Tool；
3. Mode + no-Skill/direct-tool；
4. Mode + candidate Skill。

M9-002 的 Skill Need 稳定后，M5-003 即可并行启动最小 Evaluation Manifest/baseline harness；它保存实际 baseline/trial/evaluation
条件与结果，Need 本体只声明 evaluation criteria 和 required evidence classes。M9-003 lifecycle 引用这些
record，不在 Phase B 重建完整 benchmark、metric 或 experiment framework。

Evaluation Manifest 冻结 Task、Model、Host、Tool/Resolved Capability Snapshot、预算与上下文。指标优先包括
method violation、Claim overreach、provenance error、counterevidence omission、human correction
distance、rework、context、cost 和 completion time。确定性评分与盲化人工样本分层；单次成功不
构成 promotion。

## 6. Phase E/F 边界

第一版 Strategy 只需 `direct` 加至多一个实验策略，且 direct 永远保留为基线。外部发现、自动
生成、repair/merge/prune 只作用于 candidate。

Execution reintegration 不授权 Runtime 定义 Mode、Claim、supply/Skill fallback、rebinding、silent
replacement 或权限放宽。接入前必须
解决 from-state predecessor、严格 completion marker、Evidence source binding、Tool side-effect
accounting、deadline/cancellation 和 current-main fixture 再生等已知问题。

Runtime 也不创建 Skill Need/Candidate、不执行 Trial/Evaluation/Promotion、不读取完整 Lifecycle。Skill
供给通过已发布投影进入 Capability Supply Report；no-Skill/direct Tool 路径不依赖该投影。可选
Capability Diagnostic/feedback bridge 等待 Phase C Failure/Trace 与 privacy 语义稳定，不阻塞 Topic 4。

Phase F 实施只按 M11-001～004 Core 与 M11-005～006 optional Skill supply publication/mapping 推进；M6-003 保留为历史
compatibility seam，不再充当未来执行 umbrella。M6-004 只验证 Provider/isolated session 的 live
conformance，在 M6-001/002 后由具名 live authorization 解阻；它不 hard-depend M11-004，也不替代
M11-004 的 Task→View→Host→generic Receipt Gate。

## 7. 不在近期关键路径

- 新增大量正式 Mode 或 accepted Skill；
- 通用多 Agent Supervisor、团队拓扑或全局 DAG；
- Tool marketplace 或内建大规模科学工具库；
- 长期 conversation memory；
- 更多 Provider 接线；
- 自动修改 Core；
- 没有真实消费者的数据库、消息总线或 distributed runtime。

## 8. 长期成功判据

- 更换 Model/Runtime/Tool/Skill 后，Research State 与 Method contract 仍可复用；
- 旧对象跨版本迁移和历史 Attempt 解释可复现；
- Method violation、Claim overreach、provenance error 和重复失败率下降；
- Skill measured increment 能相对简单基线说明；
- Trace 能让 reviewer 重建关键决定而无需加载完整历史；
- 至少一项复杂控制因无增量而被删除或简化。
