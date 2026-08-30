# 模块 01：最小科研内核

## 1. 目标

为不同研究模式提供极小、稳定且可追溯的公共对象模型。它约束证据与结论的关系，但不规定研究必须线性推进。

## 2. 核心对象

### Question

表示当前需要回答的问题。最低字段：`id`、`text`、`scope`、`known_ambiguities`、`status`、`revision`。

### Hypothesis / Proposition

表示待检验假设、理论命题或解释候选。最低字段：`id`、`statement`、`assumptions`、`applicability`、`status`。

### Method

表示取得证据的方法，例如实验协议、仿真模型、推导方案、统计设计或检索策略。最低字段：`id`、`kind`、`spec_ref`、`version`、`limitations`。

### Run

表示一次可识别的执行活动。最低字段：`id`、`method_ref`、`input_refs`、`environment_ref`、`started_at`、`status`、`output_refs`。

### Evidence

表示可定位的观察、文献片段、数据、反例、运行结果或推导结果。最低字段：`id`、`kind`、`source_ref`、`locator`、`content_hash`、`quality_flags`。

### Claim

表示可审查陈述。最低字段：`id`、`statement`、`strength`、`support_refs`、`counterevidence_refs`、`limitations`、`status`。

### Decision

表示正式接受、拒绝、修改、暂停、排除或发布决定。最低字段：`id`、`decision`、`scope`、`reason_refs`、`actor`、`timestamp`、`supersedes`。

### Research State candidate 与扩展边界

M10 已实现 bounded Research State composition candidate、Research Attempt lineage / Research Failure
candidate、ref-only Method Trace v0.1 和 fresh-process machine Gate。当前 Research State 可以用带 revision
的 composition 表达轻量 `Unknown` / `Assumption` item、`Contradiction` relation、derived `Frontier`，以及
对现有 Evidence、Claim 和 kernel Decision 的 exact 引用；引用、身份、哈希与 supersession closure 可由
机器重算。

这些表示仍是 bounded implementation candidate，不是最终通用 kernel Schema。machine Gate 证明的是
两份 synthetic case 的确定性 closure 和已声明 fixture behavior，不证明科学正确性，也不完成 Human/R2
semantic closeout，更不自动授予 Topic 5 implementation authority。当前覆盖与限制见
[实现状态](../STATUS.md)。

legacy execution `Attempt` 仍专指一次 Task 的一次执行，并关联 `work/<task>/<attempt>/`、Attempt Archive
与执行记录。M10 的 `research_attempt_lineage` 是独立、版本化的 sidecar：它 exact-pin 既有 execution
Attempt，并把 from-State、可选 predecessor Attempt 与 reopen justification 分开；它不改写 legacy
Attempt，也不从 Attempt 自动推导新的 State。

Research Failure 的通用语义最小值只冻结 `learned_result` 和 `revisit_condition`。execution-origin
Failure 还必须通过一个 all-or-nothing profile 精确引用 source Research Attempt，并记录 observed result
与 uncertainty；non-execution Failure 不得伪带该 profile。Research Failure 必须继续与 execution
failure、negative Evidence、Capability Gap 和 Skill Need 分离，不能因名称相近而合并。

## 3. 关系而非固定流程

允许以下关系：

- Question 可产生多个互相竞争的 Hypothesis；
- Method 可对应多个 Run，也可在无 Run 时描述形式推导；
- Evidence 可支持、反驳或仅限制 Claim；
- 新 Evidence 可使已接受 Claim 降级、撤回或分叉；
- Decision 可引用 Claim、Evidence、风险和人工判断；
- 任何对象均可 `superseded`，但旧版本不可被静默覆盖。

禁止把 `Question → Method → Run → Evidence → Claim` 实现为只能前进的全局状态机。

## 4. Claim 强度

内核只定义可扩展的强度类别，不定义学科结论：

- `exploratory`
- `source_reported`
- `derivation_supported`
- `simulation_supported`
- `observationally_supported`
- `experimentally_supported`
- `synthesis_supported`
- `unresolved`
- `withdrawn`

Mode Pack 决定每种强度需要什么工件。Agent 不能越过 Project Protocol 的 `claim_ceiling`。

## 5. 身份与版本

- 稳定 ID 表示逻辑对象，路径只是位置。
- 每次修订生成新的 `revision` 和内容哈希。
- 引用必须指向确切 revision 或不可变内容哈希。
- 原始 Evidence 不原地修改；解析、翻译和摘要是带来源关系的新工件。
- `stale`、`superseded`、`invalidated`、`withdrawn` 和 `archived` 语义不同。

## 6. 表示与演进边界

Research State 以版本化 YAML/JSON、JSON Schema 和 compact index 为事实源，不绑定 Python object、
运行时数据库或 conversation memory。对象迁移必须保留原/新 hash、版本和转换器身份；CLI 与库
只是该契约的消费者，不能成为另一套对象真值。

## 7. 主要风险

- 公共内核字段不断吸收模式专用概念，最终变成全局大 Schema；
- 结构完整被误认为科学正确；
- Claim 强度命名造成虚假精确；
- 为审计保存过量中间状态，反而提高成本；
- 路径改变导致引用失效。

应对：公共字段只有被两个差异明显的案例共同需要时才进入内核；验证器输出 `structurally_valid`，不得输出 `scientifically_true`。

## 8. 验收条件

- 证据综合和仿真案例均可用同一组核心对象表达；
- 两个案例不需要大量空字段或伪造 Run；
- 任一 Claim 可在一次命令内列出支持、反证、限制和版本；
- 旧版本与负结果不会因更新而丢失；
- 内核代码不依赖 Codex、Claude、Zotero、DVC 或具体模型 SDK。
