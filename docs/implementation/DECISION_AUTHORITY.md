# Decision Authority Matrix and preflight

状态：Active implementation contract

## 1. 目的

Decision Authority Matrix 把“谁可以对哪类决定做什么”与具体 Agent、模型、Provider 和 Runtime 分离。
它只区分三类稳定权威：

| Authority class | 允许的效果 | 明确禁止 |
|---|---|---|
| `agent` | 形成 non-binding proposal | commit Mode/Action/Mechanism、放宽权限或数据边界、提升 Claim |
| `deterministic-resolver` | 结构验证；在事实闭合且无歧义时提交有限的结构决定 | 用 PASS 代替科学判断；提交权限/数据放宽或 Claim promotion |
| `human-gate` | 在具名 Gate、必要事实和既有上位政策内提交保留决定 | 豁免 Schema、来源、法律/政策或伪造缺失 Evidence |

矩阵路径为 `registry/authority/decision-authority-matrix.yaml`，身份为
`rwb-decision-authority@1.0.0`。preflight 必须固定该文件的 repository-relative path 与 raw-byte
SHA-256。

## 2. 冻结的 v1 决定面

| Decision kind | Deterministic commit | Human Gate commit |
|---|---:|---:|
| Mode selection | 仅注册集合闭合且选择无歧义 | 歧义已披露且 Gate 具名 |
| Action selection | 仅 Registry 闭合且 trigger match 无歧义 | 歧义已披露且 Gate 具名 |
| Mechanism selection | 仅义务闭合且最小机制无歧义 | 歧义已披露且 Gate 具名 |
| Skill/Tool binding | 仅 Capability snapshot、权限交集和绑定均冻结且无歧义 | 同样不得绕过 Capability/权限事实 |
| Permission relaxation | 禁止 | 必须产生修订后的 Task/Protocol，并完成风险复核 |
| Data-boundary relaxation | 禁止 | 还必须固定目的地与数据范围 |
| Claim promotion | 只能验证 Evidence 链和 ceiling | 必须确认 ceiling 允许并复核限制 |

Agent 对以上决定都只能 `propose`。Resolver 可以 `validate`；`validate` 不是 `commit`，也不把结构
PASS 升级为科学结论。

## 3. 可重算 preflight

`decision_authority_preflight` 保存 subject、actor、operation、presented facts、可选 Human Gate ref 与
记录结果。Validator 使用矩阵原始文件 hash 重新计算结果：

```text
subject + requested operation
  → exact Matrix ref/path/hash
  → actor/operation rule
  → required facts
  → required Human Gate ref
  → allowed/proceed | blocked/human-gate | blocked
```

`allowed` 只表示该 actor 在这些冻结事实下具有所声明 operation 的权威，不证明决定内容正确，也不
执行决定。额外 Gate ref 不能作为 cosmetic approval 注入非 Gate 路径。

## 4. Fail-closed 边界

以下情况阻断：Matrix ref/path/hash 漂移、未知决定类型、actor/operation 无规则、required facts 缺失、
Human Gate ref 缺失、把 Gate ref 塞入不消费 Gate 的路径，以及记录结果与重算结果不一致。

Matrix v1 的决定类型、commit actor 和 commit required facts 在协议模型中形成闭集。任何放宽都需要新
Matrix version、迁移影响、R2 审查和新的正反 fixture，不能原位修改 v1 语义。

## 5. 非目标

- 不定义具体 Human 的组织角色、账号或长期授权；
- 不创建 Capability Snapshot、Skill Assignment 或 Tool endpoint；
- 不修改权限、Protocol、Claim、Evidence、Attempt、Receipt 或 Trace；
- 不判断科学正确性、法律合规性或外部政策许可；
- 不把 preflight 变成全局 Supervisor 或 Runtime 调度器。
