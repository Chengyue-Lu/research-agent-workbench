# ADR-0024：统一对话入口与独立短程任务

状态：Proposed for PR141；2026-10-08 人类授权纳入架构与任务定义。当前实现支持见 [STATUS](../STATUS.md)，本决定不宣称已有统一路由或短程写回实现。

## 问题与依据

人类希望在同一个对话框提出不同需求，同时保持主研究任务的上下文和执行状态。询问、段落排序等局部编辑无需进入完整研究规划，也不应因为同屏显示就被送入 main 或其 child。局部写入后仍要判断实际变化是否影响全局状态，不能预先把“短程”当成“绝无研究影响”。

现有架构已区分独立只读 Guide 与主执行，但尚未完整定义 Protocol 之前的入口分流、同级短程写入与后置状态影响评估。本提案在既有研究主线外增加应用前置层和分支面；研究 Protocol → Task/Method → main 按需组织 child → Handoff/结果消费 → MainState → 人类决定的关系保持。文件契约、Resolver 的供给选择权和 Bundle → View → Thin Host 边界保留。

## 决定候选

1. 应用入口先根据人类意图、授权范围和最小当前 Task 元数据分流：只读询问、独立短程任务、研究需求、明确的当前主 Task 指令；混合需求拆为关联请求，歧义先澄清。仅研究需求进入研究 Protocol 的形成/修订与完整规划。具体意图、路径适用性与语义影响判断由经版本绑定和评审的角色 Skill 或提示词承担；架构定义职责、输入输出、权限及分支边界，不将逐案判断硬编码进研究内核。
2. Guide 与短程任务是 main 旁的独立职责，不是可由人类任意修改的研究 child。短程任务复用有界 Task、输入版本、能力/权限、预算和输出检查；不为每次局部编辑创建研究 Protocol，不为无方法需求的编辑虚构 Research Mode/Skill。能否消费现有 no-Skill/direct Tool 控制闭包由后续实现证明，缺能力明确 gap。
3. 单一 UI 只汇聚显示；请求只投递到获准的目标会话/API及其最小上下文。路线决定不选择具体 Capability Supply，不重绑定正在运行的 Host，不放宽权限。实际模型/工具供给仍经既有资格与冻结。不同职责可以复用模型或合并步骤，但不能共享整个对话历史；累计预算及 unknown 不因换路由重置。
4. 短程写入前执行权限、输入版本与活动 main/child 读写冲突检查。写入后用 actual diff、引用/版本及任务内容检查评估 `none / relevant / unknown`；角色 Skill/提示词的语义判断与程序的 diff/hash/ref/权限检查分别留证。确定性校验只证明对应结构和执行边界，Agent 自称“无影响”或 Schema PASS 均不足以决定。缺材料或不能确定时走澄清/提案。
5. `none` 且 MainState refs 有效、无活动输入失效时，只保存局部工件/变更记录，不写 MainState、不通知或注入 main。若研究目标、主张、方法、证据、决定、依赖发生变化，或状态引用损坏/影响不明，则形成待采纳提案并暂停相关正式发布。人类采纳后由受控 state writer 核当前版本并形成新 revision；短程 Agent 不静默更新全局状态。
6. 默认旁路隔离不掩盖真实冲突。若活动 main/child 的获准输入失效，必须通过其治理接点发送最小失效/冲突事实，不能继续使用旧 pins；这不是把旁路聊天灌入 main。明确的主 Task 修改沿该 Task 处理，child 指令仍经所属 main/Task 接点。

路由、短程编辑、后置评估是职责，不规定三次模型调用或固定角色数量。必载角色提示词与可选方法 Skill 分开；选择 Skill 承载规则时须满足对应加载、评审和准入要求，提示词的版本绑定不冒充 Skill admission。路由器没有全项目研究决策权，不创建全局 Supervisor、消息总线或 continuity database；现有自动恢复/rollover/Topic 5 Gate 保留。研究状态接受、Claim/Skill 准入、权限放宽和发布仍按适用人类决定处理。

## 接点与验收

由 [TASKS](../TASKS.md) 中 M1-014/M1-015、M2-014、M3-013、M11-011 实施；[短链设计](../workstreams/chengyue-lu/RWB-CHAIN-TASK-DEFINITION/SHORT_LANE_DESIGN.md)定义各路输入、输出、影响与隔离案例。M1-011 的研究 Protocol 编译只接研究路由，Guide 保持只读；短程路径不能直接复用当前要求完整研究 ceiling 的 intake 当成已实现功能。

至少验证局部段落排序无状态变化、微小措辞造成 Claim 变化、MainState 引用版本失效、同时存在 main/child 写入、混合需求、明确主 Task 指令、任意 child 投递拒绝和新研究进入 Protocol。展示 actual diff、路由目标、实际请求上下文、工件、通知事实和 State 前后版本。合并文档只接受设计/任务定义，不接受实现、真实 API 或科学效果。
