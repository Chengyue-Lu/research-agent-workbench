# ADR-0003：模型 API 采用能力协商式中立端口

状态：Accepted
日期：2026-08-13

## 背景

Workbench 首先利用 Codex 等平台的原生 Agent/Skill 运行能力，但后续可能需要在程序化任务中调用 OpenAI、Anthropic、Gemini、OpenRouter 网关或本地模型。各 API 都有文本、工具调用和结构化输出等相似概念，却在停止原因、服务端工具、会话状态、推理参数、用量统计、数据保留和错误语义上存在实质差异。

如果公共内核直接保存某家 SDK 对象，研究工件会随提供商变化而失效；如果只保留“最小公分母”，又会掩盖工具执行方、暂停状态和数据策略等关键差异。

## 决策

建立 `ModelProvider` 端口，并采用“稳定规范对象 + 显式能力协商 + 提供商 Adapter”的结构：

1. 公共请求只包含 `Message`、`ContentBlock`、`ToolDefinition`、`ResponseFormat`、`DataPolicy` 和预算参数。
2. 公共响应只包含规范化内容、工具调用、停止原因、用量和警告。
3. 每个 Adapter 在执行前返回具体模型与配置的 `ProviderCapabilities`；缺少硬能力时返回 `CapabilityGap`，不得静默模拟。
4. 提供商特有参数只能进入命名空间化 `extensions`，其原始响应只能作为诊断元数据，不能成为 Project/Task/Claim 的权威状态。
5. 客户端工具默认由 Workbench 执行。提供商托管的服务端工具必须作为单独能力声明，并受 `DataPolicy` 约束。
6. Adapter 必须区分正常完成、工具调用、长度截断、拒答、暂停和上下文上限；不得全部压成一个 `finished` 布尔值。
7. 即使提供商承诺结构化输出，Workbench 仍进行本地 Schema 与业务规则验证。
8. 重试只适用于明确的瞬态失败并受预算限制。跨提供商回退必须记录实际提供商、模型和数据策略，不能无声发生。

模型选择是项目/任务策略，不写进科研对象；Runtime Adapter（Codex/Claude Code 等 Agent 平台）与 Model Provider Adapter（API 调用）保持分离。

## 首版能力集合

`text`、`tools`、`parallel_tools`、`structured_output`、`streaming`、`reasoning`、`images`、`files`、`server_tools`、`prompt_caching`、`provider_state`。

能力不是提供商的永久属性。Registry 中的记录只是设计基线；执行时仍须产生模型、版本、区域、路由和配置相关的能力快照。

## 依据

- OpenAI 建议面向推理、工具和多轮工作使用 Responses API，并分别测试程序输出与最终回答；Function Calling 和 Structured Outputs 均有独立契约：<https://developers.openai.com/api/docs/guides/latest-model>、<https://developers.openai.com/api/docs/guides/function-calling>、<https://developers.openai.com/api/docs/guides/structured-outputs>。
- Anthropic Messages API 用 `tool_use`、`pause_turn`、`refusal`、`model_context_window_exceeded` 等不同停止原因表达不同控制流，并区分客户端与服务端工具：<https://platform.claude.com/docs/claude/docs/tool-use>、<https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons>。
- Gemini Function Calling 同样要求应用执行函数并返回结果，同时支持组合与并行调用：<https://ai.google.dev/gemini-api/docs/function-calling>。
- OpenRouter 的统一入口仍保留下游提供商路由、能力、参数支持与数据策略差异：<https://openrouter.ai/docs/guides/routing/provider-selection>。

## 后果

优点：科研工件不依赖 SDK；能力缺口可审计；可以逐个增加 Adapter；数据策略与静默回退风险进入契约。

代价：Adapter 必须认真映射内容块、工具循环、停止原因和用量；不能仅用一个“OpenAI-compatible”客户端宣称兼容全部语义。

## 明确不做

- M1 不接入真实 API、密钥管理或自动模型路由。
- 不建立全局模型代理服务。
- 不把提供商会话 ID 当成主状态。
- 不为了统一接口删除提供商特有能力；不能规范化的能力通过 capability gap 或扩展显式暴露。
