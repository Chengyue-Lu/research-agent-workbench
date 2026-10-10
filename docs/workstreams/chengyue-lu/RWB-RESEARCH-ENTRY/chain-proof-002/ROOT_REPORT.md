# 全链路桥接测试报告

2026-10-08 · AUDIT-RWB-CHAIN-002 / CHAIN-REPORT-006；增量更新CHAIN-REPORT-009/012/014/018/022/023 · PR140工作树中的开发候选。

**Attempt15已在同一次6个真实HTTP调用中完成本例全部启用接点：intake→main两轮/readonly Tool→child独立会话→fresh main实际消费→checkpoint→Guide COMPLETE，项目文件未被Guide改动。child与fresh main均decision=complete，并保留beta缺locator。** 这是隔离合成案例的接口/消费验证；task_completion=false、human_acceptance=false，Source/正式Skill资格未完成，不能称整系统或科研验收DONE。Guide虽完成调用，其关于Receipt的表述存在局限，见下文。Root最新完整入口一次81 tests / 144.636s / OK；15次closed、41HTTP，累计known246,860/actual held0（含旧55,614）。原13 child blocked、14 main blocked及失败日志保留。最新结果来自Root022及最终A15/冷检补充，历史来自012/014/018，均在[通信](REPORT_COMMUNICATIONS.md)；Root另写[API明细](API_RESULTS.md)，编辑者未读调用原件。

第1～4节保留原离线案例，响应由脚本化offline Provider产生，输入是构造协议、Task、Method、Requirement和本地短材料，供给资格来自离线fixture。第5节列原及最新回归，第6节单独列真实API与冷检；编辑者不读取实际project/生产账。source qualification与Human acceptance仍false，不代表正式接受或已合并状态。

## 1. 一条完整链实际输入了什么、产出了什么

完整正例：`test_model_intake_exact_products_dynamic_child_closeout_checkpoint_and_actual_guide`。

输入为构造的`SYNTHETIC-CONTROL-CALL` Protocol、明确的Task/Profile、人类ceiling及既有Method/Requirement。Protocol允许最多3个并行子任务、深度2；intake预留100 input tokens、output上限128、单轮60秒。这里没有让模型从一句自由自然语言自行发明研究设计：离线intake脚本读取调用方给定ceiling与已知Method/Requirement，回传同范围候选，并明确未知：“No live source qualification in the offline synthetic test.”

| 步骤 / 模块 | 实际操作与输出 | 下一层怎样消费 |
|---|---|---|
| ① 需求接入 / intake | 一次独立Provider端口调用；返回候选Protocol、Task、Method、Requirement和unknowns。compiler校验后独占保存控制草稿，返回实际文件pins；status=success，input30/output8/held0 | 下游使用这些返回pins，不用测试前的旧Task替代产物 |
| ② 能力选择与冻结 | 测试caller为实际Task提供有界Supply及离线资格输入；产生selection、Bundle与View | 首次main和收尾main的View.task_ref均与实际发布的task.json路径/hash相等；fixture不被提升为live证明 |
| ③ main规划→child→main消费 | 三次独立角色请求：main、child、main。首个main脚本输出delegate及1个有界子Task；child返回切片结果；新main收到该child的actual状态、usage、output/receipt引用并产出消费摘要 | workflow据实际结果推进；子工件pins按引用传递，不自动打开正文扩大读集 |
| ④ 执行收尾 | 三个执行切片均取得Receipt refs；workflow=stage-completed。workflow计入之前的intake，model_calls=4、known_tokens=152、held0 | checkpoint writer消费hash-pinned workflow报告和实际Protocol pin；不是仅凭模型“complete”字符串写状态 |
| ⑤ 主状态 / checkpoint | 发布`INTAKE-CONTROL-STATE` checkpoint，保留实际状态和引用 | 独立Guide只消费该批准快照及自己的问题 |
| ⑥ 独立Guide | 人类问题为“Explain the retained state.”；另实际调用一次Provider。role=guide、tools为空、返回ModelResponse，input usage=30；调用前后项目文件字节集合相同 | 回答返回人类；测试未把回答回灌main，也未评价回答正文质量 |

调用账的口径：intake1 + main/child/main3 + Guide1 = **总5次离线端口调用**。workflow报告中的4次包含intake，Guide另算，不能把4次或5次当成同一账字段。测试明确断言Task completion=false、Human acceptance=false。

这比旧COMPLETION中的整链例向前走了两步：旧例Guide只构造请求，主执行没有child；本轮增加真实intake端口产物下游消费、真实main/child/main接合及Guide独立调用。旧报告保留原范围，不被改写成曾经完成本轮结果。

## 2. main是否真的可以决定0、1、3个子任务

`test_main_chooses_zero_one_or_three_children_each_uses_actual_frozen_task_and_receipt`用三种脚本决策驱动同一生产workflow，不把子任务数写成平台固定编制。

| 实际脚本输出的子Task数 | 实际角色调用 | 结果与已知用量 | 已检查的下游消费 |
|---|---|---|---|
| 0 | main1次 | stage-completed；38 tokens；held0 | 自行完成切片，Receipt可独立冷读校验 |
| 1 | main→child→main，共3次 | stage-completed；114 tokens；held0 | 收尾main收到child状态completed、usage=1 model/0 Tool/input30/output8、output.json工件pin和1个Receipt pin |
| 3 | main→3个child→main，共5次 | stage-completed；190 tokens；held0 | 收尾main收到三个实际子结果；每次真实Task分别选择/冻结，每个Receipt独立冷校验 |

main收尾脚本的摘要形式为“Consumed actual receipts for …”，由实际子Task ID拼接。测试同时检查新main的input snapshot hash改变，child工件refs没有偷偷加入其普通inputs允许集。证明的是响应驱动的可变调度和实际结果消费；选择由脚本构造，尚未评价真实模型何时应该委派、如何拆分或研究结果质量。当前child按顺序执行，不宣称并发性能。

## 3. Tool究竟读了什么、模型是否收到结果

正例`test_optional_procedure_and_direct_readonly_tool_feed_model_trace_host_receipt`分别走procedure中的可选Tool和direct Tool供给。

模型端口第一轮返回ToolCall：工具`research-contract-check`，参数只含`path=materials/approved.txt`。可信handler先对照Task exact input refs，复验路径/hash后读取该本地合成短材料。结果中含“bounded synthetic”，保存实际结果引用；第二次模型请求确实含tool消息。

实际输出：模型请求2次、已知76 tokens、Tool调用1次、stage-completed；Host记录tool_invocations=1，Trace保存attempted→succeeded两条Tool事件及实际结果pin，Receipt可独立冷校验。Session显式上限为2轮模型、1次Tool、最多1024字符Tool结果，预占覆盖整个可能的两轮。

这是原离线案例对本地readonly handler、模型→Tool→模型循环及Host/Trace/Receipt接点的验证。付费模型的实际Tool结果消费在Attempt12另见第6节；本节正例不代替它，也不证明任意Python callback真正只读。handler必须按具体Task允许集可信实现。

## 4. 失败和未开始是否保留

| 实际输入/故障 | 实际结果 | 为什么这项必要 |
|---|---|---|
| main要求3个child，第一个child发送失败 | 实际请求2次（main与失败child），known38、held228、safe-paused；其余CHILD-1/CHILD-2未开始；不再请求收尾main，失败child无成功Receipt | 已发生的失败调用不能漏账，未知用量不能归零，停止后不能继续花费 |
| Tool handler抛错，或返回2048字符超过1024上限 | 实际模型请求只有1次、known38/held0，Host failed、safe-paused，保留1次Tool事实；无第二次模型请求 | Root修复了“Tool失败后仍发额外模型请求”的实质缺陷；当前反例验证失败阻断下一请求 |
| 两轮Session需要的总预留放不下 | safe-paused，实际Provider calls=0，summary说明reservation不足 | 在调用前保证整段预算，不能发完再补授权 |
| 缺Tool→组件映射或handler声明external-write | Provider calls=0、handler未执行、safe-paused | 声明与权限不合格应在外部动作前失败 |
| intake返回非法JSON、LENGTH停止或扩张network权限 | 已发生1次调用，input30/output8和response原件保留；无成功draft | 不能把无效模型输出包装成控制面批准 |
| intake发送失败 | 实际calls=1、input/output未知、held228；保存request与失败报告，不重试 | 失败/unknown保留真实消耗风险 |
| intake dispatch guard拒绝或remote policy拒绝 | 未开始/拒绝；actual calls=0、held0 | 人类授权、配置和数据资格必须先成立 |
| intake写域之外的目录 | rejected，无报告写入、无Provider调用、未创建越界目录 | 拒绝行为自身也不能越权写入别人的空间 |

日志中的预期拒绝信息（如目录已存在、draft expands permissions、input hash mismatch）与这些负例同属测试范围；四份Root日志的最终结果均为OK。它们不是被掩盖的成功研究结果。

## 5. Root实际验证记录

| 测试运行 | Root日志结果 | 计数关系 |
|---|---|---|
| 基础入口重跑 | 65 tests，87.799s，OK | 原入口套；后来包含在71项中 |
| 新bridge单跑 | 6 tests，62.573s，OK | 也包含在71项中，不额外重复计数 |
| 全入口当时整套 | 71 tests，146.648s，OK | 基础65+bridge6 |
| 新intake接口套 | 5 tests，24.382s，OK | 另一次独立运行；含上述完整5端口链与4类负例 |

上述历史阶段是71+5=76项分别通过，保留原范围。**Root012当时完整入口套为78 tests PASS，142.707s，是一次整套运行；最新完整81项另列下方。** 两项实测暴露的Profile/permissions问题已有新增回归覆盖；Bundle另13 tests PASS，2.423s。Profile/wire64 tests OK（skip1：Windows symlink）、API budget8 tests OK也获Root确认。各套有重叠，不累计为一个新的unique总数。完整覆盖见[COVERAGE](COVERAGE.md)；报告编辑者没有重跑测试/API/Tool或读取Key/生产账。

CHAIN-REPORT-009的两套耗时记录仍保留：profile+wire64 tests/0.590s/OK/skip1，API budget8 tests/3.659s/OK；012未另提供这两套新耗时。完整78项和Bundle13项的最新结果来自Root的012消息，不把历史分套结果冒充最新单套运行。

Profile/wire改动的消费关系为：真实完整Profile携带required limits→pure wire编码器保留并传递该Profile ceiling→实际wire请求admission拒绝超限。开发交接曾明确指出“只传递limits仍不能拒绝超限”；Root随后补入实际enforcement并跑上述套。旧wire descriptor省略limits的兼容路径保留，未用新默认值扩大权限。此处修复的是请求上限约束，不能由离线回归代替真实整链结果。

Root018补充了后续实际失败与重跑，不能将原70项合跑日志改写成PASS：

| 后续运行 / 模块 | Root实际结果 | 验证范围与限制 |
|---|---|---|
| 70项Trace+bridge合跑 | 前64项Trace通过，含两项新增回归；同时wheel重生成resources使后6项bridge失败 | 整份70项日志保留失败；64项局部通过不等于70项全PASS，也不与旧profile/wire64混为一套 |
| 调整顺序后bridge重跑 | 6 tests，51.668s，PASS | 验证修正顺序后的bridge范围；不是同次70项整套重跑PASS |
| 先前wheel014安装后的site-packages/resource/CLI验证（历史） | 2 tests，3.724s，PASS；pip check PASS | 保留原安装与资源/CLI验证范围，不能代替全部产品回归或真实API全链 |
| 最新wheel020 installed验收（Root023） | 按build→install→installed site-packages RuntimeResources顺序；2项CLI tests，3.739s，OK；pip check：No broken requirements；installed entry help成功 | 验证安装后的资源装载及CLI；负例ERROR尾行均预期，原完整日志保留；不新增API结论或重复累计unique tests |

Root022补充：child baseline说明“禁止再委派不禁止执行自身Task”后，roles+Guide 14 tests / 9.295s / PASS。随后新增actual binding中的待由Driver发布路径/契约元数据及conditional baseline说明，**最终完整入口一次81 tests / 144.636s / OK**，含新Snapshot/child/pending publication断言；预期negative CLI ERROR尾行保留。14项局部回归、旧78项与原70项失败/6项重跑不累加或改写为同一套。A15按该source548/body27566冻结后实际结果另见第6节，不用离线PASS替代真实调用。

## 6. 提示词、Skill和真实API：当前界限

资产worker已交付角色prompt变体和3个可选Skill候选（control-format、bounded-summary、faithful-writing）；全部仍为test-candidate。Root的012消息确认candidate assets未加载；索引或文件存在不证明实际装配到request。当前案例使用内置角色baseline，候选资产不据此获得执行或Skill资格。

现有入口仍对非空required_skills明确阻断；正式Skill加载、身份/版本/package锁、admission、Projection/Supply/View及actual consumption尚不能由本轮候选文本装配代替。Guide候选外部prompt也尚无注入seam，本轮调用的是内置只读Guide。

**真实API当前结果：15同次6HTTP完成所有本例启用桥，child与fresh main complete，checkpoint发布、Guide COMPLETE且只读；Guide内容局限与正式资格另保留。** 13 child blocked、14 main blocked，以及9～12各停点不被改写。最新授权为不限Attempt、累计10,000,000 tokens、单次最多6calls；测试窗口为北京时间18:00至次日09:00，每次请求还须fresh官方闲时。该授权只用于本轮隔离合成测试，不接真实研究项目。角色、child数量、calls与事件数是实际需求/本例输出或预算上限，不是项目固定编制或固定架构；每次不必发送6次。

Root记录的候选边界：canonical `research-contract-check`禁止外传；`entry-api-bridge`使用隔离候选Requirement/供给和public synthetic材料。该候选不替换canonical定义，不自行创造运行资格。014记录Attempt11的真实调用与失败，018记录Attempt12的Tool结果实际消费。下表仅依据Root交付给报告编辑者的实测事实；本窗口未读取真实响应、实际project或生产账，其他未提供的字段不补造，Root明细见[API_RESULTS](API_RESULTS.md)。

| 真实Attempt / 模块 | 实际输出与用量 | 下游消费和停点 | 限制与下一动作 |
|---|---|---|---|
| Attempt1：intake→供给构造 | intake成功；input6473/output915，合计7388 tokens | Root构造Supply时observation_scope使用了错误enum，在main之前停止；main未发送 | Root已修正枚举；不补造后续主子/Tool/Guide结果 |
| Attempt2：intake→能力选择→View | intake成功；input6473/output937，合计7410 tokens；实际capability selection成功 | 候选Method的blocked_conditions为空，Execution View冻结停止；main未发送 | 修复候选方法产物/冻结接点后继续；选择成功不等于View可执行或来源合格 |
| Attempt3～8 | 均已关闭，各自停点原件保留 | 012消息未逐项给出本编辑读域内的全部停点；Root另写[API_RESULTS](API_RESULTS.md)，编辑者未扩大原件读取 | 不把这些Attempt合并成成功路径，也不补造缺失结果 |
| Attempt9：intake→main→child→return main→checkpoint→Guide | 5calls、31秒，delta19,653；workflow含intake为4calls/known16,235/held0 | main自主选择1child；实际child回接后main消费并发布checkpoint；Guide实际返回LENGTH | 主子回接成功，Guide截断；不是一次五调用完整PASS |
| Attempt10：intake→main→checkpoint/Guide | main自主选择0child；3calls、16.11秒，delta11,875；workflow stage-completed | Guide实际COMPLETE，project unchanged=true；Root确认零child完整API闭环通过 | 不把10的Guide拼接到9充当同一Attempt全部通过 |
| Attempt11：intake→main第一轮→readonly Tool→Trace失败 | CLOSED；实际HTTP2（intake+main第一轮），11.016秒，delta10,262；main input2840/output57 | 真实请求entry-api-bridge(path=materials/intent.txt)；readonly handler实际执行1次，Trace写Tool result发生FileNotFoundError；Session trace-capture-gap并安全停止 | 无第二model、child或Guide，无成功Receipt，facts_complete=false；失败原件保留，后续12成功不改写11 |
| Attempt12：intake→main两轮含Tool→child→fresh main | CLOSED；5HTTP，27.313秒，delta20,104；readonly Tool1次，结果进入第二model；三切片Host/Trace/Receipt成功 | main自主选择child1，fresh main实际消费child blocked；workflow最终blocked | 无checkpoint/Guide；切片收据成功不等于Task语义完成或全链PASS |
| Attempt13：intake→main两轮/Tool→child→fresh main→checkpoint→Guide | CLOSED；同次6API，32.063秒，delta23,932；main自选child1；Guide COMPLETE、project unchanged=true | child disposition=blocked；fresh main消费其观测后decision=complete，checkpoint发布，actual route completed | 六调用与消费路径完成；child语义仍blocked，main接纳观测不等于人类接受 |
| Attempt14：intake→main两轮/Tool | CLOSED；3API，15.453秒，delta14,327；Tool1、Receipt成功；main自主0child | main误认为缺文件写Tool便不能报告，并混淆Supply报告引用与Tool名称，返回blocked | 无child/checkpoint/Guide；后续Driver发布说明与81项回归已完成，不能改写14原结果 |
| Attempt15：intake→main两轮/Tool→child→fresh main→checkpoint→Guide | CLOSED；同次6HTTP、32.641秒，delta24,862；全部本例启用桥实际成立 | child及fresh main decision complete；checkpoint发布；Guide COMPLETE、project unchanged=true | workflow含intake5calls/known21,922/held0，task_completion=false、人类接受false；Guide正文质量局限保留 |

022最终汇总：新15次closed Attempts共41个HTTP entries，按角色为intake15、main18（含return/fresh main及Tool前后两轮）、child4、Guide4；累计known246,860/actual held0，含旧55,614。此前14次/35HTTP/221,998、018的12次/26HTTP/183,739、014的11次/21HTTP/163,635、012的10次/19HTTP/153,373与009截至Attempt2的70,412/actual held0均保留为历史快照；Attempt2内部workflow保守held1,101,024与API账确认仅intake1次的口径差异继续保留，不改原件。累计账、单Attempt delta与内部hold不能互相替代。

### Attempt9实际模块与消费

namespace：`chain-cb22901c-ad73-469c-accb-9d6fb876a080`。下列用量、产物与消费者由Root的012实测消息提供；具体请求文本和结果正文不在本次编辑读域，Root另写[API_RESULTS](API_RESULTS.md)。

| 模块 | Root实际结果 | 下游消费与限度 |
|---|---|---|
| intake | input6497/output859 | 控制产物进入本次链；不是旧fixture输出充数 |
| 首次main | input2520/output621，自主选择1child | 形成实际子Task；数量由这次模型控制输出决定 |
| child | `CHAIN-API-CHILD-CHECK`，input1038/output337 | 实际返回进入return main；每个实际Task独立冻结 |
| return main | input3825/output538，实际消费child结果 | 三执行切片产出actual Host/Trace/Receipt；workflow4calls包含intake，known16,235/held0 |
| checkpoint | 实际published；SHA-256 `430516528ef3b8ae57137bfa38461b4573a0418fdd079acfcc8ce730d5e390cd` | 实际状态进入Guide；编辑者没有写实际project |
| Guide | input2394/output1024，finish=LENGTH；project unchanged=true | 实际调用及只读事实成立，回答未完整结束；caller原status=completed是Root漏判finish，报告纠正，不改原件 |

Root已补caller的COMPLETE guard。Attempt10 namespace为`chain-e4b59337-20bd-4973-94c8-0c384ef48895`，main自主0child；intake/main/Guide共3calls，Guide input1461/output181、finish=COMPLETE、project unchanged=true。Root确认零child完整API闭环通过，delta11,875，16.11秒。这里的Guide成功只属于10，不补到9。

### Attempt11：Tool执行后为什么停下

namespace：`chain-4927c3a2-28d9-4553-bfaa-9653d4eb1073`。以下由Root的014实测消息提供；编辑者未运行Tool或读取响应原件。

| 模块 | 实际输入 / 操作与输出 | 下游消费与停点 |
|---|---|---|
| intake→main | 两个实际HTTP entries；main input2840/output57 | main第一轮提出真实Tool请求；该Attempt新增known10,262，actual held0 |
| readonly Tool | `entry-api-bridge`，参数`path=materials/intent.txt`；handler实际执行1次 | 执行事实保留；结果写入Trace时发生FileNotFoundError，不能称模型已收到结果 |
| Trace / Session / Receipt | Session报告`trace-capture-gap`并安全停止；无成功Receipt，facts_complete=false | 没有第二model请求，child与Guide均未开始；不把实际Tool执行当成完整Tool闭环PASS |
| 有界故障复现 / 后续验证 | Root014仅做路径检查，未调用API或Tool：absolute result路径276字符时FileNotFoundError，短名251字符时created | 原失败保留；018的Attempt12实际结果保存/第二model消费另列，不能追写11为成功 |

这次失败将接点缺口定位到Tool结果保存/Trace捕获：模型已请求、readonly handler已执行，但该次结果不能继续交给第二轮模型并形成成功收据。Attempt12另行取得了真实保存/消费结果，不借用离线正例，也不改变11的失败事实。

### Attempt12：Tool消费成功后，child为什么blocked

namespace：`chain-2c414caa-c97d-4f53-a777-62b96313a209`。以下是Root018实测事实；本编辑者不读取实际project或调用原件。

| 模块 | 实际输入 / 操作与输出 | 下游消费和限度 |
|---|---|---|
| main两轮 / readonly Tool | 两轮模型合计input5874/output891；readonly Tool执行1次，Trace result真实保存并进入第二model | main自主选择1child；Tool循环及该执行切片的Host/Trace/Receipt成功 |
| child独立会话 | `CHAIN-API-INDEP-1`，1 model，input1023/output428；child给出blocked结果 | 该切片Host/Trace/Receipt成功，证明调用与捕获成功；blocked任务结果仍保留，不改为completed |
| fresh main回接 | input3916/output601，实际消费child blocked | 第三个切片Host/Trace/Receipt成功；workflow最终blocked，无checkpoint/Guide |
| 总调用与账 | intake、main两轮、child、fresh main共5HTTP；27.313秒，新增known20,104，actual held0 | 这是当前Attempt的实际消费，不拼接别次Guide或checkpoint成全链PASS |

Root转述child认为`inputs.text`是未验证的复制，且没有文件工具便无法读取。Root核对caller事实后指出这一判断错误：`build_role_request`已按Task.input_refs实际读取原件，校验SHA、UTF-8及revision，再将相同bytes装配给模型；exact refs的允许读集和写域分别校验。这里暴露的是模型对已提供输入快照的理解问题，不能据此虚构缺少材料或放宽权限。

018时dev4正在澄清baseline，只说明`payload.inputs`的来源与可消费快照，不把整个caller_context视为trusted，不授权额外文件读取或refs追踪，不改权限Schema。022说明快照理解问题已修复；13的child又误解“禁止再委派”的含义，仍不能写成child语义成功。

### Attempt13：同次六调用完成，child结果仍blocked

namespace：`chain-1d684323-1cc1-4d1d-97f4-c40878b341be`。数据取自Root022；child ID采用其随后明确更正的`CHAIN-API-CHILD-1`。

| 模块 | Root实际输入 / 输出 | 下游消费与限度 |
|---|---|---|
| main两轮 / Tool | 合计input6114/output998，Tool1；main自主选择1child | 真实Tool结果进入下一轮；不是固定子Task编制 |
| child | `CHAIN-API-CHILD-1`，input1151/output580，disposition=blocked | 模型误解delegation=false及empty child_results；快照问题已修，子Task语义仍blocked |
| fresh main | input4207/output607，实际消费child观测后decision=complete | 主层决定该路径complete，未将child结果改成语义成功，也不是人类接受 |
| checkpoint | SHA-256 `826abeec71fb45218c56657d13cffca8c1566df2157f7c705fe6e193e91576e3` | 实际发布后交给独立Guide |
| Guide | input2593/output193，COMPLETE，project unchanged=true | 同次6API路径完成；Guide回答质量和研究正确性不由COMPLETE证明 |

这次同一Attempt实际包括intake1、main两轮、child1、fresh main1、Guide1，共6API，32.063秒、新增known23,932。Root随后补child baseline：禁止再委派只限制继续分任务，不禁止child执行自己的Task；roles+Guide14项回归通过。不能把该局部回归或主层complete补写为child已成功执行。

### Attempt14：报告由谁发布，模型为何误判

namespace：`chain-acc67f5a-ee35-450c-b466-9ea3026df676`。Root022记录intake和main两轮共3API，15.453秒、新增known14,327；main两轮合计input6102/output736，Tool1、Receipt成功，自选0child，却返回blocked。因此未启动child，没有checkpoint或Guide。

Root指出模型误认为没有文件写Tool就不能产出报告，又将Supply报告引用与Tool名称的字符串不同误判为不同供给。dev4已在actual binding补入待由Driver发布的路径/契约元数据，并用conditional baseline说明：模型返回文本，Driver按原权限与admission尝试发布；真正成功的Receipt才证明发布完成。该说明不授予额外写权限，也不保证每次发布成功；Guide/intake没有该记录时不冒称发布。最新81项回归与A15实际闭环另有证据，不将Attempt14原blocked改为成功。

### Attempt15：全部本例启用桥的同次真实验证

namespace：`chain-390138a6-3dd8-4fa5-9615-d8986b6b5345`。以下由Root022最终A15实测消息确认，没有拼接其他Attempt。

| 模块 | 实际输入 / 输出 | 下游消费与结果限度 |
|---|---|---|
| intake | input6778/output907，success | 本次控制产物进入后续执行，不用旧fixture替代 |
| main两轮 / Tool | 合计input6581/output1018，readonly Tool1；自主选择1child | 原Tool结果真实进入下一模型；本次主层实际发出子Task |
| child独立会话 | `CHAIN-API-CHILD-1`，input1464/output341，decision complete | 正常验证给定快照，并保留beta缺locator；complete不消除该定位缺口 |
| fresh main | input4188/output645，decision complete | 明确消费实际child usage与结果，形成实际主层收尾 |
| workflow / checkpoint | workflow含intake共5calls、known21,922/held0；checkpoint SHA-256 `dc68dd094a574584a474de4767014ba3d516ffdfe9d15eb933af5ae082fea698` | 实际状态发布并供Guide消费；task_completion=false、human_acceptance=false |
| 独立Guide | input2738/output202，COMPLETE，project unchanged=true | 同次第6HTTP；实际调用/只读已证，回答内容不由COMPLETE保证正确 |

总计6HTTP、32.641秒、新增known24,862，actual held0。Guide只读MainState而未展开Receipt正文时，声称“noReceipt confirms publication”；Root说明实际Machine refs及独立冷检中已有Receipt。该表述局限保留，本轮结论是Guide独立调用与只读验证，不称其内容质量完全正确，也不另开润色测试矩阵。

### 独立冷检的范围

Root的012消息记录：原17账的2082份原件与新账hash/settlement/source/project originals完成核对。**文件/hash核对不等于原17次全部语义复验。** 在9/10之前，已有3份实际main Receipt独立语义复验PASS；不能据此声称9/10的每份新Receipt均已独立语义复验。第7次actual workflow在clone中发布checkpoint并构造Guide request通过，未写原project；这是冷接续与请求构造，不是Guide实际调用。9/10另有上面的两次真实Guide调用事实。

Root022随后明确了新增冷检范围：**累计14份真实generic execution Receipt及各自Bundle冷验证PASS，覆盖当前新增14个Attempts实际生成的全部Receipt。** A12/A13/A14三个Tool proof逐一将原Tool结果bytes/hash与下一次实际模型请求的Tool消息对照，相等且Trace validator PASS；不是只指Attempt14的收据。全部history/hash已核；原17账仍仅2082引用/hash/预算完整性核验，不宣称17次全语义重放。此前012的三Receipt范围保留为历史，不限制这次新增的14份冷检证据。

Root最终A15后又用新进程核验全部15个closed Attempts的hash/history/settlements：**累计17份实际Receipt及各自Bundle PASS，A12/A13/A14/A15共4个Tool proof的原结果与下一实际模型请求Tool消息exact bytes/hash相等且Trace PASS。** 这替代当前新增冷检数量，不改写旧17账的复验范围；14份/3proof保留为此前快照。

真实Tool在11失败后，12～15均有结果进入下一模型的冷检证据；15同次启用桥完成，13/14原blocked保留。source qualification=false、Human acceptance=false；非空required Skill loader仍缺，candidate assets未加载；Guide内容局限仍如上。

| 真实API事实 | 当前记录 |
|---|---|
| 实际运行时间、Provider/Model与配置pin | 待Root填 |
| intake实际结果 | 15个HTTP intake entries；15 success并实际消费；规划内容质量未由接口结果证明 |
| main/child/Guide实际新链 | 15同次6HTTP全部本例启用桥完成，child/fresh main complete、checkpoint/Guide成功；13/14及此前停点保留，Guide内容局限不删 |
| 新资产实际加载与位置/hash | candidate assets未加载；不填虚构装配记录 |
| 成功/停点/未开始与累计用量 | 新15次均closed，41HTTP entries，累计246,860/actual held0；失败/blocked原件与内部hold差异保留 |
| live/source qualification与权限closure | source qualification=false、Human acceptance=false；其余具体closure待Root补 |
| 独立冷复验与可读最终结果 | 新进程ALL15closed/hash/history/settlements；17份实际Receipt及各自Bundle PASS，A12～15四Tool exact bytes/hash nextmodel与Trace PASS；旧17账限定为引用/hash/预算完整性 |

## 7. 下一步优先补什么，为什么

1. **把本轮接口结果交人类接收，并保留内容限度。** 15已同次完成全部本例启用桥，child与fresh main complete；beta定位缺口和Guide Receipt表述局限仍保留。81项结构回归及真实调用/冷检不替代研究质量、来源资格或人类接受；原13/14 blocked不改写。
2. **按任务选择必要Tool与Skill。** Tool已有离线桥及12的真实结果消费；正式required Skill仍有真实loader/资格/actual使用缺口。先按实际路径补接点，不把候选Skill安装或文本文件存在称为通过。
3. **保留人类可读接收和准确任务状态。** M1-010/M2-009/M11-008仅在PR141分支定义为READY候选；本轮不把它们或M5四臂、M12/Topic5、复杂工程验证变DONE。研究内容质量、Skill准入、科研价值和正式接受各有独立条件。

本次结论限定为：最新一次完整入口81项通过，15同次6HTTP接通全部本例启用桥；新进程核验15closed及17份Receipt/Bundle、A12～15四个Tool结果消费冷PASS。beta缺locator、Guide表述局限及13/14 blocked均保留，正式Skill/Source/Human资格未闭合；原17账不作全语义重放声明。不接实际科研项目、不宣布整系统DONE。最新事实来自[通信](REPORT_COMMUNICATIONS.md)中的Root022最终A15/冷检及更正/补充，历史来自012/014/018；Root另写[API_RESULTS](API_RESULTS.md)。

证据入口：[总任务](TASK_PACKET.md)、[开发桥接交接](DEV4_HANDOFF.md)、[intake交接](DEV4_INTAKE_HANDOFF.md)、[资产索引](assets/INDEX.md)。旧[COMPLETION](../COMPLETION.md)保留65项时代的原范围；本轮四份Root日志位于仓库`.rwb/entry-archive/chain-002-{baseline-tests,bridge-tests,all-entry-tests,intake-tests}.log`，具体测试断言见`tests/test_entry_bridge_flow.py`和`tests/test_entry_intake_call.py`。细节无需读JSON才能理解以上结果。
