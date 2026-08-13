# Task Worklog Template

该模板用于任务目录内的简短工作留痕。复制到 `work/<TASK>/<ATTEMPT>/WORKLOG.md` 后填写；不要记录完整 Chain-of-Thought、每次普通文件打开或敏感凭据。

```markdown
# <TASK_ID> / <ATTEMPT_ID>

- baseline: <git commit or artifact revision>
- owner: <agent/human>
- goal: <one bounded atomic unit>
- target paths: <paths>
- write scope: <paths>
- handoff level: H0 | H1 | H2
- initial content read set:
  - AGENTS.md
  - <task/profile/skill/input/target module>

## Material log

| Time/order | Type | Decision or result | References |
|---|---|---|---|
| 1 | decision | <accepted/rejected choice and short reason> | <ADR/file/task> |
| 2 | read-scope | <why new file content was needed and who approved> | <path/revision> |
| 3 | change | <material change, not every edit> | <paths> |
| 4 | check | <command/check and outcome> | <report/log ref> |
| 5 | blocker | <unresolved dependency or risk> | <owner/next action> |

## Closeout

- outputs: <formal artifact refs>
- validation: <results>
- limitations/unresolved: <items>
- next action: <one action>
```

`read-scope` 只记录正文允许集扩大，不要求记录允许集内的每次读取。若任务从未扩大读取范围，应明确写 `no expansion`。
