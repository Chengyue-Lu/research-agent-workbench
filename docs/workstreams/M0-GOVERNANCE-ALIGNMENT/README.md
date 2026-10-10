# M0-008 机器治理对齐

2026-10-10；独立 feature 完成候选。定义已随 PR141 合并；实现/远端同步验收齐备，本地代码尚未合并，当前状态见 [TASKS](../../TASKS.md)。

入口：[Task Packet](TASK_PACKET.md)、[Risk Ledger](RISK_LEDGER.md)。范围是开发人员机器限制同步，产品身份、功能权限、发布拓扑与历史事实保持原契约。

本地 implementation 和远端同步分别验收。[线上记录](REMOTE_SYNC_RECORD.md)保留修改前后事实：两review层已取消人员审批要求并清空具名bypass；两hard层逐字段不变，保留必需PR/CI/latest-base/线程解决、合并方式与force/delete，active且零bypass。

可见通信、审阅读范围、线上原始事实与检查存于执行 archive；可读结果见 [验证记录](VERIFICATION.md)。105项限定治理/文档检查通过，未引入新链接缺失；本地完成候选和实际远端同步不替代人类具体合并或发布指令。
