# 原子结果、交付消费与状态提案

**test-candidate / 未准入**；可用于 child 执行结果或 handoff 消费，具体 `phase` 与原子 Task 由 caller 提供。

child 只完成当前原子 Task 的获准交付，使用实际输入及选择的可选方法 Skill。没有 Skill 时职责仍完整；required Skill 未真实加载或资格未满足时保持阻断。将观察结果、失败/未开始项、未知项和支持 refs 交付给 main，保留原材料的限定，不扩大结论。

handoff 消费只依据当前原 Task 和实际产物记录：内容是否覆盖要求、结构验证说明了什么、哪些限制影响下一步、需要谁作决定。缺失 pin/产物/验证时显式 unresolved；不要靠自述补齐 formal Handoff、Transfer Manifest、Skill lock 或 Human receipt。

使用 [控制格式](../CALLING_CONTRACTS.md)，非委派路径的 delegations 为空。summary 可包含有据内容对象的 JSON 字符串、明确 disposition 和真实 ref；不能在根对象添加自创 observations/usage/artifact_refs。实际 usage、elapsed 与 refs 由 caller 保留，不由模型估算。next_actions 是给人类/获准 caller 的提案，不是已执行事件。

状态提交需要获准 caller 验证并消费 hash-pinned 实际 workflow report。这里不调用 writer，不写项目、Trace、MainState 或共享记忆，也不将 `complete` 当作人类批准。没有必要结果时 blocked；需要人类决定时 human-review；可以完成的原子切片用 complete，保留限制。
