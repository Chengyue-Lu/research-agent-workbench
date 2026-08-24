# M8-005 Decision Authority Matrix

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 跨负责人审查：黄毅（`let778750-cpu`）已在 PR #30 完成 R2 Code Owner review
- 已合并阶段分支：`agent/method-m8-action-resolution-node`
- 状态：DONE；已随 PR #30 合入 `develop@ead1270`

## 目标

冻结 provider-neutral 的 Decision Authority v1，并把 Agent proposal、deterministic resolver 与 Human
Gate 的 operation 规则映射到可重算 Authority Rule Eligibility。它只回答“假设 asserted facts 成立，
actor 是否匹配规则”；权限/数据边界放宽和 Claim promotion 的 Agent/Resolver commit 资格必须阻断。

## 写入与非目标

本节点只修改 authority Schema/Matrix、Method/Core protocol model、document validation、正反 fixture、
tests 与对应实现文档。不修改 Provider/API/Runtime、具体 Capability/Skill/Tool binding、Execution
Receipt/Trace，也不定义组织账户或通用 Supervisor。

## 停止条件

- 七类决定形成 exact v1 closed set；
- commit actor 与 required facts 不可静默放宽；
- Matrix raw hash、结果重算、缺 asserted fact、缺 Gate、越权 actor 与 cosmetic Gate 均有负例；
- eligible 不证明事实/Human approval，不授予 Permission、不提升 Claim、不执行决定；
- repository validation、focused/full tests、文档链接和差异检查通过。

实现契约见 [`DECISION_AUTHORITY.md`](../../../implementation/DECISION_AUTHORITY.md)，验证数字见
[`VALIDATION.md`](VALIDATION.md)。本节点不建立独立分支或 Handoff。
