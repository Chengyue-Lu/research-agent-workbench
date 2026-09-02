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
schema_version: 0.1.0
message_id: MSG-0004
task_id: MODE-001
task_revision: 1
attempt_id: A-001
sequence: 4
kind: handoff
sender_actor_id: mode-reviewer
receiver_actor_ids: [main-agent]
accountable_owner: 路诚钺
created_at: "2026-08-14T10:30:00+08:00"
in_reply_to: MSG-0003
content_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
attachment_refs:
  - path: work/MODE-001/A-001/outputs/mode-card.yaml
    sha256: "0000000000000000000000000000000000000000000000000000000000000000"
redactions: []
capture_status: complete
---
<实际传递的正文；若只发送引用，就保存引用而不复制附件正文>
```

`ACTORS.yaml` 记录 `actor_id`、角色、模型/Runtime 快照和 `accountable_owner`。人类负责人必须使用姓名；临时窗口、模型版本和 Agent Profile 是运行身份，不是审批主体。

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

该账本用于确认 Agent 是否越界读取或执行，而不是要求主 Agent 浏览全部操作。validator 应能用 `read_allowlist` 检测越界；人工只在排障 Task 中按 event ID 调取请求/结果正文。

### Execution Trace 与 Method Trace

Execution Trace 负责上述可观察执行/Archive 事实。M3-009 已实现独立的 ref-only Method Trace v0.1
candidate，用 exact refs 记录 applied Method Resolution、Mode、Action disposition、Research Attempt、
from-State、kernel Decision 和 typed path basis。两层通过稳定 ID 关联，不把方法解释塞进 Tool debug
字段，也不复制消息正文。

Method Trace 必须区分计划中的 selected Snapshot/View 与实际执行事实：Snapshot 不能冒充 actual
binding；若本 Attempt 没有 authoritative M11 `execution_trace_fact`，Trace 必须显式记录 per-Attempt
gap，不能声称 coverage complete。若存在 captured fact，它必须 exact-pin 同一 Attempt 的 actual
binding/Supply，并至少绑定一个 applied path 和 State effect。该 candidate 的确定性 closure 仍不证明
reviewer reconstruction 或科学正确性，最终语义保持 Human/R2 closeout 独立。

## 4. 原始来源接纳（M4-001 已实现）

`sources/inbox` 中的内容默认不可信、可变且不可引用。M4-001 的 `source_admission` sidecar 在接纳到
`sources/raw` 时记录：

- 原始文件名与接纳路径；
- SHA-256；
- 获取时间和来源 URI/DOI/设备/操作者；
- 许可证或数据使用边界；
- 解析器版本；
- 敏感性与外传限制；
- 与衍生文本、图表、OCR 的 provenance 关系。

`rwb source admit` 默认 dry-run，只有显式执行才写入，并拒绝覆盖既有 admitted bytes 或 sidecar。
`rwb source check` 与 repository validation 使用规范化的完整路径段判断 `sources/inbox` / `sources/raw`：
普通文档引用 raw bytes 时，必须存在同路径 `<raw-path>.admission.yaml`，其 Schema、`admitted_path` 和
SHA-256 必须与 live bytes 闭合；FileReference 自带 SHA 时还必须与 admission SHA 一致。`raw-copy`、
`inbox-old` 等相似前缀不构成分区命中。

这套 Gate 只证明 identity/hash/provenance closure，不判断来源真实性、许可证法律效力、内容安全或科学
质量。网页、API 返回和数据库查询也需要快照或可复现 locator；只保存 URL 不足以保证来源未变化。
M4-002 promotion 已作为独立层实现；M4-003 Claim trace 与 M4-004 Run reproduction 仍需各自完成，
M4-001 不替代任何后继层。

## 5. Run Manifest target（M4-004 尚未实现）

下面只展示未来 Run reproduction contract 需要保留的信息类别，不是已接受 Schema。每个实验、仿真、
统计分析、检索批次或证明检查最终应记录：

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
  resolved_execution_view_ref: execution/views/VIEW-SIM-007.yaml
status: completed
outputs:
  - path: runs/RUN-0042/metrics.csv
    sha256: "..."
limitations: []
```

Skill-bearing Run 可以额外引用 exact Assignment；no-Skill/direct Tool/procedure/Adapter 路径不得伪造该
字段。模型输出和 Agent 输出都只是工件，必须经过后续 Claim 关系与决策。

## 6. 提升与冻结（M4-002 已实现）

`promotion_record` 将 exact `work/<TASK>/<ATTEMPT>` 中 validation report 的全部 subjects 映射为
`promote` 或 `retain-in-work`。pre-Attempt canonical Task Packet 先 exact-pin 唯一 accepted-policy registry
与 policy，并把 actor write scope 收窄到该 workspace；registry 再按 Task revision 固定 checker、runner 与
validation host。host-bound execution fact 固定同一 Task/Attempt、Task/registry/policy、report、subjects、
执行者、时间和 outcome。Task → registry/policy → execution → PASS report → entries/live bytes 任一关系或
hash 漂移均阻断；调用方即使在允许稳定目录内构造一套自洽 checker/runner/policy/execution，也不能绕过
预先冻结的 Task inputs。

`rwb promotion validate` 只读检查；`rwb promotion execute` 只接受 workspace 内的 file-bound record，
先在目标目录 staging 完整字节并复算 hash，再做完整复验，并生成 exact-pin
record/Task/registry/policy/execution/report/checker/runner/host/source/actual-target/operator/time/outcome 的
Promotion Receipt。目标与 receipt 在 commit-time 再复验后
一起 exclusive-create。目标只允许位于 `objects/`、`runs/` 或
`deliverables/candidates/`；existing target、相似前缀、root/symlink escape 和
`deliverables/accepted/` 直达均 fail closed。中途冲突会回滚本次仍可确认的已创建目标，不覆盖正式
工件或 receipt，也不删除 work/archive。

Agent Trace 随 Attempt 冻结。promotion 只复制记录中明确选择的 exact bytes，不把整个 Archive 复制到
正式对象。结构 PASS 不产生 Claim acceptance、Human Decision、accepted publication 或科研质量判断；
详见 [M4-002 契约](../implementation/ARTIFACT_PROMOTION_CONTRACT.md)。

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

当前已实现的 M4-001 验收边界：

- `sources/inbox` 的完整路径段引用被阻断；
- 每个普通 `sources/raw` 引用可定位到 Schema-valid sidecar、exact admitted path 与当前 live-byte hash；
- FileReference/admission SHA 漂移、缺失或错误 sidecar 均 fail closed；
- admission PASS 不被解释为来源可信、许可合法或科学正确。

当前已实现的 M4-002 验收边界：

- pre-Attempt Task、accepted registry/policy、host-bound deterministic validation execution、PASS report、
  subjects、entries 与 live bytes exact closure，subject/entry 集合既不遗漏也不夹带；
- 每个受检工件均有 promote/retain disposition，负结果不会被静默删除；
- file-bound record、durable receipt、staging、commit-time 复验和 exclusive-create 阻断自签 PASS、覆盖、
  accepted 直达、路径逃逸及 record/source/target/receipt 竞态；
- promotion PASS 不被解释为 Claim、Human Decision、publication 或 scientific correctness。

当前 Agent/Method Trace 可追溯边界：

- 任一跨 Agent Handoff 能定位到发送前后的消息、actor、附件和接收决定；
- 能从 event ledger 核对每个 Agent 实际读取的正文与执行的工具是否在 Task 边界内；
- 未采用的中间产物、失败与覆盖尝试仍可沿 revision/tombstone 定位；
- Worklog 缺失不导致 Trace 消失，Trace 很长也不要求主 Agent 默认加载；
- capture gap、删减和延迟会显式暴露，不能被误报为完整记录。

以下仍是 M4-003～004 的 target acceptance，不能由 M4-001/002 的 DONE 状态代替：Claim trace 可一次
定位支持/反证/限制，以及 Run 可在没有原 Agent 会话时按 exact inputs/environment/execution facts 理解与
重建。
