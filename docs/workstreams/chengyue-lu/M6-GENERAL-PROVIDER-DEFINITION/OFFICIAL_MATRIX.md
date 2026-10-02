# 官方Provider协议与能力核对矩阵

核对日期：2026-10-02；RWB source：1c9cef27983e93362be33830f989e124ad3ccc41。
状态：文档事实D＋差异分析；本轮无新增离线契约通过O或live通过L。十一家公共Provider/网关与三家企业服务分别列出。
这些资料不证明任意Key可用、账户权限、全部model支持、runtime接受或科学评价。

| 服务 | D：官方入口/认证事实 | D：能力与协议差异 | 未决/本地缺口 | 来源及收集条目 |
|---|---|---|---|---|
| OpenAI | Responses＋Chat；Bearer；API surface/model snapshot分别固定。 | JSON Schema/strict依模型子集；reasoning continuation与两种stream不能混parse。 | 不能据旧Adapter证明全部新模型，O/L未新增。 | [接口/认证](https://developers.openai.com/api/reference/python/resources/responses/methods/create)；[能力/限制](https://developers.openai.com/api/docs/guides/structured-outputs)；R3:openai-responses |
| Anthropic | Messages；Bearer或仍支持x-api-key，version/workspace独立。 | output_config.format/strict Tool；thinking/signature/stream与usage-cache有专有语义。 | 所选模型续传与Schema方言要离线证明；旧x-api-key仍合法。 | [接口/认证](https://platform.claude.com/docs/en/api/overview)；[能力/限制](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)；R3:anthropic-overview |
| Gemini | generateContent / streamGenerateContent；x-goog-api-key。 | response schema子集、functionCall/Response；Gemini3要求Tool thoughtSignature原样续传。 | 现有Google Adapter没有thinking controls/完整signature续传。 | [接口/认证](https://ai.google.dev/api/generate-content)；[能力/限制](https://ai.google.dev/gemini-api/docs/generate-content/thought-signatures)；R3:gemini-api |
| DeepSeek | Responses/Chat/Anthropic；Bearer；首轮请求ID deepseek-flash，当前标称V4.1-Flash。 | Responses reasoning.effort=none关闭思考；Chat thinking.disabled；developer降user、strict差别。 | Flash/18:00约束已指定，exact Slot/profile/预算/调用Gate尚未闭合。 | [接口/认证](https://api-docs.deepseek.com/quick_start/pricing)；[能力/限制](https://api-docs.deepseek.com/api/create-response/)；R3:deepseek-pricing-current |
| Qwen/DashScope | Chat＋Responses compatible-mode；地区/workspace/Key须一起绑定。 | json_object与json_schema支持model/mode集合不同；Tool指南示例有auto/none/指定函数，Qwen非思考required不能保证调用、思考模式不支持required。 | 概要和细型号表有粒度差异，按exact model/profile验证；托管Kimi的required示例不证明Qwen支持。 | [接口/认证](https://www.alibabacloud.com/help/en/model-studio/compatibility-of-openai-with-dashscope)；[Schema限制](https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output)；[Tool限制](https://www.alibabacloud.com/help/en/model-studio/qwen-function-calling)；R3:qwen-chat；R5:qwen-tool-choice |
| GLM/Z.AI/智谱 | 国际Chat /api/paas/v4；中国Responses /api/v1、Claude /api/anthropic；账户不同。 | Z.AI已读JSON Object非server Schema保证；thinking默认/clear_thinking/effort随型号。 | 中国surface不得推广到国际/Coding Plan；always-thinks型号不进入非思考profile。 | [接口/认证](https://docs.bigmodel.cn/cn/guide/develop/responses/introduction)；[能力/限制](https://docs.z.ai/api-reference/llm/chat-completion)；R3:glm-cn-responses |
| Moonshot/Kimi | Chat＋Responses＋Messages；Moonshot Key；文档转platform.kimi.ai。 | Schema支持与稳定性随k3/k2.7-code/k2.6；reasoning_content/Tool/stream需匹配型号。 | alias与actual model、区域账户/复杂Schema仍按profile验收。 | [接口/认证](https://platform.kimi.ai/docs/api/responses)；[能力/限制](https://platform.kimi.ai/docs/guide/response_format)；R3:kimi-responses |
| MiniMax | Chat＋Responses＋Anthropic；MiniMax Key/订阅或PAYG权限分开。 | Responses输入message角色枚举为user/assistant/system/developer/tool；M3.1-Flash-Preview none报400，M2.x可忽略none；思考Tool块须续传。 | 输入枚举不证明角色优先级；首轮非思考不能默认覆盖全M系；strict Schema保证未确认。 | [接口/认证](https://platform.minimax.io/docs/api-reference/responses-create)；[能力/限制](https://platform.minimax.io/docs/api-reference/text-openai-api)；R3:minimax-responses；R5:minimax-input-roles |
| SiliconFlow | 已读Chat；Bearer；provider仍为平台，publisher/model全名另列。 | API有json_schema/json_object/Tool/stream/usage，effort取决于所选托管model。 | Anthropic参数未核实；error/index直读不可达，搜索证据保留。 | [接口/认证](https://docs.siliconflow.cn/docs/api/chat-completions-post)；[能力/限制](https://docs.siliconflow.cn/en/faqs/error-code)；R3:siliconflow-api |
| ByteDance/Ark | Chat/Responses；中国/BytePlus端点不同；Key或Access Key签名。 | 签名model须Endpoint ID；thinking encrypted/content与provider-state续传不同。 | Schema按model约束；部分猜测URL为普通页，不充证据；fallback须拒绝。 | [接口/认证](https://docs.volcengine.com/docs/ark/base-url-and-authentication?lang=en)；[能力/限制](https://docs.volcengine.com/docs/ark/chat-api?lang=zh&redirect=1)；R3:ark-auth |
| OpenRouter | Chat/Responses；OpenRouter Key；网关operator与actual upstream分别固定。 | 默认路由/fallback；需full endpoint slug、only/order、allow_fallbacks=false、require_parameters。 | Schema/Tool/思考依upstream；actual路由/转换和整链privacy/region须独立证明。 | [接口/认证](https://openrouter.ai/docs/guides/routing/provider-selection)；[能力/限制](https://openrouter.ai/docs/guides/privacy/data-collection)；R3:openrouter-routing |
| Azure OpenAI | /openai/v1 Responses/Chat；resource Key或Entra，deployment不是原厂model alias。 | 接口可复用，API/version/region/deployment与token scope分别冻结。 | 原厂Key不等于Azure权限；specific部署的Schema/Tool/continuation待验。 | [接口/认证](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle)；[能力/限制](https://learn.microsoft.com/en-us/rest/api/aifoundry/azureopenai/responses)；R3:azure-v1 |
| Vertex AI | native project/location generateContent或OpenAI Chat-compatible；ADC/OAuth/express Key分开。 | IAM/project/region与Developer API不同；native signature/Schema规则保持。 | 任何Google Key不能推定所有Vertex endpoints可用。 | [接口/认证](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/api-keys)；[能力/限制](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference)；R3:vertex-auth |
| Bedrock | Converse/Invoke及当前Responses/Chat/Messages；SigV4或Bedrock专用Bearer Key。 | runtime/mantle支持不同；mantle Messages不支持output_config.format；AWS event stream独立。 | IAM/Region/model/ARN必须固定；API Key不替原厂Key，不自动实现企业认证。 | [接口/认证](https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints.html)；[能力/限制](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)；R3:bedrock-endpoints |

共同验收范围：nonstream text/schema/client Tool。stream格式、usage/cache/reasoning细项、HTTP/business error与failed/incomplete/refusal分别处理；只有完整响应可触发Tool。SDK/provider自动retry/fallback不得隐式扩大预算或改变identity，未知失败charge保留unknown。

Flash模型与价格：deepseek-flash当前标称DeepSeek-V4.1-Flash；每1M tokens USD闲时input-hit0.003/input-miss0.15/output0.60。工作日高峰UTC01:00–04:00、06:00–10:00，即北京时间09:00–12:00、14:00–18:00；直接GET页排除中国公共假日，其余闲时。18:00后约束与该窗一致，运行前仍复核价格。[官方定价](https://api-docs.deepseek.com/quick_start/pricing)。价格不充获批数值预算。

OpenRouter应保留网关身份与actual upstream；router metadata只作provider-reported路由/转换事实，不作weights认证。data_collection/ZDR与gateway/upstream日志及region共同匹配任务要求，缺证据即不进入exact Runtime binding。[metadata](https://openrouter.ai/docs/guides/features/router-metadata)、[upstream logging](https://openrouter.ai/docs/guides/privacy/provider-logging)、[ZDR](https://openrouter.ai/docs/guides/features/zdr)。

现行M6-004 OpenAI谓词保持。M6-009负责通用四协议离线接入，M6-010负责独立Flash部件调用；任务定义已接受，完整实现与exact-run接受独立，黄毅M6维护不变。执行计划为每Attempt最多3次：指定Tool轮1＋真实纯函数结果/text轮2形成Session，再Schema轮3。失败即停并归档，离线诊断/修复/重新冻结后才可另建fresh Attempt，最多再复验2个Attempt；没有额外probe、自动retry或fallback。所有成功及失败input+output累计不得超过10,000,000；Attempt数量是执行计划，不是消耗目标或用户指定9次调用。exact实现/config/时间窗/输入预占依据/累计历史与具名调用接受仍是独立条件；未执行真实调用。

## Source receipts

R1/R2/R3为本次公开文档收集回执；hash只证明收集记录内容身份，非Provider调用或live token。正文所有官方URL可直接查阅；没有原页内容、机器绝对路径、凭据或研究数据。
- R1 FETCH_RECEIPTS.json SHA-256: 75343eade1b6cf91e1a43ef16b6fff5e94b84184880ca11b3e9d8dbdeaba26e6
- R2 REFERENCE_FETCH_RECEIPTS.json SHA-256: f02d411a1e78b2185a74bfb8d17d8eb34301bf4acfdedbafca7ac6753010b0b4
- R3 SURVEY_FETCH_RECEIPTS.json SHA-256: 8420291ed64fa04ffb52d9334ba160eaa2723e3f54e0778afac79a5e0b71d2c1

R5为2026-10-02T20:07:58Z的两项无认证官方文档补充；原R1/R2/R3与字段表R4观察保持。
公开实体与纯JSON提取仅本地归档，便携核验摘要见
[FOLLOWUP-007](../M6-GENERAL-PROVIDER-IMPLEMENTATION/attempts/FOLLOWUP-007/CHECKS.md)。

- Qwen / qwen-tool-choice entity SHA-256: 17a2bd0e9ee57bd0ea42ce754cc03f11bfd2524b2184b8986110085dd34717af
- MiniMax / minimax-input-roles entity SHA-256: 6494bc81c95951f0b568b841a266f4b4d265a5aeb65469fc97384b12949a7952
- MiniMax / input-contract extraction SHA-256: bd89b211bc15b7efcb799e1c226703055f5003659cae8607f7f1bc1e55d163be

R3条目对应的原页SHA-256（用于独立对账）：

- OpenAI / openai-responses: ac88ca2c08accf124ed26a08351f5998a21a975f9251e101d9a19d2b734b7b3c
- Anthropic / anthropic-overview: bac6917a2d4b876848b96a80e870f02082b98f33aecb858d792f02e4570e2b08
- Gemini / gemini-api: 650c76492d2fb37e6e3a56c008ef3e0706f0d4f41a34dcb4b403f2528325de92
- DeepSeek / deepseek-pricing-current: 210f102275ccf1a6542f08a3bc9e4b4c7c83278cb74b35217bffa112df6363b2
- Qwen/DashScope / qwen-chat: 6a043ac547caf8f7f300057fd65c40a45cb3ae59a0d1d5d7eaabe88d1e1cc511
- GLM/Z.AI/智谱 / glm-cn-responses: b3b7739ba34523fbee10e8380c807dd4159efa1f0a35d2a1c4d96ffbb0ace05c
- Moonshot/Kimi / kimi-responses: 17d7c9dca246b11884d37aaed549f2328c2172344e487f24ae700bb5feb769a2
- MiniMax / minimax-responses: 69d2bfcdd4df500daaf3637411f82a4dc302306e8966026fc2b2e6dfb6164112
- SiliconFlow / siliconflow-api: 9830f93579ed61549cdf76843bbd4269409a447bc524e69f767c5f2a30d88823
- ByteDance/Ark / ark-auth: 99fcea914af6efca542d30a91830f5a76a152da8e759cba5d123c7113b438678
- OpenRouter / openrouter-routing: e694978b6f90fb2c235d209a40f6d312695b288713e03f306ede45171817c669
- Azure OpenAI / azure-v1: 34de5e2ccd882d6622d7ae1a02fc171b20753a0f3d46b3506a849996dab2ddfc
- Vertex AI / vertex-auth: b945ea72842320f2736b4cdf42484439385f0aa5ffad28561bb46d9b59e009e2
- Bedrock / bedrock-endpoints: 4818a741f67e007b7bf1108d3b6204ab191776abc21e5c5c293530621bbd7f00


[逐字段覆盖与待核清单](OFFICIAL_FIELD_COVERAGE.md)：十一家服务的计划字段、日期化事实、未决条件与后续官方来源入口。
