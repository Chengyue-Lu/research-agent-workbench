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
| 目标基线 | `develop@51c86072c986826f1abc7ca3b17018169b7ca75d` | Governance v2 与调研文档已接入统一分支 |
| 统一活动节点 | `agent/method-m8-action-resolution-node` | 正式合流原 M8-002 与 M8-003 历史；后续 M8 工作只落到此分支 |
| M8-002 历史引用 | `def0689` | PR #26 已撤回、未合并；原分支已删除，提交仍是统一分支祖先 |
| M8-003 历史引用 | `1610d87` | 原分支已删除，提交仍是统一分支祖先 |

统一分支从 M8-003 完整实现 head 建立，并通过 merge commit 纳入原 M8-002 最终 head，因此两个旧
head 都是统一分支的祖先。该拓扑保留连续契约开发上下文，也消除了两个活动交付分支之间的漂移。

## 3. 验证摘要

- contracts/schemas/Action/Resolution/routing/documentation/governance focused tests：`79 passed`；
- 完整测试：`298 passed, 3 skipped`；
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

## 5. 审查与合并顺序

1. 以统一分支对 Action→Resolution 节点进行一次概念与契约审查；所有修改只落到统一分支；
2. Governance v2 已合并到 `develop`；统一分支已更新到该基线；
3. 当前 feature 快照完成 `M8-002: READY → DONE`，并把 `M8-003: PARKED → READY`；这不自动宣告
   M8-003 完成；
4. 重跑完整验证并创建一个统一的 M8 R2 PR，保留 authority/adversarial evidence 与跨负责人审查；
5. M8-003 的 `READY → DONE` 仅在节点验收成立后由后续合法状态推进完成。

Governance 与 M8 仍是两个独立风险边界；M8-002/M8-003 则只保留一个活动实现分支和一个未来 PR。
未经审查不合并；旧 `task-closeout`、人工 base SHA 和逐 Task History 不再作为未来结构。

## 6. 下一边界

本轮停止在 Method Resolution。以下内容属于下一开发段，需要新的 Task 边界后再开始：

- Mode v0.2 migration；
- Capability/Skill 候选解析与绑定；
- Resolved Execution View；
- Assignment、Receipt、Trace、Recovery 或 Runtime 接入；
- 具体模型、Provider、Adapter、MCP、工具和宿主平台选择。

当前最合理的下一动作不是扩张到新接口，而是以本交接、[M8-002 workstream](../M8-002/) 和
[M8-003 验证证据](VALIDATION.md) 为范围完成统一 R2 PR 的跨负责人节点审查。
