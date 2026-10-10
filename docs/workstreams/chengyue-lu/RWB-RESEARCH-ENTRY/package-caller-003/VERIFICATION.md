# 包内入口验证

本轮已补齐包内受信 factory/caller，并完成已支持 Action/no-Skill 路径的离线、安装包外部消费和冷回放。三项 Task 保持 IN_PROGRESS；实际 API 尚未开始。证据与缺口分开记录，避免把选定路径接通当作整项验收。

## 模块实际做了什么

| 模块 / Task | 测试输入 → 实际输出 → 直接消费者 | 当前结果 |
| --- | --- | --- |
| intake 产物桥接 / M1-010 | 明确的需求、材料 pin、独立 ceilings → 实际发布 Protocol/Task/Method/Requirement 草稿和调用报告 → caller 重读事实和精确 refs | 离线通过；控制模板转录不评价自由需求规划质量 |
| 包内 caller | 实际 IntakeCallResult、已发布报告、显式 factory、总预算和原 deadline → workflow 与被消费工件 refs | 成功成本计入一次；失败/unknown 零 workflow，原成本/hold 保留；替换、drift、截止与取消反例通过 |
| 包内 factory / M11-008 | 实际 Task/Profile/Method/Requirement、外部 Supply/evidence、独立 observer/verifier → 真实 FACTORY pin、Snapshot、Bundle、View → FrozenRoleExecutor | Action 路径通过；禁止 fixture 资格提升、歧义供给、缺 Skill、越权 Tool 与实际 binding 漂移 |
| main / children / M2-009 | baseline/Profile/本次 Task/输入快照 → main 自选 0/1/3 子任务 → fresh child 结果与 Receipt refs → 新 main 消费 | 离线通过；整 wave 预检、共同预算、失败预占和未开始兄弟任务保持；当前派发顺序执行 |
| readonly Tool | 明确 Tool 映射、Task 文件 pin、Session reservation → 实际 Tool 结果 → 下一模型请求、Trace、Host、Receipt | 离线通过；缺映射、写效果、handler failure、超大结果等留失败事实 |
| checkpoint / Guide | hash-matched workflow＋Protocol → MainState 与 Human 待办 → 独立只读 Guide | 离线通过；前置状态漂移阻断，Guide 无 Tool/自动回传，项目字节保持 |
| 安装与冷回放 | checkout 外独立 CPython3.11.16、安装 wheel 默认 schemas → actual intake/main 2 次离线 port 调用、known76/held0、真实 FACTORY/Receipt pins → 另一新进程直接文件验证 | 通过；冷进程调用模型 0 次。已核安装后的 caller/factory 与本轮 source SHA 相同 |

## 验证证据及首次失败

- 包内与直接桥接：82 项检查通过，覆盖 caller/factory、freeze、executor、动态主子、Tool、intake、预算、Guide 与 checkpoint。
- 补充 intake/Driver/control chain/文档及 Requirement 缓存：21 项通过。首次 planning 正例暴露 Runtime Bundle 不支持 planning 身份，完整失败保留。
- planning 早期 block 与原 Action 正例复测：2 项通过；原 Action 为重复验证，不叠加 unique 总数。当前三套合计 104 个不同最终用例通过，规划执行成功没有计入。
- 首轮20项的3 failures/1 error保留：Requirement 漂移已有下游拒绝但缺 factory 同级重读；子任务正例使用了过大预算；未声明 Requirement 反例使用无效 ID。修复后保留原规则与断言。

详细 stdout、worker 通信、输入/版本 pins、安装 probe 与冷回放回执位于本轮 ignored 档案；评审先读此表。此前15个实际链路 Attempt 的结果绑定旧来源，不替代本轮包内接口证明。

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

累计 API 账在本轮前置核验为 known246,860 / held0，上限10,000,000。新增实际请求只在既有授权时窗及每请求 fresh 官方闲时条件满足后开始；实际结果在这里追加。
