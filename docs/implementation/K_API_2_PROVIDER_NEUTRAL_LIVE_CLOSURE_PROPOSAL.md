# K-API-2 Provider-neutral 真实关闭提案

状态：`PROPOSED` / 非权威实施提案，尚未生效

日期：2026-08-17

维护边界：本文由黄毅负责的 API Execution 工作流提出，供黄毅与路诚钺共同审阅。本文不修改或解释性覆盖已接受的 [ADR-0013](../decisions/0013-PROJECT-LEVEL-K-API-2-TRACE-AND-MODEL-ASSIGNMENT.md)，不改变 Task、Mode、Skill、读取、Handoff、Trace、Receipt、Model Assignment 或共享 Schema 语义。在新的共同 ADR/addendum 被两位负责人接受前，项目级 K-API-2 仍按 ADR-0013 的“一次 OpenAI 真实 Gate”关闭条件执行，任何 Zhipu/GLM 结果都不得被报告为该条件已经通过。

## 1. 要解决的矛盾

[ADR-0003](../decisions/0003-PROVIDER-NEUTRAL-MODEL-PORT.md) 和 [ADR-0010](../decisions/0010-API-FIRST-ISOLATED-EXECUTION.md) 已把执行内核定义为 Provider-neutral `ModelProvider`，要求显式能力协商、精确模型槽、无静默 fallback 和可审计实际 Provider/Model。ADR-0013 的最终验收边界却指定为一次 OpenAI 真实 Gate。OpenAI 可以保留为一个 Provider 的准入证据，但把一个具体 Provider 写成项目级可移植内核的唯一关闭条件，会使“执行合同是否成立”与“某家 Provider 是否可用”成为同一个问题。

在本次 Zhipu 专属拆分之前，OpenAI Gate 与 Zhipu Gate 都固定要求 `provider_reported_cost`。两个现有 Adapter 都能映射 token usage，但都不能从当前响应合同取得请求级货币金额；因此只要启用非空货币成本上限，正常的真实响应也会按现有 session 规则 `safe-paused` 为 `cost-usage-unavailable`。本次实现已把 Zhipu 专属结果收窄为 `technical-readiness`，并把货币证据单独记录为不可得；它没有修改通用 Session、OpenAI Gate 或 ADR-0013 的项目级关闭条件。这一历史矛盾仍说明需要共同决定：项目是在验收执行能力，还是在验收响应级货币核算。不能通过估价冒充 Provider 报告，也不应把两个不同问题长期压成一个不可满足的布尔 Gate。

本提案建议：

1. 把 Provider-neutral 的 `capability_gate` 定义为 K-API-2 真实执行关闭证据；
2. 把 `monetary_accounting` 定义为独立、显式分级的财务证据；
3. 保留 OpenAI Gate 为 OpenAI 专属准入，不再把它硬编码为唯一项目级 Provider；
4. 通过新的共同 ADR/addendum 才能让上述语义成为 Provider-neutral 的项目级关闭规则；已实现的 Zhipu 专属技术/金额分层只属于 Provider readiness 证据，本文本身不授权项目状态迁移。

## 2. 两条 GLM-5.3 路线必须分开

### 2.1 标准 API `ModelProvider`

标准 API 路线由 Workbench 自己构造模型请求并直接接收 Provider 响应。只有这条路线能够按现有 `ModelProvider` 合同核对：

- 预调用冻结的 Provider Adapter、endpoint 类别和 requested model；
- Provider 响应中的 canonical provider 与 `model` 字段；
- text、结构化输出和指定客户端工具的真实响应形状；
- token usage、停止原因、警告与 Provider 错误；
- 同一 Attempt 内的受限工具往返、Trace 和文件关闭。

当前 `ZhipuChatCompletionsProvider` 只接受标准 API 的固定 Chat Completions endpoint，不接受 Coding Plan endpoint，不自动改模型，不跨 Provider fallback。它可以成为 Provider-neutral `capability_gate` 的候选实现，但前提是用户在本地确认 key 属于标准开放平台、账户已明确开放精确模型 ID，并授权自建 Workbench 调用。仅有 key 或只在配置中写入 `glm-5.3` 不能证明这些条件。

### 2.2 Coding Plan Codex `native-agent`

Coding Plan + 官方 Codex 是平台 Runtime 路线，不是 Workbench 直接 `ModelProvider`。Codex 进程可以冻结 requested model、base URL、wire API、客户端请求指纹和运行时证据，但中间平台会成为新的信任边界。除非它提供可核验的服务端回执，否则本地配置、命令行和客户端 JSONL 只能证明“请求了什么”，不能替代 Provider 对 actual model/provider 的断言。

因此：

- Coding Plan key 不得交给标准 Zhipu HTTP Adapter；
- `native-agent` 结果不得伪装成 `ModelResponse` 原始响应；
- Codex Runtime Gate 可以独立证明受控平台传输与进程隔离，但不能单独满足本提案的标准 API ModelProvider identity 条件；
- Runtime 若未来取得可信的服务端 actual-model attestation，应通过单独的共同接口评审接入，不能用本地 requested model 推定 actual model。

截至 2026-08-17 查阅的官方页面将两条产品路线明确区分：GLM-5.3 模型页说明 Coding Plan 已上线该模型，而标准模型 API 将于近期上线；Codex 接入页给出的 Coding Plan 配置为 `glm-5.3`、`https://open.bigmodel.cn/api/v1` 和 `responses`。这些是有日期的产品事实，不是对任一具体账户 entitlement 的证明：

- [GLM-5.3 模型页](https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3)
- [Coding Plan 的 Codex 接入](https://docs.bigmodel.cn/cn/coding-plan/tool/codex)
- [Coding Plan 概览](https://docs.bigmodel.cn/cn/coding-plan/overview)
- [Coding Plan 使用说明](https://docs.bigmodel.cn/cn/coding-plan/usage-notes)

产品状态可能变化。执行日必须重新核对官方页面和当前账户控制台；不得把本文日期的页面状态当作永久能力声明。

## 3. 提议的 `capability_gate`

`capability_gate` 只回答一个问题：一个被明确授权的 Provider/模型/endpoint 组合，能否通过现有 Provider-neutral 内核完成受限的真实项目 Attempt，并留下可重放的审计链。

建议所有候选 Provider 使用同一组不可降低的关闭条件：

1. **显式授权**：`--execute`、唯一 Attempt ID、新报告路径、实名 `accountable_owner` 和公开合成 fixture 均在首个网络调用前冻结；默认命令不读环境、不发网络。
2. **精确绑定**：Model Assignment 在首调前冻结 Adapter ID、canonical Provider、requested model、reasoning、能力、Data Policy、预算和模型池哈希；`automatic_fallback=false`。
3. **真实 conformance**：用固定、低输出上限的 text、structured 和合同所需 client-tool 检查真实 endpoint。缺少硬能力、远端结构与声明不符或本地 Schema 失败均 fail closed。
4. **Provider-asserted identity**：actual model 必须来自 Provider 响应中 Adapter 映射的模型身份，而不是环境变量、配置文件、请求体、CLI 输出或客户端自述；它必须与 requested model 精确一致。canonical Provider 也必须与运行时能力快照一致。
5. **正常项目路径**：conformance 通过后，通过现有 `run_task_api_attempt` 执行公开合成 evidence/H2 fixture，而不是另建一个绕过编译器、Tool Registry 或 closeout 的演示请求。
6. **有界执行**：模型轮次、Provider 调用、客户端工具、单轮 fan-out、工具结果大小、累计 token、单轮输出和 wall time 都必须在首调前固定；Adapter 和 Gate 不重试，不自动升级、降级或换 Provider。
7. **工具与数据边界**：只暴露合同与 Assignment 交集中的只读工具，重核冻结输入哈希；不得启用 Provider server tools、任意代码、任意路径、写入或研究私有数据。
8. **完整关闭**：终态必须发布 Model Assignment、Attempt、Agent Trace、Handoff、Execution Receipt 和 Main State；只有合同准入成功才发布科研输出；Main State 最后提交。
9. **文件式恢复**：新的 Python 进程只从发布文件恢复到正确下一动作，不调用 Provider，不依赖 Provider conversation/response ID。
10. **诚实结论**：报告明确记录 requested/observed provider-model、no fallback、预算、usage 完整性、capture gaps 和 monetary assurance；任何 `not-run`、`failed` 或 `safe-paused` 都不能提升为 passed。

双 Execution Contract、H1/H2 分级、Human Gate、Trace、Handoff 和 shared Model Assignment 的既有语义保持不变。本提案只建议替换“必须是 OpenAI”这一 Provider 特定关闭条件，不建议修改路诚钺维护的上游选择或交接接口。

## 4. Provider-asserted model identity 的证据等级

为防止“配置写了 GLM-5.3，所以实际就是 GLM-5.3”的循环证明，建议在未来 Gate Decision 中区分以下证据。名称目前只是提案术语，不能在共同 Schema 未批准前写入权威对象：

| 等级 | 可接受证据 | 对 `capability_gate` 的意义 |
|---|---|---|
| `provider-asserted` | 直接 Provider 响应由专属 Adapter 映射出 canonical provider 与 exact `model` | 可满足 identity 条件 |
| `trusted-runtime-attested` | 平台提供可验证、与具体响应绑定的服务端 actual provider/model attestation | 待单独共同评审；不能预先视为等价 |
| `client-request-attested` | 环境变量、配置、请求体、命令行、客户端日志或请求指纹只显示 requested model | 只能证明请求意图，不能满足 actual identity |
| `unknown` | 响应未返回 identity，或平台发生不可见路由 | Gate 失败或安全暂停 |

模型别名、自动切换或 Provider 返回不同模型，即使输出可用，也必须创建新的审阅决定或新 Attempt；不得在原 Attempt 中把 requested 与 observed 强行归一化。

## 5. `monetary_accounting` 与能力验收分离

token、调用数、轮次和 wall time 是执行器可以在调用边界直接约束的资源。请求级货币金额则可能只存在于 Provider 账单、套餐积分或外部价目表中。建议不要把这些证据混成单一 `provider_reported_cost` 含义。

建议未来 Provider-neutral/shared 报告采用以下独立保证等级；字段名仍需共同 ADR/Schema 审批。当前 Zhipu 专属 report/Decision 只用向后兼容的可选 `status_scope` 与 `monetary_cost` 表达最小分层，不改变任何共享执行工件 Schema，也不预先批准下表成为项目级合同：

| 等级 | 证据 | 可作何种声明 |
|---|---|---|
| `provider-reported` | Provider 响应返回金额与币种，且与 Attempt 用量绑定 | 可执行响应级货币 ceiling |
| `billing-reconciled` | 运行后用 Provider 官方账单/控制台导出与 Attempt 时间、账户、模型和用量对账 | 可声明事后核对；不能冒充响应字段 |
| `tariff-derived` | 用冻结价目表或 Coding Plan 积分公式计算 | 只能作为估算，必须保留价目表版本、日期、单位和公式 |
| `unavailable` | 没有可核验的请求级或账单级金额 | 明确缺口；不得填 0、猜币种或假称受货币上限保护 |

推荐的 addendum 语义是：

- `capability_gate` 可以在 `monetary_accounting=unavailable` 时通过，但必须在首调前显式选择“不设置响应级货币 ceiling”，并以严格的 Provider 调用、token、轮次、输出和 wall-time 上限限制技术执行范围；
- 实名负责人必须明确授权该次“金额未知、资源硬上限已冻结”的公开合成调用；报告不得声称货币预算已受控；
- 如果 Task 或组织政策要求可证明的货币上限，则该政策仍应阻断或 `safe-paused`，不能由 capability Gate 绕过；
- 价目表推算、Coding Plan 积分或套餐额度不得写为 `provider_reported_cost`；
- OpenAI/Zhipu 的 Provider 专属财务准入可继续 pending，而不抹掉已取得的能力证据。

这不是放宽“硬预算不可测时应停止”的原则，而是要求在执行前准确声明本次硬预算究竟是 token/call/time，还是货币。若共同负责人决定“项目级关闭必须同时具有货币证明”，则应保留当前严格 Gate，并明确它等待账单对账或 Provider 成本接口；不能同时把现状描述成普通 key 即可通过。

## 6. 非秘密 preflight

用户不应向 Agent、Issue、命令历史、报告或仓库提供 key。执行负责人只需先确认并记录以下非秘密事实：

1. 产品类型是“标准开放平台 API”还是“Coding Plan”；
2. 控制台显示的 endpoint 类别和精确模型 ID；
3. 当前账户是否明确获得该模型 entitlement；
4. 产品条款是否允许由自建 Workbench 调用；
5. 区域、Data Policy、公开合成输入和 accountable owner 是否已批准；
6. 本次允许的 Provider 调用数、token、轮次、工具、时间，以及是否要求货币证明；
7. 输出报告和 Attempt ID 都是新的，不会覆盖既有证据。

任何产品类型、endpoint、entitlement 或自建授权不明确时，只运行零环境 dry-run：

```powershell
rwb providers zhipu-gate
```

该命令按现有 Runbook 不读取环境、不发网络。只检查变量存在性时可使用：

```powershell
rwb providers probe `
  --config registry/providers/adapters.yaml `
  --check-environment
```

存在性结果只能是 preflight 信息，不能证明授权或模型可用。若 key 属于 Coding Plan，停止标准 Zhipu Gate，转入独立 `native-agent` 安全评审；当前 [GLM-5.3 Runbook](GLM_LIVE_GATE_RUNBOOK.md) 中所有 live-ready 开关未满足前不得注入真实 key。

## 7. 共同 addendum 与迁移顺序

建议采用新的共同 ADR/addendum，而不是静默改写 ADR-0013 的历史文本。共同决定至少应明确以下选择：

| 决策点 | 推荐选择 | 仍可选择的严格方案 |
|---|---|---|
| 项目级 live Provider | 任一通过共同 `capability_gate` 的命名 Provider/model/endpoint | 继续只接受 OpenAI |
| actual model 证据 | 直接 Provider-asserted exact identity | 对可信 runtime attestation 另行定义等价条件 |
| 货币证据 | 与 capability 分级报告；缺失不抹掉能力证据 | 要求货币证明后才关闭项目节点 |
| Coding Plan Codex | 独立 `native-agent` Runtime Gate | 暂不纳入任何项目级关闭证据 |
| 既有 OpenAI Gate | 保留为 OpenAI 专属证据 | 继续作为唯一项目级 Gate |

共同接受后，实施顺序应为：

1. 新增共同 ADR/addendum，只 supersede ADR-0013 验收边界中的 Provider 特定句；双合同、H1/H2、Trace、Model Assignment、恢复和科研声明边界保持原样。
2. 由两位负责人共同确认 Provider-neutral/shared Gate report/Decision 是否需要向后兼容的字段扩展；在此之前不修改共享 Schema。现有 Zhipu 专属可选字段保持局部证据语义，不得被解释为共同接口已获批准。
3. 提取 Provider-neutral Gate evaluator，让 OpenAI 和 Zhipu 只保留认证、endpoint、Adapter 和 Provider 特有 conformance 差异；不得复制一个更弱的 GLM 专用成功路径。
4. 增加负面测试：缺 key、错误产品 endpoint、返回模型不一致、identity 缺失、工具越界、usage 缺失、cost unavailable、fallback、重放和恢复期间网络调用。
5. 先以 fake Provider 验证新 Decision 组合，再由实名负责人在已授权 Windows 会话中运行一个新的标准 API Attempt；报告只保存脱敏控制面证据。
6. 只有当 live report、Decision、Attempt/Trace/Receipt/Main State 和 fresh-process 结果全部由当前 validator 验证后，才更新项目状态。OpenAI 或 Zhipu 的未运行 Provider 专属 Gate 继续保持 pending。
7. Coding Plan Codex 按独立 Runtime 安全 Gate 推进；除非未来共同 ADR 接受可信 attestation，否则不用于替代标准 ModelProvider identity。

回滚策略也必须简单：在新 addendum 未合并或 live 证据未通过时，继续使用 ADR-0013 原关闭条件；任何试验字段都保持可选，既有 `0.1.0` fixture 和历史 Attempt 不重写。

## 8. 本提案不证明什么

即使未来 `capability_gate` 通过，也只证明某个命名 Provider/模型/endpoint 在特定时间、账户、区域和配置下完成了受限的合成执行与审计闭环。它不证明：

- 模型回答、Evidence、Simulation 或 Claim 在科学上正确；
- Human Gate、同行评审或研究者批准已经完成；
- 私有研究数据已获准发送给该 Provider；
- 其他模型版本、别名、区域、账户或未来服务状态相同；
- Coding Plan Runtime 与标准 API 具有相同的 Provider identity、usage 或成本证据；
- `tariff-derived` 金额等于 Provider 报告或最终账单。

真实 Gate 的科研结论必须继续停在 `stage-completed` 或适用的 Human Gate 边界，不能因结构化输出、Trace 完整或文件恢复成功而自动提升 Claim。

## 9. 共同审阅清单

本提案进入实现前，黄毅与路诚钺应逐项共同确认：

- [ ] 是否同意把项目级 Provider 条件从“OpenAI”改为命名且通过共同 Gate 的 Provider；
- [ ] 是否同意 `capability_gate` 与 `monetary_accounting` 分级，而不是同一个 passed 布尔值；
- [ ] 金额不可得时，哪些 Task/组织政策仍必须阻断；
- [ ] 只接受 `provider-asserted` identity，还是为可信 Runtime attestation 新建独立条件；
- [ ] 哪些 Gate report/Decision 字段需要兼容扩展及其 owner；
- [ ] OpenAI 专属 Gate、Zhipu 标准 Gate 和 Codex native-agent Gate 的状态如何并列展示；
- [ ] addendum 的 supersede 范围、迁移顺序、回滚条件和历史工件兼容性；
- [ ] 所有表述是否继续明确“不证明科研正确性”。

在清单与共同 ADR/addendum 未完成前，本文件只能作为讨论和实现设计输入，不能作为项目状态、验收通过或真实调用授权。
