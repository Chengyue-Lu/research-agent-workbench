# RWB通用研究执行入口

2026-10-10 当前阅读入口（PR140 未合并开发候选）：[最新审查修复](review-fixes-007/README.md)、[执行阶段与 Guide 证据](stage-evidence-006/VERIFICATION.md)、[planning 与正式 Handoff](planning-handoff-004/VERIFICATION.md)。包内 caller/factory 的前一 Action 切片见[原记录](package-caller-003/VERIFICATION.md)。更早结果保留在[桥接报告](chain-proof-002/ROOT_REPORT.md)、[覆盖与缺口](chain-proof-002/COVERAGE.md)、[接口使用说明](chain-proof-002/USAGE.md)。真实 API 的结果与停点以对应版本报告为准；Source/Human/正式 Skill 资格、真实科研验收及 M12 未完成。

以下为初始实施任务快照；其中 READY 和初始验收范围不代表当前成熟度。原 65 项离线交付保留在历史 COMPLETION/manifest，后续桥接与修复证据在上方入口更新。

任务范围：`AUDIT-RWB-ENTRY-001`；集成分支：`codex/research-entry-integration`；基线：develop `d3c4d23206339ebc7f18b5621f3aa5453f96335e`。

入口、角色、Task/Mode/Capability、状态/Trace 与 Provider、Session、Host/Driver 的功能职责按 exact Task 和运行边界维护。当前人类批准隔离分支实现、测试、推送与PR更新；merge/release、Skill及科学接受沿用各自明确授权与验收。

## 授权与范围

2026-10-07人类明确指示：

> ok，基本没有问题，准备开始执行，这部分新开一个PR分支进行实现，并同时开两个新窗口考虑M12部分与前端部分，这部分测试通过后，将所有的内容，定义任务名称以及完成度，推送到对应分支以及PR。

承接已讨论的十模块接口盘点与角色运行方案，优先复用文件契约、Capability Resolver、Runtime Bundle→Resolved Execution View→Thin Host、Session、Trace与MainState。职责可合并；子Agent是否启用和数量由main提出，在显式预算/权限/并发/深度边界内执行。角色最低指令必须实际进入请求，Skill按方法选择，不以角色别名制造Skill准入。

本workstream以Audit ID记录隔离分支的应用接合与验证，不重定义已DONE的M Task、不解冻M12/Topic5、不把本地候选记成develop接受。两个新窗口产出M12/前端候选；若它们建议变更核心身份、路由、Human边界或Runtime ownership，先形成ADR/task-definition候选，不能以本实现批准代替核心变更接受。

## 有界实施分项

| ID | 名称 | 初始状态 | 完成所需证据 |
|---|---|---|---|
| ENTRY-01 | 入口与角色指令装配 | READY | 必载指令、显式输入快照、无Skill角色可运行、实际请求载入证据 |
| ENTRY-02 | 需求与材料接入/控制产物 | READY | 从零与缺MainState接续共用契约；Protocol/Task/Method等产物被下游消费，格式无效阻断 |
| ENTRY-03 | 通用执行绑定与Driver接合 | READY | 显式冻结输入接既有Bundle/View/Host及Session，实际facts/Trace/closeout与文件复验 |
| ENTRY-04 | main动态委派与执行链预算 | READY | main实际决定0..N；子Task/结果/取消/失败/unknown与汇总边界，不固定编制 |
| ENTRY-05 | 交接消费与人工续接状态 | READY | Compact/generic closeout，main实际消费/处置，唯一状态提交；保持正式legacy契约 |
| ENTRY-06 | 独立只读Guide | READY | 独立MainState/必要refs，实际只读工具，无main回传或科研状态写入 |
| ENTRY-07 | 通用入口轻量验收与可读报告 | READY | 正向与关键失败测试；每段真实输入输出/完成度可读，安装入口适用 |
| PLAN-M12 | M12边界与后续任务候选 | READY | 独立窗口交付现状/可复用接点/前置条件/任务候选，不声称解冻 |
| PLAN-FRONTEND | 前端产品与控制入口方案 | READY | 独立窗口交付人类交互/角色职责/格式校验/授权预算/输出/测试建议 |

状态依据只限本分支，后续逐项填写实现提交、测试与剩余项；不以单一百分比掩盖未执行的真实API或原生平台验证。完成矩阵见后续`COMPLETION.md`。

## 协作

独立文件ownership与范围见[TASK_PACKET](TASK_PACKET.md)；风险见[RISK_LEDGER](RISK_LEDGER.md)。普通产品前端方案与Protocol配置前端职责分别解释；前端不是新的core模块。主checkout PROJECT_MEMORY唯一共享，Root写前重读仅更新own-row。
