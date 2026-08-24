# Mode Action Contract and Registry

状态：Active implementation contract

## 1. 权威工件

- Schema：`schemas/v0.1.0/mode-action.schema.json`；
- Registry Schema：`schemas/v0.1.0/mode-action-registry.schema.json`；
- legacy v0.1 Action documents：`registry/modes/actions/<mode>/<action-id>.yaml`；
- v0.2+ Action documents：`registry/modes/actions/<mode>/v<mode-version>/<action-id>.yaml`；
- hash-pinned index：`registry/modes/actions.json`。

设计来源保留在历史 workstream，但不再是 Action 字段或身份的唯一真值。

## 2. 身份与引用

Action 的逻辑引用是 `action_id@version`。需要冻结一个具体 Method 或 Attempt 时，消费者同时保存
Registry 的 `content_hash`；hash 计算对象是 Action 文档原始文件字节，不把哈希嵌回文档造成循环。

一旦 `action_id@version` 进入共享 Registry，该身份、`mode_ref`、路径和内容语义不可原位重写；
任何语义变化都必须发布新版本和新 Registry entry。Schema 声明这一不变量，Registry diff 的
append-only 检查属于合并边界治理；单次静态文档验证不能伪装成已经证明 Git 历史不可变。

`mode_ref` 使用 `mode-id@version`，明确 Action 属于哪一个正式 Mode revision。Action version 变化不
自动升级 Mode、Task、Method Resolution 或历史 fixture；消费者必须显式采用新版本。

因此 Research Mode 从 v0.1 升到 v0.2 时，即使 Action 的研究义务正文未改变，也要发布新的 Action
version，使其 `mode_ref` 精确指向 v0.2。v1/v2 Action documents 与 Registry entries 并存；这不是
实现绑定变化，而是 revision ownership 的可审计迁移。迁移记录见
[Research Mode migration](RESEARCH_MODE_MIGRATION.md)。

## 3. 语义边界

Action 声明 trigger/non-trigger、failure、artifact、Claim effect、Human Gate、stop 和 blocked。
它回答“在这个 Mode 下，哪一个原子研究动作需要被约束”，不回答由哪个 Skill、Tool、Agent、模型、
Provider 或 Runtime 执行。`claim_effects` 只使用 Research Object Schema 的 canonical Claim strength，
`may_support` 与 `cannot_alone_support` 不得重叠，且前者不能越过所属 Mode 的 `allows`。
`human_gates` 只保存受限格式的 opaque Gate ID，不定义决定、actor、作用域、持续性或批准词汇。
Action 不提供任意 `metadata` 扩展口，避免把 binding 或 authority 数据藏入未治理字段。

## 4. 确定性验证

加载 Action Registry 时，`rwb validate` 检查：

- Action 文档符合 Schema，ID/version 不重复；
- `mode_ref` 指向已加载的正式 Research Mode；
- Registry entry 与 Action 的 ID、version、mode、路径和文件 SHA-256 一致；
- Registry 与 Action documents 构成闭集，不允许 missing、orphan 或 hash drift；
- Claim strength canonical、effect sides disjoint，且 `may_support` 不越过 Mode claim rules；
- routing fixture 的正式 `action_ref` 可解析到 hash-pinned entry（由 fixture test 固定）。

这些检查只证明契约与引用完整，不证明 Action 适用于某个真实研究 Task。

## 5. 非目标

- 不定义 Method Resolution 或 rejected alternatives；
- 不由 Action 契约本身迁移 Research Mode；迁移由独立、具名的 migration seam 负责；
- 不创建 Skill Need、Skill Assignment 或 Tool binding；
- 不定义 Human Gate decision vocabulary；
- 不在 Action metadata 中扩展实现绑定或权威语义；
- 不记录 Method Trace，也不改变 API / Runtime 执行。
