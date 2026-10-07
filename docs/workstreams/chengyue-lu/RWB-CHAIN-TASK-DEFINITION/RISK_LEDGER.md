# 风险记录

| 风险 | 控制与证据要求 | 保留的决定 |
|---|---|---|
| 与 M5 评价范围混淆 | 三 exact Task 单独定义；桥接表不产生四臂净价值结论 | M5 Pilot/case/评价接受 |
| 用 fixture 或 bare callback 宣称整链 | 逐桥记录实际 producer pins、consumer、请求/响应及冷回放 | source/provider/live 资格 |
| 模型控制输出扩权 | 独立 human ceilings；整 wave 预检；known/unknown 统一账 | 权限/预算与 Human Gate |
| 候选 Skill 绕过准入 | required Skill 缺失 preflight block；合法 projection/use-boundary 才启用支线 | Skill admission / release |
| checkpoint 被当自动恢复 | fresh caller 显式输入；Guide 无写入/自动回传 | Phase C closeout / Topic 5 |
| 文档把 candidate 写成 accepted | docs-only PR 不置 DONE、不修改旧 DONE 行；完成按对应验收证据 | 科学/Human/合并与发布决定 |
| 撤销人员分工被理解为降低功能权限 | ADR-0023 区分开发安排与 Human/Resolver/Runtime 权威；机器政策由 M0-008 对齐 | 权限、数据出口、Skill/来源/Claim 接受 |
| 演示上限、固定角色与检查阻断进入产品默认 | M6-011/M2-010/011/M11-009 按任务能力/预算和真实结果配置；旧测试原件不改 | 人类预算、unknown holds、选中供给使用边界 |
| 部分失败被修复或主消费掩盖 | M3-011 保留 failed/unknown/partial/副作用；Task assessment 与 action-only Receipt 分开 | 科学接受与外部恢复权限 |
| 真实化任务绕过 Topic 5 | M3-012 只处理当前 Task 状态与人工新 Task 输入；自动 rollover/resume/recovery 单独 Gate | Phase C Human/R2 与 M12 激活 |
| 前置分流改变既有研究主线或成为新 selector | ADR-0024 只扩展应用入口/分支；研究流程和 Resolver 的选择权保持 | 核心身份、方法与供给 authority |
| 角色判断被固定标签或 Schema PASS 替代 | Skill/提示词实际版本、评审、理由/未知与真实 diff 留证，程序只核结构/权限/版本 | 路由语义、Task 内容与科学接受 |
| 后置评估为先写入追认权限 | 写前核授权、目标版本和活动输入冲突；无影响也须 refs 有效，相关/未知提案不自动 MainState | 副作用授权、状态采纳与受控 writer |
| 统一对话引入历史污染或任意 child 控制 | 目标/最小上下文/实际 API recipient 核对；旁路无默认 main 回传，child 修改经所属主 Task | 任务与会话隔离、活动失效最小通知 |
| 人类采纳旧提案覆盖新 MainState | 提案绑定读取 revision；writer 消费前重查，漂移重评估，不改伪 hash | 当前状态与输入的精确版本 |

权威依据：2026-10-07 人类授权全文档校准；2026-10-08 同意真实化盘点、定义 M Task、更新计划并推送 PR141，又明确撤销人员限制并补充前置层/分支与角色规则分工。accepted 功能契约、权限/资格及 merge/release 边界继续适用；本轮不调用 API、不实现、不合并或制造接受。
