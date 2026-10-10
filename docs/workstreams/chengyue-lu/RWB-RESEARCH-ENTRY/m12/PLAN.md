# PLAN-M12：M12 边界与后续任务候选

日期：2026-10-07（Asia/Shanghai）。状态：**规划交付 / PROPOSED**。本页完成本 workstream 的 PLAN-M12 输出，不改变 canonical M Task、Phase C closeout 或 Topic 5 权限。

Agent Profile：bounded continuity-planning agent；required-Skills：`[]`。任务依据：[Task Packet](../TASK_PACKET.md)、[入口范围](../README.md)。写域仅本页和 [COMMUNICATIONS](COMMUNICATIONS.md)；具名语义负责人为路诚钺，执行接口负责人为黄毅，assistant 不代签其决定。

## 1. 结论与建议顺序

当前可复用 Main State、Context Snapshot、checkpoint、resume-check、Handoff 检查及 legacy recovery preflight。它们分别提供文件表示、确定性检查和 seed 准备；当前没有从这些结果自动获得恢复执行权的通用 consumer。

当前入口的人工再启动、缺 Main State 的有界接入、Handoff 消费和新 checkpoint 发布，可沿本次 ENTRY 授权接合既有契约。若实现开始改变 pause/resume、Attempt 连续性、自动换届、失败重试或恢复策略语义，就进入 Topic 5，不能用“人工触发”或“消费 Trace”避开其 Gate。

建议未来首个 M12 交付沿既有候选：**已闭合 action → fresh process → 一个已经冻结的 next action → 唯一新 Attempt**。首版只做文件式单步接续，保持 Resolver → Bundle/View → Host 边界。先完成 Phase C 具名有限收口，再独立接受 Topic 5 架构/ADR 与兼容选择，最后通过 docs-only task-definition 定义正式 Task。本轮只准备这些审查输入。

## 2. 实际基线、阅读范围与来源

- 实际工作 branch：`codex/research-entry-integration`；HEAD/base：`d3c4d23206339ebc7f18b5621f3aa5453f96335e`。本轮未以 primary 的旧 HEAD 作为源码基线。
- 指定 checkout 的 AGENTS、README、docs/README、DEVELOPMENT、ARCHITECTURE 已读；进一步读取 [上下文模块](../../../../modules/06-CONTEXT_GOVERNANCE.md)，及 [TASKS](../../../../TASKS.md)、[ROADMAP](../../../../ROADMAP.md)、[STATUS](../../../../STATUS.md) 的 M3/M10/M11/M12、Phase C/Topic 5 对应段落。
- 直接实现读取：context/models 的预算/评估/Main State 段落、context/handoff_transfer 的入口与风险/判定段落、context/__init__ exports、execution/recovery 全文。CLI 仅定向读取上述模块明确引用的 checkpoint/resume-check/recovery-check handlers 与参数，未扫描其他实现正文。
- 直接测试读取：test_m3_context_observability 的 context/checkpoint/resume 部分；test_execution_trace_adapter 的 safe-pause builder 和 recovery 部分；test_execution_archive_helpers 的 recovery 正例；test_handoff_transfer 的判定/反例定位。test_context_model_branches 只读符号 metadata。**本轮没有运行这些测试，测试名称或断言存在不等于本轮 PASS。**
- primary PROJECT_MEMORY 只用 M12 与 M5 最新导航核对项目归属；M5 导航用于确认本入口缺口与旧开发暂停边界，不读取私有 API Attempt、Key、账或 oracle。初次导航检索的过宽匹配/截断已在 COMMUNICATIONS 留痕，历史尾文不作当前授权或实现依据。
- 当前 checkout 没有 M12-BOUNDED-CONTINUITY 或 CLOSEOUT_CANDIDATE 正文。经 metadata 和索引定位，只读既有 PR137 参考 checkout 的 `2f1b9850e0d40f18d3a9b95057a4d01d60b8a83e`，读取其 README、ADR 候选定向段落、Task 候选定向段落、Phase C CLOSEOUT_CANDIDATE。未改该 checkout 或 PR137；未在线核对 PR 状态。
- 参考 [M12 索引](https://github.com/Chengyue-Lu/research-agent-workbench/blob/2f1b9850e0d40f18d3a9b95057a4d01d60b8a83e/docs/workstreams/chengyue-lu/M12-BOUNDED-CONTINUITY/README.md)、[ADR 候选](https://github.com/Chengyue-Lu/research-agent-workbench/blob/2f1b9850e0d40f18d3a9b95057a4d01d60b8a83e/docs/workstreams/chengyue-lu/M12-BOUNDED-CONTINUITY/ADR_CANDIDATE.md)、[Task 候选](https://github.com/Chengyue-Lu/research-agent-workbench/blob/2f1b9850e0d40f18d3a9b95057a4d01d60b8a83e/docs/workstreams/chengyue-lu/M12-BOUNDED-CONTINUITY/TASK_DEFINITION_CANDIDATE.md) 和 [Phase C 收口候选](https://github.com/Chengyue-Lu/research-agent-workbench/blob/2f1b9850e0d40f18d3a9b95057a4d01d60b8a83e/docs/workstreams/chengyue-lu/PHASE-C-RESEARCH-STATE/CLOSEOUT_CANDIDATE.md)。它们来自较早 base `6fa105b…`；本页只将其作为候选，canonical 当前边界以 d3c4 的 TASKS/ROADMAP 为准。

读取时声明输入与源码相对 d3c4 未有 diff；参考四文档相对参考 HEAD 亦未有 diff。精确路径、实际 SHA-256、阅读段落与关键事件见 COMMUNICATIONS。本轮未重验 Phase C 两个 manifest 的 24 项 closure；参考候选中的旧核验数字保留其原证据身份。

## 3. 已实现接口与保留缺口

| 现有接口 / 实际定位 | 已实现的窄职责 | 不能据此推断的能力 |
|---|---|---|
| [MainStatePacket / checkpoint_digest](../../../../../src/research_workbench/context/models.py)，504–623；公共 [context exports](../../../../../src/research_workbench/context/__init__.py) | active Task、recent Handoff、约束/决定/风险、next_actions、机器 refs；digest 为去除 digest 字段后的规范化 JSON SHA-256；可带 protocol revision、previous checkpoint、Context Snapshot、Git HEAD | 字段允许引用不代表对应研究决定被接受；Main State 是小型控制入口，Research State 与原材料各有权威 |
| [ContextBudgetEstimate / assess_context](../../../../../src/research_workbench/context/models.py)，157–201、227–344 | measured/estimated/unavailable、已知与未知指标；next-AWU + closeout + reserve；ok/warn/rollover/block；main 自动压缩触发 rollover，task 压缩按 Handoff 条件处理 | 不读取平台隐式聊天；字符数不能换算成假精确 token 余量；判定只给风险/建议，不调度新窗口 |
| [context checkpoint handler](../../../../../src/research_workbench/cli.py)，1394–1487；原子写入 80–104 | 从显式 protocol/可选 from-state 生成新 checkpoint，冻结机器 refs、digest、可选 Git HEAD；flush/fsync 后用排他 link 发布完整文件 | 原子 checkpoint 发布不等于新 Attempt 排他消费；from-state 会保留/追加列表，调用方仍须处理旧 next_actions、活动任务和已消费 Handoff |
| [context resume-check handler](../../../../../src/research_workbench/cli.py)，1209–1348 | 检查 digest、protocol/questions、next action、Snapshot scope/风险、引用、Git conflict、前后 checkpoint 的约束/决定丢失 | 不创建会话或 Attempt，不执行 next action；Git HEAD 不覆盖未提交工作树；检查没有授予人类/科研接受 |
| [assess_handoff_transfer](../../../../../src/research_workbench/context/handoff_transfer.py)，51–246 | 校验 Task/Handoff/Manifest exact refs、条目与负面区段覆盖、风险要求的独立 human sample；区分 structurally-ready / not-transfer-ready / transfer-ready-after-review | 无独立语义抽查时不能称 semantic equivalence；H2 checker 不自动证明未来 no-Skill 投影兼容 |
| [prepare_recovery_attempt](../../../../../src/research_workbench/execution/recovery.py)，65–268 | 先 file-only verify 旧 archive；仅接受 safe-paused 的 Attempt/Handoff/Main State 一致绑定；要求 Trace、不同 ID、root 内尚不存在的新目录，返回 RecoveryPreparation(seed/risks) | 不创建目录，不 dispatch，不实际恢复；`exists()` 预检不是原子认领；保留 legacy input/Skill/assignment locks，不是 Core no-Skill generic continuation consumer |
| M11 Core（TASKS：M11-001～004） | 已有 frozen closure、View、Host actual facts、generic Trace/Receipt；可作为未来接续执行缝 | 本轮未读取或运行 Host/closeout 实现；不能用选中 Snapshot 冒充本 Attempt actual fact，也不具备 Topic 5 恢复权 |

直接测试显示新进程 recovery-check 仍只做 preflight：test_execution_trace_adapter.py:471–513 明确断言 target 尚不存在；其 safe-pause builder 使用 model-api/legacy 路径。archive_helpers 的空 Skill lock 正例大量 mock 了 archive/model/schema 校验，不能当作真实 no-Skill 整链证明。上述都是静态阅读结论。

## 4. 人工再启动与 Topic 5 分界

| 情况 | 本入口可做的有界动作 | 触及恢复语义时的停止点 |
|---|---|---|
| 人类在新窗口明确继续一个项目，有完整 Main State | 按获准 refs 读 protocol/最新 checkpoint；运行/呈现既有检查；人类/main 明确本次任务、权限、预算与下一动作，再以现有执行入口开始新工作 | 不能把 resume-check PASS 当成自动 continuation grant，不能沿旧聊天补决定 |
| 人类带已有材料接入，缺 Main State | Intake 按授权材料整理可证事实/refs、未知/冲突与待确认事项；形成首个真实 checkpoint，保留真实来源；共用现有 Task/Mode/Control 契约 | 不补造历史 checkpoint、accepted Decision、Claim、已闭合 Attempt 或旧预算余量；需改变历史状态/lineage 的问题交人类 |
| 本轮完成后，人类再次启动下一项工作 | main 消费实际 Handoff/closeout 并给出 disposition；在其当前任务写域发布新 checkpoint，显式保存下一动作和未完成项 | 这只证明显式人工工作可续接，不能宣称无旧上下文恢复、故障恢复或跨 Runtime 连续性已实现 |
| 自动压力换届、safe-paused Attempt 的执行消费、进程崩溃、已发出调用结果未知、clean/salvage recovery | 保留已有输出/Trace/失败与未知，停止扩展，给具名 owner 可审阅状态 | 进入 Topic 5 residual；需独立架构/ADR、正式 Task 和该路径的验收，不自动重试/rebind/解锁 |
| 旧 action 已闭合，需程序化消耗已冻结 next action | 可准备本文首个候选的 exact source/next slice 请求草案 | 排他认领并执行新 Attempt 属未来有界 M12 consumer，当前 ENTRY 接合授权不能代替其 activation |

分类依据是目标与状态/权限效果；人工按钮也可能发起 Topic 5 recovery。前端应展示“检查通过 / 待具名确认 / 未知 / 本次 slice 已执行”的实际资格，不能把“继续”按钮变成隐式恢复授权。

## 5. 与当前 ENTRY 接合的具体接点

| 本 workstream 切片 | 可复用/应保存的接点 | 本页给 Root 的边界 |
|---|---|---|
| ENTRY-01/02 | role baseline 指令、显式输入 snapshot、Protocol/Task/Method frozen refs、初始 Main State | 可从零或材料接入构造本次工作基座；两类入口共用契约，不新增“接续 Mode”或伪造 Skill |
| ENTRY-03 | Resolver selection → Snapshot → Bundle-bound View → Host → actual Trace/Receipt/output pins | 续接只消费新的合法 frozen execution input；freshness/binding 失效时返回 Resolver，不由 consumer 替换 |
| ENTRY-04 | 动态 child Task/预算/状态、取消/失败/unknown、实际结果 refs | 当前获准 main 动态委派接合不等于 multi-Agent recovery；未来暂停/重启 child 另定义 |
| ENTRY-05 | main 对 closeout/Handoff 的实际消费与 disposition；唯一控制状态提交者；新 checkpoint 的明确 next_actions | 工件 producer、main semantic disposition、科学/Human acceptance 分开；本次成功也不等于整个 Task 完成。列表继承/旧动作清理需在 main producer 中显式处理 |
| ENTRY-06 | Guide 获准 Main State 快照与必要 refs | 独立只读解释；问答不自动回传 main、不提交科研状态或项目记忆；采用意见须经显式研究入口 |
| ENTRY-07 | 实际读取面、输出/校验范围、失败与剩余项的可读报告 | 当前接合验收与未来 M12 验收分别留证；本窗没有产品测试证据 |

这些是与 Root 实现的接口建议，未检查其他窗口的新代码，也不赋予其他文件写权。M12 不新增为 M5/本入口的 hard dependency；当前 ENTRY 可先按其授权完成。

## 6. Phase C、Topic 5 ADR 与 task-definition 前置

canonical [TASKS](../../../../TASKS.md) 和 [ROADMAP](../../../../ROADMAP.md) 仍规定：M10-001 → M10-002 → M3-009 → M10-003 的 machine prerequisites 已 DONE，Human semantic review / R2 Phase C closeout 独立 pending；M12 仅 RESERVED。M3-001～007 的 PARKED 不抹去 bounded v0.x 能力，也不能直接重开为泛化 recovery umbrella。

| 前置审查工作名称（候选，非 canonical M Task） | 依赖与责任 | 可审阅接受条件 |
|---|---|---|
| Phase C 最小表示的有限语义收口 | 路诚钺作语义决定；黄毅给 execution fact/gap 接口意见；以 exact candidate HEAD、两 manifest 与实际 closure 为输入 | 具名接受限定范围 / 指定 exact 修正 / 暂缓并列出缺口；区分 Unknown/Assumption、Execution Failure/Research Failure、from-State/predecessor/reopen basis；保留时间因果、per-Attempt actual-binding gap、Contradiction/Frontier 未全面覆盖、synthetic/science 限制 |
| Topic 5 单条已冻结 action 接续的 R2 架构/ADR | 上项真实收口后独立接受；路诚钺维护控制/状态语义，黄毅维护执行 consumer；不能迁移 PR72 普通文档批准 | 决定 source boundary、Research State/Main State/Attempt refs、唯一 writer/claim、no-Skill 版本投影或最小兼容扩展、direct consumers、读写/预算/失败边界；绑定当轮 candidate HEAD/字节 pins 与所消费 Phase C 决定 refs |
| 首个 bounded continuity 的 docs-only task-definition | 独立 Topic 5 R2/ADR 及兼容选择已接受；由具名 owner 定义并走 DEVELOPMENT 的任务治理 | 在 canonical TASKS 分配正式 ID、owner、risk、hard deps、允许读取/独占写域、outputs/acceptance/negative boundaries；定义与实现分离，不能同时造 Task 并置 DONE |

参考 PR137 的 `M12-001` 仍是候选标签，本页不分配任何新 M12 编号。机器 PASS、CI、普通 APPROVE、应用入口实施批准或 main 自动判断均不能代填以上具名决定。Topic 5 设计审查的候选准备不表示已获其 accepted architecture status。

## 7. 最小实施候选名称、依赖与验收

以下是供人类审阅的任务候选，均 **PROPOSED**；只建议首项进入未来首批 task-definition，其余在真实需要时另定义。责任分工也是提案，不代替正式 owner 接受。

| 候选名称 | 建议依赖 / 风险 / 责任 | 建议验收与停点 |
|---|---|---|
| 已闭合 action 后的新进程单步接续 | formal hard Task deps 建议 M10-003、M3-009、M11-004；另须上一节全部具名 activation；R2；路诚钺负责语义/投影，黄毅负责 consumer/执行事实 | 同 Task revision 的旧 A 已 actual closed/replay-valid；源进程退出前冻结不同 next action B 与唯一 target ID/path；新 OS process 只按 refs 执行 B 一次；新 output/actual Trace/Validation/generic Receipt 冷 replay；旧源 bytes 不变；source/next/permission/Human/freshness/binding 漂移零调用；重复请求/两个进程争同一 target 只有一个认领者；缺 actual facts/output 或 capture gap 不得成功闭合；无 retry/fallback/rebind。Receipt 保持 action slice-only / task_completion false |
| safe-paused 单 Task 的显式新 Attempt 消费 | 首项经验与真实 safe-pause 需求；独立 Topic 5 R2/ADR/正式定义，精确 deps 到时确定；既有 prepare_recovery_attempt 只是可复用前置 | 可审阅的停点确在安全边界；无 in-flight/未知外部副作用；完整冻结预算与新 Attempt lineage；证明新执行消费而非只返回 seed；旧 archive 不改；失败/未知阻断，不能用 completed-action 正例代验 |
| main 上下文的有界换届与 Handoff 信息损失抽查 | 真实 Context Snapshot 指标、既有 Main State/Handoff refs；独立 R2 定义，首项后是否硬依赖由需求决定 | fresh main 仅加载 protocol/小型 state/明确下一动作；约束/决定/失败/unknown 条目可定位且不丢失；压缩/human sample 按风险触发；记录实际读取量/人工修正/不可测成本，不能仅以 checkpoint 存在宣布恢复成功 |

首项可复用 PR137 的 A/B 本地整数程序思路，但本轮没有构造 fixture、许可材料、执行 manifest 或运行程序；旧 reconstruction timeout、旧输出/Run、mock/no-Skill 样例均不能变成本次执行授权。

首项的排他 claim 必须是写域内真正原子认领，不能以 recovery preflight 的 `exists()` 判断替代。认领后崩溃或结果未知，保留目标目录/partial evidence 并停止；首项只保证一个冻结请求的本地排他消费，不声称外部副作用 exactly-once 或自动崩溃恢复。

## 8. 短期与远景

短期：Root 完成本次 ENTRY 的 main/Handoff/state 接合；为未来 continuity 保存明确 refs 和资格，但保持普通人工再启动可用。M12 审查从已有候选与实际 baseline 差异开始，先处理 Phase C 具名输入，再推进一个最小离线 fresh-process Task。

远景按可复现故障触发：safe-pause 消费与 context rollover；之后才讨论跨 Runtime/多 writer、in-flight 与外部副作用、clean/salvage、多 Agent 生命周期恢复。各项须独立展示 failure、owner、权限、状态与验收需要，不预设固定 DAG、Supervisor、数据库或 message bus。Skill-bearing extension 可在确有需求时接现有 release projection；no-Skill 路径不以 Skill admission/M5/M14/M13 解冻为新前置。

## 9. 验证范围、风险与 Root 下一动作

本轮只做文档规划、指定 source/interface/test 的静态阅读、输入与交付文件 hash、两份文档内部链接/范围检查。没有运行产品/测试/安装/Provider/API/生产 Tool，没有读取 Key/账/private oracle，没有代码/Schema/Registry/Task authority/PR137/Git commit/push/primary memory 写入。

未证明：产品手动整链、当前 Root 新实现、fresh-process action execution、进程 kill、安全暂停消费、跨 Runtime、科学正确性或上述具名接受。reference closeout 中的 manifest/24-source 核验和 hosted PASS 为其历史输入，本窗未重新认证。

Root 下一动作：
1. 读取本页与 COMMUNICATIONS，核对交付 hash；将 PLAN-M12 记为本分支“规划输出完成”，候选实施仍未启动。
2. 在 own-row continuity 更新时采用下一节 proposed entry，先回读 primary 最新内容；本窗不写 shared memory。
3. ENTRY 实现遇到本页分界时保留候选/失败/unknown，停止越界 slice；Phase C/Topic 5 决定由具名 owner 单独处理。本轮 PLAN-M12 交付后停止。

## 10. 给 Root 的 PROJECT_MEMORY proposed entry

> 2026-10-07 | AUDIT-RWB-ENTRY-001 / PLAN-M12：指定 codex/research-entry-integration@d3c4d232 的独立窗口完成 m12/PLAN.md 与 COMMUNICATIONS.md（hash 以 Compact handoff 为准）。已静态核对 context/checkpoint/resume-check、Handoff transfer 与 legacy recovery preflight；后者仅返回 safe-paused 旧 archive 的 distinct Attempt seed，不创建/执行。区分当前人工再启动/缺 Main State 有界接入与 Topic 5 恢复；首候选沿 PR137@2f1b9850 的 closed action→fresh process→one frozen next action→unique Attempt，Phase C Human/R2、Topic 5 独立 ADR/兼容选择与 docs-only canonical task-definition 仍前置，M12 RESERVED 不变。来源：RWB-RESEARCH-ENTRY/TASK_PACKET、m12 两文档、d3c4 context/recovery/直接tests 和 pinned PR137 候选；验证仅 MD 链接/范围/hash/static source，不含产品测试/API/Tool/Key/账/安装/接受。只写两 MD、无 primary memory/PR137/代码/Schema/Registry/Git 操作；Next：Root 接收规划并继续自身 ENTRY 授权，具名审查另议；PLAN-M12 窗口停止。
