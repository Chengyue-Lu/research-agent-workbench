# 模块 05：Task 与 Handoff 契约

## 1. 目标

用结构化、窄范围的 Task Packet 取代“把整个项目背景发给子 Agent”，用可验证的 Handoff Packet 取代自由聊天总结。

## 2. Task Packet

建议结构：

```yaml
schema_version: 0.1.0
task_id: QUICKSTART-001
goal: Prepare a bounded handoff packet for one local task.
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
  - handoff-packet
permissions:
  external_write: false
delegation:
  allowed: false
budget:
  max_turns: 4
  max_output_tokens: 800
atomic_boundary: One bounded handoff packet.
completion_checks:
  - evidence and handoff contracts pass deterministic checks
safe_pause_conditions:
  - next atomic unit would consume the closeout reserve
  - required source, permission, or human decision is unavailable
stop_conditions:
  - required_outputs_complete
  - human_judgment_required
stale_if:
  - any_input_hash_changes
```

Task 必须可在有限时间内完成。`goal` 不能写成“完成整个研究”或“确保论文正确”。

`required_skills` 可以为空，也可以写唯一 active Skill ID 或精确 `skill-id@semver`。为空时 no-Skill、
direct Tool、procedure 或 Adapter/Provider supply 路径不得为了满足旧字段而伪造 Assignment；只有
Skill-bearing execution 才由 Resolver 在 Assignment 中固定实际版本和哈希。旧版本和 legacy surface 的
回放边界见[兼容性说明](../compatibility/README.md)。

Task Packet 表达 research intent、Atomic Work Unit、输入/输出约束、权限和预算；它不是最终冻结的
Execution Contract。`atomic_boundary` 说明可安全切换的最小边界；`completion_checks` 是 Task 声明的
deterministic completion criteria，不是 Claim、Human Decision 或科学正确性 authority；
`safe_pause_conditions` 说明何时允许持久化后停止。上下文不足只能进入 `safe-paused`，不能把未通过
的检查包装成 `completed`。

目标关系为：

```text
Task Packet = research intent + atomic boundary + input/output constraints + permissions/budget
Method Resolution = provider-neutral methodology decision
Capability Requirement = provider-neutral demand and ceilings
Capability Supply Report = one implementation's reported capability and boundary facts, without selection authority
Capability Resolution = Requirement-to-Report comparison under existing authority and ceilings
Resolved Capability Snapshot = frozen Requirement/Resolution/selected-Supply facts and supply-side ceilings
Runtime Bundle = exact Action/Capability-slice document closure for one Runtime consumer
Resolved Execution View = Bundle + exact Profile/DataPolicy/HostPolicy/ExecutionBinding final narrowing
Thin Execution Host = consume exact Bundle-bound View and report actual execution facts
```

这些层次共用引用和派生关系，不建立互相竞争的 execution truth。

## 3. Capability closure、Runtime Bundle 与 Resolved Execution View

Capability Resolver 比较零个或多个显式 Supply Report。Report 不能选择自身；Resolution 只能在既有
Requirement/Task ceilings 下得到 `satisfied`、`gap`、`ambiguous` 或 `blocked`，并且只有唯一合格候选才能
形成 selected closure。Snapshot 随后冻结：

- exact Task、Method Resolution、Capability Requirement 与 Capability Resolution refs；
- selected Supply Report identity、version/hash 与 supply components；
- supply-required permission、data-egress、side-effect boundaries；
- typed conformance evidence refs 与 qualification。

Snapshot 不冻结最终 Agent Profile、Provider/Adapter/Model/Runtime/Host binding、execution-time freshness 或
最终 effective permissions。它不是 permission grant、Human Decision、Method decision、Claim effect 或
fallback authority，也不能作为 actual execution fact。

M11 Runtime Bundle 在 Snapshot 之后建立本次 Runtime 可以读取的 exact document closure，并把范围固定为
一个 Action/Capability slice。它验证 Method 必须 `proceed`、完整 Task capability demand 与 Method Action
requirements 一致，但 `task_completion` 固定为 `false`；一个 slice 闭合不能冒充整项 Task 完成。

Resolved Execution View 消费已经验证的 Bundle 和 exact Profile、DataPolicy、Host policy、Execution
Binding，冻结 Provider、Adapter、Model、Runtime、Host、三组 freshness windows、required outputs，以及
permission/data-egress/side-effect/budget 的最严交集。View producer 不能重新选择 Supply，交集也不能低于
selected Supply 的真实运行需求；无法满足时 fail closed 并请求上游形成新的 Resolution→Snapshot→View。
View 是 Host 的 final frozen execution contract，但仍不创造 permission grant、Claim/Human authority 或
Task completion。

Thin Execution Host 只消费与同一 Bundle 绑定的 View，使用 trusted clock 和调用前 Bundle reload 重验
freshness/TOCTOU，并通过一个 pre-bound Driver 最多执行一次。它只能报告 actual facts、bounded diagnostic
或 re-resolution request，不能 select、rebind 或 fallback。Skill Assignment 只在 Skill-bearing extension
或 legacy compatibility 中出现；当前 M11 Core 的 no-Skill/direct Tool 路径不创建 Assignment。M11-005/006
optional extension 已 bounded 实现，但生产 projection index 为空，不表示真实 Skill 已获 admission 或
new-binding。兼容期字段映射见[兼容性说明](../compatibility/README.md)。

## 4. Handoff Packet

以下是现行 legacy Handoff Schema 的 Skill-bearing 字段形状示例。`example-legacy-skill@0.0.0` 是不对应
accepted Registry、不得用于新 Assignment 的纯占位符。该 Schema 仍要求非空 `skill_lock`；它不能被
用来证明 generic no-Skill Handoff migration 已完成。M11 no-Skill Core 使用独立 generic execution
closeout，并不伪造 Skill Assignment。

```yaml
schema_version: 0.1.0
task_id: EVID-001
attempt_id: A-001
status: completed
input_lock:
  - path: sources/raw/paper-001.pdf
    sha256: "0000000000000000000000000000000000000000000000000000000000000000"
skill_lock: [example-legacy-skill@0.0.0]
skill_assignment_ref: assignments/SA-EVID-001.yaml
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

当 Task 的 `handoff_policy.require_transfer_manifest` 为 true 时，执行者必须在压缩或结束 Task Context 前写 `handoff_transfer_manifest`。Manifest 只列需要跨上下文保留的稳定条目 ID、类型、关键度、来源工件哈希和定位符，不复制原始材料或推理日志。

接收者用 `handoff_transfer_audit` 把条目映射到 Handoff 的 `/result/facts/*`、`/limitations/*`、`/unresolved/*` 等位置。机器检查覆盖、哈希、定位、必需条目和负面区段；语义是否被改写只能由有界独立抽查记录。领域 Skill 决定哪些内容应进入 Manifest，通用 Handoff 契约不规定所有学科共用的参数或质量评分表。

Manifest/Audit 是 H2 工件，不再对所有普通 Handoff 默认要求。Task 的 `handoff_policy`、实际压缩和风险检查决定是否升级。

## 6. Attempt 与 Task

一次 Task 可以有多个 Attempt。重试必须使用新 `attempt_id`，记录触发原因、输入是否变化，以及
Skill（若有）、模型、工具或其他 execution binding 是否变化。禁止覆盖失败 Attempt。

这里存在两类需要明确区分的 Receipt surface：

- legacy `execution_receipt` 仍要求 `skill_assignment_ref`，并保留显式
  `completion_claim: contract-satisfied` 的兼容语义；它只能按现有 Schema 回放，不能代表 generic
  no-Skill migration 已完成；
- M11 `generic_execution_receipt` exact-pin action/capability slice、View、Host report、Trace、Artifact 和
  Validation closed set，固定 `skill_assignment: absent`、`task_completion: false`，completed 时也只声明
  `action-capability-slice-only`。

generic closeout 对 completed、post-call failed 与 preflight-blocked 分开验证。completed 的 actual
binding/Supply 必须等于 View；post-call failure 只有在 typed、hash-pinned Trace execution fact 能独立佐证
Provider/Adapter/Model/Runtime/Host 和 actual Supply 时才具有 replay eligibility；preflight block 不得伪造
actual binding。任何 Receipt status 都不构成 Claim promotion、Human acceptance 或科学正确性证明。

legacy Attempt/Handoff/Receipt 仍带 mandatory Skill 字段，这是当前诚实保留的 compatibility gap；在另有
implementation task 前，文档不得把它们描述为已经完成通用 no-Skill migration。

重试政策：

- Schema/格式失败：最多一次定向修复；
- 暂时工具错误：按 Task 声明重试；
- 语义不确定：不自动重试多个 Agent 直至“达成一致”；
- 权限/数据边界失败：直接阻断；
- 新输入或范围变化：创建新 Task revision，而非伪装重试。

## 7. Write Scope

- 默认子 Agent 只写 `work/<TASK>/<ATTEMPT>`；
- 只有通过验证的结果才能提升到 `objects/` 或 `runs/`；
- 两个并行 Task 的 write scope 不得重叠；
- 主 Agent 或确定性 promotion 命令负责正式合并；
- 高风险 Agent 默认只读并提交建议工件。

### Read Set 与工作留痕

- Task、仓库 guidance、选定 Profile、相关 frozen control refs、显式输入和目标模块构成初始内容允许集；
  只有 Skill-bearing path 才加入 exact Assignment/Skill 入口；
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
- `TASK-SKILL-MISMATCH`：Task 明确要求 Skill 时，冻结的 Skill binding 未覆盖该要求；一般 Capability
  Requirement 无可用供给时属于 capability gap，不得自动改写成 Skill Need；
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
