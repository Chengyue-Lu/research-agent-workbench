# CHAIN-DEV4-002 Compact Handoff

2026-10-07；Profile：bounded implementation worker；required-Skills=[]。当前为 PR140 checkout 中的未提交开发候选，基线 `d630f8e174846f4932d05a7a0d69076930b53ee1`。具名范围：路诚钺负责控制/Trace；黄毅负责 Runtime 接点的正式接受，接受仍待审。

任务来源：[DEV4 Task Packet](DEV4_TASK_PACKET.md)，SHA-256 `b11bcaaa6735364a1b9f2806ec7cbaaf5170481361644c36dd58f95c824ba806`；[总 Packet](TASK_PACKET.md)；[通信记录](DEV4_COMMUNICATIONS.md)。本片段补现有接点，不替代 Root 的入口、资产、全文档校准和全桥验证。

## 已落盘的候选改动

| 文件 | 改动及目的 |
| --- | --- |
| [workflow.py](../../../../../src/research_workbench/entry/workflow.py) | `WorkflowBudget.max_session_model_turns=1` 为兼容默认；每次 Role Session 由 Run 剩余 calls、该 Task 剩余 turns/output/time 裁定上限，预留 `session_calls * (input_reservation_per_call + output_cap)`，未知 usage 保留全额并停止后续调用。日志保存预留 calls 和每次 output cap。 |
| [executor.py](../../../../../src/research_workbench/entry/executor.py) | `FrozenRoleBinding` 增加可选 `tools`、`tool_refs`、`session_limits`；显式 Session limits 不得超过 invocation 已预留的 calls/output/tokens/time。Observation 新增实际 Tool calls、独立 receipt refs，并纳入 Host 的真实输出 artifact pins 与停止诊断。 |
| [driver.py](../../../../../src/research_workbench/entry/driver.py) | 接入显式 readonly `ClientTool`，保持零 Tool 默认。验证客户端名称、组件身份、Task/Profile/Supply 声明、Session 次数/批次/结果字数上限和只读副作用类；构建及每次请求的 Tool definitions 必须完全相等；每次 Provider/Tool 使用前复核绑定、输入、Profile pins、取消及 Session deadline。 |

child 完成后的新 main context 保留原 disposition/summary/limitations/next_actions，并增加 `execution_status`、`usage`、`artifact_refs`、`receipt_refs` 和逐 Session `execution_observations`。嵌套子链 usage 明确标为 child-task-and-descendants，仅用于消费上下文，不再次记账。引用只按 opaque pins 传递，不根据 pins 打开正文或扩展 Task read set。

Tool 客户端名称到 Supply 组件 ref 的显式映射及 definitions hash 存入 Trace decision snapshot。实际 Tool attempt/result events 使用组件 ref，与 Host `tool_invocations/tool_refs` 及现有 generic Receipt 核对接点一致。handler 异常保留失败事件，并使 Host 失败；结果过长保留 Session 的停止事实。unsupported Skill/其他 Supply 路径仍在外部调用前拒绝。

## 接入约束

- 可变 Session 上限由 `WorkflowBudget.max_session_model_turns` 显式配置。若整段 token reservation 放不下，当前实现停止该 slice；不会通过多发请求后再补授权。
- Tools 由可信 binding factory 提供，不能从模型响应中新增。`tool_refs` 必须恰好覆盖 ClientTool names，值只能来自选中 Supply 的 `component_kind=tool` components。Tools 必须提供显式 `session_limits`。
- 当前受限桥要求 ToolDefinition.name 同时在 Task.required_capabilities、Profile.allowed_tool_capabilities 和 Supply.provided_capabilities 中；沿用现有 role builder 的名称检查，不增加别名推断或 Registry 语义。需要不同客户端名称与能力词的映射时，交给具名 owner 明确契约。
- 多轮 Session 的全部可能输出不得超过 frozen Host 总 output budget；factory 可在已预留 invocation 内进一步收紧 Session limits。
- Tool failure、额度不足、未知 usage 或 child failure 仍停止后续调用，保存原因和已有产物。失败 child 不触发额外付费 main Session。

## 实际验证范围

仅使用标准库静态解析三个文件的 AST、`git diff --check`、内容 SHA-256 和本交接/通信文件的内部 Markdown 路径检查。没有 import 或执行项目模块，没有运行任何产品测试、API、生产 Tool、Key/账读取、生产预占、install、commit 或 push。此前基线测试结果不能代表本次改动已通过。

实际阅读范围：本片段/总 Packet、checkout AGENTS/README、docs 导航/Development 和主 checkout 项目连续性摘要；指定三个模块；roles.build_role_request；Session limits/ClientTool 与普通 run 的 Provider/Tool loop；Host、generic closeout、Trace 的相关公开接口。已有 entry tests 仅作接口参考，executor test 全文，driver/workflow 测试的头部和相关函数定位；未读取研究资料、Key、账或其他代理的工作输出。

| 候选源文件 | SHA-256 |
| --- | --- |
| `src/research_workbench/entry/driver.py` | `2fcad33fffdc05215640bb4c073e148a9d6da1f1827134aab911715956ad1217` |
| `src/research_workbench/entry/executor.py` | `33a356423bdf515d386083104ac9f2023ca255d22daf7b47c560497e18276ff8` |
| `src/research_workbench/entry/workflow.py` | `8649b896deedff5d23659dd5bb8b629589582ac3d8cbecccde8d9e7efa1f9685` |

## Root 应执行的关键场景

1. 默认一轮、零 Tool、无子任务的原回归；已知 usage 与真实 artifact/receipt pins 保留，旧 positional 调用仍兼容。
2. main → child（以及有界孙任务）→ fresh main：后续请求收到实际执行状态、正确聚合 usage、真实输出/receipt pins 与原摘要；不打开这些新增 pins 的正文，不重复记账。
3. 显式两轮 Session：一次 readonly Tool 调用后进入下一次 Model response；Trace Provider requests、实际 calls、Tool events、Host、Receipt 和 Workflow reservation 相互一致。
4. procedure Supply 中的可选 Tool、direct Tool Supply，以及不选择 Tool 的角色；不存在所有角色必须调用 Tool 的固定路径。
5. Run calls、Task turns、Task 总 output、总 token reservation 或剩余 time 不足：在对应外部请求前阻断；未知/失败 send 保留整段 reservation，不自动 paid retry/fallback。
6. 缺/多 handler、重复 name、额外 Tool definition、组件 ref 越界、Task/Profile/Supply 任一未声明、未显式 Tool limits、写副作用或 Skill enabled：外部调用前明确拒绝。
7. Tool 结果过长、handler 异常、批次/累计 Tool count 超限、重复 call id、Tool/输入/Profile/绑定漂移、取消或 deadline 到达：不再进入受阻 handler/request；保留真实失败及部分结果，不能产出成功结论。
8. Trace/result 捕获失败、usage 缺失、Receipt 缺失或不闭合：后续 main 不越过不确定事实继续运行；Root 检查报告给出可定位的停止原因。

## 未解决与未接受的事实

这些接口候选尚未经过产品/真实 API/Tool 测试；source/live conformance、Skill、Human 接受及整链完成均未成立。配置错误在 Driver 建立阶段抛出异常；Root 的外层入口需把异常落入明确拒绝报告，不能把未产生 Host/Receipt 当成功。

`ClientTool.execute` 是可信 application-owned callback。此桥核验声明和 frozen permission intersection，不能证明任意 Python handler 真正只读、只读取已授权内容或没有网络副作用；Root 须选用按 exact Task read set 约束参数和实际读取的 handler，并在全桥中验证。结果大小上限控制是否进入后续模型上下文，不替代 Tool 的实现可信性。

完整需求入口 → Protocol/拆分/选择/退回 → 受控执行 → 溯源/结果/下一轮接续的其他 caller、任务定义、资产和检查由 Root 与既定 owner 负责。本片段未扩大 ownership，也未把独立 docs-only worktree 的未合并新定义视为正式接受。

## Coordinator 待应用的 PROJECT_MEMORY 条目

本片段无 primary memory 写权；请 Root 重读主 checkout 最新摘要后保留他人条目，再加入：

> 2026-10-07 · CHAIN-DEV4-002 / PR140 checkout d630f8e：开发（4）在指定 entry/driver.py、executor.py、workflow.py 补 child actual status/usage/output/receipt opaque pins、显式可变 Session turns 的全额预留、readonly ClientTool 映射及 Trace/Host 接点。结果为本地未提交候选；静态 AST、diff 格式和交接链接检查通过；未运行产品测试、API/Tool、Key/账或预占，不代表 source/live/Skill/Human 接受。来源 docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/DEV4_HANDOFF.md 与 DEV4_COMMUNICATIONS.md。下一步由 Root 执行列出的正反场景、落实 handler exact-read 约束、外层拒绝报告，并由路诚钺/黄毅在各自责任内审查接受；保留全文档校准候选未接受状态。
