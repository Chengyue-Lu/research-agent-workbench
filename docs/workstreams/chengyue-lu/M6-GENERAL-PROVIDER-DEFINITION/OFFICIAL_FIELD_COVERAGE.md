# 官方字段覆盖与待核清单

本表按 [M6-009 计划](PLAN.md) 补核2026-10-02 UTC（北京时间2026-10-03）的官方公开文档/政策正文，保留此前已冻结摘要。十一家公共服务/网关与Azure/Vertex/Bedrock边界分列。本轮使用web与无认证document GET，没有调用模型API、账户端点或读取Key/环境凭据。

D表示官方正文给出该行限定范围内的明确事实；P表示有事实但仍有列明的exact条件；U表示本轮未取得该字段的正文事实，不表示官方无资料/服务不支持。每行保留官方来源或待核入口；HTTP200、URL和hash不等于字段已核。所有新增事实observed/retrieved date为2026-10-02 UTC，明确政策更新日另列。服务器Date/Last-Modified与搜索cache时间不充当发布日期。

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

11 × 15 = **165 项已登记**：D 31，P 129，U 5。原为D17/P75/U73，本轮补强115行。目前160项有保留事实、129项仍有待核、5项无正文事实；不是能力通过、live验证或M6-009完成率。

| 服务 | D | P | U |
|---|---:|---:|---:|
| OpenAI | 4 | 11 | 0 |
| Anthropic | 3 | 12 | 0 |
| Google Gemini Developer API（含独立 Gemma 文档事实） | 4 | 10 | 1 |
| DeepSeek | 6 | 9 | 0 |
| Alibaba Qwen / DashScope | 2 | 13 | 0 |
| Zhipu GLM / Z.AI / 智谱 | 3 | 11 | 1 |
| Moonshot / Kimi | 2 | 12 | 1 |
| MiniMax | 1 | 14 | 0 |
| SiliconFlow | 2 | 12 | 1 |
| ByteDance / Ark / BytePlus | 2 | 13 | 0 |
| OpenRouter | 2 | 12 | 1 |

## OpenAI

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Responses 与 Chat 是分别定义的 API surface。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [O1][O1] |
| F02 认证 | D | Bearer 认证；surface 与 model snapshot 分别固定。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [MX][MX] |
| F03 访问区域 / 部署区域 | P | 官方your-data区分符合资格project的data residency与处理区域；system/schema等数据不受全部地域保证。 | actual project资格/区域未知，不由hostname猜部署。 | [O7][O7] |
| F04 model alias / revision | P | model card当前列gpt-4o-mini与gpt-4o-mini-2024-07-18，上下文128000、最大输出16384。 | 文档型号不证明actual serving/revision或账户权限；新模型不替旧snapshot。 | [O10][O10]、[O2][O2] |
| F05 角色 | P | Responses reference明确developer/system优先于user；function_call_output为独立item。 | 完整Chat角色转换和所选snapshot限制待核，不把Tool item当普通role。 | [O1][O1]、[O6][O6] |
| F06 ToolChoice | P | 指南列auto/required/none/指定function；strict要求对象additionalProperties=false且属性全部required。 | 所选snapshot/Tool/strict组合另验。 | [O6][O6]、[O2][O2] |
| F07 Tool 往返 | D | Responses返回function_call；回传function_call_output用相同call_id，前轮output可追加至后轮input。 | 原厂文档契约不授予别厂商状态存储或Session接受。 | [O6][O6] |
| F08 并行 Tool | D | parallel_tool_calls=false使一次返回零或一个函数call，built-in Tool另有约束。 | actual所选model/Tool组合另验。 | [O6][O6] |
| F09 Schema / JSON | P | JSON Schema/strict 依模型与 Schema 子集，指南明确该 snapshot。 | 所选 Schema keyword 子集和服务器 enforcement 不能由本地 JSON 校验代替。 | [O2][O2]、V1 |
| F10 thinking / context 续传 | P | reasoning continuation 是独立语义。 | 所选非 reasoning snapshot 是否返回专有项、后续模型的续传必须分别核验。 | [MX][MX]、[O3][O3] |
| F11 stream / cancellation | P | Responses 与 Chat 的 stream 不能混 parse。 | 所选 surface 的事件、取消后 usage/charge 与终态仍待逐字段冻结。 | [MX][MX]、[O4][O4] |
| F12 usage / cache / reasoning | P | Responses usage有input/output/total；input细分cached/cache_write，output细分reasoning；示例total=input+output。 | 缺失/失败/取消不填零，子项不能再次加到total。 | [O1][O1] |
| F13 error / retry / rate | P | rate按org/project/model管理RPM/RPD/TPM等；429包含rate及quota/credit不足，500/503为服务问题。 | actual tier/shared limits未知；官方退避建议不授权本轮retry。 | [O8][O8]、[O5][O5] |
| F14 价格 / 时间窗 | P | GPT-4o-mini USD/1M input0.15、cached0.075、output0.60；Batch为独立模式。 | actual service tier/账单未核；本页不提供通用idle折扣。 | [O10][O10]、[O9][O9] |
| F15 账户数据控制 | P | API默认不训练（opt-in另定）；abuse日志通常最长30天，Responses state默认/store=true至少30天；ZDR须资格。 | actual project设置/地域及法律安全例外另核，不宣称全部数据零留存。 | [O7][O7] |

## Anthropic

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Messages；overview 固定 /v1/messages。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [AN1][AN1]、V1 |
| F02 认证 | D | direct API支持Authorization Bearer，x-api-key为仍支持的fallback；anthropic-version必填，多workspace Key须workspace header。 | 认证形状不证明actual权限，云服务IAM独立。 | [AN1][AN1] |
| F03 访问区域 / 部署区域 | P | direct API overview指向支持国家/地区；数据政策区分direct API与云服务。 | 账户访问与actual处理/部署地域未知，不继承Bedrock/Vertex。 | [AN1][AN1]、[AN11][AN11] |
| F04 model alias / revision | P | thinking 示例使用 claude-sonnet-4-6。 | 例子中的 ID 不认证当前权限、immutable revision 或 allowed observed alias。 | [AN2][AN2]、V1 |
| F05 角色 | D | Messages输入messages.role为user/assistant；system为顶层字段，不存在输入system role。 | 仅Messages文档形状，不复制Responses developer。 | [AN13][AN13] |
| F06 ToolChoice | P | 指南列auto/any/tool/none；手动extended thinking与any/tool强制选择不兼容。 | Sonnet4.6 exact mode/strict组合另验，新模型限制不反推旧型号。 | [AN7][AN7]、[AN12][AN12] |
| F07 Tool 往返 | P | assistant tool_use含id/name/input，user tool_result用tool_use_id；client执行后回传。 | 顺序/全部call配对/signature及exact模式仍待绑定；旧handle-tool-results抓取404已保留。 | [AN13][AN13]、[AN7][AN7] |
| F08 并行 Tool | P | disable_parallel_tool_use放在tool_choice内；auto时至多一call，any/tool时恰一call（模型允许该choice时）。 | Sonnet4.6 thinking/strict组合仍待核，不是顶层同名参数。 | [AN12][AN12] |
| F09 Schema / JSON | P | 文档有 output_config.format 与 strict Tool。 | 该 exact model 的 Schema 子集/enforcement 未由摘要闭合。 | [AN4][AN4]、[MX][MX] |
| F10 thinking / context 续传 | P | thinking/signature 有专有续传语义；示例包含 disabled-thinking 形状。 | 需要思考/签名的组合不能从 plain text 契约推导。 | [AN2][AN2]、[AN3][AN3]、V1 |
| F11 stream / cancellation | P | stream 有专有格式。 | 事件和取消后终态/计费须对所选 Messages 模式冻结。 | [AN5][AN5]、[MX][MX] |
| F12 usage / cache / reasoning | P | 全部input=input_tokens+cache_creation_input_tokens+cache_read_input_tokens；output独列；cache-read通常不计ITPM，有模型例外。 | 失败/取消及missing分项未知，不把input_tokens当全部input。 | [AN13][AN13]、[AN8][AN8] |
| F13 error / retry / rate | P | 按RPM/ITPM/OTPM及spend tier限额；error.type/message及request_id，413请求过大、429rate、529overloaded。 | actual org/workspace/model tier未知，SDK retry另由调用计划约束。 | [AN6][AN6]、[AN8][AN8] |
| F14 价格 / 时间窗 | P | Sonnet4.6 USD/1M input3/output15；cache 5m write3.75、1h6、read0.30；US inference_geo为1.1倍。 | actual region/tier/Batch未绑，Batch不是idle折扣。 | [AN9][AN9] |
| F15 账户数据控制 | P | 商业API通常30天内删除input/output，feature/合同/使用政策/法律例外另定；ZDR须org启用且功能合资格。 | actual ZDR/feature未知，flagged/feedback可更久，不推广全部新模型/云服务。 | [AN10][AN10]、[AN11][AN11] |

## Google Gemini Developer API（含独立 Gemma 文档事实）

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | generateContent / streamGenerateContent；native API 示例为 /v1beta/models/{model}:generateContent。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [G1][G1]、V1 |
| F02 认证 | D | API-key guide 支持 x-goog-api-key。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [G2][G2]、V1 |
| F03 访问区域 / 部署区域 | P | available-regions列美国、新加坡等；条款允许在Google/代理设施所在国处理。 | actual访问资格/处理位置未知，清单不等于可选Vertex location。 | [G15][G15]、[G13][G13] |
| F04 model alias / revision | P | 旧 gemini-2.0-flash 在后续 models/deprecations 明确已关闭；Gemma 官方页列 gemma-4-26b-a4b-it / gemma-4-31b-it。 | Gemma facts 仅 dated extracted view；新 alias/revision、当前账户权限与 observed ID 仍未认证。 | [G3][G3]、[G4][G4]、[G5][G5]、V2 |
| F05 角色 | D | generateContent Content.role仅user/model，systemInstruction是独立字段。 | native API形状不证明全部Gemma能力或其他surface映射。 | [G1][G1] |
| F06 ToolChoice | P | native FunctionCallingConfig有AUTO/ANY/NONE/VALIDATED，allowedFunctionNames仅ANY或VALIDATED时限制函数名。 | selected model支持及强制行为未验；Interactions的tool_choice不能代替该配置。 | [G16][G16]、[G14][G14] |
| F07 Tool 往返 | P | functionCall/Response 是 native 形状；Gemini3 Tool 签名须原样续传。 | Gemma text 示例不等于 Gemma Tool 往返已经验收。 | [G6][G6]、[G7][G7]、[MX][MX]、V2 |
| F08 并行 Tool | U | G6 native generateContent指南明确一轮可返回多个函数调用，dated支持表列十个Gemini型号的parallel能力；G16的NONE禁止全部函数，allowedFunctionNames限名称。 | 所选Gemma4并行支持、数量上限及允许一call但关闭并行的保证仍未取得；该型号未出现于这三份正文，不推断不支持。ANY/名称不限制数量，SDK automatic_function_calling.disable只关闭自动执行；G14 Interactions配置单独保留。 | [G6][G6]、[G16][G16]、[G14][G14]；R8 |
| F09 Schema / JSON | P | response Schema 为子集；2.5 Flash-Lite 在结构化输出表，Gemini3 mixed feature 是另列 preview。 | JSON 模式、所选模型 keyword/enforcement 与混合 Tool 支持须分开。 | [G8][G8]、V2 |
| F10 thinking / context 续传 | P | Gemma4 特有 minimal=off；Gemini3 minimal 不能当 off；2.5 Flash-Lite 可 thinkingBudget=0。 | Gemma/各 Gemini 思考与 thoughtSignature 续传分别核；账户及返回内容未实测。 | [G5][G5]、[G7][G7]、[G9][G9]、V2 |
| F11 stream / cancellation | P | native streamGenerateContent 独立于 OpenAI stream。 | 所选模型事件、取消后终态/用量仍待冻结。 | [G1][G1]、[MX][MX] |
| F12 usage / cache / reasoning | D | usageMetadata区分prompt/cachedContent/candidates/thoughts/toolUsePrompt，totalTokenCount=prompt+thoughts+candidates。 | missing保留unknown，不能假设thoughts已含在candidates，缓存不重复加总。 | [G1][G1] |
| F13 error / retry / rate | P | 限额按project而非Key，RPM/TPM/RPD依tier/model；troubleshooting区分429资源耗尽与400/403/5xx。 | actual tier/动态limit未查，取消/失败charge/retry契约待核。 | [G12][G12]、[G10][G10] |
| F14 价格 / 时间窗 | P | Gemma4 pricing：free-tier input/output/cache/storage免费，paid-tier不可用；其他Gemini按型号/tier另价。 | 免费仍受rate/账户条件，产品改进规则须结合条款和actual billing，免费不等于不训练。 | [G11][G11]、[G13][G13] |
| F15 账户数据控制 | P | active Cloud Billing project的Paid Services不用prompts/responses改善产品；unpaid通常可改善，EEA/CH/UK另定，安全日志例外。 | actual billing/地域未查，安全日志固定天数未取得，不推广Vertex。 | [G13][G13] |

## DeepSeek

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Responses、Chat 与 Anthropic-compatible 分别有入口；Responses reference 与 guide 独立。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [DS1][DS1]、[DS2][DS2]、[DS3][DS3]、[MX][MX] |
| F02 认证 | D | Bearer 认证。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [MX][MX]、[DS4][DS4] |
| F03 访问区域 / 部署区域 | P | privacy policy说明所收集信息存于中华人民共和国境内。 | 政策存储事实不认证推理部署；客户下游终端用户数据不受该一般政策全部覆盖。 | [DS11][DS11] |
| F04 model alias / revision | P | pricing将deepseek-flash映射DeepSeek-V4.1-Flash；models reference例子context_window=1048576、max_output_tokens=393216。 | alias可变；只读metadata文档，未调用models endpoint，actual身份/权限未认证。 | [DS4][DS4]、[DS10][DS10] |
| F05 角色 | D | Responses支持system/developer/user/assistant；developer按user处理，instructions为首system，function_call/output为独立item。 | 只限DeepSeek Responses，不冒充原厂developer权威。 | [DS1][DS1]、[DS2][DS2] |
| F06 ToolChoice | D | Responses原生tool_choice为none/auto（默认）/required/指定{name,type:function}；Tool原生name/parameters。 | 文档支持不是Flash非思考Tool live接受；Chat strict另有边界。 | [DS1][DS1]、[DS2][DS2] |
| F07 Tool 往返 | P | Responses每轮传完整input；call_id须非空且唯一、每call须配对应function_call_output；previous_response_id/conversation/store/background不支持；响应store固定false。 | Session本地history/所有ID配对/终态另验；store=false不等于日志或缓存零留存。 | [DS1][DS1]、[DS2][DS2]；R9 |
| F08 并行 Tool | D | Responses忽略parallel_tool_calls与max_tool_calls，始终并行，两个参数不能保证单call。 | 本地有界执行/返回拒绝规则由实现计划约束；named choice也不自动单call。 | [DS2][DS2] |
| F09 Schema / JSON | P | Responses text.format有text/json_object/json_schema(name/schema)；Chat Beta strict Tool子集含enum及required/additionalProperties规则。 | 未取得Responses独立strict/keyword表，Chat enum不是Responses enforcement证据；截断JSON须拒绝。 | [DS1][DS1]、[DS2][DS2]、[DS5][DS5]、[DS6][DS6] |
| F10 thinking / context 续传 | D | 所选deepseek-responses-nonthinking-v1为deepseek-flash+reasoning.effort=none；此原生值关思考（默认high）；max_output_tokens含reasoning。 | 这是所选profile/文档关系非live接受；Chat thinking.disabled是另surface，其他型号不继承。 | [DS1][DS1]、[DS2][DS2]、[DS7][DS7] |
| F11 stream / cancellation | P | Responses语义SSE以response.completed/incomplete/failed终止，无[DONE]；完成event携完整response/usage。 | 取消/断连/失败最终usage/charge未知；首轮非stream不偷换contract。 | [DS1][DS1]、[DS2][DS2] |
| F12 usage / cache / reasoning | P | Responses input+output=total，cached为input子项、reasoning为output子项；incomplete原因max_output_tokens/content_filter，message可incomplete。 | 失败missing不填零；保留停止状态和已收用量，未完成Tool拒绝；子项不重复加总。 | [DS1][DS1]、[DS2][DS2]、[DS4][DS4] |
| F13 error / retry / rate | P | Flash account并发2500（全部Keys合计），user_id用于KV/scheduling/content-safety隔离；错误400/401/402/422/429/500/503分列。 | 并发不是RPM/TPM或用户预算，账户可用/余额未知；不授权自动retry/fallback。 | [DS8][DS8]、[DS9][DS9] |
| F14 价格 / 时间窗 | P | USD/1M Flash闲时hit0.003/miss0.15/output0.60，峰时两倍；峰UTC工作日01–04/06–10排除中国公共假日，其余闲时。 | 执行前重核日期/假日与北京时间18:00后；文档价格非actual账单或消费目标。 | [DS4][DS4] |
| F15 账户数据控制 | P | 既有2026-02-10 privacy描述输入收集、改进/训练目的和opt-out；2026-04-29生效的Open Platform Terms适用于API/developer tools，开发者个人信息引用Privacy，开发者承担下游用户隐私披露；涉嫌违规相关记录可保留。Responses store固定false；prompt_cache_key/retention不支持，缓存自动管理。 | 这三页未证明API no-training/ZDR、固定日志/cache期限或actual账户开关；一般privacy不能充作全部下游API数据契约，stateless不推出零留存，不一概新增合成测试gate。 | [DS11][DS11]、[DS12][DS12]、[DS1][DS1]、[DS2][DS2]；R9 |

## Alibaba Qwen / DashScope

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Chat + Responses compatible-mode；Chat reference 固定 Virginia access origin。Responses新path为/compatible-mode/v1/responses，旧/api/v2/apps/protocols不再维护。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [Q1][Q1]、[Q2][Q2]、V1；R7:qwen-responses-cache |
| F02 认证 | D | compatible-mode Chat与Responses Curl使用Authorization Bearer DashScope Key；地区Key不同且workspace须匹配endpoint。 | surface认证形状不授予actual账户权限；兼容协议不改变Qwen身份。 | [Q1][Q1]、[Q2][Q2]；R7:qwen-responses-cache |
| F03 访问区域 / 部署区域 | P | Chat新文档endpoint含WorkspaceId，列北京cn-beijing/新加坡ap-southeast-1/香港cn-hongkong等maas地区hostname。qwen3.8-max显式/隐式cache各列六区：Singapore International、北京、香港/法兰克福/弗吉尼亚/东京Global。 | Cache清单北京未标scope；access不认证推理/处理地域，其他型号scope不借用，actual账户待绑。 | [Q1][Q1]、[Q9][Q9]、[Q11][Q11]；R7:qwen-responses-cache |
| F04 model alias / revision | P | Chat示例与价格页独立列qwen3.8-max，价格页另列qwen3.8-max-0902；结构化指南列Qwen3.8-Max。 | 同价不证明alias与-0902等价；observed ID/revision和账户权限另验。 | [Q1][Q1]、[Q3][Q3]、[Q9][Q9]、V1；R6:qwen-selected |
| F05 角色 | P | Chat普通参数表列system/user/assistant，system仅messages[0]，通常user/assistant交替且末条user；Tool例子使用tool和tool_call_id。Responses input可为string/数组，所选迁移例子用system/user、输出assistant；cache marker可放system/user/assistant/tool。 | marker位置不是完整Responses角色白名单；developer、exact Tool角色/顺序与普通表范围仍待核，不推断禁用。 | [Q1][Q1]、[Q4][Q4]、[Q2][Q2]、[Q11][Q11]；R6、R7 |
| F06 ToolChoice | P | qwen3.8-max非思考示例列auto/none/指定function；指南明确Qwen非思考required不能保证调用，思考模式不支持required。 | required代码示例为托管kimi/kimi-k3，不能借给Qwen；strict及其他exact型号表仍待核，指定函数不保证单call。 | [Q4][Q4]、[MX][MX] R5:qwen-tool-choice |
| F07 Tool 往返 | P | Tool循环追加assistant输出，再以同tool_call.id写role=tool.tool_call_id并回传原始结果。 | 多call配对、停止/失败与所选Session边界另核。 | [Q4][Q4] |
| F08 并行 Tool | P | qwen3.8-max+enable_thinking=false示例parallel_tool_calls=true允许无依赖Tool并行；有依赖用串行loop。 | false服务器保证与数量上限未核，不能从true例子推导。 | [Q4][Q4] |
| F09 Schema / JSON | P | json_object/json_schema支持集合不同；Schema列string/number/integer/boolean/object/array/enum，strict例子容许optional字段。 | exact region/model keyword/enforcement另绑，不复制OpenAI全属性required规则。 | [Q3][Q3] |
| F10 thinking / context 续传 | P | Chat qwen3.8-max Tool示例发送enable_thinking=false。Responses reasoning.effort优先于enable_thinking，所选示例medium、不支持thinking_budget；previous_response_id为顶层ID，公开有效7日，续轮input计入前轮上下文。 | Responses所选非思考控制/effort值与默认仍待核；Chat off不推广，ID有效期不是总体留存承诺。 | [Q4][Q4]、[Q5][Q5]、[Q2][Q2]、V1；R7:qwen-responses-cache |
| F11 stream / cancellation | P | Chat include_usage=true最后chunk给usage且choices=[]，此前文本delta累积。 | exact取消/断连/结束与charge未知；最后空choices不索引文本。 | [Q1][Q1]、[Q6][Q6] |
| F12 usage / cache / reasoning | P | Chat prompt+completion=total；显式cache示例uncached=prompt−creation−read，隐式cached为prompt子集。Anthropic兼容隐式cache_read_input_tokens不含于input_tokens。Responses样例列input/output/total及cached/reasoning细分；selected计费output包含思考与答案。 | 按surface处理，不跨协议套算法；Responses嵌套字段/零样例未闭合完整子集、exact mode与失败/截断契约，missing不填0，价格口径不补成usage契约。 | [Q1][Q1]、[Q9][Q9]、[Q11][Q11]、[Q2][Q2]；R6、R7 |
| F13 error / retry / rate | P | rate按model/region列RPM/TPM（input+output），秒级RPS/TPS可能按分钟限额/60。 | actual workspace/model quota未知；未调用quota API，错误/重试按surface另绑。 | [Q8][Q8]、[Q7][Q7] |
| F14 价格 / 时间窗 | P | qwen3.8-max两模式，input档0<Token≤1M；每百万tokens Singapore/International标准$2/$6，其他五区$1.65/$4.951。各行cache标签、北京Batch50%。显式cache增量creation为适用input标准价1.25倍；所选read价明确例外于通用显式10%/隐式20%，精确值只指console。 | Cache页已取得，精确read价为console-only unknown，不套默认比例。selected夜价仍未证；$不推断ISO币种，actual region/account/优惠/账单另核。input计费档不是context/output上限。 | [Q9][Q9]、[Q11][Q11]；R6、R7 |
| F15 账户数据控制 | P | FAQ承诺不使用客户数据训练、传输/存储加密。Cache按账户/模型隔离；显式5分钟且hit重置，隐式无固定期限。Responses x-dashscope-session-cache默认disable；enable优先支持的显式、否则隐式，disable仍可能自动隐式。 | Cache生命周期/Session header不证明整体留存、ZDR或no-training；actual region/workspace/跨境/例外另核，不能套Chat cache_control wire。 | [Q10][Q10]、[Q11][Q11]、[Q2][Q2]；R7:qwen-responses-cache |

## Zhipu GLM / Z.AI / 智谱

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | 国际 Chat /api/paas/v4；中国 Responses /api/v1、Claude-compatible /api/anthropic 独列。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [Z1][Z1]、[Z2][Z2]、[Z3][Z3]、[MX][MX] |
| F02 认证 | D | Z.AI国际Chat为Authorization Bearer；中国BigModel/Coding Plan认证独立。 | actual套餐/权限未验，不互换国际/中国Key。 | [Z1][Z1] |
| F03 访问区域 / 部署区域 | P | 国际API DPA说Customer Data通常在新加坡；中国BigModel服务边界另列。 | 通常存储不认证exact推理deployment，所选地区/中国数据位置未知。 | [Z11][Z11]、[Z2][Z2] |
| F04 model alias / revision | P | 国际 enum 列 glm-5.2；thinking 文档排除强制思考 GLM-5.3/5.3-FLASH。 | revision/alias 当前解析和账户可用未观测。 | [Z1][Z1]、[Z4][Z4]、V1 |
| F05 角色 | D | 国际Chat明确system/user/assistant/tool四种messages；输入不能只有system或assistant。 | 仅国际Chat，不借中国Claude-compatible。 | [Z1][Z1] |
| F06 ToolChoice | P | 国际Chat reference tool_choice enum只列auto，函数Tool输出另列。 | none/required/specific/strict未补证，glm-5.2 off远端组合仍未验。 | [Z1][Z1] |
| F07 Tool 往返 | P | response tool_calls含id/type/function.name/arguments，tool为独立输入类。 | exact完整往返配对/错误终态未提取，保留部分事实。 | [Z1][Z1] |
| F08 并行 Tool | U | 未取得glm-5.2 off并行控制/数量的官方正文保证。 | Z1有Tool schema/auto选择，未提取parallel字段不表示不支持；须所选型号补证，不借中国surface。 | [Z1][Z1]、[Z4][Z4] |
| F09 Schema / JSON | P | 已读 Z.AI JSON Object 不是 server Schema 保证。 | exact Schema/JSON dialect、keyword 与 enforcement 保持 unresolved。 | [Z5][Z5]、[MX][MX]、V1 |
| F10 thinking / context 续传 | P | GLM4.5+有thinking enabled/disabled，5.3/Flash只enabled；clear_thinking=true默认移旧reasoning，false需全量原样历史。 | glm-5.2 exact off/preserved实测独立，新5.3限制不替旧profile。 | [Z1][Z1]、[Z4][Z4] |
| F11 stream / cancellation | P | 国际Chat stream=true为Event Stream，终止data:[DONE]；false/省略为同步。 | 取消usage/charge、error event与selected型号终态待核。 | [Z1][Z1]、[Z6][Z6] |
| F12 usage / cache / reasoning | P | 国际reference列prompt/completion/total_tokens与prompt_tokens_details.cached_tokens。 | reasoning是否含completion、失败/缺失关系unknown，不复制别服务算法。 | [Z1][Z1] |
| F13 error / retry / rate | P | 国际错误页区分HTTP/business码；429可并发/套餐限额/产品Key类型错误，不能全当短暂rate。 | actual model/account限额数字/retry hint未取得，中国码不混用。 | [Z7][Z7]、[Z8][Z8] |
| F14 价格 / 时间窗 | P | Z.AI GLM5.2 USD/1M input1.40/cache0.26/output4.40，cache storage标limited-time free；4.7/Flash另价。 | free结束日期、actual套餐/账单/idle价未核，国际价不复制中国。 | [Z9][Z9] |
| F15 账户数据控制 | P | 2026-04-14 API terms默认不以developer内容改善模型（明确同意另定）；API DPA说实时API内容不存储，其他数据按期限/例外处理。 | consumer privacy排除API customer，actual合同/地域/例外未知，不宣称全部元数据零留存。 | [Z10][Z10]、[Z11][Z11] |

## Moonshot / Kimi

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Chat /api.moonshot.ai/v1/chat/completions；另列 Responses 与 Messages；文档迁至 platform.kimi.ai。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [K1][K1]、[K2][K2]、[K3][K3]、[MX][MX]、V1 |
| F02 认证 | D | 国际Chat api.moonshot.ai/v1为Authorization Bearer；K2.6例子一致。 | actual账户/中国区/其他surface权限另核。 | [K1][K1] |
| F03 访问区域 / 部署区域 | P | 国际privacy说明所收集个人信息安全存储在新加坡。 | 不是model deployment或全部API业务数据地域保证，不推广中国Moonshot。 | [K12][K12] |
| F04 model alias / revision | P | model overview 用 kimi-k2.6 且列专有参数约束。 | k3/k2.7-code 等不是同一 profile；alias/revision/observed identity 未认证。 | [K4][K4]、V1 |
| F05 角色 | P | K2.6 Chat多轮含system/user/assistant；Tool结果为role=tool并带tool_call_id。 | 完整白名单/降级与preserved reasoning历史按型号绑定。 | [K1][K1]、[K6][K6] |
| F06 ToolChoice | P | 参数表明确K2.6/K2.7-code不支持required且报错；K3支持auto/none/required。 | 通用Chat指定function对象不证明K2.6 specific，不能借新K3补旧profile。 | [K4][K4]、[K1][K1] |
| F07 Tool 往返 | P | Chat stateless，后轮追加完整assistant/Tool结果，tool_call_id关联调用ID。 | thinking须含reasoning原样续传，selected off Session配对/终态/上限另验。 | [K1][K1]、[K4][K4]、[K6][K6] |
| F08 并行 Tool | U | 未取得kimi-k2.6 off并行控制与返回数量官方保证。 | K1/K4同时含K3/K2.x，不借K3行为给K2.6；K6配对ID不证明parallel。 | [K1][K1]、[K4][K4]、[K6][K6] |
| F09 Schema / JSON | P | 格式/Schema 稳定性随 k3/k2.7-code/k2.6 不同。 | 该 profile 的复杂 Schema/enforcement 未冻结。 | [K7][K7]、[MX][MX] |
| F10 thinking / context 续传 | P | kimi-k2.6 overview 接受 thinking.disabled；参数 override 有限制。 | preserved reasoning/context 续传须独立 contract，不能由 disabled 推导。 | [K4][K4]、[K5][K5]、V1 |
| F11 stream / cancellation | P | Chat SSE；include_usage=true最后chunk给完整cache breakdown，finish_reason非null停止。 | 取消/失败usage/charge未知，中间无usage不当0。 | [K1][K1]、[K8][K8] |
| F12 usage / cache / reasoning | P | prompt_tokens是全部input；cached/cache_write/uncached互斥且和为prompt；org隔离cache默认5m可1h、不支持手清。 | reasoning/output与失败计数另核；KV cache不是服务器历史留存承诺。 | [K1][K1] |
| F13 error / retry / rate | P | limits按累计付费tier列concurrency/RPM/TPM/TPD；errors区分长度/auth/rate/服务问题。 | actual tier/model限额未查，不授权自动retry。 | [K11][K11]、[K9][K9] |
| F14 价格 / 时间窗 | P | 国际K2.6 USD/1M input0.95/output4/cache hit0.16；K3与缓存write TTL另价。 | actual region/套餐/cache写价/时间折扣未绑，新K3不替K2.6。 | [K10][K10] |
| F15 账户数据控制 | P | 国际Model Use允许Customer Content训练/改善，书面enterprise协议可另定；privacy留存按必要期限。 | stateless不等于不训练/零留存；actual企业合同/期限未知。 | [K13][K13]、[K12][K12] |

## MiniMax

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | Chat、Responses、Anthropic-compatible 独列；Responses 为 /v1/responses。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [M1][M1]、[M2][M2]、[M3][M3]、[MX][MX]、V1 |
| F02 认证 | P | Bearer API Key；订阅/PAYG entitlement 分开。 | 实际所选账户权限和版本适用性未验证。 | [M1][M1]、V1 |
| F03 访问区域 / 部署区域 | P | 2026-03-30国际privacy说个人数据存于美国data center。 | 不是全部API推理deployment或中国账户事实，actual处理地域未知。 | [M8][M8] |
| F04 model alias / revision | P | 所选文档 exact MiniMax-M3；M3.1-Flash-Preview 与 M2.x 另列。 | alias/revision 与远端 observed identity/账户可用仍未认证。 | [M1][M1]、V1 |
| F05 角色 | P | Responses requestBody的input可string/history array；item分message/function_call/function_call_output/reasoning；message.role枚举user/assistant/system/developer/tool，instructions为独立string。 | 枚举不证明优先级/降级、全部M3 off往返或signature语义；不由Anthropic-compatible反推。 | [M1][M1]、[MX][MX] R5:minimax-input-roles |
| F06 ToolChoice | P | MiniMax-M3 文档支持的 ToolChoice 为 none/auto。 | required/specific 未形成支持依据，不能默认启用。 | [M1][M1]、V1 |
| F07 Tool 往返 | P | function calling guide 和思考 Tool 块存在专有语义。 | 完整 exact M3 off 的 call/result/signature 往返仍待逐字段核验。 | [M4][M4]、[MX][MX] |
| F08 并行 Tool | P | Responses response有parallel_tool_calls boolean、例子true；函数guide允许多个Tool。 | M3请求控制/并行数量enforcement未知，不由响应字段推保证。 | [M1][M1]、[M4][M4] |
| F09 Schema / JSON | P | strict Schema 保证未确认。 | 补所选 model/surface 的 JSON/Schema keyword 与 enforcement。 | [M1][M1]、[MX][MX] |
| F10 thinking / context 续传 | P | M3 默认无非none effort时思考off；M3.1-Flash-Preview none报400；M2.x不能由none保证off。 | 思考 Tool 块续传独立，不把其他M系继承为同一off profile。 | [M1][M1]、V1、[MX][MX] |
| F11 stream / cancellation | P | Responses stream=true启用SSE，status有completed/incomplete/failed与error/incomplete_details。 | 事件序列/取消/断连usage/charge待核，Messages stream不能代替。 | [M1][M1] |
| F12 usage / cache / reasoning | P | Responses例子input/output/total，cache为input子项、reasoning为output子项；max_output_tokens含reasoning，过小可incomplete且无message。 | 例子不证明每个M3分项；missing/failed不填0，子项不重复相加。 | [M1][M1] |
| F13 error / retry / rate | P | native码1001timeout/1002rate/1004auth/1008balance/1024internal；rate按model/interface列RPM/TPM。 | compatible错误形状不照抄native；actual M3 tier/failed charge未验。 | [M5][M5]、[M6][M6] |
| F14 价格 / 时间窗 | P | PAYG M3 standard≤512k input USD/1M input0.30/output1.20/cache read0.06，>512k两倍；priority为1.5倍。 | actual tier/账单未核，PAYG Key与Token Plan订阅Key/credits不同，不是闲时价。 | [M7][M7]、[M9][M9] |
| F15 账户数据控制 | P | privacy按必要目的/法律期限留存个人数据并支持撤回/删除；paid terms区分PAYG与订阅Key。 | 未取得覆盖全部selected API prompt的no-training/固定期限；actual合同未知。 | [M8][M8]、[M9][M9] |

## SiliconFlow

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | China hosted Chat：POST https://api.siliconflow.cn/v1/chat/completions。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [SF1][SF1]、[SF2][SF2] |
| F02 认证 | D | Bearer API Key；operator 为 SiliconFlow，publisher/model 全名另列。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [SF1][SF1]、[SF2][SF2] |
| F03 访问区域 / 部署区域 | P | 已冻结 China access endpoint；国际站不能给中国账户授权。 | 真实 deployment/processing region、账户权限未观测。 | [SF1][SF1]、[SF2][SF2]、V2 |
| F04 model alias / revision | P | 当前pricing SSR目录列Qwen/Qwen2.5-72B-Instruct及contextLen32768；API DeepSeekV4例子独立。 | 当前目录不认证actual serving/weight revision，operator不是DashScope。 | [SF6][SF6]、[SF1][SF1]、[SF3][SF3] |
| F05 角色 | P | China Chat例子含system/user/assistant，tools例子仍为hosted DeepSeekV4。 | exact Qwen tool/developer/角色白名单未取得，不跨hosted型号推广。 | [SF1][SF1] |
| F06 ToolChoice | P | China API例子tool_choice=auto、function tools及enum参数例子。 | exact Qwen none/required/specific/strict未取得，例子非全型号保证。 | [SF1][SF1] |
| F07 Tool 往返 | P | API 有该 hosted DeepSeek 的 Tool 示例。 | exact Qwen/所选模型mode 的 call/result 往返未闭合。 | [SF1][SF1]、[SF2][SF2]、V2 |
| F08 并行 Tool | U | 未取得hosted Qwen/Qwen2.5-72B-Instruct的parallel控制/数量正文事实。 | SF1通用tools及其他型号例子不证明该Qwen，需operator/model补证；不继承DashScope。 | [SF1][SF1]、[SF6][SF6] |
| F09 Schema / JSON | P | API 列 json_object/json_schema；JSON guide 示例实际为 json_object。 | 标题/总表不证明 exact 模型 strict Schema/enforcement。 | [SF1][SF1]、[SF4][SF4]、[SF2][SF2]、V2 |
| F10 thinking / context 续传 | P | enable_thinking 泛称多数推理模型；effort 对 V4-Flash 举high/max。 | 没有 exact V4/Qwen false=off 映射；standard text 不能宣称默认off，continuation另验。 | [SF1][SF1]、[SF5][SF5]、[SF2][SF2]、V2 |
| F11 stream / cancellation | P | stream 示例分 reasoning_content/content 及 [DONE]。 | 所选 model nonstream/stream差异、取消后 usage/charge未冻结。 | [SF3][SF3]、[SF2][SF2] |
| F12 usage / cache / reasoning | P | API 示例 prompt/completion/total、reasoning/cache tokens；max_tokens不包含 reasoning。 | 样例不能证明 exact Qwen/mode用量；total/reasoning预算关系与未知分项保持unresolved。 | [SF1][SF1]、[SF2][SF2] |
| F13 error / retry / rate | P | API列400/401/403/404/429/503/504；429例子TPM，503有business50505；旧error/index失败保留。 | selected账号RPM/TPM与完整retry未知，本地预算不是vendor quota。 | [SF1][SF1] |
| F14 价格 / 时间窗 | P | 当前SSR同一Qwen/Qwen2.5-72B-Instruct的prompt和completion价格均¥4.13/M tokens，关联model price references。 | 目录数值非actual账单；cache/idle/账户优惠未取得。 | [SF6][SF6] |
| F15 账户数据控制 | P | 2026-07-30 policy：API业务input/output仅推理短时处理、不长期存储/训练，结束销毁或不可恢复；记录IP/model/token/time/status和安全审查。 | 法律/特定产品/技术支持例外保留；metadata期限/actual合同未知，旧/privacy缓存非当前政策。 | [SF7][SF7] |

## ByteDance / Ark / BytePlus

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | BytePlus Chat实际HTML内MDContent明确api/v3/chat/completions，函数示例origin ark.ap-southeast.bytepluses.com。 | 此前JS/search局限本轮正文补强；Responses/中国Volcengine另绑。 | [A2][A2]、[A4][A4] |
| F02 认证 | P | BytePlus函数正文例子Bearer Key访问Singapore Chat；中国/Access-Key签名另列。 | 不推广全部签名Endpoint ID/中国账户/其他surface权限。 | [A2][A2]、[A4][A4]、[A1][A1] |
| F03 访问区域 / 部署区域 | P | BytePlus例子Singapore access；Data Processing正文列部署/处理可在Malaysia、Indonesia及EU/EEA，content-filter触发内容另存Malaysia。 | access/推理deployment/安全存储不同，actual region/策略未知，中国Ark不继承。 | [A4][A4]、[A8][A8] |
| F04 model alias / revision | P | 函数正文例子seed-2-0-lite-260228；Chat按该及后续version区分encrypted_content。beta Schema指南另用dola-seed-2-1-turbo-260628/off。 | 已捕获指南实际model-list外链，但为SPA shell，selected seed2lite/off能力表未提取；另一型号例子不证明支持，actual serving/immutable weights/权限另验。 | [A2][A2]、[A4][A4]、[A12][A12]、[A13][A13]；R6:byteplus-schema |
| F05 角色 | D | BytePlus Chat定义system/user/assistant/tool四类，tool须tool_call_id。 | 仅Chat正文形状，不复制为Responses developer。 | [A2][A2] |
| F06 ToolChoice | P | BytePlus Chat列none/auto/required/指定function；required一或多call，默认无tools为none、有tools为auto。 | exact seed2lite off/strict须模型表与远端另验。 | [A2][A2] |
| F07 Tool 往返 | P | tool结果须附模型生成的同一tool_call_id，client执行并回传。 | 全部call配对/错误终态/selected off Session边界待验，例子不授本地执行资格。 | [A2][A2]、[A4][A4] |
| F08 并行 Tool | P | parallel_tool_calls默认true；false限制至多一call，guide明确仅模型支持该控制时成立。 | selected seed2lite/模式控制与返回上限分别核验。 | [A2][A2]、[A4][A4] |
| F09 Schema / JSON | P | BytePlus Chat/beta指南区分json_schema/json_object；7种type及local # $ref、$defs/const/enum/anyOf/oneOf/allOf、array/object keyword表。oneOf/allOf精确语义不严格保证；strict默认false，additionalProperties=false配合required为建议，sampling组合有警告。 | 实际model-list外链返回SPA shell，selected seed2lite/off支持表未提取；JSON Object不保证custom Schema，输出截断/复杂度与具名unsupported清单/enforcement另核。原A5是shell，canonical A12取得正文；不推广Responses/中国Ark。 | [A2][A2]、[A5][A5]、[A12][A12]、[A13][A13]；R6:byteplus-schema |
| F10 thinking / context 续传 | P | Chat有thinking enabled/disabled/auto，支持/默认依模型；encrypted_content与reasoning_content续传不同。 | selected off及加密/明文历史独立，参数存在不证明全型号off。 | [A2][A2]、[A3][A3] |
| F11 stream / cancellation | P | Chat SSE以[DONE]终止；chunk_include_usage=true可给每chunk累计usage，另有最终usage选项。 | 累计值不能逐chunk相加，取消/断连final charge未知。 | [A2][A2] |
| F12 usage / cache / reasoning | P | usage total=input+output；prompt细分cached、completion细分reasoning；max_tokens管答案，max_completion_tokens管reasoning+答案。 | 缺失/失败/取消unknown，预算不重复加或忽略reasoning。 | [A2][A2] |
| F13 error / retry / rate | P | model activation按account/base model共用RPM/TPM，endpoint可另设限额；同base多个endpoint不增加quota。 | actual额度、完整错误/retry/failed charge待核。 | [A6][A6]、[A2][A2] |
| F14 价格 / 时间窗 | P | BytePlus standard seed-2-0-lite-260228 prompt≤128k USD/1M input0.25/cache0.05/output2，cache storage0.0083/M tokens/hour；更长tier另价。 | Flex/Batch另价，actual service tier/账单未知，不推广中国Ark/视频折扣。 | [A11][A11] |
| F15 账户数据控制 | P | BytePlus terms默认不训练Customer Data（opt-in另定）；content filter触发input/output在Malaysia存180天，中国条款独立。 | 非所有请求180天/全部数据零留存；actual过滤/合同/安全例外未查。 | [A7][A7]、[A8][A8]、[A9][A9] |

## OpenRouter

| 字段 | 状态 | 已冻结的有限事实 | unresolved / 后续核验 | 来源 |
|---|---|---|---|---|
| F01 endpoint / API surface | D | gateway Chat /api/v1/chat/completions；Responses另列，operator仍OpenRouter。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [OR1][OR1]、[OR2][OR2]、[MX][MX] |
| F02 认证 | D | Bearer OpenRouter Key；不能替代原厂Key/身份。 | 本条为日期化文档事实；实际账户/远端结果另验。 | [OR1][OR1]、[MX][MX] |
| F03 访问区域 / 部署区域 | P | base upstream slug可匹配多区域/变体；metadata.region不是upstream部署地域。 | available upstream信息之外保持unknown，整个chain地域未认证。 | [OR2][OR2]、[OR3][OR3]、[OR4][OR4] |
| F04 model alias / revision | P | 当前openai/gpt-4.1-mini页列OpenAI/Azure及价格；旧gpt5.2为另个文档例子。 | slug非actual upstream/revision/region认证，不从列表替换profile。 | [OR12][OR12]、[OR5][OR5]、[OR2][OR2] |
| F05 角色 | P | gateway Chat消息类型user/assistant/system及tool(tool_call_id)，非OpenAI model的name可前缀转换。 | selected upstream角色/developer转换未证，不宣称原厂全支持。 | [OR1][OR1] |
| F06 ToolChoice | P | gateway ToolChoice类型none/auto/指定function；require_parameters=true过滤不支持参数的provider，默认可能忽略。 | required/strict依selected upstream另证，不复制别gateway型号。 | [OR1][OR1]、[OR2][OR2] |
| F07 Tool 往返 | P | API有工具转换行为，metadata可报告pipeline。 | 完整所选Tool/result/转换规则须冻结；本最小text资料不证明Tool闭合。 | [OR1][OR1]、[OR3][OR3] |
| F08 并行 Tool | U | 未取得openai/gpt-4.1-mini所选upstream的parallel控制/gateway转换数量保证。 | OR1通用Tool/OR2过滤不能替upstream型号并行文档；需selected route独立补证。 | [OR1][OR1]、[OR2][OR2]、[OR12][OR12] |
| F09 Schema / JSON | P | gateway Schema/Tool能力依upstream。 | selected model的strict/keyword/JSON enforcement未由总表认证。 | [OR6][OR6]、[MX][MX] |
| F10 thinking / context 续传 | P | effort=none是否适用依模型；exclude=true仅隐藏；mandatory reasoning会拒none。 | 不得从非推理benchmark标签推off；context continuation须exact冻结。 | [OR7][OR7]、V2 |
| F11 stream / cancellation | P | SSE有comment keepalive，最终[DONE]前usage chunk含非空choices/重复finish_reason；midstream rate可SSE error/finish_reason=error。 | 取消计费/usage未知，HTTP200不排除中途失败，不照搬OpenAI空choices。 | [OR1][OR1]、[OR8][OR8]、[OR13][OR13] |
| F12 usage / cache / reasoning | P | native tokenizer计数，prompt+completion=total，cache-read/write与reasoning可选子项，cost_details可分BYOK upstream。 | cache hit省router metadata仍保留；cost不是identity证据，unknown不填0。 | [OR1][OR1]、[OR3][OR3]、[OR14][OR14] |
| F13 error / retry / rate | P | 402为credit、429可gateway或upstream rate；platform错误可有X-RateLimit-*，Retry-After有条件返回。 | 默认gateway fallback仍须显式关；actual限额/failed charge未知，未访问Key查询端点。 | [OR13][OR13]、[OR9][OR9]、[OR2][OR2] |
| F14 价格 / 时间窗 | P | openai/gpt-4.1-mini USD/1M input0.40/output1.60/cache read0.10；gateway价格按provider列。 | actual route/upstream/账单/其他费用未核，未取得通用idle价。 | [OR12][OR12] |
| F15 账户数据控制 | P | gateway自身prompt retention默认关（opt-in另定），upstream日志/训练另有条款，ZDR路由为独立控制。 | actual账号logging/ZDR/upstream政策未验，不合并承诺。 | [OR10][OR10]、[OR4][OR4]、[OR11][OR11] |

## 企业服务的独立边界

| 服务 | 已冻结认证 / API 事实 | 必须单独固定的部署边界 | 后续资料入口 |
|---|---|---|---|
| Azure OpenAI | `/openai/v1` Responses/Chat；resource Key 或 Entra。 | deployment 不是原厂 model alias；resource/API version/region/deployment/token scope 与实际账户权限分别固定；所选 Schema/Tool/continuation、usage/rate/价格/数据政策仍待核。 | [API lifecycle](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle)、[Responses](https://learn.microsoft.com/en-us/rest/api/aifoundry/azureopenai/responses)；R3:azure-v1 / azure-responses |
| Vertex AI | native project/location generateContent 或 OpenAI Chat-compatible；ADC/OAuth/express Key 分开。 | IAM/project/location、endpoint/model/version 和处理地域另绑；Developer API Key 不代表所有 Vertex endpoint 权限，signature/Schema 与企业账户政策仍单独核验。 | [API keys](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/api-keys)、[inference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference)；R3:vertex-auth / vertex-inference |
| Amazon Bedrock | Converse/Invoke 与其文档列出的 Responses/Chat/Messages；SigV4 或 Bedrock 专用 Bearer Key。 | runtime/mantle API、IAM/Region/model/ARN 各自固定；mantle Messages 不支持 output_config.format，AWS event stream 独立；原厂 Key 不能替该认证；其余 exact 字段待核。 | [endpoints](https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.html)、[structured output](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)、[API keys](https://docs.aws.amazon.com/en_us/bedrock/latest/userguide/api-keys-use.html)；R3:bedrock-endpoints / bedrock-structured / bedrock-auth |

## 来源强度与补证顺序

MX 为 [既有官方矩阵](OFFICIAL_MATRIX.md)，保留 R1/R2/R3 收集回执及官方原页 hash。V1 为 2026-10-02 逐家 profile source-facts 摘要：snapshot/搜索回执与结构检查分开，exact model 例子不等于账户运行；V2 为同日 Google/SiliconFlow/OpenRouter 独立补证摘要。V1/V2 hash为既有摘要保留的记录身份，R4未重新认证其原始记录；本轮新增事实按实际官方正文与独立回执补强，链接列在各行。来源代号表示出处，不把 local record hash 冒充原始 HTTP body hash。

来源记录身份：V1（public-vendor-candidate-source-facts，observed 2026-10-02）SHA-256：`e6e3a74fb8a14bd933abcd6b911ae99658df7e0c8a198d9902fef332155342fa`；V2（local-vendor-gap-preparation，retrieved 2026-10-02）SHA-256：`82f235e922cc459d21ff6d72463cef5b10b6b516255bd0bbb2a55356e1d3a9a5`。这些是有限事实记录的 hash，非对应官方原页 body hash。

R4为本轮官方公开补核：原表/源矩阵各有保留副本。实际document GET保存实体bytes、状态/finalURL、encoding、SHA-256；派生text/BytePlus嵌入MD另hash。web可见结果原样保存，摘要/搜索结果绝不生成或冒充原bodySHA。DeepSeek八份文档实体均取得；BytePlus此前JS/search限制通过实体中的MDContent正文补强。原404/timeout/错误导航保留，失败不代表能力缺失。

本轮source pins、逐字段变更/未决与检查回执在隔离执行archive，公开文档只用官方HTTP URL/同目录相对链接。正文hash、派生摘录、web可见输出是不同证据层，资料取得不等于远端能力通过。未取得平台全量导出仍有capture-gap。

后续优先绑定exact surface/model/mode：DeepSeek Responses独立strict/Schema keyword表、各型号并行Tool控制、signature/加密续传、取消/失败usage/charge、实际账户tier/地域/合同依各行补核。账户条件未知不表示公共政策缺失，不一概强设为所有合成测试gate。本次不更改实现model/profile、Task接受、live资格或全目标状态。

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

[O6]: https://developers.openai.com/api/docs/guides/function-calling "OpenAI function calling"
[O7]: https://developers.openai.com/api/docs/guides/your-data "OpenAI your data"
[O8]: https://developers.openai.com/api/docs/guides/rate-limits "OpenAI rate limits"
[O9]: https://developers.openai.com/api/docs/pricing "OpenAI pricing"
[O10]: https://developers.openai.com/api/docs/models/gpt-4o-mini "OpenAI GPT-4o-mini model card"
[AN7]: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools "Anthropic define tools"
[AN8]: https://platform.claude.com/docs/en/api/rate-limits "Anthropic rate limits"
[AN9]: https://platform.claude.com/docs/en/about-claude/pricing "Anthropic pricing"
[AN10]: https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data "Anthropic commercial retention"
[AN11]: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention "Anthropic API data retention"
[AN12]: https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use "Anthropic parallel tools"
[AN13]: https://platform.claude.com/docs/en/api/messages.md "Anthropic Messages raw documentation"
[G11]: https://ai.google.dev/gemini-api/docs/pricing "Gemini pricing"
[G12]: https://ai.google.dev/gemini-api/docs/rate-limits "Gemini rate limits"
[G13]: https://ai.google.dev/gemini-api/terms "Gemini API terms"
[G14]: https://ai.google.dev/gemini-api/docs/function-calling "Google function calling with surface boundary"
[G15]: https://ai.google.dev/gemini-api/docs/available-regions "Google available regions"
[G16]: https://ai.google.dev/api/caching#FunctionCallingConfig "Native FunctionCallingConfig reference"
[DS10]: https://api-docs.deepseek.com/api/list-models/ "DeepSeek models metadata reference only"
[DS11]: https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html "DeepSeek privacy policy"
[DS12]: https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html "DeepSeek Open Platform API terms"
[Q8]: https://www.alibabacloud.com/help/en/model-studio/rate-limit "Model Studio rate limits"
[Q9]: https://www.alibabacloud.com/help/en/model-studio/model-pricing "Model Studio pricing"
[Q10]: https://www.alibabacloud.com/help/en/model-studio/faq-about-alibaba-cloud-model-studio "Model Studio FAQ data training"
[Z9]: https://docs.z.ai/guides/overview/pricing "Z.AI pricing"
[Z10]: https://chat.z.ai/legal-agreement/terms-of-service "Z.AI terms API section"
[Z11]: https://chat.z.ai/legal-agreement/privacy-policy "Z.AI privacy and API DPA"
[K10]: https://platform.kimi.ai/docs/pricing/chat "Kimi international prices"
[K11]: https://platform.kimi.ai/docs/pricing/limits "Kimi tier rate limits"
[K12]: https://platform.kimi.ai/docs/agreement/userprivacy "Kimi international privacy"
[K13]: https://platform.kimi.ai/docs/agreement/modeluse "Kimi Model Use terms"
[M6]: https://platform.minimax.io/docs/guides/rate-limits "MiniMax rate limits"
[M7]: https://platform.minimax.io/docs/guides/pricing-paygo "MiniMax PAYG prices"
[M8]: https://platform.minimax.io/protocol/privacy-policy "MiniMax privacy"
[M9]: https://platform.minimax.io/protocol/paid-agreement "MiniMax paid terms"
[SF7]: https://docs.siliconflow.cn/docs/legals/privacy-policy "SiliconFlow policy 2026-07-30"
[A6]: https://docs.byteplus.com/en/docs/modelark/1159200 "BytePlus model activation rate limits"
[A7]: https://docs.byteplus.com/en/docs/legal/docs-service-specific-terms "BytePlus service terms"
[A8]: https://docs.byteplus.com/zh-CN/docs/ModelArk/BytePlus_ModelArk_Data_Processing "BytePlus ModelArk data processing"
[A9]: https://docs.volcengine.com/docs/ark/volcengine-ark-platform-terms?lang=zh "China Ark platform terms"
[A11]: https://docs.byteplus.com/en/docs/modelark/1099320 "BytePlus Pricing embedded document"
[OR12]: https://openrouter.ai/openai/gpt-4.1-mini "OpenRouter GPT-4.1-mini prices"
[OR13]: https://openrouter.ai/docs/api_reference/limits "OpenRouter credit rate limits"
[OR14]: https://openrouter.ai/docs/cookbook/administration/usage-accounting "OpenRouter usage accounting"

[A12]: https://docs.byteplus.com/en/docs/modelark/structured-output-beta "BytePlus beta structured output canonical guide"

R6为FOLLOWUP-008的两组公开补充：Qwen所选型号价行/普通角色/usage及BytePlus beta Schema正文；日期为2026-10-02 UTC。原R4/R5收据身份保持，六行继续P，D31/P129/U5不变。BytePlus原A5的200/null-document/零正文与实际canonical href另存；支持表未取得是not extracted，不是服务不支持。实体hash与限定范围见[本轮检查](../M6-GENERAL-PROVIDER-IMPLEMENTATION/attempts/FOLLOWUP-008/CHECKS.md)。

[A13]: https://ai.byteplus.com/ark/region:ap-southeast-1/docs/ModelArk/model-list#86588b72 "BytePlus observed model-list href, SPA shell only"

[Q11]: https://www.alibabacloud.com/help/en/model-studio/context-cache "Qwen Context Cache observed pricing href"

R7为FOLLOWUP-009的Qwen Responses与Q9实际Context Cache href两目标公开补核，取得时间2026-10-02T21:32:32Z；两页标示更新2026-09-28。按surface补充缓存用量、所选read价例外、Session cache与续传，D31/P129/U5不变。R6及原始收据保持；不修改任何profile能力，console-only未知不转为账户访问。实体身份与检查见[FOLLOWUP-009](../M6-GENERAL-PROVIDER-IMPLEMENTATION/attempts/FOLLOWUP-009/CHECKS.md)。

R8为FOLLOWUP-010的G6/G14/G16三目标公开补核，取得时间2026-10-02T22:15:20Z–22:15:23Z；页面分别标示更新2026-09-16/09-23/09-11。native generateContent、Interactions和SDK自动执行分别记录；所选Gemma4 F08仍U，D31/P129/U5不变，不修改profile或访问账户。公开实体与条件化Flash输入预留依据见[FOLLOWUP-010](../M6-GENERAL-PROVIDER-IMPLEMENTATION/attempts/FOLLOWUP-010/CHECKS.md)。
