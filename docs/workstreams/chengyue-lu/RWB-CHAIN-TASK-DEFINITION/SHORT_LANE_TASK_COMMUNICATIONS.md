# AUDIT-RWB-DOCS-005：短链路 Task 通信

2026-10-08；Profile=`bounded documentation worker`；required-Skills=`[]`。本文是公开路径规范化记录，**不是 byte-exact 原件**。下列 Packet 的 `DOCSWT同PR141` 映射为 `DOCSWT=.`，其他正文保留；包含实际机器路径的原件保存在 ignored `.rwb/docs005-communications/task.md`，不加入 Git。没有读取或记录密钥、账户账本、隐藏推理或其他窗口消息。

## Root → Agent：完整 Task Packet（路径规范化）

执行 docs-only Task Packet AUDIT-RWB-DOCS-005/短链路 exact Tasks。Profile=bounded documentation worker, required-Skills=[]，预算15分钟/2轮。DOCSWT=.（同 PR141 checkout，公开相对路径映射），你不独自在仓库，其余人写架构/ADR/计划/合同审查，保留他人编辑。允许读AGENTS/docsREADME/Development/TASKS/REALIZATION_PLAN、最新用户指令（统一对话入口路由Guide、独立短程局部修改、完整研究；写后判MainState影响，main旁路隔离，不直接改child），及继承上一轮报告。只写 docs/TASKS.md + workstream SHORT_LANE_TASK_HANDOFF/COMMUNICATIONS，完整原通信存ignored .rwb/docs005-communications/task.md，公开路径相对映射明确非byteexact。不得实现/tests/API/Tool/Key/账/Git/configSchemaRegistry/primarymemory。
固定新增5项、无人员分工列：
M1-014 READY deps M1-004,M8-005：研究Protocol之前的请求分流producer，读取最小用户输入/项目授权/当前Task metadata，产出路由理由+scope/目标/输入允许集；Guide/short-edit/research/current-main-steering（已有目标明确才投递）与混合/歧义澄清。仅研究路由进入Protocol规划；普通Guide与短程不默认通知main，不直接路由任意child。路由建议不是权限/供给selector/状态接受，当前main的history不得给所有请求。
M3-013 PARKED deps M3-012,M11-009：短程actualdiff的后置影响评估与状态采纳接点。评估semantic none/relevant/unknown，且核currentMainState版本/refs与activeTask输入是否失效，不能模型说无关即通过。none且refs有效/无活动输入冲突→局部change record不改/不通知main；relevant/unknown或refs损坏→状态提案/相关发布hold，由人类采纳+受控statewriter新revision，不暗改Claim/权限。prewrite权限与write-conflict检查不能后置。相关进行中main/child输入真实失效须最小通知，不用‘隔离’隐瞒；非自动session/context/recovery Topic5不解冻。
M2-014 PARKED deps M1-014,M2-010,M6-012,M3-013：与Guide同级的独立短程编辑职责。最小有界Task与noSkill/directTool控制/输入pins/预算/write scope，caller隔离Model/API/上下文；不为每次段落排序生成/修订研究Protocol或造Mode。真实局部修改+检查+后置评估，当前main/child写锁/冻结输入冲突先停写；实际产物/失败/usage/副作用留证，无全局状态/发布/权限 authority，无任意child会话操控入口。
M1-015 PARKED deps M1-014,M1-013,M2-013,M2-014：统一对话入口与隔离caller投递，单UI可native/web等Adapter不锁platform；按route批准对象/recipient/预算供给绑定创建隔离会话，共享显示不拼全聊天，不给Guide/short主任务原history，不自动主反馈；current-main-steering只能明确Task经其治理接点，children仍main控制；route/message/实际API/产物可核，同累计usage/unknown，不放权限/不Host重选，不造全局Supervisor/messagebus/continuity DB。
M11-011 PARKED deps M1-015,M11-010：统一入口长短链隔离Gate；实际验证Guide、段落重排state不变、初看小改却改变Claim的post relevant/unknown+采纳/hold、混合需求、明确main steering、新研究Protocol、活动main/child文件冲突与误投child拒绝；给出actualdiff/MainState beforeafter/recipient/context/notifications真实证据，不能bare callback代替。现有main任务保持，旁路不默认污染；不自动state回收恢复、不科学准入。
同时调整未DONE定义：M1-011 加dep M1-014并明确仅research请求生成/修订Protocol，其余独立局部契约；M2-010角色baseline包括入口分流、短程编辑和后置影响评估职责，角色按需不固定新coreRole。M1-013installed入口说明完整research与旁路消费由M1-015接合，不把单CLI当一个聊天全路由已通。M2-013Guide仅readonly、mutation建议转route不直接写，用户建议仅明确采纳才main输入。M3-012引用短程影响提案的采纳桥在M3-013，不增加反向dep。原72DONE逐字不变，原3bridge READY保持。新增5=1READY4PARKED；上一19+5=24，6READY18PARKED（加原3=27候选）。全部新风险R2；Phase/Topic应用入口/Context/Runtime现有families索引，M12未激活。
输出持久化实际读域、每项定义/依赖/未知，保存可见往返原文。任何dependency环/新核心schema需要仅报告，勿自动加未授权IDs。Root负责唯一文档/治理checks与Git。

## 可见输出原文

### Agent commentary 1

我会先读取当前任务定义和REALIZATION_PLAN，再加入5个短链路Task并调整指定的未完成项。只修改TASKS及本轮交付、通信文件；最终检查和Git操作由Root负责。

### Agent → Root

已读取当前TASKS与REALIZATION_PLAN。固定5项和指定5个未DONE定义调整形成单向链：M1-014→research/short/Guide接点→M1-015→M11-011，人工对照未见反向依赖环。将保留原72 DONE行及原3 bridge READY；新增风险索引均R2，M3-013明确prewrite冲突与active输入失效通知、postwrite采纳，不借隔离隐瞒。未运行检查，Root最终核。

### Agent commentary 2

这5项把请求分流、独立短程编辑、写后影响评估和统一投递拆成可分别验收的Task。定义会明确：写前先核权限和冲突；写后若当前MainState或活动输入失效，必须hold相关发布并最小通知，不能用上下文隔离掩盖影响。

## 可观察工作与边界

- 读取本 checkout 的 `AGENTS.md`、`docs/README.md`、`docs/DEVELOPMENT.md`、`docs/TASKS.md` 和 `docs/workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/REALIZATION_PLAN.md`。文件名发现仅定位指定计划与 owned 输出；TASKS 长输出有截断，随后窄读目标与依赖段。上一轮 Compact 是继承信息，本轮不重新打开旧交付或 primary memory。
- 最新用户要求由上述 Root Packet 传入；本 Agent 未读取其他窗口中的人类原通信。没有把转述当作独立原件。
- `apply_patch` 只新增固定 5 行，调整指定 5 个未 DONE 定义，以及对应总数/风险 Phase 索引。没有写原 72 DONE 行、原 3 bridge READY 行或其他代理文件。
- 本轮只写 `docs/TASKS.md`、同目录 `SHORT_LANE_TASK_HANDOFF.md`、`SHORT_LANE_TASK_COMMUNICATIONS.md` 及获准 ignored 原通信。实际输出已落盘；最终 SHA-256 在聊天交付，后续 Root 修改需重冻。
- 未运行文档/治理 checks、产品 imports/functions/tests、API、Tool、Key、账、Git、安装、配置、Schema、Registry 或 memory 操作。文件读取和最终文件 hash 是证据定位，不构成 validator PASS。
- 依赖只人工对照，未发现本轮引入的反向环或必须新建核心 Schema；正式 DAG/链接/表格/DONE 逐字保真与治理复核由 Root 完成。没有自动增加未授权 ID、实现或接受权限。

## Compact

固定 5 项为 1 READY / 4 PARKED；连同上一轮 19 项为 24 项（6 READY / 18 PARKED），加原 3 bridge 为 27 候选。全部 5 项 R2，M12/Topic 5 不激活。具体定义、依赖、调整和未知见 [短链路交付](SHORT_LANE_TASK_HANDOFF.md)；live 状态唯一来源仍是 [TASKS](../../../TASKS.md)。本轮持久化后停止。

## 用户校正追加：可见往返原文

2026-10-08；本追加仍为 docs-only，只继续修改 TASKS、原 Handoff 和本通信文件。以下 Root 消息无机器绝对路径，正文原样保存；初次 ignored 通信原件不改写。前述初次交付 hash 是历史快照，追加后由最终聊天返回新 hash。

### Agent → Root：初次交付原文（历史 hash）

已落盘并停止。新增5项为1 READY、4 PARKED；累计24项新定义、加原3 bridge共27候选。指定5个未DONE定义已调整，原72 DONE行和3 bridge READY行未编辑。未运行检查；最终依赖、链接及逐字保真由Root复核。

SHA256：

- `docs/TASKS.md`：`B2AF01B7B7881FF2296A992C6DAA1BB4C6233146684CF382E2D14A64DA14B692`
- `SHORT_LANE_TASK_HANDOFF.md`：`EA1AA71177BF21810848F461298423DB74E42A06275F05A38221267938679D49`
- `SHORT_LANE_TASK_COMMUNICATIONS.md`：`5FE9B06C0873D51026D6D339C45C3B2E44DCB2439386F1FD25BE5D0F2D641237`
- ignored `.rwb/docs005-communications/task.md`：`F1BABBCB3D90DCB60C69800D8EE20341D99646B0CB3FDF59083334D2023450C8`

Compact包含定义、依赖、实际读写域与未知；完整可见通信已保存，公开记录明确相对路径映射。

### Root → Agent：本追加 Task 原文

补充用户新校正，请在原授权 docs/TASKS.md 及 SHORT_LANE_TASK_HANDOFF/COMMUNICATIONS 原文件继续小修，不新增范围，不动其他人。Profile bounded docs worker, required Skills=[], inputs最新用户+原TaskPacket+ADR024/SHORT_LANE_DESIGN(只为对齐可读), budget10分钟1轮,stop完成/真正缺口；不运行测试/API/工具/Key/账本/代码/Git。具体新定义M1-014、M2-014、M3-013与M2-010要明确：前置层+Guide/Short分支扩展不重构既有研究主链；意图/路由/语义影响具体判断由经过版本绑定评审的角色Skill或Prompt承载，架构/Runtime保留契约权限预算和确定性结构/引用检查，不硬编码逐案语义。Skill与prompt绑定路线可选，不强制每次Skill Supply，角色可合并、不固定API数。M1-014验收包含路由profile/prompt或Skill版本/判断理由与不确定澄清。M3-013语义判断与确定性diff/hash/ref检验区分。全部5新增状态依赖不变，72 DONE不动，保留他人编辑，你不单独开发。更新原通信与handoff声明本追加。

### Agent commentary 3

我会把这次校正写入指定定义：由版本绑定、经过评审的Prompt或Skill承载语义判断，架构和Runtime负责契约、权限、预算及确定性检查。5项新增Task的状态、依赖保持不变，并在原handoff和通信文件中记录本次追加。

### Agent commentary 4

4个指定定义已补入语义判断的承载位置，并区分Prompt/Skill判断与diff、hash、ref等确定性检查。新增Task的状态和依赖未改；接下来只补录本次通信并返回文件hash，正式检查仍由Root完成。

### 本追加实际读写与未知

只读重新定位后的 `docs/decisions/0024-UNIFIED-ENTRY-AND-SHORT-TASK-ROUTING.md`、本 workstream `SHORT_LANE_DESIGN.md`，以及当前 TASKS 目标段和原 Handoff/通信。ADR/设计仍是 Proposed/PR141 候选；文件名发现不扩展其他材料。最新人类校正由可见 Root 消息传入，本 Agent 未读取另一窗口原通信。

实际小修 M1-014、M2-010、M2-014、M3-013 的验收描述及原交付快照，全部 5 新 Task 状态/依赖和 72 DONE 行未编辑；M1-015/M11-011 行及其他代理编辑保持。前置层/Guide/Short 是研究主链外扩展；角色 Prompt/Skill 的版本绑定评审承载具体语义，Runtime 保留契约/权限/预算和确定性结构引用检查。Prompt 或 Skill 绑定路线可选，选 Skill 仍守适用资格，不固定角色/API 数，不强制每次 Skill Supply。

角色 Prompt/Skill 实际版本、装配和判断质量仍待实施验收；没有生成 Skill、修改代码/Schema/Registry 或引入核心新对象。未运行测试/API/生产 Tool/Key/账/代码/Git/文档治理 checks；只做文档读取、编辑和交付文件 hash。Root 负责正式复核。追加 Compact 已写回 [原 Handoff](SHORT_LANE_TASK_HANDOFF.md)，持久化后停止。
