# M5 System-Level Evaluation Design Risk Ledger

| Risk ID | Type | Risk | Control | Status |
|---|---|---|---|---|
| M5-EVAL-EST-001 | authority | Skill 独立效果取代 system-level primary estimand，使局部收益被误写成 RWB 整体净收益。 | Primary estimand 固定为完整 RWB 相对 simpler Agent/Tool baseline；Skill effect 只作 secondary interpretation。 | controlled by Task definitions and R2 review |
| M5-EVAL-LEAK-001 | data boundary | treatment arm 读取 Private Adjudication Package，造成 oracle leakage。 | Public/Private package 分离、独立 hash freeze、arm read boundary 与 blind-first review。 | open until dossier contracts are implemented |
| M5-EVAL-ORACLE-001 | integrity | 观察输出后改写 oracle/case 或为特定 treatment 调参。 | 输出前冻结 case/oracle hash、Human approval、记录 selection rationale、禁止 post-result rewrite 与 treatment-specific tuning。 | open until M5-001/002 |
| M5-EVAL-METRIC-001 | interpretation | N/A/unavailable/estimated 被当成 measured zero，或单一加权分数掩盖科研完整性退化。 | 四态 measurement status、三层 decision hierarchy、Research Integrity non-compensation、禁止单一 weighted aggregate score。 | open until M5-006 |
| M5-EVAL-BLIND-001 | human review | arm/Skill/RWB 标签或成本先验污染 Human 质量判断。 | Blind phase 隐藏 identity/cost/token/label，质量评分完成后再 reveal exact execution facts。 | open until M5-006/007 |
| M5-EVAL-LIVE-001 | execution | synthetic Driver/projection 被误作 system-level 真实执行证据。 | M5-004 hard-depend M6-004 和 M11-006；A4 必须使用真实 accepted Release→Projection→Supply，confirmatory run 禁止 synthetic projection。 | blocked by explicit dependencies |
| M5-EVAL-HARNESS-001 | architecture | Harness 为 A4 建旁路、直接读 candidate 或接管 admission/promotion/Human decision。 | 所有 arm 走统一 Runtime Bundle/View/Host/Trace/Receipt；禁止 A4 bypass 与 automatic decisions。 | open until M5-007 |
| M5-EVAL-DRIFT-001 | comparability | Model/Provider/Host/context/budget 漂移破坏四臂可比性。 | M5-003 共享 frozen conditions + M5-006 drift/retry/stopping rules + M5-007 exact run records。 | bounded by protocol design |
| M5-EVAL-SUNK-001 | governance | 已投入开发成本导致默认 KEEP，或单次 A4 成功触发 promotion。 | M5-005 要求 evidence-linked disposition，并显式允许 PARK/DEPRECATE/DELETE/STOP。 | open until M5-005 |
| M5-EVAL-SCOPE-001 | scope | task-definition PR 偷跑 Evaluation、实现 runner、解冻 Topic 5 或宣称净收益。 | 当前 diff 仅定义 unfinished Tasks、派生导航、workstream 和风险；M5-003 DONE immutable。 | controlled by docs-only governance |
