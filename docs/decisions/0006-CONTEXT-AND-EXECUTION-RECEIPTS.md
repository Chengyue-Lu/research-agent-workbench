# ADR-0006：上下文压力与执行成本使用显式收据

状态：Accepted
日期：2026-08-13

## 背景

主 Agent 的上下文应当克制，不能把平台自动压缩当作正常容量管理；子 Agent 的局部压缩可以容忍，但前提是 Task、输入锁、Skill Assignment、正式工件和 Handoff 已经足以恢复。与此同时，多 Agent 是否有价值不能靠主观感受判断，必须知道执行、协调、复核和上下文各自消耗了什么。

不同平台并不总能提供同样的 token、缓存、推理 token、上下文窗口或原生线程指标。若把某个平台的字段写进内核，会破坏平台中立；若把未知量填成零，又会产生虚假的低成本结论。

## 决策

1. 新增 `Context Snapshot`，记录主/任务上下文的可观察代理指标、测量来源、未知项、Handoff 是否已经固化，以及确定性的压力判断。
2. 新增 `Execution Receipt`，记录一次 Attempt 实际使用的 Runtime、Agent Profile、Skill Assignment、模型用量、协调成本、并发、复核轮次、trace 策略、输出和限制。
3. 未知指标必须进入 `unknown_metrics` 或 `model_usage_status: unavailable`，不得按零处理，也不得据此宣称节省 token 或成本。
4. 主上下文出现原始材料、隐藏决定或非计划压缩时升级为阻断/rollover；子 Agent 压缩只有在 `handoff_ready: true` 时可降为可恢复警告。
5. Main State 带规范化 digest、前一 checkpoint 和 Context Snapshot 引用；`resume-check` 验证协议 revision、引用、下一动作和约束/决定是否丢失。
6. Execution Receipt 不保存完整 prompt、Chain-of-Thought、凭据或原始工具输出副本。提供商特有信息只能留在受控诊断元数据中。
7. 协调成本优先使用 token 比例；缺 token 时可使用时间比例。二者都缺失时显式警告，不能混合成伪精确总分。
8. Receipt 只观测并验证平台原生执行，不负责 launch、调度或自动扩大预算。

## 后果

优点：主 Agent 可在压缩前主动换届；子 Agent 会话可删除而不丢失正式结果；OpenAI、Anthropic、Gemini 或其他 API 的用量可以映射到相同分析表面；高 fanout、review loop、敏感 trace 和协调成本过高可以被确定性识别。

代价：部分平台无法提供全部指标，首批数据会包含明确的 unknown；字符量是上下文压力代理而非 token 真值；真实净收益仍需在同一案例的单 Agent/轻量/多 Agent 对照中验证。

## 明确不做

- 不建立常驻遥测服务或第二个 Agent 调度器；
- 不抓取或保存模型隐式推理；
- 不用上下文代理指标预测精确剩余窗口；
- 不因缺少成本数据而静默采用零；
- 不把结构化 Receipt 当作科研质量证明。
