# AUDIT-RWB-DOCS-004：真实化 Task 定义 Compact Handoff

2026-10-08 · Agent Profile=bounded documentation worker；required-Skills=[]。文档候选工作树，PR141 task-definition；不是实现完成、共享接受或合并记录。

## 本次交付

只修改 [TASKS](../../../TASKS.md)，新增本交接与[完整公开通信](REALIZATION_TASK_COMMUNICATIONS.md)。另按 Root 后续扩展写域，在本地 ignored `.rwb/docs004-communications/control.md` 保存含原机器路径的完整 Packet；不加入 Git。公开通信明确工作树路径规范化，不冒称 byte-exact 原件。

- 在对应 M family 写入 Root 固定的 19 个 exact ID、5 READY/14 PARKED；原 M1-010/M2-009/M11-008 仍 READY，合计 22 个候选定义。Packet 初写“21”由 Root 确认为计数误写，不补 ID。
- 删除 TASKS 顶部 active 人员分工、风险/阶段索引的 Owner 列及未 DONE 定义中的指定人员限制；M6 标题去人员标注。M11/M14 的原人员列仅改标题为历史记录，M11-008 填 `—`，原三条桥接 Task 的其他语义保留。
- 原 72 条 DONE 行未作为编辑目标；正文明确其人名、双方接受和签字条件是历史验收记录，不约束未来分工。M3-007、M5-008、M6-005 取消指定人员，但 actual actor/Archive 可追溯、方法/科研/Human/权限/发布边界保留。
- 风险/Phase 按 Root 的无人员索引填写：M4-006、M2-013 为 R1（触及 authority 敏感路径时升级），其余 17 个新 Task 为 R2。索引只给导航，不复制状态。
- M0-008 单独定义机器治理/模板/远端门禁的后续同步，未声称配置、代码或远端已经修改。Root 报告新增 ADR-0023 和更新 Development，本 worker 未读 ADR 正文或复核其接受状态。

## 新 Task 状态与 hard dependencies：交付快照

后续实时状态仍只由 TASKS 维护，本表是本次定义交付记录。

| ID | 状态 | dependencies |
|---|---|---|
| M0-008 | READY | M0-004, M7-001 |
| M1-011 | PARKED | M1-010, M8-006, M9-007 |
| M1-012 | PARKED | M1-011, M4-001 |
| M1-013 | PARKED | M1-012, M2-010, M6-011, M11-009 |
| M2-010 | PARKED | M2-009 |
| M2-011 | PARKED | M2-010, M8-006, M9-007 |
| M2-012 | PARKED | M2-010, M11-007 |
| M2-013 | PARKED | M2-010, M11-008 |
| M3-010 | PARKED | M1-012, M2-009 |
| M3-011 | PARKED | M6-011, M6-012, M11-009 |
| M3-012 | PARKED | M1-012, M11-008 |
| M4-006 | READY | M4-004, M6-002 |
| M4-007 | PARKED | M1-012, M11-009, M4-003, M3-009, M10-003 |
| M6-011 | READY | M6-009, M6-002 |
| M6-012 | PARKED | M6-011, M11-008 |
| M8-006 | READY | M8-005, M8-003, M9-005 |
| M9-007 | READY | M9-005, M11-002 |
| M11-009 | PARKED | M2-009, M2-010, M11-008 |
| M11-010 | PARKED | M1-013, M2-011, M2-012, M2-013, M3-010, M3-011, M3-012, M4-006, M4-007, M6-012, M8-006, M9-007 |

人工逐项对照时，5 READY 的 hard dependencies 均在原 DONE 行；19 项新 DAG 未见环或重复 scope 的定义冲突。此处是阅读判断，没有运行依赖 validator 或治理检查；Root 已确认 5 READY/all19 的列表。

## 修改依据与实际读域

当前 Packet 与 Root 后续计数/风险/路径规范化消息是本轮定义依据；继承 READONLY-REALIZATION-001/004 的有界盘点，区分人员分工、授权 ceiling、方法/能力选择、实际加载、实际运行与科研接受。

本工作树实际全文读取：`AGENTS.md`、`docs/README.md`、`docs/DEVELOPMENT.md`、`docs/TASKS.md`、`docs/M_SERIES_IMPLEMENTATION_MAP.md`、`docs/ROADMAP.md`、`docs/STATUS.md`、本 workstream 的 `README.md`、`RISK_LEDGER.md`、`DOCUMENTATION_TASK_PACKET.md`。施工图初次按 implementation 下路径查找不存在，随后仅文件名发现定位到 docs 根；首次合并输出截断的 ROADMAP 后续单独补读。TASKS 写前重读当前入口，写后只查看目标段落。没有新读源码、ADR 正文、实际项目/原件、账、Key、另一代理域或 primary memory。

写域仅 `docs/TASKS.md`、本交接、本通信，以及 Root 后续明确授权的 ignored 原 Packet 文件。未改派生施工图/路线图、代码、配置、Schema、Registry、稳定表面或其他人的文件；没有 Git mutation、安装或再委派。

## 验证限制、未决与下一动作

本 worker 未运行产品、API、Tool、测试、文档/治理 checks；不声称验证通过。最终由 Root 核对 72 条 DONE 行相对原定义逐字未变、原三 READY 行允许差异、新 ID 唯一/deps/DAG、表结构、Markdown 链接及治理要求，并冻结最终 pins。

1. Root 的派生导航需采用新的 M6 标题 anchor 和无人员索引，及相同的 19 个 exact ID；本组不改派生计划。
2. 固定人员机器映射、配置/模板和远端实际门禁仍待 M0-008 feature 验收；本次 docs 不产生这些实际变化。
3. qualified Skill 的真实准入/供给是外部前置，不能以空 index、candidate 或 oracle 伪造；零 Skill 路径独立，M11-010 不能用该路径冒充已验收合格 Skill。
4. 普通选择不都变成人工审批；M8-006 保留 proposal/eligible/decided/executed 与歧义、放宽、Claim 人类边界。改变 authority/排序/歧义语义先 ADR。
5. M3-010/011/012 只做获准读取、当次结果/修复与显式新 Task；不激活 M3-001/M12。Topic 5、科研接受、M5 四臂净价值与复杂真实研究授权仍独立。

原文件 SHA256 在返回消息列出；后续 Root 编辑/检查须重新冻结。此交付后停止，不提交、不推送、不写共享记忆。
