# AUDIT-RWB-DOCS-004：Task 定义完整可见通信

2026-10-08 · Profile=bounded documentation worker；required-Skills=[]。公开内容采用 repository-relative 路径：下方完整 Packet 的 DOCSWT 机器工作树前缀只替换为 `.`，其他正文未摘要。含原路径的 byte-exact Packet 另保存在本地 ignored `.rwb/docs004-communications/control.md`，不加入 Git；本公开文件不是 byte-exact 原件。

## Root → worker：完整 Task Packet（仅 DOCSWT 路径规范化）

```text
执行 docs-only Task Packet AUDIT-RWB-DOCS-004/TASKS定义。Profile=bounded documentation worker; required-Skills=[]。DOCSWT=.。允许读取 AGENTS/docsREADME/DEVELOPMENT/TASKS/M_SERIES_IMPLEMENTATION_MAP/ROADMAP/STATUS 与 RWB-CHAIN-TASK-DEFINITION现有README、RISK_LEDGER、DOCUMENTATION_TASK_PACKET，以及继承上一轮盘点。只写 docs/TASKS.md + workstream REALIZATION_TASK_HANDOFF.md/REALIZATION_TASK_COMMUNICATIONS.md；不改派生计划、其他文件。用户已同意盘点并要求切为M任务推PR141，又取消所有人员负责人限制（用户承接开发，无需写谁负责什么）。撤销TASKS active责任分工/index人员列和非DONE定义中的指定人员/签字限制；72原DONE行逐字不动，明确这些为历史验收记录、不构成未来分工限制。既有 M1-010/M2-009/M11-008保持READY和语义，只移除M11-008负责人列值则会触碰整列？DONE表列不能改；可把该列标题改为历史记录，M11-008字段填 — 并说明不参与新任务授权。对新定义统一无负责人列。
新增21个exact Task（下面固定ID、依赖和状态，请用短可验收行写入相应M family，风险/Phase从无人员派生索引提供，不复制状态）：
M0-008 READY deps M0-004,M7-001：机器治理与模板的人员限制对齐（未来单独feature移除固定owner映射/跨指定人门禁，保留PR/CI/Task/权限风险；本docs不声称已改远端/配置）
M1-011 PARKED deps M1-010,M8-006,M9-007：自然意图→澄清→内部Protocol/Task编译，semantic自由与human授权上限分离，不要求human手填fullJSON
M1-012 PARKED deps M1-011,M4-001：从零研究基座/杂乱文件夹无MainState两种初始化，共同方法流程，范围版本冲突未知保真
M1-013 PARKED deps M1-012,M2-010,M6-011,M11-009：installed通用入口/config/consumer/human交付，摆脱Root私有harness/checkoutimports
M2-010 PARKED deps M2-009：角色baseline/提示词实际装配审核，intake/planning/main/specialist/reviewer/handoff/maintenance/Guide职责按需合并，Skill可选，提示优先级/注入/缺输入输出质量验收
M2-011 PARKED deps M2-010,M8-006,M9-007：main自主0..N与逐childMethod/Profile/Capability选择，选不同specialist和child实际消费，授权预算继承
M2-012 PARKED deps M2-010,M11-007：qualified Skill精确正文/resource加载→实际请求→use-boundary消费，candidate/oracle隔离，空index真实Skill路径仍待独立准入，不伪造Release
M2-013 PARKED deps M2-010,M11-008：Guide可见证据状态与解释验收，ref存在未读/已检查/失败/缺失区别，只读独立无自动main回传
M3-010 PARKED deps M1-012,M2-009：多格式大输入/Tool结果外置与按需回查compact child证据，新获准refs重冻，不扫全仓，普通selective读取不自动context rollover
M3-011 PARKED deps M6-011,M6-012,M11-009：partial结果/失败分类/预算内定向修复，新尝试保留失败unknown/副作用，非全局固定一次/无限retry，无Hostfallback/Topic5恢复
M3-012 PARKED deps M1-012,M11-008：当前Task MainState精简/风险关闭/历史索引+人工显式新Task读取；不定义automatichead/session/context迁移恢复，M3-001/M12不激活，触及Topic5停在独立Gate
M4-006 READY deps M4-004,M6-002：真实工程cwd/executable/依赖锁/Tool环境身份观察与可重建记录，root非cwd，成功/缺依赖/漂移证据，不默认自动安装
M4-007 PARKED deps M1-012,M11-009,M4-003,M3-009,M10-003：API工作结果到Source/Evidence/Claim/Run/MethodTrace/Need实际消费者桥，支持反证引用+promote条件，ResearchState候选语义/人类接受独立
M6-011 READY deps M6-009,M6-002：模型能力/项目/Task/剩余预算交集替代1024/6calls/120s/32KB等试验常量，单位分离actual usage/failed/unknown累计、动态预占，兼容旧版本
M6-012 PARKED deps M6-011,M11-008：受控真实read/write/execute/search Tool handlers+路径/进程/网络约束、实际/partial产物副作用，不只改label、readonly正常无写资格零执行
M8-006 READY deps M8-005,M8-003,M9-005：registeredfacts/obligations/pins→authority eligibility→实际Method/Binding决定producer；proposal≠eligible≠decided≠executed，歧义/放宽/Claim人类边界保留，权威变化先ADR
M9-007 READY deps M9-005,M11-002：Task范围供给catalog发现/可用性事实/逐候选排除不全局失败，Resolver唯一selector，multiple eligible不pickfirst，改变排序/歧义规则先ADR
M11-009 PARKED deps M2-009,M2-010,M11-008：Task选真实交付/内容和确定性完成checks/必要语义review，partial child可用与ParentGoal判定；独立Taskassessment不把action-onlyReceipt.task_completion改true，无科学自动接受
M11-010 PARKED deps M1-013,M2-011,M2-012,M2-013,M3-010,M3-011,M3-012,M4-006,M4-007,M6-012,M8-006,M9-007：工程真实化整链Gate；可控工程材料、2初始化、按需Mode/Skill/Tool/Profile/child+实际内容检查/失败保真/短State/Guide；qualifiedSkill外部前置不假装供给，零Skill路径独立，非M5净价值/真实复杂研究授权。
预算20min两轮，你不独自在仓库，保留他人改动。不得运行产品/API/Tool/checks，不读取Key账，不Git mutation，不代码configSchemaRegistry/primary memory。输出持久化修改依据、完整新ID/状态/deps与未决项、可见通信+Compact handoff，再短回传。发现依赖cycle/已有同scope矛盾先发Root建议，勿自行重编号。
```

## 可见消息顺序

worker commentary：

> 我会按固定 ID、状态和依赖更新 TASKS，保留原 DONE 行，并只在授权文档范围内移除未来任务的人员限制。先核对现有表结构和依赖；你列出的清单我数到 19 个新 ID，会请 Root 对照确认，不自行补号。

worker → Root：

> AUDIT-RWB-DOCS-004 已开始。Packet 写“21个exact Task”，但给出的固定清单实际为 19 个：M0×1、M1×3、M2×4、M3×3、M4×2、M6×2、M8×1、M9×1、M11×2。将按这 19 个精确 ID/状态/deps 落盘，不自行补两个号；如有遗漏请补具体 ID。先读允许面并检查现有依赖/同 scope 重叠。

Root → worker：

> 确认精确清单19项为准，口头21是计数误写；不补ID。保留5 READY/14 PARKED，新+原3共22候选定义。你的依赖列表是权威草案，感谢核对。

worker → Root：

> TASKS 现有依赖已逐项对照：5 个新增 READY 的 deps 全是原 DONE；19 项新 DAG 未见环，PARKED 与原 3 READY 的依赖关系匹配。将 M0 用独立 5 列新定义表（原4列/DONE行不动）、M11用无负责人5列表追加新Task，旧责任人表头改“历史记录”、M11-008填 —；移除 active 分工/index Owner 列及 M3-007/M5-008/M6-005 指定人员限制。M6 标题去“黄毅维护”，请派生导航更新对应anchor。请发送新19项无人员 risk/Phase/Topic 索引（或确认按M family既有风险阶段归类），我不从状态推导风险。

worker commentary：

> 依赖对照未发现环；新增 5 个 READY 的前置项都已 DONE，其余 14 个保持 PARKED。TASKS 中需移除的限制集中在顶部责任分工、Owner 索引，以及 M3-007、M5-008、M6-005；M11-008 只清空人员字段，原三条桥接任务的状态和验收语义保留。

Root → worker：

> 索引风险：M4-006与M2-013为R1（实现若触及authority敏感路径自动升级R2）；其余17项R2。Phase/Topic按family已有语义：M0 Governance；M1 Foundation/F Research Control+Contracts；M2 Foundation/F Agent Runtime+Research Control（012Capability/Skill+Topic4，013Read-only explanation）；M3 Foundation/F Context/Trace（明确012不解冻Topic5）；M4 C/F Artifact/Trace/Research objects；M6 F Topic4；M8 A Research Control；M9 B Capability/Skill Evolution；M11 F Topic4+Artifact/Trace。无需为每个新Task造重复表，可在风险索引按组分列；不写人员。5个READY/all19验证正确。请在通信保存收到Packet原文（非只摘要）及后续可见消息，handoff限定读写范围。

worker → Root：

> 19 条 TASKS 定义及无人员风险/Phase 索引已写入；原 DONE 行未作为编辑目标，原三条 READY 状态/语义保留，M11-008 人员字段为 —。本 worker 不跑 checks，最终由 Root 核 72 DONE 原文、依赖和链接。通信将保存完整 Packet 正文及全部后续消息，仅把 DOCSWT 的机器 checkout 前缀规范化为“.”并明确记录该转换，保持 repo 文档路径可移植；其余文字不摘要。M6 标题已改 API Execution，请一并改派生 anchor。

Root → worker：

> 规范化公开通信方案确认；请额外把完整Task Packet（包含原机器路径）留在ignored .rwb/docs004-communications/control.md，不加入Git。公开文件明确路径映射而非byte-exact原件。Root新增ADR-0023 personnel撤销，Development已改无分工，机器同步M0-008；riskR1x2其余R2。

worker commentary：

> 19 条定义和无人员风险索引已落盘：M4-006、M2-013 为 R1，其余为 R2；没有置 DONE 或启动实现。我正在保存完整通信和 Compact Handoff，检查由 Root 执行；机器治理与远端限制的实际修改仍留给 M0-008。

## 实际访问、编辑与运行界限

实际全文阅读：AGENTS、docs/README、DEVELOPMENT、TASKS、M_SERIES_IMPLEMENTATION_MAP、ROADMAP、STATUS，及本 workstream README/RISK_LEDGER/DOCUMENTATION_TASK_PACKET。M-series 图最初在 implementation 下不存在，经文件名发现读 docs 根；合并输出截断后补读 ROADMAP/STATUS 入口。TASKS 写前重读、写后只查看目标正文和自有交付路径元数据。继承上一轮只读分析，不再读取源码、ADR、实际项目/原件或另一代理域。

编辑仅 docs/TASKS.md、本公开通信、REALIZATION_TASK_HANDOFF.md 与 Root 后续授权的 ignored 原 Packet 文件。TASKS 采用局部 patch，DONE 行只作为定位上下文，没有编辑其正文；原三 READY 状态/语义保留，M11-008 人员列按 Packet 置空。19 条新定义及 risk/Phase 组索引均采用 Root 给定清单。

未运行产品、API、Tool、测试或文档/治理 checks；没有 Git mutation、安装、代码/config/Schema/Registry/primary memory 写入或再委派。依赖/DAG为人工读取判断，Root 确认清单；最终原 DONE 行不变、链接、表结构与治理检查由 Root 执行。本 worker 不声称 checks PASS。

## Compact

交付见 [REALIZATION_TASK_HANDOFF](REALIZATION_TASK_HANDOFF.md)；实时 Task 权威为 [TASKS](../../../TASKS.md)。新19项5 READY/14 PARKED，连原3项共22候选；没有新 Task DONE、实现/remote变化或 accepted/merge 宣称。M0-008 的机器同步、qualified Skill 外部前置、Topic5/科研/M5净价值边界保留。最终 SHA256 由交付消息列出，避免 self-hash；交付后停止。