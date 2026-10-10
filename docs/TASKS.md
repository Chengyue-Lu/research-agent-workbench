# 实施任务清单

状态：`DONE / IN_PROGRESS / READY / BLOCKED / PARKED`

2026-10-08 用户取消固定人员分工与指定人员签字限制，由用户承接后续开发安排。本页的新任务定义和
风险/阶段索引不分配人员；基线中的既有 `DONE` 行逐字保留，其人名、双方接受及签字要求仅是历史验收记录，
不构成未来任务的人员限制。移除分工不移除 Task、PR/CI、权限、风险、Human/科学接受或发布边界。
机器治理与人员政策的对齐结果见 M0-008 既有 DONE 行；本轮不修改配置或远端门禁。

本文件是唯一 implementation-level source of truth。Phase 只表示宏观成熟度与解冻 Gate，Topic 只表示
架构责任域，M-group 表示 implementation family / development route，`Mxx-yyy` 才是可执行的原子 Task；
branch、PR、CI 和验收必须绑定 M Task。若架构文档出现近期工作而本文件没有对应 Task，
实现者必须停止并先走 `task-definition`，不能从 Phase/Topic prose 自行生成施工范围。

```text
Phase   = macro maturity / architecture Gate
Topic   = architecture responsibility / authority domain
M-group = implementation family / development route
Mxx-yyy = atomic executable Task
```

M-group reservation 只预留未来可能使用的 family namespace，不是 Task，也不属于下述状态机。施工总览见
[M-series Implementation / Construction Map](M_SERIES_IMPLEMENTATION_MAP.md)；精确状态与依赖仍只看本文件的
Task 行。

状态严格解释为：`READY` 的全部 hard dependencies 已 `DONE`、现在即可合法开始；`BLOCKED` 仍在计划
路径但至少一个 hard/external condition 未满足；`PARKED` 不在当前执行队列；`IN_PROGRESS` 必须确有
active implementation；`DONE` 只表示既有验收及证据已经接受，且行内容不可变。

本轮 Topic 映射使用 accepted architecture 中已有的责任名称。当前 `develop` 只正式使用了 Topic 4
（Agent / Model / Provider / Runtime）与 Topic 5（Execution / Context / Handoff / Recovery）的数字标签；
其他责任域使用名称而不擅自补编号。Topic mapping 是导航，不新增人员授权条件或改变 architecture authority。
原三项桥接及真实化/短链后继继续保留。本轮新增 M1-016/017、M2-015、M3-014/015 和 M6-013；
定义接受与实现验收分别进行。统一入口先分解关联意图，只有 research 路由进入研究 Protocol 规划；
精确状态和依赖仍只由下列 Task 行维护，风险/Phase 索引不复制状态。

前置层/Guide/Short 扩展保持既有研究主链。通用职责规则见[短链设计](workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/SHORT_LANE_DESIGN.md)：
具体意图、路由与语义影响由版本绑定、评审的角色 Prompt 或 Skill 承载；程序独立核契约/权限/diff/hash/ref并记录实际用量，
不代替语义判断。Prompt/Skill 路线可选，选择 Skill 时满足其实际加载/资格；职责可合并，无固定角色/API 数量。

预算整改依据见 [ADR-0027](decisions/0027-USAGE-RECORDING-AND-MODEL-WORKING-INPUT.md)。通用产品采用程序记账、模型最小工作输入，
不要求经济额度、不默认 budget preflight 或模型预算管理。当前代码仍使用旧强制预算契约，迁移由 M6-013 独立实施，
已有桥接按其实际版本验收且明确旧行为；新的无额度产品路径由 M11-010 消费迁移证据。旧 DONE、固定 live grant
和 M5 冻结比较条件不静默重解释。Codex 机制对照留在 Issue #18，不是 M Task、依赖或验收前置。

## M0：架构与仓库

| ID | 状态 | 任务 | 验收 |
|---|---|---|---|
| M0-001 | DONE | 冻结产品定位与非目标 | Project Charter 完成 |
| M0-002 | DONE | 确立总体架构与模块边界 | 总架构 + 10 模块文件 |
| M0-003 | DONE | 将不同 Agent—Skill 绑定纳入架构 | Resolver、Assignment、预警与验收明确 |
| M0-004 | DONE | 建立实施、迁移与测试计划 | 三份实施文档完成 |
| M0-005 | DONE | 创建并推送独立 GitHub 仓库 | `main` 可访问，首次提交完成 |
| M0-006 | DONE | 建立零基础使用与发布就绪度指南 | 安装、离线 quickstart、真实运行边界、故障处理和分级发布 Gate 可由新用户顺序阅读 |
| M0-007 | DONE | 选择项目许可证并核对仓库原创 Skills 的许可状态 | 人类维护者确定发布许可后加入 LICENSE，并消除 `project-original-unlicensed` 发布阻断 |

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M0-008 | DONE | 对齐机器治理与模板中的人员限制 | M0-004, M7-001 | 在独立 feature 中移除固定 owner 映射与跨指定人员门禁，核对治理器、模板和实际适用门禁；保留 Task/PR/CI、权限、风险及发布边界并给出正反证据。本次定义不声称已修改代码、配置或远端 |

## M1：契约与 CLI

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M1-001 | DONE | 初始化 Python 包、pyproject 和基础 CI | M0 | 已合并 `main`；Python 3.11/3.13 GitHub CI 通过 |
| M1-002 | DONE | 实现核心对象模型与 JSON Schema | M1-001 | 7 类对象正反 fixture 通过 Draft 2020-12 Schema |
| M1-003 | DONE | 实现 Protocol、Mode、Profile、Skill Manifest | M1-002 | 能力、工具、输出、模式、冲突和 scoped permission 可验证 |
| M1-004 | DONE | 实现 Task、Attempt、Handoff、Main State | M1-002 | completed/incomplete Handoff、Attempt 与 checkpoint 示例通过 |
| M1-005 | DONE | 实现引用、revision、SHA-256 和 stale 检查 | M1-002 | 修改输入触发 `REF-HASH-MISMATCH`，input lock 不同触发 stale |
| M1-006 | DONE | 实现最小 CLI | M1-003..005 | init/validate/resolve/handoff/trace/checkpoint 可用 |
| M1-007 | DONE | 建立确定性风险检查 | M1-004..006 | Skill 缺失、越权、写冲突、Claim overreach、stale 注入均阻断 |
| M1-008 | DONE | 冻结模型 API 中立端口与能力协商语义 | M1-001 | Capability/Data Policy gap 在调用前阻断，提供商基线可查询 |
| M1-009 | DONE | 建立外部可复用项目 scaffold 与 `0.x` 兼容政策 | M1-006 | `rwb init` 可生成或选择完整模板；新项目不需手工复制 Registry/Profiles/Skills；Schema/CLI 迁移与废弃规则明确 |
| M1-010 | IN_PROGRESS | 通用研究入口的受控需求与材料接入、契约产物桥接 | M1-003, M1-004, M1-005, M1-007, M8-003, M8-005 | 声明自然语言需求/材料及独立人类权限与读取范围，实际 intake 请求与模型输出经现有契约验证形成 Protocol/Task/Method/Requirement 草稿；Capability 冻结与 Bundle/View 消费本次 producer 返回的 exact refs；拒绝无效 JSON、未知 Mode/Action、缺 Method 依据、范围/权限扩大、未授权材料与 hash drift，Human Gate 未决保持阻断；材料接入及 Source/Evidence/Claim/Method Trace 按显式场景触发并检查直接消费者；交付可复用 caller、可读输入输出/消费表及正反证据；不要求人类提供经济额度或模型编写预算，预算字段/请求投影的新版本迁移由 M6-013 实施，已有桥接须标明实际使用版本，不冒称新默认路径已通；不替代科学方法判断，不改 Core 身份/Registry/Human authority，不自动恢复旧会话 |
| M1-011 | PARKED | 自然意图澄清与内部 Protocol/Task 编译 | M1-010, M8-006, M9-007, M1-014 | 仅 research 意图生成或修订研究 Protocol/Task，其他路由使用独立局部契约；消费 M1-014 的原请求对应、共同/局部限制及显式跨意图依赖，缺少影响投递或执行的信息时有界澄清；AI 可重写/选择草稿语义，权限与范围上限独立保留；模型工作输入不默认包含额度、余额、账本或预算分配职责，完整控制对象和执行元数据由程序装配；实际编译产物及 unknown 被下游消费，不要求人类手填完整 JSON，不将草稿冒充批准 |
| M1-012 | PARKED | 从零与无 MainState 材料的研究基座初始化 | M1-011, M4-001 | 从零项目与杂乱文件夹两种入口共用方法流程；显式范围、文件版本、冲突、未知和获准 refs 进入研究基座；无 MainState 不补造历史状态/接受，给出两类实际输入输出及越界反例 |
| M1-013 | PARKED | installed 通用入口、配置和人类交付 | M1-012, M2-010, M11-009 | checkout 外安装入口以公开配置调用实际 producer/consumer 并交付可读结果、refs、限制和下一动作；复用已有 Provider 能力配置和执行事实，不等待 M6-011 的增强记录；完整 research 与旁路消费由 M1-015 接合，单 CLI 不等于统一聊天全路由已通；不依赖 Root 私有 harness、checkout imports 或手拼运行产物；成功、缺配置和不支持路径证据完整；实际版本与 M6-013 迁移边界可见 |
| M1-014 | READY | 研究 Protocol 之前的关联意图分流 producer | M1-004, M8-005 | 消息、项目授权和最小当前 Task metadata 进入角色规则判断，输出关联意图及原文对应、目的/对象、route/目标、共同与局部限制、依赖/冲突、结果入口和逐项未知；记录实际 Profile/Prompt 或 Skill 版本/hash、理由及读取允许集；区分 Guide、short-edit、research 与明确目标的 current-main-steering，明确项可先投递，真正影响执行的歧义才澄清；仅 research 进入 Protocol；不先遍历记忆库，不默认通知 main、投递任意 child 或加载预算账本；关联 request/intent/Task/Attempt 标识不互相替代，路由不产生权限、供给选择或状态接受 |
| M1-015 | PARKED | 统一对话入口与逐意图隔离 caller 投递 | M1-014, M1-013, M2-013, M2-014 | 按关联意图分别核已批准对象、recipient、权限与供给绑定后创建隔离会话，保留共同/局部限制及依赖；各项独立状态/结果，已完成项先交付，依赖失败的操作等待，只有用户要求或父目标需要时综合；共享显示不拼全聊天，不给 Guide/short 原主聊天，不自动 main 回传；current-main-steering 只向明确 Task 的治理接点投递，children 仍由 main 控制；route/message/实际 API/产物可核，用量由程序关联累计且未知不填零，不以额度、预占或账本缺失阻断；native/web Adapter 不锁平台，不造全局 Supervisor/message bus/continuity DB |
| M1-016 | READY | 运行事件增量读取与事实状态快照 | M3-008, M6-006, M11-004 | 消费已有 Trace/session/runner/observer actual facts，提供 request/intent/Task/Attempt、父子关系、阶段、操作、序号/时间、工件和待决定项的增量读取/快照；重读可定位缺口、重复与未知，缺完成事件不推定完成；实测当前实际 runner 的事件消费者，事后 sidecar 与已记录演示明确标注，不能称实时；无隐藏思维链、第二事实库或调度器，记账字段缺失不阻断事件显示 |
| M1-017 | PARKED | 基础只读运行前端 | M1-016 | 用事件/快照显示意图/任务/方向卡、时间线、成果、异常、实际用量与待决定项；刷新/断连重读不改变后台任务或重放副作用命令；关闭解释模型仍可见事实，已记录演示明示来源，实时验收接实际 runner；不提供尚未实现的操作按钮，后续操作只消费 M1-013/015 合法入口，不等待全路由首次显示 |

## M2：Agent 与 Skills

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M2-001 | DONE | 实现 Skill Registry 与 Resolver | M1 | accepted Registry、最小覆盖、显式选择、冲突、权限交集、版本/哈希锁与确定性 Assignment 已测试 |
| M2-002 | DONE | 定义四个 Agent Profiles | M2-001 | coordinator/evidence/simulation/reviewer 的权限、工具、输出和上下文边界可验证 |
| M2-003 | PARKED | 创建 literature-evidence-extraction Skill | M2-001 | `0.1.0` 已冻结为 legacy；结构证据保留，不再作为新任务默认 Skill，后续只由 Mode-derived Need + Trace 重新激活 |
| M2-004 | PARKED | 创建 simulation-vv Skill | M2-001 | `0.1.0` 已冻结为 legacy 并按 action 拆分；真实数值案例不得继续验证 broad bundle |
| M2-005 | DONE | 创建 handoff-integrity 检查 | M1 | 确定性脚本已验证 Task/input/Skill/artifact 交接边界，不宣称科学正确性 |
| M2-006 | PARKED | 扩展 Codex Runtime Adapter | M2-002, M2-005 | 已有 Agent/Skill 发现、验证和显式 dispatch 保留；平台 launch/collect 不在当前 Mode–Skill 关键路径 |
| M2-007 | PARKED | 执行首个双 Skill 垂直切片 | M7-002..006, M7-008 | 历史离线切片可精确 replay，但两个 broad Skill 均已 legacy；真实执行改由 Need + M3-008 路径重新定义 |
| M2-008 | PARKED | 建立外部 Skill 发现、隔离评估与准入 Registry | M1-005, M1-007 | 73 条候选和 11 个来源的可追溯库存已形成；停止来源驱动扩张，后续 dossier/trial 只由 Mode-derived Need 与 Trace Gate 激活 |
| M2-009 | IN_PROGRESS | 角色必载指令与有界 0..N 主子运行消费 | M2-002, M1-004, M2-005, M3-008, M6-002 | 每个启用角色实际载入 baseline/Profile/exact Task/input refs；main 实际决定 0 或多个 child，调用前验证整 wave 的权限/深度/输出冲突；fresh child 输出及有权工件 refs 进入新的 main 消费请求；程序记录 intake/main/children 的 actual usage、failed/unknown 与 wall time，不要求模型规划整链/子预算，模型输入去耦和旧字段迁移由 M6-013 实施；required Skill 未加载阻断，候选提示词不产生 admission；独立 Guide 仅消费 approved refs、无科研写入或自动回传；交付可读角色输入输出与关键失败证据，不固定角色编制、增加 Supervisor 或解冻 Topic 5；旧版本运行与新默认验收分开 |
| M2-010 | PARKED | 角色 baseline 与工作输入实际装配审核 | M2-009 | intake/planning/main/specialist/reviewer/handoff/maintenance/Guide 及分流、短程、影响职责按需组合；按必载职责与权限、当前 Task/状态、必要决定/反证 refs、可选经验导航、原始依据装配工作集，记录实际交付内容的范围/版本/hash和已知缺口；必载职责不依赖记忆命中，资料指令不提升权限；不默认注入预算余额/账本或要求模型分配额度、报告猜测用量；评审优先级、注入、缺输入、语义判断与输出质量，必载规则与可选 Skill 分开，不新增固定 coreRole；不建设记忆存储或强制调用维护 Agent |
| M2-011 | PARKED | main 自主委派与逐 child 方法、Profile 和能力选择 | M2-010, M8-006, M9-007 | main 自主决定 0..N，按实际子目标选择不同 specialist、Method/Profile/Capability 并逐 Task 冻结；继承授权和读写边界，actual child 内容/refs/失败被 main 消费；为 M2-015 提供父目标、分叉基线、局部资料/工作区及接收方的应用交接接点，程序关联消耗而不分配强制子预算；不强制复制父 Method、默认增设 branch-main Core Role 或把选择权交给 Host |
| M2-012 | PARKED | 合格 Skill 精确加载与实际使用消费 | M2-010, M11-007 | 合法选中 Skill 的 exact 正文及必要 resource 受控加载进入实际请求，use-boundary facts 被 Trace/closeout 消费；candidate/oracle 隔离、漂移/缺正文阻断；空 index 不假装真实 Skill 供给，真实路径的独立准入仍是前置，不伪造 Release |
| M2-013 | PARKED | Guide 可见证据状态与解释验收 | M2-010, M11-008 | 独立只读 Guide 区分 ref 存在但未读、已检查、失败和缺失，依据实际可见证据及当前阶段/快照版本解释状态、等待原因、限制与下一项人类决定；核对回答完整性及不越过证据的解释质量，资料陈旧可识别；关闭或失败时基础状态/成果仍由事实读取端提供，无项目写入或自动 main 回传；mutation 建议转请求 route，明确采纳后才成为 main 新输入；不新增常驻监控、自动推送、全日志轮询或执行权限 |
| M2-014 | PARKED | 与 Guide 同级的独立短程编辑职责 | M1-014, M2-010, M6-012, M3-013 | 最小有界 Task、适用 no-Skill/direct Tool 控制、输入 pins、write scope 与输出检查驱动隔离 caller；普通局部修改不逐次造研究 Protocol/Mode，实际载入获准角色规则；真实编辑、检查与后置影响评估闭合，当前 main/child 写锁或冻结输入冲突先停写；保留产物、失败、程序记录的 usage/unknown 与副作用，不以预算核准为前置；无全局状态/发布/权限 authority 或任意 child 操控入口 |
| M2-015 | PARKED | 活跃任务内的单层方向分支与成果接收 | M2-011, M3-012, M11-009 | 用现有 Task/Handoff 组织可选方向，记录父目标、分叉基线、允许变量、资料范围、局部工作区、停止和返回要求；共享只读依据、候选写隔离，不注入兄弟聊天，不要求预算份额；各方向可使用获准普通 child；父任务比较共同基线/当前状态/候选变更，分别完成文件合并与科研判断采纳，保留分歧/未采纳经验来源；反馈精确关联方向并经所属 main，不新增持久 Core branch identity、直接 child 控制权、递归搜索或自动恢复 |

## M3：上下文与风险

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M3-001 | PARKED | Main State checkpoint/resume | M1-004, M1-005 | 规范化 digest、原子文件发布、Continuity 状态、机器证据哈希、Git 基线、下一动作和约束/决定丢失检查已通过；进程级 kill 矩阵与真实新主会话恢复待演练 |
| M3-002 | PARKED | context pressure 观测与工作集接续条件 | M3-001 | 保留可测/未知上下文指标和已有 checkpoint 实现证据；后续区分实际模型窗口、相关性与来源完整性，不默认以估算 next-AWU/closeout/reserve 余额阻断任务或要求模型自算余量；旧预算阈值行为按原版本兼容记录，新的工作集优先级保持有效决定与反证；自动 rollover/恢复仍待 Topic 5 独立接受，真实压力与接续证据待采集 |
| M3-003 | PARKED | Handoff loss/stale/summary 抽查 | M1-004, M2-005 | Transfer Manifest/Audit、负面区段覆盖、风险触发抽查、Context/Receipt 绑定已实现；真实 H1/H2 成本与人工样本仍待执行 |
| M3-004 | PARKED | review loop/fanout/write race 观测与冲突检查 | M2-002, M2-005 | 保留已有 review loop、协调成本与 write race 证据；程序观测重复展开/调用和实际并发能力，权限、活动写冲突与明确停止条件分别处理；不以并发费用份额或未知记账数据默认阻断，也不要求模型自管额度；旧硬预算规则留在显式兼容范围，真实冲突/取消行为待验证 |
| M3-005 | PARKED | 敏感 trace 策略 | M1-007, M2-005 | 外部/完整/敏感 trace 会阻断或警告；真实脱敏器与密钥 fixture 待实现 |
| M3-006 | PARKED | SAFE_PAUSE 与机器完成权 | M3-001, M3-002, M3-003 | AWU/完成/暂停条件、stage/safe-pause/waiting、执行结束与 `contract-satisfied` 分离、失败报告覆盖显式完成宣称和可恢复 pause fixture 已实现；进程级 kill 与真实新进程/新 Attempt 恢复待演练 |
| M3-007 | PARKED | 冻结实名 actor、Attempt Archive 与完整 Agent Trace 规则 | M3-003, M3-004, M3-005, M3-006 | ADR-0012、目录、消息信封、写前捕获、capture gap、按需读取和 Worklog 关系一致；actual actor 身份和 Archive 归属可追溯，不固定人员分工 |
| M3-008 | DONE | 实现 Trace Envelope/Index/Event Schema、validator 与手工 fixture | M3-007 | 文件权威 Trace Core、确定性 validator、瞬时 tool-result provenance、Python 3.11/3.13 CI、覆盖率、Registry、wheel 与干净安装 Gate 均通过；不保存 Chain-of-Thought |
| M3-009 | DONE | 在 Execution Trace 之上增加 Method-aware Trace | M3-008, M8-003, M8-005, M9-005, M10-001, M10-002 | 建立独立、ref-only 的 Method Trace v0.1，记录 applied Method/Human Decision/State/path disposition；没有 accepted execution fact producer 时显式记录 actual-binding gap，且不得把 selected Snapshot 当作 actual execution 或把 gap-valid 写成 coverage-complete |
| M3-010 | PARKED | 多格式大输入、Tool 结果外置与按需证据回查 | M1-012, M2-009 | 多格式大输入和 Tool 结果有 exact 外置 refs，条目/专题导航支持范围过滤、必要决定及关键反证直接定位、compact child 工件回查；先精确 refs，再当前任务/方向，再项目专题，按必要性扩大范围；新增获准 refs 经重冻结后消费，不扫全仓；给出实际选取/遗漏/回查、模型实际容量不足、缺失/漂移及缓存源版本证据，不用经济额度决定应看到的关键依据，不自动 context rollover |
| M3-011 | PARKED | partial 结果、失败分类与定向修复 | M6-012, M11-009 | 区分可用 partial、不可用失败、内容错误、输入漂移、记账 unknown 与副作用；在原授权/适用停止条件内按实际失败原因定向修复并重新验收，保留原失败及实际消耗；费用/token 缺失单独 unknown，不单凭记账缺失否定有效交付或阻断下一步，执行事实或响应缺失仍独立判定；不因记账 unknown 自动重试，不采用全局固定一次或无条件无限 retry，不在 Host fallback，不实现 Topic 5 恢复 |
| M3-012 | PARKED | 当前 Task 的精简 MainState、风险关闭与显式接续读取 | M1-012, M11-008 | MainState 为当前协调视图，保留必要目标/当前结果/限制/开放风险和历史索引，区分历史判断、模型提议、实际执行与正式接受；完成/失败来自直接事实及时更新，不等待后台记忆整理，风险关闭有实际依据；人工新 Task 按获准 refs 读取，不把 MainState 当全部记忆唯一权威；M3-013 消费本项而不反向依赖；不定义自动 head/session/context 迁移恢复、不激活 M3-001/M12，触及 Topic 5 时停在独立 Gate |
| M3-013 | PARKED | 短程 actual diff 的后置影响评估与状态采纳接点 | M3-012, M11-009 | 角色规则从 actual diff 判断 semantic none/relevant/unknown 并留理由/未知，独立 diff/hash/ref、MainState revision 与活动输入有效性检查分别留证；none 且 refs 有效、无活动输入冲突时只留局部记录，不改/不通知 main；有关/未知或坏 refs 则提案并 hold 相关发布，人类采纳及当前 pins 重查一致后受控 writer 写新 revision，漂移重评估，不暗改 Claim/权限；写前权限/冲突检查不能后置，实际活动输入失效最小通知，不解冻 Topic 5 |
| M3-014 | PARKED | 研究记忆索引与角色工作集读取 | M3-010, M3-012, M2-010 | 在实际读取/当前视图/角色装配输出上建立条目来源关系、分层导航与范围检索，表达项目/Task/方向、适用条件、修订/替换及未确定状态；按精确 refs/任务/专题读取并留实际注入清单、源版本、选择范围/缺口及检索回查用量；权限过滤、失效摘要识别、纠正传播与低频关键反证可验；记忆是资料而非系统权限或科学决定，读取不经强制维护模型，不依赖经济额度或自动恢复 |
| M3-015 | PARKED | 有来源的增量研究记忆维护 | M3-014, M4-007, M11-009 | 从已检查交付、明确纠正或方向结束的事件形成带来源/范围的增量，处理重复、替换、冲突与失效；无有用增量可不更新，不逐工具调用运行；派生条目按维护授权原子发布，模型提议/有效条件/正式接受分别可见；中断不发布伪完整结果，个人偏好不污染项目事实、限定失败不变永久禁令；维护关闭或失败时已有读取与最新原件仍可用，记录 actual/unknown 不设额度或等待 M12，不自由改变已接受科学判断/权限 |

M3-001～007 的 `PARKED` 表示当前没有 active implementation，并非抹去已经进入仓库的 bounded v0.x
能力。各行同时混有已实现 contract slice、真实运行校准和未来 Topic 5 扩展，不能继续用无限期
`IN_PROGRESS` 表示债务。Phase C closeout 前不拆分或恢复这些工作；之后必须通过新的 R2
`task-definition` 决定哪些 residual work 形成独立 Task，不能直接把旧行重开成泛化 Recovery umbrella。

## M4：工件与复现

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M4-001 | DONE | source admission 与 provenance | M1-005, M1-007 | inbox 不可直接引用；admitted source 具有 exact identity/hash/provenance，拒绝未准入引用 |
| M4-002 | DONE | work → object/run promotion | M4-001 | 只有校验通过可提升；promotion 不等于 Claim 接受或 Human Decision |
| M4-003 | DONE | Claim trace 与 counterevidence | M4-001, M4-002, M8-005 | 支持/反证/限制一次定位；validator 不代替科研判断或 Claim promotion authority |
| M4-004 | DONE | Run manifest 与复现检查 | M3-008, M4-002 | 仿真案例可由 exact inputs/artifacts/environment refs 重建；不宣称结果科学正确 |
| M4-005 | PARKED | DVC 技术 spike | 真实大文件需求 | 无需求则不启动 |
| M4-006 | READY | 工程 cwd、可执行文件、依赖锁与 Tool 环境观察 | M4-004, M6-002 | 显式区分 project root 与执行 cwd，冻结实际 executable、依赖锁及 Tool 环境身份并形成可重建记录；提供成功、缺依赖与环境漂移证据，不凭声明证明可运行，不默认自动安装 |
| M4-007 | PARKED | 工作结果到研究对象的实际消费者桥 | M1-012, M11-009, M4-003, M3-009, M10-003 | 实际工作结果按场景进入 Source/Evidence/Claim/Run/Method Trace/Need 消费者，保留原始结果、解释、接受状态、修订/替换关系及反证引用，核对 promote 条件；为 M3-015 提供合法来源与纠正事件，不强制 Guide/局部编辑产生全套科研对象；不从执行成功推导 source/Claim/Skill 接受，Research State 候选语义与人类接受独立 |

## M5：真实案例与删减

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M5-001 | BLOCKED | 冻结 Evidence-Synthesis Evaluation Case Dossier | 人类提供/批准边界 | Public package 冻结 research question、exact admitted source set、inclusion/exclusion 与 data/read boundary、required outputs、Claim ceiling、initial context 和 Task；Private adjudication package 独立冻结 required facts、counterevidence、limitations、forbidden claims、evidence relations 与 Human scoring anchors；case/oracle 在观察 treatment output 前 hash-frozen 并记录选择理由、Human approval 与 no-treatment-specific-tuning |
| M5-002 | BLOCKED | 冻结 Theory + Simulation Evaluation Case Dossier | 人类提供/批准边界 | Public package 冻结 research question、exact model/equations、assumptions、parameters、inputs、simulation environment、required outputs、Claim ceiling 与 Task/context；Private adjudication package 独立冻结 invariants、numerical tolerances、failure/convergence conditions、limitations、forbidden overreach 与 evaluator anchors；case/oracle 在观察 output 前 hash-frozen、经 Human approval 且不得事后改写 |
| M5-003 | DONE | 建立最小 Evaluation Manifest 与 baseline harness | M9-002 | 冻结 Task、Model、Host、Tool/Snapshot、预算、上下文、指标与 evidence classes；可表达 plain Agent、Tool、Mode no-Skill/direct-tool 与 candidate Skill 对照，但不保存 Need 本体中的 trial 结果，不在 lifecycle 内重建 benchmark framework |
| M5-004 | BLOCKED | 运行已批准真实案例并分析 system-level net benefit | M4-001, M4-002, M4-003, M4-004, M5-001, M5-002, M5-003, M5-006, M5-007, M5-008, M11-006, M6-010, `A4-RUNTIME-ADMISSION-GATE`（可审计外部条件） | 先复核 M5-008 具名接受的 exact source/config/live pilot 证据对本次运行仍适用；pilot 已暴露或用于调参的 case/Task/input/private-oracle 不得作为未观察 held-out，pilot runs 不得进入 primary confirmatory run set；按 frozen protocol 对 approved real cases 执行全部四臂并保持共享条件；A4 保持 M5-003 的 `mode-candidate-skill` identity，但按 candidate-origin treatment + admitted Runtime execution 运行；Gate 必须 exact-pin candidate binding、`skill_evaluation_ref`、接受该 exact candidate/evaluation 的具名 Human Admission Decision、immutable accepted Release、candidate→Release exact identity/hash 或显式 promotion/build provenance、valid SkillReleaseProjection 与 projection-backed Skill Supply，再由唯一 Capability Resolver 形成 Snapshot→Runtime Bundle→Resolved Execution View→Thin Host 的逐跳 identity/hash closure；任一缺失即保持 BLOCKED，不以 synthetic Driver/projection 作为正式 evidence；primary net-benefit conclusion 只消费 `primary_confirmatory_eligible=true` 的 held-out cases，`admission-overlap` cases 只可作为 pilot/secondary evidence；failed Attempts 保留，blind Human Review 完成，metric evidence 完整或显式 unavailable/N/A，并产生 system-level analysis；单次成功不构成 promotion |
| M5-005 | BLOCKED | 里程碑删减与 disposition 评审 | M5-004 | 至少对一个机制作出 KEEP / KEEP-WITH-BOUNDARY / MODIFY / PARK / DEPRECATE / DELETE / STOP 或 accepted 等价决定，并引用 protocol、case dossiers、exact run set、blind reviews、analysis 与 known limitations；`admission-overlap` evidence 不得作为 pruning 的唯一证据，A4 较优或 sunk cost 均不自动触发 Skill promotion/KEEP |
| M5-006 | DONE | 冻结 System-Level Evaluation Protocol | M5-003, `M5-BASELINE-TRANSPORT-ARCHITECTURE-GATE`（由 `PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND@1.0.0` 闭合） | 必须 exact-pin `docs/decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md` 及其 Gate record 中的 SHA-256；按已接受双传输固定 A1/A2→M6、A3→M11 Core、A4→M11 Skill extension，并把 `A4 − A2` 冻结为包含 transport difference 的 primary system-level estimand；`A2 − A1` 只作同 transport Tool 条件增量，`A4 − A3` 仅在 pairwise exact-equality closure 证明唯一 delta 为 admitted Skill extension 时才作 Skill conditional increment，否则降级为 Skill-bearing package / bundled effect 或 unavailable，`A3 − A2` 不得称 pure Mode effect；Decision 不等于 M6-008 实现证据，不修改 M5-003 treatment/read boundary、不给 A1/A2 注入 Mode/Method 或 dummy Snapshot，也不授予 Runtime/Method/Supply/Human authority；拥有并冻结覆盖 A2/A3 的 `ArmExecutionQualificationRecord@1.0.0` contract、Schema、comparison rule 与 fail-closed validator，要求 exact-pin Manifest/arm、Task、Requirement、frozen/runtime Resolution/Snapshot、相关 Mode/Action/Method、Supply/component/implementation/interface 与 typed live evidence，且 permission/data-egress/side-effect ceiling 只能等价或收窄；M6-008 只产生 A2 record，A3 runtime Resolution/Snapshot 仍由唯一 Capability Resolver 产生/选择，M11 只验证并消费 exact Snapshot，M5-007 引用两端对象组装 A3 record；冻结 versioned/hash-pinned `A3A4PairwiseComparabilityRecord`，逐项比较 shared case/Task/conditions、Mode/Action/Method、non-Skill Requirement/Supply/component、Tool/procedure、provider-visible interface 与相关 boundary，结果仅允许 `exact-skill-only`、`skill-bearing-package`、`not-comparable`；随后预注册 secondary comparisons、randomization、replicates、pilot/stopping/retry、model/provider drift、blinding/reveal、跨 transport metric comparability、measurement status、analysis rule 与三层 decision hierarchy；定义独立于 M5-003 v0.1 的版本化 A4 execution-qualification overlay，exact 引用 frozen candidate/evaluation 与准入后 Release→Projection→Supply→Resolution→Snapshot→Bundle→View→Host lineage，而不修改 Manifest 或产生 admission/permission authority；冻结 admission-evidence overlap / held-out policy，并定义独立、versioned、hash-pinned `AdmissionEvidenceOverlapAssessment`，exact-pin `skill_evaluation_ref`、admission case IDs、Task/input refs、typed private-oracle/checker/Human-adjudication identities/hashes、两侧 comparison input closure、`checked_at`、validator identity/version/hash 与计算结果；`absent`/`unknown` 不得解释为 held-out；overlay exact 引用该 assessment，并记录 `case_selection_frozen_at`、`admission_evaluation_ref`、`overlap_status`、`overlap_refs` 与派生的 `primary_confirmatory_eligible`；measured/estimated/unavailable/not-applicable 严格区分，blind phase 隐藏 arm/Skill/cost/token/RWB 标签，Research Integrity 退化不得由效率抵消且禁止单一 weighted aggregate score |
| M5-007 | DONE | 建立 System-Level Evaluation Harness | M5-006, M6-008, M11-004, M11-006, M11-007, `M5-SKILL-CLOSEOUT-REPLAY-GATE`（Issue #55 可审计外部条件） | 编译 frozen plan、以 fresh Attempt/session 启动 exact arms，并在 A4 执行前于 Harness/Maintainer 侧验证 versioned execution-qualification overlay 与 `A4-RUNTIME-ADMISSION-GATE` 的逐跳 identity/hash closure；在 confirmatory freeze 前加载 `AdmissionEvidenceOverlapAssessment`，验证其 exact Evaluation/validator/input pins 与 `checked_at <= case_selection_frozen_at`，从 assessment 两侧闭包独立重算 M5-001/002 case / Task / input / private-oracle intersection、status 与 eligibility：缺失、`absent`/`unknown` 或未闭合即 fail closed，任一重叠必须记录为 `admission-overlap`、列入 `overlap_refs` 且令 `primary_confirmatory_eligible=false`；无解释的 candidate/Release substitution、hash drift 或 Resolver 选择其他 Supply 也必须 fail closed，Runtime 不读取 candidate/evaluation/lifecycle history；A1/A2 必须消费 M6-008 的 allowlisted treatment-visible baseline envelope 与 replay-valid closeout；正式 A2/A3 必须加载并用 M5-006 validator 独立重算 exact `ArmExecutionQualificationRecord@1.0.0`：A2 record 由 M6-008 产生，A3 runtime Resolution/Snapshot 由唯一 Capability Resolver 产生/选择，M11 只验证并消费 exact Snapshot，且 record 只由 Harness 在 Maintainer/Evaluation preflight 组装；两者均须证明 frozen structural binding 与 runtime-execution binding 的 Task/Requirement/Supply/component/implementation/interface 及相关 A3 Mode/Action/Method 未替换、所有 ceiling 未放宽，并拒绝 `structural-replay`/`execution_input=false`/fixture-only binding；在 plan/pre-run 与 analysis input 阶段加载并独立重算 `A3A4PairwiseComparabilityRecord`，只有 `exact-skill-only` 才可标注 Skill conditional increment，`skill-bearing-package` 必须降级为 bundled/package effect，`not-comparable` 令该 secondary contrast unavailable；预注册 exact equality 后发生 drift 必须 fail closed，当前 Method/Supply disposition incompatibility 不得由 Harness 掩盖；A3/A4 分别消费 M11 Core/Skill extension，Harness/M6-008 不取得 Supply selection；Harness 不得把 raw Task control、dummy Method/Snapshot 或 Skill Assignment 注入 plain arms；以 M11-004（传递 M11-003）的 Core Host actual-fact / Trace / generic-closeout contract 和 M11-006 Skill mapping 为明确输入，执行后必须由 typed execution fact 与 replay-valid Receipt 独立证明 actual Projection/Supply/binding 与 overlay 相同，区分 completed、post-call failed 与 preflight blocked，禁止用 planned View 冒充 actual facts；`M5-SKILL-CLOSEOUT-REPLAY-GATE` 必须先接受 projection-backed Skill actual binding 的 replay-valid closeout seam，或由 R2 正式修订本 Task 验收，不能把 M11-004 Core Receipt 假写成已经支持 Skill；Harness 只能在不改变 arm treatment/read boundary 的评价记录层统一 evidence，闭合匿名化、metric evidence、Human Review、reveal map 与 analysis input，不得 special-case A4、直接加载 candidate 目录、在 confirmatory run 使用 synthetic projection、自动 promotion/pruning/Human scoring；harness implementation 不等待真实 case data，正式 execution 留给 M5-004 |
| M5-008 | BLOCKED | Live Evaluation Pilot Gate | M5-007, M6-010, `A4-RUNTIME-ADMISSION-GATE`, `M5-LIVE-PILOT-AUTHORIZATION-GATE`（可审计外部条件） | 在完整 Harness 验收后，按[Live Pilot Gate](workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-008_LIVE_PILOT_GATE.md)冻结独立、Human-approved pilot dossier/Protocol、exact source/config、四臂 run set、预算/retry/stopping 与具名 API/数据/Tool 授权；真实 A1/A2→M6、A3→M11 Core、A4→M11 Skill，A2/A3 runtime qualification 与 A4 accepted Release→Projection→Supply→Resolver→Snapshot→Bundle→View→Host 全链重验，禁止 synthetic/fixture 替代 live；每臂/retry fresh Attempt/session，实际触发冻结的 Provider/Tool/procedure，完成预注册 pilot run set 且至少一个完整四臂 block；保留全部失败、费用与停止，use-boundary actual facts→Trace/Receipt 独立 cold replay→blind Human Review→reveal/metric/analysis input 闭合，负例验证零调用阻断、post-call failure/retry/budget stop 与篡改拒绝；复核 exact implementation/config/run set 与验收证据后才提议 DONE，不限定复核人员；pilot observations 只作工程诊断，不产生 confirmatory net-benefit conclusion，不进入 primary confirmatory run set，不自动准入/promotion/pruning，不替代 M5-001/002 或 M5-004 原有 Gate，影响执行/证据链的变更必须重新验证其适用性 |

M5-006 的 exact Decision pin 为
`docs/decisions/0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md`，raw SHA-256
`64edd73c44bc77f326a90c51e0a8cbf5fd28c4bbf1a5e18aca7f50250ce21a12`；该值与 Gate record 不一致时
M5-006 acceptance fail closed。

## M6：API Execution

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M6-001 | DONE | OpenAI/Anthropic/Gemini 薄 Model Provider Adapters | M1-008 | 三家 provider-neutral 薄 Adapter 的离线 contract 测试已通过；live conformance 单独由 M6-004 验收 |
| M6-002 | DONE | 显式模型池与隔离 API session kernel（`K-API-1`） | M6-001 | primary/worker/specialist 槽只可显式绑定；轮次、工具、并行、工具结果、输出、token/成本/time 有硬边界；无自动 fallback；离线测试通过 |
| M6-003 | PARKED | 保留 Task-to-API 文件闭环（`K-API-2`）历史兼容 seam | M1-008, M2-001, M2-002, M2-005, M6-002, M9-005 | legacy compatibility seam 继续可解释；未来 Runtime Bundle、Resolved Execution View、Thin Execution Host 与 generic Trace/Receipt 主链由 M11-001～004 承担，本 Task 不再作为新 execution umbrella |
| M6-004 | BLOCKED | 选定模型槽的真实 Windows Provider/session conformance | M6-001, M6-002 | 当前版本的 OpenAI text/structured/tool 与 bounded evidence-shaped 调用仍待授权 Windows 环境重放；该调用只验证 Provider/isolated session，不依赖 M11-004，也不冒充 Task→View→Host→generic Receipt 的端到端 Gate |
| M6-005 | PARKED | streaming/multimodal/server tools 与平台 Adapter | 真实案例或平台选择 | 按真实案例或平台选择确定执行端启动条件；没有真实需求不启动 |
| M6-006 | DONE | API/平台执行时自动写入 Agent Trace | M3-008, M6-003 | legacy Skill-bound execution 已完成 SessionEventSink、traced runner、archive closeout、file-only verify、recovery preflight 与 Attempt/Receipt Trace linkage；Method-dependent Part C 等待 M8-003 |
| M6-008 | DONE | 建立 Phase D baseline-arm traced execution envelope 与 replay-valid closeout | M5-003, M5-006, M6-002, M6-006, M11-004 | 在 M5-006 冻结 shared contract 后，按 ADR-0020 从 A1/A2 frozen arm 确定性编译独立版本的 baseline envelope：`provider_visible_payload` 必须使用正向白名单与 `additionalProperties=false`，只含 frozen public instruction/input/output contract，A1 Tool surface 为空，A2 唯一额外暴露为 exact Tool definition/interface；完整 Task、`agent_profile`、Mode/Action/Method、Task `required_capabilities`、Capability Requirement/Resolution/Snapshot control、Skill/private-oracle 与未来未知 Task 字段只能留在不可见 enforcement metadata；checked-in `structural-replay` Tool fixture 不得用于正式 execution，M5-004 A2 必须绑定 `runtime-execution`、`execution_input=true` 且 Tool implementation/availability/boundary/typed conformance 闭合的 Snapshot，并按 M5-006 冻结的 shared contract 产生 A2 `ArmExecutionQualificationRecord@1.0.0`，exact-pin Manifest/arm、Task、Requirement、frozen/runtime Capability Resolution/Snapshot，再证明两端 Tool supply identity、implementation version/hash、component、provider-visible interface 相同且 permission/data-egress/side-effect ceiling 只等价或收窄；M6-008 不产生 A3 record、不修改 M11，也不取得 Supply selection 或 shared-contract ownership；每次 provider request 消费 payload 前与每次 Tool invocation 前立即重载/重验对应 envelope/implementation/interface/boundary/conformance pins，Trace actual facts 记录 use-boundary 的 bytes/hash；以 transport trusted start/end clock 执行 time budget，分开 preventive 与 detective semantics；通过 M6 isolated session 形成 exact Provider/Adapter/Model/Runtime/Host/Tool actual facts、Trace、Artifact、Validation 与独立文件 replay Receipt，actual binding 必须由 typed hash-pinned Trace fact 独立佐证；区分 completed/post-call-failed/preflight-blocked，不复用 mandatory Skill Assignment，不 fallback/reselect/rebind，并固定 `task_completion=false`，不产生 Claim/Human/admission/promotion/pruning/Topic 5 authority |
| M6-009 | DONE | 通用协议/profile 与主流 API Key 接入的离线合同 | M6-001, M6-002 | 按[通用接入计划](workstreams/chengyue-lu/M6-GENERAL-PROVIDER-DEFINITION/PLAN.md)分离真实 Provider identity、wire protocol、endpoint/认证、exact model/generation profile 与能力；复用现有 Responses/Messages/generateContent，补齐 Chat Completions，共享确有共同语义的 codec，每个厂商仍有独立 Adapter/config/hash；OpenAI、Anthropic、Gemini Developer API、DeepSeek、Qwen/DashScope、GLM、Kimi、MiniMax、SiliconFlow、Ark、OpenRouter 均有默认 disabled 的非秘密模板、闭集 factory/request/response 正反离线 fixture 和官方能力/认证/模式/Schema/Tool/usage/error/rate/价格/数据控制矩阵；晚解析 CredentialProvider 支持跨平台环境引用及可选本地 vault/子进程桥，不提前读取、不归档密钥；未知或不支持的硬能力在出站前拒绝，不伪装 strict Schema/thinking续传/Provider身份；配置和报告版本兼容，原三家回归通过；actual endpoint/config/codec/helper闭包进入版本化binding manifest，M6 baseline producer与cold replay独立核对，endpoint/helper-only漂移出站前拒绝；conformance显式版本化specific→none两轮Session政策与wire方言/本地业务断言，默认caller与旧probe不变；零API调用；不选择Supply、不Router/fallback/retry、不修改M5/M11/Resolver/Skill实现，未验收模式或stream/multimodal/server tools/托管云执行保持明确gap |
| M6-010 | DONE | DeepSeek Flash 的真实 Windows Provider/session conformance | M6-009, M6-002, `M6-DEEPSEEK-LIVE-AUTHORIZATION-GATE`（可审计外部条件） | 按[通用接入计划](workstreams/chengyue-lu/M6-GENERAL-PROVIDER-DEFINITION/PLAN.md)冻结exact source/profile/endpoint/Flash model与observed identity策略、非思考模式、Credential reference、Windows Host/session/Tool、报告及预算/time/retry/data-egress边界；具名授权且北京时间18:00后及官方闲时窗内才运行固定合成text/schema/tool shape与实际有界client Tool/session往返；fresh session、预绑定Tool本地验证、usage/stops/全部失败费用与未知成本/零请求阻断/预算停闭合，脱敏报告可独立复核，不保存原始prompt/response/tool arguments/隐藏思考/密钥；只接受exact DeepSeek Flash Provider/session，不替代原M6-004 OpenAI验收或M11端到端/A4 admission/M5 Pilot/科研评价；M5消费同一binding，配置/model/source drift重验适用性 |
| M6-011 | READY | 实际模型能力适配与运行用量记录 | M6-009, M6-002 | 按实际模型窗口、接口输出容量和协议要求配置调用参数，区分技术容量与人为经济配额；程序关联 request/intent/Task/Attempt/父子实际 token、调用、耗时、Provider 费用、failed/unknown，零调用与未知不混淆且未知不填零；不新增通用额度、余额预检、预占、unknown holds 或模型预算上下文；记录缺失不单独阻断有效工作，费用请求可按需解释，兼容旧版本；现有 budget 字段/View/Host/Session 的强制去耦由 M6-013 负责，不把增强记账设为普通入口/Tools共同前置 |
| M6-012 | PARKED | 真实 read/write/execute/search Tool 的受控执行 | M11-008 | 真实 handlers 落实路径/进程/网络和副作用约束，记录 actual/partial 产物、失败和原生 usage/unknown；消费已有执行事实接口，不等待 M6-011 增强记账或以余额阻断；选中工具的参数、实际技术容量、环境与权限可验，不只改 label；readonly 正常路径无写入，无资格路径零执行；外写/执行仍需相应授权 |
| M6-013 | IN_PROGRESS | 运行用量与模型工作输入的版本化契约迁移 | M1-004, M1-005, M6-002, M11-002, M11-004 | 按 ADR-0027 显式发布新版本 Task/Policy/View/Host/Session 与角色请求投影，通用执行不要求 budget/sub_budget/经济额度，不做余额/预占/超额/unknown holds 阻断；模型输入只含任务相关职责/材料/权限/交付与实际停止条件，不默认含预算字段/账本或自估用量；程序记录 actual/failed/unknown 并将记账缺口与执行/交付判定分开；取消、接口真实容量/超时及权限/引用/供给/Human Gate 检查保持；旧工件/测试按原版本精确解释，拒绝静默松绑或假兼容，交付双版本正反检查、actual request 差异和迁移消费者表；不重写 DONE/旧评价协议，不因旧额度缺失妨碍新路径，不改变 Resolver/Runtime 权属 |

2026-08-19 的历史 live 诊断不替代当前 M6-004 Gate；OpenAI live conformance、EVID/SIM SIR 与
process-kill recovery 均不作为 `K-INTEGRATION-1` 的合并阻塞项。

## M7：Mode–Skill 选择与协调成本

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M7-001 | DONE | 冻结实名 owner、受控读取与分级 Handoff 文档策略 | M2, M3 | 路诚钺/黄毅职责、ADR-0011/0012、架构图和开发入口一致 |
| M7-002 | DONE | 建立现有 Mode 决策卡与边界 fixtures | M1-003 | 八个诊断 case 覆盖 evidence/simulation trigger、no-Mode、candidate Mode、组合拆分与歧义阻断 |
| M7-003 | DONE | 建立 Task-to-Mode/action/mechanism 选择矩阵 | M7-002, M7-011, M7-008 | tool-only/no-Skill、Skill Need、拆 Task、capability gap、blocked 和 Human Gate 均有可复验路径；无隐式 Assignment |
| M7-004 | DONE | 按 Mode action 重新审计并迁移三个 0.1.0 Skill 原型 | M7-011, M7-008 | 三个冻结包均有 action、direct baseline、manifest/package hash、new-assignment/版本决定与机器夹具；未创建无证据的 `0.2.0` |
| M7-005 | PARKED | 独立整理/重写最多两个 Mode-derived Need 并作证据化去留决定 | M7-011, M3-009, M8-003 | 不再从来源 shortlist 直接选择；`claim-preserving-rewrite` Stage 1 保留为历史诊断，新的 trial 等待正式 Need/Method Trace |
| M7-006 | PARKED | 建立 H0/H1/H2 与内容读取成本对照 | M3-008, M8-003 | 保留为 Evaluation baseline 输入；Method Resolution 稳定后再用 Attempt Archive 记录遗漏、返工、回查和 capture gap |
| M7-007 | PARKED | 新增 experiment/theory/observational/engineering Mode | 真实案例 + Mode 准入卡 | 证明现有 Mode 组合不足后逐个启用 |
| M7-008 | DONE | 为已确认 Mode action gap 建立首批 Tool capability cards | M1-008, M7-011 | 五张 Action-driven cards 已明确数据出口、权限、副作用、预算、失败、验证、fallback 与 owner；未实现 API/Adapter |
| M7-009 | DONE | 建立多来源 Skill 候选池与机器/人工筛选 Gate | M2-008 | 首批 54 个入口均已固定来源、路径、内容哈希和人工 Decision；一方 19 项为 18 `reference`/1 `rejected`，社区 35 项为 6 `triage`/21 `reference`/8 隔离或排除；下载内容未安装、执行或自动准入 |
| M7-010 | DONE | 建立四个来源候选 dossier 并决定是否进入验证 | M7-004, M7-009 | 四份历史 dossier 已完成；Human Decision 选择 0 个来源候选直接重写，转入 ADR-0013 的 Mode-derived Need 路线 |
| M7-011 | DONE | 建立两个正式 Mode 的 Action–Failure–Artifact–Gate 与 Skill Need 基线 | M7-002, M7-010 | evidence/simulation 的每个 action 有最小机制；每个 Mode 首批 Need≤2；no-Skill、Tool、Skill Need、blocked、Human Gate 均可出现 |
| M7-012 | DONE | 建立 project-internal Skill Need 路线与候选占位 | M7-001, M7-011 | 与 Mode-derived 路线分离；交互、输出、恢复和 Gate 候选先比较 Protocol/template/Tool；未新增 Skill/Registry/Runtime |
| M7-013 | DONE | 为两个优先 project-internal Need 建 direct baseline、failure fixture 与 compact dossier | M7-012, M1-004 | H1 omission 与 H2 semantic reversal 均形成可复验诊断；两项结论均为 `hold-no-skill`；未修改自动 Trace/API |
| M7-014 | PARKED | 对 project-internal 候选做有 Trace 的困难任务比较 | M7-013, M3-009, M8-003 | 比较 template/tool/compact Skill 的遗漏、回查、返工和上下文成本；无重复语义增量即退役 |
| M7-015 | DONE | 分离 Skill 历史解析与新分配 lifecycle | M7-004 | Registry/Resolver 表达 active/legacy/deprecated 与精确版本约束；旧 Assignment 可复验，新路由不能选择 legacy/deprecated |
| M7-016 | DONE | 执行 K-MS-1 节点评审并冻结基线 | M7-002..004, M7-008, M7-011..015 | 九项条件逐项 PASS；Decision 接受离线选择/治理基线并 safe stop，不自动进入真实 trial |

## M8：Method Core Formalization

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M8-001 | DONE | 按第二轮审计重整全局架构文档与路线 | M7-016 | ADR-0016、五平面架构、ROADMAP、审计吸收记录和单一真值导航一致；未验证外部项目或实现新 Schema |
| M8-002 | DONE | 将 Mode Action 正式化为一等契约 | M7-011, M8-001 | 两个正式 Mode 的 Action 有 stable ID/version/hash、trigger/non-trigger、failure/artifact/claim/gate/stop/blocked；既有 fixture 无损引用 |
| M8-003 | DONE | 建立版本化 Method Resolution | M8-002 | 八个 routing fixture 转成 provider-neutral Resolution；正式表达 no-Skill/tool/Skill Need/Human/split/blocked 与 rejected alternatives |
| M8-004 | DONE | 建立最小 migration seam 并迁移 Research Mode v0.1 → v0.2 | M8-002, M8-003 | v0.2 删除直接 Skill recommendation；v0.1 仍可验证/历史解释；迁移保留原/新 hash 与实现版本 |
| M8-005 | DONE | 冻结 Decision Authority Matrix 并映射 validation/preflight | M8-002, M8-003 | Agent proposal、deterministic resolution、Human Gate、权限放宽和 Claim promotion 权限有正反 fixture |
| M8-006 | READY | 实际权威事实到方法与 Binding 决定的 producer | M8-005, M8-003, M9-005 | 从 registered facts、实际 obligations 与 pins 形成可核来源的 authority eligibility，再提交实际 Method/Binding 决定并供下游消费；proposal、eligible、decided、executed 分开；歧义、放宽与 Claim 人类边界保留，改变权威语义先 ADR，不以手填 asserted_facts 或 Gate ref 冒充事实/批准 |

M8 的验收只覆盖 Method/Core 契约和下游消费边界；Capability binding、Execution View、Method Trace 与
端到端执行分别由对应 Task 验收，不能从 M8 的完成推出。后续供给消费边界见 [Phase B Gate](implementation/PHASE_B_EVOLUTION_GATE.md)。

## M9：Phase B Evolution Foundation

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M9-001 | DONE | 将 Capability Requirement 正式化为需求侧契约 | M8-003, M8-005 | 可表达目标能力、输入/输出、permission/data-egress/side-effect/验证约束；不含 Provider/Model/Adapter、可用性或具体供给绑定；Method Resolution 引用可闭合验证 |
| M9-002 | DONE | 将 Skill Need 正式化为版本化对象 | M8-003, M9-001 | need identity、trigger/non-trigger、semantic gap、no-Skill/direct-tool baseline、expected increment、evaluation criteria、required evidence classes 与 domain scope/variants 可验证；Need 只声明未来 trial/promotion 所需证据，不保存实际结果，也不等于 candidate/accepted Skill |
| M9-003 | DONE | 建立 Skill lifecycle v2 与显式迁移 | M7-015, M9-002 | intake、evaluation state、admission、runtime eligibility 四轴分离；可表达 trial/superseded/retired 并引用 baseline/trial/evaluation record/decision 与 promotion evidence；不重建完整 benchmark/metric/experiment framework；旧 Registry identity 和历史 Assignment 继续可解释 |
| M9-004 | DONE | 建立最小 Protocol Profile 契约 | M8-004, M9-001 | M9-001 接受后可与 M9-002/003 并行；以两个有界 PRISMA/V&V profile 表达 applicable/not applicable、method obligations、Gate/evidence expectations，并证明 Mode、Protocol、Skill 职责不重叠；不固定全局 DAG，不绑定 Skill/Tool/Provider/Runtime |
| M9-005 | DONE | 建立 Capability Supply Report、Capability Resolution 与 Resolved Capability Snapshot 共享接口 | M9-001, M8-005 | M9-001 接受后 Core 可独立 READY，支持 no-Skill、direct Tool、Adapter/Provider supply facts 与受 ceiling 约束的 resolution/snapshot；Report 不选择自身，Resolution 区分 satisfied/gap/ambiguous/blocked，Snapshot 冻结 exact supply/version/hash/permission/data-egress/side-effect/conformance refs；Skill Supply Extension 仅在 M9-003 runtime eligibility 稳定后接入；不实现 API session 或 Runtime consumer |
| M9-006 | DONE | 完成 Phase B migration/replay 与替换性 Gate | M9-002..005 | 已发布旧对象经显式 migration 继续解释；同一 Task/Mode/Action/Method/Requirement 在 Supply A→B 替换时只生成不同 Snapshot，且 permission/data-egress/side-effect ceiling 均不放宽、Runtime 不获得 Method authority；Phase B Stop Gate 有逐项证据 |
| M9-007 | READY | Task 范围供给发现、可用性事实与逐候选排除 | M9-005, M11-002 | 在显式 Task 范围内发现 catalog 候选并观察实际 availability/资格，逐候选记录 fail/unknown，不因一个候选失败阻断其他完整合格供给；Resolver 保持唯一 selector，multiple eligible 不 pick-first；改变排序/歧义规则先 ADR，不授予 Runtime 扫仓或重选权 |

## M10：Phase C Research State & Verification

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M10-001 | DONE | 建立并审计最小 durable Research State composition candidate | M1-002, M8-005, M9-005 | 用两个 bounded case 与反例检验最弱表示；当前 Unknown/Assumption item、Contradiction relation、derived Frontier、provenance-bearing Human Decision 与 Evidence relation 都是 implementation hypothesis，不预冻结最终 Schema；exact ref 结构可确定验证，科学判断与最终表示须 Human/R2 接受 |
| M10-002 | DONE | 建立 Attempt / Research Failure 语义与独立 lineage candidate | M1-004, M10-001 | Attempt 分离 from-State、optional predecessor Attempt 与 reopen justification；多个 Attempt 可共享 State，State 可由 Evidence/Human Decision 独立演化；Research Failure universal minimum 仅冻结 learned result/revisit condition，当前 source Attempt/observed/uncertainty 是 bounded profile candidate，并与 execution failure、negative Evidence、Capability Gap、Skill Need 分离 |
| M10-003 | DONE | 完成 Phase C bounded continuity / verification Gate | M10-001, M10-002, M3-009 | evidence-synthesis 与 synthetic simulation-negative 两案在 staged 新进程中只读 compact State、Method Trace 与 runner-owned exact closure；private oracle 只检查 exact output/read surface/fixture predicates 与 known-failure behavior，不能证明 reviewer reconstruction或科学正确性；具名 Human semantic review 与 R2 closeout 独立，Gate 不授权 Topic 5 实现 |

## M11：Phase F Execution Reintegration

M11 把 M6-003 的未来 umbrella scope 拆成可独立失败、审查和验收的 producer/consumer contracts。
Core（M11-001～004）必须在零 Skill、零 Evolution Registry 下闭合；Skill supply publication/mapping
（M11-005～006）是可选支线，不阻塞 Core。M11-001→002→003→004 保持四个独立 implementation /
acceptance identity；它们可按 `DEVELOPMENT.md` 的通用 module-level PR 规则，在一个强耦合
Execution Reintegration PR 中依拓扑顺序原子集成。PR 粒度不合并 Task identity，也不允许跳过逐 Task
implementation slice、commit、evidence、必要审查或 hard dependency。

| ID | 状态 | 任务 | 历史记录 | 风险 | Phase / Topic | 依赖 | 验收 |
|---|---|---|---|---|---|---|---|
| M11-001 | DONE | 建立 Runtime Bundle / Consumer Profile | 黄毅 | R2 | F / Topic 4 | M9-005 | 以显式 closure manifest 固定 Runtime 可读取的 exact objects/hash/import graph；拒绝目录输入、递归扫描 Registry/examples、Evolution validator import 与 fixture-only `structural-replay`；零 Skill/零 Evolution Registry 路径通过 |
| M11-002 | DONE | 建立 supply-neutral Resolved Execution View Core | 路诚钺 | R2 | F / Research Control + Topic 4 | M9-005, M11-001 | 从 frozen selection 计算并冻结 exact Host/Provider/Adapter/Model、external pin/freshness、Task/Profile/DataPolicy/Host policy 与 permission/data-egress/side-effect 最严交集；fail closed，不重新选择 Supply、不 fallback、不要求 SkillReleaseProjection |
| M11-003 | DONE | 建立 Thin Execution Host 与 actual execution fact report | 黄毅 | R2 | F / Topic 4 | M3-008, M6-002, M11-002 | Host 只消费 exact closure-valid Snapshot/View，执行冻结调用并报告 actual facts、bounded Diagnostic 或 re-resolution request；不能 reselect/rebind/fallback、修改 Method/Claim/Gate 或扩大边界；不实现 Topic 5 的 Handoff/context/recovery 语义 |
| M11-004 | DONE | 建立 generic execution Trace/Receipt linkage 与 Core vertical Gate | 黄毅 | R2 | F / Topic 4 + Artifact/Trace | M3-008, M11-003 | no-Skill 与 direct-tool bounded path 可从 Task/View/Host 到 Trace、Artifact、Validation、generic Receipt 闭合；复用 observability contract 不构成 Topic 5 membership；不伪造 Skill Assignment，不把 execution completion 写成 Claim/Human acceptance，并保留 legacy Receipt replay |
| M11-005 | DONE | 发布不可变 SkillReleaseProjection | 路诚钺 | R2 | F / Capability/Skill Evolution + Topic 4 | M9-003 | 只发布 accepted immutable Skill Release 的 runtime-minimal identity/version/hash/capability/boundary facts；不暴露 Need/Evaluation/Lifecycle 历史，不授予选择或执行权限；缺失只阻断 Skill new-binding |
| M11-006 | DONE | 将 eligible Skill supply 映射进统一 Resolved Execution View 语义 | 路诚钺 | R2 | F / Research Control + Capability/Skill Evolution + Topic 4 | M11-002, M11-005 | projection-derived Skill 与 Tool/procedure/Adapter 使用同一 Report→Resolution→Snapshot→View 语义；Capability Resolver 仍是唯一 selector，View/Host 保持 supply-kind neutral；不得形成 Skill-specific Runtime dispatcher/session/fallback seam，projection 缺失/stale/mismatch 时仅该候选 fail closed |
| M11-007 | DONE | 建立 Skill-bearing generic closeout extension 与独立 replay | 黄毅 | R2 | F / Topic 4 + Artifact/Trace | M11-004, M11-006 | 以独立版本扩展 Core execution closeout，exact-pin SkillReleaseProjection identity/version/path/hash、Skill ID/version/hash、selected Supply/component、Resolution/Snapshot、Bundle/View、Task/Action/Capability slice/Attempt 与 Host actual facts；由 use-boundary actual consumption 和 typed hash-pinned Trace fact 独立佐证 actual Projection/Supply/binding，文件 replay 重载全部 refs 并重做跨对象/生命周期 invariant，不调用 Provider/Tool 或依赖原会话；completed actual 与 selected View 相同且输出/Validation subject closed set 完整，post-call-failed 保留可被 Trace 佐证的真实 drift/diagnostic 而不强改 equality，preflight-blocked 无 actual facts/调用，driver exception 或 capture 不完整时拒绝 receipt eligibility；completed 仅 action-capability-slice-only，其他状态 none，全部 task_completion=false；保持 Core/legacy 版本语义与回放、View/Host supply-neutral 和 Resolver 唯一选择权，不引入 Assignment、dispatcher、fallback/reselection、Task/Claim/Human/admission/promotion/recovery authority；Runtime 不加载 candidate/Evaluation/oracle，M5-007 在评价侧比较 replay result 与 M5-006 overlay；交付 synthetic vertical proof、独立正反验收与现行 coverage evidence，并由双方按 [Gate B record](workstreams/chengyue-lu/M11-SKILL-CLOSEOUT-GATE/GATE.md) 接受 exact implementation/validator/fixture/replay/CI pins；任务定义不等于 Gate SATISFIED |
| M11-008 | IN_PROGRESS | 普通研究入口的冻结执行、closeout 与全链桥接 Gate | — | R2 | F / Topic 4 + Artifact/Trace | M9-005, M6-002, M11-004 | 每个实际角色 Task 经显式 Research Control factory 比较供给并冻结 exact Snapshot/Bundle/View，真实消费者验证并执行；no-Skill 与直接 Tool 的 Core 全桥独立验收，缺 Skill 资格时证明 preflight block；若启用合法 Skill 支线则要求 actual load 并复用 M11-006/007，Core 收口不宣称真实 Skill 通过，合格 Skill 正路径另由 M2-012/M11-010 验收；actual binding/request/response/Tool/usage/failed/unknown 与 Trace/Host/Receipt/output pins 保留且独立冷回放不调用模型；主子结果实际消费至 Handoff/checkpoint/Human 待办，并证明 Guide 隔离；全链矩阵逐桥给出 producer、contract、consumer、结果和缺口，不能以 fixture、裸 callback 或单模块 PASS 替代实际链；不代签 live/Skill/source 资格、Human/科学接受、M5 四臂评价、Release 或 Topic 5 recovery |

上述历史记录列仅保留旧验收追溯，不参与新任务授权。以下新增定义统一不设人员列。

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M11-009 | PARKED | Task 实际交付检查与独立完成判定 | M2-009, M2-010, M11-008 | Task 选择真实交付/内容检查、确定性 completion checks 与必要语义 review，逐意图/子任务检查 actual 产物并记录可用 partial 与 Parent Goal 判定；独立完成项先返回，partial 与最终综合分开，执行结果与记账完整性分别判定；独立 assessment 不把 action-only Receipt.task_completion 改 true，不从结构通过自动接受科学结论 |
| M11-010 | PARKED | 工程真实化整链 Gate | M1-013, M2-011, M2-012, M2-013, M3-010, M3-011, M3-012, M4-006, M4-007, M6-012, M8-006, M9-007, M6-013 | 在可控工程材料上实测两种初始化，按需选择 Mode/合格 Skill/Tool/Profile/child，检查实际内容消费、失败保真、精简 State 和独立 Guide；消费 M6-013 新版本迁移输出，验证未设置经济额度也能执行、实际模型请求无默认预算管理内容、用量未知与内容完成分别判定；qualified Skill 的真实外部前置不以假供给替代，零 Skill 路径独立验收；不以完整记忆/方向分支/前端/M12为新前置，不是 M5 净价值评价，不授予真实复杂科研或 Topic 5 实现权限 |
| M11-011 | PARKED | 统一入口长短链隔离 Gate | M1-015, M11-010 | 实测 Guide、段落重排且 State 不变、小改导致 Claim relevant/unknown 与采纳/hold、关联多意图的共同限制/依赖/冲突及独立返回、明确 main steering、新研究 Protocol、活动文件冲突及误投 child 拒绝；给出 actual diff、MainState before/after、recipient/context/notifications 和原请求对应证据，不以 bare callback 替代；失败不抹去已正确交付项，不默认污染 main，不自动状态恢复/科学准入，不增加完整记忆/方向分支/前端的全局 Gate |

M11-007 是可选 Skill execution closeout 支线；它与 M6-008 baseline closeout 保持独立 identity。
Skill closeout 资格及接受证据见 [Gate B](workstreams/chengyue-lu/M11-SKILL-CLOSEOUT-GATE/GATE.md)。
M11-008 消费 M1-010/M2-009 对应的真实产物形成全桥证据；原三条桥接 Task 的入口依赖都是既有接口，
无新 Task 间 hard dependency 不免除最终接合验收。定义分支的 READY 只有在 PR 接受后才成为共享任务状态；
候选代码及隔离测试不等于 Task DONE，边界见 [任务定义记录](workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/README.md)。

## M14：Product / Release Closure

M14 由 [ADR-0021](decisions/0021-CURATED-DEVELOP-TO-MAIN-RELEASE.md) 与
[Issue #57](https://github.com/Chengyue-Lu/research-agent-workbench/issues/57) 激活。它只负责把 frozen
`develop` 工程真相确定性投影为可安装、可追溯的精选 `main` 发行视图；不修改 Runtime、Method、Claim、
Human Decision 或 permission 语义。Issue 中的 `REL-001～005` 是工作包别名，以下 `M14-*` 才是 canonical
implementation / acceptance identity。

| ID | 状态 | 任务 | 历史记录 | 风险 | Phase / Topic | 依赖 | 验收 |
|---|---|---|---|---|---|---|---|
| M14-001 | DONE | 建立 curated release topology 与 source trust governance（REL-001） | 路诚钺 | R2 | Product / Release Governance | M0-005, M1-001 | 以声明式 policy 建立 dormant、same-repository、version-valid `release/v* -> main` R2 topology；分别校验 external expected frozen develop source/repository trust 与 exact current main Git parent/ancestry，但所有 release-branch PR 在 M14-005 readiness/cutover 前显式 fail closed；普通 feature/task-definition 仍进入 develop，现行 exact `develop -> main` 保持唯一可执行发布路径；不能只凭分支名放行，也不恢复 direct push/force/delete 或在 release branch 修改产品语义 |
| M14-002 | DONE | 建立 deterministic release surface、manifest 与 export/check（REL-002） | 路诚钺 | R2 | Product / Release Projection | M14-001 | strict、append-only versioned allowlist 与 manifest Schema 驱动同一 export/check 实现；每个输出分类为 source-blob 或 exact allowlisted generated，分别 pin blob/mode/size/hash 或 generator identity/version/hash/inputs，manifest 使用无自哈希歧义的 canonical UTF-8 JSON/LF/稳定排序且禁止时间、随机数和临时绝对路径；直接读取 frozen develop commit Git blobs，在以 exact current main 为 Git parent 的生成分支上完整构建 projection，并由 external expected repository/source/parent 重算 selection/excluded/output closure；unknown/重复/overlap/不存在 include、casefold/Unicode/Windows path collision、dirty tree、CRLF、mode/byte drift、额外/隐藏/移动/遗留文件、path escape、symlink/gitlink、undeclared generated、policy drift 及同步重算伪 hash 全部阻断；连续 v1→v2 fixture 证明旧版独有 generated 文件不会残留，prospective merge-result tree、projection tree 与 manifest closed output tree 完全相同，main parent 漂移时必须重新生成；critical checker 满足 95/90 与独立正反 evidence，但不启用 release merge path |
| M14-003 | DONE | 闭合 portable package 与 Runtime data boundary（REL-003） | 路诚钺 | R2 | Product / Package + Runtime Resources | M14-001 | 定义独立 hash-pinned `RuntimeResourceManifest`、packaged default resolver，并分离 project/filesystem、immutable runtime-resource、integration-config 三个 root，禁止隐式 CWD/checkout fallback；公开 Runtime catalog 与 maintainer/publication history 分离，repository publication validation 与 installed-runtime catalog validation 分层；wheel/sdist→wheel exact assets 在清空 `PYTHONPATH` 的 checkout 外 Python 3.11/3.13 环境加载 Schema、Mode/Action、Authority、Requirement、Profile 与空 Projection，并由 wheel-owned/generated input 完成 no-Skill structural quickstart；非空 Projection 必须通过 logical→installed path mapping 闭合其 exact immutable Skill manifest/package bytes且拒绝 orphan/unindexed asset，否则 fail closed；legacy `accepted.json` selector、`sources.json`、Need/Evaluation/Lifecycle、provider baseline、broad `.agents/**` 与 `.codex/**` 不得成为 packaged default，但被 Projection exact path/hash 引用的单个 accepted manifest/package 可作为条件 Runtime Release asset |
| M14-004 | DONE | 建立 public documentation surface（REL-004） | 路诚钺 | R2 | Product / Public Documentation | M14-002, M14-003 | README、Getting Started、Supported Features 与公开导航有单一来源，release tree 无指向 TASKS/STATUS/DEVELOPMENT/workstream 等排除文件的断链；文档区分 structural、bounded、live 与 evaluated 证据，不把空 Projection index、未完成 M5、synthetic fixture 或未验证 Provider 写成已交付能力 |
| M14-005 | DONE | 生成并验收首个 curated main release（REL-005） | 路诚钺 | R2 | Product / Release | M0-007, M1-009, M14-002, M14-003, M14-004, `GITHUB-RELEASE-PROTECTION-GATE` | 在全部依赖、许可证、scaffold、远端保护与具名 Human release decision 闭合后，冻结 exact develop source SHA 和 exact current main parent SHA；从该 main tip 创建 release branch，由 exporter 只读取 frozen develop Git blobs并完整构建 tree/manifest，两次生成稳定；main 前移必须按新 parent 重建；source required CI、release checks、双 Python clean-install、no-Skill smoke、Registry/Projection load、公开链接与零内部材料泄漏均通过，且 prospective merge-result tree = projection tree = manifest closed output tree；同一 Task 的治理激活与首次 release 按可审计 slice 执行，原子启用 `release/v* -> main` 并禁用 direct `develop -> main`；R2 release PR 以 merge commit 合入 main 后 tag/artifact/hash 与 manifest 闭合，release branch 不回并 develop |

## Future M-series reservations

以下条目只是 expected implementation-family namespace，不是 Task：没有 `READY / BLOCKED / PARKED / IN_PROGRESS / DONE`
状态，不创建 future 原子 ID，也不冻结 risk、dependency、acceptance 或
Schema。Reservation 不授权 implementation，不代表 architecture acceptance 或解冻；若未来证明既有
M-group 足以承载，可直接取消且不产生历史 Task identity。当前不推测 M15+。M14 已由独立 R2
task-definition 激活，不再属于 reservation。

| Reserved M-group | Expected implementation family | Activation condition | Confidence |
|---|---|---|---|
| **M12 — RESERVED** | Execution Continuity & Recovery：Handoff、context rollover、safe pause/resume、recovery、clean/salvage recovery 等 Topic 5 residual implementation | Phase C closeout，且完成独立 Topic 5 R2 architecture review 与 docs-only task-definition | High |
| **M13 — RESERVED** | Strategy & Governed Evolution：strategy interface、candidate strategy、bounded experimentation、merge/prune/governed evolution | Phase C/D evidence 证明现有 M2/M7 无法自然承载一个新的 coherent implementation family | Medium–High |

Reservation 只有在对应 architecture activation Gate 已接受、已有 M-group 不足已有证据、独立 docs-only
`task-definition` 完成后，才可转换为正式 M-group，并在当时定义具体 `Mxx-yyy`、risk、dependency、
acceptance 与 negative boundaries。因此：M12 reservation 不等于 Topic 5 thaw 或 implementation approval；
M13 不等于 strategy framework approval。

## Task 风险与阶段索引

本表补齐 risk 与 Phase/Topic 导航，不设人员列，不复制实时状态、完成日志或验收。原 DONE 行只保留历史定义；
scope/依赖/验收以 Task 行为准。固定人员限制按用户本轮决定撤销，机器治理与模板的实际对齐由 M0-008 验收；
风险、权限、必要审查和 PR/CI 不因人员分工撤销而消失。M4-006/M2-013 为 R1，实际修改 authority 敏感路径时按规则升级 R2。

| Task / family | Risk | Phase | Topic / responsibility |
|---|---|---|---|
| `M0-007` | R2 | Release Gate | Repository / Governance |
| `M0-008` | R2 | Governance | Repository / Governance |
| `M1-009` | R1；安装 smoke R2 | F / release readiness | Repository / Product integration |
| `M1-010` | R2 | Foundation / F | Research Control + Contracts |
| `M1-011, M1-012, M1-013` | R2 | Foundation / F | Research Control + Contracts |
| `M1-014, M1-015` | R2 | Foundation / F | Application entry + Research Control / Contracts |
| `M2-009` | R2 | Foundation / F | Agent Runtime + Research Control |
| `M2-010, M2-011` | R2 | Foundation / F | Agent Runtime + Research Control |
| `M2-012` | R2 | Foundation / F | Capability / Skill + Topic 4 |
| `M2-013` | R1；authority 敏感路径 R2 | Foundation / F | Read-only explanation |
| `M2-014` | R2 | Foundation / F | Agent Runtime + Application short-edit |
| `M11-008` | R2 | F | Topic 4 + Artifact/Trace |
| `M11-009, M11-010` | R2 | F | Topic 4 + Artifact/Trace |
| `M11-011` | R2 | F | Application entry + Topic 4 + Artifact/Trace |
| `M2-003, M2-004, M2-007, M2-008` | R1～R2 | E / optional evaluation | Capability / Skill Evolution；legacy/来源驱动路线的恢复须重新决定 |
| `M2-006` | R1 | F / optional platform | Topic 4；仅按实际平台需求启动 |
| `M3-001～007` | R2 | pre-A bounded slice；post-C future | Topic 5 + Artifact/Trace；residual 仍需独立 task-definition |
| `M3-010, M3-011, M3-012` | R2 | Foundation / F | Context / Trace；M3-012 不解冻 Topic 5 |
| `M3-013` | R2 | Foundation / F | Context / Trace + MainState impact；不解冻 Topic 5 |
| `M4-002` | R1 | C / D | Research State + Artifact/Trace |
| `M4-003, M4-004` | R1；M4-003 R2 | C / D | Research State + Artifact/Trace |
| `M4-005` | R1 | deferred | Artifact/Trace；真实大文件需求是启动条件 |
| `M4-006` | R1；authority 敏感路径 R2 | C / F | Artifact / Trace / Execution environment |
| `M4-007` | R2 | C / F | Artifact / Trace / Research objects |
| `M5-001, M5-002` | Human decisions R2 | D | Evaluation + Research State；具名案例边界 |
| `M5-004, M5-005` | R1；Human decisions R2 | D | Evaluation + Research State；真实评价与 disposition |
| `M5-006, M5-007` | R2 | D | Evaluation protocol / harness；不产生 live/admission 权威 |
| `M5-008` | R2 | D | Evaluation + Topic 4 + Artifact/Trace；独立四臂 live pilot |
| `M6-003` | R2 | historical / F compatibility | Topic 4 + Topic 5；legacy seam，主线按 M11 contracts |
| `M6-004` | R2 | F | Topic 4；OpenAI Provider/session 的独立 live 授权 |
| `M6-005` | R1～R2 | deferred F | Topic 4；真实需求/平台选择 |
| `M6-008` | R2 | D / F | Evaluation + Topic 4 + Artifact/Trace；A1/A2 baseline transport |
| `M6-009` | R2 | F | Topic 4 + Credential/DataPolicy；离线接入合同 |
| `M6-010` | R2 | F / D prerequisite | Topic 4；exact DeepSeek Flash Provider/session，适用性见[受限收口](workstreams/chengyue-lu/M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-010_COMPLETION.md) |
| `M6-011, M6-012, M6-013` | R2 | F | Topic 4；能力/用量与显式版本迁移 |
| `M7-005, M7-006, M7-014` | R2 | D | Research Control + Evaluation + Skill Evolution |
| `M7-007` | R2 | E | Research Control / Mode；真实 gap 与准入卡 |
| `M8-006` | R2 | A | Research Control |
| `M9-007` | R2 | B | Capability / Skill Evolution |
| `M1-016, M1-017` | R1；authority 敏感路径 R2 | F / Product | 运行事实读取与只读显示 |
| `M2-015` | R2 | F / C | 受控委派与活跃方向组织，不定义持久分支权威 |
| `M3-014, M3-015` | R2 | C / F | 读取/来源/角色工作集与有来源维护 |
| `M14-001～005` | R2 | Product / Release | Release Governance / Projection / Package / Public Documentation；每次发布独立决定 |

## 历史 GitHub Issues

首批 Issues 已在后续实现与架构调整后关闭；本节只保留任务来源追溯，不再作为当前执行入口：

- [#1 M1-001 Bootstrap Python package and CI](https://github.com/Chengyue-Lu/research-agent-workbench/issues/1)
- [#2 M1-002 Implement the minimal research object schemas](https://github.com/Chengyue-Lu/research-agent-workbench/issues/2)
- [#3 M1-003 Implement protocol, mode, agent, and skill manifests](https://github.com/Chengyue-Lu/research-agent-workbench/issues/3)
- [#4 M1-004 Implement task, handoff, main state, and reference integrity](https://github.com/Chengyue-Lu/research-agent-workbench/issues/4)
- [#5 M1-005 Build the minimal CLI and deterministic risk checks](https://github.com/Chengyue-Lu/research-agent-workbench/issues/5)
- [#6 M1-008 Freeze provider-neutral model API port](https://github.com/Chengyue-Lu/research-agent-workbench/issues/6)
- [#7 M2-008 Audit and admit external Skill candidates](https://github.com/Chengyue-Lu/research-agent-workbench/issues/7)（来源驱动扩张已被 Need-first 路线取代）

## 施工与证据读取规则

合法入口由 canonical Task 行给出；投入排序按用户确认的范围、具体依赖和实际能力安排，不以经济额度或记账完整性阻断文档、实现和离线验证。`BLOCKED` 只按该行列出的
hard/external conditions 解阻，`PARKED` 需要恢复决定。定义分支、代码候选和共享接受分别留证。
PR 组织和 `PARKED → DONE` 的适用条件统一采用 [DEVELOPMENT 第 5.1 节](DEVELOPMENT.md#51-pr-类型与任务状态)，不在本页另建例外。

完成含义须保持该 Task 的边界：结构/有界机器验收不推出 live、ordinary-user 全桥、Human/科学接受、
Skill admission 或系统净价值。M4 promotion eligibility 由当次 pinned pipeline 重执行确立，
claimed provenance metadata 不能认证历史 producer/operator/time；具体行为见[工件提升契约](implementation/ARTIFACT_PROMOTION_CONTRACT.md)。
M6-009 的十一厂商离线合同不等于十一家 live 支持；M6-010 只接受其[受限收口](workstreams/chengyue-lu/M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-010_COMPLETION.md)中的 exact Flash 对象，
后续 source/config/model/Host/Tool/purpose drift 必须重验适用性，不替代 M6-004、M5 pilot 或 A4 admission。

M6-003 的旧 seam 与 M6-006 的 “Part C 等待 M8-003” 保留历史解释，不定义当前恢复 Gate；
兼容入口见[兼容说明](compatibility/README.md)。M14 的历史验收见[首发完成记录](workstreams/chengyue-lu/M14-CURATED-RELEASE/FIRST_RELEASE_COMPLETE.md)，
后续发行仍按独立 frozen source/current main parent、验证及具名发布决定执行，不解除其他 Task Gate。

## Topic 4 / Topic 5 权限 Gate

Topic 4 使用 Runtime Bundle → Resolved Execution View → Thin Host → actual facts → Trace/Receipt。
Capability Resolver 是唯一供给 selector；View producer 形成 external pins、exact binding 与最严 policy 交集；
Host 消费冻结对象并报告 actual，不 reselect/rebind/fallback，也不修改 Method/Claim/Gate。
Host/Runtime 自主路由、critic voting、隐藏编排与扩权仍禁止；M2-009 的 caller 在已授权上限内提出有界 child Task，
每次经独立选择/冻结和权限/输入/供给预检后执行，实际用量由程序记录，不把编排权放入 Host，不扩大 Runtime ownership。

Topic 5 继续受 Phase C Human semantic review、R2 closeout 与独立架构审查约束。
`M10-001 → M10-002 → M3-009 → M10-003` 只是 machine prerequisite，不自动解冻 Topic 5。
即使 Phase C closeout 被接受，Handoff、context rollover、safe pause/recovery、salvage/clean recovery 或
continuation semantics 仍须独立 Topic 5 review/task-definition 与 R2 acceptance。
仅消费 Trace/Receipt、人工批准的 MainState 或执行事实不构成 Topic 5 membership；
M11-003/004/008、独立只读 Guide 与人工材料接入不获得自动恢复权限。详见[路线图 Gate](ROADMAP.md#4-phase-c--topic-5-gate)。
