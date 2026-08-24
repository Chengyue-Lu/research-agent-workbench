# M8-004 Research Mode v0.2 migration seam

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 跨负责人审查人：黄毅（GitHub `let778750-cpu`）
- Task：`M8-004`
- 当前状态：DONE；已纳入统一 M8 阶段 PR #30，等待合并审查
- 阶段分支：`agent/method-m8-action-resolution-node`
- 阶段 base：`develop`

## 1. 目标

建立一个最小、确定性、不可覆盖原件的 Research Mode v0.1→v0.2 迁移 seam：

- v0.1 Mode 与既有 Action/Resolution 保持可验证、可解释；
- v0.2 Mode 删除 `recommended_skill_capabilities`，改为显式 `action_refs`；
- 迁移记录固定 source/target 路径、Mode ref、原始文件 SHA-256 与迁移实现版本；
- 因 `ModeAction.mode_ref` 精确绑定 Mode revision，v0.2 采用新 Action version 与 append-only Registry entry，
  不原位改写已发布 Action；
- 正反 fixture 证明旧对象不会被静默升级，迁移结果不会携带 Skill、Tool、Provider 或 Runtime binding。

## 2. 非目标

- 不把 PR #30 的跨负责人审查视为已发生；
- 不迁移历史 Method Resolution、Assignment、Receipt、Trace 或 Attempt；
- 不实现 Resolved Execution View、Capability binding 或具体 Skill/Tool/Model/Provider/Runtime；
- 不定义 Decision Authority 或 Human Gate decision vocabulary；
- 不建立通用全对象 migration framework。

## 3. 迁移不变量

1. source 文件原始字节保持不变；
2. source 与 target 使用不同 `mode_id@version`，同一 Mode ID 只显式升到 `0.2.0`；
3. v0.1 只允许 `recommended_skill_capabilities`，v0.2 只允许 `action_refs`；
4. v0.2 Action 必须声明对应 `mode-id@0.2.0`，并以新 `action_id@version` 进入 append-only Registry；
5. migration record 的 source/target/action hashes 必须与仓库原始文件字节一致；
6. migration implementation 只重写被声明的 Mode/Action 引用，不补造 Method、Evidence、Claim 或执行事实；
7. 失败必须显式阻断，不能回退到 v0.1 Skill recommendation。
8. migration 只重放自身固定的 exact Action ref/path/hash；同一 mode/action ID 追加新版本不改变旧记录。

## 4. 允许写入范围

- `schemas/v0.1.0/research-mode*.schema.json`；
- `registry/modes/**` 中新增的 v0.2 Mode、Action version 与 migration record；
- `examples/modes/**` 与 `examples/compatibility/**` 的当前/历史 fixture；
- `src/research_workbench/protocol/**`、`src/research_workbench/validation/documents.py`；
- 对应 tests、implementation/compatibility/status/task/workstream 文档。

不得修改 Provider/API/Runtime、Assignment/Receipt/Trace/Recovery 或 Skill Registry。

## 5. 停止与交付边界

M8-004 在以下条件满足时停止：两个正式 Mode 均有可复验迁移、原/新 hash 闭合、v0.1/v0.2 正反
Schema 与关系测试通过、完整仓库验证通过。该节点不再维护独立开发分支或接手文档；实现随统一 M8
阶段 PR #30 接受一次 R2 审查。

结构验证不证明 Mode v0.2 对真实科研任务具有净收益。

实现结果与验证证据见 [`VALIDATION.md`](VALIDATION.md)。
