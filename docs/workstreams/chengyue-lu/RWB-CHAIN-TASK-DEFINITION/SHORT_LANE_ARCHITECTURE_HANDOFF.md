# 统一入口短程架构接点：Compact Handoff

2026-10-08；AUDIT-RWB-DOCS-005；Profile: bounded documentation worker；required-Skills: []。

## 结果与边界

六个授权架构文档已补入明确的设计候选小节。统一入口在研究 Protocol 编译前分流 Guide、独立短程 Task 和完整研究；Guide/Short 在 main 旁，保留分别受控的上下文、权限与接收者。main 保持原 Task，短程不要求每次建立或修订完整研究 Protocol，执行复用现有 no-Skill/direct Tool 的最小 Method/Requirement、合法 selection、Bundle/View。

路由按语义影响而非工作长度。写前协调当前 main/child 的目标占用及共享写冲突；写后以 actual diff、refs、冻结 Main State 版本和敏感语义区分 none/relevant/unknown。无语义影响只留局部 change record；相关或未知影响形成待采纳状态提案并暂停相关发布。人类明确采纳、当前 state pins 一致和受控 writer 是新 revision 的边界。活动 main/child 的输入失效通知不受默认静默旁路豁免；该检查不授权自动恢复或科学接受。

原完整研究传递图与功能权威保留。应用接合候选没有新增 core identity、Runtime selector、全局 Supervisor 或 permission grant。当前是否支持 router、短程写入及状态影响评估仍由 STATUS 的实现证据判断。本轮没有实现或测试这些行为。

协调者随后传递的人类校正已落实六文件：这是既有主线之外的前置入口/新分支，不修改 Protocol→main→0..N child→Handoff→Main State→human。文档限定职责、权限、I/O 和分支；经版本绑定与评审的职责 Prompt 或合法 Skill 承载意图、路由及语义影响判断。确定性校验不替代语义判断，低置信澄清/提案；Guide/Short 是概念职责，不固定 API 角色。该澄清不要求每次调用 Skill，不扩大 Skill 准入或执行权限。下面定位为此前复读定位；最后补充插入后后续行号顺延，按小节标题定位。

## 实际改动与定位

| 路径 | 修改段 | 责任接点 |
|---|---|---|
| [ARCHITECTURE](../../../ARCHITECTURE.md) | 第 58 行、105–122 行 | 完整研究入口限定；统一入口、旁路与人类状态采纳边界 |
| [开发者地图](../../../DEVELOPER_ARCHITECTURE_MAP.md) | 52–68 行 | 三入口 producer/consumer 及实现候选限定 |
| [模块 03](../../../modules/03-AGENT_RUNTIME.md) | 154–166 行 | 独立调用职责、上下文、main Task 与 child 治理 |
| [模块 05](../../../modules/05-TASK_AND_HANDOFF.md) | 81–94 行 | 最小 Task、冻结执行链及局部结果/状态提案 |
| [模块 06](../../../modules/06-CONTEXT_GOVERNANCE.md) | 92–108 行 | actual diff 与 state pins；影响分类和失效通知 |
| [模块 09](../../../modules/09-ADAPTERS_AND_INTEGRATIONS.md) | 17–29 行 | 上游合法 binding、独立 session 与 Adapter 消费边界 |

详细规范由协调者维护的 [ADR-0024](../../../decisions/0024-UNIFIED-ENTRY-AND-SHORT-TASK-ROUTING.md) 和 [SHORT_LANE_DESIGN](SHORT_LANE_DESIGN.md) 承担。本工作只增加接点摘要，没有代写上述两文件或 Task/plan。

## 实际读集与收尾字节身份

仅阅读以下授权路径，以及本次 Packet/可见传递和本次新增工件。下面的 SHA256 是收尾时文件元数据快照；六个修改文件为修改后身份。其他工作者可能继续修改，不能把此表当作整个 PR 的冻结基线。正文定位使用阅读时行号。

| 路径 | 正文审阅范围 | SHA256 |
|---|---|---|
| AGENTS.md | 全文 1–47 | 6e6975107025f24f3c067322f178a060e1ef2913df7b80739636ed40967a71d7 |
| docs/README.md | 全文 1–40 | 29c6ac6ed7bb05c49cab75907ad7e60f68b8e7489a0e7d06e24d363f24451a6e |
| docs/DEVELOPMENT.md | 全文 1–98 | a6bcfe7bdc995c9f8920d8dc8de315fd2985a8ce58cbc5a6d12106b9a030d54d |
| docs/ARCHITECTURE.md | 原全文 1–200；改后重点 55–130 | 631c92e393b8a038912717171e8a5469ca9fbfb2c9a7806e2cd059cbde9e1c92 |
| docs/DEVELOPER_ARCHITECTURE_MAP.md | 原全文；重点原 1–80、改后 39–77 | 1ba5eb7b44e55fb1eacd80d4c8eb2293a301998dec13f7694a48dcc0c02e8f7a |
| docs/modules/03-AGENT_RUNTIME.md | 原全文 1–202；重点原 1–31/135–156、改后 149–178 | 2a941f9982003ecc236b738c163d83d657e7d8393e056a096565f320e5a556f0 |
| docs/modules/05-TASK_AND_HANDOFF.md | 原全文 1–231；改后 79–104 | cf3edf174fda627f1ace9ef0f8708db4ba6c2a448ed7e091967047eeeb84d365 |
| docs/modules/06-CONTEXT_GOVERNANCE.md | 原 1–111；改后 82–122、100–108 | 6572851ef3259a4361f2fff06c6c2cfd951cde4d1decd12a3227f4be71828100 |
| docs/modules/09-ADAPTERS_AND_INTEGRATIONS.md | 原 1–40/120–152；改后 12–36、25–29 | 43cf24dc2410996febc2ecdbe0560e06724863166a138007f6649b370b1b57ab |
| docs/STATUS.md | 原 1–105，实际 EOF 为 64；补读 1–18 | 5f71bd9169669a06e84fc916b20c08a7774d9ba839de51eff06a4e864480a6c1 |
| docs/workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/REALIZATION_PLAN.md | 原 1–80，实际 EOF 为 68 | 35da318ed8ea46ea94494a72a8065eb00356ca1dd18e105a589facc3240ccb76 |

工具批次出现输出截断；需要修改的接点另行按段补读，不据截断部分作新增实现结论。未读取代码、Schema、Registry、配置、历史工作流、其他窗口目录、Key、账或新 ADR/详细设计正文。新 ADR/设计链接由 Packet 明确允许指向协调者将创建的路径。

## 两轮文字复核与限制

第一轮据现有架构/模块接点写候选摘要；第二轮复读六处改段，进一步明确模型/API binding 的选择冻结属于上游控制侧，并将 none 示例限定为主张、来源、方法、决定、目标、里程碑和依赖的语义均未变。此为手工文档复核，没有执行 Markdown checks、测试、Host、API、生产 Tool、cold、Git mutation、预占或账读写；不报告 validator PASS、已实现或 Human Gate 通过。

文档编辑本身没有遇到需要改变 core identity/selection/Human 权限的阻断。ADR-0024 仍为 proposed 设计候选；详细契约适配、实现及接受留给对应工作。既有 Topic 5 自动连续性边界保留。

下一决定由协调者完成：将 ADR/详细设计/Task 定义与这些摘要共同审阅，检查实现状态表述和相对链接，再执行本 PR 的文档验证。若后续实现需改变核心对象或权限语义，须先按独立 ADR/版本与人类决定处理，不能由本 Handoff 推定批准。primary PROJECT_MEMORY 未写入；本摘要可由协调者在其授权范围内纳入项目接续记录。

可见通信见 [SHORT_LANE_ARCHITECTURE_COMMUNICATIONS](SHORT_LANE_ARCHITECTURE_COMMUNICATIONS.md)。原 Packet 与本次可见传递仅存 ignored `.rwb/docs005-communications/architecture.md`；公开通信使用仓库相对路径和规范化摘要，不宣称为原文的 byte-exact 副本。
