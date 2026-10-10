# ENTRY-A 可见通信与验证记录

2026-10-07。仅此子Task；此前 Task266/270/273 交付冻结，不被本实现改写。Agent Profile=bounded role/intake/guide implementation worker；required-Skills=[]；30分钟/最多6轮；没有再委派。实现路径属于隔离branch `codex/research-entry-integration`，HEAD初查为base `d3c4d23206339ebc7f18b5621f3aa5453f96335e`。不读primary旧源码。

## Root 指派（全文）

> 开始有界实现子Task ENTRY-A，用户已明确批准隔离分支实现/测试/推送。你不是唯一参与者，不撤销别人编辑。实际cwd .，branch codex/research-entry-integration/base d3c4d23。先读当前AGENTS/README/primary own-row和 docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/{README,TASK_PACKET,RISK_LEDGER}，不要用primary旧源码。Agent Profile=bounded role/intake/guide implementation worker；required-Skills=[]；可读src/protocol、tasks、context、capability Profile/requirements、io/artifacts integrity/resources/schema直接接口、相应Schema/模板/tests，metadata发现后窄读。独占新文件 src/research_workbench/entry/roles.py、intake.py、guide.py，tests/test_entry_roles.py、test_entry_intake.py、test_entry_guide.py，以及workstream/control/COMMUNICATIONS.md、HANDOFF.md；不要改entry/__init__、CLI、其他代理文件/共享状态/原Schema/Registry。目标：1必载baseline覆盖intake/main/child/handoff/Guide职责，不把baseline做成Skill准入；build_role_request(root, *, role, task, profile, model, input_refs=(), tools=(), max_output_tokens=...) ->现有ModelRequest，pin/范围检查明确输入、独立messages；先支持no-Skill，required Skill未实际加载须阻断不能伪称支持。2人类需求内部JSON输出规范；已有Schema验证Protocol/Task及可选Method/Requirement控制草稿，写新目录独占、保留unknown；工具库compile/persist入口，拒绝模型扩大人类给定权限/预算/范围，不把draft自动叫approved或runtime-execution。3Guide独立MainState+获准必要refs，无Tool、无main历史/消息、无项目/Trace/state写入，调用若需只注入现有ProviderRegistry/Session，returns usage，不读Key。输出具体public signatures尽快发Root便Driver接合；Reader pin须从root内exact refs，不递归扫描。预算30分钟最多6轮；可运行你自己的离线测试，命令留存；禁止API/生产Tool/Key/账/原Attempt/安装/再委派/commit/push。临时Python Root稍后给；必要问题只发接口/风险，不扩核心Authority。交付测试/失败/限制、hash与Compact后停止。

## 发出首次 commentary

> 我会先核对隔离分支和入口工作流约束，再明确三个模块的接口，供 Driver 接合。实现先覆盖 no-Skill 路径；未实际加载的 required Skill、权限越界或输入 pin 不符都会阻断，Guide 保持独立只读。

## 发出 Root 接口提案（全文）

> ENTRY-A 接口拟定：roles.build_role_request(root, *, role, task:TaskPacket|Mapping, profile:AgentProfile|Mapping, model, input_refs=(), tools=(), max_output_tokens=1024)->ModelRequest；角色 intake/main/child/handoff/guide 的必载baseline以独立system message载入，默认读取task exact input_refs（显式传入须是其子集），required_skills非空一律阻断当前no-Skill支持。intake.compile_control_draft(root, *, response:str|Mapping, protocol_ceiling:Mapping, task_ceiling:Mapping, schema_catalog=None)->ControlDraft，响应内部JSON {protocol,task,method?,requirements?,unknowns}，ceiling来自人类给定/上游显式配置而非模型；persist_control_draft(root, *, directory, draft)->tuple[FileReference,...]，仅新目录独占，status=draft。guide.build_guide_request(root, *, question, main_state_ref:FileReference, approved_refs=(), model, max_output_tokens=1024, data_policy=None)->ModelRequest；ask_guide(..., providers:ProviderRegistry, provider_name,...)->ModelResponse，单次generate、无Tool/历史/Trace/state写入口，usage随response返回。请Driver按这些签名接合；若需名字/返回结构调整请早反馈。另首读primary regex误返回额外历史M5匹配，已改为仅原row30导航，并在通信归档记录读域偏差；没有继续历史读取。

## Root 对接约束（全文）

> Runtime接口以build_role_request直接返回ModelRequest对接（非wrapper）。Root主任务caller输出规范拟为JSON {decision:complete|delegate|blocked|human-review, delegations:[{task:合法TaskPacket}], summary:string, limitations:[...], next_actions:[...]}，由main真实输出提出是否/N子Task，Root校scope/预算后执行，最后main消费actual子result。请baseline main明确该内部格式并允许request metadata/额外独立输入作结果消费，不改变core Schema；如果你的helper接受额外instructions/info，给Root签名。各phase为fresh Role session，没有继承旧chat。Guide零Tool返回usage即可。新venv准备中。

## 发出 commentary 与 Root 接口补充（全文）

> 接口已对齐现有 ModelRequest。每个角色会使用新组装的独立 messages，main 的 JSON 决策由调用方校验后执行；额外结果上下文会单独传入并记录摘要 hash，不继承旧 chat。控制草稿的校验与保存分开，保存也不会改变批准状态。

> 收到 main JSON 格式，我将加到必载baseline。build_role_request增加 instructions: str|None=None、context: Mapping[str,Any]|None=None、data_policy:DataPolicy|None=None；instructions/context在独立user message中标为caller提供的有界任务数据，绝不改变baseline/权限；context可传actual child results以供fresh main消费，canonical SHA写metadata，无额外磁盘读取。guide禁止这些generic附加上下文，用独立Guide接口。返回仍直接ModelRequest。ControlDraft拟字段protocol/task/method/requirements/unknowns均JSON安全，draft.files()供持久化；persist返回exact FileReference tuple，Method task_ref.sha256由compiler针对即将发布Task bytes计算，不能由模型伪造pin。

说明：提案中的 `draft.files()` 未成为public API，实际最终提供 `ControlDraft.as_mapping()`；Root最终接合按HANDOFF签名。前述模板byte hash不变，由compiler计算。

## Root Python与执行边界（全文）

> 测试Python已可用 ./.rwb/entry-venv/Scripts/python.exe（3.11，独立editable .[test]）；不要reinstall，共享安装由Root负责。按你公开接口做，main context用于actual child results；Rootcallback给instructions=JSON控制格式保证child同样可给complete/delegate/blocked/human-review。输入额外context只承接实际调用产生refs，禁止main旧chat或Guide拿genericcontext。compile_control_draft Method SHA重算非常好；completed不是Human authority。请维持budget不要追完整研究规划器，绑定资格producer另组处理。

## 发出测试进展 commentary（全文）

> 独立 Guide 的 3 项离线测试已通过，覆盖不跟随未获准 refs、不读取旧 main chat，以及注入调用后返回 usage 且不执行意外 ToolCall。控制草稿的 5 项测试也通过。角色测试发现测试 Profile 少了既有 Schema 要求的 `model_policy.class`；我会修正 fixture，并核实各失败用例确实触发预期边界。

## 发出 Root 接合进度（全文）

> ENTRY-A三个产品文件已存在，public签名按前述实现。roles测试7 PASS、intake首轮5 PASS、guide3 PASS（全部离线注入/临时目录）；roles首轮fixture漏model_policy.class导致3error，已修正并重跑7 PASS，归档失败。compile/persist只称schema-validated-control-draft，Method pin来自即将发布Task canonical JSON bytes；明确未做full Mode/Registry/Runtime closure。main instructions/context均实际进入独立user message且snapshot SHA写metadata；Guide独立API不接受genericcontext、不跟随MainState机器refs。Root可开始导入接合，我做末轮边界复核/总测及归档。

## 发出末轮 commentary（全文）

> 最终定向测试共 17 项通过：角色 8、控制草稿 6、Guide 3。新增边界检查覆盖写范围超出 allowed roots、删减人类停止条件、擅改 revision，以及 Requirement 放宽本地数据边界。接下来只整理交付记录和 hash；这些结果是离线接合证据，尚未做 live 调用或完整 Runtime closure 验证。

之后同一收尾轮发现现有 Protocol mode ID/Method versioned Mode ref 的表示差异，补兼容比较与反例并仅重跑intake，7 PASS；最终总数18。没有扩写研究规划器或改核心路由，full Registry closure仍由下游验证。

## 关键读域与实现事件

Round1：当前worktree branch/HEAD/cwd、AGENTS/README、workstream README/TASK_PACKET/RISK_LEDGER；docs README/DEVELOPMENT前65行、ARCHITECTURE责任/验证边界、TASKS有界导航；primary原M5 row30导航。首次primary pattern过宽返回若干历史M5匹配，已通知Root并停止扩展，改为row30导航；没有访问历史私有日志/Key/账/Oracle或以旧源码作依据。初轮输出截断的Packet/RISK随后窄读完整。

Round2：先filename/函数metadata，再窄读现有 ModelRequest/Response/Message/DataPolicy/ToolDefinition/Usage、ProviderRegistry.require与ModelProvider.generate，以及Session构造/run签名（证明可注入接口，未执行session）。Task/FileReference/budget/delegation、MainState parser、AgentProfile、Requirement边界、io同bytes解析、integrity resolve/hash、SchemaCatalog直接接口和相关Schema、已有task/Profile/无Mode Method模板。误找 `contracts.py` 返回missing后按metadata找到contracts/common.py；缺目录examples/tasks的metadata错误未触发任何产品运行。原Schema/Registry仅只读。

Round3：仅创建三个owned产品文件与三个ownedtests；mandatory baseline、exact reader、compile/persist、independent Guide。一次多文件apply_patch因末尾context错误拒绝，未产生部分变更；检查own文件后用正确patch完成。没有触碰entry/__init__、CLI或他人代码。

Round4：三组定向离线测试并行运行；保存首轮fixture失败及两个PASS。Guide注入offline Provider，无网络/真实Tool/Key；unexpected ToolCall只返回未执行。临时目录测试写入的是可丢弃测试数据，不是项目/研究状态。

Round5：修复fixture、补dataclass输入/allowed-models/explicit permissions、immutable baselines、real output schemas、write scope/ceilings/停止条件/revision/egress反例；roles最后8 PASS、intake6 PASS；Guide代码未改，沿用其3 PASS。

Round6：Mode ID/version ref兼容校验与反例、intake最后7 PASS；产品与tests逐文件SHA256、own-path diff/whitespace、文档引用检查、HANDOFF/COMMUNICATIONS冻结回Root。未产生新Attempt/Goal、未安装、未API/生产Tool/Key/账、未commit/push/merge或全局memory写入。

## 命令、结果和失败定位

所有命令workdir为Root指定隔离worktree；解释器为Root准备的 `./.rwb/entry-venv/Scripts/python.exe`，没有自行reinstall。

| 命令 | 结果 |
|---|---|
| `& ./.rwb/entry-venv/Scripts/python.exe -m unittest discover -s tests -p test_entry_roles.py -v` 首轮 | 6 tests，3 ERROR；三处共同原因 `_profile` 校验拒绝fixture，`invalid Profile: 'class' is a required property`。失败用例：actual_request、fresh_requests、intake_receives_schemas；其余3未算成功边界证据。修fixture后继续验证 |
| 同roles命令第二轮 | 7 tests PASS，8.062s；加入真实dataclass输入消费 |
| 同roles命令最终 | 8 tests PASS，8.839s；新增 write scope outside roots |
| `& ./.rwb/entry-venv/Scripts/python.exe -m unittest discover -s tests -p test_entry_intake.py -v` 首轮 | 5 tests PASS，23.609s |
| 同intake命令扩边界 | 6 tests PASS，11.471s |
| 同intake命令最终 | 7 tests PASS，10.813s；包含既有Mode表示兼容/越界拒绝 |
| `& ./.rwb/entry-venv/Scripts/python.exe -m unittest discover -s tests -p test_entry_guide.py -v` | 3 tests PASS，8.352s；随后Guide代码未改 |
| `git diff --check -- <six owned product/test paths>` 与own文件逐行尾空白检查 | diff check exit0；六文件尾空白0。新增untracked文件另以文本检查，不声称git diff覆盖其内容 |

源码和tests最终hash见HANDOFF；本轮不从synthetic/offline tests推导live/scientific/Skill admission。Root负责整个入口集成验证、shared PROJECT_MEMORY与PR。交付后本子Task停止。

## ENTRY-FIX-01 追加：Root有界指派（全文）

> 追加有界 ENTRY-FIX-01：你负责修改 entry/workflow.py、entry/state.py 及 tests/test_entry_workflow.py、tests/test_entry_state.py，仅修复独立审核已确认的两个运行边界，不改其他文件；你并非独自在代码库，保留 Root 和他人编辑。Agent Profile=bounded implementation worker；required Skills=[]。输入为上述文件、现有 Schema、TASK_PACKET、review/RUNTIME_REVIEW.md 若已存在。1 workflow post-call 在 parse_control/complete 前复检本次output cap、node累计output/turns与node真实elapsed，保留actualusage；Task max_output10实际15和max_seconds10实际20均须safe-paused；2 state 必须完整校验WorkflowResult将消费的字段与hash-pinned workflow report一致，防dataclasses.replace(next_actions/limitations/observations...)伪造写入；建议对所有已记录结果字段canonical比对，从固定报告取权威值。加 meaningful 两项反例及正向回归，运行两个限定测试。预算10分钟2轮。输出 HANDOFF_FIX.md + COMM追加可见记录，给结果与hash。不读取Key/API/生产Tool、无安装/commit/push，遇核心contract变更停止报缺口。Root 正修executor+jointtests，避免碰这些文件。

发出首次commentary：

> 我会只修复 workflow 的调用后预算复检和 state 的报告一致性检查，保留实际 usage，并补上超限与结果篡改反例。不会改 executor 或联合测试。

## Root追加既有scope兼容（全文）

> Joint adapter首次3ERROR发生在workflow preflight：原ExecutionViewFixture的Task write_scope=[work/TASK-MR-ES-FROZEN-001]（plain directory anchor），caller _scope_within仅parent.endswith/**当目录，拒绝workflow子目录；现有Runtime/View/Driver接受此Task。请在你负责workflow边界修复时核对原scope语义（validation.relationships._scope_anchor/check_write_scope_overlap等），支持已有portable plain目录anchor（无需core修改），补一个兼容正例，禁止借此接受范围外相似前缀。Root jointfixture暂不篡改冻结Taskscope，等你的修复。

落实：仅追加窄读当前relationships.py的_scope_anchor/check_write_scope_overlap，未读或改Root的joint fixture/executor。按路径组件判定既有plain anchor，未新建权限语义。

## 发出Root接口进度（全文）

> ENTRY-FIX-01 已改 workflow/state：postcall先保留observations+actual usage，检查dispatched output cap、node累计turn/output、node真实elapsed，再parse；state canonical比较WorkflowResult全部已报告字段（report_ref除外，已有bytes pin），构建checkpoint改从已pin report取权威值。追加plain directory scope按现有relationships锚定语义支持plain或/**，使用'/'组件边界，禁止work/task-other冒入work/task；已加workflow实际正例+相似前缀反例，Root可重跑joint。正在仅workflow/state两个定向最终测试。

发出进度commentary：

> 修复已阻断“输出额度 10、实际 15”和“Task 时限 10 秒、实际 20 秒”的完成路径，同时保留实际调用数和 usage。State 会比对 WorkflowResult 的全部已报告字段，并从固定报告构建 checkpoint。也已兼容既有 plain directory scope anchor，路径组件比较会拒绝相似前缀越界。

## 本次范围、事件与验证

Round1：当前TASK_PACKET/允许的RUNTIME_REVIEW、四owned文件metadata后窄读；第一次宽source输出截断后补state完整正文与workflow报告生成/返回片段；只读取review公开审核结论，没读其私有过程。基线与branch复核保持d3c4d23/codex分支。修改预算postcheck/报告canonical一致性并补反例；Root追加scope问题后核既有relationships锚语义，在相同owned文件补兼容。中途发现新增测试块将既有deadline片段移到新测试末尾，立即恢复原测试结构，未删原回归。

Round2：最终state固定report pin并只从report取权威值；两个限定命令、来源hash与HANDOFF_FIX，追加此通信保留原ENTRY-A记录。Root并行executor/jointtests从未被本代理改动。

| 命令 | 结果 |
|---|---|
| `& ./.rwb/entry-venv/Scripts/python.exe -I -m unittest discover -s tests -t . -p test_entry_workflow.py -v` 中间 | 12 PASS，11.346s；scope兼容添加前 |
| 同workflow命令最终 | 13 PASS，15.654s；输出10/actual15、node时限10/actual20、node turns、plain anchor正例/相似前缀反例及原9项回归 |
| `& ./.rwb/entry-venv/Scripts/python.exe -I -m unittest discover -s tests -t . -p test_entry_state.py -v` 最终 | 3 PASS，13.991s；一个新测试内11类dataclasses.replace篡改均在state文件写入前拒绝，原2项回归保留 |
| 四owned code/tests的`git diff --check` | exit0 |

所有反例只用TemporaryDirectory/ScriptedExecutor，actualusage与报告bytes保留；没有失败测试隐藏、产品/API/Tool/Key/账/安装/commit/push或共享memory写入。此次产物hash另回Root；旧ENTRY-A product/test hashes保持，COMM只按Root指令追加，原内容不撤回。交付后停止。
