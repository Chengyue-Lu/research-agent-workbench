# 通用 Model Provider 接入与 DeepSeek 首轮验收

状态：task-definition 候选；2026-10-02。基线 develop `1c9cef27983e93362be33830f989e124ad3ccc41`。
Task owner：黄毅；Capability/View/DataPolicy 与 M5 Evaluation 交界由路诚钺复核。风险 R2。
任务状态与 hard dependencies 只由 [TASKS](../../../TASKS.md) 维护。

## 用户要求与现有基础

用户要求最终以通用层接入主流 API Key，官方资料完整收集；首轮真实测试只使用 DeepSeek Flash，
在北京时间 18:00 后对齐官方闲时价格。密钥已由用户交互存入本地凭据库，项目只引用凭据来源。
该输入确定测试厂商、模型系列和时间下限；具体 exact model/profile、账户数据边界、预算与当前
implementation 的执行资格仍须冻结。它没有接受新的 Task、Scope/Skill/Pilot 或授权 merge。

复用 [ADR-0003](../../../decisions/0003-PROVIDER-NEUTRAL-MODEL-PORT.md) 的 ModelProvider 端口与
[ADR-0007](../../../decisions/0007-THIN-PROVIDER-ADAPTERS.md) 的薄 Adapter、晚解析凭据、保守能力和
本地验证。现有三家 Adapter 已离线实现。当前配置/报告仅接受三家身份；DeepSeek 尚未实施。
DeepSeek 最新官方文档包含 Responses、Chat Completions 与 Anthropic 兼容入口，不能沿用
“仅 Chat”假设，也不能仅替换 URL 或把它记录为 OpenAI。

## 两个独立验收单元

| Task | 可验收对象 | 完成要求 |
|---|---|---|
| M6-009 | 通用协议配置、真实 vendor profile、晚解析凭据接口与主流 Key 接入的离线实现 | 四类协议映射复用既有 Port；所有列入 Key 接入范围的 profile 具有禁用模板、能力/参数/认证闭集与独立正反离线 fixture；保留旧配置和报告回放；无真实请求 |
| M6-010 | DeepSeek Flash 的 Windows Provider/isolated Session 真实 conformance | exact source/profile/model/credential reference/budget/time/Tool 冻结，具名授权后进行合成 shape 与 bounded Tool/session probes；只有 exact binding 的脱敏结果满足全部谓词才提出 DONE |

M6-004 继续保存原 OpenAI 真实验收范围与 BLOCKED 事实。M5-008/M5-004 的当前首轮 Provider Gate
在本定义中明确改为 M6-010，验收仍必须适用于其实际使用的同一 exact binding。未来换厂商、模型、
协议、模式或影响执行的配置必须重新验证适用性，不从 DeepSeek PASS 推导其他厂商 PASS。

## M6-009 的实施切片

1. 非秘密、闭集的版本化 profile：分开 `provider identity`、wire protocol、endpoint/认证、模型、
   generation mode/参数与能力。显式映射而非 URL 猜测；旧配置仍按原语义读取。凭据来源复用
   `CredentialProvider` 的 available/resolve 晚解析接口，环境变量是跨平台基线，本地 OS vault 是可选
   后端或只向目标子进程注入环境的桥；公共工件只含 source reference。unsupported source/profile
   在接触密钥和发出请求前拒绝，诊断/repr/Trace 不含密钥或原始认证内容。
2. 复用 Responses、Messages、generateContent 的现有实现，补齐 Chat Completions codec；每个
   vendor profile 仍有独立 adapter identity 与可 pin 的实现/config。不得让兼容协议名称取得 Provider
   身份、Supply selection 或模型换绑权。确实一致的编码/解析才共享代码。
3. 主流 Key 接入范围：OpenAI、Anthropic、Google Gemini Developer API、DeepSeek、Alibaba
   Qwen/DashScope、Zhipu GLM、Moonshot/Kimi、MiniMax、SiliconFlow、ByteDance/Ark、OpenRouter。
   各 profile 从官方资料冻结已支持的 text、client Tool、Schema/JSON、角色、usage/停止/error
   语义；每家至少一条完整配置→factory→request→response 离线路径。未知/不支持的硬能力
   返回 CapabilityGap，不能只允许 provider 字符串并把空模板称为可用。
4. 明确模型/模式组合。首轮 DeepSeek 非思考 Tool profile 必须原生显式关闭 thinking；依赖 opaque
   reasoning/thought continuation 的组合只有在其独立契约闭合后才启用。streaming、multimodal、
   server tools、自动 Router/retry/fallback 和托管云平台执行保持 M6-005 的原范围；资料仍收集。
5. conformance producer/Schema/CLI 支持新增身份和 profile 证据，保留旧版本/报告与原三家回归；
   只声明实现且在 exact profile 验证的能力。本地 JSON Schema PASS 与远端 strict enforcement
   分别表示；JSON mode 不能冒充远端 strict Schema。成本 actual/estimated/unknown 与 cache/
   reasoning 分项保留，不把未知费用填零。

## 资料覆盖与证据等级

每家记录官方 URL、核验日期、endpoint/API surface、认证/区域、model alias/revision、角色、
ToolChoice/工具往返/并行、Schema 方言/JSON、thinking/context续传、stream/cancellation、usage/cache/
reasoning、错误/retry/rate、价格/时间窗及账户数据控制。未能取得的字段明确 unresolved 和后续来源。
Azure OpenAI、Vertex AI、Amazon Bedrock 独列认证与部署边界，资料覆盖不声明相同 Key 可互换。
网关 profile 记录实际 gateway identity 与可得 upstream identity；缺失 upstream 信息保持 unknown。

`documented-compatible`、`offline-contract-tested`、`exact-live-accepted` 分开记录；新增模板默认 disabled，
无账户模型验收即 pending-live。首轮只使用 Flash；其他厂商不读 Key、不消费账户。

## M6-010 的输入与预算

运行前冻结 exact model ID 与可接受 observed model/revision、API profile/端点、非思考模式、
source/config/validator/Windows Host/Tool implementation 与界面、官方价格与闲时窗、账户数据控制、
执行者、输出目标、凭据引用及具名授权。北京时间不得早于 18:00；跨出官方优惠窗前停止新请求。
到达时间窗口不自动授予执行资格。模型别名发生漂移或报告不能闭合时先停，不换模型凑通过。

预算候选为不超过 3 次 provider invocation，遵循 ADR-0007 的首轮上限：第1轮要求一次指定client
Tool call，第2轮携带经验证的Tool结果并验证text，另1次验证Schema；前2轮同时构成bounded
Tool Session，不在三次shape probes之外追加往返。每次最多 64 output tokens、1 次确定性无副作用 Tool、0 retry、有限输入/
累计 token/费用/time ceiling。它是待冻结候选，未记录为已批准的数值预算。第一项失败后停止，保留
实际调用数、用量/费用可得性、失败与剩余 slots；不为测试故意发无效 live 请求。

固定合成输入，不读取研究语料或 private oracle；本地 Tool handler 真正执行一次且参数先本地验证。
shape conformance 与 session evidence 分层留存，不把不执行 Tool 的 shape probe 当往返通过。
报告记录 requested/observed provider/model/profile、actual config/source pins、usage/stops、成功/失败
和 redaction 事实；不保留密钥、原始 prompt/response/tool arguments/隐藏思考。费用未知按冻结策略停。

## 读取、输出与停止

允许读集：AGENTS/README/docs 导航、TASKS/ROADMAP/STATUS、上述 ADR、Provider Adapter Plan；
`src/research_workbench/adapters/models/`、直接 CLI/schema/registry 消费者与 Provider/Session tests；
M6-008 baseline 的 exact binding 消费点、M5-008 Gate；官方矩阵及对应页面。新增消费者通过 filename/
import metadata 定位，写明必要性后扩大读集。禁止读取用户凭据原文或无关研究/Agent 工作区。

产品 write scope：M6 model adapters/非秘密 config/直接 conformance CLI/tests/schemas/registry；
涉及公共 Port 的语义变化需原 owner 共同确认。M5/M11/Resolver/Skill/Research State 的实现不在
M6-009 write scope。M6-010 输出仅为本地 exact-run packet 和脱敏审查证据；失败不得改写历史 PASS。

Task definition PR 只写文档。正式委派、R2 或跨窗口触发时保存 bounded Task/消息/可观察 receipt，
原始私密材料与机器绝对路径不提交。改变 Core identity、人类权威、运行时所有权或 reasoning
可见性时停并另行 ADR；不借通用层产生新 Resolver、credential service 或全球路由器。

## 风险与验证

详见 [Risk Ledger](RISK_LEDGER.md) 与 [定义审计](attempts/DEFINITION-001/CHECKS.md)。
本定义的 CI 只验证文档、依赖与治理；产品离线合同及 live PASS 要由 M6-009/010 后续实现证明。
M5-008 的 A4 admission、pilot dossier/预算/数据/Tool/Human review 仍分别接受，不由保存 Key 解锁。
