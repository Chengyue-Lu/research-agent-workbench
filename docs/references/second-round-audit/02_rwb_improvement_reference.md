<!-- markdownlint-disable -->
# Research Agent Workbench 改进参考

> 基于 PR11 / ADR-0013 的 Mode-first 方向与第二轮外部生态平行审计整理。
> 目标不是追求单领域短期最佳，而是建立可复用、可迁移、可持续演化且历史研究资产可验证的科研 Agent 控制平面。

# 1. 建议的长期定位

推荐定位：

> **A versioned, method-aware research control plane for continuously evolving AI agents.**
>
> 一个面向持续演化 AI Agent 的、版本化科研方法控制平面。

核心原则：

> **Research semantics and history should outlive models, runtimes, tools and skills.**

RWB 应长期保存：

- research meaning；
- research state；
- evidence / claim provenance；
- human decisions；
- method decisions；
- attempts / failures / trace。

RWB 应允许持续替换：

- LLM / Provider；
- Agent Runtime；
- Tool / MCP / CLI / API Adapter；
- Skill implementation；
- Search engine / database；
- orchestration / deliberation strategy；
- Agent Profile；
- prompt template。

---

# 2. 当前 PR11 最值得保留的核心

ADR-0013 已经确立以下关键原则：

1. Mode-first，不做 Mode-to-Skill 固定绑定；
2. 从 Mode 派生 Action / Failure / Artifact / Gate；
3. 每个 Action 先判断最小充分机制；
4. `no-Skill` / `tool-only` / `Human Gate` / `blocked` 都是正常结果；
5. Skill dossier 以 Need 为主键，而不是外部 Skill 名称；
6. 现有 accepted Skill 不等于永久核心；
7. 在真实困难任务证明增量价值前，不盲目扩 Skill。

这些原则建议继续作为系统核心，而不是 PR11 的阶段性工作说明。

---

# 3. 当前最大结构性缺口

## 3.1 PR11 的方法论尚未成为正式系统语义

当前正式 `research-mode.schema.json` 仍要求类似：

- `recommended_skill_capabilities`

当前 Task Packet 也主要存在：

- `active_modes`
- `required_capabilities`
- `required_skills`

但 PR11 真正的核心链路是：

```text
Task
  ↓
Mode
  ↓
Action
  ↓
Failure / Artifact / Claim / Gate
  ↓
Method Obligation
  ↓
Minimal Mechanism
  ↓
Task / Tool / Skill Need / Human / Blocked
```

因此当前最优先工作不是继续添加 Skill，而是让这条链路成为正式 contract。

---

# 4. 建议的五层长期架构

```text
┌─────────────────────────────────────────────┐
│ 5. Execution Hosts                         │
│ Codex / Claude / Gemini / Agents SDK       │
│ LangGraph / future runtimes                │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ 4. Capability & Strategy Plane             │
│ Skill / Tool / External Agent / Strategy   │
│ Capability Resolver                        │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ 3. Method Plane                            │
│ Mode → Action → Method Resolution          │
│ Skill Need / Protocol Profile / Human Gate │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ 2. Research State Plane                    │
│ Question / Evidence / Claim / Unknown      │
│ Contradiction / Assumption / Attempt       │
│ Failure / Frontier / Decision / Artifact   │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ 1. Integrity Kernel                        │
│ ID / Schema / Hash / Version / Migration   │
│ Permission / Lineage / Trace / Validation  │
└─────────────────────────────────────────────┘
```

稳定性原则：

- 越靠下越稳定；
- 越靠上越可替换；
- Execution 不拥有科研语义解释权。

---

# 5. 建议新增或正式化的核心对象

## 5.1 `Mode Action`

正式化当前 Action Catalog，而不是继续仅保存在设计文档中。

至少包括：

```yaml
id:
mode_id:
trigger:
non_trigger:
required_inputs:
failure_modes:
required_artifacts:
claim_effects:
human_gates:
stop_conditions:
blocked_conditions:
```

## 5.2 `Method Resolution`

这是建议新增的最核心对象。

用途：解释一个 Atomic Task 为什么选择某 Mode / Action / Mechanism。

建议至少记录：

```yaml
task_id:
mode_resolution:
selected_actions:
method_obligations:
mechanism_resolution:
human_gates:
blocked_if:
alternatives_rejected:
resolution_status:
```

要求：

- 可序列化；
- 可 hash；
- 可验证；
- 可重放；
- 不依赖具体 Provider / Model / Host。

## 5.3 `Skill Need`

Skill Need 应成为正式对象，而不是候选说明文字。

至少包括：

```yaml
need_id:
mode_action:
trigger:
non_trigger:
semantic_gap:
direct_tool_baseline:
no_skill_baseline:
expected_increment:
required_evidence_before_trial:
known_domain_variants:
```

## 5.4 `Protocol Profile`

用于表达：

- PRISMA；
- Cochrane；
- ASME V&V；
- domain-specific reporting/validation standards；
- project-specific approved methodology。

原则：

```text
Mode ≠ Protocol ≠ Skill
```

Mode 表达通用科学方法边界；Protocol 表达领域/社区规范；Skill 表达可复用语义动作。

## 5.5 `Capability Requirement` + `Capability Snapshot`

RWB 应请求 capability，而不是请求某个具体厂商 Tool。

```yaml
capability_id: literature-search
constraints:
  read_write: read-only
  data_egress: metadata-only
  source_scope: [...]
```

Resolver 输出冻结 snapshot：

```yaml
provider:
adapter:
version:
capability_hash:
permission_class:
data_egress:
side_effects:
```

## 5.6 `Research Strategy`

未来可选，不应立即进入 P0。

用于表达：

- direct；
- plan-act-reflect；
- tree-search；
- tournament；
- evolutionary search；
- parallel independent review。

原则：

```text
Mode ≠ Strategy
```

同一 Mode 可在不同 Task 上采用不同 Strategy。

---

# 6. Evidence / Claim 体系需要升级

## 6.1 不再只依赖 Mode-level claim ceiling

多 Mode 组合不一定只是“取最严格值”。

例如：

```text
simulation evidence
+
experimental evidence
```

可能产生新的联合支持关系，而不是简单 `min(ceiling)`。

建议未来从：

```text
active Mode → claim ceiling
```

逐步转向：

```text
Evidence provenance
    ↓
Evidence–Claim relation
    ↓
Composition rule
    ↓
Claim admissibility
```

## 6.2 Claim promotion 权限

建议明确：

- Agent 可以提出 Claim；
- deterministic checker 可以验证结构与 provenance；
- Method rule 决定是否允许进入某个 Claim class；
- 高风险 / 科学解释类 promotion 必须 Human Gate。

---

# 7. 决策权必须显式建模

建议形成 Decision Authority Matrix：

| 决策 | Agent | Deterministic Resolver | Human |
|---|---:|---:|---:|
| Mode 建议 | ✓ | 校验 | 高风险确认 |
| Action 选择 | ✓ | catalog 校验 | 必要时 |
| Mechanism | 建议 | 主决定 | 歧义时 |
| Skill Need | 建议 | Need 校验 | 必要时 |
| 具体 Skill | 不自由决定 | 主决定 | 歧义/高风险 |
| Tool Adapter | 不自由 fallback | 主决定 | 高风险外部写 |
| Claim promotion | 建议 | 方法校验 | 最终科学解释 |
| 放宽数据/权限 | ✗ | ✗ | 必须 |

目标：避免两种极端：

- 纯 LLM Router；
- 所有科研流程完全写死为 DAG。

推荐概念：**Governed Semantic Routing**。

---

# 8. Research State：实现“跨年份科研连续性”

建议长期状态逐步包含：

```text
Question
Evidence
Claim
Unknown
Contradiction
Assumption
Method
Run
Artifact
Decision
Attempt
Failure
Frontier
Human Gate
```

其中失败记录至少包括：

```yaml
attempt_id:
goal:
method:
outcome:
failure_reason:
what_was_learned:
revisit_condition:
```

这样未来 Agent 不会因为上下文丢失而重复已经被证伪/阻断的方向。

核心原则：

> Research State 的生命周期必须长于任何 Runtime implementation。

---

# 9. Migration：长期可延续性不可缺少

Version 只说明“发生了变化”；Migration 才允许旧研究继续存在。

建议所有长期语义对象支持：

```text
schema_version
semantic_version
migration_history
content_hash
producer
producer_version
```

迁移记录至少保存：

```text
original_hash
from_version
to_version
migration_tool_version
new_hash
```

尤其需要支持：

- Research Mode migration；
- Method Resolution migration；
- Research State migration；
- Skill Need migration；
- Protocol Profile migration。

---

# 10. Skill 从“版本管理”升级为“演化管理”

建议生命周期：

```text
discovered
  ↓
audited
  ↓
candidate
  ↓
trial
  ↓
accepted
  ↓
active
  ↓
superseded
  ↓
deprecated
  ↓
retired
```

Promotion 必须基于评测证据，而不是“文档更完整”。

推荐 Evaluation Record：

```yaml
skill_version:
need_id:
mode:
task_suite:
host:
model:
tool_snapshot:
baseline:
metrics:
result:
limitations:
```

关键 baseline：

1. Plain Agent；
2. Plain Agent + Tool；
3. Mode + no-Skill/direct-tool；
4. Mode + candidate Skill。

如果候选 Skill 无明显增量，应保留 no-Skill。

---

# 11. Governed Evolution Loop

RWB 的“自我进化”不应等于 Agent 直接修改 Core。

推荐：

```text
Observed Failure / New External Method
             ↓
Method or Capability Gap
             ↓
Candidate Change Proposal
             ↓
Static Audit / License / Security
             ↓
Sandbox Trial
             ↓
Evaluation Suite
             ↓
Baseline Comparison
             ↓
Shadow Use
             ↓
Human Review
             ↓
Versioned Promotion
```

适用于：

- Skill；
- Tool Provider；
- Method Action；
- Protocol Profile；
- Strategy。

Mode Core 的变更应比上述对象更慢、更严格。

---

# 12. Trace 从 Observability 升级为科研核心

Trace 不只是：

- token；
- latency；
- API call；
- debug log。

RWB 还需要解释：

```text
why this Mode
why this Action
why Skill instead of Tool
why this Skill
what alternatives were rejected
what Human Gate occurred
what evidence changed the research state
why a Claim was promoted/rejected
```

因此 M3-008 的设计建议对齐 Method Plane，而不是只记录 Execution Plane。

长期核心可概括为：

```text
Method
Evidence
Claim
Trace
```

---

# 13. Execution Plane 的定位

PR10 类 API/session/runtime 工作仍然重要，但应明确成为下游消费层。

Execution 可以负责：

- model/provider binding；
- fresh session；
- tool calls；
- budget；
- side effects；
- checkpoint/resume；
- runtime receipt；
- execution trace。

Execution 不应负责定义：

- Claim ceiling；
- Mode semantics；
- Skill Need；
- Human scientific authority；
- external source admissibility；
- methodology fallback。

重新接入 PR10 类工作前，优先冻结 Method/Trace shared contracts。

---

# 14. 建议暂不扩张的方向

现阶段不建议把主要精力投入：

- 更多 Provider；
- 大量 Agent Profiles；
- 通用 Supervisor；
- distributed Agent runtime；
- 长上下文 memory 系统；
- Skill marketplace；
- 十几个正式 Research Mode；
- 自动安装外部 Skill；
- 大规模 Scientific Tool 内建库；
- 通用 DAG builder。

原因：这些方向已有成熟生态，且会稀释 PR11 的核心。

---

# 15. 长期设计判断标准

任何新功能进入 Core 前，建议回答五个问题：

1. 它表达的是**科研语义**还是**当前实现手段**？
2. 这个对象在换模型/Tool/Runtime 后还需要存在吗？
3. 它能否通过已有 Mode/Task/Tool/Human 表达？
4. 它是否有 baseline 证明增量价值？
5. 五年后升级时，旧研究记录还能否解释和迁移？

若答案偏向 implementation，应放到 Adapter/Provider/Strategy 层，而不是 Core。
