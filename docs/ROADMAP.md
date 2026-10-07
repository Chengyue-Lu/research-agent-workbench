# 架构演进路线图

状态：方向与 Gate 基线；逐项状态、依赖和验收只由 [TASKS](TASKS.md) 承载，成熟度见 [STATUS](STATUS.md)。

路线图解释框架接口为什么按这个顺序构建、哪些权威不得跨越。Phase 不是工期承诺，也不是科研项目的固定 DAG。
施工导航见 [M-series 施工图](M_SERIES_IMPLEMENTATION_MAP.md)；日常授权与 PR 规则见 [DEVELOPMENT](DEVELOPMENT.md)。

## 1. Phase / Topic / M-group / Task

| 层次 | 回答什么 | 权威与使用方式 |
|---|---|---|
| Phase | 接口的宏观依赖与成熟度 Gate | 本页；不能代替 Task 启动条件 |
| Topic | 架构责任域与 authority boundary | accepted Architecture 与本页；冻结仍是 Task 上限 |
| M-group | implementation family / development route | 施工图；family 箭头不是 hard dependency |
| `Mxx-yyy` | 可执行、可验收的原子工作 | TASKS；branch/PR/CI 引用 exact ID |

一个 Task 可以跨多个 Topic，一个 Phase 可以聚合多个 M-group。近期工作没有 exact Task 时，先做
独立 docs-only `task-definition`。TASKS 控制 scheduling，architecture freeze 仍约束其 scope；
分支候选的 READY 不等于共享接受，完成身份不因一个 PR 原子集成多个切片而合并。

| Phase / area | 目标与主要产物 | 依赖与 authority Gate | M-group 导航 |
|---|---|---|---|
| Foundation / pre-A | 文件契约、Profile、Trace、Provider 和 Mode–Skill baseline | 各层保持具名 owner 与权限边界 | M0/M1/M2/M3/M6/M7 |
| A — Core Formalization | Mode Action、Method Resolution、Mode migration、Decision Authority | ADR-0013/0016；方法需求先于供给绑定 | M8 |
| B — Evolution Foundation | Requirement、Need、Lifecycle、Protocol、Report/Resolution/Snapshot | Phase A 接口；Maintainer 演化外环与 Runtime consumer 分离 | M9 |
| C — Research State & Verification | State、Failure、Evidence–Claim、Method Trace | A；部分依赖 B；machine verification 与 Human/R2 closeout 分开 | M10，复用 M3-009；M4 supporting |
| D — Evaluation Loop | frozen Cases/Protocol、四臂 Harness、blind Review、analysis/disposition | 真实案例、适用 live conformance、pilot、A4 admission 与 Human Review 独立闭合 | M5，复用 M4/M6/M11；M7 比较按 Task 激活 |
| E — Strategy & Governed Evolution | bounded strategy/candidate experimentation | B/C/D evidence；不自动修改 Core | 既有 M2/M7；M13 reservation |
| F / Topic 4 — Execution Reintegration | Bundle/View/Host、actual facts、Trace/Receipt | ADR-0019 与 Snapshot Core；Skill 只 Gate 其可选支线 | M11/M6 |
| Topic 5 residual | Handoff/context rollover、recovery/continuation | Phase C Human/R2 closeout 后另做 R2 review/task-definition | M12 reservation |
| Product / Release | source trust、projection、portable package、public surface | exact frozen source/current main parent 与每次具名 release decision | M14 |

M12/M13 只保留 namespace，没有 Task state、owner、dependency、Schema 或 implementation authority。
激活需 accepted architecture Gate、既有 family 不足的证据和独立 task-definition；不创建预猜的原子 ID。

### 1.1 普通入口的桥接方向

M1-010（需求/材料与契约产物）、M2-009（角色与有界主子消费）、M11-008（冻结执行/closeout 全桥 Gate）
复用 Foundation、Research Control 与 Phase F 的文件接口。可用合成材料证明通路；它们不要求先启动真实科研案例，
也不产生 Phase D 四臂净价值结论。exact scope、owner、risk、入口依赖与验收只看 [TASKS](TASKS.md)。

新建输入和人工既有材料是入口策略，共用 Protocol/Task/Mode/Method 流程。材料必须显式声明、授权并冻结；
缺 MainState 时保持 unknown，不补造历史接受或自动恢复。角色职责可合并，必载职责提示与可选方法 Skill 分开；
main 在已授权上限内提出 0..N child，每个 child 仍有有界 Task、fresh context、权限预算预检及独立冻结。
这属于 caller 消费既有接口，不授予 Host 组队、重选 Supply 或修改科研权威。

Guide 使用独立只读上下文，只读取 approved MainState/必要 refs；不默认读取主聊天、原 logs 或全仓，
不自动回传 main，不写科研 Trace/Handoff/state。人类明确采纳时，答案及 refs 作为新的 main 输入。
定义及候选代码边界见 [任务定义记录](workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/README.md)。

## 2. Phase A Gate：方法与决策权

Mode Action 固定 trigger/non-trigger、failure/artifact/Claim/Gate/stop；Method Resolution 正式表达
no-Skill、direct Tool、Skill Need、Human Gate、split、blocked 与 rejected alternatives。
Mode 不隐式携带 Skill；Agent proposal、deterministic resolution 与具名 Human Decision 保持分离。

停止 Gate 是可引用的 `Task → Method Resolution → downstream demand` 接口及兼容 migration；
它不证明 Supply binding、Runtime 执行或科学适用性。版本迁移显式调用，旧对象保留 identity/hash，
不在读取时静默升级。协议见 [Method Resolution](implementation/METHOD_RESOLUTION_CONTRACT.md)、
[Decision Authority](implementation/DECISION_AUTHORITY.md)与[Mode migration](implementation/RESEARCH_MODE_MIGRATION.md)。

## 3. Phase B / Topic 4 Gate：需求、供给与执行

需求侧 `Capability Requirement` 不含 Provider/Model、可用性或具体供给。Maintainer 独立 triage 后才能
形成 Skill Need；gap/failure 不自动成为 Need、candidate 或 admission。Need 只声明未来所需证据，
Lifecycle 引用 trial/evaluation/decision，完整比较与净价值分析留在 Phase D。
Protocol Profile 独立表达方法适用性和 obligations，不绑定 Skill/Tool/Provider，也不固定科研 DAG。

```text
Method / Requirement
  → Supply Report(s) → Capability Resolution → Snapshot
  → Runtime Bundle → Resolved Execution View → Thin Host
  → actual facts → Trace / Artifact / Validation / Receipt
```

Report 陈述 identity/version/hash、能力、I/O、availability、conformance 与 ceiling；Capability Resolver
是唯一 selector。`structural-replay` 没有执行资格，`runtime-execution` 还需相应实际证据和执行准入。
替换性 Gate 固定 Task/Mode/Action/Method/Requirement，只产生新的供给冻结，permission/data-egress/
side-effect ceiling 不放宽。具体契约与 replay Gate 见 [Capability Resolution](implementation/CAPABILITY_RESOLUTION_CONTRACT.md)
和 [Phase B Gate](implementation/PHASE_B_EVOLUTION_GATE.md)。

Topic 4 Core 在零 Skill、零 Evolution Registry 下消费 no-Skill/procedure/direct Tool/Adapter–Provider。
Bundle 使用 exact closure manifest，拒绝目录输入、递归 Registry 扫描和 Evolution validator import。
View producer 冻结 external pins、freshness、exact Provider/Adapter/Model/Runtime/Host 与最严 policy 交集；
Host 只执行这个 View，报告 actual facts、diagnostic 或 re-resolution request，不 reselect/rebind/fallback。
Host/Runtime 自动路由、critic voting、隐藏编排和修改 Method/Claim/Gate 的权限继续禁止。
caller 的有界主子 Task 仍逐次通过这些接口，不把动态委派放入 Host。

可选 Skill 路径按 [ADR-0019](decisions/0019-OPTIONAL-MAINTAINER-SKILL-EVOLUTION-OUTER-LOOP.md)
只消费 immutable admitted Release → runtime-minimal Projection →统一 Supply/Resolution/Snapshot/View。
缺失/stale/mismatch 只阻断相应 Skill new-binding，不阻断 Core，也不允许回读完整 Need/Evaluation/Lifecycle。
Skill actual closeout 使用独立版本的[Skill closeout/replay](implementation/SKILL_EXECUTION_CLOSEOUT.md)，
不能把 Core Receipt 写成 Skill 执行证明；[Gate B](workstreams/chengyue-lu/M11-SKILL-CLOSEOUT-GATE/GATE.md)保留 exact 接受记录。
Projection publication、供给资格、实际消费和研究净收益分别验收。

执行接口分别见 [Bundle](implementation/RUNTIME_BUNDLE_PROFILE.md)、[View](implementation/RESOLVED_EXECUTION_VIEW.md)、
[Host](implementation/THIN_EXECUTION_HOST.md)与[Core closeout](implementation/GENERIC_EXECUTION_CLOSEOUT.md)。

## 4. Phase C / Topic 5 Gate

Phase C 的 machine prerequisite chain 保留原 identity：
`M10-001 → M10-002 → M3-009 → M10-003`。M4 是 provenance/promotion/reproduction support。
State entries、Unknown/Assumption、Evidence–Claim contradiction/derived Frontier、Attempt lineage 和 Failure
属于各自有界 candidate；Method Trace 以 ref-only 方式记录方法、Human Decision、State 与 path disposition。
Snapshot 不能冒充 actual execution fact；缺 accepted fact producer 时显式记录 gap。

两份 bounded synthetic cases 的 fresh-process Gate 检查 exact closure、受控读面和 fixture predicates，
不证明科学正确性、reviewer reconstruction、OS sandbox 或真实跨 Runtime 恢复。
Human semantic review 与 R2/Phase C closeout 独立；详情见 [Phase C Gate](implementation/PHASE_C_BOUNDED_GATE.md)。

Topic 5 继续冻结。machine prerequisite 完成后仍须具名接受 Phase C Human/R2 closeout，才可进入独立
Topic 5 R2 architecture review/task-definition；两者均不自动授权 Handoff、context rollover、pause/resume、
recovery、salvage/clean recovery 或 continuation 实现。Topic membership 按是否改变这些 semantics 判断；
仅消费 Trace/Receipt、人工批准的 MainState 或提供只读 Guide 不构成 membership，也不产生恢复权威。

## 5. Phase D Gate：工程闭包与净价值评价

[ADR-0020](decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md)固定双传输：
A1 plain Agent / A2 plain Agent + Tool 使用 M6 baseline；A3 Mode no-Skill/direct Tool 使用 M11 Core；
A4 保持 candidate-origin treatment，Runtime 只消费 admitted Release 的合法 Skill 支线。
A1/A2 provider-visible envelope 使用正向白名单，完整 Task、Profile、Method/Capability control 与 private oracle
留在不可见 enforcement/provenance metadata；不能把 plain arms 强塞进 M11 或注入 dummy Method/Snapshot。

| Contrast | 解释上限 |
|---|---|
| `A4 − A2` | primary system-level package effect，明确包含 transport difference |
| `A2 − A1` | 同 M6 transport 的 exact Tool 条件增量 |
| `A4 − A3` | pairwise closure 证明唯一差异是 admitted Skill 才为 Skill conditional increment；否则 bundled/package effect 或 unavailable |
| `A3 − A2` | Mode/Method 加 transport 的组合差异，不能作 pure Mode effect |
| `A4 − A1` | 完整栈支持性 contrast |

M5-001/002 冻结 Public Case 和独立 Private Adjudication Package；在观察 output 前完成 Human approval、
case/oracle hashes、选择理由与 no-treatment-specific-tuning。Protocol 冻结 comparisons、randomization、
replicates、stopping/retry、drift、blind/reveal、metric status、analysis 与 disposition；Research Integrity
退化不得被效率抵消，不建立单一 weighted aggregate score。跨 transport duration 由同一外层可信时钟观测，
内部 token/cost/timing 无法同义化时显式 estimated/unavailable/N/A，不能填零。

qualification Gate 保持两端 Task/Requirement/Supply/component/implementation/interface（及 A3 Mode/Action/Method）
不变、ceiling 不扩大。M6 baseline 产生 A2 record；Capability Resolver 产生 A3 runtime Resolution/Snapshot；
Harness 在评价侧组装 A3 record并独立重算 A2/A3 record与 A3/A4 pairwise comparability，不取得 Supply selection。
actual binding 在 use boundary 重验并由 typed Trace fact 与 replay Receipt 独立佐证，planned View 不能代替。

A4 admission Gate exact-pin candidate/evaluation →具名 Human Admission Decision→immutable Release→Projection→
Supply→Resolver→Snapshot→Bundle→View→Host；Runtime 不读取 candidate/evaluation/oracle。
Overlap assessment 在 confirmatory freeze 前重载两侧闭包，验证时间顺序并重算 case/Task/input/private-oracle
intersection；缺失/absent/unknown/unresolved 不视为 held-out。重叠案例只作 pilot/secondary，不能进入 primary
net-benefit，也不能单独支持 pruning。完整规则见 [Protocol](implementation/SYSTEM_EVALUATION_PROTOCOL.md)
与 [Harness](implementation/SYSTEM_EVALUATION_HARNESS.md)，exact Task 条款仍以 TASKS 为准。

[M5-008 Live Pilot Gate](workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-008_LIVE_PILOT_GATE.md)
验收独立获批 dossier 下的四臂真实工程闭包，要求适用 conformance、真实 A4 admission、专项 API/数据/Tool
授权和预注册 run set。全部 failed/retry/unknown 留证，不自动改变 frozen treatment/binding。
pilot observations 不产生 confirmatory net-benefit，不进入 primary run set；受其观察或调参影响的 case 不再
是未观察 held-out。M5-004 还需两个获批真实案例及其 provenance、blind Review 和 analysis；
M5-005 依据 exact evidence 作具名 disposition，单次成功、A4 较优或 sunk cost 均不自动 promotion/KEEP。

通用入口桥接与四臂评价保持独立身份。M6-009 的十一厂商 offline profiles 不代表全厂商 live；
[M6-010 受限收口](workstreams/chengyue-lu/M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-010_COMPLETION.md)
仅接受 exact Flash Provider/session，后续 binding/purpose 需重验适用性，不替代 M6-004、M11 E2E、A4 或 pilot。

## 6. Phase E/F 的停止边界

第一版 Strategy 保留 direct baseline，至多增加一个实验策略；外部发现、生成、repair/merge/prune 只作用于 candidate。
Runtime 不创建 Need/Candidate、不执行 Trial/Evaluation/Promotion，不读取完整 Lifecycle；
可选 diagnostic/feedback bridge 需已接受的 Failure/Trace/privacy 语义，不阻塞 Topic 4 Core。
M6-003 作为显式历史 compatibility seam 解释；新 Runtime 消费按 M11 contracts，不恢复旧 umbrella。
Provider cancellation/deadline、实际溯源和 ordinary-user 全桥各有独立验收，不能从单模块 PASS 推出。

## 7. Product / Release Gate

[ADR-0021](decisions/0021-CURATED-DEVELOP-TO-MAIN-RELEASE.md)将 release source trust、curated main、
portable package 与公开 surface 纳入 M14；它不修改 Phase/Topic authority，也不把未完成评价当产品价值。

内容信任沿 `develop → frozen exact source → deterministic projection`；Git ancestry 沿
`exact current main → generated release/v* → new curated main`。每次重新验证 source-CI、parent freshness、
strict allowlist/manifest、closed output set 和 prospective merge-result tree = projection tree = manifest tree；
main 前移时重新生成。active curated topology 拒绝 direct `develop → main`；release branch 不接收产品修复、不回并 develop。

portable package 分开 project/filesystem、immutable runtime resources 与 integration config，禁止隐式 cwd/checkout
fallback。installed Runtime 只消费 published identity/hash 与 RuntimeResourceManifest，repository Maintainer
另验 publication history；非空 Skill Projection 还要闭合 logical→installed exact assets并拒绝 orphan。
no-Skill Core 不等待真实 Skill admission。

每次 release 独立满足硬门禁、R2 审核和具名 merge/tag/publish 决定；机制接受不继承上一版本授权。
[首发完成记录](workstreams/chengyue-lu/M14-CURATED-RELEASE/FIRST_RELEASE_COMPLETE.md)保留历史 exact 证据，
当前发行规则见 [发布合并规范](DEVELOP_TO_MAIN_RELEASE.md)，逐 Task 状态只看 TASKS。
M14 不激活 M12/M13，也不解除 Human/live/evaluation Gate。

## 8. 停止与长期检验

没有已证明需求时，不扩建通用 Supervisor、固定团队/DAG、Tool marketplace、长期 conversation database、
自动 Core 修改或没有真实消费者的消息/数据库基础设施。新正式 Mode、accepted Skill 和 Provider 路线仍按独立 Task/Gate。

长期以可复核替换性、migration/replay、Method violation/Claim overreach/provenance error/重复失败减少、
Skill 相对简单 baseline 的 measured increment，以及 reviewer 用 compact refs 重建关键决定来检验系统；
至少一个复杂控制因无增量而被简化、停放或删除，也是有效结果。
