# Method Resolution Contract

状态：Active implementation contract

## 1. 目的与身份

Method Resolution 是一个按 Task 产生、可序列化和归档的方法决定工件。它回答：

> 对当前 Task，哪些 Mode/Action 适用，需要履行什么义务，最小充分机制是什么，哪些替代路径被拒绝？

身份由 `resolution_id + revision` 构成，Schema 为
`schemas/v0.1.0/method-resolution.schema.json`。Resolution 是按 Task 修订的决定，不是可自动发现的
全局 catalog，因此本节点不建立 Method Resolution Registry。

## 2. 正式内容

每个 Resolution 必须包含：

- `task_ref.task_id + revision + sha256`，且必须解析到实际 TaskPacket 原始字节；可选 `source_case_id`
  只记录诊断来源，不充当 Task identity；
- selected / no-new / ambiguous-blocked Mode 结果；
- 正式 `action_ref + action_content_hash`，或明确的 planning action；
- 每个 action decision 的方法义务、assessment 类别和所需 Evidence；
- 最小机制：Mode invariant、Task instruction/template、Tool、no-Skill、Skill Need、Human Gate、
  blocked 或 split Task；
- Skill disposition、Human Gate 和 blocked condition 闭集；
- 至少一个 rejected/deferred/blocked alternative；
- `proceed / blocked / split-and-block` 状态与限制。

`Skill Need` 不是 Skill Assignment；`no-skill` 是正式结果。Resolution 不含 Provider、Model、Host、
Runtime、Adapter、MCP 或具体 Tool/Skill binding。

Skill 是否已有实现、Capability snapshot 中是否 available，属于后续 Capability Resolution 的 supply-side
判断。Method Resolution 只声明稳定的 Need/Capability Requirement；即使尚无实现，Method 层仍可为
`proceed`，不能使用 `need-not-implemented` 或 `capability-gap` 偷渡供应状态。

## 3. 八个正式示例

`examples/method-resolution-tasks/` 与 `examples/method-resolutions/` 保存八组 synthetic bounded
TaskPacket 和独立 Resolution。历史诊断 suite
`examples/mode-skill-routing/mode-action-routing-v1.yaml.txt` 为每个 case 保存 Resolution 的
repository-relative path、Task path 与两者 SHA-256，形成 `diagnostic case → Task → Method Resolution`；
suite 本身仍不是 Runtime Resolver 或全局 Registry。

## 4. 确定性验证

项目验证会检查：

- Resolution 符合 Schema，identity/decision/obligation/alternative ID 不重复；
- selected Mode 引用已加载的正式 Mode；
- `task_ref` 的 ID/revision/hash 与实际 TaskPacket 完全一致；
- formal Action 引用存在，hash 与 Mode Action Registry 完全一致，且 Action.mode_ref 属于 selected Mode；
- Action `human_gates` 只能保留或追加，不能删除/换名；Action required artifacts 必须被 obligation
  evidence plan 覆盖；Action stop/blocked conditions 必须保留；Resolution 不能重定义 Action claim effects；
- Skill Need、Human Gate 和 blocked condition 顶层集合与 action decisions 精确闭合；
- no-Skill 与 Skill Need 不会生成或引用 Assignment；
- planning action 不能同时伪装成 formal Action。

这些检查不判断 Action/Mode 是否科学适用，不批准义务是否在语义上完成，也不把 Human Gate 变成
机器批准。`assessment` 只标识需要 deterministic、semantic review、human decision 或当前 unavailable，
不在 Resolution 内嵌批准语义。actor/operation 权威由独立的
[Authority Rule Eligibility](DECISION_AUTHORITY.md) 判断，Resolution 中的 Gate ref 仍是
opaque ID。

## 5. 状态与下游边界

- `proceed`：Method 层允许进入后续 Capability/Execution 解析，不表示 Task 已完成；
- `blocked`：当前 Task 不具备合法方法/能力/权限路径；
- `split-and-block`：只允许重新签发的有界子 Task 继续，受影响部分保持阻断。

Method Resolution 不等于 Resolved Execution View，不选择 Agent/Profile、权限交集、Tool endpoint、
Provider 或 Model，也不创建 Attempt、Receipt 或 Trace。上述接口必须由后续独立 Task 消费当前阶段
契约，不能通过本契约的字段扩张提前实现。
