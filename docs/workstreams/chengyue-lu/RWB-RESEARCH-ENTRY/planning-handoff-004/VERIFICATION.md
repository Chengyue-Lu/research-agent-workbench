# Planning / Handoff 验收记录

2026-10-10，PR140 未合并候选。本文件将本切片的实际检查、安装消费、API 产物和冷回放按来源分别记录。当前执行仍在进行；未完成项不视为通过。

| 桥接 | producer → contract → consumer | 本轮检查 |
| --- | --- | --- |
| planning 身份 | exact Method 决策 → planning-capability-slice → factory/Bundle/View/Host/Receipt | 首轮101检查100通过、1正例输入错误；补充明确的执行暂停条件后该正例复测通过。原校验规则保持 |
| 正式 child Handoff | 实际 child 输出/Receipt → pinned HandoffPacket → fresh main | 确定性检查通过；0/1/3 子任务与独立冻结、实际结果及正式 packet 消费通过 |
| 收尾与状态 | 固定 workflow report → final Handoff → checkpoint/Human 待办 | 确定性检查通过；子任务限制、冲突、未解项、人类待决与 safe-paused 继续传递 |
| 兼容和消费 | 原 Action/Skill closeout 原件 → 新消费者；安装包外消费与模型零调用回放 | 执行及旧 Action/Skill closeout 回归通过；安装包外 no-Mode planning 执行及独立冷回放通过；实际 API 首轮已执行并停止，后续验证进行中 |

本轮178个不同最终用例通过，包括101个 planning/执行回归、74个 Handoff/入口及3个文档检查。planning 首轮的1个正例输入错误、Handoff 首轮的1 error及同一 caller 用例的两个子场景失败均保留；修复后的1 planning、11 Handoff/state及1 caller复测计入原用例，不重复累计。

静态审查发现并修复了重复 Receipt 误计交付数量、原始路径前缀可越 Task 写域两项反例；对应实际 Receipt/产物及路径反例检查通过。最终负面聚合还出现 inherited/generated 未解说明重复违反 stringArray.uniqueItems 的真实失败；保序去重后状态与0/1/3 caller复测通过，Schema及原断言保持。未知用量、failed/partial、H2 缺证据和 required Skill 未加载的事实继续保留。交付数量的检查范围是经验证 Receipt 声明的实际 artifact contract、hash与计数；具体方法/产物内容质量依各自消费者验收。

M1-010/M2-009/M11-008 保持 IN_PROGRESS。该 Core 支持扩展归 M11-008，M1-010 的原入口定义未改写。工程材料仅触发受控读取、Method 控制与 generic Trace；Source/Evidence/Claim 及研究语义 MethodTrace 的消费者在声明相应研究场景时分别验收。后续实际结果将在此表中更新。

## 安装消费与实际 API 首次停点

独立 CPython3.11.16 在 checkout 外使用新 wheel 和默认包内 schemas，完成 actual intake→factory/caller→planning main 两次离线 port 调用（known76/held0）；另一个新进程验证 planning Receipt 和正式 Handoff，调用模型0次，独立 Handoff Skill checker通过。fixture Task 的 required_output 为 method-resolution，但执行 Receipt 声明 deterministic-check-report；正式 Handoff 如实保留 safe-paused 和 missing-output 未解项。Root 安装探针先后用了错误的完成预期、字段及 contract；三份失败日志保留，纠正探针时未改产品、Task 或 Schema。

首个实际 API 来源为 `b696272feb062573aef1ccebfda9c7281cb88877`，Attempt `chain-5fe36117-5047-4ae5-8a4e-fbd4cb1c58bb`。3次 HTTP/1次 readonly Tool、31.765秒；actual intake、planning main 两轮及1份 planning Receipt 已完成，正式 final Handoff保留 safe-paused。主 Agent 自选0个 child，其返回含正文和 fenced JSON，严格控制解析拒收；checkpoint/Guide未开始。实际新增 known15,408/held0，累计287,277/held0；完整账与原件闭合，模型零调用冷回放验证了真实停点。该 Attempt 不记为整链通过。

主/子 baseline 和 workflow 控制指令随后明确 entire final response 是一个 raw JSON，判断依据放既有字段。Guide、主Agent决定0..N、严格解析及 Schema 未改；12项实际角色请求检查通过。首次178项和新增12项共190个不同最终用例。新源码及新 Attempt 将独立记录，不覆盖首轮。
