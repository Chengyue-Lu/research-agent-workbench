# CHAIN-DEV4-003 Compact Handoff

2026-10-07；Profile：bounded implementation worker；required-Skills=[]；路诚钺控制、黄毅审核 API 接点，正式接受仍待审。本片段为 PR140 checkout 中未提交开发候选，不表示全链已通。

来源：[Intake Task Packet](DEV4_INTAKE_TASK_PACKET.md) SHA-256 `7fdf611dd9ae5618eca663dec4376ca03f8eec77d026ab27e65df10e8c644c75`；[总 Packet](TASK_PACKET.md)；[前片段交接](DEV4_HANDOFF.md)；[本片段通信](DEV4_INTAKE_COMMUNICATIONS.md)。仅新增 [intake_call.py](../../../../../src/research_workbench/entry/intake_call.py) 与本片段两份记录，未修改既有 compiler、roles、driver、Schema、Registry、tests、config 或 primary memory。

## 接口和调用接点

`IntakeCallBudget(input_reservation_tokens, max_output_tokens, max_total_tokens, max_seconds)` 明确单轮预留；正整数/有限时间且 reservation 不超过所给总 token ceiling。实际 Session 的总 token 上限取这次预留。

`call_intake(root, *, intake_task, intake_profile, protocol_ceiling, task_ceiling, provider, model, directory, budget, context=None, data_policy=None, external_upload_authorized=False, before_dispatch=None, cancel_requested=None, clock=...)` 返回 `IntakeCallResult`。

- 独立 intake Task/Profile 和人类 Protocol/Task ceilings 均显式传入。读取只走 intake Task exact input refs，compiler 可能读取的 ceiling input refs 必须包含于该集合。
- 复用 `build_role_request(role="intake")` baseline、完整控制 schemas 和 pinned inputs；context 同时携带固定 ceiling，不能用模型猜权限。随后只运行一个无 Tool Session；没有 fallback/retry。
- 使用 Task/Profile 权限交集检查输出目录，fresh directory 独占。网络/data policy、区域、local-only/ZDR 和需要外传许可时的显式 caller flag 在调用前检查；`ProviderRegistry.require` 校验配置能力。`before_dispatch(request)` 必须返回严格 True 才放行，供 Root 连接现有授权/body/预算 guard。
- 在 Provider 边界记录真实 attempted model calls；即使响应被 Session contract 拒绝，也尽可能保存标准化受控响应。发送失败没有响应时不会把实际 calls 改成 0 或 usage 填成 0。
- `complete` 响应、已知 usage、Session 完成及 compiler 校验全部通过后，才调用现有 `persist_control_draft`。保持其 schema/ceiling/hash 和独占发布规则，不增加 source qualification/Method/Human 接受逻辑。

`IntakeCallResult.status` 为 `success`、`not-started`、`rejected`、`failed`；另有 reason/details、真实 calls、in/out tokens、reserved/held tokens、Session status/stop、真实 draft/artifact/report refs。未授权写域或目录已存在时返回明确拒绝且 `report_ref=None`，不在别人的目录写拒绝记录；Root 应将返回结果保存在其已授权父记录。

`result.as_role_observation()` 提供实际 usage/pins 给现有 `run_research_workflow(prior_usage=...)`。只有成功 draft 才启动下游；失败/未知不能作为新 Run 重置。Root 保留 intake result 的精确 reservation/held 值；当 intake 与 workflow 的每次预留参数不同，现有 prior_usage 的未知 hold 推导不能替代 intake 的原始预算记录。

## 受控结果和原件

授权输出目录保存 inputs、binding、request、response、Session、事件日志、result.json 和 REPORT.md；成功另含现有 compiler 发布的 draft 子目录及真实 pins。结果包含停止原因和 usage，不把无 draft 当成功。

原件为 provider-neutral normalized evidence，不保存 transport headers、凭据解析结果或异常消息。复用现有 `sanitize_trace_value`，先转换所有 dataclass 再检查嵌套内容；秘密/隐藏推理形状的请求阻断发送，响应按既有 redaction 策略保存，含被删改输出正文时不发布 draft。用于此要求，实际阅读了该既有序列化/脱敏公开接口及规则，没有更改它。

没有伪造 Host、Receipt、Skill admission、Runtime/source/live qualification 或 Human acceptance。Provider capability snapshot 只表明配置观测；source qualification 和真实 authorization 仍来自 Root 的外部契约。

## 验证事实与范围

源 SHA-256：`03717b2d7cb0bf6267e7082301697fa2eef3b41ab0c80f1319bb28bdeee9f913`。

完成静态 `ast.parse` 和内存 `compile(..., "exec")`，没有执行该 code object、import 项目模块或运行产品测试。完成新增文件尾空白/行末、Markdown 相对文件链接及内容 hash 检查。没有安装、API/Tool、Key/账/预占、Git mutation、primary/global memory 写入。

实际阅读：三份入口 Packet/交接；intake.py/guide.py 的接口实现；roles 的 baseline、document_bytes/read_pinned_inputs/build_role_request；workflow 的公开 Observation/prior_usage 接点；models port、Session limits/状态/usage 聚合与单轮 loop；既有脱敏序列化接口；主 checkout PROJECT_MEMORY 的当前 M5/RESEARCH-ENTRY 导航片段。未读取 Root 新测试文件、账或其他准备代理输出。

Root 反馈前片段 6 项 bridge tests PASS、Tool-failure 后阻止下一 Model 请求；这是 Root 的反馈，没有由本片段重跑或验证。Root 正把 roles request payload 改为 compact JSON，保留 published document_bytes；本接点继续直接调用 build_role_request，保留全部 schema/输入内容，不截断 schema、不改变 wire guard。实际 API 仍由 Root 在现有 body/预算/source guard 下执行。

## Root 应测的关键正反场景

1. 正常 local/configured remote 单轮 complete + 已知 usage → ceiling-valid draft；用 pins 从实际文件核对 compiler 输出，下游使用同一 Run 的 intake usage。
2. 权限/Profile/model/data/region/ZDR/外传许可或 output scope 不足；既有目录/非法路径；非法预算/ceiling；必须 0 Provider calls，返回明确原因且不覆盖原目录。
3. before_dispatch 不是严格 True、调用前取消/deadline、无效时钟：未开始，0 actual calls，无 draft。
4. failed send、Provider exception、invalid response contract/identity、未知 usage 或捕获失败：actual attempted=1 不丢，未知保留预留，不发布成功 draft，不 retry/fallback。
5. refusal、length/paused/error/STOP 等非 complete、unexpected Tool 或 compiler 拒绝（重复 JSON key、越 ceiling/权限/输入等）：保存已产生原件及具体停点，不产出成功结论。
6. request/context/response 中 credential/认证头/隐藏推理形状内容：受控记录按既有脱敏规则处理，敏感正文不进入请求或 published draft；Provider exception 不保存任意 transport message。
7. Session/报告或 draft 部分发布 I/O 失败、发布前后取消/超时：保留实际 calls/usage 和已存在的局部原件，不把 partial publication 作为成功。
8. Root compact 完整 schema 请求经过实际 wire body guard；不把 archive JSON 文件大小冒充 provider wire 大小，不削减 schema 内容以规避 guard。

## 限制与后续

本片段未运行产品/API/Tool 测试，不能据静态检查宣称接口已通过。标准化响应无法序列化或写盘失败时，只能保存已经持久化的调用/捕获失败事实；原始 transport journal 由 Root 的现有外部层负责。同步 Provider call 的硬超时/取消由 Adapter 负责，此处在调用/发布边界复核，并保留超时后果。

发布沿用 existing compiler 的部分失败保留规则，不提供全目录事务。若最后报告写入失败，返回 failed 且不提供有效 report_ref；局部文件不能独立当作完整成功报告。此接口不包含 CLI/包顶层 export、整体 caller 组合、resolver/freeze/Host/checkpoint/Guide 的调用，均按既定 ownership 留给 Root。

建议 Root 重读并更新 primary PROJECT_MEMORY（本片段无写权）：

> 2026-10-07 · CHAIN-DEV4-003：新增 entry/intake_call.py，接 ModelProvider 单轮无 Tool intake → 既有 compile_control_draft/persist_control_draft；明确 success/not-started/rejected/failed、真实 calls/未知 hold、受控 request/response/Session/可读结果及真实 pins，供同一 Run 的 prior_usage 消费。本地未提交候选；仅静态 AST/compile/链接/格式/hash 检查，产品/API/Tool/Key/账/预占/Git mutation 0，未 source/live/Human 接受。来源 chain-proof-002/DEV4_INTAKE_HANDOFF.md、DEV4_INTAKE_COMMUNICATIONS.md。下一步 Root 执行正反测试、接现有 wire/body/预算/source guard，并按路诚钺/黄毅具名范围审查接受。
