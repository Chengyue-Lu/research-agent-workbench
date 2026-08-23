# Decision Authority Matrix and Authority Rule Eligibility

状态：Active implementation contract

## 1. 目的

Decision Authority Matrix 把“哪类 actor 在什么规则下可进入某类决定的下一步”与具体 Agent、模型、
Provider 和 Runtime 分离。它是 eligibility rule set，不是 Permission、Human Decision 或执行系统。
它区分三类稳定的规则角色：

| Authority class | 可满足的规则类别 | 明确禁止由 eligibility 直接产生 |
|---|---|---|
| `agent` | 形成 non-binding proposal | commit Mode/Action/Mechanism、放宽权限或数据边界、提升 Claim |
| `deterministic-resolver` | 结构验证；在事实闭合且无歧义时提交有限的结构决定 | 用 PASS 代替科学判断；提交权限/数据放宽或 Claim promotion |
| `human-gate` | 在具名 Gate、必要事实和既有上位政策内提交保留决定 | 豁免 Schema、来源、法律/政策或伪造缺失 Evidence |

矩阵路径为 `registry/authority/decision-authority-matrix.yaml`，身份为
`rwb-decision-authority@1.0.0`。Eligibility record 必须固定该文件的 repository-relative path 与
raw-byte SHA-256。

## 2. 冻结的 v1 决定面

| Decision kind | Resolver commit-rule eligibility | Human Gate commit-rule eligibility |
|---|---:|---:|
| Mode selection | 仅注册集合闭合且选择无歧义 | 歧义已披露且 Gate 具名 |
| Action selection | 仅 Registry 闭合且 trigger match 无歧义 | 歧义已披露且 Gate 具名 |
| Mechanism selection | 仅义务闭合且最小机制无歧义 | 歧义已披露且 Gate 具名 |
| Skill/Tool binding | 仅 Capability snapshot、权限交集和绑定均冻结且无歧义 | 同样不得绕过 Capability/权限事实 |
| Permission relaxation | 禁止 | 必须产生修订后的 Task/Protocol，并完成风险复核 |
| Data-boundary relaxation | 禁止 | 还必须固定目的地与数据范围 |
| Claim promotion | 只能验证 Evidence 链和 ceiling | 必须确认 ceiling 允许并复核限制 |

Agent 对以上决定都只能匹配 `propose` 规则。Resolver 可以匹配 `validate` 规则；匹配 `commit` 规则也
只表示有资格把候选交给真正的决策/执行层，不能由本模块产生 binding decision。

## 3. 可重算 Authority Rule Eligibility

`authority_rule_eligibility` 保存 subject、actor、operation、`asserted_facts`、可选 Human Gate ref 与
记录结果。Validator 使用矩阵原始文件 hash 重新计算“假设这些 assertions 成立，该 actor 是否匹配
Matrix 规则”：

```text
subject + requested operation
  → exact Matrix ref/path/hash
  → actor/operation rule
  → required asserted facts
  → required Human Gate ref
  → eligible/eligible-for-decision | blocked/human-gate | blocked
```

`eligible` 严格不等于 fact proven、Human approval、permission granted、Claim promoted 或 decision
executed。`asserted_facts` 是调用方声明，不是 provenance；本模块不验证事实来源。额外 Gate ref 也
不能作为 cosmetic approval 注入非 Gate 路径。真正 Human Decision 与 provenance system 不在本轮实现。

## 4. Fail-closed 边界

以下情况阻断：Matrix ref/path/hash 漂移、未知决定类型、actor/operation 无规则、required asserted facts 缺失、
Human Gate ref 缺失、把 Gate ref 塞入不消费 Gate 的路径，以及记录结果与重算结果不一致。

Matrix v1 的决定类型、commit actor 和 commit required facts 在协议模型中形成闭集。任何放宽都需要新
Matrix version、迁移影响、R2 审查和新的正反 fixture，不能原位修改 v1 语义。

## 5. 非目标

- 不定义具体 Human 的组织角色、账号或长期授权；
- 不创建 Capability Snapshot、Skill Assignment 或 Tool endpoint；
- 不修改权限、Protocol、Claim、Evidence、Attempt、Receipt 或 Trace；
- 不判断科学正确性、法律合规性或外部政策许可；
- 不把 eligibility evaluator 变成全局 Supervisor 或 Runtime 调度器。
