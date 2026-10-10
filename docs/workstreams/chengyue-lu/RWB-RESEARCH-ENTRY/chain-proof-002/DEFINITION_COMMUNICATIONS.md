# CHAIN-DEF-002 可见通信与读域

Profile：task-definition evidence scout；required-Skills=[]；预算10分钟/2轮。只写本目录TASK_DEFINITION_PROPOSAL.md及本文件，不改canonical/root/code，保留他人工作。禁止API/产品测试/生产Tool/Key/历史账/安装/再委派/commit/push/primary memory写入。

## Root指派原文

> 新有界规划 Task CHAIN-DEF-002。Profile=task-definition evidence scout；required Skills=[]；准备预算10分钟2轮。用户当前已明确要求先Task定义/docs再全链桥接测试。读本轮 PR140 worktree/docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/TASK_PACKET.md；读同worktree canonical TASKS/ROADMAP/DEVELOPMENT/M_SERIES_IMPLEMENTATION_MAP及原COMPLETION，src entry仅接口metadata必要窄读。独占只写chain-proof-002/TASK_DEFINITION_PROPOSAL.md、DEFINITION_COMMUNICATIONS.md，不修改canonical/root/code。提出最小exact新增Task IDs（比如M1-010、M2-009、M11-008；核是否空闲）、名字、具名owner、risk、harddeps全DONE的合法起点、scope/negative/验收、与M5-008/Topic5/真实任务分界；避免把模块通路接合变成四臂/净价值评价。考虑PR140仍Draft/currentcandidate、新docs-only task-definition先提交但隔离测试由用户当前明确授权，不伪称已merge/正式DONE。不要拆一堆相互阻断的Task；主要1～3个有界切片。你不独自在代码库，保留他人。禁止API/产品测试/Tool/Key/历史账/安装/再委派/commit/push/primary memory写入。写通信、source pins/Compact结果后停止，先发建议ID/必要性供Root开始docs。

## 先发Root的ID建议原文

> CHAIN-DEF-002先建议3个最小切片：M1-010『通用研究入口的受控需求/材料接入与契约产物桥接』（路诚钺,R2）；M2-009『角色必载指令与有界0..N主子运行消费』（路诚钺,R2，黄毅审Session实际接点）；M11-008『普通研究入口的冻结执行/closeout全链桥接Gate』（黄毅,R2，路诚钺审控制/权限/Trace）。canonical当前分别最高M1-009/M2-008/M11-007，3候选ID在TASKS/ROADMAP/施工导航无命中，空闲。各入口harddeps只列已DONE旧契约/消费者，不互相挂新Task造成锁链；新三slice间用同PR集成证据和桥矩阵关联，最终Gate验收引用producer/实际consumer source pins。PR140 currentHEAD确认为d630f8e1候选，不能写merge/DONE；当前人类已授权先定义docs后隔离bridge测试。正在核exact deps/negative与M5-008、Topic5分界，10分钟内交proposal。

## exact依赖与分界消息原文

> exact候选harddeps（本worktree TASKS对应行均DONE）：M1-010=M1-003,M1-004,M1-005,M1-007,M8-003,M8-005；M2-009=M2-002,M1-004,M2-005,M3-008,M6-002；M11-008=M9-005,M6-002,M11-004（可选Skill启用条件引用已DONE M11-006/007，不让Skill资格阻塞Core入口）。新增定义可建议READY但接受前标候选，不依赖Draft PR140 merge，也不把三新ID相互挂硬依赖。M1负责自然语言模型JSON→受人类ceilings控制的Protocol/Task/Method/Requirement+真实下游；M2负责baseline prompt/profile/input实际载入、main实际0..N、child→main消费与全Run预算；M11负责exactFrozen接口/actualfacts/Tool或eligibleSkill use-boundary/closeout/replay和wholebridge测试矩阵。M5-008仍四臂评价Gate，Topic5仍freeze；人工旧state接入与独立Guide只复用既有文件契约，无自动恢复。

## 实际读域和关键事件

Root收口消息原文：

> 请优先落盘已确认三行定义和harddeps/owner-index/negative clauses，供Root先建docs-only PR；两轮以内，避免扩展新的规划面。三Task READY为候选分支状态、未合并不等于共享接受。随后完成compact输出即停止。

- 先完整读本轮TASK_PACKET及原COMPLETION。读canonical TASKS的M1/M2/M11行、具体候选空位与DONE deps、M5-008/Topic5/M12及相关owner导航；读ROADMAP开头权威/Phase/Topic对照、Topic5冻结边界和M5/M11相关索引；DEVELOPMENT读取Task-definition/READY依赖/DONE不可变/隔离与R2 review规则；施工导航读表/前68行及M11/M5边界索引。
- 首次工具批量输出有截断，后续用精确ID行模式补读全部必要deps，不以被截断片段断言。接口metadata首次Windows wildcard传入rg失败，改为目录加 `-g '*.py'` 得到入口classes/functions定位；没有执行任何产品入口，也没有读无关正文。src只读接口符号metadata；接口的当前实现/不足由同worktreeCOMPLETION描述与本agent此前已核接口背景限定，不假称本轮完整重新审计。
- `git rev-parse HEAD`只读确认PR140候选 `d630f8e174846f4932d05a7a0d69076930b53ee1`。三个拟议ID在TASKS/ROADMAP/施工导航搜索为空，不虚造已正式定义；proposal六项正文sources以Get-FileHash固定。
- 发现canonical M6-010 Task行DONE而owner导航仍残留BLOCKED、施工导航M14总表/说明亦有历史漂移；只按TASKS当前exact rows核deps，未改这些共享文件，也不把旧导航残留列为新Core hard gate。需由Root对其本轮明确更新域处理。
- 本组仅写两提案工件，静态核Markdown相对链接/文件hash；不跑产品tests/脚本/API/Tool/Key/账，不联网读取PR/CI，不stage/commit/push、不改primary memory。PR140 Draft与后续docs-only接受状态来自本Task Packet，不伪造远端即时核验。

最终Compact/hash由Root保存。交付 [TASK_DEFINITION_PROPOSAL](TASK_DEFINITION_PROPOSAL.md) 后停止；Root负责canonical docs-only定义、bridge运行plan、当前已授权测试和后续PR/具名接受。

静态交付核验：两文件8处相对Markdown链接均存在。按Root收口消息将三条canonical候选行、exact harddeps、三条owner-index与negative clauses集中落盘；未增加Task数量或新的规划面。最终两文件Get-FileHash SHA256由Compact返回，不做self-hash循环。
