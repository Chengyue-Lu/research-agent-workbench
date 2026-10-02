# 通用 Provider 离线实现候选

本目录记录 M6-009 的隔离实现候选。定义来自 [PR #125](https://github.com/Chengyue-Lu/research-agent-workbench/pull/125)，
传输安全维护来自 [PR #126](https://github.com/Chengyue-Lu/research-agent-workbench/pull/126)；当前不构成具名接受、Task 完成或真实调用资格。
Provider/Session 维护者仍为黄毅，路诚钺协调准备及共享语义复核。Agent 结果仅为可审查的技术证据。

候选实现分离闭集配置、真实服务身份、四个协议编解码、晚解析凭据及实际源码绑定。
新配置默认禁用；原三家 facade、配置版本、ModelProvider Port 和默认 Session 行为保留。
新绑定进入独立 manifest 及 baseline envelope 1.1，旧 1.0 保持原闭集语义。
显式 conformance Session 政策只允许同 Session 的两轮 specific → 成功 Tool result → none。
这条政策采用独立的隐私摘要 sink，仅发送闭集计数和状态；原默认 Session/Trace 路径保留。

协议层的合成文本路径已覆盖九家；新工厂当前准许其中八家进入离线 fake 传输。
Google 模板的 Gemini2.0 Flash 已被官方关闭，新工厂在凭据前拒绝；其既有字节仅作历史形状/回放。
SiliconFlow 的精确模式和 OpenRouter 的网关绑定也仍阻断，
因此不能把十一份模板称为十一家完整可运行接入。新 probe、报告/CLI、跨 probe 调用账本、
安装后的 profile 资源及端到端报告集成仍需后续切片；当前没有 M6-009 DONE 提议。

入口：[Task](attempts/CANDIDATE-001/TASK.md)、[检查](attempts/CANDIDATE-001/CHECKS.md)、
[交接](attempts/CANDIDATE-001/HANDOFF.md)、[风险](RISK_LEDGER.md)。
预算及真实测试边界沿用 [定义计划](../M6-GENERAL-PROVIDER-DEFINITION/PLAN.md)：
用户累计输入＋输出上限 10,000,000 tokens，所有失败同计，只用 Flash，北京时间 18:00 后及官方空闲时窗。
预算是停止上限，不是消耗目标。
