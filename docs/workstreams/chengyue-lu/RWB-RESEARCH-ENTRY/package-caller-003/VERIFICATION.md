# 包内入口验证

本轮已补齐包内受信 factory/caller，并完成已支持 Action/no-Skill 路径的离线、安装包外部消费、真实 API 和冷回放。三项 Task 保持 IN_PROGRESS；planning 与正式 Handoff 的缺口仍未完成。证据与缺口分开记录，避免把选定路径接通当作整项验收。

## 模块实际做了什么

| 模块 / Task | 测试输入 → 实际输出 → 直接消费者 | 当前结果 |
| --- | --- | --- |
| intake 产物桥接 / M1-010 | 明确的需求、材料 pin、独立 ceilings → 实际发布 Protocol/Task/Method、可选 Requirement 草稿和调用报告 → caller 重读事实和精确 refs | 离线与本轮实际 API 通过；API 场景使用显式外部 Requirement，来源单列。控制模板转录不评价自由需求规划质量 |
| 包内 caller | 实际 IntakeCallResult、已发布报告、显式 factory、总预算和原 deadline → workflow 与被消费工件 refs | 成功成本计入一次；失败/unknown 零 workflow，原成本/hold 保留；替换、drift、截止与取消反例通过 |
| 包内 factory / M11-008 | 实际 Task/Profile/Method/Requirement、外部 Supply/evidence、独立 observer/verifier → 真实 FACTORY pin、Snapshot、Bundle、View → FrozenRoleExecutor | Action 路径离线与实际 API 通过；API 中初始 main、child、新 main 分别冻结。禁止 fixture 资格提升、歧义供给、缺 Skill、越权 Tool 与实际 binding 漂移 |
| main / children / M2-009 | baseline/Profile/本次 Task/输入快照 → main 自选 0/1/3 子任务 → fresh child 结果与 Receipt refs → 新 main 消费 | 离线0/1/3通过；本轮实际 API 主 Agent 自选1个 child，完整结果进入新 main 请求并被响应引用；整 wave 预检、共同预算、失败预占和未开始兄弟任务保持；当前派发顺序执行 |
| readonly Tool | 明确 Tool 映射、Task 文件 pin、Session reservation → 实际 Tool 结果 → 下一模型请求、Trace、Host、Receipt | 离线及本轮实际 API 通过；有效载荷与下一份实际 wire 的 UTF-8 bytes 一致，归档文件末尾 LF 单独核验；缺映射、写效果、handler failure、超大结果等留失败事实 |
| checkpoint / Guide | hash-matched workflow＋Protocol → MainState 与 Human 待办 → 独立只读 Guide | 离线及本轮实际 API 通过；Guide COMPLETE、项目字节集合不变。状态解释质量仍有局限，见本轮结果 |
| 安装与冷回放 | checkout 外独立 CPython3.11.16、安装 wheel 默认 schemas → actual intake/main 2 次离线 port 调用、known76/held0、真实 FACTORY/Receipt pins → 另一新进程直接文件验证 | 通过；冷进程调用模型 0 次。已核安装后的 caller/factory 与本轮 source SHA 相同 |

## 验证证据及首次失败

- 包内与直接桥接：82 项检查通过，覆盖 caller/factory、freeze、executor、动态主子、Tool、intake、预算、Guide 与 checkpoint。
- 补充 intake/Driver/control chain/文档及 Requirement 缓存：21 项通过。首次 planning 正例暴露 Runtime Bundle 不支持 planning 身份，完整失败保留。
- planning 早期 block 与原 Action 正例复测：2 项通过；原 Action 为重复验证，不叠加 unique 总数。当前三套合计 104 个不同最终用例通过，规划执行成功没有计入。
- 首轮20项的3 failures/1 error保留：Requirement 漂移已有下游拒绝但缺 factory 同级重读；子任务正例使用了过大预算；未声明 Requirement 反例使用无效 ID。修复后保留原规则与断言。
- 首次 hosted CI 的261项第2分片有1条公共文档断言失败：旧测试逐字要求“任何”，已接受文档使用“任意”。改为检查 Provider Adapter 的具体表行、structural/bounded 等级及账号/配置/Tool/用途资格边界，完整14项 public-surface 回归通过；未改支持承诺或产品代码。原CI日志和修正证据保留，最新提交重新执行CI。

详细 stdout、worker 通信、输入/版本 pins、安装 probe 与冷回放回执位于本轮 ignored 档案；评审先读此表。此前15个实际链路 Attempt 的结果绑定旧来源，不替代本轮包内接口证明。

## 本轮真实 API：测试什么，得到什么

2026-10-10 北京时间18:00后，Root 执行一次安装包版本的闭环 Attempt `chain-081aff32-8d07-47bd-b6db-320fc35cfcbf`。同一供应商的独立会话协作，逐次核验实际时间与 fresh 官方闲时；没有付费重试或 fallback。总共6次 HTTP、1次只读 Tool，Attempt 内耗时57.328秒。使用公开合成文本：alpha 有 id 和 locator，beta 有 id、缺 locator。

| 次序 / 调用 | 模块输入 | 实际输出与直接消费 |
| --- | --- | --- |
| 1 / intake | 明确需求、材料 pin、Protocol/Task ceilings、Method 模板 | 发布实际 Protocol/Task/Method 草稿及报告；包内 caller hash 重读，使用本次 exact refs。Requirement 为独立外部控制，不冒充模型产物 |
| 2–3 / 初始 main 与 Tool | 本次 Task、baseline/Profile、输入快照、冻结 Bundle/View、显式 readonly Tool | 实际调用 Tool 读取材料一次；其返回进入第3份实际请求。main 自行提出1个 child，判断 beta 缺 locator 需要独立核对；caller 验证并派发 |
| 4 / child | main 生成的有界 child Task、独立冻结与精确输入 | 返回 beta 缺 locator 应保留为 unresolved unknown，不从材料推断数值；发布 result 与 Receipt，未再委派 |
| 5 / 新 main | 实际 child 的文本、usage、限制、artifact/Receipt refs 与执行观察 | 完整 child_results 逐字段进入新请求；只有 system/user 两条消息，无初始 main 的 Tool/assistant 历史。实际响应点名 CHAIN-API-CHILD-1、complete disposition，并引用 child 对“无值、占位、默认或推导规则”的具体判断 |
| 无新增模型调用 / checkpoint | 实际 workflow 报告与 Protocol pin | 发布 MainState 与待人类决策：beta 缺 locator 如何处理。接受决定仍为空；正式 Handoff 未触发 |
| 6 / Guide | 独立获准 MainState 快照 | COMPLETE，解释 stage-completed 与下一人类决策；无 Tool/自动回传，项目字节集合前后相同 |

三个角色分别产生实际 FACTORY、Snapshot/Bundle/View 与 Receipt。安装包外部新进程重新校验3份 Receipt/输出闭合及对应 factory/Task/Bundle/View pins，模型调用0次。另一次只读内容核验检查38份本次账原件、98份项目原件、6份实际 request/response：Tool→下一 wire 与 Trace 内容一致，child→新 main 的完整上下文一致，主响应有具体内容使用证据。首次冷核脚本把归档文件和 Trace framing 的末尾 LF 计入 payload，失败原件保留；按实际 framing 显式核验后通过，产品和原件未改。

本次新增 known25,009 / held0；累计 known271,869 / held0，10,000,000上限剩9,728,131。前后历史原件复查一致：当前链16个 closed Attempts，加此前17个历史账；没有重置或漏计旧失败用量。没有新 Source/Skill/Human/scientific acceptance。

Guide 的解释质量尚未验收：其可见快照没有提供已消费的 Tool/出版核验证据，回答保留了“调用未建立、出版 pending”的措辞，不能用 COMPLETE 推断它已准确解释所有现有 Receipt。该可见证据与解释问题属于 [M2-013](../../../../TASKS.md) 后续范围；本轮仅证明真实调用、隔离和状态快照消费。

可复查来源身份：执行代码 `e647fd0b744fc8b41f9ac688d4eccd7821208fc4`，冻结 source root `c3c8191954723775e33340e47cc67b49c095b3fd4085c093c0e8435dd19682e2`。实际 RESULT SHA256 为 `bc77110257a6edcbe26b6792dd1dcc03e9820de2472a85fcc253542ede71c898`。原 request/response/Tool/usage/官方闲时/closed manifests 保留在忽略的本次档案，不含 Key 或认证头；后续文档提交不改变此次执行来源。

## 显式材料场景

| 对象 | 本轮触发情况 | 直接消费者或保留的边界 |
| --- | --- | --- |
| 授权材料 | 触发：公开合成文本与 exact file pin | intake/role 请求直接读取核验快照；Tool 分支直接读取同一 pin 并将结果送入下一模型请求 |
| Source | 未触发研究来源准入：材料仅说明合成接口记录 | 未制造 Source/admission；真实来源消费者仍须在声明该场景时独立验收 |
| Evidence / Claim | 未触发科学证据提取或主张提升 | beta 缺 locator 的结构观察不作为科学 Evidence/Claim；研究证据和 Human 主张接受保持独立 |
| Method / MethodTrace | 触发控制 Method、能力需求和执行 Trace；未触发研究方法应用记录 | 实际 Method pin 进入冻结与执行；generic Trace/Receipt 不改名 MethodTrace。研究方法语义记录与直接消费者仍属剩余验收 |

## 已确认的剩余缺口

1. **planning 执行契约。** 现有 Method 可以声明 `planning_action_id`，而 Runtime Bundle 的 Schema 与 consumer 只接受 `action_ref`。factory 现在在 archive/派发前明确 block。补测没有放宽 validator、替换成虚构 Action 或改 Core/Schema。
2. **Handoff 契约消费。** child→fresh main 和 workflow→checkpoint 已有直接消费；`recent_handoffs` 的索引标签不能证明 Handoff producer 或完整性消费者。现有 HandoffPacket parser 接受空 Skill lock，Schema 的 minItems=1 则拒绝 no-Skill Handoff；该结构反例已实际验证。尚未生产、接受正式/compact Handoff，不制造 Skill lock。
3. **整项验收余量。** 更广的需求/材料、语义 MethodTrace、有效 Skill 装载、角色与环境配置、质量及真实科研场景按各自 Tasks 推进。M1-010/M2-009/M11-008 的完整义务不因本次路径验证自动 DONE。

三项 Task 继续 IN_PROGRESS：本次证明包内 Action 选定通路可真实调用和消费，planning/Handoff、完整场景验收仍按上述缺口推进。
