# 风险与剩余边界

| 风险 | 应对与验收 | 当前状态 |
|---|---|---|
| Role配置存在而未进入模型请求 | 实际startup/request内容pin与消费测试；必载baseline | no-Skill路径已实现/离线验证；required Skill未实现阻断 |
| 前端未授权/未成型控制工件被Runtime消费 | 独立人类ceilings、Schema/pins；explicit完整冻结链，无fake资格 | 控制producer→Runtime实际接通；自然语言planner与真实来源适用性待补 |
| Runtime重选Supply或silent fallback | 仅消费冻结选择；调用既有Bundle/View/Host，漂移阻断 | 支持的procedure路径已验证；可信observer/verifier由caller负责 |
| 主子预算/取消/失败遗漏 | 整个执行范围统计，actual attempted而非responses；unknown保留，不自动paid retry；Task末轮复检 | 原R2/R3已修复并独立复查；合作取消不保证硬中断 |
| 任务完成与Claim/Human接受混淆 | 执行slice、main处置、人类决定分别记录 | 报告/receipt false authority守卫测试通过；Task语义接受仍待 |
| Guide问答污染main/项目 | 独立caller、获准快照、无Tool/write/message/Trace-state writer接点，反例测试 | 已实现/离线验证；外层remote授权/timeout/usage账由caller负责 |
| 多writer/局部提交失败 | 首轮单提交者/独占发布，保留失败；不宣称CAS或全事务；state从fixed report取值 | 原R4已修复并复查；覆盖/篡改拒绝，CAS/全事务未提供 |
| legacy Handoff非空Skill锁 | Compact/generic路径明确支持范围，正式迁移独立定义 | 保留 |
| M12/Topic5被普通续接暗中解冻 | 新窗口只规划，manual新输入与自动恢复分开 | 保留 |
| synthetic测试被当live/科研正确性 | 注入Provider/Driver标明测试来源，live资格独立 | 保留 |

回退：撤销本分支新增的可选入口代码与相关使用文档；既有契约/Registry/已DONE Task保持原bytes。发布与合并由具名人类及实际PR规则决定。
