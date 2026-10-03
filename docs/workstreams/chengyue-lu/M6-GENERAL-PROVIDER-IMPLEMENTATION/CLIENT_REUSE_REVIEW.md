# API 客户端复用与审核范围

日期：2026-10-03。本文是公开资料和源码审查后的实施建议；尚未选定、安装或接入第三方客户端。
M6-009 保持 IN_PROGRESS，M6-010 保持 BLOCKED。既有实现、SDK 候选和真实调用资格分别验收。

## 复用方向

模型客户端、HTTP 客户端及厂商协议映射优先评估成熟开源实现。RWB 保留自身的 ModelProvider
端口、真实 vendor/profile、权限与数据边界、client Tool 执行、本地 Schema 校验、累计 token
账本、停止条件和脱敏证据。替换客户端不改变这些公共语义。

[ADR-0007](../../../decisions/0007-THIN-PROVIDER-ADAPTERS.md) 已允许在独立 Transport/Adapter 内
以 SDK 降低维护风险。当前优先验证 PydanticAI 的 Model/Provider 层，LiteLLM 作为对照候选；
不据资料兼容直接认定任一候选满足 Flash 运行合同。

| 候选 | 可复用或参考的部分 | 下一步需证明的内容 |
|---|---|---|
| PydanticAI | 独立的单次模型请求 API、Model/Provider/Profile，以及四类协议的模型实现；不要求采用完整 Agent 工具循环 | 精确 Flash Responses、nonthinking、specific→none、Schema 方言、原始 usage 字段存在性、错误用量、显式凭据与实际发送控制 |
| LiteLLM 直接客户端库 | 主流服务的请求/响应适配与四类接口；使用客户端库不要求部署 Proxy/Router | 原生 DeepSeek Responses 路由不发生协议桥接；禁参数丢弃、跳转和隐含重发；固定依赖与启动网络行为 |
| CC Switch | Provider 到不同 harness 的配置投影、模型映射、Switch/Coexist、局部更新与恢复；可选本地路由提供协议转换 | 区分直接配置与网关；固定版本核对转换语义、重试/回退、凭据存储和日志，不把预设存在当作兼容证据 |
| OpenCode 原生 Provider | 显式 SDK/协议选择、自定义 endpoint、模型目录与配置合并；可作可选 harness 接入参考 | baseURL 与认证配置不证明跨协议转换或 Tool/Schema/usage 兼容；保持 Provider 能力与预算的区别 |
| Deep Agents | Harness 的模型配置、工具循环及停止机制，作为实现对照 | 其规划、文件系统及 subagent 默认行为与本次 API 客户端范围不同；复用范围先限定到直接消费者所需部分 |

来源：[PydanticAI Direct API](https://pydantic.dev/docs/ai/core-concepts/direct/)、
[模型与提供商](https://pydantic.dev/docs/ai/models/overview/)、
[LiteLLM Responses](https://docs.litellm.ai/docs/response_api)、
[Messages](https://docs.litellm.ai/docs/anthropic_unified)、
[generateContent](https://docs.litellm.ai/docs/generateContent)、
[Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview)。
以上为当日文档和公开 main 源码观察，尚无选定发行版本、离线 SDK 兼容测试或 live PASS。

## 既有 harness 的 API 接入

CC Switch 官方上游为 [farion1231/cc-switch](https://github.com/farion1231/cc-switch)，
[添加 Provider 手册](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/en/2-providers/2.1-add.md)
与 [本地路由手册](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/en/4-proxy/4.1-service.md)
提供两类参考：将 Provider 配置写入现有 harness，以及通过可选本地代理转换客户端与上游协议。
Rust/Tauri 应用的接入设计与 Python ModelProvider 客户端层可以分别复用。当前 main 手册与已发布版本
不同，本次没有取得完整 commit 或验证实际路由源码。

其路由文档默认启用请求用量记录；
[Failover 手册](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/en/4-proxy/4.3-failover.md)
列出重试默认值并允许开启跨 Provider 回退。RWB 的本次测试保持固定 vendor、无自动 retry/fallback
及既定数据边界，采用该类方案时须显式配置并验证这些差异。

OpenCode 的 [Providers](https://opencode.ai/docs/providers/) 文档明确区分 Chat Completions 的
`@ai-sdk/openai-compatible` 与 Responses 的 `@ai-sdk/openai`；
[Config](https://opencode.ai/docs/config/) 提供配置合并、优先级和 Provider allowlist 参考。
这些结构适用于可选 harness Adapter；具体模型、协议、ToolChoice、Schema、截断/错误和用量仍需
合成合同测试。“Key 可配置”只支持配置事实，不证明任何 API 都能无差别进入任何 harness。

下一步并行验证 SDK 薄 Adapter 与 Provider→harness 配置映射。二者写入范围独立，统一由协调窗口
比较并选择最小集成路径；当前不引入新代理服务，也不修改用户的现有 harness 配置。

## 小型离线适配验证

下一实施单元应固定库及底层 SDK 的版本、发行摘要、许可证和依赖，使用 fake HTTP 验证现有
三个阶段：指定纯函数调用、工具结果回传并获得 text、独立 JSON/Schema 请求。比较实际 endpoint、
model、nonthinking、ToolChoice、history、Schema 和返回值，保留 RWB 对每次实际发送的控制。

还须验证：

- SDK、HTTP 层和模型层均不自动 retry/fallback；任何内部重发也不能绕过停止条件。
- 每次真正发送前复核窗口、预算与剩余 timeout；模型层 timeout 不能替代 durable intent 后的发送守卫。
- 凭据只在授权的出站边界解析；构造客户端时不隐式探测其他环境或账户。
- 缺失 usage 保持 unknown 并保留预占；截断或后续捕获失败时，保留已经收到的用量。
- 跳转、日志、遥测、异常 body/header/repr 和额外的计数/价格网络请求符合冻结的数据边界。

这些是复用验证条件，尚未声称通过。第三方依赖按明确的受信依赖边界管理；不扩展成对整个 SDK
递归手工反射的审计框架。

当前源码中有两项需要针对性包装：PydanticAI 的标准化 Usage 以 0 为默认值，不能直接用于
RWB 的 unknown-token 结算；DeepSeekProvider 在自定义 client 分支之前仍可能读取环境变量，
因此仅提供 client 不足以证明延迟凭据解析。
来源：[Usage](https://pydantic.dev/docs/ai/api/pydantic-ai/usage/)、
[DeepSeekProvider 源码](https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/providers/deepseek.py)。

LiteLLM 公开 main 的异步 HTTP handler 默认允许跳转，并有连接错误后的重新发送分支。
仅设置 `num_retries=0` 不构成全链单次发送证明；选定版本及同步/异步实际路径仍需验证。
来源：[HTTP handler 源码](https://github.com/BerriAI/litellm/blob/main/litellm/llms/custom_httpx/http_handler.py)。

## Windows 测试的对象

当前本地测试针对 Python 父进程→PowerShell 凭据桥→隔离 Python child 的辅助启动路径，
主要检查以下内容：

| 检查 | 要证明的行为 |
|---|---|
| 启动与凭据 | 使用固定解释器和配置；Key 只进入被选择的 child，不进入仓库、日志或报告 |
| 生命周期 | 出错、超时或父进程退出后停止所属进程；不留下继续调用的 child |
| 调用与停止 | 固定三次调用和一次本地 Tool；出窗、预算不足或失败后不继续发送 |
| 证据 | 成功/失败用量进入同一累计历史，未知不填零，脱敏报告可独立核对 |

已经完成的 Windows Job 生命周期和 PowerShell 退出状态合成测试仅支持各自所选上下文。
联合启动链使用模拟网络；两次已观察响应和 Tool 记录不构成三调用加最终报告通过。
实际 Key 注入与真实 HTTP 返回尚未验证。这也不是科研任务或 M5 四臂评价的全流程验收。

“启动至报告共 120 秒”是本地执行计划的计时选择，不是用户新增的硬约束。应明确预检、API Attempt
和报告阶段的计时边界；用户的实际每请求北京时间 18:00 后且官方闲时、全部成功/失败 input+output
累计不超过 10,000,000、失败停止和无自动重试等约束保持。

## PR #128 的审核对象与时点

[PR #128](https://github.com/Chengyue-Lu/research-agent-workbench/pull/128) 提交的是 M6-009 离线产品
候选：显式配置/源码绑定、Session 政策、三阶段 conformance 驱动、预算历史、脱敏报告及离线 CLI。
本地 Windows 启动原型代码未进入该 diff；相关文档保留其证据和未证明范围。

该离线候选可现在开始 R2 审核，不等待真实 API 测试或所有本地启动原型完成。审核应检查公共端口
与版本兼容、真实 Provider 身份、未知/失败用量、每次发送前的停止条件、本地 Tool/Schema 与报告闭合。
SDK 替换的实现尚未提交；本轮只提交复用评估，后续适配变更需按其实际 diff 验证和审核。

PR 接受不等于 M6-009 整项 DONE 或 M6-010 执行资格。真实测试仍须固定实际运行代码、profile、
Windows 启动方式、累计用量记录、输出目标及对应接受，并满足当次模型和时间窗条件。
