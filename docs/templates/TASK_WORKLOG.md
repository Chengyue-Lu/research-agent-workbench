# Attempt Archive 与 Worklog 模板

复制到 `work/<TASK>/<ATTEMPT>/`。Worklog 只是导航摘要；Assignment、Agent 间消息、Handoff、检查和输出必须保存为独立文件。

## 目录

```text
work/<TASK>/<ATTEMPT>/
├── TASK.yaml
├── INDEX.yaml
├── ACTORS.yaml
├── events.jsonl
├── messages/
├── tool-events/
├── handoffs/
├── decisions/
├── checks/
├── outputs/
├── snapshots/
└── WORKLOG.md
```

`ACTORS.yaml` 至少记录：

```yaml
actors:
  - actor_id: main-agent
    role: coordinator
    runtime_identity: <profile/model/window ref>
    accountable_owner: 路诚钺
  - actor_id: mode-reviewer
    role: reviewer
    runtime_identity: <profile/model/window ref>
    accountable_owner: 路诚钺
```

消息使用 `NNNN-<sender>-to-<receiver>-<kind>.md`，正文格式见[工件与溯源](../modules/07-ARTIFACTS_AND_PROVENANCE.md)。所有实际可见传递均保存；不保存隐藏 Chain-of-Thought、密钥或政策禁止留存的原文。

## INDEX.yaml 最小内容

```yaml
task_id: <TASK_ID>
attempt_id: <ATTEMPT_ID>
baseline: <git commit or artifact revision>
owner: 路诚钺 | 黄毅 | <其他实名>
status: active | completed | failed | safe-paused | cancelled
read_allowlist:
  - AGENTS.md
  - <task/profile/skill/input/target module>
write_scope:
  - work/<TASK_ID>/<ATTEMPT_ID>/**
messages:
  - id: MSG-0001
    path: messages/0001-main-agent-to-mode-reviewer-assignment.md
    kind: assignment
    sender: main-agent
    receivers: [mode-reviewer]
    sha256: "..."
event_ledger: events.jsonl
tool_event_refs: []
handoff_refs: []
decision_refs: []
output_refs: []
check_refs: []
capture_gaps: []
```

Agent 默认可以读取 `INDEX.yaml` 元数据，但不能因此读取所有 `messages/`、`events.jsonl` 或 `tool-events/` 正文。正文必须由 Assignment 或 scope-decision 显式授权。运行时应把可观察的正文读取、工具调用、命令、文件 revision 和状态事件追加到 `events.jsonl`；瞬时结果没有不可变来源时保存到 `tool-events/`。

## WORKLOG.md

```markdown
# <TASK_ID> / <ATTEMPT_ID>

- baseline: <git commit or artifact revision>
- owner: <human name>
- actors: <actor IDs; details in ACTORS.yaml>
- goal: <one bounded atomic unit>
- target paths: <paths>
- write scope: <paths>
- handoff level: H0 | H1 | H2
- trace index: INDEX.yaml
- event ledger: events.jsonl

## Material log

| Time/order | Type | Decision or result | References |
|---|---|---|---|
| 1 | decision | <accepted/rejected choice and short reason> | <decision/message/task> |
| 2 | read-scope | <why new content was needed and who approved> | <scope messages> |
| 3 | change | <material change, not every edit> | <paths> |
| 4 | check | <command/check and outcome> | <report/receipt> |
| 5 | blocker | <unresolved dependency or risk> | <owner/next action> |

## Closeout

- outputs: <formal artifact refs>
- handoff: <handoff ref or H0>
- trace completeness: complete | capture-gaps:<refs>
- validation: <results>
- limitations/unresolved: <items>
- next action: <one action>
```

若没有扩大读取范围，写 `no expansion`；若没有跨 Agent 传递，使用 H0 并保持 `messages/` 为空。任何 capture gap、删减或延迟归档必须进入 `INDEX.yaml`，不能只写在聊天中。
