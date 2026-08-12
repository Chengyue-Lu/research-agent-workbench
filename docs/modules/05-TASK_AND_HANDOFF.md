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
stop_conditions:
  - required_outputs_complete
  - source_boundary_exhausted
  - human_judgment_required
stale_if:
  - any_input_hash_changes
```

Task 必须可在有限时间内完成。`goal` 不能写成“完成整个研究”或“确保论文正确”。

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
- 失败 Handoff 也是正式结果，不得丢弃。

## 6. Attempt 与 Task

一次 Task 可以有多个 Attempt。重试必须使用新 `attempt_id`，记录触发原因、输入是否变化、Skill/模型/工具是否变化。禁止覆盖失败 Attempt。

Attempt 可以引用一份 `Execution Receipt`。Receipt 记录实际 Runtime、模型用量状态、协调/执行成本、Context Snapshot 和 trace 策略；Handoff 也回指同一 Receipt。验证器检查这三者的 Task、状态、时间和路径一致性，避免把另一次执行的成本或结果串入当前交接。

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

## 8. 预警

- `TASK-TOO-BROAD`：目标无法在预算内完成；
- `TASK-SKILL-MISMATCH`：required capability 没有被 Skill 覆盖；
- `TASK-WRITE-OVERLAP`：并行写范围重叠；
- `TASK-STALE-INPUT`：输入 hash/revision 变化；
- `HANDOFF-MISSING-OUTPUT`：缺失必需工件；
- `HANDOFF-LOSSY`：摘要存在无引用关键结论；
- `HANDOFF-OMITS-NEGATIVE`：失败、反证或限制未交接；
- `HANDOFF-CLAIM-UPGRADE`：Handoff 越过 Claim ceiling。

## 9. 验收条件

- Task 不携带完整项目聊天即可执行；
- Handoff 可由 Schema 和引用检查器验证；
- 主 Agent能只读 Handoff 决定接受、回查、重做或 Human Gate；
- 失败 Attempt 和负结果保留；
- 输入变化后旧 Handoff 自动标记 stale；
- 并行任务不能写入同一正式路径。
