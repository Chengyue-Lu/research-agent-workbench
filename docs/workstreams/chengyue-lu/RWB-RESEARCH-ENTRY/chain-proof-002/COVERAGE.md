# 本轮测试覆盖：模块、输入和实际输出

2026-10-08 · CHAIN-REPORT-006；CHAIN-REPORT-009/012/014/018/022/023更新。原离线证据来自Root指定日志、测试文件及有界开发交接；13～15、累计及冷检来自Root022及更正/补充，最新wheel020 installed验收来自023，既有回归和9～12来自012/014/018，记录于[通信](REPORT_COMMUNICATIONS.md)。编辑者未测试或读取调用原件；Root已更新[API_RESULTS](API_RESULTS.md)。

最新完整入口一次81 tests / 144.636s / OK。A15同次6HTTP接通本例全部启用桥，child与fresh main complete、checkpoint发布、Guide COMPLETE且project unchanged=true；beta缺locator和Guide关于Receipt的表述局限保留。15closed/41HTTP/known246860/held0；Source、Human及正式Skill资格未完成，不整系统DONE。13 child blocked、14 main blocked，旧78项及70项失败/6项重跑保留历史。B01–B13保留离线案例；最新事实来自Root022最终补充。
“离线通过”指生产接口实际被脚本化offline Provider或受限本地handler调用，断言通过；不代表付费API、live资格、科研内容正确、具名接受或merge。

## 逐模块覆盖

| 编号 / 模块 | 实际输入与操作 | 实际输出 / 下游消费 | 本轮覆盖与限度 |
|---|---|---|---|
| B01 角色职责请求 | 显式Task/Profile/输入pins与intake/main/child/guide职责 | 独立ModelRequest、内置baseline、当前允许集与输入snapshot | 基础入口套覆盖；Root最新确认candidate assets尚未加载，不能把索引交付算实际使用 |
| B02 intake调用 | SYNTHETIC-CONTROL-CALL Protocol、Task/Profile、人类ceilings、已知Method/Requirement；调用无Tool离线端口 | success；input30/output8/held0；compiler/persist返回实际控制文件pins；unknown保留无live资格 | 新5项套含正例与无效输出/发送失败/拒绝/越写域；不是自由自然语言需求规划质量测评 |
| B03 Protocol/Task/Method产物 | intake实际候选及独立人类边界经原compiler校验/发布 | 新Protocol/Task/Method/Requirement文档与pins | 下游main两个View精确引用发布Task；proposal、draft不产生Human或来源接受 |
| B04 Capability选择 | 每个实际Task与显式typed Supply/离线资格fixture | 独立selection、Snapshot以及显式Bundle/View | bridge0/1/3调用数分别对应1/3/5次选择；fixture不是live conformance，可信检查由测试caller提供 |
| B05 Bundle/View→Session/Host | exact frozen Task/闭包、Profile/policies/binding与预绑定Driver | 实际响应、Host report、Trace、输出工件/Receipt pins | 通过真实生产消费者；已有基线同时覆盖漂移/unknown/权限拒绝；不推导生产凭据或平台native可用 |
| B06 main动态0..N | 离线脚本返回0、1、3个delegations；同一workflow执行这些真实控制输出 | stage-completed；actual calls1/3/5，known38/114/190，held0 | 不固定子数量；决策由脚本构造，不评真实模型何时/如何拆任务；child当前顺序执行 |
| B07 child独立执行与结果消费 | 每个child实际Task分别冻结；新main收到actual状态、usage、工件/Receipt opaque pins | child execution_status=completed；每个usage=input30/output8/model1/Tool0；新main消费实际子ID与收据 | 读集不自动加入child工件正文；request snapshot改变，结果消费不是单独模块假pass |
| B08 readonly Tool循环 | research-contract-check({path:materials/approved.txt})；handler只读exact input/hash | 一次实际Tool读取，结果含bounded synthetic；Trace attempted/succeeded，model2/Tool1/known76 | procedure可选Tool与direct Tool两种路径通过；第二request确实收到tool消息；不证明任意callback只读 |
| B09 Tool失败阻断 | handler抛错，或2048字符超过1024上限 | Host failed、safe-paused；model_calls=1、known38/held0、Tool事实保留；无第二请求 | Root已修失败后多余模型请求缺陷；不是删除失败日志后宣布成功 |
| B10 Handoff/Trace/Receipt | 实际Host结果、Tool事件、artifact/validation闭包与子结果pins | bridge每个generic Receipt独立冷读校验；完整intake链三执行Receipt refs被workflow/checkpoint使用 | Receipt只证明slice，task_completion=false；不证明legacy无Skill Handoff格式迁移完成 |
| B11 Main State/checkpoint | hash-pinned实际workflow报告、实际Protocol pin和允许write scope | INTAKE-CONTROL-STATE checkpoint，供Guide消费 | 已验证工程接续；不等于Research State科学语义、CAS/自动恢复或Topic5权限 |
| B12 独立Guide | “Explain the retained state.”+批准MainState | 实际独立ModelResponse、role=guide、tools空、input usage30；项目文件字节集合未变 | 当前正例实际调用一次；正文质量未评，外部候选Guide prompt未注入；不自动回传main |
| B13 总账/停止 | 同一个workflow prior_usage含intake；失败/unknown、预留不足及权限拒绝 | 离线完整链workflow累计4calls/known152/held0，Guide另一次；失败child held228，未开始兄弟保留 | 未知不填零、失败不重试、整段预留不足0calls；新真实API累计账与内部hold区别见下表 |
| B14 Profile→pure wire上限 | 真实完整Profile的required limits传入wire；Root补每Profile ceiling enforcement | 最新Root反馈64 tests/OK，skipped1为Windows symlink；0.590s是此前009快照 | 旧wire descriptor可省略limits，保留兼容；不是扩大通用权限或整链live通过 |
| B15 API预算guard | 最新授权为无限Attempt、累计10M、每次最多6calls；Root执行独立budget套 | 最新Root反馈8 tests/OK；3.659s是此前009快照 | 预算guard结果不授予来源/权限或Skill资格；不与入口测试相加为unique总数，预算也不是固定角色、次数或事件架构 |

完整正例不是把以上模块独立PASS相加：B02实际发布pins被B03/B04/B05使用，B06/B07真实子返回进入新main，B10实际报告再被B11读取，B12实际消费B11并调用独立端口。

## 数量与实际日志

| Root运行 | 结果 | 合计方式 |
|---|---|---|
| chain-002-baseline-tests.log | 65 tests / 87.799s / OK | 已包含于下方71套 |
| chain-002-bridge-tests.log | 6 tests / 62.573s / OK | 已包含于下方71套；一个test可含多个subcase |
| chain-002-all-entry-tests.log | 71 tests / 146.648s / OK | 当时全入口整套65+6 |
| chain-002-intake-tests.log | 5 tests / 24.382s / OK | 新intake单套，另行实测 |
| 原独立测试总数 | 76=71+5 | 历史两套分别通过；不是单次76，也不累加重复65/6 |
| 先前完整入口整套（Root012反馈） | 78 tests / 142.707s / PASS | 历史一次完整整套，含profile/permissions新增回归；最新81项另列 |
| 最新Bundle套（Root012反馈） | 13 tests / 2.423s / PASS | 有界Bundle验证；与入口套有交叠，不相加 |
| 最新profile+wire套（Root012反馈） | 64 tests / OK，skipped1 | Windows symlink跳过；Root未另报最新耗时；此前009为0.590s |
| 最新API budget套（Root012反馈） | 8 tests / OK | Root未另报最新耗时；此前009为3.659s，不与其他套重复累加 |
| 后续70项Trace+bridge合跑（Root018） | 前64项Trace通过，含两项新增回归；后6bridge失败 | wheel重生成resources影响后6项；原70项日志保留失败，不写为全PASS，不与profile/wire64混为一套 |
| 修正顺序后6bridge重跑（Root018） | 6 tests / 51.668s / PASS | 只证明这6项重跑范围，不冒称同次70项全通过 |
| 先前wheel014安装site-packages/resource/CLI（Root018历史） | 2 tests / 3.724s / PASS；pip check PASS | 保留历史范围，不重复累计unique总数或替代整链API |
| 最新wheel020 installed验收（Root023） | build→install→installed site-packages RuntimeResources→2 CLI tests / 3.739s / OK；pip check No broken requirements；installed entry help成功 | 安装后资源与CLI可用验证；负例ERROR尾行预期、原完整日志保留；不新增API推断或重复累计unique总数 |
| child baseline修改后roles+Guide（Root022） | 14 tests / 9.295s / PASS | 说明禁止再委派不禁child执行自身Task；不是child语义成功或其后Driver发布说明的整套回归结果 |
| 最新Driver发布契约说明后的全entry（Root022补充） | 81 tests / 144.636s / OK，一次完整套 | 含新Snapshot/child/pending publication断言；预期negative CLI ERROR尾行保留，不与旧分套相加 |

完整intake链端口调用数是5：intake1、main/child/main3、Guide1。三执行Slice有三Receipt；intake和Guide不因此冒充同样的Host Slice Receipt。

## 条件外环与未覆盖项

| 范围 | 当前本轮结果 | 下一步为何需要 |
|---|---|---|
| 真实API同Provider主子协作 | 15同次6HTTP完成所有本例启用桥，child/fresh main complete、checkpoint/Guide成功 | 接口验证不替代研究质量或人类接受；beta缺locator和Guide表述局限保留，13/14不改写 |
| canonical Tool外传 / entry-api-bridge候选 | canonical research-contract-check禁止外传；public synthetic候选在11执行后Trace失败，12实际保存Tool结果并进入第二model | 12的Host/Trace/Receipt成功只证明有界切片；不替换canonical，不解除数据、供给或资格边界 |
| 正式Skill加载与资格 | 未通过；入口required_skills非空仍阻断；3个资产为test-candidate | 要验证真实loader/package pin/实际使用及独立admission，不能用文件存在替代 |
| 人类自然需求的改写/方法选择质量 | 未评价；本例回传显式ceilings和既有Method | 真正规划能力须用适当内容任务另测，本轮只接接口 |
| 人工既有材料整理/导入 | 基础caller契约可接受显式材料；新两套没有杂乱资料整理场景 | 真实内容整理需要实际任务，不假造历史State/接受 |
| Source/Evidence/Claim/Method Trace/Need维护 | 本轮不新测科研外环；离线Supply/材料fixture无live/科学资格 | 按任务实际需要启用；不能把它们变成每个Task强制DAG |
| Human方法/Claim/发布与Skill准入 | 不由本轮PASS产生 | 具名人类保留决定，本轮task_completion/human_acceptance仍false |
| M5四臂与净价值 | 未运行 | 模块接通不替代已定义独立评价、盲审、comparability与真实案例 |
| M12/Topic5、自动恢复、复杂工程V&V | 未授权本轮实现或验收 | 独立前置/Gate与实际复杂任务证据仍需要满足 |
| M1-010/M2-009/M11-008 | PR141分支的READY定义候选 | 定义不等于实现/共享接受，当前81项不把三任务写成DONE |

## 当前真实API模块与结果

人类grant：不限Attempt，累计上限10,000,000 tokens；同Provider多独立会话协作按一个整体Attempt记录。
最新grant已授权单次最多6calls；本轮调度限北京时间18:00至次日09:00且fresh官方闲时。来源、权限、配置、历史完整性和累计账仍由Root核实。本轮使用合成隔离材料，不接真实项目；次数预算不固定main的子数量或系统角色。

| Attempt / 模块 | Root实测结果 | 消费 / 未开始 / 限制 |
|---|---|---|
| 新Attempt1 intake→Supply | intake成功6473 input+915 output=7388 tokens | Root Supply observation_scope错误enum在main前停止，已修；后续结果不补造 |
| 新Attempt2 intake→selection→View | intake成功6473+937=7410；actual capability selection成功 | 候选Method.blocked_conditions为空，Execution View停止；main未发送；source qualification仍false |
| 新Attempt3–8 | 均已closed，各停点保留于原件 | Root消息未逐项提供全部结果，编辑者不补造；Root另写[API_RESULTS](API_RESULTS.md)，未扩大本编辑读域 |
| 新Attempt9 intake→main→child→return main→Guide | main自主选择1child；实际child返回被新main消费，checkpoint发布；5calls/31s/新增known19653 | Workflow4calls含intake，known16235/held0；Guide2394+1024、finish LENGTH、project unchanged=true；同次整链未完整成功 |
| 新Attempt10 intake→main→Guide | main自主选择0child；workflow stage completed；3calls/16.11s/新增known11875 | Guide1461+181、COMPLETE、project unchanged=true；Root确认零child完整API闭环，不补到Attempt9 |
| 新Attempt11 intake→main第一轮→readonly Tool→Trace失败 | CLOSED；HTTP2（intake+main第一轮），11.016s，新增known10262；main2840+57 | entry-api-bridge(path=materials/intent.txt) handler执行1次；Trace写Tool result FileNotFoundError，Session trace-capture-gap、安全停止；无第二model/child/Guide、无成功Receipt、facts_complete=false |
| 新Attempt12 intake→main两轮/Tool→child→fresh main | CLOSED；5HTTP，27.313s，新增known20104；Tool结果保存并进入第二model，三个切片Host/Trace/Receipt成功 | main自选child1，fresh main实际消费child blocked；workflow blocked，无checkpoint/Guide，不能全链PASS |
| 新Attempt13 intake→main两轮/Tool→child→fresh main→checkpoint→Guide | CLOSED；同次6API，32.063s，新增known23932；actual route completed，Guide COMPLETE/project unchanged=true | child disposition blocked；fresh main消费其观测后decision complete；证明路径完成，不证明child语义成功或人类接受 |
| 新Attempt14 intake→main两轮/Tool | CLOSED；3API，15.453s，新增known14327；Tool1/Receipt成功；main自主0child但blocked | 误解缺文件写Tool不能报告、Supply引用和Tool名不同即不同供给；无child/checkpoint/Guide；后续说明及81项回归已完成，不改写14原结果 |
| 新Attempt15 intake→main两轮/Tool→child→fresh main→checkpoint→Guide | CLOSED；同次6HTTP/32.641s，新增known24862，全部本例启用桥实际成立 | child与fresh main complete，checkpoint发布，Guide COMPLETE/项目未变；workflow含intake5calls/known21922/held0/task_completion=false/human_acceptance=false |

最新Root022最终核实新15个closed Attempts、41个HTTP entries：intake15、main18（含return/fresh main与Tool前后两轮）、child4、Guide4。累计known246860 / actual held0，含旧55614。此前14次/35HTTP/221998及018/014/012、截至Attempt2的70,412 / actual held0保留为历史快照；Attempt2内部held1,101,024与实际API仅intake1次的差异不删。内部hold不等于实际API held，不改原件。Human acceptance=false、Source qualification=false，非空required Skill loader仍缺。

| 真实模块 | Root实际输出 | 消费与结果限度 |
|---|---|---|
| Attempt9 intake / main决策 | intake6497+859；first main2520+621，自选1child | 实际控制产物进入选择冻结；每实际Task独立冻结，不是固定脚本分配子数量 |
| Attempt9 child / main回接 | CHAIN-API-CHILD-CHECK 1038+337；return main3825+538实际消费 | 三个actual Host/Trace/Receipt；主子回接已证，Root另写[API_RESULTS](API_RESULTS.md)，编辑者未读响应原件 |
| Attempt9 checkpoint / Guide | 实际published checkpoint，SHA430516528ef3b8ae57137bfa38461b4573a0418fdd079acfcc8ce730d5e390cd；Guide截断且项目未变 | caller原status completed是Root漏判finish；报告纠正，原件保留，caller已补COMPLETE guard |
| Attempt10 Guide闭环 | Guide完整COMPLETE且project unchanged=true | 与零child workflow闭合；不替代Attempt9同次Guide完整性 |
| Attempt11真实Tool请求 / 执行 | main请求entry-api-bridge(path=materials/intent.txt)；readonly handler实际执行1次 | 结果写入Trace失败，不能称第二轮模型消费了Tool结果 |
| Attempt11 Trace / Receipt / 未开始 | Session trace-capture-gap、安全停止；无成功Receipt、facts_complete=false | 没有第二model请求，child与Guide未开始；实际执行不等于整条Tool链PASS |
| Tool写入故障复现 / 后续实测 | Root014无API/Tool路径检查：absolute result276字符→FileNotFoundError，短名251字符→created；018的12另行保存结果并进入第二model | 复现与真实后续消费分开；11失败原件不改为PASS |
| Attempt12 main两轮 / Tool | 两轮模型合计input5874/output891；readonly Tool1次，Trace result保存并进入第二model | main自选child1；该切片Host/Trace/Receipt成功，不凭独立模块拼PASS |
| Attempt12 child / fresh main | CHAIN-API-INDEP-1，一次model input1023/output428；fresh main3916/601实际消费child blocked | 三个切片Host/Trace/Receipt均成功；workflow blocked，无checkpoint/Guide；收据成功不等于任务语义完成 |
| 12的快照误解 / 后续baseline | Root核对build_role_request已按Task.input_refs读取/校验SHA、UTF-8、revision并装配同bytes；022确认快照问题已修复 | 不将caller_context整体变trusted，不授权额外读/refs追踪、不改权限Schema；13 child仍有另一项delegation误解 |
| 13 main两轮 / child / fresh main | main两轮合计6114/998、Tool1，自选CHAIN-API-CHILD-1；child1151/580 disposition blocked；fresh main4207/607消费观测后decision complete | child误解delegation=false和empty child_results；主层接纳观测不等于child成功或人类接受；ID依Root更正采用CHAIN |
| 13 checkpoint / Guide | checkpoint SHA826abeec71fb45218c56657d13cffca8c1566df2157f7c705fe6e193e91576e3；Guide2593/193 COMPLETE、project unchanged=true | 同次6API路径完成；Guide质量与研究正确性未由COMPLETE证明 |
| child禁止再委派说明 | Root补baseline：禁再委派不禁自身Task执行；roles+Guide14 tests/9.295s PASS | 局部回归不把13原child blocked改为成功 |
| 14 main / 发布契约说明 | main两轮6102/736，Tool1/Receipt成功，自选0但blocked；dev4加入actual binding中待Driver发布路径/契约元数据及conditional baseline | 模型返回文本，Driver按原权限/admission尝试发布，成功Receipt才证明发布；Guide/intake无该记录不冒称发布；81项及A15后续成功不改写14 |
| 15 intake / main两轮 / Tool | intake6778/907 success；main两轮合计6581/1018，readonly Tool1，自选child1 | 本次产物与Tool结果进入实际下游，无不同Attempt拼接 |
| 15 child / fresh main | CHAIN-API-CHILD-1 1464/341 decision complete，正常验证快照、保留beta缺locator；fresh main4188/645 complete | fresh main明确消费child实际usage及结果；task_completion=false/human_acceptance=false |
| 15 checkpoint / Guide | checkpoint SHAdc68dd094a574584a474de4767014ba3d516ffdfe9d15eb933af5ae082fea698；Guide2738/202 COMPLETE/project unchanged=true | workflow含intake5calls known21922/held0，Guide为同次第6HTTP；接口/只读验证成立 |
| Guide内容局限 | Guide只读MainState未展开Receipt正文时说noReceipt confirms publication，实际Machine refs及Root冷检已有Receipt | 不宣称Guide内容质量完全正确；保留局限，不新开润色矩阵 |
| 正式Skill加载 | candidate assets未加载，非空required Skill loader仍缺 | 不宣称正式Skill已准入 |
| 原冷检范围（012历史） | 原17账2082原件及新账hash/settlement/source/project原件核对；当时新3个main Receipt语义复验PASS | 当时三Receipt发生于9/10之前；最新14份冷检见下行，旧17仍不宣称全语义复验 |
| 前次Receipt / Bundle冷检（022历史） | 当时累计14份Receipt及各自Bundle冷PASS、A12/13/14三Tool proof PASS | 保留历史；最终17份及4proof如下，不改原17账范围 |
| 最新Receipt / Bundle冷检（Root最终A15） | 新进程ALL15closed/hash/history/settlements，累计17份实际Receipt及各自Bundle PASS | 覆盖全部新增15Attempts实际生成Receipt；旧17账仍仅2082引用/hash/预算完整性，不作全语义重放声明 |
| 最终Tool结果消费冷检（Root最终A15） | A12/A13/A14/A15共4proof，原结果bytes/hash等于下一实际模型请求Tool消息，Trace PASS | 证明四个实际结果保存/消费一致；不替代研究正确性或人类接受 |
| Attempt7接续冷检 | actual workflow clone发布checkpoint和Guide request构造PASS；原project不写 | 这是请求构造与接续验证，不是Guide实际调用；9/10实际Guide另计 |

Attempt9 namespace为`chain-cb22901c-ad73-469c-accb-9d6fb876a080`；10为`chain-e4b59337-20bd-4973-94c8-0c384ef48895`；11为`chain-4927c3a2-28d9-4553-bfaa-9653d4eb1073`；12为`chain-2c414caa-c97d-4f53-a777-62b96313a209`；13为`chain-1d684323-1cc1-4d1d-97f4-c40878b341be`；14为`chain-acc67f5a-ee35-450c-b466-9ea3026df676`；15为`chain-390138a6-3dd8-4fa5-9615-d8986b6b5345`。13～15与最新累计/冷检取自Root022及最终补充；旧结果取自012/014/018。Source/Human/正式Skill资格未完成，不能宣布整个系统DONE。

可读案例和失败过程见[ROOT_REPORT](ROOT_REPORT.md)，资产边界见[INDEX](assets/INDEX.md)与[CALLING_CONTRACTS](assets/CALLING_CONTRACTS.md)。本表的源码定位为`tests/test_entry_bridge_flow.py`、`tests/test_entry_intake_call.py`；Root日志位于仓库`.rwb/entry-archive/`。
