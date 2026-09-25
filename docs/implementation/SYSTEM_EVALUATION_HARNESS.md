# System-Level Evaluation Harness — H1–H4b

Evaluation owner：路诚钺。Execution 接口 owner：黄毅。Record version：`1.0.0`。
任务边界见 [M5-007](../TASKS.md)，完整施工顺序见 [进入计划](../workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-007_ENTRY_PLAN.md)。

H1/H2 提供确定性计划及评价侧预检，其记录固定 `actual_execution=false`。
H3 提供 synthetic 四臂执行、fresh Attempt 和执行后 replay；接口与验证范围见
[H3 实施包](../workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/M5-007_H3_PACKET.md)。
H4a 提供 evaluation-owned actual evidence 与独立重算；H4b 增加有限 synthetic 格式的盲审、具名审查冻结和揭盲候选。metrics、analysis 和持久化集成收口
属于后续 H4c/H5。所有记录保持
`execution_authority=false`、`task_completion=false`，不改写 Manifest、Protocol 或 Runtime 契约。

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

## H3：执行账本与独立 replay

`evaluation/harness_execution.py::execute_harness` 接受 `EvaluationInputs`、`HarnessContext`、
`HarnessPorts`、显式可信 `clock` 和 `admission_verifier`。重算 preflight 后按计划顺序执行完整 blocks，
遇不可重试失败停止。只接受 synthetic Protocol；没有真实模型执行的隐式授权。

A1/A2 调 M6 transport；A3/A4 的每个必需 slice 分别调 M11 Core/Skill Host 和 closeout。
Driver 工厂只收到已验证 View、当次 Trace recorder 和 fresh 输出目录，负责调用时的 actual facts。
Harness 不代写 actual binding 或 Skill consumption。M6 自行创建 fresh isolated session；
H1 session ID 是评价侧预留身份，不伪称 Provider 服务端 session identity。

多个 M11 slice 共用该 arm 的冻结 turn/output-token/time 预算。预算已耗尽时不启动下一 slice；
调用后的累计超限保留为 post-call failure。整臂已有调用时，后续 slice 的 preflight block 也归为
整臂 post-call failure；原始各 slice Receipt 仍保存其真实状态。时间检查是调用边界检测，不提供硬抢占。

评价侧账本位于 `.rwb/harness/<run-id-digest>/`；运行输出位于 frozen Task 首个具体 write directory
中的 `harness/<attempt-id>/`。每个 started/finished 文件 exclusive-create，finished ref 按执行顺序
保存于 `evaluation_harness_execution@1.0.0`。run 的 `completed` 只表示计划中的本地调用闭合。
不可预期异常保留未闭合 started marker 和已有 evidence；不能复用该 run ID 继续挑选成功结果。

`replay_harness` 要求外部 result ref 与相同 `HarnessContext`，重新验证 H2，逐个调用 M6/M11 的
独立 Receipt replay，检查计划身份、完整 slice 集合、输出目录、实际时间、失败与 retry 顺序。
它不调用 Provider、Tool、Driver 或归档 checker。M6 transient/rate-limit 的 replay-valid 失败仅在
预注册策略允许时重试；M11 和无 typed transport 分类的失败保守停止，保留全部成本来源记录。

Trace credential token 识别以词边界区分 `TASK-…` 路径与独立 `sk-…` 密钥；Skill fact 沿用
现有 project-relative creation event 和验证器，真实密钥与敏感字段继续脱敏。

## H4a：实际证据核对

`evaluation/harness_evidence.py::compile_harness_evidence` 接受 `EvaluationInputs`、外部选定的
`execution_ref`、同一 `HarnessContext`、`evidence_id` 和 `admission_verifier`，首先完整调用 H3
`replay_harness`。输出 `evaluation_harness_evidence@1.0.0` 是 Evaluation 记录。

`slots` 按冻结 block/arm/retry 顺序列出所有预留 Attempt，每项保留 case、phase、replicate、
session/Attempt identity、journal ref 与生命周期。A1/A2 每个 Attempt 有一个 transport slice，
A3/A4 列出该 Task 全部必需 slices。未执行的 retry 或停止后的 slots，以及未启动的后续 slices，
均标为 `not-started`，没有 Receipt、actual 或执行 evidence；其 Attempt 名称只是预留身份。

每个 slice 的 `frozen` 保存 qualification、Bundle/Snapshot/View 和预期 binding/Supply/Skill
consumption。`actual` 只来自 replay 已验证的 Receipt/Host/typed facts；A1/A2 同时保留每次实际
Provider response binding 和已调用 Tool implementation refs，A4 保留实际消费的 Projection/Skill
身份与哈希。原始 Receipt、Trace、Host、artifact、validation/fact refs 仍可追溯。

`comparison` 为 `not-observed`、`matches-frozen` 或 `differs-from-frozen`。completed slice 必须
匹配冻结条件；可重放的 post-call failure 保留实际 drift 和原始 diagnostic。零调用 preflight
block 没有 actual consumption。整臂 deadline failure 可以包含先前 completed slice 和随后
零调用 blocked slice；H3 整臂状态保持原样，不能因单个 slice 成功而升级。

`validate_harness_evidence` 另外要求调用方提供 `expected_execution_ref`、`expected_evidence_id`
及完整 `HarnessContext` 和 admission verifier。它重新回放 H3、重建每一项并比较完整记录；
删除失败/重试、漏 slice、替换 case/Attempt/实际身份或篡改 source/Schema/evidence pins 都会拒绝。
新进程回放不调用执行端口，不执行项目 Tool/checker。Schema identity 使用 H2 相同的全 catalog
指纹规则；输入 archives 必须与提供的 validator/Schema 版本相容，不能改写旧档案以迁就新版本。
H4a validator identity 同时绑定 baseline closeout、`execution/baseline.py` 的请求/Tool 输入重建代码
及 `adapters/models/port.py` 的消息与请求数据结构；这些回放语义的源码变化会使既存 H4a 证据失效，
须在新 identity 下重新编译和验证。

该记录始终保留 synthetic purpose，`analysis_eligibility` 和 Human/Task authority 为 false。
阶段标签不产生 confirmatory eligibility；H4b 消费该闭包，measurement 和分析资格属于后续接口。

## H4b：有限格式盲审、具名冻结与揭盲

`evaluation/harness_review.py` 新增七个 `@1.0.0` Evaluation-owned record kinds：
`evaluation_harness_review_artifact`、`evaluation_harness_review_policy`、
`evaluation_harness_review_package`、`evaluation_harness_review_mapping`、
`evaluation_harness_human_review`、`evaluation_harness_review_freeze` 和
`evaluation_harness_review_reveal`。它们仍仅支持 `synthetic-contract-proof`。
H4a 已由 PR90 接受；H4b 是待独立审核的实施候选，尚未取得 Human review 或分析资格。

`ReviewContext` 由调用方提供完整 HarnessContext、exact execution/evidence refs、evidence ID、
preregistered policy ref、可信 policy registration time 和 package creation time。每次 package、
freeze 或 reveal 验证均重做 H4a independent replay，再校验 case 集合、时间和 projection。
policy 必须在 case selection freeze 前注册，包含全部 case 的受控公共 reference integer、
固定 instruction/rubric 和 projection rule；不得从待验文件中自选可信时间或 authority。

当前 projection rule 只支持 0–9 的 synthetic 整数回答：M6 artifact 必须是已验证 Receipt 的
单个完整 text ModelResponse，正文必须恰为一个数字；M11 artifact 必须符合新
`review_artifact` Schema，包含整数 answer 和明确的 transport metadata 字段。公开投影只输出
整数与 availability；其余字段由固定规则丢弃。额外正文、嵌入 content metadata、未知字段、
多个不同 artifacts 都阻断。一个 slice 的多个 output contracts 引用同一 artifact 时只展示一次，
所有原始 refs 仍完整保存在私有映射中。该规则不证明任意自然语言的完全匿名性。

`prepare_review_package` 返回两个独立对象。只有 `review_package` 可交给 reviewer：固定的
公共任务说明与 rubric，加上匿名 slot ID、reference integer、answer 和 availability。每个计划
slice（含失败、blocked 和未启动 retry）对应一个 slot；非 completed 输出不参与评分，公开包不
暴露具体失败原因。别名使用系统私有随机熵，每次生成不同，按随机 ID 排序；不使用公开 seed、
arm 顺序、路径或执行身份派生。`review_mapping` 保留全部 source refs、projection digest、
case/arm/Attempt/slice/lifecycle、evidence/policy pins 和 validator identity。

`projection_verifier` 是必需的外部授权回调，必须核实 preregistration 与 exact source-to-projection
处理。回放使用外部固定的 package/mapping refs，重算所有投影及映射；不能只相信文件名已匿名化。
调用方应将公共包和私有材料分别 exclusive-create 持久化（可使用 `harness_runtime.persist`），
只分发公共包。该库不提供文件系统 ACL、分发服务或任意文本的自动去标识证明。

`freeze_human_reviews` 接收 `FreezeContext`：外部选定 package/mapping refs、所有具名 review refs、
每份 review 的可信 received_at 和 frozen_at。每个 slot 必须恰好评价一次，或具名记录
`unreviewable` 及非空理由；无可评价输出的 slot 不能填分。代码不产生 Human score。reviewer 的
稳定 actor ID 和名字由必需的 `human_verifier` 核验，不能用文件中的 approved 字段自我授权。
回调分别核验 `human-review`、完整 `freeze` 和 `reveal` 操作；只有布尔 True 被接受。

`reveal_human_reviews` 首先独立重验外部选定的 freeze 文件与全部 reviews，要求可信 reveal time
严格晚于 freeze time，然后生成绑定同一 evidence/package/mapping/freeze 的 reveal record。
`validate_review_freeze` 和 `validate_review_reveal` 要求调用方再次提供全部 expected refs/time，
拒绝部分集合、重复 slot、事后改分、替换映射、提前或更改揭盲时间。分发方只在验证 reveal 后
开放私有映射。重复验证同一不可变记录是允许的；对另一个冻结集合不能复用原 reveal。

通用 Schema validation 仅证明结构；缺少外部 verifier 的文件不会得到 Human authority。
synthetic fixtures 的 reviewer 和回调仅为序列测试，不是真实 Human Review。各私有记录保留
runtime/execution/supply/Human/Task/analysis authority 全部为 false。新 Schema 会更新全 catalog
identity；历史冻结闭包继续使用其匹配的 validator/catalog，不能改写旧 evidence 来迁就新版本。

## 验证与读取边界

H1–H4b records 由 Schema catalog 和文档 kind 注册。通用 repository validation 证明结构；语义重算必须
调用上述 Harness API 并提供外部上下文与 admission authority。默认 CLI 不隐式补齐这些可信输入。

对应测试为 `test_evaluation_harness_plan`、`test_evaluation_harness_preflight`、
`test_evaluation_harness_execution`、`test_evaluation_harness_evidence` 和
`test_evaluation_harness_review`。后者包含四臂证据到冷进程 freeze/reveal 的闭包及外部 authority、
时间、来源/映射/评分篡改、匿名泄漏和缺项反例。测试只使用 synthetic
文件闭包；真实 case、live conformance、production admission 与科研效果仍按 M5-004 的独立条件验收。
