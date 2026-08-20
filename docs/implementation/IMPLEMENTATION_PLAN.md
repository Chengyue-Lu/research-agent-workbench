# 历史实施计划索引

状态：Superseded as current plan

原版本：0.7（2026-08-15）

取代日期：2026-08-20

本文件原先同时维护技术基线、M0–M7 阶段和“当前下一节点”，已经造成与 `TASKS.md`、分支计划
和后续架构审计的状态重复。原内容仍可通过 Git 历史查看，但不再作为当前执行入口。

当前文档分工：

- 稳定产品边界：[`PROJECT_CHARTER.md`](../PROJECT_CHARTER.md)；
- 稳定跨模块关系：[`ARCHITECTURE.md`](../ARCHITECTURE.md)；
- 架构阶段与依赖：[`ROADMAP.md`](../ROADMAP.md)；
- 实时任务状态和唯一下一动作：[`TASKS.md`](../TASKS.md)；
- 实名维护与协作纪律：[`DEVELOPMENT.md`](../DEVELOPMENT.md)；
- 专项测试、迁移、Provider 或 Skill 协议：本目录其余文件。

## 历史里程碑映射

| 历史阶段 | 保留意义 | 当前去向 |
|---|---|---|
| M0 架构与仓库 | 产品和仓库基线 | Charter、Architecture、ADR |
| M1 契约与 CLI | 已实现对象/验证基础 | `TASKS.md` M1、Schema、tests |
| M2 Agent/Skill | 历史绑定与 Registry 基线 | M2、M7、ADR-0013/0015 |
| M3 上下文与风险 | continuity/Handoff/Trace | M3、模块 05–07/10 |
| M4 工件与复现 | 未完成的 provenance/promotion | M4、Roadmap Phase C |
| M5 真实案例 | baseline 和删减目标 | M5、Roadmap Phase D |
| M6 API Execution | 黄毅维护的执行层 | M6、Provider plan、模块 09 |
| M7 Mode–Skill | K-MS-1 离线历史基线 | M7、ADR-0013、历史 workstream |

第二轮审计后的新增工作从 M8 开始，不重写 M0–M7 历史状态。任何新计划不得在本文件恢复
“当前下一节点”字段。
