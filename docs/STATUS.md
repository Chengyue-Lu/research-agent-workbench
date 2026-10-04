# 实现状态

状态：Current implementation authority
更新：2026-10-03

本页只回答“仓库现在实现到哪里”。实时任务状态由 [`TASKS.md`](TASKS.md) 维护，依赖方向由 [`ROADMAP.md`](ROADMAP.md) 维护。

## 成熟度

RWB 处于**内部技术 alpha**：核心文件契约、解析和确定性验证可供开发与集成试验使用；尚不构成面向普通研究者的完整产品，也不对科研结果作质量保证。

Phase A / M8 Core Formalization 已完成契约收口。Phase B / M9-001～006 的需求、供给、生命周期、
Protocol、两级 Snapshot 与 migration/replacement 结构契约已经实现。这里的“完成”不表示真实 Provider、
production runtime-execution binding、Human Decision、科学有效性或端到端研究运行已经证明。

M4-001～004 已全部 accepted / merged：Source Admission、Artifact Promotion、Claim evidence localization
与 bounded Run reconstruction 构成已实现的 provenance 链。M5-006 Protocol 与资格校验器已实现，
M11-007 Skill closeout 与 Gate B 已按 PR81 实现及具名证据接受收口；M6-008 baseline envelope/closeout 已由 PR75 接受并收口。M5-007 H1–H5 bounded synthetic Harness 已完成，整项验收与证据映射见[收口记录](workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-007_COMPLETION.md)；后继 M5-008 live pilot 仍受 M6-010、真实 A4 admission 和专项授权阻断。
M4 的 bounded 验收不替代真实 Case Dossier、live Provider/session conformance 或正式系统评价。

Issue #57 / ADR-0021 的 M14-001～005 已完成首个 curated release：M14-001～004 提供受信
source、deterministic projection、portable package 与公开文档；M1-009 scaffold 和 M0-007 MIT 已接受。
#118 接受 active curated topology 与 source-owned live PR governance；完整远端 cutover 已执行并回读，
真实 direct `develop -> main` PR 的两个 required jobs 在 checkout 前失败，未以 skipped check 放行。

首发冻结 `develop@1ac70be6095f0c7aac5cf4de1cd30ca4ca959b60`、policy `1.5.0` 与旧 main parent
`b1d5a5a5850e0e7541e4c460f15384cd45357ab2`。PR #116 的 exact candidate `8300834` 获黄毅最终
R2 APPROVED 后，于 2026-10-01 正常 merge 为 `main@b5a99637e9c140df004dcd0cd07a4b6bbfcd4195`；
实际 main tree 与经审核的 298-file projection/manifest 闭包一致。annotated `v0.1.0` 已作为 GitHub
alpha prerelease 发布；wheel、sdist、release manifest、provenance 与 SHA256SUMS 五个附件下载后
逐项 hash/size 一致。actual-main direct wheel 与 sdist-derived wheel 的逻辑内容/Runtime resources 相同；
Python 3.11.16/3.13.15 各四种 checkout 外安装探针通过，离线 scaffold 重建匹配。
exact identities、source/hosted CI、review/merge/publish 决定和附件哈希见[首发完成记录](workstreams/chengyue-lu/M14-CURATED-RELEASE/FIRST_RELEASE_COMPLETE.md)。

首发仍是内部技术 alpha：安装、结构校验和固定离线示例的 bounded 重建不证明真实 Provider 可用性、
Skill admission、正式研究评价或科学有效性。产品修复继续进入 develop，再独立冻结下一次 curated
release；当前 release branch 不回并 develop，原 tag/附件保持不变。

通用 API 接入的 M6-009 离线合同已完成：闭集配置、十一家真实厂商身份、四协议映射、晚解析凭据、
版本化源码绑定、显式两轮 Session 政策和脱敏报告均有离线验证；条款与接受来源见
[整项收口](workstreams/chengyue-lu/M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-009_COMPLETION.md)。
默认禁用模板和官方矩阵中的未核实条件不产生厂商 live 资格。M6-010 独立验收 DeepSeek Flash；
2026-10-03 的前三组失败和 1205 tokens 保留，原 Tool/text 通过、Schema 发送前停止的记录见
[部件进度](workstreams/chengyue-lu/M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-010_FLASH_COMPONENT_PROGRESS.md)。
随后按用户总计十次授权，向同一账本追加单次扩限，
token 上限仍 10,000,000。新安装与 Windows 合成链通过后，第四组真实 Flash 的 Tool、结果文本、
Schema 三步部件断言全部通过，父进程正常退出、报告 1.2 冷读校验通过。
累计四组 durable Attempt、七份成功响应，input1540/output204=1744 tokens、held0。
证据见 [FOLLOWUP-023](workstreams/chengyue-lu/M6-GENERAL-PROVIDER-IMPLEMENTATION/attempts/FOLLOWUP-023/CHECKS.md)。
PR131 已合入 develop `ede2bc1d`。M6-010 本候选按用户直接收口指令接受 source66 / installed002 /
native005 的 exact Flash Provider/session 部件证据，提出 DONE；条款映射、公开脱敏报告、
独立只读复核和当前源码 delta 见[整项受限收口](workstreams/chengyue-lu/M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-010_COMPLETION.md)。
历史报告的 `live_qualified=false` 与当时接受字段保持原样，外部完成判断不改写报告；M5 消费新的
source/config 时仍须复核同一 binding 的适用性，A4 admission 和四臂 Pilot 仍有独立 Gate。
原 M6-004 OpenAI 验收仍 BLOCKED；保存本地 Key 和晚间时间安排不证明 Provider 或 Pilot 已可用。

## 已实现

| 能力 | 当前覆盖 |
|---|---|
| 项目 scaffold | no-Skill / offline-demo / minimal 模板、项目与 Runtime root 分离、exact resource pin、Task/Profile 校验及 0.x 兼容政策；离线示例调用已有 Run 检查/重建，不执行模型或授予研究结论 |
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
| System-level Protocol（M5-006） | 独立版本的 Protocol、A2/A3 qualification、admission overlap、A4 pre-run overlay 与 A3/A4 pairwise validator 已实现；exact pins、缺失测量与三态解释可重算，当前 Method 差异保留为 package effect；不产生执行、Human admission 或科研判断（[契约](implementation/SYSTEM_EVALUATION_PROTOCOL.md)） |
| 确定性验证 | Schema、引用、哈希、权限交集、Handoff lock、Claim 支持关系 |
| Source admission（M4-001） | `sources/raw` admission sidecar 固定来源 locator、时间、操作者、许可/数据边界、解析器与 exact byte hash；已提取引用若落入 `sources/inbox` 完整路径段则阻断（[契约](implementation/SOURCE_ADMISSION_CONTRACT.md)） |
| Artifact promotion（M4-002） | accepted validation policy 固定 runner/checker；validation run 三元组仅记录 claimed provenance metadata，eligibility 由 promotion 时重执行 pinned pipeline 并复现 PASS report/transcript 当场确立；错误 PASS 阻断，byte-exact 自报历史不产生历史 producer/operator/time 权威；entries/live bytes exact closure 与 file-bound record 以 staging + commit-time revalidation + exclusive-create 同批发布 object/run/candidate bytes 与 durable Promotion Receipt，保留全部 work 与负结果 disposition（[契约](implementation/ARTIFACT_PROMOTION_CONTRACT.md)） |
| Bounded Run reconstruction（M4-004，accepted / merged） | Run revision、输入/环境/输出 ObjectRef 与实际 FileRef 逐项闭合；锁定单文件程序、输入、参数和 exact Python 环境，在无原 Agent 会话的新进程重建合成整数仿真并保留负结果/差异/失败；只读检查不重跑 checker，结果不授予历史真实性、科学正确性或 Claim 权限（[契约与验收](workstreams/huangyi/M4-RUN-RECONSTRUCTION/README.md)） |
| Claim evidence localization（M4-003） | `claim trace --evidence-map` 将 exact Evidence 身份连接到 captured artifact bytes 与 admission/Promotion Receipt；支持、反证、限制同次定位，保留 retain-in-work 负结果；复用每次调用内已读字节，不重执行 checker（[契约](implementation/CLAIM_TRACE_CONTRACT.md)） |
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
| Source admission（M4-001） | 不抓取网页/API，不判断来源真实性、许可法律效力、内容安全或科学质量；它本身不实现后续 promotion、Claim trace 或 Run reproduction |
| Artifact promotion（M4-002） | policy/execution/report/receipt 记录一次声称的校验运行（provenance metadata）与 exact byte copy 的可审计事实；eligibility 只由 promotion 时的确定性重执行等价当场确立；不接受 Claim、不记录 Human Decision、不直达 accepted/publication、不证明科学正确性；Claim trace 与 Run reconstruction 分别由已完成的 M4-003/004 承担 |
| Claim evidence localization（M4-003） | 只验证声明关系和文件位置；limitation 定位于 Claim 文本，不虚构独立来源；不判定 locator 科学含义、不接受 Claim、不证明历史运行或科学正确性 |
| Skill 价值 | 现有 Registry 条目不构成已证明的普适研究增益；新任务可优先 no-Skill / direct-tool |
| Skill new-binding | 生产 projection index 仍为空；M11-005/006 只证明可选 publication/mapping contract，未重新准入任何 legacy Skill，也未证明真实 trial、Provider 可用性或科研净增量 |
| Phase D evaluation entry | [ADR-0020](decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md) 已接受 A1/A2→M6、A3/A4→M11 的双传输；M5-006 Protocol 与 qualification/overlap/overlay/pairwise 校验器已实现。M11-007 [Skill closeout 1.0.0](implementation/SKILL_EXECUTION_CLOSEOUT.md) 已由 PR81 合入，[Gate B](workstreams/chengyue-lu/M11-SKILL-CLOSEOUT-GATE/GATE.md) 绑定 exact implementation/replay/CI 和具名接受，状态 SATISFIED。M6-008 baseline envelope/replay closeout 已由 PR75 接受，Task 按[收口证据](workstreams/huangyi/M6-BASELINE-EXECUTION/CLOSEOUT.md) 为 DONE；M5-007 bounded synthetic Harness DONE，[H1/H2](implementation/SYSTEM_EVALUATION_HARNESS.md) 已由 PR86 接受，提供确定性非执行 plan 与独立 preflight；H3 四臂 synthetic execution/cold replay 与整臂 dispatch deadline 修复已由 PR89 接受并合入；[H4](workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-007_H4_PACKET.md) H4a actual evidence 已由 PR90 接受并合入；H4b synthetic 盲审/具名冻结/受控揭盲已由 PR96 使用单次维护者审核例外合入，actual develop push CI SUCCESS；[H4c measurement/analysis](workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-007_H4C_PACKET.md) 关联/方法/观察记录及独立配对输入已由 PR104 具名 R2 接受并合入 develop@26eca5742ba08d504d273423471fd7aab876a6d5（原始[验证](workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/attempts/M5-007-H4C-001/README.md)）；[H5 持久化证明](workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-007_H5_PACKET.md) 的 PR106 已获黄毅 exact-head R2 接受并正常合入 develop@81a058b228a5da2a6f46192a954f62efc72895e3；H1–H5 整项收口见[验收与 Issue #55 条款](workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-007_COMPLETION.md)，原 454 文件证明与当前源码 111/111 测试分别保留身份；synthetic 13 指标全 unavailable/null、primary eligibility=false；真实 M5-004 execution 仍受原 live/case/admission Gate 约束，并新增 [M5-008 Live Pilot Gate](workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-008_LIVE_PILOT_GATE.md) 作为正式评价前的工程验收任务；M5-008 BLOCKED，当前没有该任务的 live 验证或 confirmatory net-benefit evidence |
| 发布 | M14-001～005 DONE；#116 经最终 R2 审核正常 merge，`v0.1.0` GitHub alpha prerelease 的五个附件下载 hash/size 核验通过。八个 actual-main 双 Python 安装探针通过；source/main/tag/manifest/provenance 闭包见[完成记录](workstreams/chengyue-lu/M14-CURATED-RELEASE/FIRST_RELEASE_COMPLETE.md)。后续发行保留独立 R2/CI/维护者决定 |
| 产品体验 | scaffold 支持离线项目入口；可视化、协作 UI 和运维流程仍待完善 |

## 支持边界

- 推荐路径：离线校验、no-Skill Task 契约验证、Mode Action/Method Resolution 引用、现有 Trace / Archive 验证、Adapter 开发。
- 兼容路径：旧 Skill-bound 工件可显式读取或回放，但不作为新任务默认模板。
- 实验路径：真实模型、外部工具和 MCP 接入需要具名授权、独立凭据管理和相应 Trace。

开始使用见[上手指南](GETTING_STARTED.md)，旧对象边界见[兼容性说明](compatibility/README.md)，当前工作项见[任务清单](TASKS.md)。
