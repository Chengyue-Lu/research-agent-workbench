# Provider Adapter、配置与隔离会话

Provider Adapter、API session、live conformance 与执行事实集成的共享控制/权限/Trace 语义按
[开发协作规则](../DEVELOPMENT.md)审查。当前成熟度与 exact live 来源见 [STATUS](../STATUS.md)；本页定义接口。

## 1. 可移植执行边界

```text
Research Control / Resolver 冻结 Task、Method、Capability selection
  → Runtime Bundle → Resolved Execution View
  → 一个显式预绑定 Driver → Thin Host actual facts
  → Trace / Artifact / Validation / Receipt
```

API Session 是可选 Driver 的 building block；原生 Agent/Tool 平台也可实现同一边界。
Session 接收 fresh messages、明确模型、工具与预算，返回实际响应/用量/停止事实。它不选择 Supply、
修改 Method、运行中 rebind、自动 fallback，或产生 whole-Task/Human/科学接受。
调用方可在总预算内组织多个角色与会话；每个 Host slice 的单 binding/单 Attempt 不等于整个研究只能有一个 Agent。

## 2. 实现入口

源码均在 `src/research_workbench/adapters/models/`：

| 文件/组 | 职责 |
|---|---|
| `port.py`、`base.py` | canonical request/response、能力/DataPolicy 预检、标准错误、本地结构化验证 |
| `http.py` | 可注入有界 HTTPS Transport、晚解析凭据；错误/常规表示不暴露 header/body |
| `openai.py`、`anthropic.py`、`gemini.py` | 独立 wire 语义映射 |
| `profile_configuration.py`、`configured.py`、`wire_codecs.py` | exact profile/config 校验与协议 codec；不能只替换 base URL |
| `configuration.py`、`pool.py` | 非秘密配置、显式模型槽、延迟模型 ID；不评分、不自动排名 |
| `session.py`、`session_policy.py` | fresh context、客户端 Tool 往返、有界预算/副作用及事件捕获 |
| `provider_binding.py`、`provider_source_closure.py` | configured/observed source binding、外部 pins 与源码闭包 |
| `conformance.py`、`profile_conformance.py` | 合成端口检查与 exact profile 的受控诊断 |
| `conformance_*`、`profile_conformance_report.py` | budget grant/anchor、累计账、journal、body policy 与报告核对 |

官方协议/厂商事实由 versioned profile 引用及 exact conformance 证据限定；离线映射不证明账户/模型 live 可用。

## 3. 能力与语义

请求明确所需 text/client tools/structured output 等能力；Provider 不支持、模型未声明、DataPolicy 证据不足时在发送前阻断。
不同协议的 role priority、Schema 子集、tool IDs、finish/refusal/pause、cached/reasoning usage 分别映射，
保留原分项与 warnings，不根据厂商品牌推断数据控制，也不伪造统一成本或远端 strict 保证。

客户端 Tool 必须有本地显式定义与 handler。模型给出的名称/参数先通过本地 Schema 和 allowlist，
再按数量、并行度、结果大小与副作用 ceiling 执行；超长结果不得静默截断成完整证据。
服务端工具不能冒充受本地 handler 控制的客户端 Tool。

## 4. 凭据、预算与留存

1. 仓库只保存 credential reference；配置解析、计划和失败 preflight 不解析 Key。
2. 真正出站前晚解析凭据，先核 authorization、source/config pins、实际时间、数据和累计预算。
3. Session 限制模型轮次、Tool 次数/并行数/结果大小/副作用、单轮输出、累计 token/可得成本和 wall time。
4. failed send 与 unknown usage 按实际 attempted request 留证和预占；无自动付费重试或跨 Provider fallback。
5. 凭据/认证头始终禁止留存；正式 Attempt 依其 Task policy 捕获获准的 request/response/Tool 原件。
   脱敏 conformance report 的 shape-only 模式只适用于该诊断，不替代正式 Trace/archive 的完整性要求。

库级 deadline/取消、Host detective checks 与 OS 沙箱不同。只有实际启用并验证的 preventive control 才能称“已阻止”；
post-call drift/超额检测不能改写成事前阻止。新会话不重置 Task/整 Run 的累计预算。

## 5. 计划、live 与集成资格

`rwb providers probe` 默认仅探测显式配置；`rwb providers conformance` 默认生成计划，live 需独立显式执行授权。
`rwb providers profile-conformance` 是 exact profile 的离线计划入口，没有隐式 live 开关。
具体命令和边界以 [上手指南](../GETTING_STARTED.md)与 CLI help 为准。

一次 Provider 诊断只证明被测 source/config/model/request 范围。完整 Driver 集成还需实际消费 Bundle/View、
捕获 Host/Trace/outputs、生成适用 Receipt 并独立冷回放；参见 [Host](THIN_EXECUTION_HOST.md)、
[generic closeout](GENERIC_EXECUTION_CLOSEOUT.md)及 [Skill closeout](SKILL_EXECUTION_CLOSEOUT.md)。
源码/配置改变后的 live 资格必须重核，旧报告不能自动授予新 binding。

Handoff 文件消费、checkpoint 发布与自动 continuity/recovery 分开；Topic 5 仍受
[ROADMAP Gate](../ROADMAP.md)限制。旧 Skill-bound Assignment lane 的兼容说明见
[compatibility](../compatibility/README.md)，不作为新 no-Skill/direct Tool 入口。
