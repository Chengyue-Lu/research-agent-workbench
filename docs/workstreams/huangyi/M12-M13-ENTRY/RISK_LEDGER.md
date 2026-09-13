# 风险记录

Audit：AUDIT-M12-M13-ENTRY-001；owner：黄毅；跨 owner 语义归属：路诚钺。当前是 R2 审查输入。

| 风险 | 当前事实与控制 | 状态 |
|---|---|---|
| machine PASS 被当成 Human closeout | 两个 fixture Decision 均非真实负责人接受；语义审查表保持具名决定 PENDING，历史报告不改写 | 保留人类决定 |
| 文档 merge 被当成 M12/M13 解冻 | TASKS/ROADMAP/Schema/Runtime 不变；独立语义决定、Topic5 review、Task definition 分开 | 范围明确 |
| legacy recovery 预检冒充接续 | RecoverySeed 只作风险/迁移参考，不预定 no-Skill 公共 contract；字段保留/投影/废弃由独立 Topic5 R2 定义决定 | 待后续定义 |
| 接续重复执行或扩大权限 | 下一 frozen action、唯一新 Attempt、源 pins 与既有 consumer；选择变更返回原 Resolver | 候选验收边界 |
| 协作偏好升级科学准则或公共 Skill | 作用域/版本/用途/撤回与 Need/Admission 分开，运行中的冻结链保持不可变 | 待具体样本和设计 |
| M13 归因被误作激活或重造 M7/M9 | 采集/归因不激活；须 Phase C semantic closeout、所需 Phase D evidence、coherent family 缺口证据及独立 docs-only R2 定义；可复用或暂缓 | 缺口未证明 |
| 本地反馈归因被扩大为自动采集或外发 | 仅使用科研中自然产生且获准用于该次分析的本地记录；原授权有效、未撤回、范围未变才继续使用；不启动 telemetry/自动捕获/上传 | 用途明确 |
| 工程案例被写成反馈/科研收益 | 合成 fixture、代码 bug、模型行为样本和独立后续 Task 评价分别标明 | 未声称效果 |
| 新主线挤占 M5 或触发重复测试 | 材料可并行，实施考虑 owner 容量；本次只有文档/来源窄检查，不改 M5 前置 | 受范围控制 |

首轮不建立签名系统、continuity database、全局 Supervisor、第二套候选生命周期或训练后端。后续需要它们时必须有独立、可复现的问题和取舍依据。
