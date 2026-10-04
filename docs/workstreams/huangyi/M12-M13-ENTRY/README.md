# M12 / M13 启动审查

- Audit ID：`AUDIT-M12-M13-ENTRY-001`；风险：R2；类型：文档审计与后续定义输入。
- 责任人：黄毅（`let778750-cpu`），负责执行 consumer 与事实接口准备。
- 语义审查归属：路诚钺（`Chengyue-Lu`），负责 State/Method/Failure 及策略、Need、Evaluation/Admission 语义。此处说明责任，不填充其尚未作出的决定。
- 原始审查输入基线：`develop@ab98caf25125e6567d8bb2c8afff02105b54c940`（2026-09-12）；原 PR72 最终集成基线：`develop@451644064f558601d5778b9b115390f882f4d260`（2026-09-13）；本次重新核对基线：`develop@6fa105b720254fae82d2e889385c89292272b2d7`（2026-10-04）。
- 原授权：黄毅要求先复审最新 PR 修改，随后准备 M12/M13 输入。2026-10-04 当前授权只推进 M12 的具名收口输入、独立架构/任务定义候选与必要文档修正；M13 旧提案保留为历史导航，本轮不启动其采集、研究、任务定义或实现。
- 状态：**审查输入已准备；Phase C 具名语义收口、M12/M13 激活与 feature implementation 均未因此接受。**

## 1. 具体问题与交付

现有 `recovery-check` 能预检 legacy safe-paused 文件，但没有当前 M11 consumer 使用该结果创建并继续新 Attempt。首个 M12 候选应交付 action 已闭合之后的实际文件式接续，而非继续扩充预检规则。

M13 已有反馈改进需求，但当前材料没有真实重复模型行为的稳定样本。M7/M9 已覆盖 Need、Evaluation、Admission、Lifecycle 与 Release，必须先定位策略职责缺口，不能再造同一条演化链。

本入口保留 PR72 的以下可审查结果，并向当前 M12 候选提供导航：

- [Phase C 两案语义审查表](PHASE_C_REVIEW.md)：已填事实解释与待决定问题，供具名 owner 判断最小表示。
- [M12/M13 后续工作边界](ENTRY_PLAN.md)：首个 consumer、依赖、候选比较、输出与停止条件。
- [来源与验证](EVIDENCE.md)：固定基线、可访问的原始输入及本次检查范围。
- [风险记录](RISK_LEDGER.md)：区分人类决定、研究意义、执行事实和机制收益。

## 2. 审查应形成什么结果

| 决定 | 当前状态 | 有效结果 |
|---|---|---|
| Phase C 最小表示的语义接受 | PENDING | 路诚钺对精确输入、适用范围、保留项和必要修正作具名决定；黄毅复核实际执行事实接口 |
| M12 Topic 5 架构/任务定义 | PROPOSAL | Phase C 收口后，独立接受一个 action 边界接续 Task；明确 no-Skill consumer 和 Handoff 兼容方式 |
| M13 独立 implementation family 的必要性 | UNPROVEN | 获准本地记录支持归因与复用判断；正式激活另需 Phase C semantic closeout、所需 Phase D evidence、既有 M-group 无法自然承载 coherent family 的证据，再接受独立 docs-only R2 task-definition |

PR72 的 exact-head `7a9a0b2ac073354537db260896649f1048d778f7` 复审已明确关闭 M13 activation 文案的 P1 及三项澄清，接受范围是 bounded documentation review；该 review 仍明确保留 Phase C Human/R2 pending、M12/M13 reserved。合并或迁移本审查输入本身不改变以上状态。具名 review 要说明接受的是“材料足以审查”、具体语义还是后续任务定义；普通 APPROVE 或文档 CI 不隐式同时完成三项决定。实际语义决定应以单独、可定位的记录收口，不能改写历史机器报告。

## 3. 与当前主线的关系

在本次 exact 基线，canonical [TASKS](../../../TASKS.md) 的 M4-001～004、M5-006/007、M6-008、M11-001～007、M14-001～005 均为 DONE。[STATUS](../../../STATUS.md)区分已实现的 bounded synthetic Harness 与仍受独立 live/case/admission 条件约束的 M5-008/M5-004；M14 已完成首个 curated release。原 PR70/71/74/69/77 的状态与历史验证留在原审计记录中，不再用当时的 M6-008 PARKED 或 M14-004 待审描述当前施工入口。上述完成项不替代 Phase C Human/R2 或 Topic 5 独立接受。

本次只迁移并修正文档输入，不修改 [TASKS](../../../TASKS.md)、[ROADMAP](../../../ROADMAP.md)、Schema、Registry、CLI 或产品实现，不为 M12/M13 分配原子 Task ID。M12 继续为 RESERVED，Topic 5 继续冻结；当前候选位于独立[有界连续性工作流](../../chengyue-lu/M12-BOUNDED-CONTINUITY/README.md)。M6、M5 等线由其 owner 独立推进。M12/M13 不成为 M5 的新增前置，no-Skill 接续也不等待 Skill admission 或下一次 M14 发行。

## 4. 下一交付

1. 对 [Phase C 审查表](PHASE_C_REVIEW.md)及本次[具名收口候选](../../chengyue-lu/PHASE-C-RESEARCH-STATE/CLOSEOUT_CANDIDATE.md)形成真实语义决定，随后才按其接受范围收口既有 Gate；原 DONE Task 与历史报告保持原义。
2. 审查 M12 的[独立 ADR 候选](../../chengyue-lu/M12-BOUNDED-CONTINUITY/ADR_CANDIDATE.md)与[首个任务定义候选](../../chengyue-lu/M12-BOUNDED-CONTINUITY/TASK_DEFINITION_CANDIDATE.md)，在真实 Phase C 与独立 Topic 5 R2 接受闭合后才实施下一 frozen action 的 fresh-process 接续。
3. M13 仅保留 [ENTRY_PLAN](ENTRY_PLAN.md) 的历史归因建议与 canonical reservation 导航；本轮 M12 接手不扩展其授权。

原审计记录：[2026-09 文档准备记录](../../../../work/AUDIT-M12-M13-ENTRY-001/A-20260912-001/WORKLOG.md)；本次核对与候选检查见[当前 M12 证据](../../chengyue-lu/M12-BOUNDED-CONTINUITY/EVIDENCE.md)。两者均不声称完整平台 Trace、实时恢复或科学结果。
