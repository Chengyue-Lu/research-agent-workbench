# M8-003 验证证据

状态：统一节点分支已接入 Governance v2 基线并完成本地验证；等待 R2 节点审查，未合并。

M8-002 `def0689` 的 canonical Claim strength、Claim effect、opaque Gate、metadata rejection 与 published
Action identity hardening 已传播到本分支；Action 原始 YAML 未改变，因此 Resolution 中固定的 Action
content hashes 无需重写。接入 `develop@51c8607` 后的完整 suite 已重新执行：`298` passed、`3`
skipped；repository validation 为 `84` valid、`0` errors、`0` warnings，工作树 diff check 通过。
Governance v2 synthetic PR preflight 推导 effective risk 为 R2，验证两个 Task 状态转换、owner-matched
workstream/Risk Ledger、authority basis 与 adversarial evidence 后 PASS。

当前已验证：

- 八个 Method Resolution 均符合 `method_resolution` Schema；
- 八个 routing case 与 Resolution path/hash 构成一一映射；
- Task、Mode、Action/planning action、Capability、Skill Need、Human Gate、status 与 forbidden route
  从诊断输入无损映射；
- Action ref 固定 Registry hash；Need/Gate/block 三组集合闭合；
- Schema 阻断隐式 Assignment、formal/planning selector 混用与 provider/runtime 字段；
- `79` 个 contracts/schemas/Action/Resolution/routing/documentation/governance focused tests 通过；
- 初始节点完整 suite：`283` tests passed，`3` Hypothesis tests skipped；传播 hardening 后为
  `289` passed，`3` skipped；
- `rwb validate examples registry`：`84` valid，`0` errors，`0` warnings。

已覆盖 duplicate identity/decision/obligation/alternative、Action hash drift、Need/Gate/block closure drift、
implicit Assignment/provider field 与 formal/planning selector 混用负面测试。

原两条 M8 分支提交已在 `agent/method-m8-action-resolution-node` 形成可验证的合流历史；PR #26
撤回、旧分支删除后仍由祖先关系保留证据，不再作为交付入口。审查范围和后续合并顺序见
[M8-002 → M8-003 节点交接](HANDOFF.md)。
