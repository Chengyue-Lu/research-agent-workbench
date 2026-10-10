# CHAIN-DEV4-007 Compact Handoff

2026-10-07；bounded implementation worker；required-Skills=[]。本片段为 PR140 checkout 的隔离 R2 候选；黄毅负责 API 接点接受、路诚钺负责控制预算。没有代签 source/live/Human 接受。

来源：[本 Packet](DEV4_PROFILE_TASK_PACKET.md) SHA-256 `d3ca8517c8386b47f98283ac2734b91c7a8cb50e1c3f58daa5f15159139e6a57`；[总 Packet](TASK_PACKET.md)；[API budget handoff](API_BUDGET_HANDOFF.md)；[可见通信](DEV4_PROFILE_COMMUNICATIONS.md)。Root 报告原 1024 Profile 构造在发送前被当前 256 硬上限拒绝；本片段未重跑该诊断。

## 最小改动

| 文件 | 改动 | SHA-256 |
| --- | --- | --- |
| [profile_configuration.py](../../../../../src/research_workbench/adapters/models/profile_configuration.py) | 仅将 output limit parser 的 maximum 从 256 调为 1024；正整数/有限值等原检查保留 | `70c259e096d82124823d9313df75359ac72f62c8a7960307e7b8ff63f0a4e652` |
| [provider-api-profile.schema.json](../../../../../schemas/v0.1.0/provider-api-profile.schema.json) | 仅将对应 integer 字段 maximum 调为 1024，minimum 仍为 1 | `5d097d2b75db1d931005cc623de4d5a10ca1f6e3a0db7ff65f4533d14725bec0` |
| [test_provider_profile_configuration.py](../../../../../tests/test_provider_profile_configuration.py) | 原超上限 257 → 1025；新增 Schema/parser 数值边界及纯 encode_profile_request 的 Profile 256/request 257 admission 回归代码，不构造 Provider/transport | `59d1d8e42168258aebdff62607977134542254f95226f804688436e43c576983` |

没有修改已发布 Profile bytes、默认 Profile 值、Registry、accepted ADR/config、其他开发/测试文件或 primary memory。1024 是可声明的 Profile 最大值；实际请求仍受自己 Profile、Task、caller guard 和整个 Run 的更小上限约束。

## 共享 Schema 影响与集成顺序

按本 Packet 保持 Schema `v0.1.0` 与 Profile `1.0.0` 的既有身份/字段，仅扩展输出数值域；不新增身份、Skill 路由或权威边界。合法旧 Profile 不需改 bytes/pins；新声明 257–1024 的 Profile 会被旧 parser/Schema 拒绝，因此 parser/Schema/边界测试应同批集成，不单独先发布 Profile。

消费方：ProviderApiProfile parsing、profile config load/resolve、ConfiguredProvider factory/generate。为编写任务要求的真实 request admission 用例，仅窄查了已有测试引用的 wire encode admission 和 configured factory/capabilities/generate 公共接点；没有更改这些消费者。已有 ConfiguredProvider 使用 Profile 自己的 limits，本片段不将其改为统一 1024。

合并/执行顺序由 Root 控制：先运行所有相关离线 Schema/parser/request-admission 测试及八个构造适配诊断，再核 current source closure/hash、授权/实际时钟、body 和累计预算。Schema/parser 源已变化，不能把旧 source qualification 自动用于新实现。保持 Packet 的单 call 1024 与累计 1000 万边界；本片段未扩大任何实际授权或预占。

## 静态检查与未测事实

15:37:03 UTC 的两个 Python 文件 AST/内存 compile 及 Schema JSON syntax 检查通过，没有执行 code object、import 项目模块或测试用例。返回前检查本输出相对 Markdown 文件路径和 source hashes；静态语法通过不代表 Schema/SDK 行为或 live 成功。

本代理没有执行产品/Schema validator/API/Tool 测试，没有读取 Key/账、预占、安装、Git mutation 或 memory 写入。Root 是唯一测试与实际发送者；Root 的首次执行反馈及修正后待复测事实见下段。

Root 首次 31 profile tests 为 1 ERROR/1 skipped，transport 不匹配；修正后第二轮仍在构造阶段 ERROR，因为该 TestCase 已 patch 凭据方法，source binding 正确拒绝被替换方法。两次均未到达 257 admission 断言。按 Root 最后更正，当前测试改为 `test_profile_wire_admission_256_rejects_request_257`，仅调用纯 encode_profile_request 并断言错误类别及原凭据 mock 零调用，不再构造 Provider/transport。原 source binding 检查保持，最终 test hash 以上表为准，AST/内存 compile 通过；实际结果待 Root。

**具体未决缺口：** 当前 wire_codecs._validate_request 给 preflight 构造的 ProviderCapabilities 未传入 Profile limits；不能静态证明纯 wire 路径会按每个 Profile 声明拒绝 257。新增回归可能揭示该缺口，需 Root 实测并另行处理 codec ownership，不能改 binding、mock 判断或静默把失败用例当通过。本片段不扩展到 codec；ConfiguredProvider 的自身 limits 检查保留，Root 独立 SDK/budget 测试的范围不能替代此纯 wire 回归。

实际阅读范围：Packet、总 Packet、budget handoff；owned parser 的数字/Profile 解析段、Schema limits、owned 测试 helper 和相关 boundary/wire consumer 段；Architecture 内外环、Development 共享 Schema/风险、文件名发现后的模块 06 Task Context；上述公共 request admission 接点；primary PROJECT_MEMORY 当前导航片段。未读 private Profile、实际 Key/账、运行响应或其他代理内部产物。

## Root 下一步

1. 执行 `test_provider_profile_configuration.py` 全套，特别是两项新增边界测试；确认旧合法 Profile/固定 public pins 未变。
2. 复核 1024 可以 Schema 校验及 parser 构造；1025、bool、Python float、非正和非有限值仍在相应边界拒绝。JSON Schema integer 采用 JSON 数值语义，测试不把数学整数形式的 `1024.0` 当作 Schema 必拒绝项；Python parser 仍拒绝它。
3. 复测纯 wire admission 用例；若 256 Profile 的 257 request 没有被拒绝，保留失败并另定义 codec 修复切片。SDK 已有 per-Profile 限制和 source binding 不放松。
4. 重新检查实际 API factory 1024 Profile 的构造桥、对应 source/预算/时钟/body guard；实际调用及完整结果仍由 Root 保存验证。

Coordinator 建议条目（本片段无 primary memory 写权）：

> 2026-10-07 · CHAIN-DEV4-007：PR140 checkout 将 Provider API Profile parser/Schema max_output_tokens 声明域统一为 1..1024，旧 Profile bytes/default/Registry 不动；改原 257 超界为 1025并补高端边界与 256 Profile 请求257在凭据/transport前拒绝的代码。仅 AST/内存compile/Schema JSON syntax/交接链接与hash 静态检查，未产品/API/Tool/Key/账/预占/install/Git mutation；本地未提交 R2 候选，未 live/具名接受。来源 chain-proof-002/DEV4_PROFILE_HANDOFF.md 和 DEV4_PROFILE_COMMUNICATIONS.md。Next Root 跑相关全套与实际 factory 构造诊断，重核改变后的 source closure/guard；黄毅 API 接口、路诚钺控制预算审查接受。
