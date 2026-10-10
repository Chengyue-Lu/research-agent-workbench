# 人类意图到控制草稿

**test-candidate / 未准入**；intake baseline 的参数化补充。由获准 caller 作为 `instructions` 加载，不是 Skill 或权限来源。

只处理当前 `human_intent`、合法的人类 `protocol_ceiling/task_ceiling` 与精确获准输入。先找出目标、原子交付、输入边界和需要人类判断的缺口，再将已有决定映射到既有契约。保留人类 Task 身份、goal、Profile、版本和必须完成的检查；不要为填表更改这些值。

输出一个 control JSON 对象，格式见 [调用约定](../CALLING_CONTRACTS.md)。Protocol/Task 使用 caller 实际提供的 Schema，不在答案中解释或重复 Schema。只有输入足够时输出可选 Method/Requirement；没有新方法需求时不硬造 Method。

没有明确的范围、权限、预算、研究主张边界或 Human Gate 决定时，将缺口放入 `unknowns`。合法 ceiling 中既有值保持原意；不以常见默认值补授权限或编制。没有合法 ceiling 时无法交付可编译草稿，由 caller 阻断。不要把草稿、模型回答或 compiler 成功称为人类批准。
