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
| [0020](0020-PHASE-D-DUAL-TRANSPORT-SYSTEM-ESTIMAND.md) | Accepted | Phase D 显式双传输与系统级 estimand 解释上限 |
| [0021](0021-CURATED-DEVELOP-TO-MAIN-RELEASE.md) | Accepted | 从 develop 确定性生成精选 main 发行视图 |
| [0022](0022-SINGLE-PR-MAINTAINER-REVIEW-EXCEPTION.md) | Accepted by named maintainer | Reviewer 不可用时的单次维护者审核例外与独立硬门禁 |
| [0023](0023-DEVELOPMENT-WITHOUT-PERSON-ASSIGNMENTS.md) | Human-authorized direction；机器同步待 M0-008 | 取消固定开发人员分工和指定人员审核前置，保留功能权威与硬门禁 |
| [0024](0024-UNIFIED-ENTRY-AND-SHORT-TASK-ROUTING.md) | Proposed for PR141；尚未实现 | 既有研究主线外的入口层与 Guide/短程分支；角色规则承载判断 |
| [0025](0025-USAGE-RECORDING-AND-MODEL-WORKING-INPUT.md) | 2026-10-10 人类授权方向；本 PR 审阅，迁移未实现 | 实际用量记录、无通用经济配额及模型工作输入分离 |

`0017` 原文件曾与 Assignment Handoff 决定重复使用编号 `0005`；2026-08-22 只修正文件名和标题，Git 历史保留原路径与内容关系。

ADR 正文是历史决定及其接受状态的记录；本索引不替未完成的正式接受补签。
0012/0022 的人员开发限制由 0023 的最新人类指令取代；历史原文及接受事实保留，机器/远端同步不由文档自报完成。
当前执行边界以 [Architecture](../ARCHITECTURE.md) 的 Bundle → View → Thin Host 为准；ADR-0010 的 API isolation
路径属于可选 Adapter 实现，不要求每个运行平台使用纯 API。现行贡献/合并规则及其源码政策见
[Development](../DEVELOPMENT.md)；ADR-0018 的 Proposed 状态不应被误读为当前治理器没有规则。
