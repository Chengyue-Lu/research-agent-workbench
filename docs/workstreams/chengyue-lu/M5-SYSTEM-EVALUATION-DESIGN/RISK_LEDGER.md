# M5 System-Level Evaluation Design Risk Ledger

The following original rows retain the accepted design-stage controls and downstream dependencies.
Implementation evidence for M5-006 is recorded after the table; candidate verification does not close M6-008,
M5-007, Human case/admission or actual-execution obligations.

| Risk ID | Type | Risk | Control | Status |
|---|---|---|---|---|
| M5-EVAL-EST-001 | authority | Skill 独立效果取代 system-level primary estimand，使局部收益被误写成 RWB 整体净收益。 | Primary estimand 固定为完整 RWB 相对 simpler Agent/Tool baseline；Skill effect 只作满足 pairwise exact-equality closure 后的 secondary interpretation。 | controlled by Task definitions and R2 review |
| M5-EVAL-TRANSPORT-001 | architecture / estimand | baseline transport 未选择就冻结 Protocol，或把 architecture Decision 冒充已实现 transport。 | ADR-0020 exact-pin A1/A2→M6、A3/A4→M11，并冻结 `A4 − A2` primary、局部 contrasts 与 interpretation ceiling；新增 M6-008 作为独立实现依赖，Decision 不产生实现/执行 authority。 | architecture controlled; Gate A satisfied on merge; implementation open; no longer blocks M5-006 |
| M5-EVAL-BASELINE-INPUT-001 | treatment contamination / data boundary | 完整 Task 的 `active_modes`、`agent_profile`、Method/Capability/Skill control、private-oracle ref 或未来未知字段被送入 A1/A2，使 plain baseline 暗中消费 RWB treatment。 | M6-008 将 `additionalProperties=false` 的正向白名单 provider payload 与 enforcement metadata 分开；未知 Task 字段默认不可见，A2 只额外暴露 exact Tool interface，Trace 独立闭合 payload/Tool surface。 | open until M6-008 |
| M5-EVAL-ARM-QUAL-001 | execution validity | M5-003 的 A2/A3 `structural-replay`、`execution_input=false` fixture 被用于正式执行，或借 runtime qualification 静默替换 frozen binding/放宽 boundary。 | Synthetic fixture 只用于 contract test；M5-004 A2/A3 必须使用 `runtime-execution`、`execution_input=true` Snapshot，并由 M5-006 拥有的 versioned/hash-pinned `ArmExecutionQualificationRecord@1.0.0` exact 连接两端，证明 Task/Requirement/Supply/component/implementation/interface 与相关 A3 Mode/Action/Method 未替换、typed conformance 完整且 ceiling 不放宽；M6-008 在 M5-006 DONE 后只产生 A2 record；Capability Resolver 独立产生/选择 A3 runtime Resolution/Snapshot，M11 只验证消费，M5-007 组装/重算 record。 | open until M5-006/M6-008/M5-007 |
| M5-EVAL-A3A4-COMP-001 | comparability / interpretation | A3/A4 的 Mode/Action/Method、非 Skill capability/supply、Tool/procedure、provider-visible interface 或 boundary 实际不同，却把 `A4 − A3` 宣称为 pure Skill conditional increment。 | M5-006 冻结 `A3A4PairwiseComparabilityRecord`；M5-007 独立重算 shared surface 与唯一 admitted Skill delta。只有 `exact-skill-only` 可作 Skill conditional interpretation；`skill-bearing-package` 只能报 bundled/package effect，`not-comparable` 令 secondary contrast unavailable。当前 Method disposition 差异不得由 overlay/Harness 掩盖。 | open until M5-006/M5-007 |
| M5-EVAL-BASELINE-ACTUAL-001 | execution evidence | 多轮 session 在初始 preflight 后发生 validate/use 漂移，或 Driver 低报耗时/自报 binding 绕过 baseline actual-fact closure。 | M6-008 在每次 provider request 与每次 Tool invocation 的 use boundary 立即重验对应 pins，Trace 记录重验后的 bytes/hash；使用 transport trusted start/end clock，分开 preventive/detective semantics，并独立佐证 actual Provider/Adapter/Model/Runtime/Host/Tool binding。 | open until M6-008 |
| M5-EVAL-CROSS-TRANSPORT-001 | measurement validity | M6/M11 内部 elapsed、token、cost 或状态口径被直接比较，产生伪精确净收益。 | ADR-0020 要求同一 Harness 外层可信时钟形成可比 wall time；无法同义化的内部指标标 estimated/unavailable/N/A，不得填零；`A3 − A2` 明确含 transport difference。 | protocol rule accepted; implementation open until M5-006/007 |
| M5-EVAL-LEAK-001 | data boundary | treatment arm 读取 Private Adjudication Package，造成 oracle leakage。 | Public/Private package 分离、独立 hash freeze、arm read boundary 与 blind-first review。 | open until dossier contracts are implemented |
| M5-EVAL-ORACLE-001 | integrity | 观察输出后改写 oracle/case 或为特定 treatment 调参。 | 输出前冻结 case/oracle hash、Human approval、记录 selection rationale、禁止 post-result rewrite 与 treatment-specific tuning。 | open until M5-001/002 |
| M5-EVAL-OVERLAP-001 | evaluation validity | A4 admission Evaluation 与 Phase D primary confirmatory case 复用相同 case、Task、formal input 或 private oracle identity，或旧 Evaluation 根本没有可比较 oracle closure，却被自报为 held-out。 | M5-006 定义 versioned/hash-pinned `AdmissionEvidenceOverlapAssessment`，绑定 exact Evaluation、admission case/Task/input、typed oracle/checker/adjudication、两侧 comparison closure、时间、validator 与结果；M5-007 验证 `checked_at <= case_selection_frozen_at` 并独立重算，重叠仅限 pilot/secondary，缺失、`absent`/`unknown` 或 unresolved fail closed。该工件是 M5-006→007 内部 acceptance，不属于 pre-M5-006 external Gate。 | open until M5-006/007 |
| M5-EVAL-METRIC-001 | interpretation | N/A/unavailable/estimated 被当成 measured zero，或单一加权分数掩盖科研完整性退化。 | 四态 measurement status、三层 decision hierarchy、Research Integrity non-compensation、禁止单一 weighted aggregate score。 | open until M5-006 |
| M5-EVAL-BLIND-001 | human review | arm/Skill/RWB 标签或成本先验污染 Human 质量判断。 | Blind phase 隐藏 identity/cost/token/label，质量评分完成后再 reveal exact execution facts。 | open until M5-006/007 |
| M5-EVAL-LIVE-001 | execution | synthetic Driver/projection 被误作 system-level 真实执行证据，或把 M11-006 mechanism DONE 误作已有真实 A4 供给。 | M11-006 mechanism dependency 已满足；M5-004 仍 hard-depend M6-004 与独立 `A4-RUNTIME-ADMISSION-GATE`，A4 必须使用真实 accepted Release→Projection→Supply，confirmatory run 禁止 synthetic projection。 | open; production projection index empty, external Gate unsatisfied |
| M5-EVAL-ADMISSION-001 | identity / authority | frozen `mode-candidate-skill` 被静默改写为另一 accepted treatment，或 candidate 被 Runtime 直接加载；反向风险是只有同名字符串而没有 candidate/evaluation→Decision→Release→Projection→Supply 的可验证桥。 | A4 固定为 candidate-origin treatment + admitted Runtime execution；`A4-RUNTIME-ADMISSION-GATE` 与 versioned overlay 逐跳 exact-pin identity/path/hash，M5-003 v0.1 保持 immutable，Capability Resolver 仍为唯一 selector。 | open; production projection index empty, Gate unsatisfied |
| M5-EVAL-ACTUAL-001 | execution evidence | pre-run overlay/View 被误写成 actual execution，或 Host 实际消费另一 Projection/Supply/binding。 | M5-007 hard-depend M11-004 的 Core Trace/generic-closeout contract（M11-003 Host actual facts 由依赖传递），并要求 typed execution fact→replay-valid Receipt 独立重放 actual binding；completed/post-call failed/preflight blocked 分开，planned facts 不替代 actual facts。M11-006 不传递该 producer/closeout 责任；Skill-bearing generic Receipt 剩余缺口由 `M5-SKILL-CLOSEOUT-REPLAY-GATE` 跟踪。 | producer dependency satisfied; replay Gate unsatisfied; M5-007 not implemented |
| M5-EVAL-HARNESS-001 | architecture | Harness 为 A4 建旁路、直接读 candidate 或接管 admission/promotion/Human decision；或为了表面统一四臂而给 plain arm 注入 raw Task control、Method/Snapshot/Skill Assignment。 | Harness 保持 M5-003 treatment/read boundary，只在评价记录层统一 evidence；ADR-0020 固定 mapping，M6-008 负责 baseline execution，Skill replay seam 仍由独立 pre-M5-007 Gate 控制。 | Gate A satisfied on merge; M5-006 READY; M6-008 PARKED until M5-006 DONE; Gate B unsatisfied; M5-007 blocked |
| M5-EVAL-DRIFT-001 | comparability | Model/Provider/Host/context/budget 漂移破坏四臂可比性。 | M5-003 共享 frozen conditions + M5-006 drift/retry/stopping rules + M5-007 exact run records。 | bounded by protocol design |
| M5-EVAL-SUNK-001 | governance | 已投入开发成本导致默认 KEEP，或单次 A4 成功触发 promotion。 | M5-005 要求 evidence-linked disposition，并显式允许 PARK/DEPRECATE/DELETE/STOP。 | open until M5-005 |
| M5-EVAL-SCOPE-001 | scope | task-definition PR 偷跑 Evaluation、实现 runner、解冻 Topic 5 或宣称净收益。 | 当前 diff 仅定义 unfinished Tasks、派生导航、workstream 和风险；M5-003 DONE immutable。 | controlled by docs-only governance |

## M5-006 implementation candidate

| Risk / seam | Implemented control and adversarial evidence | Remaining acceptance |
|---|---|---|
| EST / TRANSPORT / METRIC / CROSS-TRANSPORT | Protocol exact ADR pin, explicit transport/contrast rules, four measurement states, frozen statistical/design parameters and hierarchy; `test_system_evaluation_protocol` rejects changed primary, weighted score, imputed missing zero, invalid units/ranges and incomplete registration | Exact-head CI and named review; observed transport measurement belongs to M6-008/M5-007 |
| ARM-QUAL | Reload selected and unselected Supply closure; exact frozen/runtime Task/Requirement/Supply/components/implementation/interface, A3 Method and narrowing ceilings; structural substitutions and producer/pin drift rejected | Execution producer and use-boundary replay remain downstream |
| OVERLAP | Protocol independently pins admission closure; consumer independently supplies confirmatory cases/time; recompute four identity-or-hash intersections and all derived values; missing/unknown/opaque closure remains ineligible | Human approval of real dossiers and historical oracle provenance remain required |
| ADMISSION / ACTUAL | Named Human Decision and independent callback, candidate/Release/promotion endpoints, deterministic Projection and exact Snapshot/Bundle/View; no status-only admission or planned-to-actual conversion | Real admission, actual facts and Skill closeout Gate remain open |
| A3A4-COMP / DRIFT | Compare frozen full execution binding and output/stop obligations; current Method difference yields package effect; recheck preregistered analysis refs and all input bytes | M5-007 must reconcile post-run actual facts; pure equality fixture grants no execution authority |
| SCHEMA / CACHE | Bounded same-byte parsing, finite JSON, invocation-local copied caches, captured Schema identity and rechecks; changed refs/Schemas cannot reuse cached qualification | Exact-head coverage and package verification |
| SCOPE / TRACE | One existing M5-006 feature/R2 implementation; no Task redefinition or downstream implementation; capture gaps retained in the Attempt record | Cross-owner review; no self-merge |
| PR71 / ADMISSION-CLOSURE | Confirmatory Protocol requires an exact admission-scoped closure in schema and semantics; synthetic null remains valid, wrong scope/hash fails | Review correction; real admission remains independently verified |
| PR71 / METHOD-COMPLETENESS | Derive demand from exact frozen Methods and Tasks; compare runtime Requirement identities with exact multiplicity across A3 and case-scoped A4; missing, extra, duplicate and Task/Method drift fail | Complete synthetic document-read + research-contract-check fixtures; no Task completion authority |
| PR71 / EXTENSION-COUNT | Count exact Projection/Skill ID/version/hash identities once across Requirements; one reused Skill remains one extension and distinct identities remain distinct | Interpretation still depends on the full comparison surface |
| PR71 / TASK-COMPARISON-SCOPE | Qualify the whole A3 arm and reload all Bundle/View inputs, then select A3 by the overlay's exact Task path/hash and recheck its frozen Method/Requirement completeness | Multi-Task demand/comparison regression preserves the original case result; unrelated Tasks cannot force an unavailable result; no multi-Task execution claim |

Evidence entrypoints and consumer responsibilities are in [the implementation contract](../../../implementation/SYSTEM_EVALUATION_PROTOCOL.md)
and [WORKLOG](WORKLOG.md). Test fixtures are synthetic structural evidence, not Human admission or scientific efficacy.

## M5-007 进入时风险更新（2026-09-16）

上文保留原设计及 M5-006 implementation 阶段状态。PR71、PR75、PR81/82 的 Protocol、baseline 与 Skill closeout 已接受，Gate B 已 SATISFIED；PR84 已接受 M6-008 DONE 与 M5-007 READY。剩余 Harness 风险是 preflight 重算与实际执行混同、两种 transport 被强制同形、overlap/比较等级自报、失败选择性丢弃和盲审信息泄漏。H1–H5 的逐项负例与停止条件见 [进入计划](M5-007_ENTRY_PLAN.md)，首个切片见 [H1/H2 实施包](M5-007_H1_H2_PACKET.md)。生产 admission、真实 case/live 与科研净收益保持独立未满足条件。

## M5-008 live pilot 定义（2026-09-17）

| Risk ID | 风险 | 验收控制 | 状态 |
|---|---|---|---|
| M5-PILOT-LIVE-001 | API smoke、synthetic 或部分 transport 被当作完整 live Harness 验证 | 完成冻结的四臂 run set，至少一个完整 block；真实 Provider 与声明的 Tool/procedure 调用、use-boundary facts、独立 replay、盲审/metric/analysis joins 逐项闭合 | 待 M5-008 执行验证 |
| M5-PILOT-AUTH-001 | 借 pilot 绕过正式 Runtime admission、执行许可或 Provider conformance | M6-004、A4 全链 Gate 和具名 pilot 账户/预算/数据/Tool 授权均为 hard/external prerequisites；缺失时零调用 | M5-008 BLOCKED |
| M5-PILOT-CONTAMINATION-001 | pilot 输出或调参污染后续 held-out，或 pilot 被升级为确认性数据 | 独立冻结 pilot dossier；只执行 pilot slots；分析输入拒收 pilot；后续 freeze 审计 pilot 暴露，受影响案例不再作为未观察 held-out | 待运行与独立审计 |
| M5-PILOT-FAILURE-001 | 只保存成功臂、漏计失败费用，或重复运行到满意 | 预注册 retry/complete-block stopping；保留全部失败与未完成 slots；安全/预算停止不能获得 Gate PASS；负例注入单列且须在授权边界内 | 待 live evidence |
| M5-PILOT-TRANSFER-001 | 旧版本 pilot PASS 对新 Harness/Provider/Tool/Skill 自动生效 | 具名接受 exact source/config/run set；M5-004 执行前复核适用性，影响执行/证据链的变更需重新验证 | M5-004 保持 BLOCKED |

本次仅提交 Task 定义；上表控制是未来验收要求，不是已观测结果。详见 [Live Pilot Gate](M5-008_LIVE_PILOT_GATE.md)。

## M5-007 H1/H2 implementation candidate

| Risk / seam | Implemented control and adversarial evidence | Remaining acceptance |
|---|---|---|
| ARM-QUAL / producer ownership | H2 reads M6-produced A2 reference and independently validates it; a patched M6 producer raises if Harness calls it. A3 assembly uses supplied Resolver bindings and the explicit preflight time | M6/Resolver ownership unchanged; H3 actual transport remains pending |
| OVERLAP / phase | H1 Schema contains scheduling phase only; H2 recomputes overlap and derives eligibility. Confirmatory blocks with admission overlap remain ineligible; unknown oracle blocks preflight | Real case approval and admission remain independent |
| DRIFT / clock and trust | Explicit caller `preflight_checked_at`, external replay expected time, runtime availability checks, full input and validator pin rechecks; missing callback, future/stale records and self-upgraded results fail | Trusted admission verifier stays external; use-boundary execution checks belong to H3 |
| LEAK / plan identity | Exact public input pins, private artifact hash alias rejection, bounded deterministic slots and cross-process order vector; compilation has no Provider/Tool/Host calls | Planned identities do not attest fresh actual sessions; H3–H5 remain pending |
| TRACE / acceptance | Formal Task snapshot and retained tool evidence; incomplete capture is declared with its warning | Exact-head CI and cross-owner review; Task stays IN_PROGRESS |

## PR89 H3 dispatch deadline review（2026-09-18）

| Risk / seam | Implemented control and adversarial evidence | Remaining acceptance |
|---|---|---|
| H3 / inter-slice deadline | Optional Host guard can only narrow dispatch after Host preflight; trusted boundary time is compared with the first Host start and frozen Protocol budget. Zero-call blocked Host/Receipt and per-slice observations survive cold replay. A3/A4 gap exhaustion, exact deadline, Host preparation delay and altered/missing time evidence are regression targets | Local candidate evidence in [review Attempt](attempts/M5-007-H3-REVIEW-001/README.md); new exact-head CI and cross-owner rereview remain required for acceptance |

## H4 进入准备（2026-09-19）

PR89 已接受 H3 及其 deadline 修复。以下为 H4 待实现的控制，具体顺序见 [H4 实施包](M5-007_H4_PACKET.md)。

| Risk / seam | Planned control and negative evidence | Entry status |
|---|---|---|
| ACTUAL / plan substitution | 独立 replay 完整四臂/全部 slices，再关联 actual binding/Projection/Supply；保留真实失败和零调用，不从 View 填 actual 值 | H4a 首个实现节点 |
| BLIND / reveal ordering | 白名单匿名 projection 与私有映射分离；具名全量 review freeze 后才 reveal；拒绝路径/正文元数据泄漏、部分审查和事后改分 | H4b 待实现 |
| METRIC / provenance | 现有 measurement Schema 外增加 run/Attempt/method/evidence 关联；旧记录缺失外层时间或成本时 unavailable，缺失不补零 | H4c 待实现 |
| ANALYSIS / eligibility | 分析入口重新验证 actual closure、overlap、pairwise、review/reveal 和完整配对；pilot/失败/不完整数据保留明确用途边界 | H4c 待实现；M5-008/004 Gate 保持 |

## H4a implementation candidate（2026-09-19）

`evaluation_harness_evidence@1.0.0` 通过 H3 independent replay 读取实际 Receipt/Host/facts，再逐项
关联冻结资格。显式保存所有 slots、必需 slices、失败 retry、停止与未启动项；completed 要求匹配，
失败保留可验证 drift。篡改 actual Projection/Supply/binding、删失败/slice、换 case/Attempt、
外层 pins 或 validator 身份均为负例。新进程关闭执行端口、network/process 和项目代码执行后回放。

本地证据与 capture-gap 见 [H4a Attempt](attempts/M5-007-H4-001/README.md)。本候选只核对
actual evidence；BLIND、METRIC、ANALYSIS 风险仍待 H4b/H4c，各记录 authority 保持 false。
结构性回放不能证明真实执行环境、科研效果或 Human 接受；正式接受仍需 exact-head CI 和黄毅 review。

## H4b original draft candidate（2026-09-21；历史）

当时 PR90 的 H4a 仍待审核。H4b 在独立分支实现 bounded integer projection、随机私有别名、
exact source-to-projection pins、外部具名 Human Review freeze 与晚于 freeze 的可信 reveal。
正反证据见 [H4b Attempt](attempts/M5-007-H4B-001/README.md)。匿名输出不带 transport metadata、
source paths 或执行顺序；部分/重复审查、无具名授权、时间与评分/映射替换均阻断。

BLIND 风险仅在此 finite synthetic contract 的本地测试中得到控制，仍待跨 owner 接受；
任意自由文本匿名性、生产分发 ACL、真实 Human review 与科学有效性没有因此获得证明。
调用方必须隔离私有 map/reviews 并在验证 reveal 后才开放映射。H4c METRIC/ANALYSIS 和 H5
收口继续待实施；M5-007 IN_PROGRESS，M5-008/004/005 的 Gate 保持原状态。
