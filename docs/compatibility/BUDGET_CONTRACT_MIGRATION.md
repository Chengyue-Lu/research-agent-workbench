# 预算契约的显式版本迁移

本页是迁移边界，当前覆盖由 [STATUS](../STATUS.md)维护，新方向见 [ADR-0025](../decisions/0025-USAGE-RECORDING-AND-MODEL-WORKING-INPUT.md)。新方向的实现任务为 [TASKS](../TASKS.md) 中 M6-013。

## 当前旧版行为

固定 develop `67a7c5f6a0c3495f1ad583864d87b25f5bf892e2`：Task Packet 和 execution-policy 的 `budget`/`budget_ceiling` 是必需非空对象；View producer 对声明维度取最小值且没有 ceiling 时拒绝；Host 检查 actual turns/output tokens/duration。Session kernel 也有轮次、token、费用和时间硬边界。

PR140 固定候选 `766bf45ccde4637684e2100480e9f1577cc61662` 的 baseline 有预算停止/分配职责，请求序列化完整 Task；这些是候选事实，不是已合入 develop 的新入口能力。未执行迁移前不能宣称模型输入或运行已去预算。

## 新版本的消费要求

| 接口 | 迁移要求 |
|---|---|
| Protocol/Task/delegation | 通用执行不要求预算对象、余额或子预算份额；保持目标、权限、引用与输出义务 |
| Policy/View | 新版本不把经济额度作为必需授权输入；显式版本检查保持其他最严权限/data-egress/side-effect交集 |
| Host/Session/Driver | 移除通用经济余额/预占/超额/unknown holds 阻断；保持实际取消、技术容量/超时和真实执行事实 |
| 角色请求/编译 | 声明模型工作输入白名单，不序列化整个内部 Task/Policy/账本；预算字段不由模型生成 |
| Trace/Receipt/assessment | 记录 actual/failed/unknown，记账完整性与执行/交付判定分开；不扩大 Receipt 完成权 |
| 安装与调用消费者 | 明确新版本路径；旧记录保留精确版本/哈希， unsupported version 明确 gap，不静默转换 |

迁移输出应有源/目标版本、程序身份、原件 refs/hash、转换规则、消费者清单、已知缺口和正反证据。保留原件并另写新工件；没有实际执行的历史记录不补造新 execution facts。

旧 Task/policy/预算停止测试继续按原版本校验。新路径的验收包括没有经济额度、无模型预算管理输入以及记账未知仍能独立检查有效成果；旧契约拒绝案例不能直接改标成新默认通过。M5 冻结 Protocol/Manifest 和已发 live grant 保持原本比较/授权含义，需要改它们时单独形成版本与决定。


## 旧 Protocol 示意

下例从固定基线的 `docs/modules/02-PROTOCOL_AND_MODES.md` 原样保留，只说明旧字段，不是新模型工作输入或完整可执行例。

```yaml
project_id: demo
question_refs: [Q-001]
active_modes: [evidence-synthesis, simulation]
claim_ceiling: [source_reported, simulation_supported]
required_human_gates:
  - approve_method_assumptions
  - approve_main_claim
  - approve_external_release
budgets:
  max_parallel_subagents: 2
  max_delegation_depth: 1
  coordination_cost_ratio_warn: 0.33
context_policy:
  proactive_checkpoint: true
  main_raw_material: forbidden
data_boundary:
  local_only: true
  external_upload_requires_approval: true
```


## 旧 Task 字段职责示意

下例从固定基线的 `docs/modules/05-TASK_AND_HANDOFF.md` 原样保留，只说明旧字段，不是新模型工作输入或完整可执行例。

```yaml
schema_version: 0.1.0
task_id: QUICKSTART-001
goal: Check explicit local artifact references and produce a bounded check report.
question_refs: []
active_modes: []
required_capabilities: []
required_skills: []
forbidden_skills: [final-synthesis]
agent_profile: evidence-scout
input_refs: []
write_scope:
  - work/QUICKSTART-001/**
required_outputs:
  - deterministic-check-report
permissions:
  external_write: false
delegation:
  allowed: false
budget:
  max_turns: 4
  max_output_tokens: 800
atomic_boundary: One bounded reference check and persisted report.
completion_checks:
  - declared artifact references and report pass deterministic checks
safe_pause_conditions:
  - next atomic unit would consume the closeout reserve
  - required source, permission, or human decision is unavailable
stop_conditions:
  - required_outputs_complete
  - human_judgment_required
stale_if:
  - any_input_hash_changes
```
