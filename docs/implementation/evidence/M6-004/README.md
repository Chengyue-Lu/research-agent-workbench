# M6-004 live 验收证据包（AT-API-009）

2026-08-19，黄毅在本机（Windows）对 `worker` 槽执行了一次真实 evidence 调用，
终态 `completed`，`rwb execute verify` 退出码 0。本目录是从该次 Attempt
目录复制并脱敏的工件；原始 Attempt 目录位于 git 忽略的
`work/EVID-API-001/AT-API-009/`。

## 运行参数（非秘密）

- 提供方路由：DeepSeek Anthropic 兼容端点（`https://api.deepseek.com/anthropic/v1`），
  复用仓库现有 `anthropic-messages` adapter；未新增任何 adapter 代码。
- 模型：`deepseek-v4-flash`（经环境变量 `RWB_DEEPSEEK_MODEL` 注入；
  凭据经环境变量 `DEEPSEEK_API_KEY` 注入，仓库与工件中均不出现其值）。
- 任务：`examples/api-execution/task-evidence-live.yaml`（EVID-API-001@1）。
- 本地配置（git 忽略，未随包提交）：`.rwb/pool.local.yaml`、
  `.rwb/provider-adapters.local.yaml`。

## 本包内容

- `INDEX.yaml`：本包每个工件的 sha256 钉定索引；`tests/test_evidence_index.py`
  在每次 CI 中重哈希核对，任何事后改动都会使测试失败。独立复核从它开始。
- `attempt.yaml`、`execution-receipt.yaml`、`handoff.yaml`、`check-report.yaml`、
  `transfer-manifest.yaml`、`handoff-transfer-audit.yaml`：closeout 原子发布的
  完整闭环链。
- `session-transcript.json`：全部 4 轮请求/响应与 7 次工具事件（无凭据）。
- `outputs/`：模型实际写出的 4 个正式工件（2 条 Evidence 对象、
  Handoff Packet、Transfer Manifest）。
- **有意省略** `execution-plan.yaml`：它钉住本机绝对路径（机器特定信息），
  按仓库约定不提交；其哈希记录在 `check-report.yaml` 的 `subject_refs` 中。

## 结果摘要

- 用量（provider 报告）：4 次请求，input 1443 / output 10254 / cached input 27520 tokens。
- 观察到的模型与请求模型一致（`requested_model == observed_models`）。
- 治理行为：模型读取了全部 3 个声明输入（含输出契约与正例），未越界。
- 已知噪声：DeepSeek 该端点默认返回 thinking 块且计入 output token；
  adapter 按已知缺口跳过（receipt 有对应 warning）。
- 模型把正例的 `object_id` 前缀（EVID-001-0x）一并模仿了；结构合法，
  语义上是低风险模仿，记录在此供后续任务设计注意。

## 到达本结果的 live 迭代（全部工件在本地 work/ 保留）

1. AT-API-002：incomplete —— 思考块吞掉 1800 output token（stop_reason=length）；
   同时证明越界读取会被 PermissionError 拒绝。
2. AT-API-003：会话内核未捕获 ProviderError，CLI 栈溢出 —— 已修（内核转为
   failed 终态并保留部分状态）。
3. AT-API-005：failed —— 模型最终消息为散文，结构化校验拒绝；诊断预览生效。
4. AT-API-006/007：incomplete —— Evidence 自封包不合 schema（字段类型/引用形状）。
5. AT-API-008：safe-paused —— 单轮并行工具调用超过默认上限 4（已调至 8）；
   并暴露 safe-paused 终态缺 Context Snapshot 的契约问题（见
   `PENDING_ADJUDICATIONS.md` 新增条目）。
6. AT-API-009：**completed**。

## 限度

- 本包证明的是结构闭环与账务可对账，不构成任何科学正确性结论；
  `check-report.yaml` 的 limitations 同样声明了这一点。
- 单次单模型验收，不构成对其他模型/账号的 conformance 推广。
