# Protocol 到 Task 与方法配置

**test-candidate / 未准入**；用于已有约束的 intake 配置变体，可与 [control-intake](control-intake.md) 组合。组合后仍只返回一个 control JSON。

以 supplied Protocol、完整人类 Task ceiling、获准 Mode/Action/Profile 文档为输入。把当前目标拆成一个明确的原子交付边界；执行拆并由后续 main 和获准 caller 决定，本草稿不固定 agent 数量。保持 Protocol 的 claim ceiling、Human gates、数据边界和上下文政策；Task 范围、权限、预算、委派边界只能保持或收窄。

仅在确有方法配置需求、必要 Mode/Action 依据齐全时提供 Method。每项 obligation 说明所需证据及 deterministic / semantic-review / human-decision / unavailable 的适用判断，选择已有可用机制；缺方法输入或决定时在 `unknowns`/既有 blocked 字段记录。版本化 Mode/Action refs 来自真实获准文档；不虚构 Registry release、Action hash、Skill lock 或供应资格。Method 的 Task hash 交给 compiler。

Requirement 描述所需输入、输出、artifact、权限/数据/副作用上限和验证期待，不选 Supply、provider 或执行资源。没有 Supply 时 demand 不变，下一步仍是 capability-resolution；Schema 合法不等于 Supply satisfied 或 Runtime admission。

输出格式、可选字段和 compiler 边界见 [调用约定](../CALLING_CONTRACTS.md)。不要新增控制字段或 coreRole。
