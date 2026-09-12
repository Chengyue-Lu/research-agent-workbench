# 文档准备与核对记录

## 范围与已有结果

2026-09-12，PR70 的 import binding 修复及当前 CI 通过复审，已 squash 合入 develop@ab98caf；PR71 的 Task 范围修复获正式批准但未合并。随后从该接受基线建立独立分支 `codex/m12-m13-entry-review`，准备 M12/M13 的具体审查输入。

新增 Phase C 两案事实解释、待具名决定表、M12 action 边界实际接续候选、M13 真实反馈归因/现有路径复用方案、来源与风险记录，并从黄毅 workstream 索引链接。保留所有 canonical Task 状态和当前 Gate，未把文档提交等同于解冻或功能实现。

## 来源核对

按两个 manifest 实际 source_ref 路径读取字节，24 项 SHA-256 全部匹配；manifest 自身哈希及每项结果见 [SOURCE_INDEX](SOURCE_INDEX.json)。未读取 private oracle、未执行 actor 或新模型会话。

## 独立复核与最小验证

指派及结果见 [HANDOFFS](HANDOFFS.md)。独立复核指出 RecoveryPreparation 返回类型、Resolver 与 View producer 分工两处文字应精确化；主 agent 对照已有实现/ADR 后已修正，没有扩大实现或测试范围。提交前执行内部文档链接与 diff 范围核对；提交后用现有治理器核验精确 base/head 及 PR 正文。实际结果由 PR 验证段和后续本地输出记录承载，不预填 hosted CI 结果。

本地核对结果：复用 `tests/test_documentation.py` 的内部链接规则检查本次 9 份 Markdown，55 个内部链接全部存在；上述 24 项源字节 pin 匹配；`git diff --check` 通过。对照 base，TASKS、ROADMAP、src、schemas、registry、.github 无差异。没有新增/执行功能测试，也没有声称 fresh actor、人工重建或科研效果。

本记录的边界和授权见 [TASK](TASK.md)。核心判断供维护者审查，最终 Phase C Human 语义决定、独立 Topic 5 定义及 M13 真反馈样本仍待完成。
