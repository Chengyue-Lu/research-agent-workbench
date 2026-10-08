# M0-008 机器治理对齐

2026-10-08；独立 feature 候选。定义已随 PR141 合并；本实施尚未合并，M0-008 当前状态见 [TASKS](../../TASKS.md)。

入口：[Task Packet](TASK_PACKET.md)、[Risk Ledger](RISK_LEDGER.md)。范围是开发人员机器限制同步，产品身份、功能权限、发布拓扑与历史事实保持原契约。

本地 implementation 和远端同步分别验收。启动时实际四层 ruleset 均 active：develop/main 硬门禁零 bypass，分别规定 squash/merge、必需 CI、latest-base、线程解决和 force/delete 保护；独立 review 层仍存在 Code Owner 规则，main 还要求 approval 与 last-push approval。两套 review 层现有用户级 PR 例外不表示硬门禁可绕过。本次仅只读保存修改前事实，尚未改远端。

可见通信、审阅读范围、脱敏线上原始事实与本次检查存于执行 archive；可读结果见 [验证记录](VERIFICATION.md)。105项限定治理/文档检查通过，未引入新链接缺失；远端规则尚未同步，M0-008 未完成。
