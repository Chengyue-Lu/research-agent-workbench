# 通用全链路桥接任务定义

任务：原三项桥接及本轮 19 项真实化后继；Audit：AUDIT-RWB-CHAIN-002 / AUDIT-RWB-DOCS-003 / AUDIT-RWB-DOCS-004；风险 R2。

2026-10-08 人类同意真实环境盘点，要求切分 M Task、与上一轮全文档校准一同推送 PR141，并取消所有固定开发人员分工和指定人员签字限制。先读 [下一阶段实施计划](REALIZATION_PLAN.md)，查精确任务读 [TASKS](../../../TASKS.md)。本轮仅更新文档，不实现或调用 API，最终由人类审阅 PR141 后决定合并。

范围扩展为 AUDIT-RWB-DOCS-003：2026-10-07 路诚钺要求全文档校准 M 系列/架构缺口、歧义及臃肿。
[全文档 Packet](DOCUMENTATION_TASK_PACKET.md)声明全体系覆盖、互斥 ownership 和原件保留边界。

2026-10-07 路诚钺要求先校准 Task 与文档，随后直接测试每个桥接，并同步准备角色提示词与 Skill。采用有界合成材料；真实科研案例和系统净价值评价保持后续任务。Root 是唯一整链/API/Tool 测试执行者，开发与资产准备可有界协作。

此 PR 仅做文档校准与 Task 定义；分支 READY 表示 hard dependencies 均 DONE，不表示定义已经合并或产物已经完成。代码候选 [PR140](https://github.com/Chengyue-Lu/research-agent-workbench/pull/140) 的实际桥接证据保持独立身份；Task 完成仍须对应完整验收证据。旧 Packet 和审计记录解释当时范围，现行人员规则以 [ADR-0023](../../../decisions/0023-DEVELOPMENT-WITHOUT-PERSON-ASSIGNMENTS.md) 为准。

## 定义与执行顺序

唯一完整 Task 定义、状态、依赖和验收位于 [TASKS](../../../TASKS.md)。三切片可独立复用已 DONE 接口；M11-008 最终 Gate 仍要求实际消费 M1/M2 对应产物，不能因没有新 Task 间硬依赖而跳过接合证据。

1. M1-010：需求/材料 → 实际 intake 输出 → 受控 Protocol/Task/Method/Requirement → downstream exact refs。
2. M2-009：角色 baseline/Profile/input → main 0..N 决定 → fresh children → 新 main 消费，统一预算。
3. M11-008：exact selection/freeze → Bundle/View/Host → Tool/合格 Skill 可选支线 → Trace/Receipt → Handoff/checkpoint/Human 待办/独立 Guide。

每个测试列出实际输入、producer 输出、消费这些输出的 consumer、断言及缺口。先确定性结构/引用/预算负面验证，再由 Root 使用既有授权和累计账执行隔离 API；不自动重试，失败及 unknown 留证。候选 prompt/Skill 均隔离保存，不能自行制造 Registry admission 或资格。

M5-008 保留四臂工程评价身份；本任务不替代其 Pilot、M5-004 净价值评价或具名评审。M12/Topic 5 保持原 Gate；人工声明旧状态与 Guide 读取复用文件契约，不产生自动恢复。

## 验证与接受边界

文档验证检查 exact ID 唯一、READY deps 全 DONE、全部新任务 DAG、原 DONE 行内容不变、内部链接及治理元数据。文档/公开闭包与结构检查记录在 [静态检查](STATIC_CHECKS.md)；API 桥接另在实现 PR 取证。R2 按风险与证据审查，不要求指定人员；代理不制造 live/Skill/科学或 Human 接受。机器人员政策同步单列 M0-008，不声称本 PR 已改配置或远端规则。

见 [风险记录](RISK_LEDGER.md)；现有 accepted [架构方向](../../../ROADMAP.md) 与 [施工导航](../../../M_SERIES_IMPLEMENTATION_MAP.md)。

## 整体贯通的结果标准

来自本轮人类补充并经开发（4）转交：入口收到需求后，在已有授权内形成 Protocol、拆分及选择，匹配不足要明确退回原因；
执行独立推进，交付实际结果和可溯源材料，留给下一轮显式接续。运行中不增加无必要的人工干预，遇权限/资格/输入/预算
不足时形成确定的 blocked/waiting/rejected 结果。本轮通过补接点贯通现有模块；未知/不支持需求不宣称成功。
自然语言需求的任意措辞不等于无限方法覆盖；支持范围由现有 Mode/Capability 和授权上限限定。
