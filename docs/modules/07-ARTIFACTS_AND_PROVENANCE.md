# 模块 07：工件与溯源

## 1. 目标

以文件优先、稳定 ID、内容哈希和显式引用保存科研事实。工件层承担长期记忆；Agent 会话只承担临时工作。

接点：执行者在 work 区产出有界工件，Trace recorder 保存实际传递与可观察事件；来源接纳、验证和
promotion producer 各自产出 sidecar/report/receipt，由 Evidence/Claim 定位器、Handoff、审计与 Human
消费。研究任务需要来源、正式工件复制、主张回查或 Run 重建时才启用对应外环；普通入口接通不强制
创建全部科研对象。既有材料仍按相同来源、版本和资格规则接入。

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

Execution Trace 负责上述可观察执行/Archive 事实。独立的 ref-only Method Trace
candidate，用 exact refs 记录 applied Method Resolution、Mode、Action disposition、Research Attempt、
from-State、kernel Decision 和 typed path basis。两层通过稳定 ID 关联，不把方法解释塞进 Tool debug
字段，也不复制消息正文。

Method Trace 必须区分计划中的 selected Snapshot/View 与实际执行事实：Snapshot 不能冒充 actual
binding；若本 Attempt 没有 authoritative `execution_trace_fact`，Trace 必须显式记录 per-Attempt
gap，不能声称 coverage complete。若存在 captured fact，它必须 exact-pin 同一 Attempt 的 actual
binding/Supply，并至少绑定一个 applied path 和 State effect。该 candidate 的确定性 closure 仍不证明
reviewer reconstruction 或科学正确性，最终语义保持 Human/R2 closeout 独立。

## 4. 原始来源接纳

`sources/inbox` 中的内容默认不可信、可变且不可引用。`source_admission` sidecar 在接纳到
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
source admission、promotion、Claim localization 与 Run reproduction 各自承担独立验收；任何一层不替代
后继层。Claim localization 的实现覆盖由 STATUS 维护。

### Claim evidence localization

`rwb claim trace --evidence-map` 通过显式 ObjectRef/FileRef 连接支持、反证与实际工件；raw 来源消费
admission sidecar，晋升或保留的产物消费 Promotion Receipt 与原 record。限制原文定位到 Claim 文件的
JSON pointer。读取复用同次调用捕获的字节，不启动 checker、promotion 或科学计算，也不决定 Claim
是否成立。详见 [Claim localization 契约](../implementation/CLAIM_TRACE_CONTRACT.md)。

## 5. Run reconstruction

`run_reconstruction_manifest` exact-pin 一个 Run 文档、单文件 Python 程序、输入、参数、环境定义及
预期输出。`run_ref` 关闭现有 Run 的对象身份与 revision；`input_bindings`、`environment_binding` 和
各输出的 `object_ref` 将 Run 的输入、环境、输出 ObjectRef 与对应 FileRef 精确映射，检查完整集合、
revision 和已声明的对象哈希。对象哈希仍表达原有 `content_hash` 语义，实际文件字节独立由 FileRef
校验，不改变 Run/Claim 核心权限。
输入绑定必须各声明一次 `role: input` 和 `role: parameters`，其 FileRef 分别匹配实际执行的
`input_ref` 和 `parameters_ref`；仅交换绑定顺序不影响配对，交换文件则拒绝。

`rwb run check MANIFEST --root ROOT` 只验证 Schema、文件哈希和来源边界，不执行代码。
`rwb run reproduce MANIFEST --root ROOT --attempt-dir work/RUN-DEMO/A-NEW` 将锁定字节复制到新目录，
用当前且符合环境定义的 Python 执行固定文件入口：

```text
python -I -S program.py inputs.json parameters.json outputs
```

生成报告区分 pin drift、前置缺失、运行失败、输出差异与字节一致；保留 stdout/stderr、staged bytes、
实际输出和负结果标记。通用 `rwb validate` 能只读校验 manifest/environment/report 及报告直接引用的
字节，不会重跑科研程序或 promotion checker。`matched` 只表达这次重建的完整输出集合及字节一致，
不证明过去发生过某次运行，不授予科学正确性、Claim、Human Decision 或 promotion 权限。
`code_ref` 只锁定程序字节，未绑定 `Run.method_ref`，因此不证明程序实现了该 Run 声明的方法。

可选 `promotion_receipt_ref` 验证 receipt 位于其无别名的原始
`runs/promotions/<promotion_id>/receipt.json`，并检查结构及预期输出是其 exact target FileRef；历史
promotion eligibility 属于独立 promotion 验证，读操作不重执行。最小合成案例、环境锁定边界和验收
矩阵见[Run reconstruction 实施记录](../workstreams/huangyi/M4-RUN-RECONSTRUCTION/README.md)。
合成重建证据不构成正式研究价值评估结果。

## 6. 提升与冻结

`promotion_record` 将 exact `work/<TASK>/<ATTEMPT>` 中受检 subjects 完整分配为 `promote` 或
`retain-in-work`。pre-Attempt Task exact-pin accepted policy registry/policy，后者固定 checker、runner
和 validation host；producer 在受控环境实际执行 pinned pipeline 并保存候选 report、execution 和 host
receipt。它们是 claimed provenance metadata，`validation_execution_fact=false`，不自证历史执行。

promotion validator 重载 Task→policy→validation records→report→subjects/live bytes 的 exact closure，
再独立重执行并 byte-exact 比较 PASS report 和 transcript；只有当场重执行才能确立复制资格。
自签 PASS 或自洽的手写历史不能绕过这一步。checker/runner 必须受信且无副作用；环境清理不等于 OS 沙箱。

execute consumer 只接受 workspace 内的 file-bound record，staging exact bytes 后完整复验，在 commit-time
再核对并 exclusive-create 目标与 durable Promotion Receipt。目标限于 `objects/`、`runs/` 或
`deliverables/candidates/`；既有目标、路径逃逸、hash 漂移或 accepted 直达均阻断。中途冲突只回滚本次
仍可确认的创建，不覆盖正式工件，不删除 work/archive。

Agent Trace 随 Attempt 冻结。promotion 只复制记录中明确选择的 exact bytes，不把整个 Archive 复制到
正式对象。结构 PASS 不产生 Claim acceptance、Human Decision、accepted publication 或科研质量判断；
checker/runner/host 的完整 pin、环境清理与失败边界见
[Artifact Promotion 契约](../implementation/ARTIFACT_PROMOTION_CONTRACT.md)。

## 7. 大文件与保留策略

首版只用 Git 管理文本、Schema、索引和小型工件。出现真实大数据或模型文件后再选择：

- DVC：文件型数据版本与可复现 pipeline；
- MLflow：确有服务器型实验追踪和模型管理需求时；
- 外部对象存储：配合不可变 manifest 与访问策略。

大数据存储仅在出现真实使用需求时选型，不提前自建 CAS、远程对象存储或复杂引用计数。

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

来源接纳验收边界：

- `sources/inbox` 的完整路径段引用被阻断；
- 每个普通 `sources/raw` 引用可定位到 Schema-valid sidecar、exact admitted path 与当前 live-byte hash；
- FileReference/admission SHA 漂移、缺失或错误 sidecar 均 fail closed；
- admission PASS 不被解释为来源可信、许可合法或科学正确。

promotion 验收边界：

- pre-Attempt Task、accepted registry/policy、validation execution 与 host receipt（claimed provenance metadata，
  `validation_execution_fact=false`）、PASS report、subjects、entries 与 live bytes exact
  closure，subject/entry 集合既不遗漏也不夹带；eligibility 只由 promotion 时的确定性重执行等价当场
  确立；手写的错误 PASS report/transcript 被阻断，byte-exact 自报历史不携带历史权威；
- 每个受检工件均有 promote/retain disposition，负结果不会被静默删除；
- file-bound record、durable receipt、staging、commit-time 复验和 exclusive-create 阻断自签 PASS、覆盖、
  accepted 直达、路径逃逸及 record/source/target/receipt 竞态；
- promotion PASS 不被解释为 Claim、Human Decision、publication 或 scientific correctness。

Agent/Method Trace 可追溯边界：

- 任一跨 Agent Handoff 能定位到发送前后的消息、actor、附件和接收决定；
- 能从 event ledger 核对每个 Agent 实际读取的正文与执行的工具是否在 Task 边界内；
- 未采用的中间产物、失败与覆盖尝试仍可沿 revision/tombstone 定位；
- Worklog 缺失不导致 Trace 消失，Trace 很长也不要求主 Agent 默认加载；
- capture gap、删减和延迟会显式暴露，不能被误报为完整记录。

Claim trace 通过显式引用一次定位支持、反证和限制；有界 Run reconstruction 在没有
原 Agent 会话时按 exact inputs/artifacts/environment refs 重建合成案例。两者分别验证引用定位与完整输出
集合的字节一致，不授予科学正确性、Claim acceptance 或正式研究评价资格。
