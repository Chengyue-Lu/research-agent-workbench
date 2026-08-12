# ADR-0007：模型提供商采用薄适配器与延迟凭据解析

状态：Accepted（首个离线合同切片）

日期：2026-08-13

## 背景

ADR-0003 已冻结提供商中立端口，但仅有端口不能证明三家 API 的消息、工具调用、停止原因和用量可以在不掩盖差异的前提下映射。直接依赖三套 SDK 会增加版本和传递依赖；把三家都当成 “OpenAI-compatible” 又会丢失 Anthropic `pause_turn`、Gemini 并行函数调用和各自结构化输出位置等语义。

凭据还有独立边界：仓库、Task、Handoff、日志和测试 fixture 都不能保存 API key。Codex 嵌入式/沙箱进程也不作为真实 Windows 身份和凭据状态的判定依据。

## 决策

1. 每家 API 使用独立、模型绑定的薄 Adapter；公共端口不保存厂商 SDK 类型。
2. 首版使用标准库 HTTPS Transport，并允许测试注入 Transport；不自动重试，也不自动跨提供商回退。
3. Adapter 构造时只接收 `CredentialProvider`，凭据值只在出站请求边界解析。HTTP request/response 的 `repr` 隐藏 header 和 body。
4. 仓库配置只记录环境变量名称，不记录值。`rwb providers probe` 默认只验证配置；只有显式 `--check-environment` 才做存在性检查，且永不输出值。
5. 能力默认保守。每个 Adapter 只允许声明其已经实现的能力；具体模型和账户是否可用仍需真实环境的 live conformance。
6. OpenAI Responses 请求默认发送 `store=false`；提供商 response/conversation ID 只作诊断元数据。
7. Client tools 统一为 `tool_call` / `tool_result`，但 provider-hosted tools 不进入首版实现，也不伪装为客户端工具。
8. 提供商结构化输出返回后仍进行本地 JSON 解析与 Draft 2020-12 Schema 校验。
9. 未知响应块、停止原因、用量字段和 API 形状不能静默吞掉：可安全忽略的进入 warning，破坏契约的返回 `contract_violation`。

## 首版实现面

| Adapter | API | 已实现能力 | 明确保留的差异 |
|---|---|---|---|
| OpenAI | Responses API | text、tools、structured_output、reasoning | `function_call` items、`store=false`、cached/reasoning tokens |
| Anthropic | Messages API | text、tools、structured_output | top-level system、必需 `max_tokens`、`pause_turn` 与 context limit |
| Google | Gemini `generateContent` | text、tools、parallel_tools、structured_output | `systemInstruction`、parallel function calls、prompt block、usageMetadata |

首版不实现 streaming、图片、文件、服务端工具、prompt caching、provider state 或自动路由。

## 依据

- OpenAI Responses 的函数调用以 `function_call` output item 表达，并通过 `call_id` 关联工具输出；Structured Outputs 在 Responses API 使用 `text.format`：[Function calling](https://developers.openai.com/api/docs/guides/function-calling)、[Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)。
- Responses 默认存储，需显式 `store: false` 关闭：[Migrate to the Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses)。
- Anthropic 区分 client tools 与 server tools，client tool use 通过 `tool_use` / `tool_result` 往返：[Tool use overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)。Structured Outputs 当前位于 `output_config.format`：[Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)。
- Gemini `generateContent` 分开表达 `systemInstruction`、`contents`、`tools`、`generationConfig`、候选停止原因和 `usageMetadata`：[GenerateContent API](https://ai.google.dev/api/generate-content)、[Function calling](https://ai.google.dev/gemini-api/docs/function-calling)。

## 后果

好处是适配器可离线用官方形状 fixture 测试，凭据不进入常规对象表示，厂商控制流差异仍可见。代价是必须维护三套映射和 live conformance 矩阵；标准库 Transport 也不承担连接池、流式传输或自动重试。

## 退出与替换条件

- 某厂商 SDK 明显降低实现风险且不会污染公共端口时，可在独立 Transport/Adapter 内替换。
- 若真实案例只使用一个平台且跨提供商能力没有消费者，停止扩展其他 Adapter。
- 任何 endpoint variant（Azure OpenAI、Vertex AI、Bedrock 等）若认证或语义不同，必须成为独立配置/Adapter，不靠更换 base URL 冒充等价。
