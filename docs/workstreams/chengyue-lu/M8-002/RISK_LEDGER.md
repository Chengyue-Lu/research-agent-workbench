# M8-002 风险台账

状态：feature 审查输入。`fact` 只描述本分支或固定基线可证明的行为；`proposal` 不改变项目权威。

| ID | 类型 | 风险与边界 | 处置 | 状态 |
|---|---|---|---|---|
| M8A-SEM-001 | fact | Schema、Registry 与测试只能证明结构和引用完整，不能证明 Action 的科学适用性。 | 文档与 validator 保持 authority ceiling；真实方法价值留给后续案例和 Human Gate。 | controlled |
| M8A-BIND-001 | fact | 如果 Action 字段绑定 Skill、Tool、Agent、Model、Provider 或 Runtime，Method/Core 会被执行实现反向塑形。 | Schema 禁止实现绑定；M8-003 通过独立 Method Resolution 消费 Action 引用。 | controlled |
| M8A-HASH-001 | fact | Action 原始字节变化而 Registry 哈希未更新，会使历史引用与实际内容漂移。 | Registry 固定 path/hash 闭集；missing、orphan、ID/version/mode/path/hash drift 均为确定性错误。 | controlled |
| M8A-IDENTITY-001 | fact | 已发布 Action 若保持 `action_id@version` 却同时更新 Registry hash，会让逻辑身份静默改义。 | 契约规定 entry append-only、语义变化必须升版；合并边界比较 base/head Registry，静态验证明确不声称能证明历史不可变。 | controlled by merge governance |
| M8A-CLAIM-001 | fact | 自由字符串或相互冲突的 Claim effect 会建立第二套 Claim vocabulary，或越过 Mode claim rules。 | 复用 canonical Claim strength；validator 阻断 effect overlap 和 `may_support` 越界。 | controlled |
| M8A-GATE-001 | fact | `human_gates` 若在 Action 中定义批准结果、持续性或 authority，会抢占 M8-005。 | 本契约只保存 Gate ID；decision vocabulary 与 authority matrix 明确排除。 | controlled |
| M8A-CROSS-001 | fact | Execution/Receipt 仍存在 legacy Skill Assignment 耦合；在 M8-002 中修补会跨越两线 owner 和任务边界。 | 不修改 Execution/Receipt；等待 M8-003 后的独立 Resolved Execution View/Execution Boundary Task。 | deferred |
| M8A-GOV-001 | fact | 把工作流文案绑定到某一版 closeout 机制，会在治理更新后再次产生流程死结。 | 本分支保持非 DONE；完成与后继激活引用合并时有效 policy，不预设独立 closeout。 | controlled |
| M8A-COMPAT-001 | inference | 后续 Mode v0.2 migration 可能误把 Action 引用变化描述成自动升级历史 v0.1 对象。 | v0.1 保持只读兼容；迁移需独立 M8-004、原/新 hash 与版本证据。 | deferred |
| M8A-VALUE-001 | proposal | 16 个 Action 可能只增加分类元数据，而未减少真实 method violation。 | M8-002 只建立可评估契约；净增量由 M8-003 后真实 forward cases 判断。 | deferred |

## 跨线合并规则

- Runtime/Execution 线可以读取已冻结 Action ref，但不得修改 Action 语义或静默选择替代 Action；
- Method/Core 线不修改 Provider、API session、Receipt、Recovery 或数据出口实现；
- 共享 Schema 需要双方 owner 审查；无法隔离写入时串行；
- 个人审计稿和候选 PR 只作来源，不覆盖 ADR、TASKS、正式 Schema 或已合入代码。
