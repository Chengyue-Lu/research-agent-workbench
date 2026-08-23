# M8-003 验证证据

状态：stacked branch 实现、验证、远端同步与节点 handoff 已收束；等待节点级审查，未合并。

M8-002 `def0689` 的 canonical Claim strength、Claim effect、opaque Gate、metadata rejection 与 published
Action identity hardening 已传播到本分支；Action 原始 YAML 未改变，因此 Resolution 中固定的 Action
content hashes 无需重写。传播后的完整 suite 已重新执行：`289` passed、`3` skipped；repository
validation 仍为 `84` valid、`0` errors、`0` warnings，`git diff --check` 通过。

当前已验证：

- 八个 Method Resolution 均符合 `method_resolution` Schema；
- 八个 routing case 与 Resolution path/hash 构成一一映射；
- Task、Mode、Action/planning action、Capability、Skill Need、Human Gate、status 与 forbidden route
  从诊断输入无损映射；
- Action ref 固定 Registry hash；Need/Gate/block 三组集合闭合；
- Schema 阻断隐式 Assignment、formal/planning selector 混用与 provider/runtime 字段；
- `33` 个 focused contract/routing/documentation tests 通过；
- 初始节点完整 suite：`283` tests passed，`3` Hypothesis tests skipped；传播 hardening 后为
  `289` passed，`3` skipped；
- `rwb validate examples registry`：`84` valid，`0` errors，`0` warnings。

已覆盖 duplicate identity/decision/obligation/alternative、Action hash drift、Need/Gate/block closure drift、
implicit Assignment/provider field 与 formal/planning selector 混用负面测试。

分支 ancestry、远端同步与 Draft PR 状态已在节点收束时复核。审查范围和后续合并顺序见
[M8-002 → M8-003 节点交接](HANDOFF.md)。
