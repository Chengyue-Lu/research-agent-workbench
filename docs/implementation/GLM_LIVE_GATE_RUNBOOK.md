# GLM-5.3 标准 API 接入与真实 Gate Runbook

状态：标准 API Adapter 已完成离线合同测试；真实调用未执行

日期：2026-08-16

维护边界：本文和 `zhipu` Provider Adapter 由黄毅维护。本文不实现或修改路诚钺负责的 Mode、Skill、选择矩阵、评估 fixtures 或准入语义，也不改变共享 Task、Handoff、Trace、Receipt 和 Model Assignment 合同。

## 1. 先区分“有 key”与“可以通过 Gate”

截至 2026-08-16，智谱官方模型页已经发布 `glm-5.3`，但同时说明 GLM Coding Plan 已上线、标准 Model API 将于近期上线。因此，拥有一个写着“GLM-5.3”的 key 仍不能证明以下事项：

1. key 属于标准开放平台 API，而不是 Coding Plan；
2. 该账户已经获得 `glm-5.3` 标准 API 权限；
3. key 对应的 endpoint 与协议允许自建 Research Agent Workbench 调用；
4. 返回模型不会由其他别名自动路由；
5. text、结构化输出、客户端工具、usage 和数据政策全部满足本项目 Gate。

不要向 Agent、Issue、日志或仓库粘贴 key。只需由用户在本地确认以下非秘密信息：产品类型、控制台显示的 base URL、模型 ID 和是否明确允许自建应用。

## 2. key 类型决定能否接入

| key 类型 | 当前处理 |
|---|---|
| 标准开放平台 API key，且控制台明确开放 `glm-5.3` | 可以在用户自己的已授权终端执行本文的有界 conformance |
| GLM Coding Plan 专属 key | 不直接接入本自建 Runner；除非另有明确书面授权，不能把 Workbench 伪装成官方支持的 Codex 等工具 |
| 标准 key，但控制台尚未开放 `glm-5.3` | 停止；不静默改用 `glm-5.2`，不把其他模型的结果记为 5.3 Gate |
| 产品类型、endpoint 或模型 ID 不明确 | 只运行零环境 dry-run，不发网络请求 |

Coding Plan endpoint 与标准开放平台 endpoint 不是可互换的 base URL。当前 Adapter 只面向国内标准 API：

```text
https://open.bigmodel.cn/api/paas/v4/chat/completions
```

它不会接受 Coding Plan endpoint，也不会复用 `OpenAIResponsesProvider`。兼容请求形状不等于相同 Provider 身份、响应协议或数据政策。

## 3. 当前 Adapter 能力

`ZhipuChatCompletionsProvider` 当前保守实现：

- canonical provider 为 `zhipu`；
- 模型从显式 `RWB_ZHIPU_MODEL` 读取，响应 `model` 必须与请求完全一致；
- 凭据只在即将发送请求时从 `ZHIPU_API_KEY` 读取；
- 自动重试固定为 0，不自动切换 Provider 或模型；
- 支持单轮 text；
- 对 `json_schema` 请求通过有界 system instruction 约束输出形状，远端只启用 `json_object`，返回后再按 Draft 2020-12 本地校验；这不是 Provider-native strict JSON Schema；
- 编译器产生的 Task/Assignment/Contract metadata 只留在本地审计面，不写入 Zhipu HTTP payload；
- 映射 prompt/completion/cached token，但不推导或伪造货币成本；
- 不持久化 `reasoning_content`、prompt、响应正文、response ID、认证头或 key。

当前不声明 tools、parallel tools、reasoning handback、streaming、images、files 或 server tools。缺失能力在凭据解析和网络调用前阻断。

通用 conformance 报告当前只保存归一化错误类别与 HTTP 状态，不持久化 Zhipu 业务错误码。如要将失败结果升格为项目级 Gate Decision，需通过共享 Schema 的兼容扩展增加该字段，不在本 Provider 独立分支中单方修改。

## 4. 为什么它还不能关闭项目级 K-API-2

现有两个 `ExecutionContract` 都需要客户端工具：evidence/H2 需要冻结的 `document-read`，simulation/H1 需要 `file-read` 与 `bounded-compute`。GLM-5.3 的工具轮次还要求正确保留 Provider 特有的思考/工具上下文；当前共享 `ModelRequest`/`ModelResponse` 端口没有可审计且不泄露隐藏推理的 handback 表达。

因此当前行为是有意的：

- text/structured generic conformance 可以执行；
- evidence/H2 或 simulation/H1 编译会因 `MODEL-CAPABILITY-GAP: tools` 在网络前阻断；
- 不新增“无工具但声称等价”的合同；
- 不删除 Task 所需工具；
- 不降低 ADR-0013 的真实 Gate 强度。

要让 GLM 替代 ADR-0013 中的 OpenAI 项目 Gate，必须先由共享接口负责人共同确认工具/推理 handback 契约，并用新的 ADR 明确把关闭条件改为 Provider-neutral Gate。只增加一个能返回文本的 Adapter 不等于项目级 Gate 通过。

## 5. 零环境检查

以下命令不读取环境变量，也不发网络：

```powershell
rwb providers probe `
  --config registry/providers/adapters.yaml

rwb providers conformance `
  --config registry/providers/adapters.yaml `
  --adapter zhipu-chat-completions
```

预期计划只列出 `text` 和 `structured` 两项，Adapter 默认 `enabled: false`，网络请求数为 0。

如需只检查变量是否存在，可由用户在已授权终端显式运行：

```powershell
rwb providers probe `
  --config registry/providers/adapters.yaml `
  --check-environment
```

输出只有 `present/missing`，不会显示值。`present` 仍不等于授权、模型可用或 Gate 通过。

## 6. 真实 generic conformance

只有在确认是标准 API key、控制台已开放 `glm-5.3` 且自建调用获得授权后执行：

```powershell
New-Item -ItemType Directory -Force .rwb
Copy-Item registry/providers/adapters.yaml .rwb/provider-adapters.local.yaml
# 只在本地副本中把 zhipu-chat-completions 的 enabled 改为 true。
# 不要把 key 或 model 值写入该文件。

$env:RWB_ZHIPU_MODEL = "glm-5.3"
# ZHIPU_API_KEY 应由用户自己的安全凭据机制注入；不要粘贴到聊天或仓库。

rwb providers conformance `
  --config .rwb/provider-adapters.local.yaml `
  --adapter zhipu-chat-completions `
  --checks text structured `
  --max-provider-invocations 2 `
  --max-output-tokens 64 `
  --execute `
  --execution-context authorized-standard-api-windows-session `
  --output runs/provider-conformance/zhipu-glm-5.3.yaml
```

第一次失败后停止，不重试。报告只保存脱敏控制面字段。通过该两项检查只能证明当前账户、模型、endpoint 的 text/JSON 基础兼容；它不证明工具合同、H1/H2 文件闭环、科研正确性或 Provider 报告成本可用。

## 7. 失败和停止条件

以下任一情况都必须保留为 pending/failed，而不是修改标签或自动降级：

- 401/403、模型未开放、endpoint 不匹配；
- 返回的 `model` 不是精确 `glm-5.3`；
- 结构化输出未通过本地 Schema；
- usage 缺失或与分项矛盾；
- 需要 Provider-reported cost 但响应不提供；
- 当前 Task 需要工具、reasoning handback 或项目级 H2；
- 不能确认 key 的产品类型或自建使用授权。

## 8. 官方依据

- GLM-5.3 模型页：<https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3>
- 模型概览：<https://docs.bigmodel.cn/cn/guide/start/model-overview>
- 标准 API 介绍：<https://docs.bigmodel.cn/cn/api/introduction>
- Chat Completions 参考：<https://docs.bigmodel.cn/api-reference/模型-api/对话补全>
- API 错误码：<https://docs.bigmodel.cn/cn/faq/api-code>
- Coding Plan 概览：<https://docs.bigmodel.cn/cn/coding-plan/overview>
- Coding Plan 订阅协议：<https://docs.bigmodel.cn/cn/terms/subscription-agreement>
