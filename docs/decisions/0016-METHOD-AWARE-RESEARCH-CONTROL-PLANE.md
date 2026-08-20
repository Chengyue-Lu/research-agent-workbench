# ADR-0016：方法感知、可演化的科研控制平面

状态：Accepted

日期：2026-08-20

## 背景

ADR-0013 已把 Skill 选择从“来源优先”改为 `Mode → Action → 最小机制 → Skill Need`，但该链路
仍主要存在于设计文档和诊断 fixture 中。正式 Schema 仍允许 Mode 直接推荐 Skill capability，
`Resolved Task` 也没有独立说明为何选择某个 Action、Tool、Skill、Human Gate 或 blocked。

与此同时，Provider、Agent Runtime、科研工具和通用检索能力正在快速商品化。若 RWB 继续以
Runtime、Agent 数量、Tool 数量或 Skill 仓库为中心，将与现有平台重复，并使历史研究状态绑定
短生命周期实现。

## 决定

### 1. 长期定位

RWB 定位为：

> 一个面向持续演化 AI Agent 的、版本化且方法感知的科研控制平面。

科研语义、研究状态、证据关系、人类决定、失败与关键 Trace 应比 Model、Runtime、Tool、Skill
和 prompt 活得更久。

### 2. 五个逻辑平面

1. **Integrity Kernel**：ID、Schema、hash、version、migration、permission、lineage、validation；
2. **Research State Plane**：Question、Evidence、Claim、Unknown、Contradiction、Assumption、
   Attempt、Failure、Frontier、Decision 与 Artifact；
3. **Method Plane**：Mode、Mode Action、Method Obligation、Method Resolution、Protocol Profile、
   Skill Need 与 Human Gate；
4. **Capability & Strategy Plane**：Capability Requirement/Snapshot、Skill、Tool、External Agent 与
   可替换 Research Strategy；
5. **Execution Hosts**：纯 API session、Codex、Claude、OpenCode 或其他 Runtime。

越靠下越稳定；Execution 只能消费冻结契约，不拥有科研语义解释权。

### 3. Method Resolution 成为正式中间语义

未来的正式解析链为：

```text
Task → Mode → Action → Method Obligation → Minimal Mechanism
     → Capability Requirement / Skill Need / Human Gate / Blocked
```

`Method Resolution` 必须可序列化、可哈希、可验证、可回放且不包含 Provider/Model/Host 字段。
当前 `Resolved Task` 和 `Skill Assignment` 继续作为兼容执行视图，待新契约稳定后再迁移，不能
通过文档改名假称已经实现。

### 4. 概念正交

- `Mode != Protocol Profile != Research Strategy`；
- `Skill Need != Skill candidate != accepted Skill`；
- `Capability Requirement != Tool/Provider binding`；
- `Execution Trace != Method Trace`；
- `Research State != conversation memory`。

### 5. 决策权和评测

Agent 可以提出 Mode、Action、Mechanism 与 Claim 候选；确定性 Resolver 校验 catalog、边界和
证据链；歧义、高风险科学解释、权限放宽和 promotion 进入 Human Gate。LLM 不得静默放宽
source、data、permission 或 Claim 边界。

任何新增 Skill、Strategy 或复杂控制机制都必须与 Plain Agent、Tool-only、Mode+no-Skill 等
简单基线比较。没有可测增量时保留简单机制。

### 6. Trace 分层演进

M3-008 继续负责 provider-neutral 的可观察执行/Archive 基线；后续独立节点增加 Method Trace，
记录 Mode/Action/Mechanism/Human Gate/Evidence/Claim/Failure 的关键决定。两者通过稳定 ID 关联，
不要求主 Agent 默认读取完整账本，也不保存隐藏 Chain-of-Thought。

### 7. 受治理的演化

外部 Skill、Tool、Method、Protocol 或 Strategy 只能沿
`discover → audit → candidate → trial → evaluation → shadow → human review → promotion`
演化。发现和自动生成永远不等于准入；旧版本与原始研究状态不得被静默覆盖。

## 后果

- 下一优先级从真实 Skill/Handoff 扩跑转为 Mode Action、Method Resolution、Mode v0.2 和
  Decision Authority 的正式化；
- Research State、Claim composition、Method Trace、Capability Snapshot 和迁移框架进入后续
  阶段，不一次构建统一知识图谱；
- API/Runtime 工作保留，但在共享 Method/Capability/Trace 契约稳定后重新接入；
- 现有 M0–M7 工件保留为实现和历史证据，不因新分层被重命名或删除。

## 不采用

- 把端到端 autonomous scientist 作为产品目标；
- 用固定 Blueprint/DAG 代替 Method Resolution；
- 让 Mode 直接加载 Skill bundle；
- 以长期聊天记录代替 Research State；
- 先建设 Tool marketplace、通用 Supervisor 或更多 Provider；
- 一次性形式化所有学科的 Claim composition。
