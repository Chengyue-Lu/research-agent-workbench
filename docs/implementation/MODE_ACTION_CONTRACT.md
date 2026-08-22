# Mode Action Contract and Registry

状态：Active implementation contract

## 1. 权威工件

- Schema：`schemas/v0.1.0/mode-action.schema.json`；
- Registry Schema：`schemas/v0.1.0/mode-action-registry.schema.json`；
- Action documents：`registry/modes/actions/<mode>/<action-id>.yaml`；
- hash-pinned index：`registry/modes/actions.json`。

设计来源保留在历史 workstream，但不再是 Action 字段或身份的唯一真值。

## 2. 身份与引用

Action 的逻辑引用是 `action_id@version`。需要冻结一个具体 Method 或 Attempt 时，消费者同时保存
Registry 的 `content_hash`；hash 计算对象是 Action 文档原始文件字节，不把哈希嵌回文档造成循环。

`mode_ref` 使用 `mode-id@version`，明确 Action 属于哪一个正式 Mode revision。Action version 变化不
自动升级 Mode、Task、Method Resolution 或历史 fixture；消费者必须显式采用新版本。

## 3. 语义边界

Action 声明 trigger/non-trigger、failure、artifact、Claim effect、Human Gate、stop 和 blocked。
它回答“在这个 Mode 下，哪一个原子研究动作需要被约束”，不回答由哪个 Skill、Tool、Agent、模型、
Provider 或 Runtime 执行。`human_gates` 只引用 Gate 身份，不定义批准结果、作用域或持续性。

## 4. 确定性验证

加载 Action Registry 时，`rwb validate` 检查：

- Action 文档符合 Schema，ID/version 不重复；
- `mode_ref` 指向已加载的正式 Research Mode；
- Registry entry 与 Action 的 ID、version、mode、路径和文件 SHA-256 一致；
- Registry 与 Action documents 构成闭集，不允许 missing、orphan 或 hash drift；
- routing fixture 的正式 `action_ref` 可解析到 hash-pinned entry（由 fixture test 固定）。

这些检查只证明契约与引用完整，不证明 Action 适用于某个真实研究 Task。

## 5. 非目标

- 不定义 Method Resolution 或 rejected alternatives；
- 不迁移 Research Mode v0.1；
- 不创建 Skill Need、Skill Assignment 或 Tool binding；
- 不定义 Human Gate decision vocabulary；
- 不记录 Method Trace，也不改变 API / Runtime 执行。
