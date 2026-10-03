# FOLLOWUP-022：保留历史的累计扩限与有界等待

用户于 2026-10-03 直接授权累计最多十组 Attempt，包含已用三组，成功/失败 input+output 上限仍为
10,000,000。每组最多三次调用、一次纯 Tool、每次 output256、失败即停；诊断、离线修复、重新
冻结后才建立 fresh Attempt。只用官方精确 Flash、合成输入，北京时间18:00后与官方闲时窗同时满足。
费用不可得记录 unknown，未知 tokens 保留预占并停止。权威源为用户原文；本记录不认证人类身份。

实施范围：显式单次 attempt-limit-grant、保留 header/meta/namespace/identity/旧事件，accounting1.1、
必需绑定的 report1.2 冷读；共享360秒候选与各阶段剩余 deadline。旧默认三组/120秒/报告版本保留。
下一次 socket180、外层600/teardown605 是执行选择，实际安装、配置、helper、Windows context 与
源引用必须重新冻结。不得仅改启动参数重跑原入口或替换真实预算历史。

Root 负责实施整合、预算授权记录、统一验证、进度与 draft PR；黄毅仍是 Provider/Session 责任人。
委派 profile 为 conformance-budget-extension implementer 和 independent conformance reviewer，
required Skills=[]；输入仅仓库指导、相关 PLAN、预算设计、直接产品/Schema/test消费者及本地证据。
作者仅改预算、报告与直接测试；Root 改 driver/deadline、CI和文档；独立复核者只写本地 review 输出。
各次有界委派25/12/8分钟，到期保留partial、失败与capture gap；禁止真实 API/密钥/真实预算操作。

输出为可审查的产品候选、正负合成回归、风险及 [CHECKS](CHECKS.md)/[HANDOFF](HANDOFF.md)。
本次未迁移真实账本、未新增真实调用；完整 M6-010 保持 BLOCKED。旧三组1205tokens与四份成功响应
原样保留，Schema 尚未发出。停止条件是未闭合绑定、未知用量、持久化/anchor漂移、容量或deadline耗尽。
没有具名 Task/run 接受、remote strict、M5 Pilot/A4/science/release 权威。
