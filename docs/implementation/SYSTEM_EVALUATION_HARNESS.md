# System-Level Evaluation Harness — H1/H2

Evaluation owner：路诚钺。Execution 接口 owner：黄毅。Record version：`1.0.0`。
任务边界见 [M5-007](../TASKS.md)，完整施工顺序见 [进入计划](../workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-007_ENTRY_PLAN.md)。

H1/H2 提供确定性计划及评价侧预检。Provider/Tool/Host 的实际调用、fresh session 分配、执行后 replay、
盲审、metrics 和 analysis 属于后续 H3–H5。两个新 record 都固定 `actual_execution=false`、
`execution_authority=false`、`task_completion=false`，保持现有 Manifest、Protocol 与 Runtime 契约。

## H1：冻结计划

`evaluation/harness_plan.py::compile_harness_plan` 接收 `EvaluationInputs` 和显式的
`protocol_ref`、`case_closure_ref`、`case_selection_frozen_at`、`public_cases`、`plan_id`、`run_id`。
它重载 exact Protocol/Manifest/case commitments，使用 M6 public projection 白名单验证逐 case 的公共
payload，并保存其摘要。所有 frozen Task 都必须由 case closure 覆盖。

`evaluation_harness_plan` 中的 `phase=pilot/confirmatory` 只表示计划阶段。H1 不判断
`primary_confirmatory_eligible`，该字段不属于 plan Schema。pilot/confirmatory 的可分析资格必须等待
H2 重算 overlap；计划存在不代表已执行、已准入或已满足 confirmatory 条件。

排列算法 `sha256-arm-order-v1` 在每个 phase × case × replicate block 内按以下 JSON 的 SHA-256
升序排列四个 canonical arm，哈希相同则按 arm ID 排序。使用 UTF-8、键排序、无空白分隔和非 ASCII
原文编码；拒绝非有限值。输入为 `algorithm`、Protocol `seed`、`phase`、`case_id`、`replicate`、`arm_id`。
case 按 ID 排序、replicate 从 1 起，先 pilot 后 confirmatory；算法和固定向量由测试锁定。

Attempt/session slot 的摘要另绑定完整规范化 plan request 和 retry index。它们是预留身份；retry slot
仅允许标为 `after-eligible-failure`，H3 才会根据实际失败分配 fresh Attempt/session。重新编译同一计划
会得到同一身份集合；再次执行必须由调用方提供新的 `run_id`。单份计划最多容纳 100,000 个预留 slot。

`validate_harness_plan` 对调用方给定的 Protocol、case/time 与 run ID 重新编译。使用者先从外部可信
FileReference 加载 plan；文档内部不能改写外层 pins。private case/oracle/checker/adjudication artifact
的已知哈希不能作为 public payload/input，即使换路径或被误放进共享 context。

## H2：独立预检

`evaluation/harness_preflight.py::compile_harness_preflight` 消费外部 `plan_ref`、同一冻结上下文、
`preflight_id`、`preflight_checked_at`、`a2_qualification_ref`、`a3_qualification_ref`、`overlap_ref`、
完整 `case_bindings` 以及授权调用方提供的 `admission_verifier`。

- A2 record 由 Harness 外部的 M6 producer 产生；H2 加载并调用 M5 qualification validator 重验。
- `produce_a3_qualification` 使用同一个显式 `preflight_checked_at` 组装调用方提供的 Resolver frozen/runtime bindings，再调用共享 validator；
  Supply、Resolution、Snapshot 的唯一选择责任保持在 Resolver。
- `preflight_checked_at` 是调用方提供的可信时间。H2 不调用当前时钟；它检验 case freeze 和
  qualification/overlay/pairwise 的先后关系，并在该时间检查 runtime availability。
- overlap 从两侧 exact closure 独立重算。`unresolved` 阻断预检；`admission-overlap` 保留
  `primary_confirmatory_eligible=false`；held-out 才产生 true。pilot 的 primary eligibility 始终为 false。
- A4 overlay 的 Task、overlap assessment 必须等于相应计划输入；pairwise 必须使用相同 A3 qualification
  和 A4 overlay，且处于 `plan-pre-run`。每个计划 case 恰有一组绑定。
- admission verifier 保持调用方外部 authority，不序列化进记录，也没有默认成功实现。

`evaluation_harness_preflight` 保存重新计算的 eligibility、pairwise 等级、A1/A2 payload 摘要及
validator/Schema pins。当前完整 synthetic fixture 的 A3/A4 Method disposition 不同，结果是
`skill-bearing-package`；primary `A4 − A2` 继续包含 transport difference。

`validate_harness_preflight` 要求外部 `expected_plan_ref`、冻结上下文、`expected_run_id`、
`expected_preflight_checked_at` 和 admission verifier，再次加载全部 inputs 并重算结果。保存的预检
不构成实时执行授权；H3 仍须按现有 transport 的 use-boundary 规则验证实际调用。

## 验证与读取边界

两个 record 由 Schema catalog 和文档 kind 注册。通用 repository validation 证明结构；语义重算必须
调用上述 Harness API 并提供外部上下文与 admission authority。默认 CLI 不隐式补齐这些可信输入。

对应测试为 `test_evaluation_harness_plan` 和 `test_evaluation_harness_preflight`。测试只使用 synthetic
文件闭包；真实 case、live conformance、production admission 与科研效果仍按 M5-004 的独立条件验收。
