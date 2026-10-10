# DOCS-005：Root 协调与读取范围

2026-10-08；设计/文档输出，无执行或接受权限。最新人类校正原文见 [Packet](SHORT_LANE_TASK_PACKET.md)，Root 将其送达架构与 Task 代理并在 ADR/spec/计划中落实。主线外前置层/分支、角色规则判断与程序检查是本轮共同依据。

实际正文范围：primary AGENTS/README/本任务 PROJECT_MEMORY 行；本分支 docs README/Development、Architecture/地图新增接点、相关模块新增段、TASKS新增及修改行、STATUS/ROADMAP/施工图相关段、ADR索引/新ADR、计划/spec、审计风险与本次交接。历史文件仅机器链接/inventory和Git基线Task比较；未深读全部历史、私有评分答案、Key、API账或原科研材料。

## 可见传递与落盘

| 传递 | 有界记录与结果 |
|---|---|
| 原入口/短程用户需求 → Root/代理 | [契约通信](SHORT_LANE_CONTRACT_COMMUNICATIONS.md)、[架构通信](SHORT_LANE_ARCHITECTURE_COMMUNICATIONS.md)、[Task通信](SHORT_LANE_TASK_COMMUNICATIONS.md)保存各自收到的Packet、范围补正和回复 |
| 用户“前置层/分支，依赖 Skill/提示词” → 架构与Task代理 | 架构同轮追加；Task原任务追加10分钟1轮；无新增实现授权，状态/依赖不改 |
| 契约报告 → Root | Runtime Core不import研究Protocol，Task能力闭包仍须具备；Guide direct Provider、intake完整ceilings、factory readonly；未知保留，未运行产品 |
| Task/架构交付 → Root | 新5项1READY/4PARKED，累计24真实化+原3；指定未DONE定义对齐，6架构文件候选接点；pins指交付时字节 |
| 最终窄审委派/交付 | [窄审通信](SHORT_LANE_REVIEW_COMMUNICATIONS.md)与[报告](SHORT_LANE_NARROW_REVIEW.md)限定主线/判断/状态/隔离/依赖 |
| Root整合 → PR141 | ADR-0024、唯一短链设计/实施计划、5exact定义及派生链接；验证结果见 [STATIC_CHECKS](STATIC_CHECKS.md) |

公开通信以相对路径映射机器 checkout 前缀，不声称 byte-exact。完整消息原件在本地 ignored `.rwb/docs005-communications/`；源Hash和交付Hash在对应通信/Compact中。隐藏推理、秘密及无关原logs不记录。Git规范化或Root后续编辑可能改变交付字节，最终身份读具体PR commit/blob。
