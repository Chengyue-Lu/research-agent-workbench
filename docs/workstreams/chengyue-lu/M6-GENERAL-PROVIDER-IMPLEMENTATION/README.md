# 通用 Provider 离线实现候选

本目录记录 M6-009 的隔离实现候选。定义来自 [PR #125](https://github.com/Chengyue-Lu/research-agent-workbench/pull/125)，
传输安全维护来自 [PR #126](https://github.com/Chengyue-Lu/research-agent-workbench/pull/126)；两项已分别按用户直接定义接受、正式cross-owner批准合入develop，本实现候选已更新到该基线。
M6-009进入IN_PROGRESS；本实现仍待独立R2审核，不构成Task完成或真实调用资格。
Provider/Session 维护者仍为黄毅，路诚钺协调准备及共享语义复核。Agent 结果仅为可审查的技术证据。

候选实现分离闭集配置、真实服务身份、四个协议编解码、晚解析凭据及实际源码绑定。
新配置默认禁用；原三家 facade、配置版本、ModelProvider Port 和默认 Session 行为保留。
新绑定进入独立 manifest 及 baseline envelope 1.1，旧 1.0 保持原闭集语义。
显式 conformance Session 政策只允许同 Session 的两轮 specific → 成功 Tool result → none。
这条政策采用独立的隐私摘要 sink，仅发送闭集计数和状态；原默认 Session/Trace 路径保留。

十二份 profile 覆盖十一家身份；工厂有九家离线 fake 正例。Google 新增独立的 Gemma Text-only profile，
历史 Gemini2.0 Flash 仍在凭据前拒绝。SiliconFlow 的精确模式和 OpenRouter 的网关绑定保留阻断，
所有正例只证明合成传输路径。进程内 ledger 和 SQLite 持久 journal 保留失败及未知用量；
新 probe、报告/CLI、实际 send 观测、唯一预算文件与完整 source pins、安装后的 profile 资源
及端到端报告集成仍需后续切片；当前没有 M6-009 DONE 提议。

入口：[Task](attempts/CANDIDATE-001/TASK.md)、[检查](attempts/CANDIDATE-001/CHECKS.md)、
[交接](attempts/CANDIDATE-001/HANDOFF.md)、[风险](RISK_LEDGER.md)。
预算及真实测试边界沿用 [定义计划](../M6-GENERAL-PROVIDER-DEFINITION/PLAN.md)：
用户累计输入＋输出上限 10,000,000 tokens，所有失败同计，只用 Flash，北京时间 18:00 后及官方空闲时窗。
预算是停止上限，不是消耗目标。

费用、币种或账单不可得时记录 unknown，不作为停止条件；未知 token 用量仍保留预占并停止。
