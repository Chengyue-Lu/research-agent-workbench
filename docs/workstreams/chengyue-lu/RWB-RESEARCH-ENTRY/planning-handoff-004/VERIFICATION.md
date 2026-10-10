# Planning / 正式 Handoff 验收记录

2026-10-10，PR140 未合并候选。本切片已接通选定的 planning 执行和正式 Handoff 链；三项 M Task 仍为 IN_PROGRESS。下面分别说明实现、实际结果和剩余义务，不将候选通路视为通用研究完成。

## 测了什么、产出了什么

| 模块 / 桥接 | 实际输入 | 实际输出及直接消费者 | 验收范围 |
| --- | --- | --- | --- |
| M1-010 入口控制 | 有界人类意图、Protocol/Task ceilings、工程 Method template | API 返回经 compiler 发布为 Protocol、Task、Method pins；包内 caller 重读产物和 intake report，再供 factory 消费 | 真实 API 控制转录已发生；自由自然语言规划质量未验收 |
| M11-008 planning 身份 | exact Method revision/hash 中唯一 planning_action_id 与对应 Requirement | Snapshot → planning-capability-slice Bundle → View → Host → planning Receipt；各 Role Task 独立冻结，Receipt 用自身 Bundle/View 冷回放 | planning 和原 Action/Skill closeout 的确定性兼容通过；实际 planning 链产生3份 Receipt |
| M2-009 主子执行 | 父 Task、实际权限/预算、主 Agent 提出的子 Task | 主会话选择实际 child，child 返回独立结果/usage/Receipt；新主会话收到真实结果 | 离线0/1/3子任务与失败/unknown通过；本轮实际 planning 场景主 Agent 选择1个 child，未固定产品子任务数 |
| M11-008 正式子 Handoff | actual child Task、结果、输入锁、产物/Receipt、限制和未解项 | source record、Task 与 HandoffPacket 分别固定；consumer 按自己保留的 expected Task/attempt/observation检查，再将完整 packet及pin送入 fresh main | 实际 API child → 正式 Handoff → 新主请求及具体处置已发生；独立冷回放和 Handoff integrity Skill checker通过 |
| M2-009 收尾与状态 | hash-pinned workflow report、正式 final Handoff | caller返回handoff_ref；checkpoint消费child/final packets及独立事实，发布MainState、保留Human待办、accepted_decisions为空 | 正反确定性检查、实际API和新进程冷回放通过；Task/Human接受保持false |
| M2-009 只读 Guide | MainState与按Attempt显式获准的approved_refs；第8轮另含final Handoff、最终Receipt | 独立API回答，无Tool、主会话消息或状态写入；调用前后项目bytes保持 | API调用与隔离通过；首个回答误把早期pending限制当当前事实，内容质量不计通过，详见下文 |

执行材料只含alpha/beta两个公开合成记录。实际子评审识别beta缺locator，区分记录不完整与来源无效；新主明确引用真实child Task和结果，保留来源接受unknown。这是工程交接证据，不是科学正确性、独立同行评审或Skill净价值证据。

## 确定性和安装消费

218个不同最终用例通过：101个planning/执行回归、74个Handoff/入口、3个文档检查、14个实际Role request装配检查和26个执行合同helper检查。增量复测计入原用例，不重复累计。正反例覆盖错误/mixed planning selector、歧义或非proceed Method、Task/输入/packet/产物漂移、重复Receipt与实际产物计数、写域逃逸、binary输出、missing-output、required Skill/H2缺证据、负面事项/Human传播，以及0/1/3子任务和failed/unknown预算。

首轮planning有1个正例输入错误；仅补既有规则所需的明确暂停条件后通过。Handoff首轮有1 error及同一caller用例两个子场景失败：inherited/generated未解说明重复违反既有uniqueItems，保序去重后通过。重复测试收集的受控中断、路径/计数反例、失败日志和修复后复测均保留；未改Schema规则或原断言来放行。

40f8a1f0的hosted CI分片1有253个用例、1 error：旧Receipt builder正例使用共享桩的占位kind="slice"，新身份检查拒绝了这个既有Manifest合同也不允许的输入。只在该正例显式提供合法Action scope，保留共享桩、产品校验与原正反断言；完整执行合同helper模块26/26复测通过。原hosted失败及本地修后结果均保留，最终远端结果须读取修后最新HEAD。

独立CPython3.11.16在checkout外用新wheel和默认包内schemas完成intake→factory/caller→no-Mode planning两次离线port调用（known76/held0）。fixture Task要求method-resolution，但执行Receipt交付deterministic-check-report，正式Handoff如实safe-paused并保留缺交付；独立冷回放与Skill checker通过。Root探针曾误用完成预期、packet字段与输出contract，三份失败保留，纠正探针未改产品/Task/Schema。后续提示词wheel的7模块源码与资源pins均独立核对一致。

## 真实 API：成功、失败和未开始

所有Attempt都保留实际request/response、Tool/Trace、usage、project/source原件与闭合账。当前临时测试上限6模型调用、1024output/call、32768bytes/body、120秒；仅北京时间18:00–09:00且每请求fresh官方闲时，无自动付费重试或fallback。Source qualification与Human acceptance均false。

| Attempt（独立原件） | 执行代码来源 | 实际结果 | 新增known / held |
| --- | --- | --- | --- |
| chain-5fe36117-5047-4ae5-8a4e-fbd4cb1c58bb | b696272 | 3HTTP/1readonly Tool；正文+fenced JSON被严格parser拒收，safe-paused；checkpoint/Guide未开始 | 15,408 / 0 |
| chain-058aa883-7ee5-4877-b96b-31b3c0a90e2f | 8f4743e | 2HTTP/0Tool；raw JSON收尾，但模型误称已调用Tool，实际事实gate拒收；checkpoint/Guide未开始 | 11,483 / 0 |
| chain-1ef4da45-7ceb-409c-9484-1448943027da | 97517d1 | 2HTTP/0Tool；仍误称快照读取为Tool调用，事实gate保持拒收；checkpoint/Guide未开始 | 11,843 / 0 |
| chain-4d9e58d1-b55a-4fe8-a0b7-e676e49ca4ef | 97517d1 | 4HTTP；实际child正式Handoff已进入新主请求，父Task/phase正确；模型误认child为自身旧答，追加委派触及临时预算而safe-pause；checkpoint/Guide未开始 | 20,472 / 0 |
| chain-d6948304-8eb6-49f6-ae37-663346ae7539 | 4da65a6 | 3HTTP；child观察返回，但缺必需next_actions，严格parser拒收；新主消费/checkpoint/Guide未开始 | 14,271 / 0 |
| chain-164574dd-a768-401b-91fc-a6f3d1edce3b | d617a8e | 5HTTP/0Tool，103.031秒；intake→main→actual child→正式Handoff→fresh main→final Handoff→checkpoint→独立Guide完整发生 | 23,343 / 0 |
| chain-e2c33c21-51ff-4f5b-a4c2-b87dae05dfd8 | d617a8e | 5HTTP/0Tool，105.875秒；整链完成，Guide显式读取final Handoff后识别已返回child，但仍误述实际publication需授权 | 25,917 / 0 |
| chain-873883d4-e618-4711-92ba-756a9e064327 | d617a8e | 5HTTP/0Tool，105.765秒；整链完成，Guide显式读取MainState、final Handoff和最终Receipt，识别actual artifact及早期pending条件，不新增授权gate | 27,528 / 0 |

前五次停止不记为整链通过。各停点的模型零调用审计通过，保留其真实Scope、Receipt、Handoff及未开始事实。修正只明确raw JSON、快照与原生Tool事实、模型可见role/Task/phase/child来源，以及child完整五字段合同；无动作时next_actions允许空列表。同Profile可复用到不同会话，不强迫complete或固定child数。

首个完成链的累计账为368,689/held0，剩余9,631,311。代码来源完整SHA为d617a8e02bfcad021051280939637504d99abb0d；RESULT SHA为ebaea7f0985861a267715ec57840a68f85063405df18a01ed971850a96ae3165。另一新进程验证3份planning Receipt、child/final两份正式Handoff、checkpoint机器pins与Human待办，模型调用0。实际HTTP内容审计确认child完整packet及结果/限制/usage/refs进入fresh main请求；新主响应具体消费beta缺locator及来源unknown。最终和子Handoff分别通过独立Skill checker，结论仅structural。原Action/no-Skill Tool通路的实际证据仍属于[前一切片](../package-caller-003/VERIFICATION.md)所列来源，不跨版本冒充本次Tool覆盖。

Guide首个回答COMPLETE且项目bytes未变，但它只收到MainState，open_risks合并了初始main的“child尚未返回”“publication pending”与最终限制，缺阶段信息；回答因此误述未产生child/Receipt。这个内容缺陷保留。两轮后续分别用既有approved_refs显式追加已消费final Handoff、再加入最终执行Receipt，不自动遍历refs。第7轮整链与冷回放通过，Guide识别child但仍将模型时间的pending publication当当前缺口。第8轮整链与冷回放通过；其Guide实际请求仅3份获准快照、23,092bytes/0Tool，全部text/hash与原件一致，项目bytes不变。回答正确记录child、actual artifact及阶段变化，不再提出额外发布授权；仍用了契约之外的“Receipt-of-publication”说法，对记录交付与自身复核的区别表达不准确，因此不标通用Guide质量通过。Root首个冷构造漏显式remote DataPolicy，被默认local-only正确阻断；纠正仅探针授权参数，模型调用0。Root输入审计另有两次tools键/compact result字段误读，仅修冷探针并保留失败；未改原API bytes。

最后一轮RESULT SHA为c94dcacda9870a1b1c803906c856b290df537be87d5f33bb1aa73d38b71e6473。独立冷回放核验3份planning Receipt、2份formal Handoff；33份账原件、100份项目原件及5个实际HTTP request/response内容审计通过。完整历史重新闭合后累计422,134/held0，剩余9,577,866；本切片8个新增Attempt共150,265known，三个完成链分别保留自己的source/config/helper原件，未互相覆盖。后续文档提交不改变执行代码来源。

## 验收边界与后续

M1-010/M2-009/M11-008保持IN_PROGRESS。planning与Handoff的Core支持扩展归M11-008；候选ADR-0025/0026待合并边界接受，未改写M1-010原定义。新消费者兼容旧Action输入；旧消费者对新增planning kind/producer_ref可能fail-closed，单向兼容不等同统一升级完成。

仍需按各自Task补齐自由需求/材料规划质量、实际Skill加载及准入、研究Source/Evidence/Claim/语义MethodTrace消费者、阶段化MainState与Guide解释质量、真实工程任务与Topic5/M12条件。本轮不制造H2 Manifest/Audit或Skill接受，结构Receipt不代替产物内容质量。远端验收绑定PR140最新HEAD的GitHub Checks；历史绿色检查不证明新HEAD通过。
