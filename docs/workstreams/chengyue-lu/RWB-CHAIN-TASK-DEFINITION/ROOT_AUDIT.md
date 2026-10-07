# 全文档校准：结果与覆盖

2026-10-07；AUDIT-RWB-DOCS-003；具名 owner 路诚钺；Runtime/共享接口接受保留黄毅审查；R2。

## 修复的主要问题

| 问题 | 处理与必要性 | 位置 |
|---|---|---|
| M 系列 Task 与派生状态矛盾 | M6-010/M5-007/M14 的旧状态/日志从派生面移除；TASKS 保留 exact 定义与接受状态 | TASKS、ROADMAP、施工图、STATUS、owner 索引 |
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

文档候选完成后由 Root 继续原全桥测试，实际代码保留独立 PR140。开发（4）仅补现有 driver/executor/workflow，
无测试/API/Tool/Key/账操作。候选提示词及三个窄 Skill 已在实现 workstream 隔离准备，未安装或准入。
测试先验证 producer→consumer refs 与明确拒绝结果，再核现有 grant/history/source/time 运行实际 API；不重复无关矩阵，不自动付费重试。
