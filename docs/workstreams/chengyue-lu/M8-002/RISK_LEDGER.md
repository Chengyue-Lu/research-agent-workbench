# M8-002 风险台账

状态：feature 审查输入。`fact` 只描述本分支或固定基线可证明的行为；`proposal` 不改变项目权威。

| ID | 类型 | 风险与边界 | 处置 | 状态 |
|---|---|---|---|---|
| M8A-SEM-001 | fact | Schema、Registry 与测试只能证明结构和引用完整，不能证明 Action 的科学适用性。 | 文档与 validator 保持 authority ceiling；真实方法价值留给后续案例和 Human Gate。 | controlled |
| M8A-BIND-001 | fact | 如果 Action 字段绑定 Skill、Tool、Agent、Model、Provider 或 Runtime，Method/Core 会被执行实现反向塑形。 | Schema 禁止实现绑定；M8-003 通过独立 Method Resolution 消费 Action 引用。 | controlled |
| M8A-HASH-001 | fact | Action 原始字节变化而 Registry 哈希未更新，会使历史引用与实际内容漂移。 | Registry 固定 path/hash 闭集；missing、orphan、ID/version/mode/path/hash drift 均为确定性错误。 | controlled |
| M8A-GATE-001 | fact | `human_gates` 若在 Action 中定义批准结果、持续性或 authority，会抢占 M8-005。 | 本契约只保存 Gate ID；decision vocabulary 与 authority matrix 明确排除。 | controlled |
| M8A-CROSS-001 | fact | Execution/Receipt 仍存在 legacy Skill Assignment 耦合；在 M8-002 中修补会跨越两线 owner 和任务边界。 | 不修改 Execution/Receipt；等待 M8-003 后的独立 Resolved Execution View/Execution Boundary Task。 | deferred |
| M8A-GOV-001 | fact | 原 feature 提交曾直接把 M8-002 置为 DONE，并提前宣布 M8-003，违反最新 feature/closeout 分离规则。 | feature 仅设 IN_PROGRESS；DONE、Changelog 和 M8-003 READY 进入独立 task-closeout。 | controlled |
| M8A-COMPAT-001 | inference | 后续 Mode v0.2 migration 可能误把 Action 引用变化描述成自动升级历史 v0.1 对象。 | v0.1 保持只读兼容；迁移需独立 M8-004、原/新 hash 与版本证据。 | deferred |
| M8A-VALUE-001 | proposal | 16 个 Action 可能只增加分类元数据，而未减少真实 method violation。 | M8-002 只建立可评估契约；净增量由 M8-003 后真实 forward cases 判断。 | deferred |

## 跨线合并规则

- Runtime/Execution 线可以读取已冻结 Action ref，但不得修改 Action 语义或静默选择替代 Action；
- Method/Core 线不修改 Provider、API session、Receipt、Recovery 或数据出口实现；
- 共享 Schema 需要双方 owner 审查；无法隔离写入时串行；
- 个人审计稿和候选 PR 只作来源，不覆盖 ADR、TASKS、正式 Schema 或已合入代码。
