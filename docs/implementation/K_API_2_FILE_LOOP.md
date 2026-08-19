# K-API-2 Task-to-API 文件闭环设计（推倒重写版）

状态：实施契约（黄毅维护；共享接口不变）

日期：2026-08-19

## 1. 目标与非目标

目标：把一个**已冻结**的 Task Packet + Skill Assignment 编译成一个全新、有界、隔离的 API 会话，执行后把 Research Artifacts、Handoff、Execution Receipt、Attempt 以原子方式落盘为可重放文件闭环。

非目标：不做 Skill 选择（输入必须是已冻结 Assignment）、不做模型路由/自动 fallback、不实现 M6-006 自动 Agent Trace（依赖 M3-008）、不承诺 live 真实调用（M6-004 单独验收）、不新增共享 Schema 文档种类、不改路诚钺冻结的 Task/Mode/Skill/read/handoff 接口。

## 2. 总体流程

```text
Task Packet + Skill Assignment + Agent Profile + Model Pool 槽位
  → compile_execution()        纯函数编译，全部前置检查在此 BLOCK
  → ExecutionPlan              不可变执行计划（模型绑定/预算/工具白名单/初始消息/写入范围）
  → execute_plan()             IsolatedApiSessionRunner（K-API-1 内核）+ 受限文件工具
  → ExecutionRunResult         会话结果 + 工具事件日志 + 输入哈希复核
  → closeout()                 严格输出校验 → Attempt/Receipt/Handoff/check-report 原子发布
  → verify_attempt()           仅凭文件重放全部确定性检查（幂等）
```

CLI：`rwb execute task`（compile+run+closeout）与 `rwb execute verify --attempt <dir>`。

执行器 Provider 二选一，显式互斥：
- `--scripted-session <file.json>`：离线脚本化 Provider（文件即证据，可复现，测试与示例用）；
- `--allow-live`：经 `build_live_provider` 走真实 Provider，模型名/凭据只来自 pool 槽位的 `model_env` 与 adapters.yaml 的 `credential_env` 环境变量；仓库内不保存任何 key/url/model 名。
- 两者都不给 → exit 2。

## 3. 模块契约（src/research_workbench/execution/）

### models.py（固定接口，先行落地）

- `ModelBinding`：slot_id、provider_adapter、provider、model、reasoning_effort|None。
- `ExecutionPlan`（frozen，to_mapping 可序列化）：attempt_id、task_id、task_revision、root、attempt_dir、provider、model_binding、request（ModelRequest）、limits（ApiSessionLimits）、input_lock（FileReference…）、write_scope、required_outputs、skill_lock（id@version…）、assignment_ref、profile_ref、handoff_policy、readable_inputs（允许读取的精确路径集）、started_at。
- `ToolEvent`：name、ok、path|None、sha256|None、detail。
- `ExecutionRunResult`：session（ApiSessionResult）、tool_events、stale_inputs（执行后复核出的漂移列表）。
- `CloseoutResult`：status、attempt_path、receipt_path、handoff_path、check_report_path、risks（ContractRisk…）。
- `ExecutionPlanError(ValueError)`：携带 `risks: tuple[ContractRisk, ...]`，编译期一切阻断走这里。
- 状态词汇：closeout 最终状态 ∈ {completed, safe-paused, incomplete, failed}，映射规则见 §5。

### compiler.py

`compile_execution(task_path, assignment_path, *, slot, pool_path, adapters_path, root, attempt_id=None, environment=None, started_at=None) -> ExecutionPlan`

前置检查（失败 → ExecutionPlanError，携带对应 BLOCK 风险码）：

| 风险码 | 条件 |
|---|---|
| EXEC-TASK-ASSIGNMENT-MISMATCH | assignment.task_id/task_revision 与 Task 不一致 |
| EXEC-PROFILE-MISMATCH | assignment.agent_profile ≠ task.agent_profile，或 Profile 文件加载失败 |
| EXEC-INPUT-STALE | 任一 input_refs 活哈希与锁不一致 |
| EXEC-SKILL-DRIFT | skill_lock 钉的 manifest/source 哈希与 Registry 活文件不一致（Registry 用 historical-replay 语义加载，legacy 可执行已冻结 Assignment） |
| EXEC-MODEL-UNBOUND | 槽位不存在/未启用/model_env 未设置（脚本化 Provider 注入时豁免 model_env） |
| EXEC-ADAPTER-MISMATCH | 槽位 provider_adapter 不在 adapters.yaml 或能力超集（复用 validate_pool_adapters） |
| EXEC-WRITESCOPE-INVALID | write_scope 为空或含越界/绝对路径 |

编译产物要点：
- limits：task.budget 映射（max_turns→max_model_turns、max_output_tokens→max_output_tokens_per_turn、max_seconds），缺省 max_tool_calls=12、max_parallel_tool_calls=4、max_tool_result_chars=8000；allowed_tool_side_effects={read-only, local-write}（external_write=false 时不含 external-write）。
- 初始消息：system = Profile 行为边界 + 锁定 Skills 的正文（按 skill_lock 从 Registry 读 source 文件）+ 输出契约 + Handoff 要求；user = task goal、input_refs 仅路径+哈希（不内联正文）、write_scope、required_outputs、completion_checks、safe_pause_conditions、stop_conditions。主上下文历史一律不传入。
- response_format：JSON object {status: completed|safe-paused, summary, limitations[], unresolved[]}。

### runner.py

`execute_plan(plan, *, providers, clock=time.monotonic) -> ExecutionRunResult`

- 构造 3 个 ClientTool（handler 抛异常即 is_error，不含异常正文）：
  - `read_file(path)`：仅允许 plan.readable_inputs 精确路径或 attempt_dir/outputs 内文件；返回 {path, sha256, content}；越界 → 抛错。
  - `write_artifact(name, content)`：仅允许裸文件名（不得含路径分隔符），写入 attempt_dir/outputs/；重复写同名 → 报错（追加历史用新文件名）。
  - `list_outputs()`：返回 outputs/ 的文件名+sha256 列表。
- 每次工具调用记录 ToolEvent（path+sha256）。
- 调用 IsolatedApiSessionRunner.run(provider_name=plan.provider, request=plan.request, limits=plan.limits)。
- 运行后复核 input_lock 活哈希，漂移记入 stale_inputs。

### closeout.py

`closeout(plan, run, *, root) -> CloseoutResult`

- 状态映射：session COMPLETED 且 final JSON status=completed 且 required_outputs 全部存在且过 Schema → completed；session SAFE_PAUSED 或 stale_inputs 非空 → safe-paused；BLOCKED/INCOMPLETE → incomplete；FAILED 或 closeout 校验失败 → failed。任何确定性检查 BLOCK → 状态不得为 completed（不伪造完成）。
- 落盘（全部 tempfile+fsync+排他 link 原子发布；process 文件只增不改）：
  - attempt_dir/execution-plan.yaml（plan.to_mapping，内部工件，无新文档种类）
  - attempt_dir/session-transcript.json（请求/响应/工具事件，无凭据——请求本来不含凭据）
  - attempt_dir/outputs/*（Agent 经 write_artifact 写入的正式输出）
  - attempt.yaml（AttemptRecord，回指 receipt/handoff）
  - execution-receipt.yaml（ExecutionReceipt：runtime=provider/实际 observed models，model_usage 来自 AggregateUsage 对账，output_refs、validation_refs、limitations）
  - handoff.yaml（HandoffPacket：completed 含摘要/工件引用/限制/未决；非 completed 一律 incomplete Handoff 并附原因）
  - check-report.yaml（本次全部确定性检查结果的汇总内部工件）
- task.handoff_policy.require_transfer_manifest 时：先写 transfer-manifest 再跑 assess_handoff_transfer，BLOCK → 状态降级 incomplete。
- `verify_attempt(attempt_dir, *, root)`：仅凭文件重跑——plan/attempt/receipt/handoff schema 校验、outputs 哈希对账、check_execution_receipt、check_handoff_against_task；幂等，返回风险列表。

### testing.py

`ScriptedProvider`：实现 ModelProvider 协议，从 JSON 文件读取脚本化响应序列（含 usage），supports 任意 model，capabilities 声明 text/tools/structured_output；供测试与 `--scripted-session`。脚本格式：`{"responses": [{...ModelResponse 字段...}]}`。

## 4. Attempt 目录布局

```text
work/<TASK-ID>/<ATTEMPT-ID>/
  execution-plan.yaml
  session-transcript.json
  outputs/…（Agent 正式输出）
  attempt.yaml
  execution-receipt.yaml
  handoff.yaml
  check-report.yaml
```

## 5. 风险码（新增，须登记 contracts/risk_codes.py 并配测试）

EXEC-TASK-ASSIGNMENT-MISMATCH、EXEC-PROFILE-MISMATCH、EXEC-INPUT-STALE、EXEC-SKILL-DRIFT、EXEC-MODEL-UNBOUND、EXEC-ADAPTER-MISMATCH、EXEC-WRITESCOPE-INVALID（以上编译期 BLOCK）、EXEC-CLOSEOUT-INVALID（发布工件不过 Schema，BLOCK）、EXEC-CLOSEOUT-SUMMARY（check-report 汇总行，存在 BLOCK 风险时判 fail）、EXEC-LIVE-NOT-ALLOWED（未显式允许却尝试 live，BLOCK）。编译期 malformed 文件仍走 ContractError → CLI exit 2。

## 6. 测试策略（全离线、无网络、无凭据）

- compiler：每个风险码一个反向 fixture + 一个正例；model_env 缺失/槽位禁用/能力超集分支。
- runner：脚本化 Provider 驱动 工具读→写→完成 全链路；越界 read/write 被拒；工具异常 → is_error 且不含异常正文；预算耗尽 → safe-paused；transcript 无秘密标记。
- closeout：四终态（completed/tool-failed→incomplete/budget→safe-paused/stale-input）；required_outputs 缺失降级；原子发布（同名重复发布被拒）；verify_attempt 幂等且能检出人为篡改的 output 哈希。
- CLI e2e：`rwb execute task --scripted-session` 全绿闭环 + `rwb execute verify`；无 --allow-live 无 --scripted-session → exit 2；假 key 标记不出现在任何输出/transcript。
- Receipt 对账：usage 与脚本声明逐字段一致。

## 7. 与路诚钺侧的合并接口

- 输入只消费冻结工件：Task Packet、Skill Assignment（historical-replay 语义，legacy 可重放）、Agent Profile、Registry。
- 不新增共享 Schema 种类、不改 Task/Handoff/Receipt/Trace 语义；新增文件仅 execution/ 包、tests、examples/api-execution fixtures、本文件；共享文件仅 cli.py（新增 execute 命令组）与 contracts/risk_codes.py（登记新码）与 CHANGELOG/TASKS（黄毅行）。
- live 所需 key/url/model 全部经环境变量注入，仓库留空；需要 live 验证（M6-004）时由黄毅提供。
