# 工作流隔离记录（2026-08-16）

状态：已执行

## 目的

按实名维护边界，将此前混入共享工作树、但属于路诚钺负责范围的 Mode–Skill / K-MS-1 实现从黄毅的 API 分支剔除，同时保留可恢复归档，并保持项目共享接口兼容。

## 可恢复归档

- 归档分支：`codex/archive-k-ms-1-20260816`
- 归档指向：`7377dcd`
- 活动 API 分支：`codex/glm-5-3-runner`
- 隔离提交：`a60d0c9`

归档分支保留隔离前的完整文件状态。活动分支不删除或改写归档分支；恢复、审阅或移交 K-MS 内容应从归档分支另开路诚钺所有的工作分支，不把它重新混入 API Provider 提交。

## 从活动 API 分支剔除的范围

- Mode 决策卡与 Mode Registry 扩展；
- Task-to-Skill 选择模型、评估器与 CLI；
- KMS 选择 fixtures；
- accepted Skill 边界审计；
- H0/H1/H2 fixture-only 比较；
- candidate triage 决定；
- 上述内容专用 Schema 与测试；
- 文档中“这些工件已完成”的状态声明。

## 保留的共享兼容接口

活动分支继续保留并验证：

- Task Packet / Resolved Task / Skill Assignment；
- H0/H1/H2 Handoff 等级与 Handoff Packet；
- Agent Trace Envelope / Actors / Event / Index；
- Attempt、Execution Receipt、Main State 与 Model Assignment 引用；
- Execution Contract、Provider capability、Data Policy、状态与错误语义；
- 既有 accepted Skill Registry 和显式 resolver 的基线行为。

隔离后运行共享 CLI、Schema、Registry、Skill resolver、candidate 边界和文档链接回归，均通过；`rwb validate examples registry` 无错误。隔离不代表 K-MS 工作被否定或丢弃，只表示它不由当前 API 分支实现、修改或宣称完成。
