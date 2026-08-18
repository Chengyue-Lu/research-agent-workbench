# 模块 07：工件与溯源

## 1. 目标

以文件优先、稳定 ID、内容哈希和显式引用保存科研事实。工件层承担长期记忆；Agent 会话只承担临时工作。

## 2. 工作区分区

```text
projects/<project-id>/
├── protocol.yaml
├── sources/
│   ├── inbox/       # 可变隔离区，不可直接引用
│   └── raw/         # 已接纳原始字节 + sidecar manifest
├── objects/
│   ├── questions/
│   ├── hypotheses/
│   ├── methods/
│   ├── evidence/
│   ├── claims/
│   └── decisions/
├── tasks/
├── work/<task>/<attempt>/
│   ├── TASK.yaml             # 本 Attempt 使用的冻结 Task
│   ├── INDEX.yaml            # 默认可读的元数据索引
│   ├── ACTORS.yaml           # actor_id → 实名责任人/运行身份
│   ├── events.jsonl          # 顺序事件账本；读取/工具/文件/状态
│   ├── messages/             # Agent 间实际传递的可见内容
│   ├── tool-events/          # 瞬时或较长工具请求/结果正文
│   ├── handoffs/             # H1/H2 回传和接收决定
│   ├── decisions/            # 范围、接受、拒绝与升级决定
│   ├── checks/               # 验证报告与关键工具收据
│   ├── outputs/              # 尚未 promotion 的过程产物
│   ├── snapshots/            # 必要的上下文/运行快照
│   └── WORKLOG.md            # 从上述记录提炼的导航摘要
├── runs/<run-id>/
├── checks/
├── indexes/
├── deliverables/
│   ├── candidates/
│   └── accepted/
└── archive/
```

阶段视图可以生成，但物理存储按工件类别和生命周期组织，避免移动目录破坏身份。

Attempt Archive 是一次 Agent 协作的完整过程边界。正式 Evidence、Claim、Run 等仍提升到稳定对象区；Archive 保留它们在产生、审查和交接时的路径、哈希和消息/工具关系。旧项目若保留顶层 `handoffs/`，可作为正式 Handoff 索引，但新内容的原始副本应归入对应 Attempt。

## 3. Agent Trace 与消息信封

所有 Agent 间实际可见的传递都必须归档，包括 Assignment、澄清问题/回答、读取范围申请/批准、进度、Handoff、review、接受/拒绝、确认、错误、取消与安全暂停。Worklog 不能替代这些正文。

消息文件按发送顺序命名，例如：

```text
messages/0001-main-agent-to-mode-reviewer-assignment.md
messages/0002-mode-reviewer-to-main-agent-read-scope-request.md
messages/0003-main-agent-to-mode-reviewer-scope-decision.md
messages/0004-mode-reviewer-to-main-agent-handoff.md
```

每个文件使用可机器解析的头部并保存当时实际发送的可见 payload：

```yaml
---
message_id: MSG-0004
task_id: MODE-001
attempt_id: A-001
sequence: 4
kind: handoff
sender_actor_id: mode-reviewer
receiver_actor_ids: [main-agent]
accountable_owner: 路诚钺
created_at: 2026-08-14T10:30:00+08:00
in_reply_to: MSG-0003
content_sha256: "..."
attachment_refs:
  - path: work/MODE-001/A-001/outputs/mode-card.yaml
    sha256: "..."
redactions: []
capture_status: complete
---
<实际传递的正文；若只发送引用，就保存引用而不复制附件正文>
```

当前 `0.1.0` Trace Envelope 把 actor 表直接保存在 `TRACE.yaml`；未来如拆出
`ACTORS.yaml`，它只能是 Envelope 的哈希引用，不能形成第二个责任来源。actor 记录包含
`actor_id`、角色、模型/Runtime 快照和 `accountable_owner`。人类负责人必须使用姓名；临时窗口、
模型版本和 Agent Profile 是运行身份，不是审批主体。

发送方应先持久化消息再 dispatch；接收方应在基于消息继续行动前完成接收记录。平台不支持写前捕获时，Adapter 必须尽快导出并在 `capture_status` 标记 `delayed`。丢失、截断、政策性删减或平台不可导出时，写 `capture-gap` 事件，说明受影响的 message range、原因和可用定位信息，不能静默假装完整。

`INDEX.yaml` 只保存 actor、消息 ID、kind、时间、状态、哈希、附件引用和 Handoff/Decision 关系，不复制消息正文。Agent 默认可用索引发现记录，但只有 Task 明确引用的消息正文进入读取允许集。完整 Trace 主要供排障、审计和对照评估，不回灌主上下文。

### 可观察操作账本

`events.jsonl` 以单调 sequence 记录运行时能够观察到的动作：

- 文件/文档读取：actor、路径、revision/hash、读取范围、是否仅看元数据、允许集依据；
- 工具或命令：工具名、脱敏参数、开始/结束时间、状态、exit/error、结果正文或不可变 result ref；
- 文件写入：路径、旧/新哈希、revision、创建/修改/删除；
- 外部动作：目标类别、授权依据、副作用状态和 Receipt；
- Attempt 状态：开始、暂停、恢复、失败、完成与 capture gap。

如果源文件已经不可变且有哈希，读取事件引用它即可，不复制正文；如果工具结果只存在于瞬时 stdout/API response 且进入过 Agent 上下文，应将脱敏后的实际结果保存在 `tool-events/`。过程产物不原地覆盖：新版本使用新路径/revision；确需删除时事件账本保存 tombstone、旧哈希、责任人和原因。

该账本用于确认 Agent 是否越界读取或执行，而不是要求主 Agent 浏览全部操作。当前已实现的
validator 使用 Envelope 中的 `read_allowlist`、`write_scope`、`allowed_tools` 和
`external_actions` 检查边界；人工只在排障 Task 中按 event ID 调取请求/结果正文。

### 当前 `0.1.0` 可执行契约

- [`agent-trace-envelope.schema.json`](../../schemas/v0.1.0/agent-trace-envelope.schema.json)：
  冻结 Attempt 身份、实名 owner、actors、读写/Tool/外部动作边界、capture policy 及 Index/ledger 引用；
- [`agent-trace-index.schema.json`](../../schemas/v0.1.0/agent-trace-index.schema.json)：
  只保留 event/message 元数据、哈希和 Handoff/Decision 引用，不复制正文；
- [`agent-trace-event.schema.json`](../../schemas/v0.1.0/agent-trace-event.schema.json)：
  保存运行时可观察事件；`details` 是受控扩展槽，不改变事件身份、授权或引用字段；
- [`examples/agent-trace/valid`](../../examples/agent-trace/valid)：
  一个手工 H1 fixture，演示消息写前留存、读取、Tool 请求/瞬时结果、过程输出与 Handoff；
- `rwb trace validate <TRACE.yaml> --root <project-root>`：验证 Schema、引用哈希、连续顺序、
  actor/owner、读写与 Tool 边界、消息收发覆盖、捕获声明、瞬时结果和过程文件 revision。

验证器只判断档案是否自洽、边界是否可审计；它不证明运行时没有漏报、消息在网络上真的被接收，
也不判断研究内容正确。自动捕获属于执行 Adapter，当前 fixture 只证明 provider-neutral 文件契约。

## 4. 原始来源接纳

`sources/inbox` 中的内容默认不可信、可变且不可引用。接纳到 `sources/raw` 时记录：

- 原始文件名与接纳路径；
- SHA-256；
- 获取时间和来源 URI/DOI/设备/操作者；
- 许可证或数据使用边界；
- 解析器版本；
- 敏感性与外传限制；
- 与衍生文本、图表、OCR 的 provenance 关系。

网页、API 返回和数据库查询也需要快照或可复现 locator；只保存 URL 不足以保证来源未变化。

## 5. Run Manifest

每个实验、仿真、统计分析、检索批次或证明检查记录：

```yaml
run_id: RUN-0042
method_ref: M-SIM-002@3
input_refs:
  - ref: code/model.py
    sha256: "..."
parameters_ref: runs/RUN-0042/params.yaml
environment:
  platform: windows
  runtime: python-3.12
  lock_ref: uv.lock
agent_execution:
  task_ref: tasks/SIM-007.yaml
  profile_ref: simulation-auditor@0.1.0
  skill_assignment_ref: assignments/SA-0043.yaml
status: completed
outputs:
  - path: runs/RUN-0042/metrics.csv
    sha256: "..."
limitations: []
```

模型输出和 Agent 输出都只是工件，必须经过后续 Claim 关系与决策。

## 6. 提升与冻结

- 子 Agent 先写 `work/<TASK>/<ATTEMPT>`；
- 校验通过后由 promotion 操作复制/登记到正式区；
- accepted deliverable 不原地覆盖；
- 发布是 accepted 工件的明确子集，并需要独立 Decision；
- archive 表示保留但不活跃，不等于可删除；
- 垃圾回收不进入首版。

Agent Trace 随 Attempt 冻结。promotion 只引用所需消息、Decision 或输出，不把整个 Archive 复制到正式对象，也不删除失败、拒绝或未采用路径。

## 7. 大文件与保留策略

首版只用 Git 管理文本、Schema、索引和小型工件。出现真实大数据或模型文件后再选择：

- DVC：文件型数据版本与可复现 pipeline；
- MLflow：确有服务器型实验追踪和模型管理需求时；
- 外部对象存储：配合不可变 manifest 与访问策略。

不得为兼容未来可能的大数据，在 M1 自建 CAS、远程对象存储或复杂引用计数。

Trace 默认保存在项目工作区，但不等于默认提交 Git：

- 小型、脱敏的测试 fixture 和契约样例可以版本化；
- 真实运行的完整消息、工具输出和敏感材料按 Project Protocol 设置位置、访问权和保留期限；
- 大正文通过不可变路径与哈希引用，避免在消息、Handoff 和输出区重复复制；
- event ledger 保留操作元数据，瞬时结果放在 `tool-events/`；已有不可变来源时不制造第二份正文；
- 到期清理必须先保留索引、必要 provenance 和删除 Decision；首版不自动清理。

## 8. 数据安全

- 数据边界随 Project Protocol 和 Task Packet 传递；
- Tool/Skill 不能隐式上传本地材料；
- 外部 API 输入必须形成可审查清单；
- 敏感数据的摘要也可能泄露，不能因为“只是 Handoff”而放宽；
- 外部来源中的提示文本视为数据，不视为指令；
- 日志和 trace 中不得无意保留密钥、私人数据或受限原文。
- 不保存隐藏 Chain-of-Thought；保存的是实际跨 Agent 发送的可见内容、决策和正式过程工件；
- 对认证头、密钥、个人数据或政策禁止留存内容进行删减时，保留 redaction/omission 类型和原因，不保存被删值；
- 完整 Trace 的可见性不得高于其中最敏感输入的边界。

## 9. 预警

- `ARTIFACT-HASH-MISMATCH`
- `ARTIFACT-UNVERSIONED-REF`
- `ARTIFACT-INBOX-CITED`
- `ARTIFACT-OVERWRITE`
- `ARTIFACT-MISSING-PROVENANCE`
- `ARTIFACT-NEGATIVE-DROPPED`
- `ARTIFACT-PROMOTION-BYPASS`
- `DATA-BOUNDARY`
- `SOURCE-INJECTION`
- `REPRO-GAP`
- `TRACE-MESSAGE-MISSING`
- `TRACE-SEQUENCE-GAP`
- `TRACE-ACTOR-UNOWNED`
- `TRACE-HASH-MISMATCH`
- `TRACE-CAPTURE-DELAYED`
- `TRACE-REDACTION-UNDECLARED`
- `TRACE-READ-OUTSIDE-SCOPE`
- `TRACE-EVENT-MISSING`
- `TRACE-TRANSIENT-RESULT-MISSING`
- `TRACE-PROCESS-ARTIFACT-OVERWRITTEN`

## 10. 验收条件

- 任一正式 Evidence 和 Run 可定位到不可变输入或快照；
- 路径调整不破坏逻辑 ID 与内容引用；
- 失败和负结果不会因 promotion 被过滤掉；
- 子 Agent无权直接覆盖 accepted 工件；
- 外部发送的数据有清单和授权；
- 一个 Run 可在没有原 Agent 会话的情况下理解与重建；
- 任一跨 Agent Handoff 能定位到发送前后的消息、actor、附件和接收决定；
- 能从 event ledger 核对每个 Agent 实际读取的正文与执行的工具是否在 Task 边界内；
- 未采用的中间产物、失败与覆盖尝试仍可沿 revision/tombstone 定位；
- Worklog 缺失不导致 Trace 消失，Trace 很长也不要求主 Agent 默认加载；
- capture gap、删减和延迟会显式暴露，不能被误报为完整记录。
