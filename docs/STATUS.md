# 实现状态

状态：Current implementation authority
更新：2026-09-02

本页只回答“仓库现在实现到哪里”。实时任务状态由 [`TASKS.md`](TASKS.md) 维护，依赖方向由 [`ROADMAP.md`](ROADMAP.md) 维护。

## 成熟度

RWB 处于**内部技术 alpha**：核心文件契约、解析和确定性验证可供开发与集成试验使用；尚不构成面向普通研究者的完整产品，也不对科研结果作质量保证。

Phase A / M8 Core Formalization 已完成契约收口。Phase B / M9-001～006 的需求、供给、生命周期、
Protocol、两级 Snapshot 与 migration/replacement 结构契约已经实现。这里的“完成”不表示真实 Provider、
production runtime-execution binding、Human Decision、科学有效性或端到端研究运行已经证明。

## 已实现

| 能力 | 当前覆盖 |
|---|---|
| 版本化对象 | Task、Assignment、Handoff、Evidence、Claim、Decision、Protocol、Receipt 等 Schema 与示例 |
| Method-aware control | 两个正式 Mode 的 16 个逻辑 Action、跨 v0.1/v0.2 的 32 个版本化 Action 文档、hash-pinned Registry，以及八组 `diagnostic case → bounded TaskPacket → Method Resolution`；Resolution 继承 Action Gate/Artifact/stop/block 且不绑定供应实现 |
| Mode compatibility | v0.1/v0.2 Mode 并存，显式 v0.1→v0.2 迁移器与两个 exact-pin migration record；Registry 追加同 Action 新版本不改变旧 migration replay |
| Authority Rule Eligibility | v1 Matrix 与九个 hash-pinned eligibility record 只判断“假设 asserted facts 成立时 actor 是否匹配 operation rule”；不证明事实、不记录 Human approval、不授予 Permission、不提升 Claim、不执行决定 |
| Capability Requirement | 四个被八组 Method Resolution 复用的需求 ID 已成为不可变、hash-indexed 的需求侧契约；Task↔Method↔Requirement 引用可闭合，且契约拒绝 Provider/Model/Adapter、供给状态与 fallback |
| Skill Need / lifecycle v2 | 三个版本化 Need 只声明 gap、baseline、expected increment 与证据要求；lifecycle 分离 intake/evaluation/Human admission/runtime eligibility；`eligible_for_new_binding()` 要求 new-binding scope、trial/evaluation/promotion/Human refs，真正新绑定还须外部 evidence 与 decision resolver |
| Protocol Profile | 两个有界 PRISMA/V&V profile 只增加 method obligation 与 Gate/evidence expectation，不复制 Mode、不绑定 Skill/Tool/Provider，也不建立全局研究 DAG |
| Capability supply / Snapshot | typed Report→Resolution→Snapshot 拒绝自报 evidence status、artifact/identity/version/capability/result 漂移和 routing/fallback；structural Snapshot 不是执行输入，Snapshot 只冻结 Supply-side permission/data-egress/side-effect facts，不生成最终权限、Provider binding 或 Authority eligibility |
| Phase B Gate | hash-bound Gate 固定 Task/Mode/Action/Method/Requirement、A/B structural Snapshot 与两类 migration；供给替换保持三类 Supply boundary facts，不赋予 Runtime Method authority |
| Research State candidate（M10-001） | bounded revisioned composition：exact ref、duplicate identity、pin verifiability、role/type、stale current 与 supersede lineage fail closed；Unknown/Assumption 保持轻量 item，Human Decision 复用 kernel Decision；最终表示仍待 Human/R2（[契约](implementation/RESEARCH_STATE_CANDIDATE_CONTRACT.md)） |
| Research Attempt / Failure candidate（M10-002） | legacy execution Attempt 保持不变；versioned sidecar 以真实文件 SHA-256 精确绑定 execution Attempt，并分离 State/predecessor/reopen；Research Failure 只冻结 learned result/revisit condition，source/observed/uncertainty 保持可选 bounded profile（[契约](implementation/RESEARCH_ATTEMPT_FAILURE_CONTRACT.md)） |
| Method Trace v0.1 candidate（M3-009） | 独立 ref-only Trace 精确绑定 Attempt/Task/Method Resolution/Mode/Action disposition/State/kernel Decision；无本 Attempt authoritative M11 fact 时记录 per-Attempt gap，captured fact 必须 exact 绑定 applied path 与 State effect，Snapshot 不得冒充 actual execution（[契约](implementation/METHOD_TRACE_CANDIDATE_CONTRACT.md)） |
| Phase C bounded Gate（M10-003） | runner 以 source manifest 精确 pin 并 staging 两案 closure；fresh actor 新进程只读生成 manifest 与 allowlist，结束后 runner 才读取 private oracle；machine PASS 仍保持 Human semantic review、R2 closeout 与 Phase C closeout pending，且不授权 Topic 5（[契约](implementation/PHASE_C_BOUNDED_GATE.md)） |
| 评估对照（M5-003） | Evaluation Manifest 直接以四个 Phase D treatment 为 canonical arms；Task、exact Model、Host、budget、context 与 evidence classes 共享冻结，Tool/no-Skill Snapshot 和 candidate Skill binding fail closed；`rwb eval plan` 编译同一条件 digest 的 non-executing baseline plan（[契约](implementation/EVALUATION_MANIFEST_CONTRACT.md)） |
| 确定性验证 | Schema、引用、哈希、权限交集、Handoff lock、Claim 支持关系 |
| Source admission（M4-001） | `sources/raw` admission sidecar 固定来源 locator、时间、操作者、许可/数据边界、解析器与 exact byte hash；已提取引用若落入 `sources/inbox` 完整路径段则阻断（[契约](implementation/SOURCE_ADMISSION_CONTRACT.md)） |
| Legacy alpha Task 解析 | 旧 `task resolve` 路径仍以 Task + Agent Profile + 显式或 Registry Skill 生成冻结 Assignment、权限交集与版本锁；它是 Skill-bearing compatibility seam，不是 M11 Runtime Core 的统一入口 |
| Legacy Skill 兼容 | accepted Registry 的 active / legacy / deprecated 历史选择边界与精确版本继续可验证；新绑定使用 lifecycle v2 eligibility |
| 文件式连续性 | Main State、checkpoint、resume-check、受控 Handoff 与归档约定 |
| Execution Trace | Envelope、Index、append-only events、工具结果持久化与闭集校验 |
| Legacy execution bridge | 既有 Skill-bound Assignment 到 Trace / Receipt 的适配和恢复检查 |
| Provider seam | provider-neutral 的隔离会话接口、离线 probe 与合成 conformance 基础 |
| Runtime Bundle/Profile | M11-001 显式 manifest 固定 exact Task→Method→Requirement→selected Supply→Resolution→Snapshot closure，并声明 exact Action/Capability slice 与完整 Task demand；多候选 Resolution 只导入最终 selected Supply、要求唯一 eligible，未闭合 capability 不得冒充 Task completion |
| Resolved Execution View | M11-002 supply-neutral producer 固定 exact execution slice 与 Provider/Adapter/Model/Runtime/Host，Profile Tool allowlist 只约束真实 Tool Supply；最严 permission/data-egress/side-effect 交集后还必须证明 selected Supply 仍可运行，否则 fail closed |
| Thin Execution Host | M11-003 exact View consumer 绑定同一 Runtime Bundle，以 Host-owned/injected trusted clock 和调用前重载阻断 backdating 与受控文件 TOCTOU；preflight requested facts 与 post-call actual facts 分离，preventive/detective 语义不混淆；无 retry/fallback/Topic 5 recovery |
| Generic execution closeout | M11-004 对 completed/post-call failed/preflight blocked 作 status-aware replay；Trace 显式 pin execution slice，actual binding/Supply 与 Provider/Tool facts 按生命周期交叉闭合；completed 只声明 Action/Capability-slice completion，永不声明 Task/Claim/Human completion |
| Optional Skill runtime supply | M11-005/006 发布 runtime-minimal、Schema-closed 的 SkillReleaseProjection，并把 eligible Skill 映射回统一 Report→Resolution→Snapshot→View 路径；repository validator 重验真实 Evaluation evidence closure 与 named Human Decision，Capability Resolver 仍是唯一 selector，View/Host 不按 supply kind 分派 |

## 受限或尚不可用

| 范围 | 限制 |
|---|---|
| Method-aware control continuation | M6-003 只保留 legacy Task-to-API compatibility seam；M11-001～004 Core 已实现 bounded no-Skill/direct Tool vertical Gate；Method Trace 现为 ref-only candidate，尚不独立证明 actual path/state effect。当前 checked-in 三条 Snapshot 都是 `structural-replay` 且 `execution_input=false`，M11 vertical fixtures 仅在临时项目中构造 runtime-execution 输入；Mode/lifecycle migration 不迁移历史 Resolution、Assignment、Receipt 或 Trace，Authority Rule Eligibility 也不执行决定 |
| Legacy no-Skill Assignment | Task 契约允许空 `required_skills`，但旧 alpha `task resolve` 尚不能将其解析为冻结 Assignment；该缺口不阻塞 M11-001～004 的 no-Skill/direct-tool Core |
| Runtime Snapshot | 仓库没有 checked-in `runtime-execution` Snapshot/View/Receipt；测试只在临时目录构造 bounded local Core Gate，既有 structural fixture 不得被 Runtime 接受。M11-001～004 证明 exact closure、deterministic View、bounded Thin Host 与 execution-only replay，不形成 permission grant、真实 Provider readiness、scientific Claim 或 Human acceptance |
| End-to-end research run | 尚无面向普通用户的一键 Task-to-research 闭环；Runtime 集成由开发者显式接入 |
| 真实外部模型 | 仓库测试不证明各供应商真实账号、配额、工具调用或长期兼容性 |
| 科学有效性 | Validator 不评判方法适用、证据质量或 Claim 正确性 |
| Phase C candidates（M10-001/002 + M3-009 + M10-003） | 两个 synthetic bounded case 只证明 State/Attempt/Failure/Method Trace 的确定性 closure、fresh-process 受控读取和固定 fixture behavior；Human semantic review、R2/Phase C closeout 仍 pending，最终表示与 Topic 5 实现均未获授权 |
| Source admission（M4-001） | 不抓取网页/API，不判断来源真实性、许可法律效力、内容安全或科学质量；promotion、Claim trace 与 Run reproduction 尚未在本层实现 |
| Skill 价值 | 现有 Registry 条目不构成已证明的普适研究增益；新任务可优先 no-Skill / direct-tool |
| Skill new-binding | 生产 projection index 仍为空；M11-005/006 只证明可选 publication/mapping contract，未重新准入任何 legacy Skill，也未证明真实 trial、Provider 可用性或科研净增量 |
| Phase D evaluation entry | [ADR-0020](decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md) 已选择 A1/A2→M6、A3/A4→M11 的显式双传输并允许 M5-006 Protocol 启动；这不是执行实现。M6-008 treatment-visible baseline envelope/replay closeout 尚未实现，Skill-bearing closeout Gate 仍未满足，M5-007 Harness 与真实 M5-004 execution 继续 BLOCKED |
| 发布 | 仓库缺少最终许可证选择，原创 Skill 许可状态仍阻断正式发布 |
| 产品体验 | 初始化、可视化、协作 UI、安装包和运维流程仍是开发者级别 |

## 支持边界

- 推荐路径：离线校验、no-Skill Task 契约验证、Mode Action/Method Resolution 引用、现有 Trace / Archive 验证、Adapter 开发。
- 兼容路径：旧 Skill-bound 工件可显式读取或回放，但不作为新任务默认模板。
- 实验路径：真实模型、外部工具和 MCP 接入需要具名授权、独立凭据管理和相应 Trace。

开始使用见[上手指南](GETTING_STARTED.md)，旧对象边界见[兼容性说明](compatibility/README.md)，当前工作项见[任务清单](TASKS.md)。
