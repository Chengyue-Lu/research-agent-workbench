# AUDIT-RWB-DOCS-005：入口层与短程分支文档扩展

2026-10-08；R2；PR141 task-definition。本轮仅修订文档并交付现有 PR，由人类审查合并。

## 需求与范围

人类要求单一对话框容纳只读查询、局部修改、完整研究和当前主 Task 意见；Guide/短程在 main 旁隔离，局部修改后再评估 MainState 影响。最新直接校正：

> 这是一套架构设计，但是具体的判断会依赖我们的skill或者角色绑定提示词设计，他并未修改当前主线架构，只是又加了一个前置层与新分支面，你需要评估并修改那几个文档。

只新增主线前置层及应用分支，现有研究 Protocol/Task/Method→main/child→Handoff→MainState→人类决定保持。角色 Skill/提示词承载具体判断，程序检查权限/预算/版本/ref/冲突；不强制固定角色数、API 数或逐修改研究 Protocol。完整分支规则唯一维护于 [SHORT_LANE_DESIGN](SHORT_LANE_DESIGN.md)，精确 Task 唯一维护于 [TASKS](../../../TASKS.md)。

## 有界委派

required-Skills=[]。各代理保留其他编辑，无代码/API/Host/生产 Tool/Key/账本/Git mutation/全局记忆动作；Root 统一检查及推送。

| Profile / 执行记录 | 输入与互斥写入 | 预算、输出与停止 |
|---|---|---|
| bounded contract explorer；[记录](SHORT_LANE_CONTRACT_COMMUNICATIONS.md) | 候选 Task Schema、Bundle/import 与验证片段、intake/Guide、额外授权唯一 factory；只写契约报告/通信 | 10分钟1轮；精确定位、未知、Compact；报告完成或缺输入 |
| bounded docs worker；[记录](SHORT_LANE_TASK_COMMUNICATIONS.md) | 入口规则、原计划、精确 Task；只写 TASKS 与其交接/通信 | 15分钟2轮及校正10分钟1轮；5定义和5未DONE更新、原DONE不动 |
| bounded docs worker；[记录](SHORT_LANE_ARCHITECTURE_COMMUNICATIONS.md) | 共用入口/架构及模块03/05/06/09；只写 Architecture/地图/4模块与交接/通信 | 15分钟2轮；候选层/边界、保留原主线；完成或超范围停止 |
| targeted reviewer；[记录](SHORT_LANE_REVIEW_COMMUNICATIONS.md) | ADR/spec/计划、精确11个Task及新增架构段；只写最终窄审/通信 | 10分钟1轮；主线/角色判断/状态/隔离/依赖风险定位，不修改受审文档 |

Root 写 ADR及索引、唯一 spec/计划、导航/状态/路线图、审计/风险/检查/通信；primary PROJECT_MEMORY 仅 own-row 且即时重读。所有路径 repo-relative；完整可见通信保存在 ignored `.rwb/docs005-communications/`，公开记录声明前缀映射并非 byte-exact 原件。最终文件身份以 PR commit/blob 为准。

## 验证及交付边界

核新27候选ID/依赖DAG、所有READY硬依赖DONE、72原DONE行不变、Markdown路径/active锚点、公开闭包测试、Task示意Schema和PR治理/CI。结构PASS不证明路由语义、实际API、短程实现、MainState正确性或科学接受。缺失依赖/越界/正式权限漂移停止对应动作；交付PR后停在人类检查/合并，不从本次文档授权实施或测试。
