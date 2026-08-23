# 历史与审计入口

这里保存系统如何形成、曾尝试什么以及为什么改变。它们是复核和排障证据，不是新用户的操作指南，也不覆盖稳定文档、当前状态或实时任务清单。

- [详细开发日志](../../DEVELOPMENT_HISTORY.md)：逐批次变更与旧节点记录；
- [Workstream 记录约定](../workstreams/README.md)：当前和已关闭工作流的证据结构；
- [已完成工作流](../workstreams/chengyue-lu-mode-skill/README.md)：Mode–Skill 探索、筛选与迁移证据；
- [第二轮审计采纳说明](../references/SECOND_ROUND_AUDIT_ADOPTION.md)：外部审计如何影响架构；
- [外部审计原始材料](../references/second-round-audit/)：保留输入与议题草案；
- [旧实施计划](../implementation/IMPLEMENTATION_PLAN.md)与[迁移计划](../implementation/MIGRATION_PLAN.md)：不再承担当前规划权威。

当前系统从[文档导航](../README.md)进入；架构决定从[ADR 索引](../decisions/README.md)查找。

## 新 workstream 的 closeout

细粒度证据在原 `docs/workstreams/<owner>/<workstream>/` 目录冻结，不移动目录，以免破坏已有
链接。workstream 合并到 `main` 后，在本目录新建
`YYYY-MM-DD-<task-id-or-audit-id>-<slug>.md`，至少记录：

- owner、cross-owner reviewer、feature PR、`develop` integration commit 与 release PR；
- 最终范围、clean-checkout 验证命令和已提交证据；
- TASKS/STATUS/ADR 的真实变化，或明确说明没有变化；
- 已知限制、延后项、后续 Task 和 workstream 原目录链接。

进行中的 workstream 不得预先写成已完成历史；`DEVELOPMENT_HISTORY.md` 继续作为旧记录和全局
索引，不再复制每个新 workstream 的完整正文。
