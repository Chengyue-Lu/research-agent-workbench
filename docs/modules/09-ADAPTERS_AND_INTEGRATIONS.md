# 模块 09：API 执行、运行时与工具适配

## 1. 目标

将平台中立的 Project Protocol、Agent Profile、Skill Assignment、Task 和 Handoff 映射到模型 API、可选 Agent 平台与科研工具。纯 API 隔离会话是可移植基线；平台 Adapter 是便利层。任何 Adapter 都只能执行映射，不能改变科研状态或批准 Gate。

本模块的 API 实现与测试由黄毅维护。路诚钺只提供冻结的 Mode/Skill/read/handoff/trace 接口并消费脱敏结果，不在自己的分支上补 Provider 或 session 功能。

目标输入边界是 `Task + Method Resolution + Capability Requirement + Data/Permission Policy`；执行
前再生成 Resolved Capability Snapshot。当前 `Resolved Task + Skill Assignment` 在迁移期继续可用，
但 Adapter 不得据此反向定义 Mode、Claim、Skill Need 或 methodology fallback。

Capability 名称分为 demand、available supply 与本次 resolved binding：

```text
Capability Requirement = provider-neutral demand
Host Capability Report / Tool Capability Card / Provider Capability Report = available supply
Resolved Capability Snapshot = this Attempt's frozen implementation binding
```

现有代码类型 `RuntimeCapabilitySnapshot` 是 Host Capability Report 的兼容实现名，不表示本次
Attempt 已完成 Skill/Tool/Adapter 绑定；在正式 Schema 迁移前保留该类型名。

## 2. API-first 执行接口

首版 API 执行只需要三类对象：

```text
ModelPool.bind(explicit_slot) -> ModelBinding
ProviderRegistry.require(provider_adapter, request) -> ModelProvider
IsolatedApiSessionRunner.run(request, limits) -> ApiSessionResult
```

模型池固定为 `explicit-slot-only`。初始约定为一个 `primary`、一个 `worker` 和按需的少量 `specialist` 槽；允许多个槽暂时指向同一模型，也允许没有 specialist。不实现价格抓取、综合评分、LLM Router 或自动降级。

每次 `run` 都是新隔离会话；Runner 不保存跨调用消息、不把 provider response ID 当状态，也不跨 Provider fallback。它当前提供模型轮次、工具调用、单轮并行、工具副作用类别、工具结果字符、单轮输出、累计 token/可得成本与 wall time 硬边界。集成分支的 `K-API-2` 已把 Task/Assignment/Method/Snapshot 编译到 Attempt/Handoff/Receipt，并以 marker-last manifest 提供 file-only replay；live 结果仍与离线证据分开。

## 3. Runtime Adapter 接口（可选平台路径）

```text
capabilities() -> HostCapabilityReport
resolve_agent(profile_ref) -> RuntimeAgentConfig
resolve_skills(skill_assignment) -> RuntimeSkillBinding
launch(resolved_task) -> RuntimeExecutionRef
collect(execution_ref) -> HandoffCandidate
cancel(execution_ref) -> CancellationResult
```

Adapter 必须暴露：

- 支持的 Agent、Skill、权限、工具和并发能力；
- 平台版本和配置快照；
- 哪些约束可由平台强制，哪些只能通过提示/验证；
- 原始会话标识与正式 Task/Attempt 的映射；
- 失败与取消语义。

## 4. Codex Adapter（已有可选实现）

映射建议：

| 平台中立对象 | Codex 表面 |
|---|---|
| Repo guidance | `AGENTS.md` |
| Agent Profile | `.codex/agents/<name>.toml` |
| Skill | `.agents/skills/<name>/SKILL.md` |
| Skill metadata | Registry manifest + Skill frontmatter |
| Skill Assignment | Task Prompt 显式调用 + lock 文件 |
| Task execution | 原生 subagent thread |
| Permission ceiling | custom agent config 与会话权限交集 |
| Handoff | 子 Agent返回 + 仓库工件 |
| Rollover | Main State + 新主线程/会话 |

官方能力允许项目级自定义 Agent 设置模型、推理、sandbox、MCP 和 Skill 配置；仓库级 Skill 通过渐进披露加载。平台路径利用这些能力，不包裹一个长期驻留的自建调度进程。

当前实现依据 OpenAI 官方的 [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) 与 [Build skills](https://learn.chatgpt.com/docs/build-skills) 文档：项目 Agent 使用 `.codex/agents/*.toml`，仓库 Skill 使用 `.agents/skills/*/SKILL.md`。Canonical Agent Profile 不固定厂商模型；Codex 配置也默认继承会话模型。Task Assignment 通过 dispatch 中的显式 `$skill-name` 调用绑定，而不是把 Skill 永久写死在 Agent Profile 中。

`CodexRuntimeAdapter` 当前实现 `capabilities`、`resolve_agent`、`resolve_skills`、布局验证和 dispatch 渲染。`launch/collect/cancel` 保留给 Codex 原生线程。它不再位于当前关键路径；OpenCode 或其他平台只有在真实使用选择明确后才增加 Adapter。

运行后由平台适配器或人工采集器生成平台中立 `Execution Receipt`：原生 thread/response ID 只能进入可选诊断字段，实际模型/提供商、可得用量、Context Snapshot、输出和限制必须映射到统一契约。无法取得 token 或成本时写 `unavailable`，不能由 Adapter 猜测或填零。

## 5. 其他 Runtime

OpenCode、Claude Code 等平台以后按真实选择以独立 Adapter 接入。Canonical manifests 保持不变，Adapter 负责翻译对应的 Agent/Skill 配置、模型槽、权限与显式调用方式。

不得为了“跨平台统一”只保留所有平台的最小公分母。Adapter 应报告 capability gap；上层可以选择降级、换平台或请求人工决定。

## 6. Model Provider Adapter

Runtime Adapter 与 Model Provider Adapter 仍是两层：前者映射完整 Agent 平台，后者处理程序化模型 API。后者现在是首要执行路径的底层端口。当前已实现 OpenAI Responses、Anthropic Messages 和 Gemini `generateContent` 三个模型绑定的薄 Adapter，详见 [多提供商模型 API 实施计划](../implementation/PROVIDER_ADAPTER_PLAN.md)、[ADR-0007](../decisions/0007-THIN-PROVIDER-ADAPTERS.md)与[ADR-0010](../decisions/0010-API-FIRST-ISOLATED-EXECUTION.md)。

首版只声明经过离线合同测试的能力，不根据厂商品牌推断模型能力。真实模型/账户仍需 live conformance；缺少能力、模型不匹配或 data policy 不满足时必须在解析凭据和发送请求前失败。Adapter 不自动重试、不静默 fallback，且结构化响应仍需本地 Schema 校验。

工具选择以公共 `ToolChoice` 表达 auto、none、required 或指定 client tool，但由各 Adapter 映射厂商原生字段。任何返回的工具名称、call ID 和 arguments 都必须在工具执行前通过本地 allowlist、唯一性和 JSON Schema 检查，不能只依赖远端 strict mode。

非秘密配置只保存环境变量名称。`rwb providers probe` 默认不读取环境；真实 Windows 中可显式使用 `--check-environment` 做不回显值的存在性检查。

`rwb providers conformance` 默认同样是零环境、零网络 dry-run。显式 live 执行使用固定合成内容、至多三次请求，并生成 `provider_conformance_report`；该报告可审计预算、停止原因和用量，但禁止保留正文、工具参数、凭据与 provider response ID。

## 7. Tool Adapter

Tool Adapter 提供数据或动作，Skill 提供工作流程：

- 文献：Zotero、Crossref、OpenAlex、PaperQA2；
- 数据/实验：DVC 或 MLflow（二选一起步）；
- 报告：Quarto/Jupyter；
- 推导：CAS/证明助手；
- 仿真/统计：项目已有 CLI 或 Python/R；
- 外部资料：Web Search、浏览器、受控 API。

首版不同时接入所有工具。只有首个案例需要且可替换的最小适配器进入实现。

## 8. 权限模型

有效权限是以下交集：

```text
Runtime session permission
∩ API session/tool allowlist
∩ Agent Profile permission ceiling
∩ Task Packet permission
∩ Resolved Capability Snapshot permission/data boundary
∩ Skill permission ceiling
∩ Project data boundary
```

任一层缺失不按最宽权限推断。Skill 缺少工具时返回 capability gap；不自动安装、不自动登录、不自动扩大网络或文件权限。

## 9. 平台与模型漂移

运行前记录 Host Capability Report（当前代码类型为 `RuntimeCapabilitySnapshot`）：

- runtime 名称与版本；
- Agent 配置发现路径；
- Skill 发现/显式调用能力；
- 并发和递归限制；
- sandbox/approval 语义；
- 工具/MCP 可用性；
- 已知限制。

版本变化后运行 Adapter contract tests。平台新增原生能力时优先删掉重复代码，而不是保留兼容层。

API 路径额外记录所选模型槽、请求模型和 Provider 实际返回模型；三者不一致时进入 Receipt warning 或阻断。模型槽配置只保存环境变量名，不保存 API key；配置变化后重新运行离线合同和目标模型 live conformance。

## 10. 安全边界

- Adapter 不签署 Human Gate；
- Tool 输出视为不可信数据；
- 凭据由平台/环境管理，不写入 Task、Handoff、trace 或仓库；
- 外部写动作需要 Project Protocol 与 Task 双重授权；
- 安装依赖、插件或 Skill 属于供应链变化，需要明确任务或人工批准；
- Runtime 会话日志不能成为唯一证据。

## 11. 验收条件

- Codex Adapter 能把冻结 Profile 与可选 Skill binding 映射到原生配置，并保留合法 no-Skill 路径；
- Adapter 不保存自己的权威项目状态；
- capability gap 可以清晰报告；
- 平台升级后可通过 contract test 发现关键行为漂移；
- 替换 Tool Adapter 不修改科研内核；
- 所有外部写动作可追溯到授权 Task。
- 模型 Adapter 的离线合同测试与 live conformance 状态分开记录；未知响应语义不会被静默归一化。
- 一个显式 `worker` 槽可以启动 fresh API session，完成一次有界客户端工具往返；
- 未知槽、缺少模型、data-policy gap、工具预算和不可测硬预算会在本地失败或安全暂停；
- API Runner 不保存跨 Attempt 会话，也不自动更换 Provider/Model。
- 严格执行在调用 Provider 前验证 Method Authority、Capability binding、前序 Main State 与全部 pin；
- Evidence 精确绑定 Task input，工具 invocation（含失败/超大结果）记录预算与副作用；
- cancel/deadline 有显式停止语义，半发布批次没有 completion marker 就不能视为已提交。
