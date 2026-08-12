# 模块 06：上下文治理

## 1. 目标

把上下文当作受预算约束的决策空间，而不是被动依赖平台压缩的无限日志。主 Agent 优先保持连续判断能力；子 Agent 的局部历史可以被压缩或丢弃，但正式工件与交接不能受损。

## 2. 三类上下文

### Main Context

用于需求、约束、决定、冲突和下一步行动。必须小、可轮换、可由 Main State 恢复。

### Task Context

用于一个窄任务。由 Task Packet、Agent Profile、Skill Assignment 和必要输入组成；任务结束后关闭。

### Artifact Context

长期存在于文件、数据、运行记录和索引中。按引用拉取，不随聊天完整推送。

## 3. 主上下文分区

| 分区 | 内容 | 目标 |
|---|---|---|
| Pinned | 问题、不可破坏约束、Claim ceiling、关键决定 | 始终可见，尽量短 |
| Active | 当前一步所需输入与推理 | 完成后卸载 |
| Recent Handoffs | 待合并结果、冲突、Human Gate | 只保留短摘要与 refs |
| Reserve | 用户新指令、异常、复杂判断余量 | 必须主动留白 |

不将具体百分比写死为平台真值。首版用代理指标估计压力：累计读取字符、最近 Handoff 数、未关闭问题数、长工具输出次数、线程持续回合、平台压缩预警以及主 Agent 自检。

当前实现使用 `Context Snapshot` 把每个指标标记为“已测量”或“未知”。缺失数据不能自动填零；字符数只用于本地压力比较，不换算成假精确的 token 余量。默认阈值可由 Project Protocol 覆盖，并随 Snapshot 一起冻结，避免事后改变解释。

## 4. Main State Packet

```yaml
schema_version: 0.1.0
checkpoint_id: MS-0018
project_protocol_ref: protocol.yaml@4
current_questions: [Q-001@3]
pinned_constraints:
  - local data must not be uploaded
  - claim ceiling is simulation_supported
accepted_decisions: [D-003, D-004]
active_tasks:
  - task_id: SIM-007
    status: running
    expected_handoff: handoffs/SIM-007.yaml
recent_handoffs:
  - ref: handoffs/EVID-002.yaml
    disposition: accepted-with-limitations
open_conflicts: [C-002]
open_risks: [CTX-MAIN-PRESSURE, REPRO-GAP]
next_actions:
  - wait for SIM-007
  - ask human to accept model boundary
artifact_index_refs:
  - indexes/current-claims.yaml
rollover_reason: approaching soft context budget
```

Main State 是恢复入口，不是第二套数据库。它只引用正式工件，不复制原始内容。

当前 Main State 还可携带 `created_at`、`previous_checkpoint_ref`、`context_snapshot_ref` 和规范化 `checkpoint_digest`。`rwb context resume-check` 会验证协议 revision、引用、下一动作、活动 Task 的预期 Handoff，以及相邻 checkpoint 是否丢失已固定约束或决定。

## 5. 主动 checkpoint 与 rollover

在以下边界写 checkpoint：

- Project Protocol 变更后；
- 一组 Handoff 合并后；
- Human Decision 后；
- 进入新研究模式前；
- 上下文压力进入 WARN；
- 计划等待长任务或结束当前会话前。

rollover 步骤：

1. 关闭或明确标记全部 active Task；
2. 验证最近 Handoff 和工件引用；
3. 写 Main State；
4. 运行 deterministic resume check；
5. 新主会话只加载 Project Protocol、最新 Main State 和下一动作；
6. 按需回查旧工件，不加载完整旧聊天。

目标是在平台自动压缩前主动换届。若仍发生自动压缩，应把它视为可恢复事故并记录，而不是正常依赖。

## 6. 子 Agent 压缩容忍条件

子 Agent 的上下文压缩只有同时满足以下条件才可接受：

- Task Packet 和 input lock 可重新读取；
- 已完成内容已写入正式或 attempt 工件；
- 尚未完成项明确列出；
- Facts、inferences、recommendations 已分离；
- Skill Assignment 和版本仍可定位；
- 关键中间参数、引用和负结果不只存在于对话；
- Handoff 可通过结构验证。

否则 Agent 必须在压缩/终止前输出 `incomplete` Handoff。不能仅凭“我记得主要结论”继续。

确定性规则区分两种情况：`scope: task`、发生过压缩且 `handoff_ready: true` 时，Context Snapshot 必须引用一份 Handoff Transfer Audit；Receipt 会重新检查其条目覆盖。低风险未做人类抽查时最多得到 `structurally-ready` 和可恢复警告；缺少 Audit、必需条目或关键语义抽查时阻断。主上下文发生任何非计划压缩仍触发 rollover，不使用同一宽容规则。

## 7. 按需拉取

主 Agent 读取顺序：

1. Main State / Project Protocol；
2. Handoff 摘要；
3. Evidence/Run/Claim 索引；
4. 具体工件片段；
5. 原始材料或日志，仅在争议仍无法解决时。

这避免把“可访问”误解为“应全部进入上下文”。

## 8. 隐藏风险与预警

| 代码 | 风险 | 处置 |
|---|---|---|
| CTX-MAIN-PRESSURE | 主上下文噪声增大 | checkpoint，卸载 Active，必要时 rollover |
| CTX-AUTO-COMPACTION | 平台发生非计划压缩 | 验证 Main State，记录事故，必要时新会话恢复 |
| CTX-HANDOFF-LOSS | 子 Agent 关键信息未固化 | BLOCK，要求 incomplete Handoff/补交工件 |
| CTX-SUMMARY-DISTORTION | 摘要改变限定条件 | 沿 refs 抽查，降低 Claim，修复 Handoff |
| CTX-STALE | 上下文引用旧 revision | BLOCK 合并，刷新输入 |
| CTX-RECALL-LOOP | 主 Agent频繁回读原始材料 | 重建索引或改进 Handoff，而非扩大上下文 |
| CTX-PINNED-GROWTH | Pinned 信息只增不减 | 人工/主 Agent清理已失效约束 |
| CTX-SKILL-POLLUTION | 加载不相关 Skills | 重新解析最小 Skill Assignment |
| CTX-HIDDEN-STATE | 决定只存在于对话 | 创建 Decision 工件 |
| CTX-RECOVERY-DRIFT | 新会话恢复后目标改变 | 对比 checkpoint 与下一动作，Human Gate |

## 9. 当前 CLI

```text
rwb context assess ...
rwb context checkpoint ...
rwb context resume-check ...
rwb handoff audit-transfer ...
```

`assess` 不读取聊天隐式状态，调用方必须传入可测代理指标；压缩后的 task 若声明 handoff-ready，还要传 `--handoff-audit-ref`。`checkpoint` 可以从上一 Main State 继承状态；`resume-check` 是换届门槛，不启动或管理新会话。

## 10. 不保存的内容

- 完整 Chain-of-Thought；
- 没有消费方的每轮自省；
- 为证明控制系统可靠而产生的控制系统日志洪流；
- 未经验证的自动摘要集合；
- 可以从源工件确定性重建的重复视图。

## 11. 验收条件

- 主 Agent 在不读取原始论文/日志的情况下恢复并继续下一步；
- 人工抽查能够从 Handoff 定位到原始 Evidence/Run；
- 自动压缩后不会丢失已固化事实和 Decision；
- 主 Agent非计划读取原始材料的频率随版本下降；
- Main State 保持小而稳定，不随项目历史线性增长；
- 子 Agent 结束后其会话可删除而不影响正式结果。
