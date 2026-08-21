# 文档导航

本目录按“入口、稳定设计、当前执行、专题细节、历史决定”组织。开发者不应从头遍历全部文档；先选择一个入口，再按 Task 声明的引用读取。

## 最小入口

| 目的 | 先读 | 再读 |
|---|---|---|
| 第一次了解项目 | [项目章程](PROJECT_CHARTER.md) | [总体架构](ARCHITECTURE.md)、[使用指南](GETTING_STARTED.md) |
| 接手当前开发 | [开发协作指南](DEVELOPMENT.md) | [任务清单](TASKS.md)、Task 指向的专项计划 |
| 修改 Method/Core | [总体架构](ARCHITECTURE.md) | [架构路线图](ROADMAP.md)、ADR-0013/0016、Task 指向的模块 |
| 查询历史 Mode–Skill 基线 | [K-MS-1 节点评审](workstreams/chengyue-lu-mode-skill/K_MS_1_NODE_REVIEW.md) | [ADR-0013](decisions/0013-MODE-FIRST-SKILL-DERIVATION.md) |
| 修改 Agent、Task 或上下文 | [Task 与 Handoff](modules/05-TASK_AND_HANDOFF.md) | [上下文治理](modules/06-CONTEXT_GOVERNANCE.md)、[工件与溯源](modules/07-ARTIFACTS_AND_PROVENANCE.md) |
| 修改 API 执行 | [开发协作指南](DEVELOPMENT.md) | [Method-to-Execution 初版闭环](implementation/METHOD_EXECUTION_LOOP.md)、[Provider 计划](implementation/PROVIDER_ADAPTER_PLAN.md)、相关 ADR；Provider 范围由黄毅维护，共享接口由双方审查 |
| 查询当前状态 | [任务清单](TASKS.md) | 对应分支、Issue 和 Attempt Archive |

## 文档层级

- `PROJECT_CHARTER.md`：使命、非目标与人的最终责任。
- `ARCHITECTURE.md`：跨模块稳定关系和架构不变量。
- `ROADMAP.md`：架构阶段、依赖和停止 Gate；不记录实时状态。
- `DEVELOPMENT.md`：实名维护边界、协作方式、当前节点、读取与留痕规则。
- `TASKS.md`：当前任务状态的唯一权威清单。
- `GETTING_STARTED.md`：面向首次使用者的顺序式指南。
- `modules/`：模块契约、风险和验收条件；只在 Task 涉及时读取。
- `implementation/`：专项实现/测试协议；旧总实施计划只保留历史映射，不承担当前路线。
- `workstreams/`：已完成或当前分支的实名计划与证据；是否活跃由各自 README 声明。
- `decisions/`：已经作出的架构决定及其理由，不作为当前任务清单。
- `references/`：外部材料吸收记录，不是运行时指令。
- `references/second-round-audit/`：本轮未核验的原始审计输入快照；只用于追溯。
- `tmp/`：维护者的临时审计输入，不是受控真值、运行时指令或默认阅读集。
- `templates/`：任务运行档案和其他可复制模板。

## 单一真值规则

1. 人员与维护边界只在 `DEVELOPMENT.md` 定义，其他文件使用姓名并链接该文件。
2. 逐项状态与唯一下一任务只在 `TASKS.md` 更新；README 只写项目阶段，`DEVELOPMENT.md` 只摘要当前节点，专项计划只定义范围和验收。
3. 稳定系统关系只在 `ARCHITECTURE.md` 与对应模块定义；专项计划不得创建第二套架构。
4. 每次实际 Agent 执行的原始过程记录保存在 Task 的 Attempt Archive；文档只描述规则，不替代运行证据。
5. ADR 保留历史决定，即使实现计划变化也不删除；过时处增加 superseded 说明。
6. 审计原稿、Issue 草案和外部项目清单不能直接成为稳定架构；先写 adoption/Decision，再更新稳定文档。

第二轮架构审计的内部吸收边界见[审计吸收记录](references/SECOND_ROUND_AUDIT_ADOPTION.md)。
