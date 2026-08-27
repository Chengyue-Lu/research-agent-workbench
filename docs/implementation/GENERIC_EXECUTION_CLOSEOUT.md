# Generic Execution Closeout 与 M11 Core Gate

M11-004 在不修改 legacy Skill-bound Receipt 的前提下，为 no-Skill/direct Tool Core 增加独立、可文件重放的
Action/Capability-slice closeout：

```text
Task + exact Action/Capability slice + Resolved Execution View
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

- Host report 的 View/Runtime Bundle/Task/execution-slice/Attempt lineage 对齐；receipt-eligible 生命周期的
  facts capture 必须完整，completed 还至少有
  一个输出 Artifact，failed/blocked 时不得宣称 execution completion；
- completed：Host actual binding/Supply 必须等于 View；detected post-call failed：保留可能不相等的 actual
  binding/Supply，并由 diagnostic + typed hash-pinned Trace execution fact 共同佐证；preflight blocked：actual binding/Supply
  必须不存在且 Trace 不得含 Provider/Tool 调用；
- Trace 通过既有 M3-008 validator，identity/status/frozen/completeness 对齐，且 provider-request 与 tool
  operation 的实际次数/identity 分别闭合到 Host facts；Trace Actor 的 Provider/Runtime identity 闭合到
  Host actual binding，实际 Tool 必须属于 selected Supply 的 Tool component；
- Trace `decision_refs` 必须恰好含一个 hash-pinned execution-scope binding record；每个 post-call Trace 还必须
  恰好含一个符合 `execution_trace_fact` Schema 的 actual-execution-binding record，逐字段闭合
  Provider/Adapter/Model/Runtime/Host 和 actual Supply；preflight-blocked Trace 禁止该 fact。这里复用 v0.1
  的 immutable file-ref envelope，不把 execution fact 解释成 Method 或 Supply decision；
- Artifact path/hash 与 Host report 一致；
- deterministic validation 为 `pass`，checker source hash 有效；
- validation subject closed set 精确等于 Host report + Trace INDEX + Artifacts，无遗漏或偷渡；
- selected Supply kind 属于 procedure/no-Skill、direct Tool 或 Adapter/Provider Core，而不是 Skill。

completed Receipt 固定 `completion_claim: action-capability-slice-only`；failed/blocked Receipt 只能为
`none`，且所有状态均固定 `task_completion: false`。Schema 排除
`skill_assignment_ref`、Claim、Human approval、recovery 等字段。`validate_generic_execution_receipt()` 从
Receipt 自身 refs 重新加载 View、Host report、Trace、Actors、event ledger、hash-pinned execution fact、
Artifacts 和 validation，独立重做完整 actual binding/Supply、provider/tool facts 与 selected-Supply component
等 cross-object invariant，再调用同一 builder 逐字段重算。failed post-call 若缺少该 fact，或任一
Provider/Adapter/Model/Runtime/Host/Supply 字段不能被 Trace 独立闭合，就不具备 replay-valid Receipt 资格。

## 为什么不改 legacy Receipt

现有 `execution_receipt` 与 `ExecutionReceipt` model 继续要求 Skill Assignment，并服务既有 Skill-bound
archive/replay。M11 新路径使用 `generic_execution_receipt`，避免把“可选 Assignment”硬塞进旧 Schema，或
破坏历史解析。回归测试继续解析 checked-in legacy Receipt，证明旧字节和模型保持不变。

## Core Vertical Gate

`execution_core_gate` 必须同时引用一条已文件重放的 no-Skill Receipt 和一条 direct-Tool Receipt，并固定：

- exact replay；
- Skill Assignment absent；
- Action/Capability-slice execution only；
- legacy Receipt unchanged；
- 无 Claim/Human/fallback/Topic 5 effect。
- 无 whole-Task completion effect。

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
