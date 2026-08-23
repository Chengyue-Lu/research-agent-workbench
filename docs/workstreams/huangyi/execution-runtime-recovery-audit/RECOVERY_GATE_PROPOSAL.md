# Execution / Runtime / Recovery Gate 草案

状态：`PROPOSAL`。本文件保存待审查的 contract shape、Gate 和对抗场景；它不是 ADR、Schema、
TASKS acceptance，也不代表解除或扩大 Architecture Hold。

## 1. Hold 边界

继续推进：M8-002、M8-003、安全修复、单元/集成/对抗测试、Trace、redaction、hash/ref、
archive、file-only verification，以及只读外部机制调查。

暂停扩张：新 Runtime、自动 Router/fallback、多 Agent/critic、复杂 salvage recovery、隐藏会话
状态、streaming/multimodal/server-tool 接入，以及把 Execution 重新接到尚未完成的 Method
Resolution 之前。

## 2. 候选不变量 I1–I12

| ID | 不变量 | 最低证明方式 |
|---|---|---|
| I1 | Runtime 只能消费已解析 Method，不能覆盖或补写 Method。 | schema validation + negative integration test |
| I2 | frozen binding 缺失或失配必须停止，不能静默重选 Skill/Tool/Model。 | hash/ref mismatch test |
| I3 | 未声明的 Skill、Tool、Agent 或 side effect 不得执行。 | preventive policy test + Trace absence |
| I4 | 每次远程数据出口都要核对 source、classification、destination、authorization、transformation/redaction、retention；策略缺失默认 BLOCK。 | two-call Tool Result adversarial fixture |
| I5 | Capability/Execution View 必须版本化、可 hash、可追溯到输入，不依赖隐藏平台状态。 | schema + canonical digest test |
| I6 | Session termination、Attempt/Receipt lifecycle、Task contract satisfaction、Research acceptance 四层分离。 | state-transition tests |
| I7 | no-Skill、tool-only、Skill 是一等路径；前两者不得生成虚假 Assignment。 | three independent end-to-end fixtures |
| I8 | Receipt 记录 requested/observed model、实际工具、side effects 与 Trace completeness，不用计划值冒充观察值。 | provider drift and side-effect tests |
| I9 | 隐藏/远端 session 不能成为长期 authority；恢复依赖已提交 canonical artifacts。 | clean-checkout/file-only verification |
| I10 | Runtime 不能批准 Claim、Method、权限放宽、Human Gate 或 Research acceptance。 | permission/state negative tests |
| I11 | immutable input pin、resume-check、clean resume 与 salvage recovery 必须分别命名和测试。 | distinct CLI/schema/test assertions |
| I12 | 每项保障标注 `preventive / detective / advisory / unknown`；没有测试或观测证据不得写成 enforceable。 | enforcement matrix review + CI |

## 3. 分阶段 Gate

### Gate 0：审计来源可信

- `SOURCE_MANIFEST` 固定 main/develop/PR head、私有来源 hash 与 Share fingerprint；
- `CLAIM_LEDGER` 分开 fact/inference/proposal 及 main/PR23/future scope；
- 原始私密材料和 1640 行个人稿不进入 Git。

### Gate 1：上游契约完成

- M8-002 经 `develop` 验证并发布；
- M8-003 提供版本化 Method Resolution；
- 审计与外部调查可并行，但不能成为 M8 的前置。

### Gate 2：Execution Boundary Contract 获批

- 双方批准 Resolved Execution View、egress policy、conditional Assignment、状态分层和
  enforcement matrix；
- 影响 Stable Architecture/Schema 的内容由独立 ADR/Task 承载。

### Gate 3：K-API-2 洁净重建

- 从当时最新 `develop` 新建分支，不复用 PR #23 head；
- K-API-2 是 M6-003 的修复/稳定化，不代表解除 Runtime 扩张暂停；
- 可借鉴机制重新实现、重新测试，不继承 PR #23 TASKS、风险目录、临时文档或证据包。

### Gate 4：Conformance 与对抗验收

- 下列最低场景全部通过，并有 clean-checkout、Trace、archive 与 file-only verification；
- M6-003/M6-004 只按真实验收证据更新状态。

### Gate 5：可选外部 Runtime

- 只有 Gate 0–4 完成且建立独立 Task，才评估新的 native/multi-agent/runtime adapter；
- ADR-0010 Gate F 已完成，不因生态调查重新开放。

## 4. 最低对抗场景

1. 未授权本地 Tool Result 在第二次 Provider 调用前被阻断，且不进入 transcript/archive；
2. 获批出口只保留脱敏必要内容，并记录 destination、authorization、transformation、retention；
3. read-only 或 allowed-roots/write-scope 不覆盖 Attempt 输出目录时，创建文件前阻断；
4. no-Skill、tool-only、Skill 三条端到端 fixture 独立通过，前两者无虚假 Assignment；
5. Provider `COMPLETE` 但机器检查失败时，Handoff 不得 completed，Receipt 不得
   `contract-satisfied`；
6. summary 不自动成为 fact，H2 semantic reversal 能被抽查或 Human Gate 捕获；
7. context-limit 只标 incomplete；safe-paused 只能恢复到新 Attempt；
8. requested/observed model 漂移在普通执行告警，在 evaluation/benchmark 阻断；
9. model-api/native-agent 满足同一最低 Trace 事件和完整度；缺少扫描时敏感状态为 unknown，
   不能写 false；
10. base-state hash pin、真正 resume-check、salvage recovery 的术语、schema 和测试互不混用；
11. 干净检出只凭已提交文件完成 archive verification，不依赖 ignored `work/` 或临时目录；
12. PR #23 的 TASKS、第二风险目录、临时文档和原始 transcript 不出现在替代分支。

## 5. 外部 Agent 机制调查模板

每项调查记录：

| 字段 | 要求 |
|---|---|
| mechanism | delegation、context isolation、routing、checkpoint/recovery、human intervention、observability、concurrency 或 failure semantics |
| problem solved | 机制实际解决的问题；不能只写产品口号 |
| assumptions | 隐藏状态、可信边界、Provider、并发和持久化假设 |
| RWB fit | 对 I1–I12 是满足、需适配、冲突还是未知 |
| version/date | 版本、提交或文档日期，避免把动态事实写成永久结论 |
| evidence | 优先官方文档、源码、测试或论文；区分 observation 与 inference |
| decision | `reference / prototype later / reject / unresolved`，并说明理由 |

调查输出是设计证据，不是 M8、安全修复或 K-API-2 的硬前置，也不授权接入外部 Runtime。
