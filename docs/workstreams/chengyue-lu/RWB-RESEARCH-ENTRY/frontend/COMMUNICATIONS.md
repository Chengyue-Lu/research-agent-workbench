# PLAN-FRONTEND 可见通信与关键事件

2026-10-07；Task `PLAN-FRONTEND`；Agent Profile：bounded frontend-product and intake-planning agent；required-Skills=[]。
权威输出：[PLAN.md](PLAN.md)。本文件只存本窗可见指派、关键观察、验证与交付边界，不存隐藏推理。
预算：20分钟 / 4轮（入口核对、接口映射、方案成稿、静态验收）；禁止再委派。

## 可见指派

来源：Codex create_thread；source_thread_id=`01a1064a-eaef-7da0-aebd-962910ff42b8`；本窗收到以下任务。为了保持文档路径便携性，原指派中指定的绝对 checkout 路径以“指定 checkout”替换，primary以“primary”表示；分支/基线及其余约束保留。

> 用户明确要求新开窗口考虑前端，当前执行PLAN-FRONTEND规划Task。实际读写checkout为指定 checkout，branch codex/research-entry-integration，base develop d3c4d23206339ebc7f18b5621f3aa5453f96335e；不要使用primary旧HEAD，不新建branch或checkout。先读该checkout AGENTS、README、docs/README/DEVELOPMENT/ARCHITECTURE和docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/TASK_PACKET.md、README，按PLAN-FRONTEND(required-Skills=[])/读域/两MD互斥写域/20分钟4轮/stop执行。你不是唯一参与者，不覆盖别人的修改；primary PROJECT_MEMORY只读M5 own-row导航，不写。规划人类需求配置角色与后续产品图形前端：输入→内部角色→Protocol/Task/Method/Capability→执行→Human决定，合法bootstrap/格式与错误、可读完成度、从零/无MainState接续、独立只读Guide。明确角色baseline与可选Skill，main决定0..N，不固定编制、不新建/接续Mode。仅写本workstream frontend/PLAN.md、COMMUNICATIONS.md；给可验收候选任务名、现有接口映射和近期/远景。0代码/Schema/Registry/API/生产Tool/Key/账/产品测试/安装/Git commit/push/新子代理。Root会读取输出，无需主动给其他任务发消息。保存可见指派及关键事件，最终回hash和10行内Compact结论后停止。

## 本窗可见进度消息

1. “我会在指定 checkout 读取任务约束和现有接口，完成前端规划，并将结果写入本 workstream 的 `frontend/PLAN.md` 与 `COMMUNICATIONS.md`。”
2. “已确认指定分支的基线为 `d3c4d23`，memory 配置也符合项目政策。规划会沿用文件契约和 Resolver 的权限边界，并分别说明需求配置 Agent 与后续图形前端的职责。”
3. “已核到两个影响界面的接口细节：`init` 只创建并校验项目；现有 `task resolve` 是 Skill Assignment 入口。前端需将 no-Skill 的 Capability 执行路径单独映射；无 MainState 的接入也需先核对人类提供的现存材料，不能直接显示为‘恢复成功’。”
4. “规划已成稿，列出六个近期、两个远景候选任务及各自验收条件。完成度将按控制、执行、Task 检查和 Human 决定逐项展示。接下来只做两份文档的链接、来源 pin 与写域静态检查。”

## 关键事件与实际阅读范围

| 轮次/事件 | 观察及处理 |
|---|---|
| R1 checkout核对 | `git branch --show-current` = `codex/research-entry-integration`；`git worktree list --porcelain`显示本checkout HEAD=d3c4d23206339ebc7f18b5621f3aa5453f96335e，primary另有旧HEAD。本窗所有repo读写均显式指定本checkout；未新建branch/worktree。起始status：`.codex/config.toml`已修改、RWB-RESEARCH-ENTRY目录untracked，视为其他工作，不覆盖。 |
| R1 控制输入 | 读取AGENTS、README、docs/README、DEVELOPMENT、ARCHITECTURE、workstream TASK_PACKET与README；实际config memories.generate_memories=false/use_memories=true，未写config。required-Skills=[]，本轮没有加载Skill或委派。 |
| R1 读取偏差 | 首轮primary memory的M5关键词导航匹配过宽，工具返回历史条目且输出截断；没有把该历史正文作为规划事实/接受依据。后续收窄到M5-008 own-row导航（BLOCKED/Issue123）和本checkout权威状态。该偏差保留，不能声称首轮只返回own-row。 |
| R2 module/interface | 四指定模块02/03/05/06；STATUS maturity及实现/限制段；TASKS的CLI/scaffold、M12 reservation与Topic5相关行。最初按无扩展名目录查module返回not-found，metadata发现实际为`.md`后定向读取；没有为此扩大正文域。 |
| R2 source阅读 | scaffold.py全文；cli.py的handler/parser符号、init/project-check/validate/task-resolve、context-assess/checkpoint/resume-check及异常出口；protocol/models.py的ProjectProtocol/Budget实现与类名；protocol/profiles.py公开类/方法名。没有运行上述产品接口。 |
| R2 downstream直接接口 | capability/supply.py：assess_supply符号及resolve_status实现；legacy capability/resolver.py类/函数名；execution/runtime_bundle.py、execution_view.py、host.py、generic_closeout.py的公开函数名和本规划引用的入口签名/首段；context/models.py公开对象/方法与metric常量定位。其余源码仅filename/metadata发现，未全文读取。 |
| R2 Schema/template | project-protocol、task-packet全文；agent-profile、method-resolution、capability-requirement、capability-resolution、resolved-capability-snapshot、main-state、context-snapshot、protocol-profile顶层required/fields闭集；common的fileRef/relativePath/permissions定义；examples/quickstart/task-no-skill.yaml全文。未声称读完所有嵌套Schema或Skill正文。 |
| R2 输出截断 | 部分批量工具输出超过token上限；对架构与规划所用接口随后单独定向读取。没有由截断输出推导全仓阅读或全接口支持。 |
| R3 成稿 | 只新增frontend/PLAN.md与本文件。将现有接口事实、候选UX和未验证内容分开；FE-C01～06/FE-F01～02是候选名，不改TASKS/STATUS/ROADMAP，不声称正式READY或M12解冻。 |

所有文件引用指向本checkout；源码基线由下一节的pin检查记录。既有文件是稳定来源，未把raw logs、私有API Attempt、Key、账或private oracle当输入。跨窗新消息：无；主动消息发送：无；交付由Root主动读取。

## 静态验收与交付

2026-10-07 21:34北京时间：R4静态检查完成。PowerShell解析两MD的Markdown链接，按所在目录解析本地目标，Test-Path检查路径，对带anchor目标由heading生成slug比较；结果`links=23 errors=0`。同一检查搜索机器盘符绝对路径，0命中。没有执行repo产品测试或安装。

来源核对命令：每个声明文件执行`git rev-parse d3c4d23206339ebc7f18b5621f3aa5453f96335e:<path>`与`git hash-object --path=<path> <path>`比较。22项guidance/module/source/template与11项Schema，分别`drift=0`。这是当前文件与冻结Git内容的静态一致性检查，不是产品功能或scientific correctness验证；根workstream两份输入为本地未提交文件，另按当前SHA记录，不声称它们来自基线。

Write scope：本窗工具仅创建/修改frontend/PLAN.md与frontend/COMMUNICATIONS.md。收尾status另显示`src/research_workbench/entry/`正在由其他任务新增，保留；`.codex/config.toml`原有修改和workstream其他文件保持。无Git stage/commit/push、无primary/global memory写入、无新子代理/对外消息。产品单测、CLI执行、安装、API/生产Tool、Key/账操作均为0。

结果：PLAN-FRONTEND本地规划输出已完成，候选任务/图形实现及各项产品验收尚未启动。Primary PROJECT_MEMORY的proposed entry保存在PLAN第9节，由Root决定写入。

本文件hash由交付时外部计算，避免自引用。Root应按收到的两份SHA-256重新核对，引用新内容需新的hash；本窗在最终回传后停止。

### Compact交付记录

- PLAN.md：SHA-256=`5e6380a92de3fe07f268ed7ff4cf3791cd264613cfad201b3b8525ebb31d97c9`，22536 bytes；以此固定本次规划输出。
- 结论：需求配置与图形前端分开，main决定0..N，baseline必载/Skill可选；三种bootstrap、合法格式、错误/unknown、分层完成度与独立只读Guide均已规划。
- 候选：FE-C01～06近期、FE-F01～02远景，逐项给依赖/验收；尚非canonical Task/READY，不解冻M12。
- 最终链接复验`23/23`、绝对路径0命中；另核legacy resolver符号来源与base一致，累计34项base文件pin一致（23项guidance/module/source/template + 11项Schema）。36项实际输入当前SHA持久化，其中2项workstream输入为未提交文件。
- 未执行产品测试、安装、API/生产Tool；未写primary memory；未commit/push。Root下一动作：核对hash、消费规划，并将PLAN第9节候选continuity entry按最新primary own-row情况整合。
- 本文件最终SHA仅在对外Compact结论给出，避免文件自哈希循环；后续若追加Root消费记录，必须使用新的文件SHA。

## 实际输入的当前内容SHA-256

以下为收尾时当前文件bytes的SHA-256，支持按path/hash回查；base文件另由上节Git pin核对。未提交workstream输入后续可改变，Root须重验。哈希覆盖完整文件，阅读范围仍以上表为准。

| Path | SHA-256 |
|---|---|
| AGENTS.md | 9e3b17ec2306518fd23d52fc52c3dfdb69aa8108114fe23abb4516abaa584a3a |
| README.md | 43d7c9e8d11c98ee8a56b19e3e1c449be0cdb17f49297db1eead6d420c778884 |
| docs/README.md | 4c5368332ad8a72191cf42f95f037056ba97cc51ea9f096b170fa845654de8d2 |
| docs/DEVELOPMENT.md | a8155269c627b6476467f1f019e8373a356925a53a59965637c5c44a86601d8a |
| docs/ARCHITECTURE.md | 6c952cfaca6f7072a1959633fbca99a98726eb0d1dde062f726e6e3733ed1aff |
| docs/STATUS.md | 31258d2340e2ba2c703dd619da04cdf3f6a6c74a8bfa7617d6148a23ef8d0e77 |
| docs/TASKS.md | 6a75ec90b3e88d06b894eed6b30322ddbd2770a60a093f7349b7f1244bde7e54 |
| docs/modules/02-PROTOCOL_AND_MODES.md | 0d369ba67ec836173017ca92e107975adaae2e86884c6237611133b348706bf1 |
| docs/modules/03-AGENT_RUNTIME.md | f3ad3bfb9c1c46e39a111c43a77e87bac5c934e7705ba0ecf5597069fbaa4b56 |
| docs/modules/05-TASK_AND_HANDOFF.md | 1d9123d0b9b97ee7d5bd69e24fb6a39a4eb06aa2a8e78be01f498f442f094420 |
| docs/modules/06-CONTEXT_GOVERNANCE.md | 752f9e434c842da4d83c9979701ba11edd4f6321ae28c583ef4efa40bf59567c |
| src/research_workbench/scaffold.py | da9cde15b3fbcea8d3dc43ecc70d63531f0350a5f800dbe8297091fb5606123e |
| src/research_workbench/cli.py | 8f3f1cb860d4b33f6265278a3eabd80e1e2d17d6843c8bb3db1a03cfb6168d11 |
| src/research_workbench/protocol/models.py | 87751f98db156f3eae6fdbef1a51eebea9b22abdbd210a6875d5a73dda46095b |
| src/research_workbench/protocol/profiles.py | 5054a5adc2b728adf867a9564eb7f1a09c9c9d6f4dcf5d7523391590c5e3c7ba |
| src/research_workbench/capability/resolver.py | 6b295cbf7ca38bb819556b5aff26f6d6ae30285ad8516ef3cb65fcba70311e1e |
| src/research_workbench/capability/supply.py | 8f1b5f14e9d54d8c10f0ebbbe91cca3ff78a59354b0a1506d996b6589ddec60f |
| src/research_workbench/execution/runtime_bundle.py | 5c24a3abf255f224ebf678928dc58d29741affec74ebd6c12385d5e7990a9053 |
| src/research_workbench/execution/execution_view.py | 45ca586ead6158dd8f2662516442f343429f6291e09872dea89b716fb9878be9 |
| src/research_workbench/execution/host.py | ce4044c4f59a91b5e6f89f401744957fa0df8b8e07248add0ba9808d6d7ae2c6 |
| src/research_workbench/execution/generic_closeout.py | c0ebc1d212cb25586f277728e48a315bbbc5f8f4c0677940179896284074a7dd |
| src/research_workbench/context/models.py | e601b697bd479a2144d577a89fd3116004039d8c4db0c3bfd1e63fbb2b19e5b1 |
| examples/quickstart/task-no-skill.yaml | 62920ee816005668346067bbb397ef036a2258a555a6c057e010be98c74b51a1 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/TASK_PACKET.md | a8a4b8a71f539fdb044f0fb2eb049c11e9ac3afc77888af439f26da07c41ffe2 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/README.md | a9cf67dcddfd05aba4698a20b173220b6f16c985134a214ae6461446c8b657b7 |
| schemas/v0.1.0/project-protocol.schema.json | 8c3c303e0364c1178ac3d00a3bbc215ea33603cad8c4170ae066549aa0021a43 |
| schemas/v0.1.0/task-packet.schema.json | d2ebc01795522103d09465c8af0c54f025f26b69ed41abac08793d4a75a7d24f |
| schemas/v0.1.0/agent-profile.schema.json | b01dabfe08bd5c2fbfca44192301885f10c3246f5c7b4bbfb8ac87e170433ce8 |
| schemas/v0.1.0/method-resolution.schema.json | 7a58105d95b5ad53a33dfbe2e7e3c732735edaeba5c38093a1d3612e0aae51e5 |
| schemas/v0.1.0/capability-requirement.schema.json | 0e0739fb04a9dcfd039f0df38c72b3036c05175fcf56c62314abcfceceea18f5 |
| schemas/v0.1.0/capability-resolution.schema.json | 05fc8af8468b9fa07691cf241ff8d747cda68971fee5831f591324800c39916f |
| schemas/v0.1.0/resolved-capability-snapshot.schema.json | e34e77b53ad98d5d75a74bd35110aabf3e6231c74518dbadca0fa908fff42279 |
| schemas/v0.1.0/main-state.schema.json | c05d31a93f46b16ca81632b97130ffddd7effc85ae8139aa35d6c0eb76dd9fa4 |
| schemas/v0.1.0/context-snapshot.schema.json | aeabf1ec1157cbce8240871fed27cccd4fabec510b6c75a2c9a7b4e2e007c424 |
| schemas/v0.1.0/protocol-profile.schema.json | f005fe53310df0b9d2cf1c4f8d115be54175c899d0a0b17ab0cd32c97bb70986 |
| schemas/v0.1.0/common.schema.json | f9e94daf4fd9250514d30d67a5307423ea724fe1b96fbc421c7c7c709352fa97 |
