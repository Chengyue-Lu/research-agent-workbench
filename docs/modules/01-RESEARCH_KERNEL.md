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

### Research State 的扩展原则

`Unknown`、`Contradiction`、`Assumption`、`Attempt`、`Failure` 与 `Frontier` 用于表达长期研究状态。
它们只有在跨 Mode 的真实案例证明字段稳定后才逐项进入核心对象，不一次扩成统一知识图谱。
Schema 覆盖程度由[实现状态](../STATUS.md)说明。

Failure 至少应保留 `goal`、`method`、`outcome`、`failure_reason`、`what_was_learned` 和
`revisit_condition`，避免新 Runtime 因缺少聊天历史重复已知失败。

`Attempt` 专指一次 Task 的一次执行，并关联 `work/<task>/<attempt>/`、Attempt Archive 与
Execution Receipt。包含多个执行 Attempt 的 research-level / method trial 必须采用独立对象名或
显式关系，不能复用或静默改变 `Attempt` 语义。

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
