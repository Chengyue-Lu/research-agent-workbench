# 官方字段覆盖与待核清单

本表按 [M6-009 计划](PLAN.md) 的资料字段整理 **2026-10-02 已冻结的文档摘要**，编辑日期为 2026-10-03。覆盖十一家公共服务/网关；Azure、Vertex、Bedrock 的认证与部署边界另列。本轮只读既有来源记录，未访问网络或 Provider API。

`D` 表示已冻结摘要给出明确字段事实；`P` 表示有相关事实，但该字段尚有列明的 exact 条件待核；`U` 表示本轮已读摘要尚无可填值。`U` 不表示官方没有该资料，也不表示服务不支持。每项都有已收集的官方入口或后续核验入口；HTTP200、URL 存在或来源 hash 不等于该字段已被核验。

事实始终保留 model/surface/mode 与日期边界。协议兼容、厂商文档、离线实现、账户可用和具名 live 接受分开。本表不改变 Task 状态、选择模型或授予运行资格；高级能力允许继续明确待核或拒绝。只对首轮 DeepSeek Flash 的非思考 Tool 要求原生关闭，不要求全部厂商以同一模式接入。

## 字段与数量

| ID | 字段 |
|---|---|
| F01 | endpoint / API surface |
| F02 | 认证 |
| F03 | 访问区域 / 部署区域 |
| F04 | model alias / revision |
| F05 | 角色 |
| F06 | ToolChoice |
| F07 | Tool 往返 |
| F08 | 并行 Tool |
| F09 | Schema / JSON |
| F10 | thinking / context 续传 |
| F11 | stream / cancellation |
| F12 | usage / cache / reasoning |
| F13 | error / retry / rate |
| F14 | 价格 / 时间窗 |
| F15 | 账户数据控制 |

11 × 15 = **165 项已登记**：D 17，P 75，U 73。这是资料状态统计：92 项有已保留事实（D＋P），其中 75 项仍部分待核；73 项未填事实值。不是 165 项能力通过或 M6-009 完成率。

| 服务 | D | P | U |
|---|---:|---:|---:|
| OpenAI | 2 | 6 | 7 |
| Anthropic | 2 | 7 | 6 |
| Google Gemini Developer API（含独立 Gemma 文档事实） | 2 | 6 | 7 |
| DeepSeek | 3 | 9 | 3 |
| Alibaba Qwen / DashScope | 1 | 6 | 8 |
| Zhipu GLM / Z.AI / 智谱 | 1 | 5 | 9 |
| Moonshot / Kimi | 1 | 6 | 8 |
| MiniMax | 1 | 6 | 8 |
| SiliconFlow | 2 | 9 | 4 |
| ByteDance / Ark / BytePlus | 0 | 6 | 9 |
| OpenRouter | 2 | 9 | 4 |

## OpenAI

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Responses 与 Chat 是分别定义的 API surface。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [O1][O1] |
| F02 认证 | D | Bearer 认证；surface 与 model snapshot 分别固定。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [MX][MX] |
| F03 访问区域 / 部署区域 | U | 本轮已读摘要未冻结该字段的可用值。 | 核对所选服务的访问限制、部署区域和账户地域；不能从 hostname 代填。 | [O1][O1] |
| F04 model alias / revision | P | structured-output 指南明确举出 gpt-4o-mini-2024-07-18 snapshot。 | 其他 alias 的漂移/版本、远端 observed ID 与权重身份未由文档例子证明。 | [O2][O2]、V1 |
| F05 角色 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选 Responses/Chat 的 system/developer/user/assistant/tool 映射；不能跨 surface 推广。 | [O1][O1] |
| F06 ToolChoice | P | Responses reference 有 function Tool 入口。 | 固定模型的 none/auto/required/specific、strict 与约束组合须逐项补证。 | [O1][O1]、V1 |
| F07 Tool 往返 | P | 文档定义 function Tool surface。 | 完整 call ID/arguments/result 回传及停止状态契约须逐模型/协议冻结。 | [O1][O1]、V1 |
| F08 并行 Tool | U | 本轮已读摘要未冻结该字段的可用值。 | 补 exact snapshot 的 parallel_tool_calls 与并行返回约束。 | [O1][O1] |
| F09 Schema / JSON | P | JSON Schema/strict 依模型与 Schema 子集，指南明确该 snapshot。 | 所选 Schema keyword 子集和服务器 enforcement 不能由本地 JSON 校验代替。 | [O2][O2]、V1 |
| F10 thinking / context 续传 | P | reasoning continuation 是独立语义。 | 所选非 reasoning snapshot 是否返回专有项、后续模型的续传必须分别核验。 | [MX][MX]、[O3][O3] |
| F11 stream / cancellation | P | Responses 与 Chat 的 stream 不能混 parse。 | 所选 surface 的事件、取消后 usage/charge 与终态仍待逐字段冻结。 | [MX][MX]、[O4][O4] |
| F12 usage / cache / reasoning | U | 本轮已读摘要未冻结该字段的可用值。 | 补 input/output/cache/reasoning 计数、缺失值、total 关系与失败 charge 规则。 | [O1][O1] |
| F13 error / retry / rate | U | 本轮已读摘要未冻结该字段的可用值。 | 错误页已有收集条目；补所选协议错误体、retry 与账户 RPM/TPM，HTTP200 不等于字段已读。 | [O5][O5] |
| F14 价格 / 时间窗 | U | 本轮已读摘要未冻结该字段的可用值。 | 从官方导航定位所选 snapshot 定价、cache 计价和时间窗；本轮不写数值。 | [O1][O1] |
| F15 账户数据控制 | U | 本轮已读摘要未冻结该字段的可用值。 | 从官方导航定位账户 retention/training/region 政策并绑定实际账户；不据原厂身份推定。 | [O1][O1] |

## Anthropic

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Messages；overview 固定 /v1/messages。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [AN1][AN1]、V1 |
| F02 认证 | D | overview 保留 x-api-key；api version 与 workspace 独立，当前摘要也区分 Bearer。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [AN1][AN1]、[MX][MX] |
| F03 访问区域 / 部署区域 | U | 本轮已读摘要未冻结该字段的可用值。 | 核对所选 workspace/账户访问区域与部署/处理区域；未知保持未知。 | [AN1][AN1] |
| F04 model alias / revision | P | thinking 示例使用 claude-sonnet-4-6。 | 例子中的 ID 不认证当前权限、immutable revision 或 allowed observed alias。 | [AN2][AN2]、V1 |
| F05 角色 | U | 本轮已读摘要未冻结该字段的可用值。 | 补 Messages 的 system 与 messages role 边界，不能复制 Responses developer 规则。 | [AN3][AN3] |
| F06 ToolChoice | P | 文档存在 strict Tool surface。 | exact model 的 choice、strict 与 thinking 组合尚未逐项冻结。 | [AN4][AN4]、[MX][MX] |
| F07 Tool 往返 | P | Messages reference 定义 text/Tool 形状。 | tool_use/tool_result 与 signature 的 exact 往返细则仍需单独冻结。 | [AN3][AN3]、V1 |
| F08 并行 Tool | U | 本轮已读摘要未冻结该字段的可用值。 | 补 exact model/模式的并行 Tool 与控制参数。 | [AN3][AN3] |
| F09 Schema / JSON | P | 文档有 output_config.format 与 strict Tool。 | 该 exact model 的 Schema 子集/enforcement 未由摘要闭合。 | [AN4][AN4]、[MX][MX] |
| F10 thinking / context 续传 | P | thinking/signature 有专有续传语义；示例包含 disabled-thinking 形状。 | 需要思考/签名的组合不能从 plain text 契约推导。 | [AN2][AN2]、[AN3][AN3]、V1 |
| F11 stream / cancellation | P | stream 有专有格式。 | 事件和取消后终态/计费须对所选 Messages 模式冻结。 | [AN5][AN5]、[MX][MX] |
| F12 usage / cache / reasoning | P | usage-cache 有专有语义。 | 补 cache creation/read、reasoning 与 input/output 的计数关系、缺失与失败值。 | [AN3][AN3]、[MX][MX] |
| F13 error / retry / rate | U | 本轮已读摘要未冻结该字段的可用值。 | 错误页已收集；补结构化 error/retry 和账户 RPM/TPM，不能从兼容接口猜限额。 | [AN6][AN6] |
| F14 价格 / 时间窗 | U | 本轮已读摘要未冻结该字段的可用值。 | 从官方导航定位 exact model 的定价、缓存计价/时间窗，订阅与 API 分开。 | [AN1][AN1] |
| F15 账户数据控制 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选 workspace 的日志/retention/training/地域约束及官方账户政策。 | [AN1][AN1] |

## Google Gemini Developer API（含独立 Gemma 文档事实）

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | generateContent / streamGenerateContent；native API 示例为 /v1beta/models/{model}:generateContent。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [G1][G1]、V1 |
| F02 认证 | D | API-key guide 支持 x-goog-api-key。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [G2][G2]、V1 |
| F03 访问区域 / 部署区域 | U | 本轮已读摘要未冻结该字段的可用值。 | Developer API 的账户访问限制、处理/部署区域须另核；不可据 Google 身份推广到 Vertex。 | [G2][G2] |
| F04 model alias / revision | P | 旧 gemini-2.0-flash 在后续 models/deprecations 明确已关闭；Gemma 官方页列 gemma-4-26b-a4b-it / gemma-4-31b-it。 | Gemma facts 仅 dated extracted view；新 alias/revision、当前账户权限与 observed ID 仍未认证。 | [G3][G3]、[G4][G4]、[G5][G5]、V2 |
| F05 角色 | P | Gemma 页有 text、system instruction 与 multi-turn 示例。 | 不能从示例推广全部 Gemini/Gemma role 或跨模型映射。 | [G5][G5]、V2 |
| F06 ToolChoice | U | 本轮已读摘要未冻结该字段的可用值。 | function calling 示例不完整覆盖每个模型的 none/auto/required/specific；须所选 model card/API reference 另核。 | [G6][G6] |
| F07 Tool 往返 | P | functionCall/Response 是 native 形状；Gemini3 Tool 签名须原样续传。 | Gemma text 示例不等于 Gemma Tool 往返已经验收。 | [G6][G6]、[G7][G7]、[MX][MX]、V2 |
| F08 并行 Tool | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选模型并行函数调用和返回配对约束。 | [G6][G6] |
| F09 Schema / JSON | P | response Schema 为子集；2.5 Flash-Lite 在结构化输出表，Gemini3 mixed feature 是另列 preview。 | JSON 模式、所选模型 keyword/enforcement 与混合 Tool 支持须分开。 | [G8][G8]、V2 |
| F10 thinking / context 续传 | P | Gemma4 特有 minimal=off；Gemini3 minimal 不能当 off；2.5 Flash-Lite 可 thinkingBudget=0。 | Gemma/各 Gemini 思考与 thoughtSignature 续传分别核；账户及返回内容未实测。 | [G5][G5]、[G7][G7]、[G9][G9]、V2 |
| F11 stream / cancellation | P | native streamGenerateContent 独立于 OpenAI stream。 | 所选模型事件、取消后终态/用量仍待冻结。 | [G1][G1]、[MX][MX] |
| F12 usage / cache / reasoning | U | 本轮已读摘要未冻结该字段的可用值。 | 补 prompt/candidate/total/thought/cache 字段、缺失值与输出上限关系；不推断 thoughts=0。 | [G1][G1] |
| F13 error / retry / rate | U | 本轮已读摘要未冻结该字段的可用值。 | troubleshooting 页已收集；补所选模型错误体、retry、账户 rate/tier。 | [G10][G10] |
| F14 价格 / 时间窗 | U | 本轮已读摘要未冻结该字段的可用值。 | 从官方 model/API 导航定位所选 Gemini 或 Gemma 的价格/额度/时间窗；不把“低成本”当数值。 | [G3][G3]、[G5][G5] |
| F15 账户数据控制 | U | 本轮已读摘要未冻结该字段的可用值。 | 补 Developer API 所选账户/计费层的数据处理、retention/training/地域；不由无历史用户限制推断权限。 | [G2][G2]、[G3][G3] |

## DeepSeek

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Responses、Chat 与 Anthropic-compatible 分别有入口；Responses reference 与 guide 独立。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [DS1][DS1]、[DS2][DS2]、[DS3][DS3]、[MX][MX] |
| F02 认证 | D | Bearer 认证。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [MX][MX]、[DS4][DS4] |
| F03 访问区域 / 部署区域 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选账户服务访问/处理区域和数据地域，不从 api.deepseek.com 猜部署。 | [DS1][DS1] |
| F04 model alias / revision | P | 2026-10-02 pricing snapshot 将 deepseek-flash 标为 DeepSeek-V4.1-Flash。 | alias 可漂移；实际 observed ID、权重/账户仍需 exact live binding。 | [DS4][DS4]、V1 |
| F05 角色 | P | Responses guide 的 developer 降 user 语义与原厂 Responses 不同。 | 所选 role 的完整白名单须按 exact surface 冻结；文档兼容不授予隐式身份替换。 | [DS2][DS2]、[MX][MX] |
| F06 ToolChoice | P | Responses/Chat 的 Tool choice、thinking 与 strict 入口有差别。 | exact Flash + off 的 choice/strict 组合须按所选 surface 单独核验。 | [DS1][DS1]、[DS3][DS3]、[DS5][DS5] |
| F07 Tool 往返 | P | 官方 Tool guide 定义客户端执行及函数结果往返。 | Session 两轮/本地纯函数执行与业务结果是独立实现验收。 | [DS5][DS5] |
| F08 并行 Tool | D | 已冻结准备摘要指出所选 service 总启用并行 Tool calling。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [DS2][DS2]、V1 |
| F09 Schema / JSON | P | Responses format、Chat JSON mode 与 Beta strict/Schema 子集各有独立规则。 | 不能由 Chat strict 或本地 Schema PASS 推导 Responses remote strict。 | [DS1][DS1]、[DS5][DS5]、[DS6][DS6]、V1 |
| F10 thinking / context 续传 | P | Responses reasoning.effort=none 关闭思考；Chat thinking.disabled；thinking guide 另列上下文续传限制。 | 首轮仅 Flash off；其他 mode/续传与模型不得自动继承。 | [DS1][DS1]、[DS3][DS3]、[DS7][DS7]、V1 |
| F11 stream / cancellation | U | 本轮已读摘要未冻结该字段的可用值。 | 官方 stream/keep-alive 相关入口已收集；精确取消/最终 usage/charge 契约需逐 surface 提取。 | [DS1][DS1]、[DS8][DS8] |
| F12 usage / cache / reasoning | P | pricing 区分 input cache-hit、cache-miss、output；reference/guide 描述停止与 usage。 | 失败/取消/reasoning 总量及缺失计数不能填零，实际账单另验。 | [DS1][DS1]、[DS4][DS4] |
| F13 error / retry / rate | P | errors 文档含 402/422 与 auth/rate/transient 错误；Rate Limit & Isolation 为账户级限制。 | 具体账户阈值、retry 与失败 charge 仍待绑定；user isolation 不等于 fresh 上下文。 | [DS8][DS8]、[DS9][DS9] |
| F14 价格 / 时间窗 | P | dated 闲时 USD/1M：input-hit 0.003、input-miss 0.15、output 0.60；工作日高峰 UTC01–04/06–10，排除中国公共假日，其余闲时。 | 运行前重核价格/节假日与北京时间18:00后约束；文档价格不是用户预算或实际 charge。 | [DS4][DS4]、[MX][MX] |
| F15 账户数据控制 | U | 本轮已读摘要未冻结该字段的可用值。 | 补账户日志/retention/training/区域控制的官方政策；本轮不声明 data-control capability。 | [DS1][DS1] |

## Alibaba Qwen / DashScope

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Chat + Responses compatible-mode；Chat reference 固定 Virginia access origin。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [Q1][Q1]、[Q2][Q2]、V1 |
| F02 认证 | P | 地区/workspace/Key 须一起绑定。 | 所选 surface 的认证 header、workspace scope 和账户 entitlement 尚须具体核验。 | [Q1][Q1]、[MX][MX] |
| F03 访问区域 / 部署区域 | P | 准备摘要有 Virginia access_region。 | 访问点不等于 model deployment/处理地域；所选账户 region/workspace 未实测。 | [Q1][Q1]、V1 |
| F04 model alias / revision | P | 官方 Tool 示例 qwen3.8-max，结构化指南列 Qwen3.8-Max。 | alias/revision、observed ID 与当前账户权限不能由示例认证。 | [Q1][Q1]、[Q3][Q3]、V1 |
| F05 角色 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选 compatible surface 对 system/developer/user/tool 的角色支持/降级规则。 | [Q1][Q1]、[Q2][Q2] |
| F06 ToolChoice | U | 本轮已读摘要未冻结该字段的可用值。 | 补 qwen3.8-max + enable_thinking=false 的 choice/strict 子集。 | [Q4][Q4] |
| F07 Tool 往返 | P | 有 function Tool 与 thinking=false 示例。 | exact model 的 call ID/arguments/result 及多轮边界仍待逐字段冻结。 | [Q4][Q4]、V1 |
| F08 并行 Tool | U | 本轮已读摘要未冻结该字段的可用值。 | 补 exact model/mode 的 parallel_tool_calls 及响应并行限制。 | [Q4][Q4] |
| F09 Schema / JSON | P | json_object 和 json_schema 支持 model/mode 集合不同；指南列 Qwen3.8-Max Schema 支持。 | JSON 与 strict enforcement/keyword 子集不互换。 | [Q3][Q3]、V1 |
| F10 thinking / context 续传 | P | qwen3.8-max Tool 示例发送 enable_thinking=false。 | 不得推广至全 Qwen；reasoning/context 续传未由 off 请求证明。 | [Q4][Q4]、[Q5][Q5]、V1 |
| F11 stream / cancellation | U | 本轮已读摘要未冻结该字段的可用值。 | stream 页已收集；补 exact 模式事件、结束与取消后 usage。 | [Q6][Q6] |
| F12 usage / cache / reasoning | U | 本轮已读摘要未冻结该字段的可用值。 | 摘要只指出 usage 另有参数；补 cache/reasoning 与 output 上限/总量关系。 | [Q1][Q1] |
| F13 error / retry / rate | U | 本轮已读摘要未冻结该字段的可用值。 | error-code 页已收集；补 exact surface 的错误、retry 和账户/region 的 RPM/TPM。 | [Q7][Q7] |
| F14 价格 / 时间窗 | U | 本轮已读摘要未冻结该字段的可用值。 | 从官方导航定位所选 region/model 的定价、cache/思考计价与时间窗。 | [Q1][Q1] |
| F15 账户数据控制 | U | 本轮已读摘要未冻结该字段的可用值。 | 补该 region/workspace 账户的数据 retention/training/跨境/处理地域政策。 | [Q1][Q1] |

## Zhipu GLM / Z.AI / 智谱

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | 国际 Chat /api/paas/v4；中国 Responses /api/v1、Claude-compatible /api/anthropic 独列。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [Z1][Z1]、[Z2][Z2]、[Z3][Z3]、[MX][MX] |
| F02 认证 | P | 国际/中国/Coding Plan 账户分开。 | 所选账户认证 header/token scope 未在本轮摘要逐项冻结，不以兼容性推定互换。 | [Z1][Z1]、[Z2][Z2]、[MX][MX] |
| F03 访问区域 / 部署区域 | P | 国际与中国 surface 不能相互推广。 | access 限制、deployment/处理地域与账户绑定仍 unresolved。 | [Z1][Z1]、[Z2][Z2]、[MX][MX] |
| F04 model alias / revision | P | 国际 enum 列 glm-5.2；thinking 文档排除强制思考 GLM-5.3/5.3-FLASH。 | revision/alias 当前解析和账户可用未观测。 | [Z1][Z1]、[Z4][Z4]、V1 |
| F05 角色 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选国际 Chat role 规则，不借中国 Claude-compatible 语义。 | [Z1][Z1] |
| F06 ToolChoice | U | 本轮已读摘要未冻结该字段的可用值。 | 补 exact glm-5.2 off 的 choice/strict 控制。 | [Z1][Z1] |
| F07 Tool 往返 | U | 本轮已读摘要未冻结该字段的可用值。 | API 有 Tool surface；完整 exact call/result 往返须另提取冻结。 | [Z1][Z1] |
| F08 并行 Tool | U | 本轮已读摘要未冻结该字段的可用值。 | 补该模型/模式并行 Tool 控制与返回集合。 | [Z1][Z1] |
| F09 Schema / JSON | P | 已读 Z.AI JSON Object 不是 server Schema 保证。 | exact Schema/JSON dialect、keyword 与 enforcement 保持 unresolved。 | [Z5][Z5]、[MX][MX]、V1 |
| F10 thinking / context 续传 | P | thinking.disabled 适用范围按型号；强制思考型号例外。 | clear_thinking/effort 与续传需 exact 模式核验。 | [Z4][Z4]、V1 |
| F11 stream / cancellation | U | 本轮已读摘要未冻结该字段的可用值。 | stream 页已有收集条目；补 exact 事件和 cancellation usage/charge。 | [Z6][Z6] |
| F12 usage / cache / reasoning | U | 本轮已读摘要未冻结该字段的可用值。 | 补 prompt/completion/cache/reasoning 计数和缺失值/总量，不复制其他 Chat 服务。 | [Z1][Z1] |
| F13 error / retry / rate | U | 本轮已读摘要未冻结该字段的可用值。 | 国际与中国 errors 均有收集条目；补所选账户/surface error/retry/rate 数值。 | [Z7][Z7]、[Z8][Z8] |
| F14 价格 / 时间窗 | U | 本轮已读摘要未冻结该字段的可用值。 | 从官方 model/API 导航定位国际/中国/Coding Plan 所选 API 定价和时间窗。 | [Z1][Z1]、[Z2][Z2] |
| F15 账户数据控制 | U | 本轮已读摘要未冻结该字段的可用值。 | 补 exact 账户服务的数据控制/日志/retention/training 与地域条款。 | [Z1][Z1]、[Z2][Z2] |

## Moonshot / Kimi

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Chat /api.moonshot.ai/v1/chat/completions；另列 Responses 与 Messages；文档迁至 platform.kimi.ai。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [K1][K1]、[K2][K2]、[K3][K3]、[MX][MX]、V1 |
| F02 认证 | P | Moonshot Key；兼容 surface 与区域账户须区分。 | exact header/workspace/token scope 未在摘要完整冻结。 | [K1][K1]、[MX][MX] |
| F03 访问区域 / 部署区域 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选账户/域名的访问地域和 deployment/处理地域。 | [K1][K1] |
| F04 model alias / revision | P | model overview 用 kimi-k2.6 且列专有参数约束。 | k3/k2.7-code 等不是同一 profile；alias/revision/observed identity 未认证。 | [K4][K4]、V1 |
| F05 角色 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选 Chat role 与 reasoning_content/history 的角色约束。 | [K1][K1]、[K5][K5] |
| F06 ToolChoice | P | 准备摘要记录 required 不支持、specific 未验证；不得按通用 Chat 视为支持。 | exact none/auto/specific 与模式组合须另核。 | [K1][K1]、[K4][K4]、V1 |
| F07 Tool 往返 | P | 官方 Tool guide 已列入收集导航。 | 本轮摘要未冻结完整 call/result配对与每一错误/停止状态。 | [K6][K6] |
| F08 并行 Tool | U | 本轮已读摘要未冻结该字段的可用值。 | 补 exact 模型 off 的并行调用与控制字段。 | [K6][K6] |
| F09 Schema / JSON | P | 格式/Schema 稳定性随 k3/k2.7-code/k2.6 不同。 | 该 profile 的复杂 Schema/enforcement 未冻结。 | [K7][K7]、[MX][MX] |
| F10 thinking / context 续传 | P | kimi-k2.6 overview 接受 thinking.disabled；参数 override 有限制。 | preserved reasoning/context 续传须独立 contract，不能由 disabled 推导。 | [K4][K4]、[K5][K5]、V1 |
| F11 stream / cancellation | U | 本轮已读摘要未冻结该字段的可用值。 | stream 页已收集；补该模型事件、取消与返回 usage。 | [K8][K8] |
| F12 usage / cache / reasoning | U | 本轮已读摘要未冻结该字段的可用值。 | 补 cache/reasoning/prompt/completion 总量与缺失值，不从 Chat family 推值。 | [K1][K1] |
| F13 error / retry / rate | U | 本轮已读摘要未冻结该字段的可用值。 | errors 页已收集；补所选账户 rate、retry 与 failed charge。 | [K9][K9] |
| F14 价格 / 时间窗 | U | 本轮已读摘要未冻结该字段的可用值。 | 从官方 model/API 导航定位 exact Kimi 及区域账户定价/cache/时间窗。 | [K4][K4] |
| F15 账户数据控制 | U | 本轮已读摘要未冻结该字段的可用值。 | 补该账户 retention/training/日志及地域数据控制。 | [K1][K1] |

## MiniMax

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Chat、Responses、Anthropic-compatible 独列；Responses 为 /v1/responses。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [M1][M1]、[M2][M2]、[M3][M3]、[MX][MX]、V1 |
| F02 认证 | P | Bearer API Key；订阅/PAYG entitlement 分开。 | 实际所选账户权限和版本适用性未验证。 | [M1][M1]、V1 |
| F03 访问区域 / 部署区域 | U | 本轮已读摘要未冻结该字段的可用值。 | 核对所选服务的 access/deployment/处理地域，不能由域名或模型publisher推值。 | [M1][M1] |
| F04 model alias / revision | P | 所选文档 exact MiniMax-M3；M3.1-Flash-Preview 与 M2.x 另列。 | alias/revision 与远端 observed identity/账户可用仍未认证。 | [M1][M1]、V1 |
| F05 角色 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选 Responses 的 role 规则，不能从 Anthropic-compatible 反推。 | [M1][M1] |
| F06 ToolChoice | P | MiniMax-M3 文档支持的 ToolChoice 为 none/auto。 | required/specific 未形成支持依据，不能默认启用。 | [M1][M1]、V1 |
| F07 Tool 往返 | P | function calling guide 和思考 Tool 块存在专有语义。 | 完整 exact M3 off 的 call/result/signature 往返仍待逐字段核验。 | [M4][M4]、[MX][MX] |
| F08 并行 Tool | U | 本轮已读摘要未冻结该字段的可用值。 | 补 exact M3/模式的并行 Tool 控制与返回上限。 | [M4][M4] |
| F09 Schema / JSON | P | strict Schema 保证未确认。 | 补所选 model/surface 的 JSON/Schema keyword 与 enforcement。 | [M1][M1]、[MX][MX] |
| F10 thinking / context 续传 | P | M3 默认无非none effort时思考off；M3.1-Flash-Preview none报400；M2.x不能由none保证off。 | 思考 Tool 块续传独立，不把其他M系继承为同一off profile。 | [M1][M1]、V1、[MX][MX] |
| F11 stream / cancellation | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选 Responses stream 事件、取消/终态与用量；兼容 Messages stream 不能代替。 | [M1][M1] |
| F12 usage / cache / reasoning | U | 本轮已读摘要未冻结该字段的可用值。 | 补缓存/思考 usage 分项、计数关系及失败值；不从 off 请求填零。 | [M1][M1] |
| F13 error / retry / rate | U | 本轮已读摘要未冻结该字段的可用值。 | errorcode 页已收集；补 exact surface/账户 rate 与retry、失败 charge。 | [M5][M5] |
| F14 价格 / 时间窗 | U | 本轮已读摘要未冻结该字段的可用值。 | 从官方 API 导航定位 exact M3 的PAYG/cache/时间窗；订阅金额不替API单价。 | [M1][M1] |
| F15 账户数据控制 | U | 本轮已读摘要未冻结该字段的可用值。 | 补该服务账户 retention/training/日志/处理地域。 | [M1][M1] |

## SiliconFlow

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | China hosted Chat：POST https://api.siliconflow.cn/v1/chat/completions。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [SF1][SF1]、[SF2][SF2] |
| F02 认证 | D | Bearer API Key；operator 为 SiliconFlow，publisher/model 全名另列。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [SF1][SF1]、[SF2][SF2] |
| F03 访问区域 / 部署区域 | P | 已冻结 China access endpoint；国际站不能给中国账户授权。 | 真实 deployment/processing region、账户权限未观测。 | [SF1][SF1]、[SF2][SF2]、V2 |
| F04 model alias / revision | P | API 示例 deepseek-ai/DeepSeek-V4-Flash；stream 示例 Qwen/Qwen2.5-72B-Instruct。 | Qwen例子不证明当前serving/revision；hosted model 不等于原厂服务，observed model 必须另冻结。 | [SF1][SF1]、[SF3][SF3]、[SF2][SF2]、V2 |
| F05 角色 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选 hosted exact 模型的 system/developer/user/tool 白名单与降级规则。 | [SF1][SF1] |
| F06 ToolChoice | U | 本轮已读摘要未冻结该字段的可用值。 | 通用 tools 表不证明 exact hosted model 的 none/auto/required/specific。 | [SF1][SF1] |
| F07 Tool 往返 | P | API 有该 hosted DeepSeek 的 Tool 示例。 | exact Qwen/所选模型mode 的 call/result 往返未闭合。 | [SF1][SF1]、[SF2][SF2]、V2 |
| F08 并行 Tool | U | 本轮已读摘要未冻结该字段的可用值。 | 补 exact hosted model/mode 的并行参数和数量/返回配对约束。 | [SF1][SF1] |
| F09 Schema / JSON | P | API 列 json_object/json_schema；JSON guide 示例实际为 json_object。 | 标题/总表不证明 exact 模型 strict Schema/enforcement。 | [SF1][SF1]、[SF4][SF4]、[SF2][SF2]、V2 |
| F10 thinking / context 续传 | P | enable_thinking 泛称多数推理模型；effort 对 V4-Flash 举high/max。 | 没有 exact V4/Qwen false=off 映射；standard text 不能宣称默认off，continuation另验。 | [SF1][SF1]、[SF5][SF5]、[SF2][SF2]、V2 |
| F11 stream / cancellation | P | stream 示例分 reasoning_content/content 及 [DONE]。 | 所选 model nonstream/stream差异、取消后 usage/charge未冻结。 | [SF3][SF3]、[SF2][SF2] |
| F12 usage / cache / reasoning | P | API 示例 prompt/completion/total、reasoning/cache tokens；max_tokens不包含 reasoning。 | 样例不能证明 exact Qwen/mode用量；total/reasoning预算关系与未知分项保持unresolved。 | [SF1][SF1]、[SF2][SF2] |
| F13 error / retry / rate | P | API 有 HTTP/business/rate-limit 示例；专门error/index直读失败如实记录。 | 账户RPM/TPM、完整错误语义/retry未冻结；不从本地256/8限额造vendor quota。 | [SF1][SF1]、[SF2][SF2]、[MX][MX] |
| F14 价格 / 时间窗 | P | pricing可见文本仅部分model集合。 | 所选完整ID的价格/cache/时间窗未取得；未见Qwen2.5不能推断停售。 | [SF6][SF6]、V2 |
| F15 账户数据控制 | U | 本轮已读摘要未冻结该字段的可用值。 | 补China账户日志/retention/training/地域；不继承direct DeepSeek/DashScope政策。 | [SF1][SF1] |

## ByteDance / Ark / BytePlus

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | P | Chat/Responses；中国Volcengine与BytePlus分开；搜索回执有Singapore origin。 | 部分HTTP200为普通页/正文不完整；所选exact API surface还需强原源核验。 | [A1][A1]、[A2][A2]、[A3][A3]、[MX][MX]、V1 |
| F02 认证 | P | Key 或Access Key签名；签名model须Endpoint ID；所选BytePlus示例为Bearer。 | 不能从Bearer示例推广所有签名部署或中国账户。 | [A1][A1]、[A3][A3]、V1、[MX][MX] |
| F03 访问区域 / 部署区域 | P | BytePlus示例Singapore access，非中国endpoint证据。 | deployment/processing region与账户数据地域仍unknown。 | [A3][A3]、V1 |
| F04 model alias / revision | P | 官方搜索回执示例 seed-2-0-lite-260228。 | 来源质量为search/extracted；observed ID、revision与账户serving未认证。 | [A3][A3]、V1 |
| F05 角色 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选Chat/Responses角色规则，不能以compatible字样猜映射。 | [A2][A2] |
| F06 ToolChoice | U | 本轮已读摘要未冻结该字段的可用值。 | 补exact model/off的Tool choice与strict支持。 | [A4][A4] |
| F07 Tool 往返 | U | 本轮已读摘要未冻结该字段的可用值。 | Tool页有收集入口，但所选off组合完整往返未由摘要冻结。 | [A4][A4] |
| F08 并行 Tool | U | 本轮已读摘要未冻结该字段的可用值。 | 补exact endpoint/model/mode的parallel规则。 | [A4][A4] |
| F09 Schema / JSON | P | Schema按model约束。 | selected model的keyword/JSON/remote strict组合未闭合；HTTP200不是事实值。 | [A5][A5]、[MX][MX]、V1 |
| F10 thinking / context 续传 | P | 搜索示例包含thinking.disabled；encrypted/content/provider-state续传语义分开。 | 不推广至其他endpoint/型号；思考/加密续传尚待独立契约。 | [A3][A3]、[MX][MX]、V1 |
| F11 stream / cancellation | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选surface事件和取消后终态/usage/charge，不能复制OpenAI stream。 | [A2][A2] |
| F12 usage / cache / reasoning | U | 本轮已读摘要未冻结该字段的可用值。 | 补usage/cache/reasoning字段与上限/总量，来源正文不完整处保持unresolved。 | [A2][A2] |
| F13 error / retry / rate | U | 本轮已读摘要未冻结该字段的可用值。 | 补exact服务错误/retry/rate；明确拒绝fallback不证明账户阈值。 | [A1][A1]、[A2][A2] |
| F14 价格 / 时间窗 | U | 本轮已读摘要未冻结该字段的可用值。 | 从官方导航定位exact endpoint/model/region的价格/cache/时间窗。 | [A1][A1] |
| F15 账户数据控制 | U | 本轮已读摘要未冻结该字段的可用值。 | 补中国或BytePlus所选账户retention/training/地域/日志；两服务不共享默认承诺。 | [A1][A1] |

## OpenRouter

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | gateway Chat /api/v1/chat/completions；Responses另列，operator仍OpenRouter。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [OR1][OR1]、[OR2][OR2]、[MX][MX] |
| F02 认证 | D | Bearer OpenRouter Key；不能替代原厂Key/身份。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [OR1][OR1]、[MX][MX] |
| F03 访问区域 / 部署区域 | P | base upstream slug可匹配多区域/变体；metadata.region不是upstream部署地域。 | available upstream信息之外保持unknown，整个chain地域未认证。 | [OR2][OR2]、[OR3][OR3]、[OR4][OR4] |
| F04 model alias / revision | P | 官方例子请求openai/gpt-5.2；model页列Text/Tool/format与OpenAI/Azure供应方。 | model/alias/revision/actual upstream不由slug认证；默认model必须显式处理。 | [OR1][OR1]、[OR5][OR5]、V2 |
| F05 角色 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选gateway/model roles与转换政策；compatible不等于原厂role全支持。 | [OR1][OR1] |
| F06 ToolChoice | P | require_parameters可过滤不支持参数的供应方；默认可能忽略参数。 | ToolChoice仍依exact upstream/mode，不能由gateway字段存在声明支持。 | [OR2][OR2] |
| F07 Tool 往返 | P | API有工具转换行为，metadata可报告pipeline。 | 完整所选Tool/result/转换规则须冻结；本最小text资料不证明Tool闭合。 | [OR1][OR1]、[OR3][OR3] |
| F08 并行 Tool | U | 本轮已读摘要未冻结该字段的可用值。 | 补exact upstream/model并行Tool与gateway转换关系。 | [OR1][OR1] |
| F09 Schema / JSON | P | gateway Schema/Tool能力依upstream。 | selected model的strict/keyword/JSON enforcement未由总表认证。 | [OR6][OR6]、[MX][MX] |
| F10 thinking / context 续传 | P | effort=none是否适用依模型；exclude=true仅隐藏；mandatory reasoning会拒none。 | 不得从非推理benchmark标签推off；context continuation须exact冻结。 | [OR7][OR7]、V2 |
| F11 stream / cancellation | U | 本轮已读摘要未冻结该字段的可用值。 | stream页已收集；补gateway/upstream事件、取消后charge/usage与错误状态。 | [OR8][OR8] |
| F12 usage / cache / reasoning | P | cache-hit回复省略router metadata。 | usage/cache/reasoning计数和完整route观察不由普通model envelope闭合。 | [OR3][OR3]、[OR1][OR1] |
| F13 error / retry / rate | P | 默认router/fallback；allow_fallbacks=false禁fallback，require_parameters=true过滤不支持参数；空交集失败。 | error页有入口；账户rate、失败charge/retry仍待冻结，不允许隐式fallback补证。 | [OR2][OR2]、[OR9][OR9] |
| F14 价格 / 时间窗 | U | 本轮已读摘要未冻结该字段的可用值。 | 补所选gateway slug、upstream与cache/reasoning单价/时间窗；model列表不等于账户账单。 | [OR5][OR5] |
| F15 账户数据控制 | P | gateway与upstream数据政策独立；ZDR/data_collection偏好不建立整个chain retention/region保证。 | actual账户policy与上游unknown必须显式处理；reported metadata不是weights/privacy认证。 | [OR4][OR4]、[OR10][OR10]、[OR11][OR11] |

## 企业服务的独立边界

| 服务 | 已冻结认证 / API 事实 | 必须单独固定的部署边界 | 后续资料入口 |
|---|---|---|---|
| Azure OpenAI | `/openai/v1` Responses/Chat；resource Key 或 Entra。 | deployment 不是原厂 model alias；resource/API version/region/deployment/token scope 与实际账户权限分别固定；所选 Schema/Tool/continuation、usage/rate/价格/数据政策仍待核。 | [API lifecycle](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle)、[Responses](https://learn.microsoft.com/en-us/rest/api/aifoundry/azureopenai/responses)；R3:azure-v1 / azure-responses |
| Vertex AI | native project/location generateContent 或 OpenAI Chat-compatible；ADC/OAuth/express Key 分开。 | IAM/project/location、endpoint/model/version 和处理地域另绑；Developer API Key 不代表所有 Vertex endpoint 权限，signature/Schema 与企业账户政策仍单独核验。 | [API keys](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/api-keys)、[inference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference)；R3:vertex-auth / vertex-inference |
| Amazon Bedrock | Converse/Invoke 与其文档列出的 Responses/Chat/Messages；SigV4 或 Bedrock 专用 Bearer Key。 | runtime/mantle API、IAM/Region/model/ARN 各自固定；mantle Messages 不支持 output_config.format，AWS event stream 独立；原厂 Key 不能替该认证；其余 exact 字段待核。 | [endpoints](https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.html)、[structured output](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)、[API keys](https://docs.aws.amazon.com/en_us/bedrock/latest/userguide/api-keys-use.html)；R3:bedrock-endpoints / bedrock-structured / bedrock-auth |

## 来源强度与补证顺序

MX 为 [既有官方矩阵](OFFICIAL_MATRIX.md)，保留 R1/R2/R3 收集回执及官方原页 hash。V1 为 2026-10-02 逐家 profile source-facts 摘要：snapshot/搜索回执与结构检查分开，exact model 例子不等于账户运行；V2 为同日 Google/SiliconFlow/OpenRouter 独立补证摘要。V1/V2 的本地记录 hash 在本次文档回执中冻结，具体事实的官方链接列在各行。来源代号表示出处，不把 local record hash 冒充原始 HTTP body hash。

来源记录身份：V1（public-vendor-candidate-source-facts，observed 2026-10-02）SHA-256：`e6e3a74fb8a14bd933abcd6b911ae99658df7e0c8a198d9902fef332155342fa`；V2（local-vendor-gap-preparation，retrieved 2026-10-02）SHA-256：`82f235e922cc459d21ff6d72463cef5b10b6b516255bd0bbb2a55356e1d3a9a5`。这些是有限事实记录的 hash，非对应官方原页 body hash。

Google models/deprecations 有独立 raw/extracted hash；Gemma、部分 Ark 与 OpenRouter补证保留 dated extracted/search 事实，未取得强原始正文的字段如实保留该限制。SiliconFlow API raw/extracted 收集与专门 error/index 抓取失败分开；来源失败不代表能力缺失。本轮不读取全部 rawdocs，也不把后续新候选代码或新检索写为已接受事实。

下一次资料采集先选择 exact endpoint/model/mode，再集中核对表中 P/U：角色和 Tool choice/往返/并行、Schema keyword 与远端 enforcement、思考/签名续传、取消/失败 usage 与账户 rate，以及 pricing/time/account data。可复用已冻结 snapshot 的字段提取；需更新或缺页时另行有界获取官方来源并保存日期、质量与原始/提取 hash。账户权限和实际费用另有 live/账单证据，不能用文档填成实测。

OpenRouter 的 full endpoint slug 在要求具体 upstream 变体时才有相应观察要求；[计划](PLAN.md)允许不可得 upstream identity 保持 unknown，旧补证中的强 upstream/region 方案属于提案。无论采用何种最低 TEXT profile，都不能隐式获得 Router/fallback/retry 或把 reported metadata当认证；gateway 与 upstream 数据控制也不合并。

## 官方入口索引

[MX]: OFFICIAL_MATRIX.md "既有官方矩阵"
[O1]: https://developers.openai.com/api/reference/python/resources/responses/methods/create "OpenAI Responses reference"
[O2]: https://developers.openai.com/api/docs/guides/structured-outputs "OpenAI structured outputs"
[O3]: https://developers.openai.com/api/docs/guides/reasoning "OpenAI reasoning"
[O4]: https://developers.openai.com/api/docs/guides/streaming-responses "OpenAI streaming"
[O5]: https://developers.openai.com/api/docs/guides/error-codes "OpenAI errors"
[AN1]: https://platform.claude.com/docs/en/api/overview "Anthropic overview"
[AN2]: https://platform.claude.com/docs/en/build-with-claude/extended-thinking "Anthropic thinking"
[AN3]: https://platform.claude.com/docs/en/api/http/messages "Anthropic Messages"
[AN4]: https://platform.claude.com/docs/en/build-with-claude/structured-outputs "Anthropic structured outputs"
[AN5]: https://platform.claude.com/docs/en/build-with-claude/streaming "Anthropic streaming"
[AN6]: https://platform.claude.com/docs/en/api/errors "Anthropic errors"
[G1]: https://ai.google.dev/api/generate-content "Google generateContent"
[G2]: https://ai.google.dev/gemini-api/docs/api-key "Google API keys"
[G3]: https://ai.google.dev/gemini-api/docs/models "Google models"
[G4]: https://ai.google.dev/gemini-api/docs/deprecations "Google deprecations"
[G5]: https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api "Gemma on Gemini API"
[G6]: https://ai.google.dev/gemini-api/docs/generate-content/function-calling "Google function calling"
[G7]: https://ai.google.dev/gemini-api/docs/generate-content/thought-signatures "Google thought signatures"
[G8]: https://ai.google.dev/gemini-api/docs/generate-content/structured-output "Google structured output"
[G9]: https://ai.google.dev/gemini-api/docs/generate-content/thinking "Google thinking"
[G10]: https://ai.google.dev/gemini-api/docs/troubleshooting "Google troubleshooting"
[DS1]: https://api-docs.deepseek.com/api/create-response/ "DeepSeek Responses reference"
[DS2]: https://api-docs.deepseek.com/guides/responses_api/ "DeepSeek Responses guide"
[DS3]: https://api-docs.deepseek.com/api/create-chat-completion/ "DeepSeek Chat reference"
[DS4]: https://api-docs.deepseek.com/quick_start/pricing "DeepSeek pricing"
[DS5]: https://api-docs.deepseek.com/guides/tool_calls/ "DeepSeek Tool calls"
[DS6]: https://api-docs.deepseek.com/guides/json_mode/ "DeepSeek JSON output"
[DS7]: https://api-docs.deepseek.com/guides/thinking_mode/ "DeepSeek thinking"
[DS8]: https://api-docs.deepseek.com/quick_start/rate_limit/ "DeepSeek rate/isolation"
[DS9]: https://api-docs.deepseek.com/quick_start/error_codes/ "DeepSeek errors"
[Q1]: https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope "Qwen Chat"
[Q2]: https://www.alibabacloud.com/help/en/model-studio/compatibility-with-openai-responses-api "Qwen Responses"
[Q3]: https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output "Qwen structured output"
[Q4]: https://www.alibabacloud.com/help/en/model-studio/qwen-function-calling "Qwen function calling"
[Q5]: https://www.alibabacloud.com/help/en/model-studio/deep-thinking "Qwen thinking"
[Q6]: https://www.alibabacloud.com/help/en/model-studio/stream "Qwen stream"
[Q7]: https://www.alibabacloud.com/help/en/model-studio/error-code "Qwen errors"
[Z1]: https://docs.z.ai/api-reference/llm/chat-completion "Z.AI Chat"
[Z2]: https://docs.bigmodel.cn/cn/guide/develop/responses/introduction "智谱中国 Responses"
[Z3]: https://docs.bigmodel.cn/cn/guide/develop/claude/introduction "智谱中国 Claude-compatible"
[Z4]: https://docs.z.ai/guides/capabilities/thinking-mode "Z.AI thinking"
[Z5]: https://docs.z.ai/guides/capabilities/struct-output "Z.AI JSON object"
[Z6]: https://docs.z.ai/guides/capabilities/streaming "Z.AI stream"
[Z7]: https://docs.z.ai/api-reference/api-code "Z.AI errors"
[Z8]: https://docs.bigmodel.cn/cn/api/api-code "智谱中国 errors"
[K1]: https://platform.kimi.ai/docs/api/chat "Kimi Chat"
[K2]: https://platform.kimi.ai/docs/api/responses "Kimi Responses"
[K3]: https://platform.kimi.ai/docs/api/messages "Kimi Messages"
[K4]: https://platform.kimi.ai/docs/api/models-overview "Kimi models overview"
[K5]: https://platform.kimi.ai/docs/guide/use-thinking-models "Kimi thinking"
[K6]: https://platform.kimi.ai/docs/guide/use-kimi-api-to-complete-tool-calls "Kimi Tool calls"
[K7]: https://platform.kimi.ai/docs/guide/response_format "Kimi response format"
[K8]: https://platform.kimi.ai/docs/guide/utilize-the-streaming-output-feature-of-kimi-api "Kimi stream"
[K9]: https://platform.kimi.ai/docs/api/errors "Kimi errors"
[M1]: https://platform.minimax.io/docs/api-reference/responses-create "MiniMax Responses"
[M2]: https://platform.minimax.io/docs/api-reference/text-openai-api "MiniMax Chat"
[M3]: https://platform.minimax.io/docs/api-reference/text-anthropic-api "MiniMax Anthropic-compatible"
[M4]: https://platform.minimax.io/docs/guides/text-m3-function-call "MiniMax function calling"
[M5]: https://platform.minimax.io/docs/api-reference/errorcode "MiniMax errors"
[SF1]: https://docs.siliconflow.cn/docs/api/chat-completions-post "SiliconFlow Chat"
[SF2]: https://docs.siliconflow.cn/docs/api/chat-completions-post "SiliconFlow已冻结API资料入口"
[SF3]: https://docs.siliconflow.cn/docs/userguide/capabilities/stream-mode "SiliconFlow stream"
[SF4]: https://docs.siliconflow.cn/docs/userguide/guides/json-mode "SiliconFlow JSON mode"
[SF5]: https://docs.siliconflow.cn/docs/userguide/capabilities/reasoning "SiliconFlow reasoning"
[SF6]: https://siliconflow.cn/pricing "SiliconFlow pricing"
[A1]: https://docs.volcengine.com/docs/ark/base-url-and-authentication?lang=en "Ark auth"
[A2]: https://docs.byteplus.com/en/docs/modelark/chat-api?redirect=1 "BytePlus Chat"
[A3]: https://docs.byteplus.com/en/docs/modelark/deep-thinking?redirect=1 "BytePlus thinking"
[A4]: https://docs.byteplus.com/en/docs/modelark/function-calling?redirect=1 "BytePlus function calling"
[A5]: https://docs.byteplus.com/en/docs/modelark/structured-output?redirect=1 "BytePlus structured output"
[OR1]: https://openrouter.ai/docs/api_reference/overview "OpenRouter API"
[OR2]: https://openrouter.ai/docs/guides/routing/provider-selection "OpenRouter routing"
[OR3]: https://openrouter.ai/docs/guides/features/router-metadata "OpenRouter metadata"
[OR4]: https://openrouter.ai/docs/guides/privacy/provider-logging "OpenRouter provider logging"
[OR5]: https://openrouter.ai/openai/gpt-5.2 "OpenRouter gpt-5.2"
[OR6]: https://openrouter.ai/docs/guides/features/structured-outputs "OpenRouter structured output"
[OR7]: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens "OpenRouter reasoning"
[OR8]: https://openrouter.ai/docs/api_reference/streaming "OpenRouter stream"
[OR9]: https://openrouter.ai/docs/api_reference/errors-and-debugging "OpenRouter errors"
[OR10]: https://openrouter.ai/docs/guides/privacy/data-collection "OpenRouter data collection"
[OR11]: https://openrouter.ai/docs/guides/features/zdr "OpenRouter ZDR"
