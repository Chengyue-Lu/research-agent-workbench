# Phase C 有限语义收口候选

状态：**PENDING — 具名 Human semantic review / R2 closeout 的审查候选**。本文件由 assistant 整理；
路诚钺的语义决定与黄毅的执行事实接口意见均未由本文件代填。M12 保持 RESERVED。

本轮输入基线为 `origin/develop@6fa105b720254fae82d2e889385c89292272b2d7`（2026-10-04 fresh-fetch，由
主任务核验），并纳入 PR72 的文档输入与原始审计归档。未更改 Phase C 源 fixture、契约、Schema 或 Runtime。

## 当前任务与权限事实

[TASKS](../../../TASKS.md) 的 M10-001、M10-002、M3-009、M10-003 均为 DONE；
[ROADMAP Phase C](../../../ROADMAP.md#4-phase-cresearch-state-与-verification) 与
[bounded Gate contract](../../../implementation/PHASE_C_BOUNDED_GATE.md) 仍明确 Human/R2/Phase C closeout
独立 pending。现有机器报告与[历史验证](../../huangyi/M10-RESEARCH-STATE/VALIDATION.md)的 PASS 不构成该决定。

[Issue38 planning ACCEPT](https://github.com/Chengyue-Lu/research-agent-workbench/issues/38#issuecomment-5403110100)
及[规划收尾](https://github.com/Chengyue-Lu/research-agent-workbench/issues/38#issuecomment-5415874531)
授权 bounded 实现探索，随后仍须具名语义收口，再进入独立 Topic 5 架构审查。
[PR72 对 exact head `7a9a0b2` 的 APPROVE](https://github.com/Chengyue-Lu/research-agent-workbench/pull/72)
接受的是文档输入，review 正文仍保留 Phase C pending 与 M12/M13 pre-activation。该 historical approval
不能被迁移后的 CI 或本候选扩大解释。

本候选只提出：当前最弱表示是否足以作为**下一项已冻结 action 在新进程中的有界连续性设计**的研究意义输入。
真实 closeout 若存在，也只允许独立 Topic 5 R2 architecture/task-definition 继续接受；它不创建 canonical M12 Task，
不直接允许 continuation、recovery、salvage 或 multi-Agent 实现，不改变 Resolver/Bundle/View/Host 的职责。

## Exact 输入与本轮字节核对

| 输入 | 当前实际 manifest SHA-256 | 源文件 |
|---|---|---:|
| [Case A source manifest](../../../../examples/phase-c/m10-003-gate/case-a/source-manifest.json) | `d737238601c0321328d1445dce891a3f40e2f6e41ec8a431f3b3384bff1d01ba` | 13 |
| [Case B source manifest](../../../../examples/phase-c/m10-003-gate/case-b/source-manifest.json) | `6b30550de75233d6ab86d3e8d116ef447ded1c37c53e1a3a9610f09a3c2d8865` | 11 |

本轮直接读取两个 manifest 的 `source_ref.path` 所指 24 项文件，按实际字节计算 SHA-256；24/24 与
`source_ref.sha256` 相符，两个 manifest 及 24 项 alias/path/SHA 也全部与 PR72
[SOURCE_INDEX](../../../../work/AUDIT-M12-M13-ENTRY-001/A-20260912-001/SOURCE_INDEX.json) 相同。
原索引基线 `ab98caf25125e6567d8bb2c8afff02105b54c940` 保留历史含义；本轮不是重用旧检查结果。
对象内部的示例 `content_hash` 与 source 文件真实字节 pin 是不同层次，没有互相代替。

仅作源文档读回与 hash/link 检查：未读取 private oracle、未运行 actor、未重跑历史测试或 Gate，0 provider API。
本轮没有产生新的 reviewer reconstruction、科学正确性、live execution 或完整进程隔离证据。

## 可以审查的含义与保留范围

| 审查项与 exact refs | 当前源材料支持的有限解释 | 仍不能据此接受的结论 |
|---|---|---|
| Case A [State r2](../../../../examples/phase-c/m10-001-case-a/states/RSTATE-PC-A-r2.yaml)、[Claim](../../../../examples/phase-c/m10-001-case-a/objects/CLAIM-PC-A.yaml)、[Decision](../../../../examples/phase-c/m10-001-case-a/objects/D-PC-A.yaml) | UNKNOWN-PC-A-01 由 D-PC-A@1 resolved；Claim 仍 `proposed-fixture` / `strength: unresolved`，并保留 `No causal claim is accepted.` | Unknown 关闭不等于 Claim promotion、因果成立或真实 owner 接受。D-PC-A 的 fixture actor/status 不能冒充具名 Human 决定。 |
| Case B [State r2](../../../../examples/phase-c/m10-001-case-b/states/RSTATE-PC-B-r2.yaml)、[Evidence](../../../../examples/phase-c/m10-001-case-b/objects/EVID-PC-B.yaml)、[Failure](../../../../examples/phase-c/m10-002-case-b/failures/RFAIL-PC-B-001.yaml) | 粗网格足够的 Assumption invalidated；更高分辨率是否改变结果仍 open。Failure 保留 learned result、revisit condition 与 resolution 是否独立解释不稳定性的 uncertainty；execution Attempt 本身为 completed。 | negative Evidence、Research Failure、Execution Failure 不能合并；不能宣布最终证伪，不能把 completed Attempt 解释成研究成功。 |
| Case B [Decision](../../../../examples/phase-c/m10-003-gate/case-b/closure/objects/D-PC-B.yaml)、[candidate paths](../../../../examples/phase-c/m10-003-gate/case-b/source-manifest.json) | D-PC-B 仅为 synthetic fixture 的指标/资源 ceiling 准入。重复粗网格对应已知 Failure；检查高分辨率输入是非重复候选。Failure 要求高分辨率输入先经 Human review 准入后才值得重访。 | 当前 Decision 没有批准高分辨率输入、自动 retry、输入替换或更大仿真；候选路径不构成执行许可。 |
| Case A [lineage 01](../../../../examples/phase-c/m10-002-case-a/attempt-lineage/A-PC-A-01.yaml)、[lineage 02](../../../../examples/phase-c/m10-002-case-a/attempt-lineage/A-PC-A-02.yaml) 与 State r1/r2 | 两个 Attempt 共享 State r1；State r2 独立 supersede。from-State、optional predecessor、reopen justification 分字段记录，引用理由不授予 reopen 权限。 | 这些 fixture 不证明真实时间因果重建：A-PC-A-02 finished_at 为 `2026-08-25T09:01:00Z`，其 basis D-PC-A timestamp 为 `2026-08-26T10:00:00+08:00`，晚于该 Attempt。此次仅审查声明关系的表示，不将其当成有效历史 reopen 因果证据。 |
| [Method Trace A](../../../../examples/phase-c/m3-009-case-a/traces/MTRACE-PC-A.yaml)、[Method Trace B](../../../../examples/phase-c/m10-003-gate/case-b/closure/traces/MTRACE-PC-B.yaml) | 两条 Trace 均记录 exact Method/Mode/Action、applied disposition、State effect 与 fixture Decision；`actual_binding=unavailable` / `coverage=gap-only`，path fact refs 为空。 | applied 声明不能证明观察到实际执行。契约/历史验证记载 M11 producer/captured 分支存在，本轮未重新读取该分支源事实或执行验证；不得以全局 producer 存在消除这两个 Attempt 的 gap。 |
| Contradiction / Frontier | [State contract](../../../implementation/RESEARCH_STATE_CANDIDATE_CONTRACT.md) 声明复用 Evidence–Claim counterevidence relation、从 entries/open items 派生 Frontier；避免新增独立对象是当前最弱表示假设。 | 此 exact closure 的 Claim counterevidence_refs 为空，也没有独立 Frontier 输出或复杂冲突案；不能声称全面覆盖 Contradiction、Frontier 或 universal ontology。 |

[Attempt/Failure contract](../../../implementation/RESEARCH_ATTEMPT_FAILURE_CONTRACT.md)、
[Method Trace contract](../../../implementation/METHOD_TRACE_CANDIDATE_CONTRACT.md) 与
[现有风险台账](RISK_LEDGER.md)继续限定引用形状、meaning、实际执行事实和 authority 的不同层次。
本候选保留原 negative/failure/gap 证据，不改写旧机器报告中的 pending/false。

## 待具名决定的具体选项

| 选项 | 决定范围与后续效果 |
|---|---|
| A — 有限接受（建议） | 接受 exact-ref composition、轻量 Unknown/Assumption、独立 Attempt/Failure 与 ref-only Method Trace 作为上述单 action/fresh-process 设计的最小研究意义输入；保留表内时间、actual-binding、Contradiction/Frontier 覆盖限制。Phase C Human/R2 对此限定范围收口，允许独立 Topic 5 R2 设计审查；不授予实现或 universal/scientific authority。 |
| B — 要求具体修正 | 指定本表哪一关系不能恢复、哪一含义混淆，及 exact ref；按既有职责处理该问题后再审，不由通用 CI PASS 代答。 |
| C — 暂缓决定 | 明确缺少哪项已有边界所需的语义输入，并继续保持 Phase C pending / Topic 5 frozen；不泛化为额外全量测试或新 Gate 体系。 |

以下是可由具名 reviewer 修改、采用或拒绝的**PENDING 文本**，不是已有签字：

> 我（路诚钺 / Chengyue-Lu）审阅本候选 exact head【完整 SHA，填写】（base 为
> develop@6fa105b720254fae82d2e889385c89292272b2d7）、
> 两个上述 SHA 固定的 source manifest 及其 24 项 exact closure，决定【A 有限接受 / B 具体修正 / C 暂缓】。
> 若选择 A：接受上表所列最小表示作为单条已冻结 action / fresh-process 连续性设计的研究意义输入；
> 时间因果、两案 actual-binding gap、Contradiction/Frontier 未全面演示与 fixture/science 限制均保留。
> Phase C Human semantic review / R2 closeout 仅在此范围闭合，允许独立 Topic 5 R2 架构与 docs-only task-definition
> 审查；本决定不激活 M12 Task、不批准 implementation、不改变科研 Claim、人类准入或控制权限。
> 理由 / 限定项：【填写】；日期：【填写】；正式决定记录 exact ref：【填写】。

> 我（黄毅 / let778750-cpu）对同一 exact 输入确认 / 指出修正：【填写】。Method Trace 的 applied/gap 与
> M11 authoritative execution fact producer 的职责仍分开；没有本 Attempt 的合格 fact 就保持 gap，Resolver
> 仍选择 Supply，Bundle/View producer 仍冻结读取面与 exact binding，Host 仍只消费冻结输入并报告事实。
> 接口意见不代替路诚钺的语义决定，也不批准新 rebind/fallback/retry 权限。日期 / 正式记录 exact ref：【填写】。

真实决定前，canonical Task/ROADMAP/implementation 状态保持原义。决定后，只按其实际限定范围同步当前状态；
原报告仍保留运行时的 pending/false。独立 Topic 5 架构与首个 bounded task-definition 必须另有 R2 acceptance，
其实施不能借本候选提前开始。M13、M5/A4/Pilot 与 Provider 开发线保持各自授权和验收路径。
