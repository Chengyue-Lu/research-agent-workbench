# 模块 10：观测、成本与评估

## 1. 目标

衡量系统是否真正提高研究质量和降低认知负担，而不是只记录“多少 Agent、多少消息、多少流程通过”。观测必须有消费方和保留期限。

## 2. 最小运行记录

每个 Attempt 记录：

- Task、Agent Profile、Skill Assignment 和 Runtime snapshot；
- 开始/结束时间、状态、重试原因；
- 输入/输出工件引用；
- token/调用/工具执行等平台可获得成本；
- deterministic checks；
- 是否触发 review/Human Gate；
- Handoff 被接受、修改、拒绝或废弃；
- 敏感 trace 是否关闭或脱敏。

不默认保存完整 prompt、Chain-of-Thought 或原始工具输出副本。

## 3. 质量指标

- 关键 Claim 的 Evidence 覆盖率；
- 引用 locator 可验证率；
- unsupported / overreaching Claim 比例；
- stale result 被错误合并次数；
- 负结果和冲突保留率；
- Run 可复现率；
- 人类纠正的实质错误类型；
- Agent 结果采纳、修改和拒绝比例。

## 4. 上下文指标

- 主 Agent发生非计划压缩的次数；
- checkpoint/rollover 后恢复成功率；
- Handoff 缺失限制或未完成项比例；
- 主 Agent回查原始材料/日志频率；
- Pinned State 大小与增长率；
- Skill 正文加载量；
- 因摘要失真导致的返工次数。

## 5. 成本指标

- 每条最终采用 Evidence 的 token/时间；
- 每条 accepted Claim 的 token/人工时间；
- 协调、汇总、校核占总成本的比例；
- 每个 Skill 的加载成本与采纳率；
- 子 Agent无效产出比例；
- reviewer 改变实际决定的比例；
- Human Gate 阅读与等待时间。

协调成本持续超过三分之一时进入 WARN，并优先减少 Agent、Handoff 字段、review 或规则，而不是提高预算。

## 6. 对照评估

首批真实案例采用三种条件：

1. 基线：单 Agent，无本框架；
2. 轻量：单 Agent + 最小科研工件/Skill；
3. 目标：主 Agent + 一个或少量不同 Skill 的子 Agent。

比较相同问题下的证据定位、错误、遗漏、人工纠正、完成时间、token 和可恢复性。不能只比较生成文本的主观“看起来更完整”。

## 7. Skill 评估

每个 Skill 有独立小型 eval 集：

- 正常触发案例；
- 不应触发案例；
- 缺输入/工具案例；
- 恶意或提示注入来源；
- 输出契约边界；
- 版本升级回归；
- 与相近 Skill 的路由区分。

Skill 的价值由任务成功、错误率、上下文成本和结果采纳率衡量，不以安装次数或描述覆盖范围衡量。

## 8. Trace 政策

Tracing 用于定位 handoff、工具、guardrail 和成本问题，但不是科研证据本身。默认策略：

- 本地开发允许最小 trace；
- 敏感项目关闭外部 trace 或先脱敏；
- trace 有保留期限；
- 正式事实必须提升为工件；
- 没有调试消费方的 trace 不保存；
- trace 关闭不能破坏核心可追溯性。

## 9. 反指标异化

- 指标必须关联一个决策；无消费方则删除；
- PASS 数、Agent 数、消息数、Schema 覆盖率不是成功指标；
- Claim coverage 不能鼓励制造低价值 Claim；
- token 降低不能以丢失限制、反证和来源为代价；
- Human Gate 通过率高可能表示 Gate 无价值，而不是质量高；
- 每个里程碑进行一次“删减评审”。

## 10. 验收条件

- 能回答每次结果用了哪个 Agent/Skill/输入/工具；
- 能比较单 Agent 与多 Agent 的净收益；
- 能识别上下文污染和 review loop 的真实成本；
- trace 不包含不必要的敏感数据；
- 至少一个低价值机制因指标被删除或降级；
- 评估结果能支持继续、修改或停止项目，而不是只支持扩张。
