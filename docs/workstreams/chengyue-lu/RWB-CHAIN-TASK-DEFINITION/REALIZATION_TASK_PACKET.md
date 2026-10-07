# AUDIT-RWB-DOCS-004：真实化任务与人员规则扩展

2026-10-08；R2；PR141 task-definition。人类授权把已同意的盘点切成 M Task、与原全文档更新一起推送 PR141、更新下一阶段计划，并取消固定人员开发限制。输出是可审阅的定义与计划，本轮不实施、不运行 API、不接入真实研究或合并。

## 输入与写入

来源：本轮直接人类指令、已有有界源码盘点、原 PR141 文档、PR140 固定候选身份及继承的实际桥接报告。读取全体系文件/标题/匹配行 metadata，正文限 AGENTS/README、TASKS/Development/Architecture/地图/模块/规划/状态、相关接口、当前 workstream 与 active 文档直接链接的资格 Gate；历史原报告、私有评价答案、凭据和 API 账不展开。

写入限本分支的 Markdown/文档 inventory：exact TASKS、唯一 REALIZATION_PLAN、派生导航、active 人员规则、ADR-0023、风险/审计/交接/通信/检查。primary PROJECT_MEMORY 仅更新本任务 own-row，写前重读保留他人内容。代码、Schema、Registry、治理配置和远端门禁不改；历史 DONE/ADR/接受记录不回写。

## 有界委派与输出

Profile=bounded documentation worker / targeted reviewer；required-Skills=[]。19项清单经计数更正固定为5 READY/14 PARKED。文档工作互斥划分 TASKS、12稳定架构面、4派生导航面，后续窄审只读定义/计划/人员规则/功能边界。每项输出 Compact Handoff、实际读写范围与可见通信；20分钟/2轮，窄审10分钟/1轮。保留他人编辑，不做产品/API/Tool测试、读取Key/账、Git mutation或全局记忆写入。遇需改变核心语义或授权外范围，报告具体事实并停止对应修改。

公开通信将机器 checkout 前缀映射为 repo-relative，明确不是 byte-exact 原件；完整可见消息留在 ignored `.rwb/docs004-communications/`。不保存隐藏推理或秘密。Task/Handoff pins 是交付时快照，最终身份以 PR commit/blob 为准。

## 验证、决定与停止

统一整合后检查 Task ID唯一、新DAG/READY deps、72原DONE行不变、内部文件/active锚点、公开文档和发行闭包、Task示意Schema、实际PR治理/CI及staged范围。验证只证明对应结构/文档事实，不证明API、科学或Task完成。新任务定义的实现、真实 Skill资格、Topic5与M5评价均后续独立。

M11-008 的 Core与可选Skill验收条件在独立窄审后明确，避免Core与未来loader互等。M0-008另行同步机器人员限制；现行文档不再要求固定人员参与/签字。交付 PR141 后停于人类检查/合并，不能由文档授权自行继续实现或测试。
