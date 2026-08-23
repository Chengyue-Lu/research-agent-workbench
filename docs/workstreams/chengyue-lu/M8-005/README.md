# M8-005 Decision Authority Matrix

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 跨负责人审查：统一 M8 阶段 PR #30 的 R2 Code Owner review
- 阶段分支：`agent/method-m8-action-resolution-node`
- 状态：implementation complete；共享 `docs/TASKS.md` 状态不在本 PR 中越级改写

## 目标

冻结 provider-neutral 的 Decision Authority v1，并把 Agent proposal、deterministic resolver 与 Human
Gate 的 operation 权威映射到可重算 preflight。权限/数据边界放宽和 Claim promotion 必须阻断 Agent
或 Resolver commit。

## 写入与非目标

本节点只修改 authority Schema/Matrix、Method/Core protocol model、document validation、正反 fixture、
tests 与对应实现文档。不修改 Provider/API/Runtime、具体 Capability/Skill/Tool binding、Execution
Receipt/Trace，也不定义组织账户或通用 Supervisor。

## 停止条件

- 七类决定形成 exact v1 closed set；
- commit actor 与 required facts 不可静默放宽；
- Matrix raw hash、结果重算、缺事实、缺 Gate、越权 actor 与 cosmetic Gate 均有负例；
- repository validation、focused/full tests、文档链接和差异检查通过。

实现契约见 [`DECISION_AUTHORITY.md`](../../../implementation/DECISION_AUTHORITY.md)，验证数字见
[`VALIDATION.md`](VALIDATION.md)。本节点不建立独立分支或 Handoff。
