# 待共同裁定清单（路诚钺 × 黄毅）

> 背景：Phase 0 建立了风险码"发射必登记"强制测试（`tests/test_risk_codes.py`），注册表现存 230 个已发射码 + 24 个文档已定义但未发射码。`src/research_workbench/contracts/risk_codes.py` 中的 `ALIGNMENT_NOTE = "语义对齐待路诚钺+黄毅共同确认"` 具体指以下四项。每项附黄毅侧建议和裁定后的工程动作。
>
> 状态：**待裁定**。裁定结果将转化为新 ADR（见文末附注），本文件随后删除。
>
> 日期：2026-08-19

## 裁决项 1：DOCUMENTED_GAP —— 204 个"已发射但未进模块文档表"的码

**现状**：模块文档（[04 §10](docs/modules/04-SKILL_SYSTEM.md)、[05 §8](docs/modules/05-TASK_AND_HANDOFF.md)、[06 §8](docs/modules/06-CONTEXT_GOVERNANCE.md)、[08 §4](docs/modules/08-VALIDATION_RISK_AND_GATES.md)）的风险表只挂了 33 个码，其余 204 个已发射码没有文档落点。测试目前把"已发射且无文档链接"机械地收集为 DOCUMENTED_GAP，但"文档表应该穷举还是精选"这个口径本身未定。

| 归属模块 | 数量 | 码族 | 性质 | 建议责任人 | 建议文档落点 |
|---|---|---|---|---|---|
| evaluation.skill_evaluation | 72 | EVAL-* | Skill 评估流水线检查 | 路诚钺 | 08 §4 或新增评估章节 |
| context.handoff_transfer | 27 | HANDOFF-AUDIT/REVIEW-* | Transfer Manifest/Audit/Review | 路诚钺 | 05 §8 或 08 §4 |
| validation.documents | 23 | SCHEMA-INVALID、PARSE-ERROR 等 | 通用结构校验 | 共有 | 08 §4 |
| observability.models | 22 | RECEIPT-*、TRACE-* | Receipt/Trace 契约 | 路诚钺 | 08 §4 |
| cli | 19 | STATE-*、RESUME-* 等 | 状态恢复与一致性 | 黄毅 | 08 §4 |
| validation.relationships | 11 | HANDOFF-*、REF-HASH | 引用关系校验 | 共有 | 08 §4 |
| capability.resolver | 10 | SKILL-*/TASK-* | Skill 选择/权限升级 | 路诚钺 | 04 §10 |
| execution | 9 | EXEC-* | K-API-2 执行闭环 | 黄毅 | [K_API_2_FILE_LOOP.md §5](docs/implementation/K_API_2_FILE_LOOP.md)（表已写好，只欠挂链） |
| context.models | 4 | CTX-* | 上下文契约 | 路诚钺 | 06 §8 |
| capability.catalog 等小组 | 6 | SKILL-INACTIVE 等 | Registry 生命周期 | 路诚钺 | 04 §10 |

**三选一**：

- 方案 A（全量对齐）：204 码逐条补进文档表。文档即字典，但约 204 行编写量。
- 方案 B（注册表唯一权威）：声明 `risk_codes.py` 是唯一穷举源，文档表只保留精选码；DOCUMENTED_GAP 改名改注释，不再视为"缺口"。成本最小。
- 方案 C（分层，**黄毅建议**）：影响人为决策的码（WARN/HUMAN/触发 Gate 的 BLOCK）必须进文档表；纯结构校验码（SCHEMA-INVALID、PARSE-ERROR 等）留在注册表即可。编写量明显小于 A，文档保持可读。

裁定后动作：按选定方案改 `risk_codes.py` 注释、同步对应文档、必要时调整 `test_documented_gap_*` 的断言口径。

## 裁决项 2：NOT_YET_EMITTED —— 24 个"文档已定义、代码未发射"的码

**现状**：这些码只在文档表里有一行语义，其中 18 个连 severity 都是空字符串。谁先实现发射谁就会"猜"语义——所以发射前必须两人确认。下表含黄毅建议值，逐行确认或改判即可：

| 码 | 出处 | 文档语义 | 当前 severity | 黄毅建议 | 待确认点 |
|---|---|---|---|---|---|
| SKILL-VERSION-DRIFT | 04 §10 | 执行用 Skill 版本 ≠ Assignment | block | 维持 | — |
| SKILL-CONTEXT-FLOOD | 04 §10 | Skill 上下文总账超预算 | "warn/block" 二义 | 拆两档：软预算 warn、硬预算 block | 是否拆档 |
| SKILL-PERMISSION-ESCALATION | 04 §10 | Skill 请求越权 | block | 维持 | — |
| SKILL-SUPPLY-CHAIN | 04 §10 | Skill 来源/脚本/许可未核 | human | 维持，并把 human 写为正式等级 | human 是否入 severity 词表 |
| SKILL-TAXONOMY-GROWTH | 04 §10 | Registry 膨胀但复用低 | warn | 维持 | — |
| SKILL-STALE-EVAL | 04 §10 | 版本更新后无回归评估 | warn | 维持 | — |
| TASK-TOO-BROAD | 05 §8 | 预算内完不成 | （空） | block | — |
| HANDOFF-LOSSY | 05 §8 | 结论无引用 | （空） | block | — |
| HANDOFF-OMITS-NEGATIVE | 05 §8 | 未交接失败/反证 | （空） | block | — |
| HANDOFF-CLAIM-UPGRADE | 05 §8 | 超出 Claim 上限 | （空） | block | — |
| HANDOFF-OVERHEAD | 05 §8 | 审计工件成本涨但不改变决定 | （空） | warn（见裁决项 3） | 与 CTX 版归并 |
| TASK-READ-OUTSIDE-SCOPE | 05 §8 | 读未声明内容且无扩域记录 | （空） | block | — |
| TRACE-MESSAGE-MISSING | 05 §8 | 跨 agent 传递无 Archive 记录 | （空） | block | — |
| TRACE-ACTOR-UNOWNED | 05 §8 | actor 未绑定实名责任人 | （空） | block | — |
| CTX-MAIN-PRESSURE | 06 §8 | 主上下文噪声增长 | （空） | warn | — |
| CTX-SUMMARY-DISTORTION | 06 §8 | 摘要改变源文限定条件 | （空） | block | — |
| CTX-STALE | 06 §8 | 引用过期 revision | （空） | warn | — |
| CTX-RECALL-LOOP | 06 §8 | 反复重读原始材料 | （空） | warn | — |
| CTX-PINNED-GROWTH | 06 §8 | 钉住信息只增不减 | （空） | warn | — |
| CTX-SKILL-POLLUTION | 06 §8 | 加载无关 Skill | （空） | warn | — |
| CTX-RECOVERY-DRIFT | 06 §8 | 恢复后目标已变更 | （空） | block | — |
| CTX-READ-SCOPE-DRIFT | 06 §8 | 读未声明内容/误用临时材料 | （空） | block | 与 TASK-READ-OUTSIDE-SCOPE 的边界 |
| CTX-HANDOFF-OVERHEAD | 06 §8 | Handoff 工件增长但不改变决策 | （空） | warn（见裁决项 3） | 与 HANDOFF 版归并 |
| CTX-TRACE-RELOAD | 06 §8 | 因 Trace 存在而批量重读历史 | （空） | warn | — |

裁定后动作：把确认的 severity 和 modules 填回注册表，删除 ALIGNMENT_NOTE 中对应部分。

## 裁决项 3：HANDOFF-OVERHEAD 与 CTX-HANDOFF-OVERHEAD 疑似重复

原文几乎同义：

- [docs/modules/05-TASK_AND_HANDOFF.md](docs/modules/05-TASK_AND_HANDOFF.md) 第 190 行："审计工件成本持续增加但不改变接受、返工或 Gate 决定"
- [docs/modules/06-CONTEXT_GOVERNANCE.md](docs/modules/06-CONTEXT_GOVERNANCE.md) 第 150 行："Handoff 工件增长但没有改变决策"

**二选一**：

- 合并为一个码（**黄毅建议**：保留 `HANDOFF-OVERHEAD` 于 05 §8，从 06 §8 删除 CTX 版）——同一风险两个名字只会让实现者无所适从。
- 或保留两个，但必须把边界写清楚（例如 05 版管"工件成本"，06 版管"上下文占用"）。

裁定后动作：改对应文档表 + 注册表，若删除一码需在 CHANGELOG 记一笔。

## 裁决项 4：M0-007 LICENSE（[docs/TASKS.md](docs/TASKS.md) 中状态 BLOCKED）

**现状**：仓库无 LICENSE 文件，原创 Skills 带 `project-original-unlicensed` 发布阻断。候选：

| 选项 | 特点 | 对科研项目的影响 |
|---|---|---|
| MIT | 最简、兼容最好 | 无专利条款 |
| Apache-2.0（黄毅建议） | 含专利授权与商标保护 | 篇幅略长，同样兼容学术引用 |
| 其他（CC/BSD/双许可） | 视发布对象定 | 需讨论 |

裁定后动作：黄毅加 LICENSE 文件、消除发布阻断、TASKS.md M0-007 → DONE。

## 附：顺手发现的小问题

- `docs/decisions/` 存在两个 0005 编号（0005-ASSIGNMENT-REFERENCE-IN-HANDOFF 与 0005-SCOPED-WRITE-PERMISSIONS），建议裁定结果落成新 ADR 时一并重编号。

## 裁决项 5（M6-004 live 新发现）：safe-paused 终态与 Context Snapshot 的契约关系

**现象**：live 运行 AT-API-008 因并行工具预算安全暂停，closeout 诚实发布，但 Receipt 关系校验 BLOCK：`RECEIPT-SAFE-PAUSE-CONTEXT-MISSING`（"safe-paused execution must pin the Context Snapshot that triggered closeout"）。K-API-2 的 API 会话没有 Context Snapshot 机制（自动 Trace/上下文捕获属 M6-006），导致任何 safe-paused 的 API Attempt 目前都无法通过关系校验。

**二选一**：

- 规则放宽（**黄毅建议**）：`execution_kind=model-api` 且尚无上下文捕获时，safe-paused 的 Receipt 改钉 `session-transcript.json` 作为触发现场，该校验降级为 WARN；M6-006 落地后再恢复 BLOCK。
- 维持 BLOCK：safe-paused 的 API Attempt 一律视为不可发布终态，直到 M6-006。

裁定后动作：按结论改 `validation/relationships` 对应规则与测试。

## 裁决项 6（M6-004 live 新发现）：Skill 包内容两处待修（路诚钺 lane）

- `literature-evidence-extraction` 的 `references/evidence-contract.md` 只有字段散文，真实模型字段级合规率不稳定；建议内嵌一个最小合法 Evidence YAML 示例（本次 live 靠把 `examples/objects/evidence/EVID-001-01.yaml` 列为任务输入才稳定达标）。
- 同 Skill 的 SKILL.md 第 8 步引用 `scripts/check_evidence_record.py`，仓库中不存在该脚本；建议删除该引用或补脚本。

注意：接受态 Skill 的任何内容修改都会改变 package hash，需走 Skill admission 流程重新钉版本（本次未动）。
