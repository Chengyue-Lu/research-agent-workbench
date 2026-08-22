# Issue #13 调整执行说明：integration branch rebase 与 shared seam 对齐

## 目的

当前 `agent/m3-m6-trace-integration` 的大量实现基于旧的 Skill-first execution contract：

```text
Task
→ required Skills
→ Skill Assignment
→ API / Runtime
→ Handoff / Receipt
```

而当前 `main` 已通过 ADR-0013、ADR-0016 及 Issue #12 文档冻结，将长期目标调整为：

```text
Task
→ Mode Action
→ Method Resolution
→ Capability Resolution
→ Resolved Execution View
→ Runtime
```

其中以下均为合法 Method Resolution：

```text
no-Skill
direct-tool
Skill Need
Human Gate
blocked
split
```

因此当前 integration branch 需要做一次架构调谐。

本轮目标不是重写 API execution，也不是提前实现 M8，而是：

> 将 execution branch 从已经过时的 shared contract 中解耦，只保留可以稳定复用的 Execution/Trace 能力，为后续 M8-003 后重新接入做好接口准备。

---

# 一、开发冻结范围

在本次 integration cleanup 完成前，请暂停继续扩大以下功能：

- 新增 Provider / Runtime 功能；
- 扩大 Task → API compiler；
- 新增 Method fallback；
- 新增 Skill 自动选择逻辑；
- 为 no-Skill 增加兼容 Skill；
- 新增 live scientific vertical slice；
- 修改 M8 Method/Core 语义；
- 修改 M8-002～M8-005 的任务状态。

允许继续进行：

- rebase；
- Trace contract 整理；
- execution-only tests；
- Provider conformance 准备；
- CI / packaging 修复；
- compatibility seam 清理；
- 将现有改动拆成可独立 review 的 commits。

---

# 二、第一步：rebase 到当前 `main`

请首先将：

```text
agent/m3-m6-trace-integration
```

rebase 到最新 `main`。

重点检查以下近期变化：

```text
ADR-0013
ADR-0016
docs/ARCHITECTURE.md
docs/ROADMAP.md
docs/TASKS.md
docs/modules/02-PROTOCOL_AND_MODES.md
docs/modules/03-AGENT_RUNTIME.md
docs/modules/04-SKILL_SYSTEM.md
docs/modules/05-TASK_AND_HANDOFF.md
docs/modules/07-ARTIFACTS_AND_PROVENANCE.md
docs/modules/09-ADAPTERS_AND_INTEGRATIONS.md
docs/modules/10-OBSERVABILITY_EVALUATION_COST.md
```

不要以旧 branch 中的 docs 覆盖当前 `main` 的 Method/Core 语义。

---

# 三、将现有改动分为三类

## A. 可直接保留的 Execution/Trace 实现

以下能力原则上与新 Method architecture 正交，可继续保留：

```text
Trace Envelope
Trace Event
Trace Index

actor_id
accountable_owner

message sequence
message hash

read event
tool event
command event
file write event
external side-effect event
attempt state event

transient tool result capture

capture gap
delayed capture

redaction metadata
sensitive-data boundary

sequence validation
hash validation
actor ownership validation
read-scope validation
event completeness validation
```

这些内容属于：

```text
M3-008 Execution / Archive Trace
```

其目标是记录：

> 实际发生了什么。

而不是解释：

> 为什么科研方法上应该这么做。

---

## B. 保留但需要重新标记为 compatibility seam 的实现

以下对象当前仍有价值，但不再代表长期架构：

```text
Task.required_skills

Skill Assignment

ResolvedTask
skill_lock

Attempt.skill_lock
Attempt.skill_assignment_ref

Handoff.skill_lock
Handoff.skill_assignment_ref

ExecutionReceipt.skill_assignment_ref
```

处理原则：

1. 不删除历史 replay 能力；
2. 不原地改变 `v0.1.0` 的历史语义；
3. 明确标记为 legacy / compatibility execution contract；
4. 新代码不得继续假定其是未来所有 execution 的必经层；
5. 不扩大这些对象以承载 Method Resolution。

推荐注释语义：

```text
Legacy compatibility representation for Skill-bound execution.
Not the canonical Method → Execution contract.
```

---

## C. 必须删除或延后的实现

以下逻辑不得随当前 integration PR 进入 `main`：

### 1. execution layer 自行决定科研机制

包括：

```text
required capability 缺失
→ 自动选 Skill

Skill 不存在
→ 自动 fallback 到 generic model

Tool 能做
→ execution 自行决定 no-Skill

Provider 不支持
→ execution 更换 methodology
```

这些属于 Method/Capability resolution，不属于 Runtime。

### 2. fake `no-skill` Skill

禁止创建：

```text
no-skill
generic-execution
plain-agent
direct-tool
```

之类的占位 Skill，只为满足：

```text
skill_lock.minItems = 1
```

### 3. 修改 legacy Schema 来伪装支持 no-Skill

不接受仅进行：

```text
skill_lock:
  minItems: 1
```

改成：

```text
minItems: 0
```

因为当前 Resolver、Attempt、Handoff、Receipt 和 capability coverage 均仍是 Skill-first。

这不是完整修复。

### 4. execution branch 内提前实现 Method Resolution

不得在当前 branch 自行新增或冻结：

```text
MethodResolution
MechanismDecision
SkillNeed
ModeAction resolution
Claim admissibility
Decision Authority
```

这些由：

```text
M8-002
M8-003
M8-005
```

负责。

---

# 四、M3-008 的明确边界

本次应优先抽离出一个纯 M3-008 Trace Core。

允许的 Trace 字段回答：

```text
Who?
When?
Read what?
Called what?
Wrote what?
Sent what?
Received what?
What side effect occurred?
What failed?
Was capture complete?
Was anything redacted?
```

不允许 M3-008 回答：

```text
Why was this Mode selected?
Why was this Action required?
Why was Skill preferred over Tool?
Why was no-Skill valid?
Why was a Claim promoted?
Why was a Human Gate triggered?
Why was an alternative rejected?
```

后一组属于：

```text
M3-009 Method Trace
```

并依赖：

```text
M8-003 Method Resolution
M8-005 Decision Authority
```

---

# 五、建议拆分当前 branch

建议至少形成以下 commit / PR boundary。

## Part A — M3-008 Trace Core

包含：

```text
Trace Schema
Trace models
Trace validator
risk codes
fixtures
tests
CLI validation surface
```

要求完全 provider-neutral。

## Part B — Execution Trace Adapter

依赖 Part A。

包含：

```text
API session → trace events
tool call → trace event
file/result capture
capture gap
execution receipt linkage
```

对应：

```text
M6-006
```

可以继续开发，但最好不要和 Trace Schema 本身混成不可拆 PR。

## Part C — Method-dependent execution bridge

暂缓。

等待：

```text
M8-002
↓
M8-003
```

之后重新实现：

```text
Method Resolution
→ Capability Resolution
→ Resolved Execution View
→ Runtime
```

---

# 六、no-Skill 问题的临时处理规则

当前 branch 不负责“解决 no-Skill execution”。

在 M8-003 完成前：

## Legacy historical task

如果明确引用历史 Skill：

```text
required_skills:
  - skill-id@version
```

则继续走：

```text
legacy Skill Assignment
→ legacy ResolvedTask
→ execution
```

用于：

```text
historical replay
compatibility fixture
legacy regression
```

## 新 Method-first task

如果逻辑上属于：

```text
no-Skill
direct-tool
```

则当前 integration branch：

```text
不得伪造 Skill
不得自行 fallback
不得声称完整 Method execution 已支持
```

可以返回明确 capability/interface gap，例如：

```text
METHOD-RESOLUTION-REQUIRED
```

或等价的临时 integration blocker。

该 gap 在 M8-003 后由正式 Method Resolution 消除。

---

# 七、未来 shared seam 预期

execution branch 后续应准备消费，而不是定义以下对象：

```text
Task Packet
Method Resolution
Capability Requirement
Data / Permission Policy
```

之后由 Capability 层产生：

```text
Resolved Capability Snapshot
```

再形成：

```text
Resolved Execution View
```

Runtime/API 的职责是：

```text
Resolved Execution View
↓
执行
↓
Execution Trace
Execution Receipt
Artifacts
Handoff candidate
```

Runtime 不应反向修改：

```text
Mode
Action
Method Resolution
Skill Need
Claim ceiling
Human Gate
```

---

# 八、未来 Resolved Capability Snapshot 应允许三类正常状态

以下只是接口方向，不要求当前 branch 实现 Schema。

## no-Skill

```yaml
skills: []
tools: []
```

## tool-only

```yaml
skills: []
tools:
  - capability: bounded-compute
    binding: ...
```

## Skill-backed

```yaml
skills:
  - skill_id: convergence-study
    version: 1.0.0
    content_hash: ...
tools:
  - capability: bounded-compute
    binding: ...
```

因此未来：

```text
Skill Assignment
```

只是 Capability Resolution 的一个结果，而不是 execution 的 universal root object。

---

# 九、EVID-SIR-001 / SIM-SIR-001 调整

若当前两个 SIR 依赖新的：

```text
no-Skill / direct-tool Method Resolution
```

则不再作为 M3-008 merge gate。

当前 M3-008 只需使用：

```text
synthetic fixture
contract fixture
legacy Skill-bound fixture
```

证明：

```text
Task/Attempt
→ execution
→ Trace
→ closeout
→ validator
```

的执行事实链正确。

完整的新架构 live path 延后到 M8-003 后：

```text
Task
→ Mode Action
→ Method Resolution
→ Capability Resolution
→ Resolved Execution View
→ API
→ Execution Trace
→ Receipt
→ closeout
→ verify
```

---

# 十、OpenAI live conformance

以下工作仍可继续准备：

```text
OpenAI Responses text
OpenAI Responses structured output
OpenAI Responses client tool call
```

但它们属于：

```text
Provider / M6 live conformance
```

不影响 Method/Core 语义。

要求继续保持：

- 显式模型；
- 不自动 fallback；
- 不保存 credential；
- Provider 返回模型可核对；
- structured result 本地 Schema 再验证；
- Tool call 本地 allowlist + argument Schema；
- conformance report 脱敏。

---

# 十一、SAFE_PAUSE / process recovery

以下测试继续保留：

```text
process kill
↓
Attempt remains incomplete / safe-paused
↓
state persisted
↓
new process
↓
new Attempt
↓
resume from frozen inputs
```

但需要注意：

```text
resume
```

不得通过恢复 Provider session / hidden model state 实现。

恢复事实源必须继续来自：

```text
Task
Attempt
Main State
Artifacts
Trace
Receipt
Handoff
```

而不是 provider response ID。

---

# 十二、`docs/TASKS.md` 处理规则

请从 integration branch 中移除对以下任务状态的自行修改：

```text
M8-002
M8-003
M8-004
M8-005
```

当前 `main` 中：

```text
M8-002 READY
M8-003 PARKED
M8-004 PARKED
M8-005 PARKED
```

继续作为唯一权威状态。

execution branch 依赖未来接口：

```text
≠
这些接口已经 IN_PROGRESS
```

若需要记录依赖，请在：

```text
PR body
Issue #13
branch worklog
```

中说明，不修改共享任务真值。

---

# 十三、risk codes 审查规则

Execution Trace risk code 可以描述：

```text
TRACE-MESSAGE-MISSING
TRACE-SEQUENCE-GAP
TRACE-HASH-MISMATCH
TRACE-ACTOR-UNOWNED
TRACE-CAPTURE-DELAYED
TRACE-REDACTION-UNDECLARED
TRACE-READ-OUTSIDE-SCOPE
TRACE-EVENT-MISSING
TRACE-TRANSIENT-RESULT-MISSING
TRACE-PROCESS-ARTIFACT-OVERWRITTEN
TRACE-SENSITIVE
TRACE-DATA-BOUNDARY
```

但不要由 execution Trace 新增类似：

```text
MODE-WRONG
METHOD-WRONG
SKILL-NOT-NEEDED
CLAIM-INVALID
HUMAN-GATE-WRONG
```

这类 Method/Core 判断。

---

# 十四、完成本次调谐后的验收条件

## Branch hygiene

- [ ] 已 rebase 最新 `main`
- [ ] 不覆盖 ADR-0016 / Issue #12 后的稳定 docs
- [ ] 不修改 M8-002～005 状态
- [ ] Method/Core 与 Execution 代码修改可以明确区分

## M3-008

- [ ] Trace 只记录可观察 Execution/Archive facts
- [ ] Trace Schema 不包含 Method reasoning
- [ ] message/event sequence 可验证
- [ ] actor/accountable owner 可验证
- [ ] capture gap 可表达
- [ ] redaction 可表达
- [ ] read/tool/write/external events 可验证
- [ ] transient tool result 不会静默丢失
- [ ] 不保存 Chain-of-Thought / secret

## Legacy compatibility

- [ ] v0.1 Skill-bound execution 可 replay
- [ ] 未原地改变历史 Schema 语义
- [ ] legacy Skill Assignment 被明确视为 compatibility contract
- [ ] 新代码不假定所有未来 execution 必有 Skill

## no-Skill

- [ ] 没有 fake Skill
- [ ] 没有通过空 Skill lock 假装完成迁移
- [ ] execution branch 不定义 Method Resolution
- [ ] 新 no-Skill path 在 M8-003 前明确保持 gap

## Runtime boundary

- [ ] Runtime 不改变 Mode
- [ ] Runtime 不选择 methodology fallback
- [ ] Runtime 不批准 Human Gate
- [ ] Runtime 不提升 Claim
- [ ] Runtime 不自动更换 Provider/Model

## Tests

- [ ] offline contract tests PASS
- [ ] Trace regression tests PASS
- [ ] Python 3.11 / 3.13 CI PASS
- [ ] wheel / clean venv PASS
- [ ] live-only tests 与 offline tests 明确分开

---

# 十五、本轮完成标志

达到以下状态即可认为 Issue #13 的“shared architecture blocker”已经解决：

```text
current main
+
clean M3-008 Execution Trace contract
+
legacy Skill execution compatibility
+
explicit Method-resolution gap
+
no execution-defined methodology
```

此时可建立同步节点：

```text
K-INTEGRATION-1
Method / Execution Shared Seam Freeze
```

随后恢复开发顺序：

```text
M8-002 Mode Action
↓
M8-003 Method Resolution
↓
M3-009 Method Trace
      +
Method → Capability → Execution bridge
↓
EVID-SIR / SIM-SIR
↓
live conformance / recovery integration
```

---

# 核心原则

本轮调整不要以“让旧 pipeline 继续跑通”为目标。

应以：

> **让 Execution 层能够在不理解、也不重新定义科研方法语义的情况下，稳定消费未来 Method/Core 输出。**

为目标。

已经完成且经过充分测试的 API、Trace、Receipt、SAFE_PAUSE 等实现尽可能保留；需要淘汰的是过时的 shared assumptions，而不是为了架构更新重写全部 execution code。
