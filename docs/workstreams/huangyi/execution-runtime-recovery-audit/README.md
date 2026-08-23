# Execution–Runtime–Recovery 恢复开发审计

- 责任人：黄毅（GitHub 主名 `let778750-cpu`；昵称/界面名 `huangyi855`，二者为同一账户）
- 必需审查人：路诚钺（GitHub `Chengyue-Lu`）
- 审计 ID：`AUDIT-EXEC-RUNTIME-001`
- 状态：审计与采纳提案；不是 Stable Architecture、TASKS 状态或已批准 ADR
- 目标 base：`develop`
- 工作分支：`codex/execution-runtime-recovery-audit`
- 证据截止：2026-08-23（Asia/Shanghai）
- accepted baseline：`main@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- integration baseline：`develop@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- PR #23 审计范围：`b1d5a5a5850e0e7541e4c460f15384cd45357ab2..57b3d24a8383ec3618dd29b4d5c52ee7ff9fcbef`

## 1. 术语消歧

本审计中的“4/5”只来自个人架构导航，分别表示：

- Agent / Model / Provider / Runtime；
- Execution / Context / Handoff / Recovery。

它不表示 [`TASKS.md`](../../../TASKS.md) 的 M4/M5，也不表示模块文档 04/05。以下统一使用
`execution-runtime-recovery`。

## 2. 目标与权威边界

本工作流恢复并核验既有风险分析，把内容分为：已接受不变量、`main` 实现缺口、PR #23
分支特有缺陷、未来集成风险和待人类批准的恢复 Gate。

证据按问题类型解释：

1. `main@SHA` 的 Stable docs/ADR 决定规范语义，`TASKS.md` 决定实时状态，代码与测试决定实际行为；
2. PR diff 只证明候选分支行为；
3. 会议纪要是待确认的决策来源；
4. ChatGPT Share 只证明匿名 `user` 的意图和 GPT 建议；
5. 黄毅个人稿是 derived working paper。

规范与实现不一致时登记 implementation gap，不让任何一侧静默覆盖另一侧。

写入范围仅限本 workstream、workstream/history 入口、开发治理文档、PR 模板/CODEOWNERS、
治理 CI 与对应测试；不修改 Runtime 实现、Schema、ADR、STATUS、ROADMAP 或 TASKS。允许读取
固定的 main/develop/PR #23 blobs 及私有来源，但私有原文不进入工作分支。

## 3. Architecture Hold 的提案边界

本工作流将 Hold 缩窄为 **feature expansion / execution reintegration hold**。

保持开放：M8-002/M8-003、安全修复、负面测试、Trace、redaction、hash/ref、archive、
file-only verification 和只读外部机制调查。

暂缓：新 Runtime、自动 Router/fallback、多 Agent/critic、隐藏会话状态、复杂 salvage recovery、
streaming/multimodal/server-tool 扩张，以及继续加深 Skill-bound execution。

该提案只有在双方维护者审查并按需进入 ADR/TASKS 后才具有正式项目约束力；它不重排
[`TASKS.md`](../../../TASKS.md) 已确定的 M8-002 → M8-003 主线。

## 4. PR #23 当前合并结论

PR #23 继续作为 branch-only 反例保存，不得整体 merge、rebase-merge 或批量 cherry-pick 到
`develop`/`main`。已证实的硬阻断包括：

- 本地 Tool Result 缺少逐数据出口授权却进入后续 Provider 请求；
- 完整 request/response 与本地正文进入第二套 transcript，未接入 M3-008 Trace；
- 未执行敏感扫描却固定声明未发现敏感数据、未做 redaction；
- effective permission、allowed roots、Task write scope 与实际输出目录未形成完整前置约束；
- 模型自由文本 summary 被自动写成 Handoff fact；
- Receipt 未结构化保存实际 observed model；
- `--from-state` 只完成输入 hash pin，却被描述成恢复能力；
- 分支修改 M6-003/M6-004 的任务状态和验收边界。

base-state pin、原子 closeout、file-only verify 和输入 provenance 只能作为洁净重写参考。

## 5. 输出导航

- [来源清单](SOURCE_MANIFEST.md)：固定来源、哈希、获取边界和限制；
- [主张台账](CLAIM_LEDGER.md)：区分 fact/inference/proposal，记录证据和处置；
- [采纳决定](ADOPTION.md)：记录 `SATISFIED / ADOPT / ADAPT / DEFER / REJECT`；
- [恢复 Gate 草案](RECOVERY_GATE_PROPOSAL.md)：保存恢复不变量、Gate 和对抗测试，不自动改变任务状态。
- [GitHub 治理 rollout](GITHUB_GOVERNANCE_ROLLOUT.md)：区分仓库内已实现门禁与仍需 Admin 完成的远端状态。

## 6. 非目标与完成条件

本工作流不复制原始会议、聊天或 1640 行个人稿；不选择 Runtime；不实现 K-API-2、salvage
recovery、Router 或 fallback；不把 GPT 回复升级为架构决定。

完成条件：

- 每条 claim 都有类型、scope、固定证据、限定和 disposition；
- 所有 PR #23 事实均标为 branch-only；
- 私有来源只提交逻辑定位、最小脱敏摘要和哈希，不含机器绝对路径；
- 两位维护者完成审查；
- 文档链接、治理检查和仓库测试通过；
- 后续需要修改 ADR/TASKS/Schema 的内容进入独立、具名 Task，不在本审计中偷渡。

合并到 `main` 后才创建 `docs/history/` closeout；此前没有完成历史入口，也不把待审查内容描述为
已发布结论。
