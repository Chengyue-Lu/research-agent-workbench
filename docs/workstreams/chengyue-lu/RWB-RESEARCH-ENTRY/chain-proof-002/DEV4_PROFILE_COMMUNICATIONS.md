# CHAIN-DEV4-007 可见通信

2026-10-07；[Packet](DEV4_PROFILE_TASK_PACKET.md)；[Handoff](DEV4_PROFILE_HANDOFF.md)。路径按仓库相对 locator 规范化，保存 bounded development 可见传递/检查事实，不保存隐藏推理或文件打开流水。Root 负责完整运行 Archive 与全部测试。

## 输入消息

Root 委派：

> 继续有界开发 CHAIN-DEV4-007，Root真实API预备适配遇到当前SDK Profile仍硬限256，旧获授权1024 Profile构造被拒绝，实际发送0。Task Packet已落盘在当前PR140 checkout docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/DEV4_PROFILE_TASK_PACKET.md；工作树当前 research-entry-integration。按完整Profile/Skills=[]/读域/ownership/10分钟1轮推进最小Schema+parser上限一致1024及边界测试代码；只开发/静态，不测试/API/Tool/Key/账/安装/Git/memory。Root唯一测试者。你不独自在代码库，保留他人编辑。完成保存handoff/可见通信及源hash后停止。

## 可见开发更新

1. 我会先读 CHAIN-DEV4-007 的 Packet，核对 Profile 的 Schema 和 parser 上限，再按指定范围修正并补边界测试代码。本片段只做开发与静态检查，测试仍由 Root 执行。
2. 阻断已定位：parser 和 Schema 都把 Profile 输出上限写死为 256。我会将可声明范围统一为 1–1024，并补用例确认：较小 Profile 仍按自身上限拒绝请求，声明 256 的 Profile 不会因此允许 257。
3. Schema、parser 和边界测试代码已落盘，静态语法检查通过；测试用例尚未执行。新增用例覆盖 1024 可解析、1025 及非法数值被拒绝，以及 Profile 声明 256 时，请求 257 在凭据和 transport 接点前被拒绝。交接后由 Root 验证。

## 实际操作与检查

- 15:32:45 UTC 起，10 分钟/一轮。起始工作区已有 config、多个 entry 模块和 Root 的新测试，不回滚、不修改这些内容。
- 文件名发现得到模块 `06-CONTEXT_GOVERNANCE.md`，仅读其 Task Context 段；读 Architecture/Development 对共享 Schema、运行权威和风险的相关段。
- 为判定新测试应该验证的真实 request admission，窄查既有 wire encode 与 configured factory/capabilities/generate 的公共接点，确认实际 SDK 保留自身 Profile limits；这些文件只读，未改动。
- 一轮修改三个 owned 文件：两个数值 maximum 和 original reject boundary，加两项边界测试代码。
- 15:37:03 UTC：标准库 AST parse/内存 compile 两个 Python 文件，未执行 code object；json.loads 仅解析 Schema JSON syntax，未运行 jsonschema validator 或测试。三个 source pins 见 Handoff。
- 只读 Git status/diff 用于共享工作区/指定差异元数据核对；无 Git mutation。没有产品/API/Tool/Key/账/预占、安装或 primary/global memory 写入。
- 新增交接/通信内部 Markdown 文件 targets 在返回前静态检查。原 fixtures/default Profile bytes/Registry 不改；尚未运行回归、SDK factory 适配或 live 测试。

Packet SHA-256 `d3ca8517c8386b47f98283ac2734b91c7a8cb50e1c3f58daa5f15159139e6a57`。源 hashes 与建议 continuity 条目在 Handoff；正式接受仍按黄毅 API/路诚钺控制职责由 Root 组织。

## Root 实测更正与限定修复

Root 新消息原文：

> Root开始实际离线验证当前已落盘版本：31 profile tests中1 ERROR/1 skipped。新增 test_profile_256_rejects_request_257_before_credential_or_transport 在 Provider构造时报 provider transport differs from configuration，尚未达到257 preflight断言。请在原ownership修正test中的RecordingTransport max_response_bytes精确等于该adapter配置（不是产品放松transportidentity），静态完成后给最终hash/停。Root自己的私有budget tests另因__main__ fixture类无显式source module被正确拒绝，Root正在修正测试fixture模块身份，不改core绑定检查。实际API0。

可见更新：

> Root 的测试已定位到新用例的构造问题：测试 transport 与 adapter 配置不一致，尚未执行到 257 请求的拒绝断言。我会只修正测试 transport 的配置值，保持产品的 transport identity 检查。

修复前重读 owned test 当前段与 constructor transport identity 公共检查，未覆盖其他编辑。仅把测试 Mock 换成 RecordingTransport，max_response_bytes 来自 adapter.transport.max_response_bytes，send 进入则记录并失败。15:40:13 UTC 只 AST/内存 compile 通过；最终 test SHA-256 `bdc581e8283ad1e9353e0843b0cac9d3b20c6ffd73fc615060ad4b775f6efd02`。parser/Schema pins 不变；未运行测试/API，不把 Root 的首轮错误或此语法通过称修正后测试 PASS。

## 最终交接通知

用户授权的同一主准备窗口 `01a1064a-eaef-7da0-aebd-962910ff42b8` 已收到工具确认的完成通知：1..1024 parser/Schema 与边界代码；RecordingTransport 取 adapter 的 max_response_bytes，产品 identity 不动；三个最终 source hashes；本目录 Handoff/通信；静态检查/未测试事实、首轮 Root ERROR与修正后待复测，以及版本/兼容/source闭包/预算/具名接受与 memory 待应用事项。此后停止本片段，不运行任何测试或 API。

路径规范化后的发送原文：

> 接续用户授权的主准备窗口同步：CHAIN-DEV4-007 已完成并停止该有界片段。parser/Schema 只将 max_output_tokens 可声明域改1..1024；旧默认/已发布Profile bytes/Registry/config均未改。原257拒绝边界改1025，补数值边界与256 Profile请求257 preflight拒绝代码。
> 已按你的实测反馈修正测试 transport：RecordingTransport.max_response_bytes 精确取 adapter.transport.max_response_bytes，未修改产品 transport identity；send进入则记录并失败。最终测试源 sha256=bdc581e8283ad1e9353e0843b0cac9d3b20c6ffd73fc615060ad4b775f6efd02；parser=70c259e096d82124823d9313df75359ac72f62c8a7960307e7b8ff63f0a4e652；Schema=5d097d2b75db1d931005cc623de4d5a10ca1f6e3a0db7ff65f4533d14725bec0。
> 交接位于 docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/DEV4_PROFILE_HANDOFF.md；同目录 DEV4_PROFILE_COMMUNICATIONS.md 保留可见消息及你的首轮31 tests/1 ERROR/1 skipped反馈，修正后结果待你复测。
> 仅AST/内存compile、Schema JSON syntax/MD链接静态检查；未测试/API/Tool/Key/账/预占/install/Git mutation/primary memory。Handoff说明版本/兼容/消费方/原子集成顺序、需重新核source closure和budget/body guard及memory待应用条目。黄毅API、路诚钺预算接受仍待，不宣称live通过。

## Root 第二次更正与最终纯 wire 范围

Root 原文：

> Root第二轮31 profile checks中新增请求边界仍1 ERROR：这次构造Provider触发 actual Provider component method was replaced，因为该TestCase setUp已经patch EnvironmentCredential.resolve/available，核心binding正确拒绝Mock方法。请不要放松source binding；此边界最小改为当前纯 encode_profile_request(request257, profile256) 实际拒绝并assert原resolve_mock/available_mock零调用，不构造ConfiguredProvider/不用RecordingTransport。Root独立budget适配测试已实际覆盖known/unknown/授权先于credential，SDK构造适配在另组真方法fake端口验证。把用例名称/交接范围准确写成纯profile wire admission，其他owned源不扩展。静态后hash停，Root复跑。

可见更新：

> 第二次失败来自现有 TestCase 对凭据方法的 patch，触发了真实 source binding 检查。我会按 Root 指定把用例收窄为纯 profile wire admission，移除 Provider 构造和 transport，并据此更新交接范围。

最终用例名 `test_profile_wire_admission_256_rejects_request_257`；源码 SHA-256 `59d1d8e42168258aebdff62607977134542254f95226f804688436e43c576983`，只有 AST/内存 compile 通过。该更正消息跨过原十分钟时限，仅完成其指定测试收窄/必要交接即停，没有继续实现额外 consumer。

向同一主准备窗口同步并获工具确认：

> 按你的第二轮更正，边界测试已改为 test_profile_wire_admission_256_rejects_request_257：直接 encode_profile_request(request257, profile256)，assert ProviderError INVALID_REQUEST 与 resolve_mock/available_mock 零调用，不构造ConfiguredProvider、不用transport，不改任何binding/codec。静态AST/compile通过。另有需你复测的具体风险：我窄读当前 wire_codecs._validate_request，给preflight构造的ProviderCapabilities并没有传入profile limits；因此不能静态宣称纯wire已按每Profile声明拒绝257。该回归可能暴露纯codec缺口，若确实失败，需要你另行处理codec范围，本片段不扩大ownership。parser/Schema已1..1024，源码pins不变，handoff现在更新最终纯wire范围及此缺口，随后停止。
