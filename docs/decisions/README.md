# Architecture Decision Records

ADR 保存已接受架构决定及其理由；当前系统说明仍以[总体架构](../ARCHITECTURE.md)为准。

| ADR | 状态 | 主题 |
|---|---|---|
| [0001](0001-NATIVE-RUNTIME-FIRST.md) | Superseded in execution priority by 0010；边界仍有效 | 原生 Runtime 优先、拒绝自建全局 Supervisor |
| [0002](0002-EXPLICIT-SKILL-BINDING.md) | Accepted | 显式 Agent / Skill 绑定 |
| [0003](0003-PROVIDER-NEUTRAL-MODEL-PORT.md) | Accepted | provider-neutral 模型端口 |
| [0004](0004-MINIMAL-DEPENDENCY-M1.md) | Accepted | 最小 Python 依赖 |
| [0005](0005-ASSIGNMENT-REFERENCE-IN-HANDOFF.md) | Accepted | Handoff 引用完整 Assignment |
| [0006](0006-CONTEXT-AND-EXECUTION-RECEIPTS.md) | Accepted | 上下文与执行收据 |
| [0007](0007-THIN-PROVIDER-ADAPTERS.md) | Accepted | 薄 Provider Adapter |
| [0008](0008-HANDOFF-TRANSFER-AUDIT.md) | Accepted；由 0011 限定触发范围 | Transfer Manifest 与有界审计 |
| [0009](0009-FILE-FIRST-CONTINUITY-AND-SAFE-PAUSE.md) | Accepted | 文件式连续性与安全暂停 |
| [0010](0010-API-FIRST-ISOLATED-EXECUTION.md) | Accepted | 隔离 API 执行基线 |
| [0011](0011-RISK-TIERED-HANDOFF-AND-CONTROLLED-READS.md) | Accepted | 风险分级 Handoff 与受控读取 |
| [0012](0012-NAMED-OWNERSHIP-AND-REPLAYABLE-AGENT-TRACE.md) | Accepted | 实名责任与可回放 Trace |
| [0013](0013-MODE-FIRST-SKILL-DERIVATION.md) | Accepted | Mode-first Skill Need |
| [0014](0014-PROJECT-INTERNAL-SKILL-LANE.md) | Accepted | 项目内生 Skill lane |
| [0015](0015-SKILL-LIFECYCLE-AND-EXACT-VERSION.md) | Accepted | Skill 生命周期与精确版本 |
| [0016](0016-METHOD-AWARE-RESEARCH-CONTROL-PLANE.md) | Accepted | 方法感知科研控制平面 |
| [0017](0017-SCOPED-WRITE-PERMISSIONS.md) | Accepted | 源只读、任务区受限写 |
| [0018](0018-RISK-BASED-DEVELOPMENT-GOVERNANCE.md) | Proposed | 基于风险的开发治理与共享真值边界 |
| [0019](0019-OPTIONAL-MAINTAINER-SKILL-EVOLUTION-OUTER-LOOP.md) | Accepted | Skill Evolution 作为可选 Maintainer 外环 |

`0017` 原文件曾与 Assignment Handoff 决定重复使用编号 `0005`；2026-08-22 只修正文件名和标题，Git 历史保留原路径与内容关系。
