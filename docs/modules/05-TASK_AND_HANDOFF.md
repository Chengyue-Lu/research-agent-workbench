# 模块 05：Task 与 Handoff 契约

## 1. 目标

用结构化、窄范围的 Task Packet 取代“把整个项目背景发给子 Agent”，用可验证的 Handoff Packet 取代自由聊天总结。

## 2. Task Packet

建议结构：

```yaml
schema_version: 0.1.0
task_id: EVID-001
goal: Extract evidence for the bounded question.
question_refs: [Q-001@3]
active_modes: [evidence-synthesis]
required_capabilities: [evidence-extraction, citation-location]
required_skills: [literature-evidence-extraction]
forbidden_skills: [final-synthesis]
agent_profile: evidence-scout
input_refs:
  - path: sources/raw/paper-001.pdf
    sha256: "..."
write_scope:
  - work/EVID-001/**
  - objects/evidence/EVID-001-*.yaml
required_outputs:
  - contract: evidence-record
    min_count: 1
  - contract: handoff-packet
permissions:
  external_write: false
delegation:
  allowed: false
budget:
  max_turns: 10
  max_output_tokens: 1800
atomic_boundary: One bounded source set and its formal Handoff.
completion_checks:
  - evidence and handoff contracts pass deterministic checks
safe_pause_conditions:
  - next atomic unit would consume the closeout reserve
  - required source, permission, or human decision is unavailable
stop_conditions:
  - required_outputs_complete
  - source_boundary_exhausted
  - human_judgment_required
stale_if:
  - any_input_hash_changes
```

Task 必须可在有限时间内完成。`goal` 不能写成“完成整个研究”或“确保论文正确”。

Task Packet 同时是 Atomic Work Unit/ExecutionContract，不另建平行契约。`atomic_boundary` 说明可安全切换的最小边界；`completion_checks` 是机器完成权；`safe_pause_conditions` 说明何时允许持久化后停止。上下文不足只能进入 `safe-paused`，不能把未通过的检查包装成 `completed`。

## 3. Resolved Task

Capability Resolver 在执行前添加：

- Agent Profile revision；
- Skill Assignment ID 与 lock；
- Runtime Adapter 和 capability snapshot；
- effective permissions；
- 实际输出路径；
- 冲突/例外。

Resolved Task 不修改原始 Task；它是一次带版本的执行视图。

## 4. Handoff Packet

```yaml
schema_version: 0.1.0
task_id: EVID-001
attempt_id: A-001
status: completed
input_lock:
  - ref: sources/raw/paper-001.pdf
    sha256: "..."
skill_lock:
  - literature-evidence-extraction@0.1.0
result:
  summary: Extracted four evidence records; one source conflicts with the proposed mechanism.
  facts:
    - four records passed locator checks
  inferences:
    - evidence is insufficient for a causal claim
  recommendations:
    - search for preregistered replication data
artifact_refs:
  - objects/evidence/EVID-001-01.yaml
validation_refs:
  - checks/EVID-001-handoff.json
limitations:
  - only English-language sources were in scope
conflicts:
  - evidence_ref: EVID-001-04
    with: HYP-001
unresolved:
  - no source directly measures the proposed mediator
human_decision_required: []
recommended_next_actions:
  - create a bounded replication-search task
```

## 5. 交接原则

- 事实、推断、建议必须分开；
- 关键陈述必须引用正式工件；
- 必须声明限制、冲突、未完成和失败；
- 长内容写文件，Handoff 只返回摘要和索引；
- 原始日志不进入主上下文，但保存在 Run/Attempt 目录；
- 若摘要可疑，主 Agent可沿引用按需回查；
- `completed` 只表示 Task 合同完成，不表示 Claim 被接受；
- `stage-completed` 表示预定义阶段完成但上层目标未完成；`safe-paused` 表示机器验收尚未满足但恢复状态完整；`waiting` 保留人类或外部依赖等待；
- 失败 Handoff 也是正式结果，不得丢弃。

### 按风险分级

交接复杂度不是固定流水线：

- `H0`：同一 Agent/上下文内完成，不发生交接；保留正式输出、验证和工作留痕即可。
- `H1`：普通跨 Agent 返回；默认只要求一个 Handoff Packet。
- `H2`：发生压缩、关键 Evidence/Claim/Decision promotion、外部副作用、长等待/会话销毁、摘要争议或 Task 明确要求时，增加 Transfer Manifest/Audit，并按需增加 Context Snapshot、Execution Receipt 与独立语义抽样。

H1/H2 都必须声明失败、限制、冲突和未完成项。H2 不是默认“更可靠”；若额外工件不改变主 Agent 决策，应缩减触发条件。Handoff 等级只控制回传主上下文的摘要与审查强度，不控制是否留存原始过程：所有跨 Agent 可见传递均进入 Attempt Archive。

### Transfer Manifest 与接收审计

当 Task 的 `handoff_policy.require_transfer_manifest` 为 true 且本次 Attempt 接纳了正式 Research Artifact 时，执行者必须在压缩或结束 Task Context 前写 `handoff_transfer_manifest`。Manifest 只列需要跨上下文保留的稳定条目 ID、类型、关键度、来源工件哈希和定位符，不复制原始材料或推理日志。`failed`、`blocked` 或 `safe-paused` 没有接纳科研工件时不得为满足清单而伪造 Manifest/Audit。

接收者用 `handoff_transfer_audit` 把条目映射到 Handoff 的 `/result/facts/*`、`/limitations/*`、`/unresolved/*` 等位置。机器检查覆盖、哈希、定位、必需条目和负面区段；语义是否被改写只能由有界独立抽查记录。领域 Skill 决定哪些内容应进入 Manifest，通用 Handoff 契约不规定所有学科共用的参数或质量评分表。

Manifest/Audit 是 H2 工件，不再对所有普通 Handoff 默认要求。Task 的 `handoff_policy`、实际压缩和风险检查决定是否升级。

## 6. Attempt 与 Task

一次 Task 可以有多个 Attempt。重试必须使用新 `attempt_id`，记录触发原因、输入是否变化、Skill/模型/工具是否变化。禁止覆盖失败 Attempt。

`K-API-2` 当前 H2 fake-local 切片的终态落盘矩阵是：

- `completed`：Attempt、Research Artifact、Transfer Manifest/Audit、Handoff、Task/Main Context Snapshot、Execution Receipt，最后发布 Main State；
- `safe-paused`、`incomplete`、`failed`、`blocked`：Attempt、Handoff、Task/Main Context Snapshot、Execution Receipt，最后发布 Main State；不生成 Research Artifact、Manifest 或 Audit。`incomplete` 表示 Provider 只返回不完整终止结果，必须持久化自己的下一动作并使用新 Attempt，不能恢复或重放原 transcript。

多文件 closeout 采用 commit-last 协议，不是多文件事务：各正式文件逐个排他发布，Main State 是最后提交点。崩溃可能留下未被 Main State 引用的不可变孤立文件；验证完成的 stage 可以续发而不重放 Provider，只有 intent 但没有可验证结果的 Attempt 必须 fail-closed 并人工确认后使用新 Attempt。

该矩阵不代表普通 H1 closeout 或完整 Attempt Archive/Agent Trace 已实现；当前编译器只接受明确要求 Transfer Manifest 的 H2 Task，其他等级在 Provider 调用前阻断。

Attempt 可以引用一份 `Execution Receipt`。Receipt 记录实际 Runtime、模型用量状态、协调/执行成本、Context Snapshot 和 trace 策略；Handoff 也回指同一 Receipt。验证器检查这三者的 Task、状态、时间和路径一致性，避免把另一次执行的成本或结果串入当前交接。

Receipt 的生命周期 `status: completed` 只表示一次执行已经结束，不等于 Task 合同已满足；这使负对照和失败实验仍能成为合法记录。只有显式声明 `completion_claim: contract-satisfied` 时，Receipt 才必须至少引用一个内核能够解释的机器验证工件。若确定性报告为 `fail`，或其 checker/subject 哈希已漂移，该声明被阻断；Receipt/LLM 文本不能覆盖机器证据。

重试政策：

- Schema/格式失败：最多一次定向修复；
- 暂时工具错误：按 Task 声明重试；
- 语义不确定：不自动重试多个 Agent 直至“达成一致”；
- 权限/数据边界失败：直接阻断；
- 新输入或范围变化：创建新 Task revision，而非伪装重试。

上述“一次定向修复”是调度政策，不授权在已经写入执行 intent 的同一 Attempt 内自动再次调用 Provider 或重放工具。

## 7. Write Scope

- 默认子 Agent 只写 `work/<TASK>/<ATTEMPT>`；
- 只有通过验证的结果才能提升到 `objects/` 或 `runs/`；
- 两个并行 Task 的 write scope 不得重叠；
- 主 Agent 或确定性 promotion 命令负责正式合并；
- 高风险 Agent 默认只读并提交建议工件。

### Read Set 与工作留痕

- Task、仓库 guidance、选定 Profile/Skill、显式输入和目标模块构成初始内容允许集；
- 允许用文件名、目录名、大小、版本和哈希定位依赖，但不默认读取其他正文；
- 新正文必须由实名 Task owner 扩展允许集，并在 Task 工作目录记录 scope-decision 消息；
- 每个 Agent 间实际可见的 Assignment、澄清、范围变化、进度、Handoff、review、确认、失败与取消都进入 `work/<TASK>/<ATTEMPT>/messages/`；
- 运行时可观察的正文读取、工具/命令与文件 revision 进入 `events.jsonl`；Worklog 不逐项复制，但 validator 可用账本核对越界读取；
- `INDEX.yaml` 提供消息元数据发现，但另一个 Agent 的消息正文不在默认读取集，除非 Assignment 或后续 scope-decision 明确引用；
- worklog 记录基线、关键决定、范围变化、修改路径、重要验证和未完成项，不记录每次普通读取或完整推理；它是 Trace 的可读索引，不是 Trace 本身；
- 另一个 Agent 的 `work/<TASK>/<ATTEMPT>` 不在默认读取集，除非作为正式输入交接。

可复制使用[Attempt Archive Template](../templates/TASK_WORKLOG.md)，完整目录和消息信封见[工件与溯源](07-ARTIFACTS_AND_PROVENANCE.md)。

## 8. 预警

- `TASK-TOO-BROAD`：目标无法在预算内完成；
- `TASK-SKILL-MISMATCH`：required capability 没有被 Skill 覆盖；
- `TASK-WRITE-OVERLAP`：并行写范围重叠；
- `TASK-STALE-INPUT`：输入 hash/revision 变化；
- `HANDOFF-MISSING-OUTPUT`：缺失必需工件；
- `HANDOFF-LOSSY`：摘要存在无引用关键结论；
- `HANDOFF-OMITS-NEGATIVE`：失败、反证或限制未交接；
- `HANDOFF-CLAIM-UPGRADE`：Handoff 越过 Claim ceiling。
- `HANDOFF-AUDIT-COVERAGE`：Manifest 条目没有 Handoff 映射；
- `HANDOFF-NEGATIVE-UNMAPPED`：限制、冲突、未解决项或 Human Gate 没有来源映射；
- `HANDOFF-SUMMARY-DISTORTION`：有界语义抽查发现限定条件改变。
- `HANDOFF-OVERHEAD`：审计工件成本持续增加但不改变接受、返工或 Gate 决定。
- `TASK-READ-OUTSIDE-SCOPE`：Agent 请求或读取未授权正文且没有 Task 扩展记录。
- `TRACE-MESSAGE-MISSING`：已发生跨 Agent 传递但 Attempt Archive 找不到对应消息。
- `TRACE-ACTOR-UNOWNED`：Agent actor 没有绑定实名责任人。

## 9. 验收条件

- Task 不携带完整项目聊天即可执行；
- Handoff 可由 Schema 和引用检查器验证；
- 主 Agent能只读 Handoff 决定接受、回查、重做或 Human Gate；
- 失败 Attempt 和负结果保留；
- 输入变化后旧 Handoff 自动标记 stale；
- 并行任务不能写入同一正式路径。
- 普通 H1 与高风险 H2 可以分别验收，且能够记录其协调成本差异。
- 不读取原 Agent 会话也能按 message sequence、Handoff 和 Decision 回放一次委派。
