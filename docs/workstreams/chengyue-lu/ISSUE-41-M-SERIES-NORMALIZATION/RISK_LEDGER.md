# Issue #41 M-series normalization 风险台账

| ID | 类型 | 风险 | 控制 | 状态 |
|---|---|---|---|---|
| MSN-STALE-001 | fact | 审计期间 `develop` 新增已合并 Task/状态，使 normalization 基线过时。 | 固定并注明审计 SHA；最终 diff 前重新同步 develop，只接受已合并状态，重跑全量 inventory；未合并 PR/branch 完全排除。 | active |
| MSN-HISTORY-001 | fact | 为整齐而重编号、删除或改写历史 Task，破坏 PR/ADR/fixture 引用。 | 已发布 Task ID 保留；只用 refine/split/supersede lineage；DONE 定义不可变。 | controlled by rule; audit pending |
| MSN-STATE-001 | fact | READY/BLOCKED/PARKED/IN_PROGRESS 继续表达愿望或历史债务，而非严格状态。 | 已逐项修正 M3、M4、M5、M6 与 M10；最终 R2 review/CI 继续检查。 | proposed control |
| MSN-UMBRELLA-001 | inference | M3/M6 umbrella 拆分时顺手重设 Runtime、Recovery 或 Method authority。 | Task 拆分只描述实施契约；涉及 authority 变化立即 STOP 并转独立 R2 architecture decision。 | active stop condition |
| MSN-TOPIC5-001 | fact | 为补齐 future Task 而把 Topic 5 recovery 工作置 READY/BLOCKED，造成事实解冻。 | future Topic 5 Task 只能 PARKED，且必须声明 Phase C closeout与后续 task-definition/R2 Gate。 | controlled by explicit ceiling |
| MSN-INFLATION-001 | inference | 把每个 Research State 概念或架构名词机械变成 Task，导致 Task DAG 失去可执行性。 | 只新增六个已有 accepted producer/consumer surface；字段、Provider、State 概念和纯 closeout 不单独建 Task。 | proposed control |
| MSN-DUPLICATE-001 | fact | 跨 Topic 工作被复制为多个语义重复 Task。 | 一个 canonical Task 可列多个 Topic；M3-009 与 M11-004 等跨域 Task 均保持单一 identity。 | proposed control |
| MSN-OWNER-001 | fact | workstream/Phase/Topic 名称替代具名 owner，跨 owner contract 无审查责任。 | 每个 active-path Task 明确 owner/risk/topics；共享接口保留 cross-owner review。 | audit pending |
| MSN-DUALTRUTH-001 | fact | ROADMAP 与 TASKS 同时充当实施队列，Agent 继续自行推导 scope。 | TASKS 控制 Task status/dependency/scheduling；ROADMAP 只聚合 Phase/Topic/Gate，DEVELOPMENT 明确无 Task 即 STOP。 | proposed control |
| MSN-TOPIC-LABEL-001 | fact | 当前 develop 只正式给出 Topic 4/5 的数字名称；擅自命名 Topic 1～3/6/7 会借 normalization 改写 ownership。 | 对其余稳定责任域使用 accepted architecture 名称，不新增数字标签；未来若需数字化，另走 architecture decision。 | controlled by explicit non-goal |
| MSN-MIXEDPR-001 | fact | task-definition PR 同时实现代码或把新 Task 直接置 DONE。 | 分支写入面限 docs；PR class 固定 task-definition；新/调整 Task 保持未完成状态。 | controlled by branch scope |
| MSN-OVERCLAIM-001 | fact | normalization matrix 被误解为 architecture acceptance。 | matrix 在 R2 review/merge 前标 proposal；不改变 Method/Capability/Claim/Human/Runtime authority。 | controlled by labeling |
