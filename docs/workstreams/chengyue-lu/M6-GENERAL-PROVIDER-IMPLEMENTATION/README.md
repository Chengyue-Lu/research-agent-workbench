# 通用 Provider 离线实现与验收

本目录记录 M6-009 的隔离实现候选。定义来自 [PR #125](https://github.com/Chengyue-Lu/research-agent-workbench/pull/125)，
传输安全维护来自 [PR #126](https://github.com/Chengyue-Lu/research-agent-workbench/pull/126)；两项已分别按用户直接定义接受、正式cross-owner批准合入develop，本实现候选已更新到该基线。
离线基础已在 [PR #127](https://github.com/Chengyue-Lu/research-agent-workbench/pull/127) 获正式 cross-owner 批准，
正常合入 develop `27cbf860e48e9639bd3af32a58c12bfd88d87526`。
[PR #128](https://github.com/Chengyue-Lu/research-agent-workbench/pull/128) 的后继合同和报告修复已按维护者
直接指令合入 `3e01158bbf6730bcd3089356e7e307cef4b857dc`；M6-009 的条款映射、当前源码验证与
直接接受来源见[整项收口](M6-009_COMPLETION.md)。离线完成与 M6-010 真实调用资格分别验证。
Provider/Session 维护者仍为黄毅，路诚钺协调准备及共享语义复核。Agent 结果仅为可审查的技术证据。

API 客户端与厂商协议映射的复用建议、Windows 辅助链测试对象及 PR #128 审核范围见
[客户端复用与审核范围](CLIENT_REUSE_REVIEW.md)。第三方 SDK 的选择、集成和兼容验证尚未完成，
没有作为当前通用离线合同或 Flash 首轮准备的新增门槛。

候选实现分离闭集配置、真实服务身份、四个协议编解码、晚解析凭据及实际源码绑定。
新配置默认禁用；原三家 facade、配置版本、ModelProvider Port 和默认 Session 行为保留。
原显式绑定采用 manifest1.0 / baseline envelope1.1。
新增 opt-in manifest1.1 / provider-binding-v3 / baseline envelope1.2，引用独立源码图；
源码图覆盖实际 roots 的 helper 与 package initialization，各次 use-boundary 和 cold replay 消费相同归档。
旧版本保持原闭集语义。源码图依赖明确的 compiler/native/dependency 信任边界。
显式 conformance Session 政策只允许同 Session 的两轮 specific → 成功 Tool result → none。
这条政策采用独立的隐私摘要 sink，仅发送闭集计数和状态；原默认 Session/Trace 路径保留。

十四份 profile 覆盖十一家身份；工厂有十一家离线 fake 正例。Google 使用独立的 Gemma Text-only profile，
SiliconFlow Qwen 和 OpenRouter GPT-4.1 Mini 新增独立 standard Text 路径。OpenRouter 固定
提供方限制、拒绝 fallback；未知上游端点/区域保持 unknown。历史 Gemini2.0 与原 SF/OR 阻断 profile 保留。
所有正例只证明合成传输路径。进程内 ledger 和 SQLite 持久 journal 保留失败及未知用量；
后续 [FOLLOWUP-001](attempts/FOLLOWUP-001/TASK.md) 补齐其余摘要异常处理、
固定合成 Tool/session/Schema 驱动内核、版本化脱敏报告、离线 CLI 与安装资源。
未选 binding 的旧内核保留两模块源码回执；guard 和输入上界仍由调用者声明，transport entry 只证明委托方法入口。
后续 [FOLLOWUP-002](attempts/FOLLOWUP-002/TASK.md) 加入显式 retained anchor，检测预算历史单边回退、
同 anchor 换 DB 和未知提交状态；默认无 anchor 的旧语义保留。实际唯一预算选择、完整运行
source/config/helper/Windows/time 闭包、输入预占依据接受与具名运行接受继续待定；
该阶段的待定事实按历史源保留；当前 M6-009 完成判断见整项收口，M6-010 尚无 live PASS。
后续 [FOLLOWUP-003](attempts/FOLLOWUP-003/TASK.md) 实现上述源码图消费者及显式
ConformanceBodyPolicy：沿用已有 Flash Responses nonthinking，credential 前检查 ModelRequest，
intent 前检查实际 body；三个 local phase 固定 Tool/call ID/history/result、Schema 和大小上限。
默认 None 路径和既有报告保持兼容。
后续 [FOLLOWUP-004](attempts/FOLLOWUP-004/TASK.md) 将实际驱动显式绑定到含 conformance roots 的
v3 manifest；这一选项要求固定 body policy 和真实 UrllibTransport 类型，合成测试在 native urllib
边界替代网络。实际 Provider 在 Attempt 前匹配所选 manifest，caller guard 返回后重新检查源码图，
拒绝编码后 helper 漂移。新报告 1.1 保存冻结的配置、manifest、完整源码图、body/session 政策、
输入预占上界及实际 Attempt ordinal；独立 reader 按归档引用派生同一闭包并核对已保留的该轮预占。
报告发布需要显式 archive root，只新建文件。无绑定调用继续产生 1.0 报告。
该证据不认证 caller guard 的全局状态、Windows 时间/环境、真实 socket 或账单；具名实现及运行接受仍待审核。

[FOLLOWUP-013](attempts/FOLLOWUP-013/TASK.md) 补齐 bound 1.1 报告的用量一致性：当前 Attempt
实际用量匹配对应持久回执，累计值核对全部历史调用，缓存/推理计数保持子集语义。
partial、未结算失败、最终 accounting 不可得及旧 1.0 回放保留原有事实；
篡改报告在发布前拒绝。检查与交接见 [CHECKS](attempts/FOLLOWUP-013/CHECKS.md)、
[HANDOFF](attempts/FOLLOWUP-013/HANDOFF.md)。

安装版可读取默认禁用配置并输出离线计划：

```powershell
rwb providers profile-conformance --config <adapters-v2.json> --adapter <adapter-id> --output <new-plan.json>
```

profile 引用默认相对安装资源目录；独立配置可显式传入 `--root`。
安装资源另提供 `registry/providers/text-adapters-v2.disabled.json`，包含上述三家 Text-only 模板；
全部禁用，Text-only 不满足三调用 Tool/Schema conformance 计划的能力要求。
禁用或缺少能力时退出 1；提供显式 enabled/config/capabilities 只使计划结构 ready，
仍然 `live_qualified=false`。没有执行开关。报告 writer 验证版本化闭集 Schema，
只新建输出文件，保留失败后的已知用量；累计账本不可读时保留每轮事实并标为 blocked。

入口：[Task](attempts/CANDIDATE-001/TASK.md)、[检查](attempts/CANDIDATE-001/CHECKS.md)、
[交接](attempts/CANDIDATE-001/HANDOFF.md)、[风险](RISK_LEDGER.md)。
后续检查和交接见 [FOLLOWUP-001 检查](attempts/FOLLOWUP-001/CHECKS.md)
及 [FOLLOWUP-001 交接](attempts/FOLLOWUP-001/HANDOFF.md)；早期候选检查保留原 source 身份。
最新检查见 [FOLLOWUP-004](attempts/FOLLOWUP-004/CHECKS.md)，历史检查见
[FOLLOWUP-003](attempts/FOLLOWUP-003/CHECKS.md) 及
[FOLLOWUP-002](attempts/FOLLOWUP-002/CHECKS.md)，逐厂商字段事实与待核项见
[官方字段覆盖表](../M6-GENERAL-PROVIDER-DEFINITION/OFFICIAL_FIELD_COVERAGE.md)。
预算及真实测试边界沿用 [定义计划](../M6-GENERAL-PROVIDER-DEFINITION/PLAN.md)：
用户累计输入＋输出上限 10,000,000 tokens，所有失败同计，只用 Flash，北京时间 18:00 后及官方空闲时窗。
预算是停止上限，不是消耗目标。

费用、币种或账单不可得时记录 unknown，不作为停止条件；未知 token 用量仍保留预占并停止。
