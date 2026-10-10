# 候选资产调用约定

状态：**test-candidate / 未准入**。本文只描述 PR140 已有接口与资产装配建议。不存在新 coreRole、固定编制、自动状态提交或 Skill Release。

源接口：[roles.py](../../../../../../src/research_workbench/entry/roles.py)、[intake.py](../../../../../../src/research_workbench/entry/intake.py)、[guide.py](../../../../../../src/research_workbench/entry/guide.py)。对象格式由既有 [Protocol](../../../../../../schemas/v0.1.0/project-protocol.schema.json)、[Task](../../../../../../schemas/v0.1.0/task-packet.schema.json)、[Method](../../../../../../schemas/v0.1.0/method-resolution.schema.json)、[Requirement](../../../../../../schemas/v0.1.0/capability-requirement.schema.json)、[MainState](../../../../../../schemas/v0.1.0/main-state.schema.json) Schema 决定。

可直接使用的 public signatures：

```python
build_role_request(root, *, role, task, profile, model, input_refs=(),
                   tools=(), max_output_tokens=1024, instructions=None,
                   context=None, data_policy=None) -> ModelRequest
compile_control_draft(root, *, response, protocol_ceiling, task_ceiling,
                      schema_catalog=None) -> ControlDraft
persist_control_draft(root, *, directory, draft) -> tuple[FileReference, ...]
build_guide_request(root, *, question, main_state_ref, approved_refs=(),
                    model, max_output_tokens=1024, data_policy=None) -> ModelRequest
ask_guide(root, *, providers, provider_name, question, main_state_ref,
          approved_refs=(), model, max_output_tokens=1024,
          data_policy=None) -> ModelResponse
```

上述 `1024` 是已有函数默认值，不是本轮规定的预算。Root 应按每个测试 Task 的实际授权值显式传入。`tools` 空值不会自动要求某个 Skill；main 的 `delegations=[]` 是合法路径。

非 Guide 装配顺序为：现有 system baseline 必载；所选角色变体作为 `instructions`；可选 Skill 文本与精确材料 refs 由获准 caller 装配；`context` 只包含明确当前输入及实际调用产生的结果。`instructions/context` 位于 user JSON payload，不取代 system baseline。Root 必须在实际 request 记录所选资产路径、实际加载字节的 SHA256 与 message 位置；仅把路径写入 Task 或索引不能证明文本已加载。

建议的 caller 数据参数：intake 使用 `human_intent`、`protocol_ceiling`、`task_ceiling`、获准 `mode/action/profile` 文档；main 使用 `phase`、剩余全链路限制、实际 `child_results`；child/handoff 使用原子 Task、实际 `result_refs`、失败/未知项与消费目的。这些是建议的 payload 键，不是新增持久化 Schema。模型只消费获准内容，不能用参数扩大授权。输入文件须进入 Task 的精确 `input_refs` 并由 Root pin；不得目录扫描或自动追随文件内链接。

Intake 返回且只返回一个 JSON 对象：

```text
{protocol: <既有 Project Protocol>, task: <既有 Task Packet>,
 method?: <既有 Method Resolution>, requirements?: [<既有 Requirement>],
 unknowns: [string]}
```

`protocol/task/unknowns` 必需。没有 Method/Requirement 的合法必要输入时省略对应可选项并记录 unknown。`compile_control_draft` 校验完整人类 ceilings；若没有合法 ceilings，caller 在调用/编译前阻断，prompt 不能补授权限。Method 的 `task_ref.task_id/revision` 必须对应 Task；`task_ref.sha256` 由 compiler 补齐或替换，模型不得编造。`persist_control_draft` 仅写新的独占目录，结果仍为 draft，不是 approved/runtime-execution。Method/Requirement 的 Schema 合法也不证明 Supply、Registry、Runtime closure。

main/child/handoff 的控制输出使用同一个 caller 内部格式：

```text
{decision: "complete" | "delegate" | "blocked" | "human-review",
 delegations: [{task: <既有 Task Packet>}],
 summary: string, limitations: [string], next_actions: [string]}
```

这是说明格式的类型记法，不是可提交的 JSON 实例。实际输出必须合法 JSON、无 Markdown fence、无额外根字段。没有实际委派提案时用空数组。可选摘要/写作 Skill 的内容对象可 JSON 编码到 `summary` 字符串或由 caller 用获准 artifact writer 保存，再提供真实 ref；不得为适配 Skill 改控制根字段或捏造 artifact refs。当前 PR140 `build_role_request` 对非空 `required_skills` 明确阻断；读取 test-candidate 文件只证明 caller 文本装配，不能冒称正式 required Skill 支持。若以后走正式 required Skill 路径，需真实身份/版本/lock/loader/资格证据，失败保持阻断。

`complete` 表示当前执行切片结束。main 对实际子结果作 accept-for-next-step / revision-needed / unresolved 等语义 disposition，可写入 `summary/limitations/next_actions`；它不是 Human Gate 接纳，也不触发 checkpoint。状态提交必须由获准 caller 对 hash-pinned 实际 workflow report 验证后发起。实际 usage、elapsed、turns、refs、报告 hash 来自运行记录，不能从模型文字推定。

Guide 只走专用接口；其输入为一个 pinned MainState 与显式获准必要 refs，不消费 main 历史、通用 `context` 或 workflow 累积消息。PR140 没有加载外部 Guide prompt 的参数，generic Guide 又禁止 `instructions/context`；[Guide 候选](prompts/guide-read-only.md) 是后续有界 seam 的设计文本，当前只能验证内置 baseline。把候选作为 `approved_ref` 只能让它成为数据，不能升级为职责指令。Guide 输出是向人类的解释，返回实际 response/usage，零 Tool、零 project/Trace/state 写入，也不自动回传 main；显式人类采纳后才由研究链 caller 选择新输入。

关闭任一可选 Skill 后仍保留相应角色 baseline、Task/权限/预算/输出检查。关闭某个角色变体不移除内置职责。缺必要输入、权限、资格或预算时记录 blocked/unknown，不让候选文本变成授权来源。
