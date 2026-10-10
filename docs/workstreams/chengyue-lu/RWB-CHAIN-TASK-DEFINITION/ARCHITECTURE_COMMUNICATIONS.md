# 架构文档校准：可见通信

本记录只保存当前AUDIT-RWB-DOCS-003的实际可见传递，不扩展读取旧任务或其他Agent原始工作目录。
顺序为实际接收/发送顺序；消息通道未提供精确timestamp，不补造时间。

## 001 Root → documentation worker：任务

最新用户扩为全文档校准与精简。切换 [当前仓库根：路径已规范化]，先读 docs/workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/DOCUMENTATION_TASK_PACKET.md、AGENTS/README。Profile bounded documentation worker，required-Skills=[]。Ownership：ARCHITECTURE、DEVELOPER_ARCHITECTURE_MAP、PROJECT_CHARTER、modules/*.md + ARCHITECTURE_AUDIT/HANDOFF/COMMUNICATIONS。通读这些 active docs，按明确引用核ADR/实现接口；补模块producer/consumer/启用条件及职责角色/会话/Skill/Profile区别，入口新建/人工既有材料共用研究流程，Guide独立只读，main动态0..N；简化重复实施历史/状态，将这些转为链接，稳定第一接触面禁exact MTask状态泄漏。保持accepted Core/owner/Human/Gate和portable baseline，不制造固定DAG或新coreRole。你不独自在仓库，保留他人。20分钟两轮，只文档编辑，不产品/API测试/Key/账/Git/安装/config/memory。保存阅读列表、问题/修复及剩余待决，不重写历史证据。

路径规范化说明：上述实际消息中的机器路径在此归档中规范化为当前仓库根；文档与Handoff引用均使用repo-relative路径。被规范化字段为任务cwd，不改变任务内容或读取/写范围。

## 002 documentation worker → Root：问题与方案

全文档审阅已发现架构地图含过期成熟度矩阵、旧任务状态/数量/历史Gate，模块03/04/05/07/09/10重复实现快照。准备把地图压缩为职责与逐跳契约导航（producer/artifact/consumer/启用条件），状态统一链接STATUS/TASKS；保留唯一Supply selection、Bundle→View→Host、Human/PhaseC/Topic5和四臂估计规则。架构/章程补新建与既有材料入口、可合并应用职责、main 0..N、Guide只读。模块05默认no-Skill示例不再要求legacy Skill-bound handoff，旧格式仅链接兼容面。PR140只作未合并候选证据，不写成develop能力。

## 003 Root → documentation worker：其他窗口更新与路径要求

Root已重写 implementation/README、PROVIDER_ADAPTER_PLAN、TESTING_STRATEGY；修正 ResearchState/SOURCE/Harness 旧‘本PR/后继BLOCKED’快照；Development适用检查与Host slice/session多turn区分；工作流/ADR索引去漂移。请你的audit/handoff只用repo-relative路径，公文档不出现本机C:/D:/。总体Markdown/公开闭包3tests已初次通过，最后交付再由Root统一重核。

## 004 documentation worker → Root：编辑进度

架构/章程/地图及10模块接点已更新，地图从661行压到约230行；各模块补producer→产出→consumer和触发条件。普通研究链与Source/Claim/MethodTrace/Need/四臂评价外环已区分，未把Guide/main职责变coreRole。模块05默认改为no-Skill有界引用检查输出，legacy mandatory Skill格式退到兼容链接；Runtime Host一次Driver与Session多轮Tool请求区分保留。正在做仅静态链接与用语检查、落盘阅读/问题/剩余待决及相对路径handoff；未运行产品/API测试。

后续实际计数为地图183行；进度消息中的约数保留为当时实际发送内容。

## 005 Root → documentation worker：总审修正

总审发现重要残留：ARCHITECTURE表Assignment写‘仅Skill-bearing路径所需→View’，模块04:145强制‘选Skill即生成Assignment’、:288未被Assignment选则正文不读，模块05对应技能锁措辞。现行M11 projection/View/Skillcloseout接口不要求Assignment；Assignment是legacy Skill-bound兼容缝，不能作为所有Skill运行的前置。请按direct implementation refs限定旧Resolver/Assignment章节为兼容，当前Skill运行用合法Projection/Supply/View exact锁及实际载入；不要只改no-Skill为空。并核模块05Task例 schema条件（Root随后Schema实测），示意不得冒称完整可执行输入。

## 006 documentation worker → Root：修正已完成

已按直接接口核对并修正全拥有域：Assignment只属legacy Skill-bound兼容缝；当前Skill运行锁是合法Projection/Supply/Snapshot/View +实际加载/consumption/Trace/closeout，不要求Assignment。模块04移除默认Assignment YAML并明确skill_facts reader只核metadata/pins、不加载SKILL.md正文；03/05/06/08/10同步修正，普通任务分派消息与Skill Assignment分开。模块05Task YAML明确为字段示意，不能冒称完整可执行输入，等你Schema实测。ARCHITECTURE_AUDIT/COMMUNICATIONS已落盘，Handoff/pins随后交付。
