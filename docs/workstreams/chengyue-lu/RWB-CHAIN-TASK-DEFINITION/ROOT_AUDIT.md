# 全文档校准：结果与覆盖

2026-10-07 全文档校准及 2026-10-08 真实化任务扩展；AUDIT-RWB-DOCS-003/004；R2。旧校准证据保持下述阅读边界，最新任务与人员规则见 [下一阶段实施计划](REALIZATION_PLAN.md)与 [ADR-0023](../../../decisions/0023-DEVELOPMENT-WITHOUT-PERSON-ASSIGNMENTS.md)。

## 本轮扩展

人类基本同意真实环境盘点并要求并入 PR141。本轮增加 19 个 M Task（5 READY、14 PARKED），保留原 3 READY 桥接定义；逐项映射自然意图、初始化、决策事实、供给发现、角色/Skill/Tool 实际装配、动态子任务、工程环境、预算、大材料、质量/partial/修复、短状态、研究对象、Guide、安装入口与工程 Gate。

active 开发文档撤销固定人员分工和指定另一人签字前置，历史 DONE/ADR/验收事实保持。ADR-0023 记录本次直接人类指令，M0-008 承接机器配置和远端审核对齐；本 PR 不改机器政策、代码、Schema 或 Registry，也不把 API slice 完成认作 Task/科学接受。实施顺序只在计划中解释，exact deps/state/验收只在 TASKS。

独立窄审发现 M11-008 若将未来合格 Skill 正路径作为 Core 后继前置，会与未来 loader 形成语义上的互等。Root 澄清尚未合并的 M11-008：no-Skill/direct Tool Core 全桥及缺资格阻断独立验收，Skill 真正加载另由 M2-012/M11-010 闭合，M11-010 缺真实合格供给仍不能 DONE。未改 DONE 行或核心执行契约。

本轮委派限定为 TASKS、稳定架构、派生导航三个互斥文档面；实际读写范围、可见通信与未决点见本目录 REALIZATION_*_HANDOFF/COMMUNICATIONS。公开通信将 checkout 前缀映射为仓库相对路径，完整原文保留在本地 ignored 档案，不声称公开文件是 byte-exact 原件。Root 处理共同规则、接口 metadata、计划、风险、引用和验证。结构检查覆盖全部文档路径与新 DAG，不重新声称语义深读所有历史文档或运行产品/API。

## 修复的主要问题

| 问题 | 处理与必要性 | 位置 |
|---|---|---|
| M 系列 Task 与派生状态矛盾 | M6-010/M5-007/M14 的旧状态/日志从派生面移除；TASKS 保留 exact 定义与接受状态 | TASKS、ROADMAP、施工图、STATUS、风险/阶段索引 |
| 架构到应用入口职责不完整 | 明确需求/材料、协议/任务方法、冻结、主子运行、结果消费、Guide 的输入输出；职责可合并，不新增 core Role | Architecture、地图、10 模块 |
| 模块实现与可接通混为一谈 | 每模块声明 producer/consumer/产物/触发；实现、候选、live、科研评价分别取证 | 地图、STATUS、implementation 导航 |
| 单 Host 被误读成只能单 Agent | Host slice 固定一个 Driver；caller 可组织有界 0..N Tasks；Session 可多轮，权限与总预算不重置 | 模块03/05/09、Host、Provider 接口 |
| Assignment 被写成所有 Skill 的前置 | 当前 Projection/Supply/Snapshot/View + actual load 与 legacy Assignment lane 分开；模板/兼容/双臂 assessor 同步限定 | Architecture、模块04/05、compatibility、Skill evaluation |
| 来源驱动 Skill 与固定编制残留 | candidate pipeline 回到 Need-first；数量按 Task/Profile/config ceiling；角色必载职责不依赖方法 Skill | Skill candidate、模块04、地图 |
| 正式 Archive 与脱敏诊断留存冲突 | shape-only 仅限定 conformance/assessment report；正式 Task policy 的获准原件与真实 failed/unknown 仍捕获 | Provider、Skill evaluation、Worklog 模板 |
| 实现文档保存旧“本 PR/后继 BLOCKED” | State/Source/Promotion/Harness 改为接口范围及现行权威链接，旧原件不改 | 对应 implementation 文档 |
| 文档重复且体积大 | 地图/ROADMAP/STATUS/施工图/接口索引去重复状态和实施日记，保留独有规则与原证据入口 | 同名 active 文档 |

新增候选 M1-010/M2-009/M11-008 分别验证 intake/control 产物、角色/动态主子消费、冻结执行/closeout 全桥。
分支 READY 仅表示硬依赖均 DONE；不把定义、PR140 局部测试或文档更新当作全链实现接受。

## 实际覆盖与保留边界

三组分别通读全部 M 系列与规划、14 份架构/模块、六个读者面；阅读清单和依据见
[Task audit](TASK_AUDIT.md)、[Architecture audit](ARCHITECTURE_AUDIT.md)、[Surface audit](SURFACE_AUDIT.md)。
Root 深读共同入口、implementation 索引、Provider/测试策略/冻结执行/Trace/状态及准入关键段、兼容与工作流索引；
其余接口按标题/边界/引用做结构核对。全仓 Markdown 机器 inventory/内部链接扫描不等于所有历史正文的语义深读。

Accepted ADR 正文、历史 Trial/Attempt、原验证报告、原 DONE Task 行、Schema、Registry、代码和 package 来源在此 PR 保持原内容。
历史 work 记录中三条既有链接缺失仍列在 [静态检查](STATIC_CHECKS.md)，不补造缺失原件；active 入口保持可达。
语义/权威的实质改变仍要新 ADR；本轮澄清已有边界及新桥接 Task，不暗中解冻 M12/Topic 5 或代签 Skill/source/live/科学接受。

## 验证与下一步

Root 已运行公开文档/发行闭包三项测试 PASS，模块05 Task 示意通过现有 Task Schema；旧 DONE 行内容变化为零，
三新 Task 的 hard dependencies 均 DONE。全文件路径/heading 扫描与最终治理/CI结果以 [检查记录](STATIC_CHECKS.md)和 PR 为准。
独立窄审发现的 Harness 旧 IN_PROGRESS 已修复；没有用文档 PASS 宣称 API 或科学 PASS。

[最终限定交叉审查](FINAL_NARROW_REVIEW.md)没有发现新的 P 级问题，其实际读取范围与输入路径更正在原记录中保留。
各代理 handoff 的 SHA-256 指其交付时的工作文件；Git 的行尾规范化及 Root 后续修改可能改变最终文件字节，
最终交付应按 PR 的具体 commit/blob 读取，不能把原 handoff pins 当作最终版本的重新接受。
Draft [PR141](https://github.com/Chengyue-Lu/research-agent-workbench/pull/141) 首版的 governance、plan、Component (3.11, shard 0) 与 CI result 全部通过；
文档本地路径检查零新增缺失、active 锚点零问题。已保留三条 baseline 历史链接缺失。

当前下一步由人类审阅 PR141；合并后按新计划和 TASKS 激活实施，不从本次文档授权启动付费测试或真实研究。PR140 与其资产候选保持独立，提示词/Skill 未因文档更新获得资格；后续测试按适用 grant/source/config/history/time 重核。
