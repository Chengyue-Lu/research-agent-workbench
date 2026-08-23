# M8-003 验证证据

状态：stacked branch 本地证据；远端分支与节点 handoff 尚未收束。

当前已验证：

- 八个 Method Resolution 均符合 `method_resolution` Schema；
- 八个 routing case 与 Resolution path/hash 构成一一映射；
- Task、Mode、Action/planning action、Capability、Skill Need、Human Gate、status 与 forbidden route
  从诊断输入无损映射；
- Action ref 固定 Registry hash；Need/Gate/block 三组集合闭合；
- Schema 阻断隐式 Assignment、formal/planning selector 混用与 provider/runtime 字段；
- `33` 个 focused contract/routing/documentation tests 通过；
- 完整 suite：`283` tests passed，`3` Hypothesis tests skipped；
- `rwb validate examples registry`：`84` valid，`0` errors，`0` warnings。

已覆盖 duplicate identity/decision/obligation/alternative、Action hash drift、Need/Gate/block closure drift、
implicit Assignment/provider field 与 formal/planning selector 混用负面测试。

节点收束前还需：最终 diff/link 检查、远端分支 ancestry 验证，以及不触发正式 review 的 compact handoff。
