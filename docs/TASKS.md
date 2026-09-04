# 实施任务清单

状态：`DONE / IN_PROGRESS / READY / BLOCKED / PARKED`

当前责任人：路诚钺维护 Method/Core、Mode/Action、Capability/Skill Evolution、Evaluation、Research
State/Claim/Method Trace，以及 Resolved Execution View/Skill supply mapping 的语义（M11-002/005/006）；
黄毅维护 Provider Adapter、API session、Runtime Bundle、Thin Execution Host 与执行 Trace/Receipt 集成
（M6、M11-001/003/004）。M11 的 Capability↔Runtime 交界是共享接口，按
[开发协作指南](DEVELOPMENT.md)进行跨负责人独立架构审查；具名 Task owner 仍对各自行的完成判断负责。

本文件是唯一 implementation-level source of truth。Phase 只表示宏观成熟度与解冻 Gate，Topic 只表示
架构责任域，M-group 表示 implementation family / development route，`Mxx-yyy` 才是可执行的原子 Task；
branch、PR、CI 和验收必须绑定 M Task。若架构文档出现近期工作而本文件没有对应 Task，
实现者必须停止并先走 `task-definition`，不能从 Phase/Topic prose 自行生成施工范围。

```text
Phase   = macro maturity / architecture Gate
Topic   = architecture responsibility / authority domain
M-group = implementation family / development route
Mxx-yyy = atomic executable Task
```

M-group reservation 只预留未来可能使用的 family namespace，不是 Task，也不属于下述状态机。施工总览见
[M-series Implementation / Construction Map](M_SERIES_IMPLEMENTATION_MAP.md)；精确状态与依赖仍只看本文件的
Task 行。

状态严格解释为：`READY` 的全部 hard dependencies 已 `DONE`、现在即可合法开始；`BLOCKED` 仍在计划
路径但至少一个 hard/external condition 未满足；`PARKED` 不在当前执行队列；`IN_PROGRESS` 必须确有
active implementation；`DONE` 只表示既有验收及证据已经接受，且行内容不可变。

本轮 Topic 映射使用 accepted architecture 中已有的责任名称。当前 `develop` 只正式使用了 Topic 4
（Agent / Model / Provider / Runtime）与 Topic 5（Execution / Context / Handoff / Recovery）的数字标签；
其他责任域使用名称而不擅自补编号。Topic mapping 是导航，不改变
[实名维护边界](DEVELOPMENT.md#1-实名维护边界)或 architecture authority。

## M0：架构与仓库

| ID | 状态 | 任务 | 验收 |
|---|---|---|---|
| M0-001 | DONE | 冻结产品定位与非目标 | Project Charter 完成 |
| M0-002 | DONE | 确立总体架构与模块边界 | 总架构 + 10 模块文件 |
| M0-003 | DONE | 将不同 Agent—Skill 绑定纳入架构 | Resolver、Assignment、预警与验收明确 |
| M0-004 | DONE | 建立实施、迁移与测试计划 | 三份实施文档完成 |
| M0-005 | DONE | 创建并推送独立 GitHub 仓库 | `main` 可访问，首次提交完成 |
| M0-006 | DONE | 建立零基础使用与发布就绪度指南 | 安装、离线 quickstart、真实运行边界、故障处理和分级发布 Gate 可由新用户顺序阅读 |
| M0-007 | BLOCKED | 选择项目许可证并核对仓库原创 Skills 的许可状态 | 人类维护者确定发布许可后加入 LICENSE，并消除 `project-original-unlicensed` 发布阻断 |

## M1：契约与 CLI

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M1-001 | DONE | 初始化 Python 包、pyproject 和基础 CI | M0 | 已合并 `main`；Python 3.11/3.13 GitHub CI 通过 |
| M1-002 | DONE | 实现核心对象模型与 JSON Schema | M1-001 | 7 类对象正反 fixture 通过 Draft 2020-12 Schema |
| M1-003 | DONE | 实现 Protocol、Mode、Profile、Skill Manifest | M1-002 | 能力、工具、输出、模式、冲突和 scoped permission 可验证 |
| M1-004 | DONE | 实现 Task、Attempt、Handoff、Main State | M1-002 | completed/incomplete Handoff、Attempt 与 checkpoint 示例通过 |
| M1-005 | DONE | 实现引用、revision、SHA-256 和 stale 检查 | M1-002 | 修改输入触发 `REF-HASH-MISMATCH`，input lock 不同触发 stale |
| M1-006 | DONE | 实现最小 CLI | M1-003..005 | init/validate/resolve/handoff/trace/checkpoint 可用 |
| M1-007 | DONE | 建立确定性风险检查 | M1-004..006 | Skill 缺失、越权、写冲突、Claim overreach、stale 注入均阻断 |
| M1-008 | DONE | 冻结模型 API 中立端口与能力协商语义 | M1-001 | Capability/Data Policy gap 在调用前阻断，提供商基线可查询 |
| M1-009 | READY | 建立外部可复用项目 scaffold 与 `0.x` 兼容政策 | M1-006 | `rwb init` 可生成或选择完整模板；新项目不需手工复制 Registry/Profiles/Skills；Schema/CLI 迁移与废弃规则明确 |

## M2：Agent 与 Skills

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M2-001 | DONE | 实现 Skill Registry 与 Resolver | M1 | accepted Registry、最小覆盖、显式选择、冲突、权限交集、版本/哈希锁与确定性 Assignment 已测试 |
| M2-002 | DONE | 定义四个 Agent Profiles | M2-001 | coordinator/evidence/simulation/reviewer 的权限、工具、输出和上下文边界可验证 |
| M2-003 | PARKED | 创建 literature-evidence-extraction Skill | M2-001 | `0.1.0` 已冻结为 legacy；结构证据保留，不再作为新任务默认 Skill，后续只由 Mode-derived Need + Trace 重新激活 |
| M2-004 | PARKED | 创建 simulation-vv Skill | M2-001 | `0.1.0` 已冻结为 legacy 并按 action 拆分；真实数值案例不得继续验证 broad bundle |
| M2-005 | DONE | 创建 handoff-integrity 检查 | M1 | 确定性脚本已验证 Task/input/Skill/artifact 交接边界，不宣称科学正确性 |
| M2-006 | PARKED | 扩展 Codex Runtime Adapter | M2-002, M2-005 | 已有 Agent/Skill 发现、验证和显式 dispatch 保留；平台 launch/collect 不在当前 Mode–Skill 关键路径 |
| M2-007 | PARKED | 执行首个双 Skill 垂直切片 | M7-002..006, M7-008 | 历史离线切片可精确 replay，但两个 broad Skill 均已 legacy；真实执行改由 Need + M3-008 路径重新定义 |
| M2-008 | PARKED | 建立外部 Skill 发现、隔离评估与准入 Registry | M1-005, M1-007 | 73 条候选和 11 个来源的可追溯库存已形成；停止来源驱动扩张，后续 dossier/trial 只由 Mode-derived Need 与 Trace Gate 激活 |

## M3：上下文与风险

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M3-001 | PARKED | Main State checkpoint/resume | M1-004, M1-005 | 规范化 digest、原子文件发布、Continuity 状态、机器证据哈希、Git 基线、下一动作和约束/决定丢失检查已通过；进程级 kill 矩阵与真实新主会话恢复待演练 |
| M3-002 | PARKED | context pressure 与 AWU 预算 | M3-001 | 可测/未知指标、动态 next-AWU/closeout/reserve 判定、WARN/rollover/block 和 checkpoint 链已测试；真实运行估计误差待采集 |
| M3-003 | PARKED | Handoff loss/stale/summary 抽查 | M1-004, M2-005 | Transfer Manifest/Audit、负面区段覆盖、风险触发抽查、Context/Receipt 绑定已实现；真实 H1/H2 成本与人工样本仍待执行 |
| M3-004 | PARKED | review loop/fanout/write race 检查 | M2-002, M2-005 | 并发预算、review loop、协调成本与既有 write race 检查已落地；真实停止行为待验证 |
| M3-005 | PARKED | 敏感 trace 策略 | M1-007, M2-005 | 外部/完整/敏感 trace 会阻断或警告；真实脱敏器与密钥 fixture 待实现 |
| M3-006 | PARKED | SAFE_PAUSE 与机器完成权 | M3-001, M3-002, M3-003 | AWU/完成/暂停条件、stage/safe-pause/waiting、执行结束与 `contract-satisfied` 分离、失败报告覆盖显式完成宣称和可恢复 pause fixture 已实现；进程级 kill 与真实新进程/新 Attempt 恢复待演练 |
| M3-007 | PARKED | 冻结实名 actor、Attempt Archive 与完整 Agent Trace 规则 | M3-003, M3-004, M3-005, M3-006 | ADR-0012、目录、消息信封、写前捕获、capture gap、按需读取和 Worklog 关系一致；负责人明确为路诚钺/黄毅 |
| M3-008 | DONE | 实现 Trace Envelope/Index/Event Schema、validator 与手工 fixture | M3-007 | 文件权威 Trace Core、确定性 validator、瞬时 tool-result provenance、Python 3.11/3.13 CI、覆盖率、Registry、wheel 与干净安装 Gate 均通过；不保存 Chain-of-Thought |
| M3-009 | DONE | 在 Execution Trace 之上增加 Method-aware Trace | M3-008, M8-003, M8-005, M9-005, M10-001, M10-002 | 建立独立、ref-only 的 Method Trace v0.1，记录 applied Method/Human Decision/State/path disposition；没有 accepted execution fact producer 时显式记录 actual-binding gap，且不得把 selected Snapshot 当作 actual execution 或把 gap-valid 写成 coverage-complete |

M3-001～007 的 `PARKED` 表示当前没有 active implementation，并非抹去已经进入仓库的 bounded v0.x
能力。各行同时混有已实现 contract slice、真实运行校准和未来 Topic 5 扩展，不能继续用无限期
`IN_PROGRESS` 表示债务。Phase C closeout 前不拆分或恢复这些工作；之后必须通过新的 R2
`task-definition` 决定哪些 residual work 形成独立 Task，不能直接把旧行重开成泛化 Recovery umbrella。

## M4：工件与复现

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M4-001 | DONE | source admission 与 provenance | M1-005, M1-007 | inbox 不可直接引用；admitted source 具有 exact identity/hash/provenance，拒绝未准入引用 |
| M4-002 | DONE | work → object/run promotion | M4-001 | 只有校验通过可提升；promotion 不等于 Claim 接受或 Human Decision |
| M4-003 | READY | Claim trace 与 counterevidence | M4-001, M4-002, M8-005 | 支持/反证/限制一次定位；validator 不代替科研判断或 Claim promotion authority |
| M4-004 | READY | Run manifest 与复现检查 | M3-008, M4-002 | 仿真案例可由 exact inputs/artifacts/environment refs 重建；不宣称结果科学正确 |
| M4-005 | PARKED | DVC 技术 spike | 真实大文件需求 | 无需求则不启动 |

## M5：真实案例与删减

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M5-001 | BLOCKED | 冻结 Evidence-Synthesis Evaluation Case Dossier | 人类提供/批准边界 | Public package 冻结 research question、exact admitted source set、inclusion/exclusion 与 data/read boundary、required outputs、Claim ceiling、initial context 和 Task；Private adjudication package 独立冻结 required facts、counterevidence、limitations、forbidden claims、evidence relations 与 Human scoring anchors；case/oracle 在观察 treatment output 前 hash-frozen 并记录选择理由、Human approval 与 no-treatment-specific-tuning |
| M5-002 | BLOCKED | 冻结 Theory + Simulation Evaluation Case Dossier | 人类提供/批准边界 | Public package 冻结 research question、exact model/equations、assumptions、parameters、inputs、simulation environment、required outputs、Claim ceiling 与 Task/context；Private adjudication package 独立冻结 invariants、numerical tolerances、failure/convergence conditions、limitations、forbidden overreach 与 evaluator anchors；case/oracle 在观察 output 前 hash-frozen、经 Human approval 且不得事后改写 |
| M5-003 | DONE | 建立最小 Evaluation Manifest 与 baseline harness | M9-002 | 冻结 Task、Model、Host、Tool/Snapshot、预算、上下文、指标与 evidence classes；可表达 plain Agent、Tool、Mode no-Skill/direct-tool 与 candidate Skill 对照，但不保存 Need 本体中的 trial 结果，不在 lifecycle 内重建 benchmark framework |
| M5-004 | BLOCKED | 运行已批准真实案例并分析 system-level net benefit | M4-001, M4-002, M4-003, M4-004, M5-001, M5-002, M5-003, M5-006, M5-007, M11-006, M6-004, `A4-RUNTIME-ADMISSION-GATE`（可审计外部条件） | 按 frozen protocol 对 approved real cases 执行全部四臂并保持共享条件；A4 保持 M5-003 的 `mode-candidate-skill` identity，但按 candidate-origin treatment + admitted Runtime execution 运行；Gate 必须 exact-pin candidate binding、`skill_evaluation_ref`、接受该 exact candidate/evaluation 的具名 Human Admission Decision、immutable accepted Release、candidate→Release exact identity/hash 或显式 promotion/build provenance、valid SkillReleaseProjection 与 projection-backed Skill Supply，再由唯一 Capability Resolver 形成 Snapshot→Runtime Bundle→Resolved Execution View→Thin Host 的逐跳 identity/hash closure；任一缺失即保持 BLOCKED，不以 synthetic Driver/projection 作为正式 evidence；primary net-benefit conclusion 只消费 `primary_confirmatory_eligible=true` 的 held-out cases，`admission-overlap` cases 只可作为 pilot/secondary evidence；failed Attempts 保留，blind Human Review 完成，metric evidence 完整或显式 unavailable/N/A，并产生 system-level analysis；单次成功不构成 promotion |
| M5-005 | BLOCKED | 里程碑删减与 disposition 评审 | M5-004 | 至少对一个机制作出 KEEP / KEEP-WITH-BOUNDARY / MODIFY / PARK / DEPRECATE / DELETE / STOP 或 accepted 等价决定，并引用 protocol、case dossiers、exact run set、blind reviews、analysis 与 known limitations；`admission-overlap` evidence 不得作为 pruning 的唯一证据，A4 较优或 sunk cost 均不自动触发 Skill promotion/KEEP |
| M5-006 | READY | 冻结 System-Level Evaluation Protocol | M5-003, `M5-BASELINE-TRANSPORT-ARCHITECTURE-GATE`（由 `PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND@1.0.0` 闭合） | 必须 exact-pin `docs/decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md` 及其 Gate record 中的 SHA-256；按已接受双传输固定 A1/A2→M6、A3→M11 Core、A4→M11 Skill extension，并把 `A4 − A2` 冻结为包含 transport difference 的 primary system-level estimand；`A2 − A1` 只作同 transport Tool 条件增量，`A4 − A3` 仅在 pairwise exact-equality closure 证明唯一 delta 为 admitted Skill extension 时才作 Skill conditional increment，否则降级为 Skill-bearing package / bundled effect 或 unavailable，`A3 − A2` 不得称 pure Mode effect；Decision 不等于 M6-008 实现证据，不修改 M5-003 treatment/read boundary、不给 A1/A2 注入 Mode/Method 或 dummy Snapshot，也不授予 Runtime/Method/Supply/Human authority；拥有并冻结覆盖 A2/A3 的 `ArmExecutionQualificationRecord@1.0.0` contract、Schema、comparison rule 与 fail-closed validator，要求 exact-pin Manifest/arm、Task、Requirement、frozen/runtime Resolution/Snapshot、相关 Mode/Action/Method、Supply/component/implementation/interface 与 typed live evidence，且 permission/data-egress/side-effect ceiling 只能等价或收窄；M6-008 只产生 A2 record，A3 runtime Resolution/Snapshot 仍由唯一 Capability Resolver 产生/选择，M11 只验证并消费 exact Snapshot，M5-007 引用两端对象组装 A3 record；冻结 versioned/hash-pinned `A3A4PairwiseComparabilityRecord`，逐项比较 shared case/Task/conditions、Mode/Action/Method、non-Skill Requirement/Supply/component、Tool/procedure、provider-visible interface 与相关 boundary，结果仅允许 `exact-skill-only`、`skill-bearing-package`、`not-comparable`；随后预注册 secondary comparisons、randomization、replicates、pilot/stopping/retry、model/provider drift、blinding/reveal、跨 transport metric comparability、measurement status、analysis rule 与三层 decision hierarchy；定义独立于 M5-003 v0.1 的版本化 A4 execution-qualification overlay，exact 引用 frozen candidate/evaluation 与准入后 Release→Projection→Supply→Resolution→Snapshot→Bundle→View→Host lineage，而不修改 Manifest 或产生 admission/permission authority；冻结 admission-evidence overlap / held-out policy，并定义独立、versioned、hash-pinned `AdmissionEvidenceOverlapAssessment`，exact-pin `skill_evaluation_ref`、admission case IDs、Task/input refs、typed private-oracle/checker/Human-adjudication identities/hashes、两侧 comparison input closure、`checked_at`、validator identity/version/hash 与计算结果；`absent`/`unknown` 不得解释为 held-out；overlay exact 引用该 assessment，并记录 `case_selection_frozen_at`、`admission_evaluation_ref`、`overlap_status`、`overlap_refs` 与派生的 `primary_confirmatory_eligible`；measured/estimated/unavailable/not-applicable 严格区分，blind phase 隐藏 arm/Skill/cost/token/RWB 标签，Research Integrity 退化不得由效率抵消且禁止单一 weighted aggregate score |
| M5-007 | BLOCKED | 建立 System-Level Evaluation Harness | M5-006, M6-008, M11-004, M11-006, `M5-SKILL-CLOSEOUT-REPLAY-GATE`（Issue #55 可审计外部条件） | 编译 frozen plan、以 fresh Attempt/session 启动 exact arms，并在 A4 执行前于 Harness/Maintainer 侧验证 versioned execution-qualification overlay 与 `A4-RUNTIME-ADMISSION-GATE` 的逐跳 identity/hash closure；在 confirmatory freeze 前加载 `AdmissionEvidenceOverlapAssessment`，验证其 exact Evaluation/validator/input pins 与 `checked_at <= case_selection_frozen_at`，从 assessment 两侧闭包独立重算 M5-001/002 case / Task / input / private-oracle intersection、status 与 eligibility：缺失、`absent`/`unknown` 或未闭合即 fail closed，任一重叠必须记录为 `admission-overlap`、列入 `overlap_refs` 且令 `primary_confirmatory_eligible=false`；无解释的 candidate/Release substitution、hash drift 或 Resolver 选择其他 Supply 也必须 fail closed，Runtime 不读取 candidate/evaluation/lifecycle history；A1/A2 必须消费 M6-008 的 allowlisted treatment-visible baseline envelope 与 replay-valid closeout；正式 A2/A3 必须加载并用 M5-006 validator 独立重算 exact `ArmExecutionQualificationRecord@1.0.0`：A2 record 由 M6-008 产生，A3 runtime Resolution/Snapshot 由唯一 Capability Resolver 产生/选择，M11 只验证并消费 exact Snapshot，且 record 只由 Harness 在 Maintainer/Evaluation preflight 组装；两者均须证明 frozen structural binding 与 runtime-execution binding 的 Task/Requirement/Supply/component/implementation/interface 及相关 A3 Mode/Action/Method 未替换、所有 ceiling 未放宽，并拒绝 `structural-replay`/`execution_input=false`/fixture-only binding；在 plan/pre-run 与 analysis input 阶段加载并独立重算 `A3A4PairwiseComparabilityRecord`，只有 `exact-skill-only` 才可标注 Skill conditional increment，`skill-bearing-package` 必须降级为 bundled/package effect，`not-comparable` 令该 secondary contrast unavailable；预注册 exact equality 后发生 drift 必须 fail closed，当前 Method/Supply disposition incompatibility 不得由 Harness 掩盖；A3/A4 分别消费 M11 Core/Skill extension，Harness/M6-008 不取得 Supply selection；Harness 不得把 raw Task control、dummy Method/Snapshot 或 Skill Assignment 注入 plain arms；以 M11-004（传递 M11-003）的 Core Host actual-fact / Trace / generic-closeout contract 和 M11-006 Skill mapping 为明确输入，执行后必须由 typed execution fact 与 replay-valid Receipt 独立证明 actual Projection/Supply/binding 与 overlay 相同，区分 completed、post-call failed 与 preflight blocked，禁止用 planned View 冒充 actual facts；`M5-SKILL-CLOSEOUT-REPLAY-GATE` 必须先接受 projection-backed Skill actual binding 的 replay-valid closeout seam，或由 R2 正式修订本 Task 验收，不能把 M11-004 Core Receipt 假写成已经支持 Skill；Harness 只能在不改变 arm treatment/read boundary 的评价记录层统一 evidence，闭合匿名化、metric evidence、Human Review、reveal map 与 analysis input，不得 special-case A4、直接加载 candidate 目录、在 confirmatory run 使用 synthetic projection、自动 promotion/pruning/Human scoring；harness implementation 不等待真实 case data，正式 execution 留给 M5-004 |

M5-006 的 exact Decision pin 为
`docs/decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md`，raw SHA-256
`64edd73c44bc77f326a90c51e0a8cbf5fd28c4bbf1a5e18aca7f50250ce21a12`；该值与 Gate record 不一致时
M5-006 acceptance fail closed。

## M6：API Execution（黄毅维护）

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M6-001 | DONE | OpenAI/Anthropic/Gemini 薄 Model Provider Adapters | M1-008 | 三家 provider-neutral 薄 Adapter 的离线 contract 测试已通过；live conformance 单独由 M6-004 验收 |
| M6-002 | DONE | 显式模型池与隔离 API session kernel（`K-API-1`） | M6-001 | primary/worker/specialist 槽只可显式绑定；轮次、工具、并行、工具结果、输出、token/成本/time 有硬边界；无自动 fallback；离线测试通过 |
| M6-003 | PARKED | 保留 Task-to-API 文件闭环（`K-API-2`）历史兼容 seam | M1-008, M2-001, M2-002, M2-005, M6-002, M9-005 | legacy compatibility seam 继续可解释；未来 Runtime Bundle、Resolved Execution View、Thin Execution Host 与 generic Trace/Receipt 主链由 M11-001～004 承担，本 Task 不再作为新 execution umbrella |
| M6-004 | BLOCKED | 选定模型槽的真实 Windows Provider/session conformance | M6-001, M6-002 | 当前版本的 OpenAI text/structured/tool 与 bounded evidence-shaped 调用仍待授权 Windows 环境重放；该调用只验证 Provider/isolated session，不依赖 M11-004，也不冒充 Task→View→Host→generic Receipt 的端到端 Gate |
| M6-005 | PARKED | streaming/multimodal/server tools 与平台 Adapter | 真实案例或平台选择 | 黄毅决定执行端启动条件；没有真实需求不启动 |
| M6-006 | DONE | API/平台执行时自动写入 Agent Trace | M3-008, M6-003 | legacy Skill-bound execution 已完成 SessionEventSink、traced runner、archive closeout、file-only verify、recovery preflight 与 Attempt/Receipt Trace linkage；Method-dependent Part C 等待 M8-003 |
| M6-008 | PARKED | 建立 Phase D baseline-arm traced execution envelope 与 replay-valid closeout | M5-003, M5-006, M6-002, M6-006, M11-004 | 在 M5-006 冻结 shared contract 后，按 ADR-0020 从 A1/A2 frozen arm 确定性编译独立版本的 baseline envelope：`provider_visible_payload` 必须使用正向白名单与 `additionalProperties=false`，只含 frozen public instruction/input/output contract，A1 Tool surface 为空，A2 唯一额外暴露为 exact Tool definition/interface；完整 Task、`agent_profile`、Mode/Action/Method、Task `required_capabilities`、Capability Requirement/Resolution/Snapshot control、Skill/private-oracle 与未来未知 Task 字段只能留在不可见 enforcement metadata；checked-in `structural-replay` Tool fixture 不得用于正式 execution，M5-004 A2 必须绑定 `runtime-execution`、`execution_input=true` 且 Tool implementation/availability/boundary/typed conformance 闭合的 Snapshot，并按 M5-006 冻结的 shared contract 产生 A2 `ArmExecutionQualificationRecord@1.0.0`，exact-pin Manifest/arm、Task、Requirement、frozen/runtime Capability Resolution/Snapshot，再证明两端 Tool supply identity、implementation version/hash、component、provider-visible interface 相同且 permission/data-egress/side-effect ceiling 只等价或收窄；M6-008 不产生 A3 record、不修改 M11，也不取得 Supply selection 或 shared-contract ownership；每次 provider request 消费 payload 前与每次 Tool invocation 前立即重载/重验对应 envelope/implementation/interface/boundary/conformance pins，Trace actual facts 记录 use-boundary 的 bytes/hash；以 transport trusted start/end clock 执行 time budget，分开 preventive 与 detective semantics；通过 M6 isolated session 形成 exact Provider/Adapter/Model/Runtime/Host/Tool actual facts、Trace、Artifact、Validation 与独立文件 replay Receipt，actual binding 必须由 typed hash-pinned Trace fact 独立佐证；区分 completed/post-call-failed/preflight-blocked，不复用 mandatory Skill Assignment，不 fallback/reselect/rebind，并固定 `task_completion=false`，不产生 Claim/Human/admission/promotion/pruning/Topic 5 authority |

2026-08-19 的历史 live 诊断不替代当前 M6-004 Gate；OpenAI live conformance、EVID/SIM SIR 与
process-kill recovery 均不作为 `K-INTEGRATION-1` 的合并阻塞项。

## M7：Mode–Skill 选择与协调成本

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M7-001 | DONE | 冻结实名 owner、受控读取与分级 Handoff 文档策略 | M2, M3 | 路诚钺/黄毅职责、ADR-0011/0012、架构图和开发入口一致 |
| M7-002 | DONE | 建立现有 Mode 决策卡与边界 fixtures | M1-003 | 八个诊断 case 覆盖 evidence/simulation trigger、no-Mode、candidate Mode、组合拆分与歧义阻断 |
| M7-003 | DONE | 建立 Task-to-Mode/action/mechanism 选择矩阵 | M7-002, M7-011, M7-008 | tool-only/no-Skill、Skill Need、拆 Task、capability gap、blocked 和 Human Gate 均有可复验路径；无隐式 Assignment |
| M7-004 | DONE | 按 Mode action 重新审计并迁移三个 0.1.0 Skill 原型 | M7-011, M7-008 | 三个冻结包均有 action、direct baseline、manifest/package hash、new-assignment/版本决定与机器夹具；未创建无证据的 `0.2.0` |
| M7-005 | PARKED | 独立整理/重写最多两个 Mode-derived Need 并作证据化去留决定 | M7-011, M3-009, M8-003 | 不再从来源 shortlist 直接选择；`claim-preserving-rewrite` Stage 1 保留为历史诊断，新的 trial 等待正式 Need/Method Trace |
| M7-006 | PARKED | 建立 H0/H1/H2 与内容读取成本对照 | M3-008, M8-003 | 保留为 Evaluation baseline 输入；Method Resolution 稳定后再用 Attempt Archive 记录遗漏、返工、回查和 capture gap |
| M7-007 | PARKED | 新增 experiment/theory/observational/engineering Mode | 真实案例 + Mode 准入卡 | 证明现有 Mode 组合不足后逐个启用 |
| M7-008 | DONE | 为已确认 Mode action gap 建立首批 Tool capability cards | M1-008, M7-011 | 五张 Action-driven cards 已明确数据出口、权限、副作用、预算、失败、验证、fallback 与 owner；未实现 API/Adapter |
| M7-009 | DONE | 建立多来源 Skill 候选池与机器/人工筛选 Gate | M2-008 | 首批 54 个入口均已固定来源、路径、内容哈希和人工 Decision；一方 19 项为 18 `reference`/1 `rejected`，社区 35 项为 6 `triage`/21 `reference`/8 隔离或排除；下载内容未安装、执行或自动准入 |
| M7-010 | DONE | 建立四个来源候选 dossier 并决定是否进入验证 | M7-004, M7-009 | 四份历史 dossier 已完成；Human Decision 选择 0 个来源候选直接重写，转入 ADR-0013 的 Mode-derived Need 路线 |
| M7-011 | DONE | 建立两个正式 Mode 的 Action–Failure–Artifact–Gate 与 Skill Need 基线 | M7-002, M7-010 | evidence/simulation 的每个 action 有最小机制；每个 Mode 首批 Need≤2；no-Skill、Tool、Skill Need、blocked、Human Gate 均可出现 |
| M7-012 | DONE | 建立 project-internal Skill Need 路线与候选占位 | M7-001, M7-011 | 与 Mode-derived 路线分离；交互、输出、恢复和 Gate 候选先比较 Protocol/template/Tool；未新增 Skill/Registry/Runtime |
| M7-013 | DONE | 为两个优先 project-internal Need 建 direct baseline、failure fixture 与 compact dossier | M7-012, M1-004 | H1 omission 与 H2 semantic reversal 均形成可复验诊断；两项结论均为 `hold-no-skill`；未修改自动 Trace/API |
| M7-014 | PARKED | 对 project-internal 候选做有 Trace 的困难任务比较 | M7-013, M3-009, M8-003 | 比较 template/tool/compact Skill 的遗漏、回查、返工和上下文成本；无重复语义增量即退役 |
| M7-015 | DONE | 分离 Skill 历史解析与新分配 lifecycle | M7-004 | Registry/Resolver 表达 active/legacy/deprecated 与精确版本约束；旧 Assignment 可复验，新路由不能选择 legacy/deprecated |
| M7-016 | DONE | 执行 K-MS-1 节点评审并冻结基线 | M7-002..004, M7-008, M7-011..015 | 九项条件逐项 PASS；Decision 接受离线选择/治理基线并 safe stop，不自动进入真实 trial |

## M8：Method Core Formalization

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M8-001 | DONE | 按第二轮审计重整全局架构文档与路线 | M7-016 | ADR-0016、五平面架构、ROADMAP、审计吸收记录和单一真值导航一致；未验证外部项目或实现新 Schema |
| M8-002 | DONE | 将 Mode Action 正式化为一等契约 | M7-011, M8-001 | 两个正式 Mode 的 Action 有 stable ID/version/hash、trigger/non-trigger、failure/artifact/claim/gate/stop/blocked；既有 fixture 无损引用 |
| M8-003 | DONE | 建立版本化 Method Resolution | M8-002 | 八个 routing fixture 转成 provider-neutral Resolution；正式表达 no-Skill/tool/Skill Need/Human/split/blocked 与 rejected alternatives |
| M8-004 | DONE | 建立最小 migration seam 并迁移 Research Mode v0.1 → v0.2 | M8-002, M8-003 | v0.2 删除直接 Skill recommendation；v0.1 仍可验证/历史解释；迁移保留原/新 hash 与实现版本 |
| M8-005 | DONE | 冻结 Decision Authority Matrix 并映射 validation/preflight | M8-002, M8-003 | Agent proposal、deterministic resolution、Human Gate、权限放宽和 Claim promotion 权限有正反 fixture |

M8 / Phase A 已通过 PR #30 的 R2 跨负责人审查并于 `develop@ead1270` 收口。这里的完成含义是
Method/Core 契约和下游消费边界稳定，不表示 Capability binding、Resolved Execution View、Method Trace、
Human Decision 或端到端研究执行已经实现。

## M9：Phase B Evolution Foundation

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M9-001 | DONE | 将 Capability Requirement 正式化为需求侧契约 | M8-003, M8-005 | 可表达目标能力、输入/输出、permission/data-egress/side-effect/验证约束；不含 Provider/Model/Adapter、可用性或具体供给绑定；Method Resolution 引用可闭合验证 |
| M9-002 | DONE | 将 Skill Need 正式化为版本化对象 | M8-003, M9-001 | need identity、trigger/non-trigger、semantic gap、no-Skill/direct-tool baseline、expected increment、evaluation criteria、required evidence classes 与 domain scope/variants 可验证；Need 只声明未来 trial/promotion 所需证据，不保存实际结果，也不等于 candidate/accepted Skill |
| M9-003 | DONE | 建立 Skill lifecycle v2 与显式迁移 | M7-015, M9-002 | intake、evaluation state、admission、runtime eligibility 四轴分离；可表达 trial/superseded/retired 并引用 baseline/trial/evaluation record/decision 与 promotion evidence；不重建完整 benchmark/metric/experiment framework；旧 Registry identity 和历史 Assignment 继续可解释 |
| M9-004 | DONE | 建立最小 Protocol Profile 契约 | M8-004, M9-001 | M9-001 接受后可与 M9-002/003 并行；以两个有界 PRISMA/V&V profile 表达 applicable/not applicable、method obligations、Gate/evidence expectations，并证明 Mode、Protocol、Skill 职责不重叠；不固定全局 DAG，不绑定 Skill/Tool/Provider/Runtime |
| M9-005 | DONE | 建立 Capability Supply Report、Capability Resolution 与 Resolved Capability Snapshot 共享接口 | M9-001, M8-005 | M9-001 接受后 Core 可独立 READY，支持 no-Skill、direct Tool、Adapter/Provider supply facts 与受 ceiling 约束的 resolution/snapshot；Report 不选择自身，Resolution 区分 satisfied/gap/ambiguous/blocked，Snapshot 冻结 exact supply/version/hash/permission/data-egress/side-effect/conformance refs；Skill Supply Extension 仅在 M9-003 runtime eligibility 稳定后接入；不实现 API session 或 Runtime consumer |
| M9-006 | DONE | 完成 Phase B migration/replay 与替换性 Gate | M9-002..005 | 已发布旧对象经显式 migration 继续解释；同一 Task/Mode/Action/Method/Requirement 在 Supply A→B 替换时只生成不同 Snapshot，且 permission/data-egress/side-effect ceiling 均不放宽、Runtime 不获得 Method authority；Phase B Stop Gate 有逐项证据 |

## M10：Phase C Research State & Verification

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M10-001 | DONE | 建立并审计最小 durable Research State composition candidate | M1-002, M8-005, M9-005 | 用两个 bounded case 与反例检验最弱表示；当前 Unknown/Assumption item、Contradiction relation、derived Frontier、provenance-bearing Human Decision 与 Evidence relation 都是 implementation hypothesis，不预冻结最终 Schema；exact ref 结构可确定验证，科学判断与最终表示须 Human/R2 接受 |
| M10-002 | DONE | 建立 Attempt / Research Failure 语义与独立 lineage candidate | M1-004, M10-001 | Attempt 分离 from-State、optional predecessor Attempt 与 reopen justification；多个 Attempt 可共享 State，State 可由 Evidence/Human Decision 独立演化；Research Failure universal minimum 仅冻结 learned result/revisit condition，当前 source Attempt/observed/uncertainty 是 bounded profile candidate，并与 execution failure、negative Evidence、Capability Gap、Skill Need 分离 |
| M10-003 | DONE | 完成 Phase C bounded continuity / verification Gate | M10-001, M10-002, M3-009 | evidence-synthesis 与 synthetic simulation-negative 两案在 staged 新进程中只读 compact State、Method Trace 与 runner-owned exact closure；private oracle 只检查 exact output/read surface/fixture predicates 与 known-failure behavior，不能证明 reviewer reconstruction或科学正确性；具名 Human semantic review 与 R2 closeout 独立，Gate 不授权 Topic 5 实现 |

## M11：Phase F Execution Reintegration

M11 把 M6-003 的未来 umbrella scope 拆成可独立失败、审查和验收的 producer/consumer contracts。
Core（M11-001～004）必须在零 Skill、零 Evolution Registry 下闭合；Skill supply publication/mapping
（M11-005～006）是可选支线，不阻塞 Core。M11-001→002→003→004 保持四个独立 implementation /
acceptance identity；它们可按 `DEVELOPMENT.md` 的通用 module-level PR 规则，在一个强耦合
Execution Reintegration PR 中依拓扑顺序原子集成。PR 粒度不合并 Task identity，也不允许跳过逐 Task
implementation slice、commit、evidence、owner review 或 hard dependency。

| ID | 状态 | 任务 | 责任人 | 风险 | Phase / Topic | 依赖 | 验收 |
|---|---|---|---|---|---|---|---|
| M11-001 | DONE | 建立 Runtime Bundle / Consumer Profile | 黄毅 | R2 | F / Topic 4 | M9-005 | 以显式 closure manifest 固定 Runtime 可读取的 exact objects/hash/import graph；拒绝目录输入、递归扫描 Registry/examples、Evolution validator import 与 fixture-only `structural-replay`；零 Skill/零 Evolution Registry 路径通过 |
| M11-002 | DONE | 建立 supply-neutral Resolved Execution View Core | 路诚钺 | R2 | F / Research Control + Topic 4 | M9-005, M11-001 | 从 frozen selection 计算并冻结 exact Host/Provider/Adapter/Model、external pin/freshness、Task/Profile/DataPolicy/Host policy 与 permission/data-egress/side-effect 最严交集；fail closed，不重新选择 Supply、不 fallback、不要求 SkillReleaseProjection |
| M11-003 | DONE | 建立 Thin Execution Host 与 actual execution fact report | 黄毅 | R2 | F / Topic 4 | M3-008, M6-002, M11-002 | Host 只消费 exact closure-valid Snapshot/View，执行冻结调用并报告 actual facts、bounded Diagnostic 或 re-resolution request；不能 reselect/rebind/fallback、修改 Method/Claim/Gate 或扩大边界；不实现 Topic 5 的 Handoff/context/recovery 语义 |
| M11-004 | DONE | 建立 generic execution Trace/Receipt linkage 与 Core vertical Gate | 黄毅 | R2 | F / Topic 4 + Artifact/Trace | M3-008, M11-003 | no-Skill 与 direct-tool bounded path 可从 Task/View/Host 到 Trace、Artifact、Validation、generic Receipt 闭合；复用 observability contract 不构成 Topic 5 membership；不伪造 Skill Assignment，不把 execution completion 写成 Claim/Human acceptance，并保留 legacy Receipt replay |
| M11-005 | DONE | 发布不可变 SkillReleaseProjection | 路诚钺 | R2 | F / Capability/Skill Evolution + Topic 4 | M9-003 | 只发布 accepted immutable Skill Release 的 runtime-minimal identity/version/hash/capability/boundary facts；不暴露 Need/Evaluation/Lifecycle 历史，不授予选择或执行权限；缺失只阻断 Skill new-binding |
| M11-006 | DONE | 将 eligible Skill supply 映射进统一 Resolved Execution View 语义 | 路诚钺 | R2 | F / Research Control + Capability/Skill Evolution + Topic 4 | M11-002, M11-005 | projection-derived Skill 与 Tool/procedure/Adapter 使用同一 Report→Resolution→Snapshot→View 语义；Capability Resolver 仍是唯一 selector，View/Host 保持 supply-kind neutral；不得形成 Skill-specific Runtime dispatcher/session/fallback seam，projection 缺失/stale/mismatch 时仅该候选 fail closed |

## M14：Product / Release Closure

M14 由 [ADR-0021](decisions/0021-CURATED-DEVELOP-TO-MAIN-RELEASE.md) 与
[Issue #57](https://github.com/Chengyue-Lu/research-agent-workbench/issues/57) 激活。它只负责把 frozen
`develop` 工程真相确定性投影为可安装、可追溯的精选 `main` 发行视图；不修改 Runtime、Method、Claim、
Human Decision 或 permission 语义。Issue 中的 `REL-001～005` 是工作包别名，以下 `M14-*` 才是 canonical
implementation / acceptance identity。

| ID | 状态 | 任务 | 责任人 | 风险 | Phase / Topic | 依赖 | 验收 |
|---|---|---|---|---|---|---|---|
| M14-001 | DONE | 建立 curated release topology 与 source trust governance（REL-001） | 路诚钺 | R2 | Product / Release Governance | M0-005, M1-001 | 以声明式 policy 建立 dormant、same-repository、version-valid `release/v* -> main` R2 topology；分别校验 external expected frozen develop source/repository trust 与 exact current main Git parent/ancestry，但所有 release-branch PR 在 M14-005 readiness/cutover 前显式 fail closed；普通 feature/task-definition 仍进入 develop，现行 exact `develop -> main` 保持唯一可执行发布路径；不能只凭分支名放行，也不恢复 direct push/force/delete 或在 release branch 修改产品语义 |
| M14-002 | PARKED | 建立 deterministic release surface、manifest 与 export/check（REL-002） | 路诚钺 | R2 | Product / Release Projection | M14-001 | strict、append-only versioned allowlist 与 manifest Schema 驱动同一 export/check 实现；每个输出分类为 source-blob 或 exact allowlisted generated，分别 pin blob/mode/size/hash 或 generator identity/version/hash/inputs，manifest 使用无自哈希歧义的 canonical UTF-8 JSON/LF/稳定排序且禁止时间、随机数和临时绝对路径；直接读取 frozen develop commit Git blobs，在以 exact current main 为 Git parent 的生成分支上完整构建 projection，并由 external expected repository/source/parent 重算 selection/excluded/output closure；unknown/重复/overlap/不存在 include、casefold/Unicode/Windows path collision、dirty tree、CRLF、mode/byte drift、额外/隐藏/移动/遗留文件、path escape、symlink/gitlink、undeclared generated、policy drift 及同步重算伪 hash 全部阻断；连续 v1→v2 fixture 证明旧版独有 generated 文件不会残留，prospective merge-result tree、projection tree 与 manifest closed output tree 完全相同，main parent 漂移时必须重新生成；critical checker 满足 95/90 与独立正反 evidence，但不启用 release merge path |
| M14-003 | PARKED | 闭合 portable package 与 Runtime data boundary（REL-003） | 路诚钺 | R2 | Product / Package + Runtime Resources | M14-001 | 定义独立 hash-pinned `RuntimeResourceManifest`、packaged default resolver，并分离 project/filesystem、immutable runtime-resource、integration-config 三个 root，禁止隐式 CWD/checkout fallback；公开 Runtime catalog 与 maintainer/publication history 分离，repository publication validation 与 installed-runtime catalog validation 分层；wheel/sdist→wheel exact assets 在清空 `PYTHONPATH` 的 checkout 外 Python 3.11/3.13 环境加载 Schema、Mode/Action、Authority、Requirement、Profile 与空 Projection，并由 wheel-owned/generated input 完成 no-Skill structural quickstart；非空 Projection 必须通过 logical→installed path mapping 闭合其 exact immutable Skill manifest/package bytes且拒绝 orphan/unindexed asset，否则 fail closed；legacy `accepted.json` selector、`sources.json`、Need/Evaluation/Lifecycle、provider baseline、broad `.agents/**` 与 `.codex/**` 不得成为 packaged default，但被 Projection exact path/hash 引用的单个 accepted manifest/package 可作为条件 Runtime Release asset |
| M14-004 | PARKED | 建立 public documentation surface（REL-004） | 路诚钺 | R2 | Product / Public Documentation | M14-002, M14-003 | README、Getting Started、Supported Features 与公开导航有单一来源，release tree 无指向 TASKS/STATUS/DEVELOPMENT/workstream 等排除文件的断链；文档区分 structural、bounded、live 与 evaluated 证据，不把空 Projection index、未完成 M5、synthetic fixture 或未验证 Provider 写成已交付能力 |
| M14-005 | BLOCKED | 生成并验收首个 curated main release（REL-005） | 路诚钺 | R2 | Product / Release | M0-007, M1-009, M14-002, M14-003, M14-004, `GITHUB-RELEASE-PROTECTION-GATE` | 在全部依赖、许可证、scaffold、远端保护与具名 Human release decision 闭合后，冻结 exact develop source SHA 和 exact current main parent SHA；从该 main tip 创建 release branch，由 exporter 只读取 frozen develop Git blobs并完整构建 tree/manifest，两次生成稳定；main 前移必须按新 parent 重建；source required CI、release checks、双 Python clean-install、no-Skill smoke、Registry/Projection load、公开链接与零内部材料泄漏均通过，且 prospective merge-result tree = projection tree = manifest closed output tree；同一 Task 的治理激活与首次 release 按可审计 slice 执行，原子启用 `release/v* -> main` 并禁用 direct `develop -> main`；R2 release PR 以 merge commit 合入 main 后 tag/artifact/hash 与 manifest 闭合，release branch 不回并 develop |

## Future M-series reservations

以下条目只是 expected implementation-family namespace，不是 Task：没有 `READY / BLOCKED / PARKED / IN_PROGRESS / DONE`
状态，不创建 future 原子 ID，也不冻结 owner、risk、dependency、acceptance 或
Schema。Reservation 不授权 implementation，不代表 architecture acceptance 或解冻；若未来证明既有
M-group 足以承载，可直接取消且不产生历史 Task identity。当前不推测 M15+。M14 已由独立 R2
task-definition 激活，不再属于 reservation。

| Reserved M-group | Expected implementation family | Activation condition | Confidence |
|---|---|---|---|
| **M12 — RESERVED** | Execution Continuity & Recovery：Handoff、context rollover、safe pause/resume、recovery、clean/salvage recovery 等 Topic 5 residual implementation | Phase C closeout，且完成独立 Topic 5 R2 architecture review 与 docs-only task-definition | High |
| **M13 — RESERVED** | Strategy & Governed Evolution：strategy interface、candidate strategy、bounded experimentation、merge/prune/governed evolution | Phase C/D evidence 证明现有 M2/M7 无法自然承载一个新的 coherent implementation family | Medium–High |

Reservation 只有在对应 architecture activation Gate 已接受、已有 M-group 不足已有证据、独立 docs-only
`task-definition` 完成后，才可转换为正式 M-group，并在当时定义具体 `Mxx-yyy`、owner、risk、dependency、
acceptance 与 negative boundaries。因此：M12 reservation 不等于 Topic 5 thaw 或 implementation approval；
M13 不等于 strategy framework approval。

## 未完成 Task 的责任与阶段索引

详细 objective/scope/acceptance 以各 Task 行为准；本表补齐 owner、risk、Phase 与 Topic 导航，不生成
第二套状态。具名 owner 对完成判断负责；共享接口仍按 `DEVELOPMENT.md` 触发 cross-owner review。

| Task | Owner | Risk | Phase | Topic / responsibility | 当前路径说明 |
|---|---|---|---|---|---|
| `M0-007` | 路诚钺 | R2 | Release Gate | Repository / Governance | 缺人类许可证决定，BLOCKED |
| `M1-009` | 路诚钺 | R1 | F / release readiness | Repository / Product integration | 独立 READY，不阻塞 Phase C/F Core |
| `M2-003, M2-004, M2-007, M2-008` | 路诚钺 | R1～R2 | E / optional evaluation | Capability / Skill Evolution | legacy 或来源驱动路线，保持 PARKED |
| `M2-006` | 黄毅 | R1 | F / optional platform | Topic 4 | 无真实平台需求，保持 PARKED |
| `M3-001～007` | 路诚钺、黄毅按既有边界 | R2 | pre-A bounded slice；post-C future | Topic 5 + Artifact/Trace | 无 active implementation，future residual 等待 Phase C closeout 后重新 task-definition |
| `M4-002` | 路诚钺 | R1 | C / D | Research State + Artifact/Trace | exact validation closure 与 fail-closed promotion 已实现，DONE；eligibility 只由 promotion 时重执行 accepted pinned runner/checker 确立；validation 三元组仅为 claimed provenance metadata，错误 PASS 阻断，byte-exact 自报历史可通过有效性检查但不产生历史 producer/operator/time 权威 |
| `M4-003, M4-004` | 路诚钺 | R1；M4-003 R2 | C / D | Research State + Artifact/Trace | M4-002 已完成；两个独立后继均为 READY，仍须分 Task/PR 验收 |
| `M4-005` | 路诚钺 | R1 | deferred | Artifact/Trace | 只在真实大文件需求出现时恢复 |
| `M5-001, M5-002` | 路诚钺 | Human decisions R2 | D | Evaluation + Research State | 等待人类选定并批准两类真实案例边界，BLOCKED |
| `M5-004, M5-005` | 路诚钺 | R1；Human decisions R2 | D | Evaluation + Research State | 真实执行仍等待 M4 闭环、M5-001/002、Protocol/Harness、live Provider 与当前未满足的 A4 external admission Gate，BLOCKED |
| `M5-006` | 路诚钺 | R2 | D | Evaluation protocol | ADR-0020 已选择并 exact-pin dual transport，`M5-BASELINE-TRANSPORT-ARCHITECTURE-GATE` 闭合；当前 READY，可先实现 Protocol，但不得把 Decision 当成 M6-008 transport 证据 |
| `M5-007` | 路诚钺 | R2 | D | Evaluation harness + Runtime evidence linkage | 等待 M5-006、M6-008 与 `M5-SKILL-CLOSEOUT-REPLAY-GATE`；M11-004 Core actual-fact/Trace/Receipt contract 与 M11-006 Skill mapping mechanism 均已 DONE；真实 A4 admission Gate 不阻塞 synthetic Harness 实现但阻塞 M5-004 execution |
| `M6-003` | 黄毅 | R2 | historical / F compatibility | Topic 4 + Topic 5 | legacy seam PARKED；mainline superseded by M11-001～004 |
| `M6-004` | 黄毅 | R2 | F | Topic 4 | 只等具名 live authorization；与 M11-004 无 hard dependency，BLOCKED |
| `M6-005` | 黄毅 | R1～R2 | deferred F | Topic 4 | 真实需求/平台选择前 PARKED |
| `M6-008` | 黄毅 | R2 | D / F | Evaluation + Topic 4 + Artifact/Trace | ADR-0020 产生的 baseline transport 实现入口；等待 M5-006 冻结 shared qualification contract，当前 PARKED；不替代 Skill replay Gate |
| `M7-005, M7-006, M7-014` | 路诚钺 | R2 | D | Research Control + Evaluation + Skill Evolution | evidence-driven trials PARKED |
| `M7-007` | 路诚钺 | R2 | E | Research Control / Mode | 真实案例证明 Mode gap 前 PARKED |
| `M14-001` | 路诚钺 | R2 | Product / Release | Release Governance | dormant curated release topology/source trust seam 已实现并保持 fail closed，DONE |
| `M14-002, M14-003` | 路诚钺 | R2 | Product / Release | Projection + Package/Runtime Resources | M14-001 已满足；两项仍需独立激活并可作为并行 slice，当前 PARKED |
| `M14-004` | 路诚钺 | R2 | Product / Release | Public Documentation | 等待 deterministic surface 与 portable package，当前 PARKED |
| `M14-005` | 路诚钺 | R2 | Product / Release | First Curated Release | 等待 M0-007、M1-009、M14-002～004 与远端 GitHub 保护，BLOCKED |

## 历史 GitHub Issues

首批 Issues 已在后续实现与架构调整后关闭；本节只保留任务来源追溯，不再作为当前执行入口：

- [#1 M1-001 Bootstrap Python package and CI](https://github.com/Chengyue-Lu/research-agent-workbench/issues/1)
- [#2 M1-002 Implement the minimal research object schemas](https://github.com/Chengyue-Lu/research-agent-workbench/issues/2)
- [#3 M1-003 Implement protocol, mode, agent, and skill manifests](https://github.com/Chengyue-Lu/research-agent-workbench/issues/3)
- [#4 M1-004 Implement task, handoff, main state, and reference integrity](https://github.com/Chengyue-Lu/research-agent-workbench/issues/4)
- [#5 M1-005 Build the minimal CLI and deterministic risk checks](https://github.com/Chengyue-Lu/research-agent-workbench/issues/5)
- [#6 M1-008 Freeze provider-neutral model API port](https://github.com/Chengyue-Lu/research-agent-workbench/issues/6)
- [#7 M2-008 Audit and admit external Skill candidates](https://github.com/Chengyue-Lu/research-agent-workbench/issues/7)（来源驱动扩张已被 Need-first 路线取代）

## 当前施工读取规则

本文不再在 Task 表之外维护一份“当前下一任务”清单。合法施工入口始终由上方
canonical `READY` 行直接给出；资源排序由具名 owner 决定，branch/PR 必须引用 exact
Task。`BLOCKED` 行只能由其显式 hard/external condition 解除，`PARKED` 行则需要独立的恢复决定。

M10-001 → M10-002 → M3-009 → M10-003 的 bounded machine chain 与 M11-001 → M11-002 →
M11-003 → M11-004 的 Core chain 均已按各自 Task 验收完成。前者不等于 Phase C Human/R2
semantic closeout，后者不等于 live Provider 或 ordinary-user E2E。M11-005 → M11-006 的可选 Skill supply
publication/mapping 也已按独立 Task identity 完成；它不阻塞零 Skill Core、不建立第二条 Runtime consumer
path，也不等于任何真实 Skill 已获准入、证明研究增量或获得 Runtime new-binding 资格。

M14 已由 Issue #57 与 ADR-0021 完成 family activation/task-definition；`M14-001` 已建立 dormant
release trust anchor，严格候选即使 prerequisites 成立也仍由 topology Gate 阻断。M14-002/003 不因前置已完成而
自动进入队列，M14-004/005 也不得绕过 public surface、
package、许可证、scaffold 或 GitHub remote protection Gate。M14-001～004 都不产生 release merge eligibility；
M14-005 readiness/cutover 前继续以现行治理为准，不手工创建 release tree。

Issue #41 新增或规范化的 M4、M5、M10、M11 dependency chains 保持逐 Task implementation /
acceptance identity；PR 组织统一遵守 `DEVELOPMENT.md` 的 module-level DAG 规则。Governance v2 的
`PARKED → DONE` R2 exception 只保留给
已经被 task-definition 明确证明为不可独立验收的同一 Stage，不能从“风险同为 R2”自行推导适用。

M6-003 只保留历史 compatibility identity，当前 Core 主链由已完成的 M11-001～004 承担；M6-004 只等待独立 live
授权，可与 M11 Core 分开验证。M3-001～007 不再用 `IN_PROGRESS` 表示未排期债务。M6-006 行中的 “Part C 等待
M8-003” 是不可改写的 DONE 历史快照，不再定义当前恢复 Gate。M7-005/006/014 的真实比较继续
PARKED，直到相应 Trace/Evaluation Manifest 与真实需求稳定。

## Topic 4 / Topic 5 解冻 Gate

Topic 4 thin-layer Architecture Hold 的 architecture prerequisites 已由 M9-001/M9-005 与 ADR-0019 满足；
M11-001～004 已在 bounded zero-Skill/direct-Tool fixtures 中实现 Runtime Bundle 明确读取面、View producer
的 external pin/freshness/exact Provider/Adapter/Model/Runtime/Host 与最严 policy 交集、Host 对
exact Bundle-bound View 的消费与 actual facts，以及 generic Trace/Receipt 闭合。该实现仍不代表
live Provider readiness、ordinary-user E2E 或科学正确性。automatic fallback、model auto-routing、multi-Agent orchestration、critic
voting、hidden routing，以及 Runtime 修改 Method/Claim/Gate 仍被禁止。

Topic 5 的 minimal Research State、Failure/Attempt、Method Trace 和 bounded machine Gate prerequisites 已经完成；
Human semantic review、R2/Phase C closeout 仍独立 pending，因此 Topic 5 继续冻结。即使该 closeout 未来被接受，
也只允许 Topic 5 重新进入**独立架构设计审查**；Handoff、context rollover、safe pause、recovery、
salvage/clean recovery 或 continuation 实现仍必须另有 task-definition 与 R2 acceptance。`M10-001 →
M10-002 → M3-009 → M10-003` 是上述 activation Gate 的 machine prerequisite chain，不属于 Topic 5，
也不因完成而自动获得 Topic 5 implementation authority。Topic 5 membership 只授予会改变 Handoff、context rollover、safe pause、recovery、
salvage/clean recovery 或 continuation semantics 的 Task；仅消费 Trace/Receipt 或报告 execution facts
不构成 membership。因此 M11-003/004 属于 Topic 4/Artifact-Trace integration，明确不属于 Topic 5，
也不获得其恢复/编排 authority；M9-005 Snapshot Core 同样不解除 Topic 5。
