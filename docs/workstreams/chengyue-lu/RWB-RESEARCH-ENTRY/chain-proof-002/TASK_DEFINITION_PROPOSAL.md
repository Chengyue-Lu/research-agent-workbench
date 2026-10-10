# CHAIN-DEF-002：最小Task定义候选

Profile：task-definition evidence scout；required-Skills=[]。来源为本轮 [TASK_PACKET](TASK_PACKET.md)、canonical [TASKS](../../../../TASKS.md)、[ROADMAP](../../../../ROADMAP.md)、[DEVELOPMENT](../../../../DEVELOPMENT.md)、[施工导航](../../../../M_SERIES_IMPLEMENTATION_MAP.md)、PR140候选 [COMPLETION](../COMPLETION.md)。本文件只提案，不修改canonical，不宣称新Task已定义、READY接受或DONE。

## 建议采用三个有界切片

核到PR140 worktree HEAD `d630f8e174846f4932d05a7a0d69076930b53ee1`，base develop `d3c4d23206339ebc7f18b5621f3aa5453f96335e`。PR140仍Draft/current candidate；其65新入口/53原消费者回归与installed证据沿用原范围，本组没有重跑。canonical M1最高009、M2最高008、M11最高007；三个候选ID在TASKS/ROADMAP/施工导航均无命中，当前空闲。

| 候选ID | 名称 | 具名owner / 风险 / 导航 | hard dependencies（当前canonical行全DONE） | docs-only建议状态 |
|---|---|---|---|---|
| M1-010 | 通用研究入口的受控需求与材料接入、契约产物桥接 | 路诚钺；R2；Foundation / Research Control + Contracts | M1-003, M1-004, M1-005, M1-007, M8-003, M8-005 | READY候选 |
| M2-009 | 角色必载指令与有界0..N主子运行消费 | 路诚钺；R2；Foundation / Agent Runtime + Research Control；黄毅review实际Session接点 | M2-002, M1-004, M2-005, M3-008, M6-002 | READY候选 |
| M11-008 | 普通研究入口的冻结执行、closeout与全链桥接Gate | 黄毅；R2；F / Topic4 + Artifact/Trace；路诚钺review控制/权限/Trace语义 | M9-005, M6-002, M11-004 | READY候选 |

这里的READY候选表示依赖条件允许提案，不是共享状态已迁移。三个Task不互相挂新ID为hard dependency；它们以现有已接受接口独立进入，对同一应用接口的集成用显式producer/consumer pins与桥矩阵关联。最终M11-008 Gate必须实际消费相应输入产物及主子结果，不因无新ID硬依赖而免除接合证据。避免将自然语言intake、role职责和runtime执行三种ownership塞进一个无限execution umbrella，也不拆为多层串行锁链。

### 可直接转录的canonical新增行（仅提案）

保留现有M1/M2五列表头及旧DONE行；新增行如下，owner/risk同时进入下方owner-index。详细验收即本文件对应slice，Root复制到docs-only分支时转换为该分支的portable workstream引用。

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M1-010 | READY | 通用研究入口的受控需求与材料接入、契约产物桥接 | M1-003, M1-004, M1-005, M1-007, M8-003, M8-005 | 有界人类问题/声明材料经真实intake请求及独立人类ceilings产生Schema/ref-valid Protocol/Task/Method/Requirement；实际producer返回pins被冻结执行下游消费；无效/unknown/Human待决/越权/hash漂移阻断，保留可读输入输出与失败；不批准Claim/Method科学适当性、准入或真实研究案例 |
| M2-009 | READY | 角色必载指令与有界0..N主子运行消费 | M2-002, M1-004, M2-005, M3-008, M6-002 | 角色baseline/Profile/Task/获准输入实际进入fresh请求；main实际提出0..N child，整波边界检查、实际child结果进入main消费；Task/Run预算跨会话累计并保留failed/unknown；required Skill未加载阻断；Guide独立只读无自动main回传；不固定编制、不产生Skill admission、全局scheduler或Topic5恢复 |

M11沿现有九列表头追加：

| ID | 状态 | 任务 | 责任人 | 风险 | Phase / Topic | 依赖 | 验收 |
|---|---|---|---|---|---|---|---|
| M11-008 | READY | 普通研究入口的冻结执行、closeout与全链桥接Gate | 黄毅 | R2 | F / Topic4 + Artifact/Trace | M9-005, M6-002, M11-004 | 实际控制producer与main/child Task经唯一冻结→Bundle/View→Host/Session实际Provider/Tool或eligible Skill consumption→Trace/Artifact/validation/receipt/replay→main结果消费/人工checkpoint/Guide，逐bridge保存exact输入输出/hash与失败；Core no-Skill/direct-tool按实际支持验收，Skill仅在现有资格闭合时启用，未通分支明确BLOCKED；不重选/fallback、不复制selected自证actual、不授予Task/Claim/Human/admission/Release/Topic5权威，不替代M5四臂评价 |

owner-index新增候选行：

| exact Task | 具名owner | 风险 | Phase | Topic/边界 | 候选定位 |
|---|---|---|---|---|---|
| M1-010 | 路诚钺 | R2 | Foundation | Research Control + Contracts | READY仅候选分支；人类ceilings与真实控制产物消费；代码候选PR140不等于接受 |
| M2-009 | 路诚钺；黄毅review实际Session接点 | R2 | Foundation | Agent Runtime + Research Control | READY仅候选分支；必载prompt/有界动态委派/独立Guide，非Skill准入或Topic5 |
| M11-008 | 黄毅；路诚钺review控制/权限/Trace | R2 | F | Topic4 + Artifact/Trace | READY仅候选分支；逐bridge Gate与冷复验，非M5净价值/科学结论或恢复接受 |

## M1-010 的scope与验收候选

**Scope**：复用现有Protocol、Task、Profile、Mode/Action/Method Resolution和Requirement契约，把人类问题、范围、声明材料、独立权限/预算ceilings及必要已有状态refs，装入真实intake请求；消费实际模型结构化输出，验证/保存受控草稿及exact refs，让下游真正消费这些producer返回pins。新建与人工已有材料接入共用契约，缺MainState可显式从问题/材料重新准备，不自动恢复旧会话。

**最小验收**：

1. 有界人工材料的自然语言输入形成独立角色请求，实际baseline、声明输入快照及模型输出都可定位；输出必须经现有Schema/引用/权限检查，不把漂亮summary当可执行Task。
2. Protocol/Task/Method/Requirement输出来自本次producer，其实际返回refs被Capability冻结及Bundle/View真实消费者读取。不得用另一份手写控制fixture替代模型/producer输出却称上游桥通过。
3. 无效JSON、缺字段、未知Mode/Action或缺Method依据、权限/预算扩大、未授权材料、stale/hash变化、需要Human Gate但未决等保留原结果并阻断后续执行；未知保持unknown，不猜测出合格Method或accepted source。
4. 若例启用材料来源接入，按既有Source admission/provenance接口保存hash/来源，未admitted inbox不能成为Evidence引用。Source/Evidence/Claim/Method Trace分支只在显式场景中启用并检查其直接消费者；不强迫每个Task创建所有对象。
5. 交付可读输入→控制产物→下游消费表、正向和关键失败证据、读写范围、可复用caller/CLI及明确限制；结构通过不证明科学方法适当或模型需求改写质量。

**Negative / stop**：不更改Core对象身份/Schema语义、Mode/Action/Registry版本或Human authority；不把模型proposal当Human Decision，不引入新的研究DAG。需改变这些边界时另提ADR/task-definition候选并停越界切片。intake质量评估、真实研究案例和杂乱材料科学筛选不是本Task验收。

现有候选接点（仅接口metadata与已有COMPLETION）：`entry/intake.py:101 compile_control_draft/:215 persist_control_draft`，`entry/roles.py:155 build_role_request`。当前草稿producer已候选实现；模型实际自然语言intake与完整caller尚需桥接证据，不重写旧DONE Task。

## M2-009 的scope与验收候选

**Scope**：将角色最低职责、Profile、exact Task/input refs、可选方法Skill与显式模型/预算绑定成真实请求；main实际提出0..N child Tasks，caller在现有权限/深度/并发/预算上限内检查与执行，child独立输出进入新的main消费请求。职责可合并，不设固定编制；先有完整role baseline，再按Task/Method需要选Skill，optional Skill不能带走必须职责。

**最小验收**：

1. 每个启用role的真实请求载入baseline/Profile/Task/输入快照，可核具体prompt与hash；no-Skill合法运行，required Skill未加载必须阻断。角色别名不产生Skill admission或新coreRole对象。
2. main控制输出实际决定至少0-child与多个child场景；child数/Task目标来自模型输出或受测决策，测试场景数字不写成平台固定规则。不用Root固定N或固定子结果替代动态producer→consumer链。
3. child Task/Profile/input/scopes/permissions/capabilities/depth及required outputs均经parent ceiling检查；整个wave先核，越权、重复Task/输出冲突、不完整控制输出在child dispatch前阻断。
4. children使用fresh隔离请求，不继承main全聊天/日志；实际结果及必要有权限工件refs进入main的consume-child-results请求。主次消费、失败/取消/unstarted siblings和最终提出处置均留证，不能以“已delegate”当child完成。
5. intake/main/children同一授权Run的实际调用、known usage、failed/unknown reservations及wall time统一累计；Task跨fresh Session的turn/output/time不重置，失败发送按attempted request算，不以received response计数代替。不自动付费重试/fallback；合作取消与已发生超额检测分开说明。
6. 独立Guide只读approved MainState/必要refs；不加载main聊天、原logs或默认全仓，不写科研Trace/Handoff/state、不自动回传main。人类明确采纳才形成main的新输入。Guide自身实际API费用仍按其明确授权范围记录，不能借只读身份免除账或重置整体上限。

**Negative / stop**：不恢复PARKED的M2-006原生launch umbrella，不固定四类Agent编制，不产生全局Supervisor/bus/continuity database。Role/native adapter只能实现同一可选port；真实平台launch/collect/cancel或OS隔离必须独立列适用证据，不能由prompt声称权限已enforced。改变Handoff/context/recovery语义的部分停至Topic5前置接受。

候选接口metadata：`roles.py:155`，`workflow.py:85 RoleExecutor/:207 run_research_workflow`，`executor.py:33 FrozenRoleExecutor`，`guide.py:20 build_guide_request/:54 ask_guide`。COMPLETION已有0/1/3离线caller证明，但真实Provider整链例仍main/0child；多独立会话子树不能继承该证据。

## M11-008 的scope与验收候选

**Scope**：应用级绑定factory消费实际control producers与角色Tasks，经既有Capability唯一选择/冻结、Runtime Bundle、Resolved View、Thin Host、Session与actual facts，闭合Trace/Artifact/validation/generic receipt/cold replay，再由caller消费结果、单提交者发布人工checkpoint与人类待办。把每个生产接口接点可达性和输入输出消费测清楚，保持各核心authority不变。

**最小验收**：

1. 每个main/child接收到自身exact frozen Task/Profile/View，错误Task或binding/source/hash/freshness漂移零dispatch；actual五组件与实际Supply由独立config/source/runtime观察佐证，不复制selected值自证actual。
2. Core no-Skill路径在无Skill/无Evolution/无Assignment下真实闭合；有界direct Tool路径启用时实际调用对应生产port，定义/输入/实现hash/权限/side-effect/工具结果/usage被记录和下游消费，不能只伪填Tool次数或输出。当前候选Driver零Tool是已知缺口，需实现接点或把该路径明确BLOCKED，不能报告该路径通过。
3. Skill-bearing路径仅在现有M11-006/007和exact eligible Projection/Supply/Method/授权输入闭合时启用；实际Skill正文/必需输入在use boundary消费并留hash事实，Skill receipt独立replay。未准入的测试候选Skill只作为隔离资产，缺qualification则保留阻断；没有资格不能借fixture accepted标签生产化。Core Gate不被 optional Skill资格拖成前置，但“全路径通过”只能列实际通过的路径。
4. 同一recorder保存实际请求/响应/Tool/usage/failed/unknown→Host→closeout。preflight-blocked、post-call-failed、driver exception/capture gap分别测；缺完整事实不得出完整receipt，unknown输出不是完整零，Task/Claim/Human完成保持false。
5. checkpoint消费实际hash-pinned workflow及closeout工件，保留已有决定/限制并拒篡改/覆盖/权限扩大；随后Guide只读该已发布快照。只证明人工提交与再次输入，不能声称自动恢复或current-head CAS。
6. 对启用的每个bridge保存actual producer/consumer路径、refs/hash、事实/失败/停止、可读结果；在独立文件复验中重载输入/closeout，冷复验零模型调用。单模块PASS、summary或进程无异常退出不足以“整链已通”。

**negative / stop**：不重选Supply/rebind/fallback，不改M5 Harness/四臂shared contract/private oracle，不做Skill净价值/科研质量/准入/Release/Claim决定。真实任务、case/provenance/Human评分不进入本轮；真实API测试只由Root按当前source/config/grant/time/history/累计上限重新核准，M6-010旧exact部件接受不是新caller整链资格。资格或预算不能闭合时保存BLOCKED/unstarted/ref及已发生费用未知，不重置计数。

候选接口metadata：`binding.py:145 freeze_capability_selection/:301 freeze_execution_inputs`，`driver.py:126 SessionExecutionDriver/:286 execute_role_slice`，`executor.py:33`，`state.py:32 publish_workflow_checkpoint`。这些是PR140候选接点，不作为已merge依赖或正式Task DONE。

## 提交、计划与状态表述

Root先在独立docs-only `task-definition` 分支追加exact三Task及本细化，不改任何旧DONE定义/验收。TASKS拥有状态/依赖/验收；ROADMAP只说明Foundation/Topic4应用接合不等于PhaseD净价值或Topic5解冻；施工导航由TASKS派生；STATUS/公共支持只描述已接受能力，未合并PR140及本定义候选用候选索引表达。stable surfaces不写本轮测试日记。旧M6-010 owner导航残留BLOCKED与canonical行DONE有历史冲突，不能当新Task阻塞来源；本建议不用它作Core harddep，live适用另审exact source。

docs-only PR不能同时置DONE。正式READY/IN_PROGRESS依赖必须在相应head snapshot全DONE；feature接受对应实施Task后才能按机器/owner证据推进。此建议不将PR140 Draft提前视为merged，也不把反向对齐Task定义等同原候选正式接受。

**本轮人类已明确授权先定义/更新文档，形成计划后直接开始隔离桥接测试。** 因此Root可在提交docs-only候选并保存确切测试plan后，继续已授权的PR140隔离准备/诊断/测试；这不替代定义merge、R2具名review或formal DONE门禁。本组没有执行这些测试，也不申请新增付费范围。

建议plan只设三工作包：A控制输入产物、B角色/动态消费、C冻结执行及逐bridge Gate。运行场景先列人工材料和0..N、权限/漂移/unknown/缺资格反例，再分no-Skill、direct Tool、eligible Skill及Guide。每行status固定为planned/implemented/tested/blocked/not-applicable之一并解释证据；不要给“系统整体百分比”。Source/Evidence/Claim/Method Trace/Human Gate/Need只有被Task显式启用时测其生产和直接消费；不可用“暂不启用”掩盖承诺必走的bridge。

## 与既有任务身份的分界

- M5-008保持原四臂live工程验收与获批Pilot/真实A4/Human评价Gate；本三Task不需要四臂对照、不估计net benefit、不产出科研质量结论，也不替代M5-004/005。真实任务采用另获批dossier，不能由人工测试材料直接转成正式案例。
- M12/Topic5仍RESERVED/frozen；Phase C machine Tasks DONE不是Human/R2 closeout。人工旧state refs→新的受控Task输入、immutable checkpoint及只读Guide复用既有契约；不会启动被冻结的自动continuation/recovery。
- M2-003/004 legacy broad Skills及M2-008外部发现/准入PARKED不被角色prompt或测试资产恢复。M11-006/007已有机制可条件复用；新的Skill admission仍需原Need/Evaluation/Human/Release链。
- M6-004 OpenAI BLOCKED范围保留；M6-009十一厂商离线合同不是全部live。M6-010 exact Flash历史部件接受不自动覆盖本轮新source/完整Run/各路径。

## 六项正文source pins

| 源文件（本worktree读时） | SHA256 |
|---|---|
| docs/TASKS.md | 6a75ec90b3e88d06b894eed6b30322ddbd2770a60a093f7349b7f1244bde7e54 |
| docs/ROADMAP.md | fef83bb1456a4e59ba43a8a2f1493081bd6e6dac19f3de285032cb0f4a30ecd9 |
| docs/DEVELOPMENT.md | a8155269c627b6476467f1f019e8373a356925a53a59965637c5c44a86601d8a |
| docs/M_SERIES_IMPLEMENTATION_MAP.md | 128f58fb9586346a6f0a161d8a61aac1adb3b742efb5be6d56ac8e8a983d4f31 |
| RWB-RESEARCH-ENTRY/COMPLETION.md | 1fd5bb92aba17a7a0447d2fa98cf1c322b5758071945606458303c01c7a2d3ae |
| chain-proof-002/TASK_PACKET.md | 4b46cde3dbb25a5691d1c41d5f87aaab953bec2cf8bbfc18c9435ae92c2d9b95 |

本组读域、可见指派/建议消息及交付检查见 [DEFINITION_COMMUNICATIONS](DEFINITION_COMMUNICATIONS.md)。Root写canonical/PR/primary continuity并执行整链；本组仅提案交付后停止。
