# ADR-0005：执行 Agent 使用源只读、任务区受限写权限

状态：Accepted
日期：2026-08-13

## 背景

Evidence Scout 等 Agent 常被简称为“只读 Agent”，但它仍必须写入自己的 attempt、Evidence 候选和 Handoff。如果把 `filesystem: read-only` 解释为整个会话完全只读，Task 合同无法完成；如果直接授予整个 worktree 写权限，又会允许它修改输入、正式 Claim 或其他 Task 工件。

## 决策

- “只读”描述输入和正式工件的治理语义，不作为含糊的系统权限值。
- 需要产生工件的 Agent 使用 `filesystem: worktree-write`，同时由 Profile、Task 和 Skill 的 `allowed_roots` 取路径交集。
- Task 的 `write_scope` 必须完全位于有效 `allowed_roots` 内；否则在启动前以 `TASK-PERMISSION-ESCALATION` 阻断。
- 首版子 Agent 默认只写 `work/<TASK>`。向 `objects/`、`runs/` 或正式索引的提升由主 Agent 或确定性 promotion 操作负责。
- 外部写入仍单独由 `external_write` 控制；文件写权限不隐含网络、上传或发布权限。

## 后果

Agent 可以保存正式交接所需的局部工件，同时不能靠“需要输出”扩大到整个项目。路径交集采用保守规则；复杂 glob 无法证明互斥时宁可阻断并要求缩窄 Task。
