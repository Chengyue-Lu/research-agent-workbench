# 下一阶段：从受控桥接到可用运行入口

2026-10-08；AUDIT-RWB-DOCS-004/005；PR141 文档候选。任务定义、状态、hard dependencies 和验收只由 [TASKS](../../../TASKS.md) 维护。本计划解释实施顺序、必要性和验证方式，合并本计划不等于实现完成，也不授权真实科研项目。

## 当前起点与目标

上一轮全文档校准与三项桥接定义继续保留。PR140 的合成隔离 API 记录证明了 intake、main 自主委派、readonly Tool、child、新 main 消费、checkpoint 和独立 Guide 的选定通路；[实际结果](https://github.com/Chengyue-Lu/research-agent-workbench/blob/22b16e6a683becb35f613f968e0e60530b2fdc90/docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/API_RESULTS.md)及[覆盖与缺口](https://github.com/Chengyue-Lu/research-agent-workbench/blob/22b16e6a683becb35f613f968e0e60530b2fdc90/docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/COVERAGE.md)绑定代码候选身份，不能作为 develop 已支持、合格 Skill 或净价值证明。本轮不重复 API 测试。

下一阶段交付是通用入口：人类提供需求、材料与授权，先按角色 Skill/提示词分流。研究需求形成内部 Protocol/Task、选择适用方法和能力，由 main 按需组织执行、消费 Handoff 并形成 MainState 与人类待决定项；询问走独立只读 Guide，局部修改走有界短程任务，针对当前主 Task 的意见沿其接点处理。新增的是主线前置层与分支面，既有研究流程保持。模型调用顺序、子 Agent 数量、输出格式和预算取决于 Task。程序负责权限、预算、文件版本、执行事实与发布边界，不代替角色规则做语义判断。

[短链设计](SHORT_LANE_DESIGN.md)与 [ADR-0024](../../../decisions/0024-UNIFIED-ENTRY-AND-SHORT-TASK-ROUTING.md)集中定义各分支接点。角色规则须版本绑定、评审并记录实际使用；不将“段落修改”等例子硬编码成永远无研究影响，也不为 Guide/短程任务强造研究 Protocol。新增五项与原十九项共二十四项真实化定义，原三项桥接继续独立。

人员分工限制按最新人类指令撤销，见 [ADR-0023](../../../decisions/0023-DEVELOPMENT-WITHOUT-PERSON-ASSIGNMENTS.md)。审查按变更风险和证据组织；不要求指定另一人参与。机器政策同步属于 M0-008，本 PR 不修改治理配置或远端 ruleset，也不宣称已完成同步。

## 缺口到任务的完整映射

下表为本轮盘点的覆盖索引，不重复 TASKS 的状态或依赖。每个 implementation slice 均应提供实际输入、产物、消费方、检查结果和剩余限制。

| 盘点范围与现有起点 | 需要补齐的桥接与必要性 | Task |
|---|---|---|
| 现行文档与机器治理曾绑定人员 | 文档撤销分工；配置、模板、CODEOWNERS 和远端审核同步另行实施，保留 PR、CI、风险和功能权限 | M0-008 |
| 入口曾把所有自然需求接到研究 Protocol | 前置分流职责绑定 Skill/提示词，按 intent/授权/目标/未知选择 Guide、短程、研究或当前主 Task；只研究路形成 Protocol，其他路不默认注入 main | M1-014 |
| intake 已能消费合法 ceilings | 自然意图/澄清与授权分别处理，生成内部 Protocol/Task；语义改写不以字面相等代替范围判定，人类无需手填完整 JSON | M1-011 |
| scaffold 和材料 refs 已有 | 从零建立研究基座；从人工杂乱文件夹、无 MainState 开始做范围内清点，标明版本、冲突与未知；两者汇入同一方法流程 | M1-012 |
| 候选以私有 caller 拼装整链 | 已安装入口、项目配置、受信工厂和 observer 可独立工作；人类交付回答目标、结果、依据、限制和决定 | M1-013 |
| 角色 baseline 已有，外部提示候选未加载 | 精细化 intake/规划/main/specialist/review/handoff/维护/Guide 职责；按需合并，版本化实际装配并审查缺输入、提示注入与交付质量 | M2-010 |
| main 已决定 0..N，但同 Profile/Method 范围较窄 | 子 Task 可按实际需求选择不同 Method/Profile/Capability；权限预算继承，主 Agent 选择是否委派及数量，并消费结果 | M2-011 |
| Projection/View/closeout 存在，入口拒绝非空 Skill | 合法正文和资源精确加载、请求装配和 actual consumption；loader 工程验收与生产 Skill 评价/准入独立 | M2-012 |
| Guide 已隔离但曾从未读 Receipt 推断发布状态 | 区分缺失、仅有引用、已检查和检查失败，按批准证据解释；只读并与主执行上下文独立 | M2-013 |
| Guide 可询问但没有同级局部编辑职责 | 最小 Task/能力/预算下独立执行获准修改；写前核权限/版本/活动输入冲突，写后消费影响评估，不直接改 MainState 或指挥 child | M2-014 |
| 小 UTF-8 输入与 compact child refs 可用 | 多格式材料分段、受控检索、大 Tool 结果外置、必要子工件回查；实际引用重新冻结，避免全部原件进入 main | M3-010 |
| provider 异常停闭，未实现通用修复 | 区分格式/内容问题、输入漂移、未知费用、Tool 副作用与研究未知；保留 partial，按 Task 预算定向修复与重新验收 | M3-011 |
| checkpoint 继承状态且历史引用增长 | 当前 Task 内整理短 MainState、已关闭风险与历史索引，人工显式新 Task 消费；自动 rollover/resume/recovery 留在 Topic 5 | M3-012 |
| 局部编辑大小不足以判断研究影响 | actual diff/hash/ref 检查与角色规则语义判断共同形成 none/relevant/unknown；必要时提交当前版本绑定的状态提案，经人类采纳再受控写入 | M3-013 |
| Bundle root/View binding 已有，root 不等于 cwd | 观察真实 cwd、可执行文件、依赖锁与 Tool 环境；工程产物重建用实际环境身份，缺依赖或漂移不能当成功 | M4-006 |
| Source/Evidence/Claim/Run/Method Trace 各有消费者 | API 工作结果真正进入这些研究对象，支持/反证/限制和实际 Run pins 可定位；summary/checkpoint 不冒充 Research State | M4-007 |
| 1024 output、6 calls、120s、32KiB 是试验入口限制 | 用模型能力、项目政策、Task 与剩余预算交集配置，区分 token/bytes/time/calls；预占合理、actual/failed/unknown 累计，不继承演示常量为产品规则 | M6-011 |
| generic ClientTool 有接口，当前入口 readonly | 实际 read/write/execute/search handler 接入路径、进程和网络约束；保留产物、partial 和副作用事实，标签变化不等于实现 | M6-012 |
| Authority evaluator 核 asserted facts，不证明事实/提交 | 从 Registry、义务、Snapshot 和验证结果生产事实，再提交具体 Method/Binding 决定，区分 proposal/eligibility/decision/execution | M8-006 |
| Resolver 选择显式供给，caller 提供 catalog | 受控发现和可用性记录；坏候选逐个排除，选中供给必须合格；多个合格候选仍按现行歧义规则，不能 pick-first | M9-007 |
| Host 检查输出形状/引用，Receipt 仅 execution slice | Task 选择真正工件与完成检查，必要时语义复核；采用有用 partial 并判断 parent goal；独立评估不将 Receipt 改写为科学接受 | M11-009 |
| 模块及选定合成链已有证据 | 通用配置驱动的真实化工程整链 Gate，逐桥展示被实际消费的内容、失败和人类边界；不把 M5 评价或复杂案例强塞为入口前置 | M11-010 |
| 多 API 试验尚未形成统一对话消费入口 | 单入口按 route/target 投递最小上下文至获准会话，聚合结果与统一累计费用；Guide/短程不默认通知 main，child 改动仍由所属 main/Task 协调 | M1-015 |
| 主研究 Gate 未覆盖新增前置层及旁路 | 独立验证询问、局部编辑/影响提案、混合需求、当前主 Task、新研究、活动冲突及 child 隔离，实际上下文和 State 前后事实须可复核 | M11-011 |

## 实施批次与可并行范围

批次是排程建议，不是研究 DAG，也不覆盖 TASKS 的精确依赖。PR 可原子集成已定义的耦合切片，但每项保留独立提交、验收证据和完成判断。

1. **基础接口。** 先做 M0-008、M4-006、M6-011、M8-006、M9-007 及前置路由 M1-014；原 M1-010/M2-009/M11-008 先按候选代码和完整 Task 验收查缺补齐，不能从 PR140 的局部成功直接置 DONE。M11-008 的 no-Skill/direct Tool Core 全桥可独立收口，Skill 缺资格的阻断必须证明；不等待未来 loader，也不宣称实际 Skill 已验收。合格 Skill 正路径由 M2-012/M11-010 完整闭合。基础项读写范围可分开；共享契约改动串行协调。
2. **实际选择与执行。** 依拓扑推进自然需求/两种初始化、角色指令审查、不同 child 路径、真实 Skill loader、Guide 与写入/执行 Tool。必载角色规则承担最低职责，可选 Skill 补具体方法；无 Skill 路径独立可用。真实 Skill 供应不足时保留支线阻断并继续合法 no-Skill 工作。
3. **有效交付与持续材料消费。** 补 Task 内容检查、大输入与证据回查、partial/定向修复、短 MainState 和研究对象接合。格式错误可有预算内局部修复；权限不足、input drift、费用 unknown 或已有外部副作用不能当普通格式错误重跑。
4. **安装入口与研究整链 Gate。** 用已安装包、项目配置和受控工程材料接通 M1-013/M11-010；从0与人工材料两个入口，任务应实际改变合法 Mode/Tool/Skill/Profile/子任务选择。先验通运行体系，后续真实复杂研究和净价值评估分别另立执行范围。
5. **前置层与长短路汇合。** 按精确依赖完成后置影响 M3-013、独立短程 M2-014，再以 M1-015 汇合已安装研究入口、Guide 和短程。M11-011 验证统一入口实际投递/隔离和状态消费；它追加分支覆盖，不倒置为原 M11-010 的前置，也不重构既有研究主线。

每次激活后继项先核 TASKS deps。应用层增加合法 producer/consumer 可复用既有契约；改变核心对象身份、选择/歧义语义、人类决定边界或 Runtime 权威时，先完成对应版本/ADR/R2，再实施，不以任务表自动接受方案。

## 保留、移出默认流程与待决定项

| 类别 | 实施处理 |
|---|---|
| 临时数值和固定编制 | 1024、6 calls、120s、32KiB、同 child Profile/Method、单轮与固定角色序列改为适用配置/能力；当前测试记录保持原值 |
| 输出、检查和修复 | 机器控制记录在内部校验；真实工作工件按任务需要选格式/检查。定向修复次数由风险与预算政策决定，不输出无关固定文件，不把 hash/schema PASS 当内容正确 |
| 重复重放与全局阻断 | 普通请求只做适用使用边界检查；完整 cold replay 在审计、版本/资格变更或正式接受时运行。未选中坏候选可隔离，选中供给和实际使用边界仍需验证 |
| 不可降低的功能边界 | 人类授权、数据出口/副作用、精确内容版本、选中供给资格、累计预算与 unknown holds、来源/Claim/Skill/发布的适用接受条件 |
| 尚需独立语义决定 | 多合格供给自动排名；歧义自动裁决；全局方法选择 blanket Human Gate 与条件化机器提交的适用区分；自动 context rollover/resume/recovery；任何核心表示改变 |

## 验证和可读交付

每个 Task 先跑与新增行为相关的确定性正反检查，再按明确 grant、时间窗、现行 source/config/credential refs 做需要的实际 API 验证。测试配置作为配置记录，不生成通用上限。一次工作流可以包含多个 API 会话，子 Agent 数量由 main 在授权内决定。全部实际失败、unknown 和未开始事实保留，费用不因新 Task/Attempt 重置；本轮文档提交不发付费请求。

工程 Gate 的最小可读交付应包含：输入目标与材料；本次启用模块/角色/Mode/Skill/Tool 及理由；实际产物与内容片段；逐桥 producer→consumer 和检查结果；实际费用/失败/partial；MainState 与人类决定；未读/未验证项。JSON/Trace/Receipt 是可复核附件，不能替代读者能理解的结果报告。

研究入口接受同时检查两类初始化、至少两个需求引起的不同执行选择、无子/有子及不同 specialist 消费、真实 Tool 副作用与预算停、内容失败的定向处理、大结果回查、Guide 事实保真，以及安装包不依赖私有 harness。Skill 路径须另有实际合格供给；缺供给时明确工程 loader 通过与真实 Skill 尚未验证，不能将整项 M11-010 记 DONE。追加分支按短链设计检查实际角色规则版本、路由理由、授权/context、diff/check、影响/采纳和通知；无影响且 refs 有效的局部编辑不改变 MainState 或 main 上下文。上述是受控工程接通测试，科学主张与真实项目准入另行决定。

M5 四臂/盲评/Pilot 与 net benefit，Mode/Skill 准入，后续复杂研究，M12/Topic 5 自动连续性，M13 策略和每次 release 均保留独立 Gate。人工新 Task 显式消费获准 MainState 不构成自动恢复；需要自动迁移/恢复的部分停止在 Topic 5 architecture review/task-definition 前。
