# Phase B Evolution Gate

M9-006 的 Gate 是一份可机器重算的阶段证据，不是新的 Runtime 对象。正式 fixture 位于
[`phase-b-evolution-gate.yaml`](../../examples/capability-resolution/phase-b-evolution-gate.yaml)，其目标是把
“可替换、可重放、不得越权”从测试中的隐含断言提升为显式、hash-bound 的检查面。

## 固定链

Gate 固定同一条研究契约链：

```text
Task
  → Research Mode
  → Mode Actions
  → Method Resolution
  → Capability Requirement
  → Supply Report A → Resolution A → Snapshot A
  → Supply Report B → Resolution B → Snapshot B
```

Task、Mode、Action、Method 与 Requirement 均由 exact identity、repository path 和 raw-file SHA-256
固定。validator 会重查 Method→Task hash、selected Mode、完整 Action set/hash 与 Requirement lineage。
Snapshot A/B 必须保留同一 Method 和 Requirement，只允许 exact supply identity 改变。

## 替换不变量

当前 bounded fixture 将本地 Tool A 替换为 Adapter/Provider B，并要求：

- selected Supply Report 与 frozen supply identity 确实不同；
- `effective_permissions` 完全相同；
- `data_egress` 完全相同；
- `side_effects` 完全相同；
- Snapshot 继续声明无 Method、permission、Claim、Human Decision 或 fallback authority。

这里采用“边界完全相同”作为首版 Gate，比仅判断“不放宽”更保守。以后若需要合法收紧，必须新增
Gate 版本与可解释的偏序规则，不能静默改变本 fixture。

## Migration replay

Gate 同时固定并调用现有两类迁移证据：

- Research Mode v0.1→v0.2 migration；
- accepted Skill Registry→lifecycle v2 migration。

两者仍由各自 validator 重放。Gate 只证明 exact migration record 被加载、身份/hash 未漂移且两类
coverage 都存在；它不建设通用 migration engine，也不迁移 Method Resolution、Assignment、Receipt 或
Trace。Research Mode 的 Action append-stability 与 lifecycle migration 的 accepted-entry append-stability
分别由原有对抗测试继续证明。

## 结论边界

`verification_status = deterministic-pass` 只表示仓库内契约闭合与合成替换成立。Schema 强制以下结论为
false：Runtime 获得 Method authority、automatic fallback、Claim/Gate effect、真实执行已经发生、live
Provider conformance 已证明、Skill 科研净收益已证明。

因此 M9-006 可以作为 Phase B 的结构性 Stop Gate，但不能替代 CI、跨负责人 R2 审查、Human Decision、
Phase D evaluation 或真实 Runtime integration。
