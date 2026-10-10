# 实现状态

状态：Current implementation authority。文档校准：2026-10-10；继承已审实现范围的基线为 develop `d3c4d23206339ebc7f18b5621f3aa5453f96335e`。
本轮协调者提供的 primary develop 来源元信息为 `11c3b57dfbf8af0dc2587fc421d097e2544941c3`；它不表示本轮重新完整审查或重测了该来源的所有新增实现，也不扩大旧接受范围。

本页维护工程成熟度、实现覆盖、候选和缺口。exact Task 的定义、状态、risk、依赖与验收以 [TASKS](TASKS.md) 为准，方向与 Gate 见 [ROADMAP](ROADMAP.md)；公开入口的使用契约与证据等级见 [SUPPORTED_FEATURES](SUPPORTED_FEATURES.md)。历史收口记录绑定当时身份，不作为新的运行、权限或接受事件。

## 成熟度与来源身份

RWB 处于**内部技术 alpha**：核心文件契约、解析、确定性校验与有界集成可用于开发试验；普通研究任务的完整入口、真实 Skill 资格和科研净收益尚不能据此认定。

| 来源 | 已有事实 | 本页采用的边界与来源 |
| --- | --- | --- |
| 接受的 develop 实现 | 文件 Core、方法/能力控制、受限 Runtime、provenance 与 synthetic Harness 已有实现 | 分类见下表；Task DONE 不超出原验收含义 |
| 已发布 `v0.1.0` | curated alpha、wheel/sdist、Runtime resources 与 checkout 外 Python 3.11/3.13 安装及 offline-demo 重建证据 | [首发完成记录](workstreams/chengyue-lu/M14-CURATED-RELEASE/FIRST_RELEASE_COMPLETE.md)固定 source/main/tag/附件身份；其后 develop 修复不自动成为该包内容 |
| 独立代码候选 PR140 | 研究入口、角色请求、主子结果消费与 checkpoint 等分支实现；本轮安装包内 caller/factory 的 Action/no-Skill 合成路径完成实际 API、只读 Tool 与冷回放 | [PR140](https://github.com/Chengyue-Lu/research-agent-workbench/pull/140) 未合并，不计入本页 develop 支持；候选输入输出、exact producer→consumer 与 planning/Handoff 缺口见 [package-caller-003](workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/package-caller-003/README.md)。M1-010/M2-009/M11-008 保持 IN_PROGRESS；选定通路证据不证明通用真实工程、Skill 资格或科研效果 |
| 已合并的通用桥接定义 | 需求/材料接入、动态主子运行与冻结执行分别定义验收 | [定义与验证边界](workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/README.md)；M1-010/M2-009/M11-008 的状态由 TASKS 维护，定义接受不代表实现完成 |
| 已合并的真实环境接合定义 PR141 | 27 项桥接与真实化 Task 已进入 develop；实现、质量与整链验收分别按各项定义推进 | [PR141](https://github.com/Chengyue-Lu/research-agent-workbench/pull/141) 于北京时间 2026-10-08 03:03 合并为 `e49386140c18cdfb9e6065b7c59e2545f863e386`；[下一阶段唯一计划](workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/REALIZATION_PLAN.md)与 [TASKS](TASKS.md)维护实施顺序和状态，不把文档合并计为实现通过 |

## 本分支的应用接合候选

`codex/research-entry-integration` 增加可选 research entry 应用层：角色最低指令和获准快照、受人类 ceilings 限制的控制草稿、显式供给冻结与 Bundle/View 接合、procedure/no-Skill/零 Tool 的 Session Driver、main 动态0..N及跨请求预算、固定报告的 checkpoint 发布、独立只读 Guide。实际支持和测试范围见[完成矩阵](workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/COMPLETION.md)，参数和接点见[使用说明](workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/USAGE.md)。这是待 PR 审查的隔离实现，不表示已合并、live 资格、整 Task/科研接受、M12 解冻或新的发行。

M12 与前端独立窗口已交付[连续性规划](workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/m12/PLAN.md)和[前端规划](workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/frontend/PLAN.md)。它们是后续候选与接合约束，未实施恢复或图形 UI，canonical Task 状态不变。

## 已实现

以下证据分类使用公开等级的含义，记录的是相应接口或固定范围的事实，不为整套系统合成一个 PASS。

| 类别 | 实现覆盖与证据 | 精确入口与限制 |
| --- | --- | --- |
| 项目与随包资源 | structural / bounded：no-Skill、offline-demo、minimal scaffold，项目/Runtime/integration roots 分离，exact resource pin 与 Task/Profile 检查 | [scaffold](implementation/PROJECT_SCAFFOLD.md)、[Runtime resources](implementation/RUNTIME_RESOURCES.md)；模板只生成文件，离线示例需显式重建，不是人类意图规划器 |
| 文件 Core 与验证 | structural：Task、Assignment、Handoff、Evidence、Claim、Decision、Protocol、Receipt；Schema、identity、refs、hash、权限交集、Handoff lock 与 Claim 支持关系 | [Schema catalog](../schemas/v0.1.0/)、[实现索引](implementation/README.md)；结构有效不判断科学正确性 |
| Mode / Action / Method | structural / bounded：版本化 Registry、诊断 case 到 Task/Method、Gate/Artifact/stop/block 继承；显式 v0.1→v0.2 迁移保持旧 pin replay | [Mode Action](implementation/MODE_ACTION_CONTRACT.md)、[Method](implementation/METHOD_RESOLUTION_CONTRACT.md)、[迁移](implementation/RESEARCH_MODE_MIGRATION.md)；方法决定不绑定 Supply，诊断 producer 不等于通用人类需求入口 |
| Authority 与 Protocol Profile | structural：asserted facts 下的 actor/rule eligibility，方法义务与证据/Gate expectation | [Authority](implementation/DECISION_AUTHORITY.md)、[Protocol Profile](implementation/PROTOCOL_PROFILE_CONTRACT.md)；不证明事实、不授权限或记录 Human approval，不建立固定研究 DAG |
| Requirement / Supply / Resolution / Snapshot | structural / bounded：不可变需求身份，typed 供给比较、唯一选择、两级 Snapshot 与 migration/replacement 边界 | [Requirement](implementation/CAPABILITY_REQUIREMENT_CONTRACT.md)、[Resolution](implementation/CAPABILITY_RESOLUTION_CONTRACT.md)、[Phase B Gate](implementation/PHASE_B_EVOLUTION_GATE.md)；Snapshot 冻结供给事实，不生成最终权限、Provider binding 或 Authority eligibility |
| Runtime Bundle / View / Thin Host | bounded：exact Task→Method→Requirement→selected Supply→Resolution→Snapshot 闭包，最严边界交集、trusted clock 与调用前重载，no-Skill/direct-tool 本地正反路径 | [Bundle](implementation/RUNTIME_BUNDLE_PROFILE.md)、[View](implementation/RESOLVED_EXECUTION_VIEW.md)、[Host](implementation/THIN_EXECUTION_HOST.md)；未满足完整需求不能冒充 Task completion；无 retry/fallback/reselection 或 Topic 5 recovery |
| Execution Trace 与 closeout | structural / bounded：文件权威 events/index，actual facts 与 planned facts 分离，completed/post-call-failed/preflight-blocked replay；Skill extension 固定 actual Projection/Supply/binding | [Trace Core](implementation/TRACE_CORE.md)、[generic closeout](implementation/GENERIC_EXECUTION_CLOSEOUT.md)、[Skill closeout](implementation/SKILL_EXECUTION_CLOSEOUT.md)；completed 仅 Action/Capability slice，task_completion=false，不接受 Claim/Human Gate |
| 可选 Skill 生命周期与映射 | structural / bounded：Need/lifecycle 分离，new-binding eligibility、immutable ReleaseProjection 与统一 Supply→View 路径，真实 Evaluation/Human Decision 引用检查 | [Need](implementation/SKILL_NEED_CONTRACT.md)、[lifecycle](implementation/SKILL_LIFECYCLE_V2.md)、[Projection](implementation/SKILL_RELEASE_PROJECTION.md)；生产 Projection index 为空，未重新准入 legacy Skill，Resolver 仍是唯一 selector |
| MainState 与文件连续性 | structural / bounded：checkpoint、resume-check、受控 Handoff 与归档，使用精确输入与文件权威记录 | [上下文实现](../src/research_workbench/context/)、[兼容边界](compatibility/README.md)；可读取状态不表示自动恢复会话或研究接受 |
| Source / Artifact / Claim / Run | structural / bounded：source admission exact bytes，promotion 当场重执行 pinned policy、exclusive publication 与 Receipt，支持/反证/限制定位，固定程序/输入/环境重建 | [Source](implementation/SOURCE_ADMISSION_CONTRACT.md)、[Promotion](implementation/ARTIFACT_PROMOTION_CONTRACT.md)、[Claim trace](implementation/CLAIM_TRACE_CONTRACT.md)、[Run 验收](workstreams/huangyi/M4-RUN-RECONSTRUCTION/README.md)；provenance metadata 不证明历史 producer/time、来源质量或科学结果，负结果保留 |
| Provider / Session 离线接缝 | structural / bounded：十一家身份、四协议映射、闭集配置、晚解析凭据、固定 Session/Tool 政策、版本化源码绑定与脱敏报告 | [M6-009 离线收口](workstreams/chengyue-lu/M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-009_COMPLETION.md)；默认禁用配置与 unresolved 能力不产生 live 资格，历史安装证据仅适用于其源身份 |
| 选定 Provider/session 部件 | live，exact limited binding：Windows Python 3.11.16 / DeepSeek Flash 的 Tool、text、Schema 与 Session 部件及失败记录已受限接受 | [M6-010 收口](workstreams/chengyue-lu/M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-010_COMPLETION.md)固定 source66/installed002/native005；原报告 live_qualified=false 与 warnings 保持，外部完成决定不改历史字段；新用途/配置/source 要重核适用性，不覆盖 OpenAI 或 M11/M5 全链 |
| Evaluation 计划与 synthetic Harness | structural / bounded：四臂 Manifest、双传输 Protocol、qualification/overlap/pairwise/overlay 验证，以及 H1–H5 plan、执行事实、盲审/揭盲、measurement/analysis 与 cold replay | [Manifest](implementation/EVALUATION_MANIFEST_CONTRACT.md)、[Protocol](implementation/SYSTEM_EVALUATION_PROTOCOL.md)、[Harness](implementation/SYSTEM_EVALUATION_HARNESS.md)、[整项证据](workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-007_COMPLETION.md)；synthetic 指标 unavailable/null、primary eligibility=false，不产生 live 或科研净收益 |

## 受限或尚不可用

| 类别 | 当前边界与未决项 | 依据 |
| --- | --- | --- |
| Research State / Attempt / Failure / Method Trace | 有 bounded revisioned composition、ref-only Trace 与两案 fresh-process Gate；最终研究状态表示、语义接受与 Phase C closeout 保持独立，执行 Snapshot 不能冒充 actual path/state effect | [State](implementation/RESEARCH_STATE_CANDIDATE_CONTRACT.md)、[Attempt/Failure](implementation/RESEARCH_ATTEMPT_FAILURE_CONTRACT.md)、[Method Trace](implementation/METHOD_TRACE_CANDIDATE_CONTRACT.md)、[Phase C](implementation/PHASE_C_BOUNDED_GATE.md)；相关 Task 完成候选工程检查不等于最终表示已接受，也不授权 Topic 5 |
| 普通研究入口与全链桥接 | 尚无面向普通用户的一键 Task-to-research 闭环；新建与人工材料接入需明确 refs/人类 ceilings，缺 MainState 保持 unknown；角色职责不等于已支持的请求 producer | [通用桥接定义候选](workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/README.md)与 [TASKS](TASKS.md)；PR140 不计作 develop 完成或通用 live 通过 |
| 前置分流与独立短程分支 | PR141 仅定义主研究链外的入口层、Guide 同级局部编辑和后置影响提案；具体判断由版本绑定的角色 Skill/提示词承载。现有 intake 仍要求完整研究 ceilings，候选 Tool 接点仅 readonly，尚无统一投递/短程写回/状态影响消费者 | [短链设计](workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/SHORT_LANE_DESIGN.md)、[契约窄审](workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/SHORT_LANE_CONTRACT_REVIEW.md)；既有研究主线保持，定义不证明实现 |
| Runtime 与 Skill 资格 | checked-in structural-replay Snapshot 不能执行；runtime-execution 输入由显式集成构造；Skill publication/mapping 的 synthetic 闭包不产生真实 Skill admission 或新绑定权限 | [Bundle 契约](implementation/RUNTIME_BUNDLE_PROFILE.md)、[Projection 契约](implementation/SKILL_RELEASE_PROJECTION.md)；无 checked-in 通用 Runtime View/Receipt 或生产 Skill 保证 |
| Live pilot 与正式评价 | 选定 Provider 部件 DONE 不等于四臂 pilot 已走通；真实 A4 admission、pilot 专项授权、case/Human/正式评价 Gate 分别保留，尚无 evaluated 科研效果或成本净收益结论 | [现行 Live Pilot Gate](workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-008_LIVE_PILOT_GATE.md)；当前前置按 M6-010 解释，旧收口文档的 M6-004 blocker 是历史观察，不改写原件 |
| 科学与发布决定 | validator 不判断方法适用、许可法律效力、证据质量、来源科学性或 Claim 正确性；工具执行/重建不提供 OS sandbox；下一次发行仍有独立审查与 Human 决定 | [公开边界](SUPPORTED_FEATURES.md)、[发布合并规范](DEVELOP_TO_MAIN_RELEASE.md)；不从既有 alpha 发布、绿色检查或 Task DONE 推出新授权 |
| 兼容与产品体验 | legacy Task/Skill-bound Assignment/Receipt 仅按显式兼容 seam 解析或回放；旧 task resolve 的 no-Skill Assignment 缺口不阻碍统一 Runtime Core；可视化、协作 UI 和运维尚未形成完整用户产品 | [兼容性说明](compatibility/README.md)；新任务优先合法 no-Skill/direct-tool，不复制历史 Skill 绑定 |

## 真实环境差距与下一阶段

候选链路证明有界接口可接合，真实长任务仍需工程环境与 Tool 版本事实、actual 决策提交、逐候选供给发现、
可配置能力/预算和权限执行，以及自然意图、人工材料、职责/prompt、不同 child 方法与 qualified Skill 的实际消费者。
大材料/大 Tool 结果的外置回查、partial artifacts 与定向修复、人工新 Task 读取短 MainState、研究对象实际消费及 Task 目标质量
分别取证；同步调用的协作式取消、未知用量和失败留存不能被通路成功掩盖。

具体改造、证据与停止条件只在 [REALIZATION_PLAN](workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/REALIZATION_PLAN.md)
和 TASKS 维护，导航不复制另一套状态/依赖/验收。M5 的四臂 pilot/净价值评价、Mode 候选与 Skill 准入、M12/Topic 5
保持独立 Gate；人工短状态输入不意味着自动恢复，action-only Receipt 不意味着 Task 目标完成。

## 使用与接续

离线用户从[上手指南](GETTING_STARTED.md)开始；集成者依据 exact 输入与[实现协议](implementation/README.md)接线。所有新调用、工件提升、Human Gate 与接受决定保留各自权威和证据。实时推进只更新 TASKS、相应 workstream 与本页成熟度摘要，稳定入口不复制 M Task 的实施日志。
