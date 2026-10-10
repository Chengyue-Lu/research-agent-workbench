# M6-013 / Slice 001 Task Packet

2026-10-11；Agent Profile: implementation worker；required-Skills: []；risk R2。

授权来源：主准备窗口 `RWB M5-008 续接`（thread `01a1064a-eaef-7da0-aebd-962910ff42b8`）转达的人类并行开发授权。固定候选起点 `76fd3d892eb1f1a15799c9f24a255ef2dcf0190e`，本地已组合 PR143 fcb1cfd 和 PR144 fee6b3af；不是 GitHub merge 或设计/实现接受。候选分支 `codex/m6-013-working-inputs`，使用独立 managed worktree，不写测试窗口 checkout。

## 目标、范围与交付

沿 [ADR-0027](../../../decisions/0027-USAGE-RECORDING-AND-MODEL-WORKING-INPUT.md) 和 [迁移边界](../../../compatibility/BUDGET_CONTRACT_MIGRATION.md)，交付显式白名单、纯程序工作输入投影；保留用户费用讨论与获准输入 exact pins，给完整 producer→consumer 迁移表、独立测试代码、候选投影 Schema 和 Compact Handoff。M6-013 只推进到 IN_PROGRESS，不判 DONE。

允许读：现行 AGENTS/README/primary PROJECT_MEMORY 相关入口，docs 导航/Development/Architecture，TASKS M6-013/M6-011/M2-009，上述 ADR/compatibility；直接 Task/Policy/View/Host/Session、roles request、intake compiler、factory 链及必要 Schema。先文件名/接口发现，禁止 API 原始日志、凭据和旧 .rwb 实际运行目录。

互斥写：新增 `src/research_workbench/entry/working_inputs.py`、`tests/test_entry_working_inputs.py`、候选 `schemas/v0.2.0/model-working-input.schema.json`；本目录；docs/TASKS 的 M6-013 own status；primary PROJECT_MEMORY 的本片段 own-row。旧版契约/测试保留。工作树本地 memory 配置 generate=false/use=true 仅为运行环境政策，不混入产品提交。

不写共享 roles/intake/workflow/factory/Host/View/Session 消费者、Schema v0.1.0、build backend、CI 两文件/映射、Registry/Skill/示例/安装资源。测试窗口 M1-010 与 CI P2 修复保持独立，后续由 Root 串行接入消费者。

20 分钟工作段；仅静态 AST/内存 compile、JSON syntax、hash、Markdown 目标、diff 检查。禁止运行测试、API/付费模型、生产 Tools/Attempt、Key/认证/生产账本；Root 统一测试。可提交并推独立候选 ref，不 merge、不等 review；如创建 PR 则 attach。遇共享接口必需变更，停该部分并报告精确缺口，继续独立模块。无全局记忆更新或后台调度。

输出：[迁移表](MIGRATION.md)、[风险](RISK_LEDGER.md)、[通信](COMMUNICATIONS.md)、[交接](HANDOFF.md)。本片段运行开始 00:29:52+08:00，工作段上限 00:49:52+08:00；停止于首切片完成或工作段耗尽。

