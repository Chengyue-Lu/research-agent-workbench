# ADR-0008：用 Transfer Manifest 和有界抽查约束 Handoff 摘要失真

状态：Accepted

日期：2026-08-13

## 背景

子 Agent 的局部上下文允许被压缩或丢弃，但 `handoff_ready: true` 过去只是一项布尔自述。Schema、路径和哈希可以证明 Handoff 存在，却不能证明关键限定、负结果或未解决项确实从任务工件进入了 Handoff。另一方面，对每份 Handoff 启动第二个 Agent 全量复核，会把节省的上下文和 token 重新消耗在控制面上。

## 决定

1. Task 可用 `handoff_policy` 要求 Transfer Manifest，并选择 `required` 或 `risk-triggered` 语义抽查。
2. 子 Agent 在压缩或关闭上下文前写 `handoff_transfer_manifest`，为需要交接的事实、推断、限制、冲突、负结果、参数等建立稳定 ID，并固定来源工件哈希和定位符。
3. 接收端用 `handoff_transfer_audit` 把 Manifest 条目映射到 Handoff 的具体 JSON Pointer；确定性检查负责覆盖率、引用、分类区段、必需条目和负面区段。
4. 只有关键条目、特定风险类型或 Task 明确要求时，才阻断并要求独立人工语义抽查。低风险且未抽查的结果只能标为 `structurally-ready`，不得声称语义等价。
5. `Context Snapshot` 若记录 task scope 已压缩且 `handoff_ready: true`，必须引用 Transfer Audit；Execution Receipt 会重新评估该 Audit。
6. 不保存 Chain-of-Thought，不读取完整子 Agent 对话，不增加常驻 critic/reviewer Agent。

## 学科差异

通用内核只定义条目种类和审计机制。哪些参数、假设、反证、V&V 失败、实验偏差或推导边界必须进入 Manifest，由对应 Research Mode、Task 与领域 Skill 决定。不得把文献证据模式的检查表强加给实验、仿真或理论推导。

## 限制

- Manifest 仍由任务执行者声明，可能在源头遗漏重要项；领域 Skill、抽样和真实案例负责暴露这种遗漏。
- 结构映射和字符哈希不能证明改写语义一致。
- 人工抽查记录不是密码学签名，也不能推广为整体科研正确性。
- 若真实案例显示 Manifest 维护成本高于恢复收益，应缩减条目、降低触发范围或删除该机制。
