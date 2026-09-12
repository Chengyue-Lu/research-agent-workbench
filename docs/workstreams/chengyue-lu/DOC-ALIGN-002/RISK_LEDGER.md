# DOC-ALIGN-002 Risk Ledger

| ID | 类型 | 风险 | 控制与剩余决定 |
|---|---|---|---|
| DA2-TRUTH | fact | 派生文档沿用旧 candidate/READY，或把其他分支未提交状态当成 develop 真值。 | 以 frozen develop 的 canonical Task 行与 merged PR 为依据；TASKS 不变，M14 activation 由独立 lane 处理。 |
| DA2-EVIDENCE | fact | 文档维护覆盖负结果、旧 review 或冻结 Gate 的 exact bytes。 | 只更新 current-state 顶部；逐字节比较历史正文、frozen mapping 与 ADR0020 hash。 |
| DA2-MATURITY | inference | bounded M4/M11 完成被写成真实案例成功、科学质量、Skill 增益或可发布。 | 保留 synthetic/live/evaluated 边界、空 production index 与人类准入/评价/发行决定。 |
| DA2-FUTURE | inference | 将已定义的 M5-006/007 与 M6-008 acceptance 写成已存在 Schema/validator/Harness。 | 唯一 active Evaluation implementation 仍是 M5-003；明确后继工作和剩余 Gate。 |
| DA2-REVIEW | fact | 文字变更被误当成 R0，绕过决策路径的 R2 review。 | 按路径声明 R2；提供 authority basis 和反向范围检查，请求 cross-owner review，独立 owner 决定是否合入。 |
| DA2-CAPTURE | fact | Native session 的早期工具事件不能完整回填为实时 Trace。 | Archive 明示 delayed/capture-gap；保留可见委派记录和实际检查结果，不声称完整事件捕获。 |
| DA2-INTEGRATION | fact | M14-004 preparation 或未合并的 M5-006 分支被写成 develop 的完成状态，或文档清理被误加为集成前置。 | 按 canonical Task 行与各 PR 接受范围表述；PR #68 已提供文档基线，本次辅助说明清理不增加 PR #69 或任何 Task 的 hard dependency。 |
