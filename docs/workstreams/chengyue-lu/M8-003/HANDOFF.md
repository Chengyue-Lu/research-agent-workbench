# M8-002 → M8-003 节点交接

状态：实现与验证完成，等待节点级审查；未合并。

## 1. 节点结果

本节点把 Mode 的诊断结果推进到两个正式、可追溯但仍不绑定 Runtime 的契约：

```text
Mode result
→ versioned Action（含 Registry content hash）
→ per-Task Method Resolution
→ no-Skill / abstract capability / Skill Need / Human Gate / blocked / split
```

- M8-002 将 Action 从诊断字段提升为可版本化、可哈希引用的正式契约；
- M8-003 为每个 Task 形成独立 Method Resolution，并固定所采用的 Action 内容；
- 八个 routing cases 均有一一对应的 Resolution path/hash；
- Resolution 只表达 obligations、机制、抽象 capability 与处置结果，不选择具体 Tool、Skill、Agent、
  Model、Provider、Adapter、MCP 或 Runtime；
- `no-skill`、Human Gate、blocked 与 split 均为一级结果；`proceed` 不表示 Task 完成或科学主张被接受。

## 2. 分支与提交

| 层级 | 分支 / 提交 | 状态 |
|---|---|---|
| 目标基线 | `develop@5991cafdb7f536cd7b871508de9055d02b558728` | 未改动 |
| M8-002 | `agent/method-m8-002-mode-action-contract@def0689` | PR #26 Draft，无 review request，未合并；审计阻塞项已修复 |
| M8-003 | `agent/method-m8-003-method-resolution`（含 `db17d67` 传播提交） | 堆叠在 M8-002 上，未创建 PR |

M8-003 的提交基点是 M8-002 快照，不是当前 `develop`。这保留了连续契约开发所需的上下文，但在
M8-002 合并前不应直接把 M8-003 作为 `develop` PR 审查或合并。

## 3. 验证摘要

- focused contract/routing/documentation tests：`33 passed`；
- 完整测试：`283 passed, 3 skipped`；
- examples/registry 验证：`84 valid, 0 errors, 0 warnings`；
- Action hash、Resolution path/hash、Need/Gate/block 闭集及 duplicate identity 均有确定性检查；
- provider/runtime/隐式 Assignment/formal-planning selector 混用均有负面测试。

这些证据只证明结构、引用和边界一致，不证明研究方法在具体学科任务中的科学有效性。

## 4. 节点审查重点

一次审查覆盖 M8-002 与 M8-003 的连续语义，重点回答：

1. Action 是否足够稳定、可引用，但没有固化成全局研究 DAG；
2. Method Resolution 是否忠实消费 Action，而没有成为第二个 Router；
3. no-Skill、Skill Need、Human Gate、blocked 与 split 是否保持显式且无损；
4. provider-neutral、Human authority 和执行所有权边界是否仍被保留；
5. 八个诊断 case 是否足以进入下一节点，或需要先补充方法差异 fixture。

审查不要求在这一步决定具体 Skill、Tool、模型、供应商或宿主平台。

## 5. 审查后的合并顺序

1. 对 Action→Resolution 节点进行一次概念与契约审查；需要修改时分别落到所属分支；
2. 先按当前有效政策审查并合并 PR #26（M8-002 implementation，保持 IN_PROGRESS）；
3. 独立审查并合并 Governance v2 R2 PR，再按 rollout 启用远端 ruleset；
4. 用新 `feature` 状态机完成 `M8-002: IN_PROGRESS → DONE`，并在同一 head 激活
   `M8-003: PARKED → READY`；这不是独立 `task-closeout` class，也不自动制造 History；
5. 将 M8-003 变基到该 `develop`，形成合法 `READY → DONE/IN_PROGRESS`，重跑完整验证并创建 R2 PR；
6. M8-003 PR 只需确认节点审查修改、重排 diff、authority/adversarial evidence 与 CI 完整保留。

上述 PR 可以共享一次节点级概念审查，但仍按所属分支和风险分别落地。未经审查不合并；旧
`task-closeout`、人工 base SHA 和逐 Task History 不再作为未来结构。

## 6. 下一边界

本轮停止在 Method Resolution。以下内容属于下一开发段，需要新的 Task 边界后再开始：

- Mode v0.2 migration；
- Capability/Skill 候选解析与绑定；
- Resolved Execution View；
- Assignment、Receipt、Trace、Recovery 或 Runtime 接入；
- 具体模型、Provider、Adapter、MCP、工具和宿主平台选择。

当前最合理的下一动作不是继续编码，而是以本交接、[M8-002 workstream](../M8-002/) 和
[M8-003 验证证据](VALIDATION.md) 为范围进行一次节点审查。
