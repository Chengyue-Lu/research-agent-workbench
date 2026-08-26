# Durable Research State Composition Candidate (M10-001)

状态：Bounded implementation candidate；最终表示待 Human/R2 接受

更新：2026-08-26

## 1. 单层范围

本契约只实现 Phase C 依赖链入口 M10-001。Research Failure/Attempt（M10-002）、Method Trace
（M3-009）与 continuity/fresh-actor Gate（M10-003）不在本 PR，状态保持 BLOCKED。

Research State 是 revisioned composition：`entries` 引用现有 Question/Hypothesis/Evidence/Claim/
Decision/Run/Task，`open_items` 以轻量 `unknown / assumption` 表达尚未闭合项。Contradiction 继续
复用既有 Evidence–Claim counterevidence relation；Frontier 只由 current entries/open items 派生，
不新增对象。

## 2. Human Decision 表示

本层不创建 `human-decision-record`。具名 Human Decision 直接复用 kernel `decision` research object
的 actor/timestamp/reason_refs，并可在 metadata 记录 authority basis。State 以 role `decision` 引用它；
role/type closure 要求目标确为 `object_type: decision`。这是一项最小复用假设，不扩张 Decision authority。

## 3. Exact closure

`ClosureIndex` 只消费调用者显式提供的 bounded document set，并 fail closed：

- 所有 ref 必须包含 revision；
- 同一 `identity@revision` 出现多次即为 ambiguous，既报告 closure duplicate，也拒绝解析；
- ref 携带 `sha256` 时，target 必须声明可验证 `content_hash` 且值一致；
- State entry role 必须与 target semantic type 匹配；
- `current` entry 不能落后于 closure 中同 identity 的最新 revision；
- supersedes 必须同 lineage、严格早于当前 revision、且目标是 Research State；
- resolved/invalidated open item 必须有可解析 provenance refs。

`rwb research-state validate <state> --closure <path>...` 要求显式 closure 路径，不扫描仓库或猜测
convention filename。

## 4. 证据边界

两个 synthetic bounded case 分别覆盖 Evidence/Claim/Human Decision 闭合与 negative Evidence 导致
Assumption invalidation。它们只证明 Schema、identity、revision、pin、role/type 与 lineage 的确定性
性质，不证明科学判断、reviewer reconstruction、最终 State 表示或 Topic 5 解冻。
