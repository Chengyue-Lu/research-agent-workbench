# Review basis

https://github.com/Chengyue-Lu/research-agent-workbench/pull/60#pullrequestreview-5124757022

Task-owner technical re-review at exact HEAD `87d8dc497e6469d26f5849a3d3d2d0a7d1c377ea` — **changes requested conceptually**.

M14-002 的主体方向认可：frozen Git source、source/generated 二分类、manifest-last、external source/parent expectations、candidate exact-parent、complete tree equality、prospective merge-tree、v1→v2 stale-output removal、path/mode/byte/symlink/gitlink/casefold/Unicode/Windows adversarial coverage，以及 `merge_eligible: false` 均符合 ADR-0021 / M14-002 的核心边界。exact-head CI 当前也已全绿。

但在接受 `M14-002: PARKED -> DONE` 前还需要闭合两个 contract-level 问题。

### [P1] append-only policy 仍允许 retroactive version insertion

当前 `policy_at()` 只证明：当前版本列表 unique + increasing，且历史出现过的 version 仍存在且同 version 语义未改。它没有证明“新 version 只能追加在既有历史最大 version 之后”。因此例如：

```text
history: [1.0.0]
current: [0.9.0, 1.0.0]
```

或：

```text
history: [1.0.0, 2.0.0]
current: [1.0.0, 1.5.0, 2.0.0]
```

都可能通过现有检查，但这不符合冻结 acceptance 中的 strict append-only versioned allowlist。

请保持 merged-history 兼容，不要简单要求每个历史列表都必须是当前 prefix。建议对 source 可达历史求出曾经出现过的 immutable version identities；历史 identity 必须全部保留且内容不变，同时任何“当前首次引入”的 version 必须严格大于此前历史已出现的最大 version。

至少补两个 regression：

```text
history [1.0.0] -> current [0.9.0, 1.0.0]             => BLOCK
history [1.0.0, 2.0.0] -> current [1.0.0,1.5.0,2.0.0] => BLOCK
```

### [P1] required_checks 的逻辑语义无序，但 canonical manifest 仍受输入顺序影响

当前 prerequisite 通过：

```python
sorted(ci["required_checks"]) == REQUIRED_CHECKS
```

把 required checks 当作无序集合验证；但随后原始 `expected` 直接写入 manifest，所以 caller 只改变数组顺序就会生成不同 manifest/tree。

也就是说当前存在：

```text
validation semantics: order-insensitive
output semantics:     order-sensitive
```

这与 M14-002 的 canonical / stable ordering 目标不一致。

请二选一闭合：

1. 规定唯一 canonical input 顺序，直接要求 `ci["required_checks"] == REQUIRED_CHECKS`；或
2. 在生成 manifest / generated inputs 前规范化为 canonical REQUIRED_CHECKS 顺序。

并增加 permutation regression，证明仅调整 required-check 顺序不会产生第二个合法但不同的 release tree。

### Non-blocking follow-up

Issue #57 还要求 curated main 最终包含 release-only workflow / release checks；当前 surface policy 尚未包含 release workflow。这个可以继续留给 M14-005，但建议在后续 Task ownership 中明确，不作为本次 M14-002 blocker。

除上述两个 P1 外，我目前不要求重做 exporter、manifest、source/generated closure、prospective merge-tree、Windows path safety 或 dormant topology 设计。两项修复后可直接做 focused re-review。
