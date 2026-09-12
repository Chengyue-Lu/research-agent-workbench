# M12 / M13 启动审查

- Audit ID：`AUDIT-M12-M13-ENTRY-001`；风险：R2；类型：文档审计与后续定义输入。
- 责任人：黄毅（`let778750-cpu`），负责执行 consumer 与事实接口准备。
- 语义审查归属：路诚钺（`Chengyue-Lu`），负责 State/Method/Failure 及策略、Need、Evaluation/Admission 语义。此处说明责任，不填充其尚未作出的决定。
- 接受基线：`develop@ab98caf25125e6567d8bb2c8afff02105b54c940`；日期：2026-09-12。
- 授权：黄毅要求先复审最新 PR 修改，随后推进 M12/M13；本次把此前本地分析转为可共同审查的仓库输入。
- 状态：**审查输入已准备；Phase C 具名语义收口、M12/M13 激活与 feature implementation 均未因此接受。**

## 1. 具体问题与交付

现有 `recovery-check` 能预检 legacy safe-paused 文件，但没有当前 M11 consumer 使用该结果创建并继续新 Attempt。首个 M12 候选应交付 action 已闭合之后的实际文件式接续，而非继续扩充预检规则。

M13 已有反馈改进需求，但当前材料没有真实重复模型行为的稳定样本。M7/M9 已覆盖 Need、Evaluation、Admission、Lifecycle 与 Release，必须先定位策略职责缺口，不能再造同一条演化链。

本 PR 只提交以下可审查结果：

- [Phase C 两案语义审查表](PHASE_C_REVIEW.md)：已填事实解释与待决定问题，供具名 owner 判断最小表示。
- [M12/M13 后续工作边界](ENTRY_PLAN.md)：首个 consumer、依赖、候选比较、输出与停止条件。
- [来源与验证](EVIDENCE.md)：固定基线、可访问的原始输入及本次检查范围。
- [风险记录](RISK_LEDGER.md)：区分人类决定、研究意义、执行事实和机制收益。

## 2. 审查应形成什么结果

| 决定 | 当前状态 | 有效结果 |
|---|---|---|
| Phase C 最小表示的语义接受 | PENDING | 路诚钺对精确输入、适用范围、保留项和必要修正作具名决定；黄毅复核实际执行事实接口 |
| M12 Topic 5 架构/任务定义 | PROPOSAL | Phase C 收口后，独立接受一个 action 边界接续 Task；明确 no-Skill consumer 和 Handoff 兼容方式 |
| M13 独立 implementation family 的必要性 | UNPROVEN | 真实失败/反馈与现有 Protocol/M7/M9 的复用判断，支持复用、窄新 family 或暂缓任一种结果 |

合并本审查输入本身不改变以上状态。具名 review 要说明接受的是“材料足以审查”、具体语义还是后续任务定义；普通 APPROVE 或文档 CI 不隐式同时完成三项决定。实际语义决定应以单独、可定位的记录收口，不能改写历史机器报告。

## 3. 与当前主线的关系

M4-001～004 已 DONE。PR70 已接受合入，提供当前 CI 优化基线。PR71 的 M5-006 修复已被复审认可，但截至本文件基线尚未合并；M6-008、Skill replay、Harness、真实 case/live/admission 保持其既有条件。PR69 的 M14-004 是准备范围，未因此完成最终 scaffold/Quickstart 验收。

本变更不修改 [TASKS](../../../TASKS.md)、[ROADMAP](../../../ROADMAP.md)、Schema、Registry、CLI 或产品实现；不为 M12/M13 分配原子 Task ID。准备工作可以并行，实际 feature 仍消费其准确依赖。M12/M13 不成为 M5 的新增前置，no-Skill 接续也不等待 Skill admission 或 M14 发行。

## 4. 下一交付

1. 对 [Phase C 审查表](PHASE_C_REVIEW.md)形成真实具名语义决定，并依据接受范围更新既有 Gate 说明；原 DONE Task 与历史报告保持原义。
2. 将 M12 单条接续候选转成独立 ADR/task-definition；接受后由黄毅实现，路诚钺审 State/Method 语义。
3. 在正常计算/仿真使用中收集 M13 首个实际纠正及后续重复情况。先明确归因和承载处，再冻结 direct 与一个窄候选的独立比较任务。

工作记录：[本次文档准备记录](../../../../work/AUDIT-M12-M13-ENTRY-001/A-20260912-001/WORKLOG.md)。该记录不声称完整平台 Trace、实时恢复或科学结果。
