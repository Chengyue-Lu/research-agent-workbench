# M5-007 整项收口候选

最终结果：PR122 已按用户明确的直接接受/不等待审核指示合入 `develop@b033c05`，
M5-007 DONE、Issue55 completed；[完成回执](M5-007_CLOSEOUT_RECEIPT.md)保存 actual merge、验证和决定。
下文保留 PR122 创建时的候选记录，原 Attempt 与其 pending 观察不改写。

日期：2026-10-02。Task / Evaluation owner：路诚钺（`Chengyue-Lu`）；
Execution 接口复核：黄毅（`let778750-cpu`）。风险：R2；PR class：feature。
进入基线：`develop@30600f2e9ae25852289f1d0ca12f114291c31457`。

用户在审阅下一步计划后指示“可以，先收口”。本候选在同一 PR 中提出整项验收、
`M5-007 IN_PROGRESS → DONE`、实现状态及施工导航同步，并核对 Issue #55 的关闭条件。
这项指示授权准备收口候选；本记录没有代写黄毅 APPROVED 或 reviewer 不可用确认。
合入前的共享状态仍是 M5-007 IN_PROGRESS、Issue #55 OPEN。
整项接受须由路诚钺承担 Task/Evaluation 判断，黄毅复核 Execution 接口，按
[开发协作指南](../../../DEVELOPMENT.md#51-hard-authority-adaptive-workflow)完成 R2 审查和必需 CI。

## Task 验收与当前身份

[H1–H5 逐项验收矩阵](M5-007_ACCEPTANCE_REVIEW.md)覆盖 frozen plan、四臂资格与 transport、
A4 admission/overlap/pairwise、actual facts/Receipt、全部失败/retry、匿名审查/freeze/reveal、
metric/analysis joins 和全链冷回放。PR86/89/90/96/104/106 的实现已合入；
PR107/121 分别合入准备和复核证据，不把这两个文档合并记为整项接受。

本 PR 只改 M5-007 的状态列，原 Task 名称、依赖和验收逐字保留，其他 Task 行不变。
M5-006、M6-008、M11-004/006/007 均为 DONE；Gate A/B 为 SATISFIED。
[本次输入](attempts/M5-007-COMPLETION-001/INPUTS.json)固定基线文件内容 SHA-256；
[验证记录](attempts/M5-007-COMPLETION-001/verification.json)分别记载当前候选检查、
复用证据的原始 source，以及源码相同的依据。

H5 获审 head 为 `68e612b353233bb8faf739d5012876739793cd84`。当前产品源码、Schema、
受信 H5 helper/fixture/test 与该 head 没有 Git 差异，本 PR 也不修改这些路径。
原 proof ZIP 的 454 个文件及 SHA-256
`176c47b3ebbc8e71d3cdb27f835d82a8e5af2ac876638d7ca7d0c7601a063b2d` 保持不变。
此前当前源码的 H1–H5 集中测试 111/111 PASS，原 ZIP 独立冷回放 PASS；
它们仍分别绑定[原验证 source](attempts/M5-007-ACCEPTANCE-REVIEW-001/verification.json)，
不改写为本次新运行的结果。H5 Agent Trace capture-gap warning 如实保留。

本次文档、公开接口及治理测试 113/113 PASS；内部 Markdown 链接和 Task 状态迁移检查通过。
九个本次入口、五个历史入口、五个复核入口内容哈希匹配，22 个既有 Attempt 无差异。

## Issue #55 关闭条件对照

以下是原 Issue 的十二项条件及其证据，表内“已验证”指工程契约验证。
具名整项 R2 接受和本候选的合入仍是关闭 Issue 的最后条件；CI 通过不自动产生人类接受。

| 原条件 | 当前证据与核对结果 |
|---|---|
| Gate A：A1/A2 transport 由具名 R2 Decision 接受并 exact-pin | [Gate A](BASELINE_TRANSPORT_GATE.md)保存 ADR-0020 identity/hash、具名接受与 SATISFIED 状态 |
| Gate A：逐臂 mapping 与 estimand/shared-condition/limitation/interpretation 冻结 | [Protocol 契约](../../../implementation/SYSTEM_EVALUATION_PROTOCOL.md)与 ADR-0020 固定 A1/A2→M6、A3/A4→M11，primary A4−A2 保留 transport package difference |
| Gate A：A1/A2 不消费或暴露 Mode/Method treatment | M6-008 allowlisted public envelope 与 H1–H3 baseline 正反用例；资格/transport/公开输入在[验收矩阵](M5-007_ACCEPTANCE_REVIEW.md)对照，已验证 |
| Gate A：新增实现依赖已经 task-defined | M6-008 在原 Task DAG 中已定义且 DONE；本 PR 不增加、删除或改写依赖 |
| Gate A：Decision 不冒充实现或 execution authority | Gate A 决策证据与 M6-008 实现/closeout 证据分开；Harness 只消费受信 transport，不授予权限 |
| Gate B：A4 actual Projection/Supply/binding 有 replay-valid closeout | [Gate B](../M11-SKILL-CLOSEOUT-GATE/GATE.md)已具名接受 M11-007 exact implementation/replay/CI；H4a/H5 再比较 overlay、actual fact 与 Receipt |
| Gate B：三种生命周期保留 actual facts 语义 | H3–H5 保留 completed/post-call-failed/preflight-blocked，失败/retry 不删；原冷回放保留 8 completed、1 post-call-failed、7 not-started |
| Gate B：无 Skill-specific dispatcher/fallback/reselection/mandatory Assignment | Gate B 接受统一 View/Host 与 Resolver 唯一选择权；H1–H5 不改变 M11 接口或 M5-003 treatment，源码身份核对通过 |
| Internal：admission Evaluation 能 exact 表达 private-oracle 或 typed absent/unknown | M5-006 版本化 overlap closure 与 H2 negative cases；缺失/absent/unknown 保持不合格，不进入 Runtime public 输入 |
| Internal：held-out/overlap eligibility 由 Harness 重算 | H2 preflight 与 H4c analysis 输入重新加载双方 identity/hash、冻结时序、intersection 与 eligibility；H1 phase 标签不授予 primary 资格 |
| Internal：新 fail-closed surface 有正反证据及 critical inventory | [coverage policy inventory](../../../../tests/coverage_policy.yaml)保留 qualification/overlap/overlay/comparability；H1–H5 111 项包含 proof 篡改负例；原[完整 source CI](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36955201792)含 coverage-quality SUCCESS，当前候选按 component CI 验证文档/治理 |
| Internal：M5-003 v0.1 与既有 M11 authority 不变 | 当前 source/pin 核对与本 PR changed-path 核对确认零产品契约变化；Task 验收内容与 H5 获审行逐字相同 |

合入且具名整项接受闭合后，回填 actual base/head/merge、CI/review 与 Issue 关闭回执，
保留 Issue 中原历史定义及快照。Issue #55 只负责这里的 architecture/internal closure，
不承担下面的真实运行 Gate。

## 接续与解释边界

M5-007 完成的是 bounded synthetic Harness 工程验收。四臂 8 cells / 10 pairs 的证明中，
13 指标仍全为 unavailable/null，`primary_confirmatory_eligible=false`；
没有真实 Provider/Tool/Human/admission 或科研净收益结论。

M5-008 保持 BLOCKED：M6-004 live conformance、`A4-RUNTIME-ADMISSION-GATE`、
`M5-LIVE-PILOT-AUTHORIZATION-GATE` 尚未闭合。接续准备按
[Live Pilot Gate](M5-008_LIVE_PILOT_GATE.md)处理；真实调用须另有具名账户、预算、数据和 Tool 授权。
M5-001/002、M5-004/005 原有 case/Human/正式评价 Gate 不变；本收口不修改 main、tag 或发行。
