# 通用 Provider 离线实现候选

本目录记录 M6-009 的隔离实现候选。定义来自 [PR #125](https://github.com/Chengyue-Lu/research-agent-workbench/pull/125)，
传输安全维护来自 [PR #126](https://github.com/Chengyue-Lu/research-agent-workbench/pull/126)；两项已分别按用户直接定义接受、正式cross-owner批准合入develop，本实现候选已更新到该基线。
离线基础已在 [PR #127](https://github.com/Chengyue-Lu/research-agent-workbench/pull/127) 获正式 cross-owner 批准，
正常合入 develop `27cbf860e48e9639bd3af32a58c12bfd88d87526`。M6-009 保持 IN_PROGRESS。
后续实现仍须独立 R2 审核；基础合入不构成整项完成或真实调用资格。
Provider/Session 维护者仍为黄毅，路诚钺协调准备及共享语义复核。Agent 结果仅为可审查的技术证据。

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
内核的 guard 和输入上界仍由调用者声明，源码回执仅覆盖新模块，transport entry 只证明委托方法入口。
后续 [FOLLOWUP-002](attempts/FOLLOWUP-002/TASK.md) 加入显式 retained anchor，检测预算历史单边回退、
同 anchor 换 DB 和未知提交状态；默认无 anchor 的旧语义保留。实际唯一预算选择、完整运行
source/config/helper/Windows/time 闭包、输入预占依据接受与具名运行接受继续待定；
当前没有 M6-009 DONE 或 M6-010 真实调用提议。
后续 [FOLLOWUP-003](attempts/FOLLOWUP-003/TASK.md) 实现上述源码图消费者及显式
ConformanceBodyPolicy：沿用已有 Flash Responses nonthinking，credential 前检查 ModelRequest，
intent 前检查实际 body；三个 local phase 固定 Tool/call ID/history/result、Schema 和大小上限。
默认 None 路径和既有报告保持兼容；驱动、报告及真实运行上下文的整合接受仍待后继完成。

安装版可读取默认禁用配置并输出离线计划：

```powershell
rwb providers profile-conformance --config <adapters-v2.json> --adapter <adapter-id> --output <new-plan.json>
```

profile 引用默认相对安装资源目录；独立配置可显式传入 `--root`。
安装资源另提供 `registry/providers/text-adapters-v2.disabled.json`，包含上述三家 Text-only 模板；
全部禁用，Text-only 不满足三调用 Tool/Schema conformance 计划的能力要求。
禁用或缺少能力时退出 1；提供显式 enabled/config/capabilities 只使计划结构 ready，
仍然 `live_qualified=false`。没有执行开关。报告 writer 验证独立 1.0.0 闭集 Schema，
只新建输出文件，保留失败后的已知用量；累计账本不可读时保留每轮事实并标为 blocked。

入口：[Task](attempts/CANDIDATE-001/TASK.md)、[检查](attempts/CANDIDATE-001/CHECKS.md)、
[交接](attempts/CANDIDATE-001/HANDOFF.md)、[风险](RISK_LEDGER.md)。
后续检查和交接见 [FOLLOWUP-001 检查](attempts/FOLLOWUP-001/CHECKS.md)
及 [FOLLOWUP-001 交接](attempts/FOLLOWUP-001/HANDOFF.md)；早期候选检查保留原 source 身份。
最新检查见 [FOLLOWUP-003](attempts/FOLLOWUP-003/CHECKS.md)，历史检查见
[FOLLOWUP-002](attempts/FOLLOWUP-002/CHECKS.md)，逐厂商字段事实与待核项见
[官方字段覆盖表](../M6-GENERAL-PROVIDER-DEFINITION/OFFICIAL_FIELD_COVERAGE.md)。
预算及真实测试边界沿用 [定义计划](../M6-GENERAL-PROVIDER-DEFINITION/PLAN.md)：
用户累计输入＋输出上限 10,000,000 tokens，所有失败同计，只用 Flash，北京时间 18:00 后及官方空闲时窗。
预算是停止上限，不是消耗目标。

费用、币种或账单不可得时记录 unknown，不作为停止条件；未知 token 用量仍保留预占并停止。
