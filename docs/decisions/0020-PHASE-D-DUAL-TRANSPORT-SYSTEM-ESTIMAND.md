# ADR-0020：Phase D 采用显式双传输的系统级评估

状态：Accepted only when the exact-head R2 PR is cross-owner approved and merged；在 feature branch 中为
Proposed target state

日期：2026-09-02

Decision identity：`PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND@1.0.0`

审计基线：`develop@dd2454b5595e33a12aa058529358d46d311a08c4`

接受边界：本决定只有在承载它的 exact-head R2 `task-definition` PR 经路诚钺与黄毅完成各自
authority 范围内的 cross-owner review 并合入 `develop` 后，才成为共享项目真值。PR 分支、Issue
文本或本文件单独存在都不关闭 Gate。

## 背景

M5-003 v0.1 已冻结四个 canonical treatment：

```text
A1 plain-agent
A2 plain-agent-tool
A3 mode-no-skill
A4 mode-candidate-skill
```

四臂共享 exact Task、Model、Provider Adapter、Host、预算、上下文、数据边界与 evidence classes；
`plain-agent` / `plain-agent-tool` 抑制 Mode/Method control，只有 A3/A4 消费 exact Mode/Method。
M5-003 只编译 non-executing plan，不选择执行 transport，也不形成实际运行证据。

现有执行面不能在不改变 treatment 的情况下强行统一：

- M11 Runtime Bundle / Resolved Execution View 要求 `proceed` Method Resolution、Action、Capability
  Requirement、Resolution 与 runtime-execution Snapshot 闭包；给 A1/A2 补 dummy Method/Snapshot 会改变
  已冻结 treatment；
- M6 isolated session 可以承载 method-neutral baseline 调用，但 legacy `execution_receipt` 强制
  Skill Assignment，且现有 traced session 尚未提供 M5 baseline 的确定性输入投影、完整 actual binding
  fact 与 no-Skill replay-valid closeout；
- Task 自身可能包含 `active_modes`、`agent_profile`、`required_capabilities` 等控制字段。M5 可以 exact-pin
  完整 Task 作为比较身份，但 A1/A2 不能因此把这些控制字段送入模型上下文；
- M11-004 的 generic Receipt 只接受 no-Skill/direct-Tool/procedure/Adapter-Provider Core，M11-006 只完成
  projection-backed Skill Supply mapping；A4 的 Skill actual binding closeout 仍由独立 Gate 跟踪。

因此，Phase D 在冻结 Protocol 前必须明确选择：建立一条所有 arm 共享的新 neutral execution
transport，或接受 M6 baseline / M11 Mode arms 的显式双传输系统 estimand，并诚实限制因果解释。

## 决定

### 1. v0.1 选择显式双传输，不新增全局 neutral Runtime

Phase D v0.1 使用以下固定映射：

| Arm | Execution transport | Frozen treatment / read boundary |
|---|---|---|
| A1 `plain-agent` | M6 isolated API session + M3 Trace + `M6-008` baseline closeout | 只消费 public case 与正向白名单的 treatment-visible payload；Tool surface 为空；Mode/Action/Method/Capability/Agent Profile/Skill/Evaluation/Lifecycle 均不可见 |
| A2 `plain-agent-tool` | 与 A1 相同的 M6 transport | 与 A1 相同，额外只暴露 exact-pinned Tool definition/interface；Snapshot 与 Method ref 留在 enforcement/provenance metadata，不进入模型控制输入 |
| A3 `mode-no-skill` | M11 Core：Runtime Bundle → View → Thin Host → Trace/Artifact/Validation → generic Receipt | 消费 exact Mode/Action/Method 与 runtime-execution Snapshot；Supply 必须为 no-Skill/direct-Tool/procedure；不得以 M5 structural-replay fixture 作为执行输入 |
| A4 `mode-candidate-skill` | M11 Core + optional projection-backed Skill extension | Candidate 只保留 experiment origin；Runtime 只消费 admitted Release → Projection → Supply → Resolution → Snapshot → Bundle → View → Host，不读取 Candidate/Evaluation/Lifecycle 历史 |

该选择只服务 Phase D v0.1 Evaluation。它不把 M6 提升为新的系统主 Runtime，不降低 M11 的
Method-bound contract，也不建立 Host 中的 arm-specific hidden branch。未来若真实试验表明 transport
confounding 使结论不可用，可以另发版本化 ADR 设计 neutral envelope；不得原位重解释本版本结果。

### 2. A1/A2 使用版本化 treatment-visible baseline envelope

`M6-008` 必须从 M5-003 的 exact references 确定性产生 baseline execution envelope，而不是把 raw Task、
Snapshot 或仓库目录直接交给 Driver。该 envelope 必须把两个 surface 分开：

1. `provider_visible_payload`
   - 使用独立、版本化 Schema 和**正向字段白名单**，固定 `additionalProperties: false`；
   - 只允许 frozen public case instruction、public input refs、treatment-neutral required-output contract；
   - A1 不得出现 Tool definition；A2 只可增加 exact-pinned Tool definition/interface；
   - Task 新增字段默认不可见，只有发布新 envelope version 并经 R2 接受后才可进入白名单。
2. `transport_enforcement_metadata`
   - exact-pin source Evaluation Manifest、arm、完整 Task、shared frozen conditions、compiler identity/version/hash；
   - 保存 accountable actor、permission/data ceiling、budget、Provider Adapter、Model、Runtime、Host，以及 A2
     Tool Snapshot/implementation/conformance pins；
   - 仅供 preflight enforcement、Trace 与 replay，绝不能作为 prompt、system instruction 或模型上下文。

完整 Task 继续作为实验身份被 exact-pin，但 `active_modes`、`agent_profile`、`required_capabilities`、
Mode/Action/Method/Capability Requirement/Resolution/Snapshot control、Skill refs、private-oracle refs 与任何未知
Task 字段都不进入 A1/A2 provider request。A2 的唯一例外是经过 qualification 后的 exact Tool
definition/interface 及实际 Tool result；Snapshot 本体和其中的 Method Resolution ref 只作 evaluator-side
provenance，不改变 prompt、策略或执行规则。Trace 必须能证明 provider request payload 与 Tool surface 恰好
等于白名单 envelope，而不是相信 Harness 的自报布尔值。

M5-003 checked-in A2 与 A3 Snapshot 都是 `structural-replay`、`execution_input=false`，只能用于 synthetic
contract tests，不得进入 M5-004 正式执行。正式 A2/A3 必须绑定 `qualification=runtime-execution`、
`boundaries.execution_input=true` 的 exact Snapshot，并重新验证 implementation、availability、
permission/data/side-effect boundary 与 typed conformance evidence；`structural-replay`、fixture-only availability
或缺失 conformance 一律 BLOCK。

这种执行资格转换必须由独立、versioned、hash-pinned 的 `ArmExecutionQualificationRecord@1.0.0` 闭合，
而不是在 Harness 中替换引用。v1 只覆盖 A2 `plain-agent-tool` 与 A3 `mode-no-skill`，并至少 exact-pin：

- Evaluation Manifest/arm、完整 Task、frozen structural Capability Resolution/Snapshot 与 runtime
  Capability Resolution/Snapshot 两端的 identity/path/hash；
- Requirement ref；A3 还必须 exact-pin Mode、Action 与 Method Resolution；A2 的 Method ref 仍只是不可见
  provenance，不能变成 treatment control 或 provider input；
- 两端 Supply kind/identity、implementation version/hash、component multiset 与 treatment/provider-visible
  interface digest；
- permission、data-egress、side-effect ceiling 的逐项比较，以及 typed live availability/conformance evidence；
- validator identity/version/hash、派生结果、限制与不产生 authority 的 boundary。

validator 必须加载真实对象重新计算，不得相信记录中自报的 equality/result。runtime 侧只能增加 live
availability/conformance evidence 或收窄 boundary；Task、Requirement、A3 Mode/Action/Method、Supply、
implementation bytes/component/interface 任一替换，或 filesystem/network/external-write permission class、
data-egress、side-effect ceiling 任一放宽都必须 BLOCK。若相同 implementation/hash 无法获得 live qualification，
必须发布新的 versioned live Evaluation Manifest/Protocol 并保留 M5-003 历史，不能借 qualification record
静默换绑。

ownership 固定为：M5-006 拥有 shared record 的 contract、Schema、comparison rule 与 fail-closed validator；
M6-008 在 M5-006 DONE 后只从 M6 baseline path 产生 A2 record；Capability Resolver 是 A3 runtime Capability
Resolution/Snapshot 的唯一 producer/selector，M11 只验证并消费 exact runtime Snapshot 形成 Bundle/View/Host，
M5-007 只在 Maintainer/Evaluation preflight 引用两端对象组装 A3 record，并对 A2/A3 两类 record 独立重算。
Harness、M6-008 与 M11 都不因此取得 Supply selection；记录本身不授予 execution、Method、Capability、
permission 或 Human authority。

该投影不修改、复制或发布新版本 Task，也不构成 Method Resolution、Capability Resolution、permission grant
或 execution authorization。

### 3. 新增 Execution-owned `M6-008`

双传输决定产生一个明确的新实现依赖：

```text
M6-008 — Phase D baseline-arm traced execution envelope and replay closeout
owner: 黄毅 / let778750-cpu
risk: R2
```

`M6-008` 必须在不复用 legacy mandatory Skill Assignment 的前提下，闭合：

```text
M5-003 A1/A2 arm
  → treatment-visible baseline envelope
  → bounded M6 isolated session
  → actual Provider/Adapter/Model/Runtime/Host/Tool facts
  → Trace + Artifact + deterministic Validation
  → replay-valid baseline Receipt
```

它必须在每一次 provider request 实际消费 payload 前重新加载并校验 envelope 与对应 external pins，并在
每一次 Tool invocation 前立即重载 Tool implementation/interface/boundary/conformance pins；Trace 记录的 actual
facts 必须来自该次 use-boundary 重验后的 bytes/hash，而不是 session 初始 preflight 的缓存。由此阻断多轮 session
中的 validate/use TOCTOU 漂移。transport-owned/injected trusted clock 记录 start/end 并执行 time budget，不能
信任 Driver 自报 elapsed。
pre-call preventive control 与 post-call detective finding 必须分开。它还必须区分 `completed`、
`post-call-failed` 与 `preflight-blocked`；Provider/Adapter/Model/Runtime/Host/Tool actual binding 必须由 typed、
hash-pinned Trace fact 独立佐证，不能只相信 Driver/Harness。post-call failure 只有在该 fact 能独立闭合 actual
binding 时才具备 Receipt replay eligibility；preflight block 不得伪造 actual facts。所有状态固定
`task_completion=false`，也不得产生 Claim、Human acceptance、Skill admission、fallback、reselection、
recovery 或 Topic 5 authority。

`M6-008` 可以复用 M6-006 的 traced-session 基础与 M11-004 已接受的 actual-fact/status/replay 原则，
但不得把 M11 Bundle/View、dummy Method/Snapshot 或 Skill Assignment 偷渡到 A1/A2。

### 4. Primary estimand 与解释上限

M5-006 必须把以下比较写入 frozen Protocol：

| Contrast | 允许的解释 |
|---|---|
| `A4 − A2` | **Primary system-level estimand**：完整 RWB Mode/Method/admitted-Skill/M11 execution package 相对 tool-enabled simpler Agent/M6 baseline 的净收益；明确包含 transport package difference |
| `A2 − A1` | 同一 M6 transport 内 exact Tool 的条件增量 |
| `A4 − A3` | 仅在 A3/A4 pairwise exact-equality closure 证明**唯一差异为 admitted Skill extension**时，才可称 Skill conditional increment；否则只可称 Skill-bearing package / bundled effect，或记为不可比较 |
| `A3 − A2` | Mode/Method package **加 transport** 的组合差异；不得称为 pure Mode effect |
| `A4 − A1` | Tool、Mode/Method、Skill 与 transport 的完整栈组合差异，只作支持性 system contrast |

这些解释只适用于 exact case、Task、Model、Provider、Host、budget、context、data policy 与版本化 transport。
任何 contrast 都不能单独证明普遍科研增益、生产 readiness、Skill promotion、具体因果机制、Claim 正确性或
Human acceptance。

M5-006 必须冻结 versioned、hash-pinned 的 `A3A4PairwiseComparabilityRecord` 契约；M5-007 在 plan/pre-run
阶段加载真实对象独立重算，并在分析输入中保留结果。该记录必须比较：shared case/Task/frozen conditions；
Mode bytes；Action set/order；Method Resolution identity/revision/bytes 及 obligations、Gate、stop/block、claim
effects；Capability Requirement multiset；排除唯一 Skill component 后的 non-Skill Supply/component multiset；
Tool/procedure identity/version/hash；provider-visible interface digest；permission、data-egress、side-effect、
context/output/budget boundaries。A4 唯一允许的 delta 是由 candidate/evaluation→named Human Decision→
immutable Release→Projection→Skill Supply exact 闭合的 admitted Skill extension，且不得放宽任何 ceiling。

结果固定为：`exact-skill-only` 才允许 Skill conditional increment；`skill-bearing-package` 必须列出 mismatch
surface/refs 且只允许 bundled/package interpretation；`not-comparable` 用于缺 pin、hash drift 或无法验证的
closure，使该 secondary contrast unavailable，但不因此改写 primary `A4 − A2`。若 Protocol 预注册了
`exact-skill-only` 而 pre-run/actual closure 发生漂移，该 run 必须 fail closed。当前 checked-in Method 的
`skill_disposition=no-skill` 与 M11 Skill Supply 所需 `skill-need|mixed` 不能被 Harness 掩盖；若 live A3/A4
因此不能 exact-equal，就必须降级或不可比较，而不是伪造 pure Skill 解释。

跨 transport 的 completion time 只能使用同一 Harness 外层可信时钟作为可比观测；M6/M11 内部 elapsed
只作诊断。token、cost、context 或其他无法同义化的指标必须记为 `estimated`、`unavailable` 或
`not-applicable`，不得填为 measured zero。A1/A2 不适用的 Mode/Method 指标为 N/A，不是“零违规”。

### 5. Authority 与失败边界

- Evaluation Protocol/Harness 不选择 Supply、不放宽权限、不授权执行；
- M6 baseline compiler 只能消费 Manifest 已冻结的 Provider/Model/Tool，不能路由、替换或 fallback；
- A3/A4 的唯一 Supply selector 仍为 Capability Resolver，View/Host 保持 supply-kind neutral；
- 任一 arm 失败时不得切换 transport、Provider、Tool、Supply 或 treatment；retry/stopping 只按 frozen
  Protocol 发布新 Attempt；
- Decision、envelope、Trace、Receipt 或 Harness 均不产生 Task completion、Claim、Human Decision、
  admission、promotion 或 pruning authority；
- 本决定不解除 `M5-SKILL-CLOSEOUT-REPLAY-GATE`、`A4-RUNTIME-ADMISSION-GATE`、M6-004 live
  conformance、M5-001/002 Human case、M4 provenance 或 M5-004 其他 Gate；
- 本决定不解冻 Handoff、context rollover、safe pause、recovery、salvage、continuation 或其他 Topic 5
  语义。

## 后果

优点：

- 不修改 M5-003 v0.1，也不伪造 Method/Snapshot 让 plain arms 进入 M11；
- 复用已经存在的 M6 baseline session 与 M11 Mode-aware Runtime，各自保持权威边界；
- A2−A1 保留同 transport Tool 局部解释；A4−A3 只有在 pairwise exact-equality closure 成立时才有 Skill
  conditional interpretation，否则显式降级为 bundled/package effect；primary contrast 诚实声明系统 package
  confounding；
- `M6-008` 把输入污染、actual facts 与 replay closeout 收成一个具名、可独立验收的 Execution Task。

代价：

- A4−A2 不能解释为 pure Mode 或 pure Skill effect；
- 两条 transport 的内部 timing/token/cost 口径可能不同，需要外层观测与 measurement status；
- M5-007 必须同时等待 baseline `M6-008` 与 Skill replay Gate，不能因为 Gate A 已接受就宣称 Harness
  execution closure 已完成；
- 若真实 pilot 显示 transport confounding 不可接受，未来仍可能需要成本更高的 neutral envelope v0.2。

## 实施顺序

1. 本 ADR 通过 exact-head R2 cross-owner review，并由外部 Gate record 固定 identity/version/path/hash；
2. `M5-006` 进入 READY，按本决定冻结 Protocol、arm mapping、estimand、shared
   `ArmExecutionQualificationRecord` contract、A3/A4 pairwise comparability 与限制；
3. `M5-006` DONE 后，`M6-008` 才从 PARKED 解锁，按 frozen shared contract 实现 baseline
   envelope/Trace/Receipt，并只产生 A2 qualification record；
4. Skill-bearing actual binding 继续通过独立 `M5-SKILL-CLOSEOUT-REPLAY-GATE` 收口；
5. 只有 M5-006、M6-008、M11-004、M11-006 与 Skill replay Gate 全部满足后，M5-007 才可进入，并负责
   组装 A3 qualification record、独立重算 A2/A3 qualification 与 A3/A4 pairwise comparability；
6. M5-001/002、M4、M6-004 与 A4 admission 等真实执行 Gate 继续阻断 M5-004。

## 非目标

本 ADR 不实现 Schema、baseline runner、Receipt、Harness、真实 Provider、真实案例、Skill closeout、
Evaluation result、Human Review 或 disposition；不修改 M5-003、M6 session、M11 Bundle/View/Host/Receipt、
Capability、Method、Claim、permission 或 Topic 5 契约；不建立 automatic fallback、model routing、multi-Agent
orchestration、critic voting、recovery 或 Skill self-evolution。

## 接受条件

- 路诚钺确认 primary/secondary estimand、M5-003 treatment/read boundary 与 interpretation ceiling；
- 黄毅确认 A1/A2 的 M6 ownership、`M6-008` actual-fact/replay 责任及 M11 不被改写；
- 两位 owner 确认 Task exact-pin 与 treatment-visible input projection 不等于修改 Task；
- 两位 owner 确认 shared A2/A3 execution qualification exact 维持 frozen Task/Requirement/Supply、相关
  Mode/Action/Method、implementation/component/interface，且 boundary 只能等价或收窄；M6-008 只拥有 A2
  producer；Capability Resolver 仍是 A3 Resolution/Snapshot 唯一 producer/selector，M11 只验证和消费；
- 两位 owner 确认 A4−A3 只有在 `A3A4PairwiseComparabilityRecord` 证明唯一 delta 为 admitted Skill extension
  时才可称 Skill conditional increment，否则必须降级为 Skill-bearing package / bundled effect 或 unavailable；
- 两位 owner 确认 Decision 不等于 transport implementation，Gate A 关闭后 M5-007 仍因实现依赖与 Gate B
  保持 BLOCKED；
- 对抗性审查确认 A1/A2 无 Mode/Method/dummy Snapshot/Skill Assignment，A3−A2 不被解释为 pure Mode，
  且任何路径都不获得 permission、Supply selection、Task completion、Claim、Human 或 Topic 5 authority。
