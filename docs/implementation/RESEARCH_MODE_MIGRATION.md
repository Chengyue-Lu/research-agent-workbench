# Research Mode v0.1 → v0.2 migration

状态：Active compatibility contract

## 1. 目的

该 seam 把两个已知 Research Mode 从直接 `recommended_skill_capabilities` 的 v0.1 表示迁移为引用
Mode Action 的 v0.2 表示，同时保留历史文件、版本和解释能力。它解决结构兼容问题，不宣称完成
Method、Capability 或 Execution 迁移。

## 2. 权威工件

- Mode Schema：`schemas/v0.1.0/research-mode.schema.json`；
- migration record Schema：`schemas/v0.1.0/research-mode-migration.schema.json`；
- v0.1/v0.2 Mode：legacy `registry/modes/*.yaml` 与 versioned `registry/modes/v0.2.0/`；
- versioned Actions 与闭集索引：`registry/modes/actions/`、`registry/modes/actions.json`；
- migration records：`registry/modes/migrations/`；
- 实现：`research_workbench.protocol.migrations`。

Schema 目录版本仍为 `v0.1.0`；Mode 文档自身的 `version` 决定其互斥字段形状：v0.1 必须且只能使用
`recommended_skill_capabilities`，v0.2 必须且只能使用 `action_refs`。未知 Mode version fail closed。

## 3. 显式迁移流程

```text
v0.1 Mode file + raw SHA-256
  → named migration implementation@version
  → deterministic v0.2 Mode
  → v0.2 Action refs with exact mode_ref ownership
  → migration record pins source/target/action paths and raw SHA-256
```

调用迁移函数是显式操作。普通加载和验证不会自动替换 v0.1，也没有“找不到 v0.2 就退回 v0.1”的
fallback。迁移只接受已登记的 Mode 和 Action 映射，未知版本、缺失映射或 hash/path/ref 漂移都会阻断。

## 4. Action revision ownership

`ModeAction.mode_ref` 精确指向 `mode-id@version`。所以 v0.1 Action 不能直接充当 v0.2 Mode 的正式
Action，即使研究义务正文相同。v0.2 发布对应的 `action-id@2.0.0`，旧 `@1.0.0` 与 Registry entry
保持不变。migration record 保存一一对应的 source/target Action ref、路径和 hash。

## 5. 保留与排除

迁移保留 Mode ID、触发条件、Artifact、Claim rules、Human decisions 与 Risk rules；移除直接 Skill
recommendation，新增 Action refs。它明确不：

- 选择或绑定 Skill、Tool、Agent、Model、Provider 或 Runtime；
- 迁移历史 Method Resolution、Assignment、Receipt、Attempt 或 Trace；
- 推断执行事实、Evidence、Claim 或 Human decision；
- 原位改写 v0.1 Mode、Action 或 Registry entry；
- 证明 v0.2 对真实研究任务具有方法或成本净收益。

## 6. 验证边界

`rwb validate` 校验 migration record Schema、Mode/Action 引用闭集、exact revision ownership、raw-byte
hash、实现身份、一一映射和 target `action_refs` 闭合。单元测试另外验证 deterministic output、旧新版本
并存以及未知版本、缺失 Action、hash drift 和映射漂移的 fail-closed 行为。

这些结果只证明迁移可重复且可审计。真实研究质量仍须通过独立 forward case 与 Human Gate 判断。
