# AUDIT-RWB-DOCS-005：短链路 exact Task Compact Handoff

2026-10-08；Profile=`bounded documentation worker`；required-Skills=`[]`；PR141 docs-only 候选。本交付记录定义修改，不声称实现完成、PR 已接受或 API/科学资格。

## 写入与实际读域

只修改 [TASKS](../../../TASKS.md)，新增本 Handoff、[通信记录](SHORT_LANE_TASK_COMMUNICATIONS.md)和 ignored `.rwb/docs005-communications/task.md`。公开通信明确相对路径映射，ignored 原件保留完整原通信及实际 checkout 映射。没有覆盖架构、ADR、计划、合同审查或其他代理文件。

实际读入：`AGENTS.md`、`docs/README.md`、`docs/DEVELOPMENT.md`、`docs/TASKS.md`、本 workstream `REALIZATION_PLAN.md`。先文件名定位计划，TASKS 长输出截断后只补目标/依赖段；上一轮结果由 Compact 继承。最新人类要求由本轮 Root Task Packet 传入，未读取另一窗口原件。未读 Key、账、其他代理输出、primary memory 或额外源码/Schema。

## 新定义快照

以下为交付时快照；不替代 TASKS 的 live 状态/依赖权威。固定 5 ID 均为 R2，无人员列，没有增补未授权 ID。

| ID | 状态 | hard dependencies | 具体验收边界 |
|---|---|---|---|
| M1-014 | READY | M1-004, M8-005 | 前置分流/Guide/Short 扩展不重构研究主链；最小输入及 Task metadata，由版本绑定且经评审的角色 Prompt 或 Skill 判断路由，记录路由 Profile、Prompt 或 Skill 版本/hash、理由与不确定澄清；仅 research 进入 Protocol；Runtime 保留权限预算/结构引用检查而不硬编码逐案语义，绑定路线可选、角色可合并且 API 数不固定，无任意 child 投递或 main history 扩散 |
| M3-013 | PARKED | M3-012, M11-009 | 扩展接点保留研究主链；角色 Prompt/Skill 经版本绑定评审后承担 none/relevant/unknown 语义判断，与 actual diff/hash/ref/State 版本/活动输入确定性检验分别留证；路线可选、无每次 Skill Supply/固定 API 要求；none 且 refs 有效、无冲突才保持 main 不变且不通知，相关/未知/损坏提案及 hold，人类采纳后受控 writer 新 revision；prewrite 检查/失效最小通知保留，Topic 5 不解冻 |
| M2-014 | PARKED | M1-014, M2-010, M6-012, M3-013 | 与 Guide 同级扩展、不重构研究主链；隔离最小 Task/适用 no-Skill/direct Tool/pins/预算/write scope，局部修改不逐次研究 Protocol/Mode；版本绑定评审的 Prompt/Skill 承担语义判断，路线可选、无每次 Skill Supply/固定角色 API 数要求；Runtime 保留契约及确定性检查，实际修改/后评估/失败usage副作用闭合，活动冲突先停，无任意 child 控制 |
| M1-015 | PARKED | M1-014, M1-013, M2-013, M2-014 | 平台可替换单 UI，按合法对象/recipient/预算/供给投递隔离 caller；共享显示不拼历史、不自动 main 反馈；明确 main steering 只经当前 Task 治理接点，child 由 main 控制；真实 route/message/API/产物及累计 usage/unknown，可核而不扩权/Host 重选/全局控制服务 |
| M11-011 | PARKED | M1-015, M11-010 | 实际长短链 Gate 覆盖 Guide、段落重排无 State 改动、Claim 小改相关/未知提案和采纳/hold、混合/steering/research、活动文件冲突/误投 child 拒绝；actual diff、State before/after、recipient/context/notifications 原事实，不以 bare callback 代替；现有 main 保持，不恢复/科学准入 |

新增为 1 READY / 4 PARKED；上一轮 19 加本轮 5 为 24 项（6 READY / 18 PARKED），加原 M1-010/M2-009/M11-008 共 27 候选。原三项 READY 行没有修改；原 72 DONE 行没有编辑。新风险/Phase 导航按现有 Application entry、Research Control/Contracts、Agent Runtime、Context/Trace 和 Topic 4 family 表述，不复制状态，不激活 M12。

## 指定未 DONE 定义调整

- M1-011 增加唯一新依赖 M1-014，限定 research 才生成/修订研究 Protocol；其他请求用独立局部契约。
- M2-010 baseline 包括入口分流、短程编辑、后置影响评估，前置和 Guide/Short 扩展不重构研究主链；具体语义由版本绑定且经评审的角色 Prompt 或 Skill 承载，结构/引用、权限和预算检查留在架构/Runtime。路线可选、角色按需合并、无固定 API 数或每次 Skill Supply 要求；选择 Skill 仍守适用准入/加载边界，不新增固定 coreRole。
- M1-013 installed producer/consumer 交付保留原依赖；明确完整 research 和旁路由 M1-015 接合，单 CLI 不是统一聊天全路由验收。
- M2-013 保留原依赖、只读证据解释；mutation 建议转 route，用户建议只有明确采纳才成为 main 输入。
- M3-012 保留原依赖；引用 M3-013 承担短程影响提案采纳，不增加反向 hard dependency。

## 未决与验证范围

人工对照本轮依赖：M1-014 的 M1-004/M8-005 均显示 DONE；新增链向后连接既有 PARKED 项，未发现本轮反向依赖环。没有执行 DAG validator、DONE byte comparison、链接/文档/治理 checks；这些正式检查由 Root 唯一执行。本交付没有 PASS 宣称。

路由 schema/内部表示、MainState 后置影响证据与受控 writer 的具体实现、活动写锁/输入失效事实 producer、批准 recipient 的 adapter 投递和通知证据均未实现或验证，须在相应 exact Task 下补齐。没有发现必须在本 docs-only 阶段追加核心 Schema 的依据；若实现触动核心对象身份、选择/歧义、人类接受或 Runtime ownership，停止并走独立 ADR/R2，不把任务定义当作语义接受。

Root 后续需同步自己 owned 计划/导航及适用架构记录，核固定 ID/依赖/风险、表格/链接、72 DONE 行逐字保真和治理，再按用户授权处理 PR。任何后续改动重冻文件 hash。没有实现、运行产品/API/Tool、读取 Key/账、Git mutation、安装、配置/Schema/Registry 或 memory 变更。

## 用户校正追加：语义判断的承载位置

2026-10-08；沿用 bounded documentation worker / Skills=[]。本追加仅修改 TASKS 中 M1-014、M2-010、M2-014、M3-013 的验收描述和原 Handoff/通信文件；全部 5 新 Task 的状态、依赖、风险保持，72 DONE 和原 3 bridge READY 行没有编辑，不新增写域或 ID。

新增只读输入经文件名定位后读取 [ADR-0024](../../../decisions/0024-UNIFIED-ENTRY-AND-SHORT-TASK-ROUTING.md) 和 [SHORT_LANE_DESIGN](SHORT_LANE_DESIGN.md)，仅对齐入口扩展、职责可合并与原研究链保留；两者仍是 PR141 设计候选，不推导当前实现或已接受事实。旧 Packet/最新校正由可见 Root 消息提供；本追加完整原文及 Agent 可见输出写入原通信文件，ignored 原件保留初次通信，不在本追加中改写。

新增验收区分角色语义判断与确定性 diff/hash/ref/版本/权限预算检查。Prompt 与 Skill 绑定是可选承载路线，角色评审/版本绑定不代替 Skill 的适用资格；不强制每次 Skill Supply，不硬编码逐案意图或影响，不固定角色/API 次数，也不重构研究主链。具体角色 Prompt/Skill 版本、路由 Profile 和判断质量仍是后续实现/验收输入，未生成或验证；没有新增核心 Schema 提案。

本追加没有运行 tests/API/生产 Tool/Key/账/代码/Git 或文档治理 checks；Root 仍负责正式复核。交付 SHA-256 由最终聊天返回，避免本文件自哈希；本轮落盘后停止。
