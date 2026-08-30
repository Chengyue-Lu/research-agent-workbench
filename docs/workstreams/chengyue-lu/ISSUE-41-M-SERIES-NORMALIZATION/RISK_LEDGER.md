# Issue #41 M-series normalization 风险台账

| ID | 类型 | 风险 | 控制 | 状态 |
|---|---|---|---|---|
| MSN-STALE-001 | fact | 审计期间 `develop` 新增已合并 Task/状态，使 normalization 基线过时。 | 固定并注明审计 SHA；最终 diff 前重新同步 develop，只接受已合并状态，重跑全量 inventory；未合并 PR/branch 完全排除。 | controlled at PR #42 closeout; snapshot label retained |
| MSN-HISTORY-001 | fact | 为整齐而重编号、删除或改写历史 Task，破坏 PR/ADR/fixture 引用。 | 已发布 Task ID 保留；只用 refine/split/supersede lineage；DONE 定义不可变。 | controlled by accepted rule and R2 review |
| MSN-STATE-001 | fact | READY/BLOCKED/PARKED/IN_PROGRESS 继续表达愿望或历史债务，而非严格状态。 | 已逐项修正 M3、M4、M5、M6 与 M10；后续状态只由 TASKS 维护并持续校核。 | controlled at normalization closeout; recurring drift remains auditable |
| MSN-UMBRELLA-001 | inference | M3/M6 umbrella 拆分时顺手重设 Runtime、Recovery 或 Method authority。 | Task 拆分只描述实施契约；涉及 authority 变化立即 STOP 并转独立 R2 architecture decision。 | retained stop condition |
| MSN-TOPIC5-001 | fact | 把 Phase C prerequisites 或使用 Trace/Receipt 的 M11 thin execution 计入 Topic 5，造成 membership/freeze 歧义与事实解冻。 | M10-001/002、M3-009、M10-003 只作为 activation prerequisites；membership 只按 Handoff/context/safe-pause/recovery/continuation objective 判定；M11-003/004 属于 Topic 4/Artifact-Trace；M12 只作 reservation。 | controlled by explicit ceiling |
| MSN-INFLATION-001 | inference | 把每个 Research State 概念或架构名词机械变成 Task，导致 Task DAG 失去可执行性。 | 只新增六个已有 accepted producer/consumer surface；字段、Provider、State 概念和纯 closeout 不单独建 Task。 | controlled by accepted bounded inventory |
| MSN-DUPLICATE-001 | fact | 跨 Topic 工作被复制为多个语义重复 Task。 | 一个 canonical Task 可列多个 Topic；M3-009 与 M11-004 等跨域 Task 均保持单一 identity。 | controlled by accepted identity map |
| MSN-OWNER-001 | fact | workstream/Phase/Topic 名称替代具名 owner，跨 owner contract 无审查责任。 | 每个 active-path Task 明确 owner/risk/topics；共享接口保留 cross-owner review。 | controlled by R2 owner audit and TASKS rows |
| MSN-DUALTRUTH-001 | fact | ROADMAP 与 TASKS 同时充当实施队列，Agent 继续自行推导 scope。 | TASKS 控制 Task status/dependency/scheduling；ROADMAP 只聚合 Phase/Topic/Gate，DEVELOPMENT 明确无 Task 即 STOP。 | controlled by accepted surface discipline |
| MSN-TOPIC-LABEL-001 | fact | 当前 develop 只正式给出 Topic 4/5 的数字名称；擅自命名 Topic 1～3/6/7 会借 normalization 改写 ownership。 | 对其余稳定责任域使用 accepted architecture 名称，不新增数字标签；未来若需数字化，另走 architecture decision。 | controlled by explicit non-goal |
| MSN-MIXEDPR-001 | fact | task-definition PR 同时实现代码或把新 Task 直接置 DONE。 | 分支写入面限 docs；PR class 固定 task-definition；新/调整 Task 保持未完成状态。 | controlled by branch scope |
| MSN-OVERCLAIM-001 | fact | normalization matrix 被误解为 architecture acceptance。 | matrix 在 R2 review/merge 前标 proposal；不改变 Method/Capability/Claim/Human/Runtime authority。 | controlled by labeling |
| MSN-ATOMIC-001 | fact | 把 module-level PR 误解为合并 Task identity，或仅因风险同为 R2 就把断连/未验收 Task 偷渡进同一 PR。 | 通用规则要求预定义 Task、READY 入口、base-DONE 外部依赖、入口可达 DAG、独立 slice/commit/evidence、最高风险与相关 owner review；治理负例阻断断连 completion。 | controlled by canonical module-level rule and governance tests |
| MSN-SKILL-SEAM-001 | fact | M11-006 由 Runtime owner 建成 Skill-specific dispatcher/session/fallback seam，破坏 unified View/Capability semantics。 | M11-006 归 View/Capability semantic owner；所有 supply kind 使用同一 Report→Resolution→Snapshot→View 路径，Host 无 Skill 特例。 | controlled by owner and negative acceptance |
| MSN-M6-LIVE-001 | fact | 把 Provider/session live conformance 错误绑定到 M11-004，使独立适配器验证被 Runtime E2E 不必要阻塞。 | M6-004 只 hard-depend M6-001/002，并由 live authorization 解阻；明确不等于 M11 Core E2E。 | controlled by corrected DAG |
| MSN-RESERVATION-001 | fact | 把 future M-group reservation 当成 READY/PARKED Task、architecture acceptance 或 implementation approval。 | Reservation 无状态、无原子 ID、无 owner/dependency/acceptance/Schema；必须经 activation Gate、旧 group 不足证据与独立 task-definition 才激活。 | controlled by explicit reservation contract |
| MSN-NAMESPACE-001 | inference | 过早冻结 M12+ 细节或继续推测 M15+，造成 namespace lock-in 与 task inflation。 | 只预留 accepted roadmap 可预见的 M12/M13/M14 family；不展开原子 Task，允许旧 group 足够时取消 reservation。 | controlled by bounded reservation set |
| MSN-MAP-DRIFT-001 | fact | Architecture Map、Construction Map 与 TASKS 变成三套实施真值。 | Architecture Map 只管 Phase/Topic/authority/Gate；Construction Map 只作 M-series 导航并明确由 TASKS 派生；Task 状态与 exact dependency 只在 TASKS。 | controlled by authority labels and navigation |
