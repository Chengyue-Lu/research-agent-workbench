# Generic Execution Closeout 与 M11 Core Gate

M11-004 在不修改 legacy Skill-bound Receipt 的前提下，为 no-Skill/direct Tool Core 增加独立、可文件重放的
execution-only closeout：

```text
Task + Resolved Execution View
  ↓ Thin Host
Execution Host Fact Report
  + frozen Agent Trace
  + exact output Artifacts
  + passing deterministic validation report(s)
  ↓ exact subject closure
Generic Execution Receipt
```

## Generic Receipt

`build_generic_execution_receipt()` 只接受 exact pins，并验证：

- Host report 为 `completed` 且 facts capture 完整，View/Task/Attempt lineage 对齐；
- Trace 通过既有 M3-008 validator，identity/status/frozen/completeness 对齐；
- Artifact path/hash 与 Host report 一致；
- deterministic validation 为 `pass`，checker source hash 有效；
- validation subject closed set 精确等于 Host report + Trace INDEX + Artifacts，无遗漏或偷渡；
- selected Supply kind 属于 procedure/no-Skill、direct Tool 或 Adapter/Provider Core，而不是 Skill。

Receipt 固定 `completion_claim: execution-only`，并以 schema 排除 `skill_assignment_ref`、Claim、Human approval、
recovery 等字段。`validate_generic_execution_receipt()` 从 Receipt 自身 refs 重新加载 View、Host report、Trace、
Artifacts 和 validation，再调用同一 builder 逐字段重算；hash-valid Receipt rewrite 或任一下游文件漂移都会
fail closed。

## 为什么不改 legacy Receipt

现有 `execution_receipt` 与 `ExecutionReceipt` model 继续要求 Skill Assignment，并服务既有 Skill-bound
archive/replay。M11 新路径使用 `generic_execution_receipt`，避免把“可选 Assignment”硬塞进旧 Schema，或
破坏历史解析。回归测试继续解析 checked-in legacy Receipt，证明旧字节和模型保持不变。

## Core Vertical Gate

`execution_core_gate` 必须同时引用一条已文件重放的 no-Skill Receipt 和一条 direct-Tool Receipt，并固定：

- exact replay；
- Skill Assignment absent；
- execution-only；
- legacy Receipt unchanged；
- 无 Claim/Human/fallback/Topic 5 effect。

测试中的两个独立 bounded project fixture 都经过：

```text
Runtime Bundle → View → Host → Trace + Artifact + Validation → Generic Receipt replay
```

Gate 证明结构和执行边界闭合，不证明真实 Provider readiness、方法适用性、科研输出正确性或 Human Gate 已满足。

## 边界

- closeout 不创建 Trace，只消费已经 frozen 的 Trace；
- 不把 Host `completed` 改写为 Task contract satisfied、Claim accepted 或 Human approved；
- 不创建 dummy Skill/Assignment；
- 不实现 Handoff、safe pause、resume、salvage 或 recovery；
- 不负责发布文件或 marker-last transaction；需要持久化时，调用方应使用单独的原子发布层。
