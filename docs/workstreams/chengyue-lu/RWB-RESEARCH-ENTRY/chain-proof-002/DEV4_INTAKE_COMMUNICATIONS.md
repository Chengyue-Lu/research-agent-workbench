# CHAIN-DEV4-003 通信记录

2026-10-07；[Packet](DEV4_INTAKE_TASK_PACKET.md)；[Handoff](DEV4_INTAKE_HANDOFF.md)。只记录有界开发可见指令、更新与静态检查，完整运行 Attempt 由 Root 负责。路径按仓库相对 locator 规范化；不保存隐藏推理或逐文件打开记录。

## Root 委派

> 继续有界开发 CHAIN-DEV4-003。唯一新入口 Packet：docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/DEV4_INTAKE_TASK_PACKET.md。仅新增 entry/intake_call.py 及本片段 handoff/communication；补实际 intake Model 端口到现有 compiler/persist 的调用接点，保留成功、未开始、拒绝、失败与 usage/原件。你不独自在代码库，Root 正在测试既有三个改动，不回滚他人内容。不得运行产品/API/Tool测试、Key/账/预占、安装、Git mutation 或写 primary memory。先读 Packet 后按限定实现，超范围明确停止。Root 负责所有测试与真实 API，正式接受仍待具名 owner。

## Root 的中途互斥写域通知

> Root 测试进展及互斥写域通知：CHAIN-DEV4-002 实际桥接测试发现 Tool handler failed 后仍会发送下一模型请求，Root 已仅在 driver.run 的 cancel callback 合并 failure，保留 Session/已知 usage，相关6项桥接测试全部PASS。另发现 intake full-schema request 的 pretty JSON 占用近53,370 wire bytes，超过既有32,768；Root正在 roles.py 将 request payload 改为compact JSON（不改published document_bytes），测得同内容约30,179 bytes。你只继续 intake_call.py 的限定ownership，不修改 driver/roles 或测试。请在 handoff说明调用build_role_request保持全部schema/输入内容，实际API仍Root控制既有body/预算guard。

未把这些反馈转换成本片段亲自验证的事实，没有读取 Root 的新测试内容或修改 driver/roles/tests。

## 可见开发更新

1. 我会先读 CHAIN-DEV4-003 的 Packet，确认 intake 端口与现有 compiler/persist 的接点，再只新增指定模块和交接记录。既有三个文件由 Root 测试，我保留其当前改动；本片段仍只开发和静态检查。
2. 现有 compiler 已负责校验 ceiling 并独占发布 draft，缺的是把实际 intake Session 接进来，并统一记录调用与结果。我会复用 compiler；只有完整响应、已知 usage 且编译通过时才发布成功，其余情况保留未开始、拒绝或失败原因。
3. 调用接点已新增：单轮、无 Tool 的 Session 后直接接现有编译与发布函数，实际调用数在进入 Provider 时记录。第二轮静态审查会重点看拒绝时的写权限、失败发送后的未知 usage，以及报告是否足以解释未发布 draft 的原因。
4. 模块的静态语法检查已通过，调用参数、状态和停止原因都已写入实现。交接会说明如何把 intake usage 接入同一 Run。Root 正在做 compact request 的改动，我没有修改 roles.py；本接点继续通过 build_role_request 保留完整 schema 和输入，实际 API 的 body／预算 guard 由 Root 控制。

## 操作和固定输出

- 14:51:01 UTC 开始；20 分钟/两轮预算。起始 Git status 包含既有 config/driver/executor/workflow 和 chain-proof-002 目录，不属于本片段新增写域。
- 第一轮新增一个 application intake port、实际 Provider 边界计数/受控捕获、既有 compiler/persist 接合和四种结果。
- 第二轮静态检查后补 Profile 权限、明确拒绝 detail、发布边界检查与局部 I/O 失败保留。没有调用产品、Provider/API、Tool、Key/账或生产预占。
- 15:05:52 UTC：标准库 ast.parse 和内存 compile 通过；未执行 code object 或 import 项目模块。新增源 SHA-256 `13e75ef38cf40f961cb697690ae6913b0ff98723a659f87e79bb566120640fb1`。Packet SHA-256 `7fdf611dd9ae5618eca663dec4376ca03f8eec77d026ab27e65df10e8c644c75`。
- 返回前检查本片段新增文件格式与内部 Markdown 文件路径。Git status 仅用于核对共享工作区元数据，没有 add/commit/push/install 或修改别人的内容。
- 15:07:55 UTC：静态审查补实际 output usage 不得超过 dispatch cap；最终源 SHA-256 `03717b2d7cb0bf6267e7082301697fa2eef3b41ab0c80f1319bb28bdeee9f913`。AST/内存 compile 通过；两份输出内部 Markdown 文件 target 0 errors；三份新增输出 trailing whitespace 0。上述 15:05:52 hash 是此前静态快照，不作为最终 candidate pin。

Handoff 列 API 参数、正常/阻断场景、尚未验证事实、whole Run usage 接续条件及 primary memory 待应用条目；正式接受及所有实际验证保持归 Root 和具名 owner。

## 返回前向主准备窗口报告

15:09:11 UTC 后，延续用户授权同步给同一 `01a1064a-eaef-7da0-aebd-962910ff42b8`（RWB M5-008 续接）；工具确认送达。路径规范化后的正文：

> 接续用户授权的主准备窗口同步：CHAIN-DEV4-003 已冻结有界候选，仅新增 entry/intake_call.py 与 DEV4_INTAKE_HANDOFF/COMMUNICATIONS。源 sha256=03717b2d7cb0bf6267e7082301697fa2eef3b41ab0c80f1319bb28bdeee9f913。
> 公开入口：from research_workbench.entry.intake_call import call_intake, IntakeCallBudget。call_intake 显式 intake_task/intake_profile、protocol_ceiling/task_ceiling、provider/model、fresh directory、budget，另可给 context/data_policy/external_upload_authorized/before_dispatch/cancel/clock。IntakeCallBudget 四字段 input_reservation_tokens/max_output_tokens/max_total_tokens/max_seconds。结果 success/not-started/rejected/failed，真实 calls/usage/held 与原件/pins；as_role_observation 用于同一 Run prior_usage。
> 交接：docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/DEV4_INTAKE_HANDOFF.md；sha256=3622933b5a7907691c12c4213c469971591ccb5952dbfc6a777dc4a52c330e84。
> 保留 build_role_request 完整 schema/输入，未改 roles/driver 或你的 tests；before_dispatch(request) 接现有实际 source/body/预算 guard。无产品/API/Tool/Key/账/预占/install/Git mutation/primary memory 写入；仅静态 AST/内存 compile/格式/内部 Markdown links/hash 通过。Handoff 列8组应测场景、未测事实及 memory 待应用条目。关键边界：compiler 读取的 ceiling inputs 必须已在独立 intake Task read set；拒绝写域/目录冲突返回 report_ref=None，由已授权父记录接收；不同 intake/workflow 预留参数时不能用 prior_usage 的推导替代 intake 原始 held；原件 normalized/sanitized，不保留认证头/hidden reasoning。仍待 Root 全部测试及具名接受，不宣称全链通过。
