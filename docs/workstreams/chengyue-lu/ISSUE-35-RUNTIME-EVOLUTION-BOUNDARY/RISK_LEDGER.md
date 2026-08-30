# ISSUE-35 Risk Ledger

| ID | 类型 | 风险 | 控制 | 当前状态 |
|---|---|---|---|---|
| I35-RUNTIME-READ-001 | fact | Runtime 递归读取 Need/Candidate/Evaluation/Lifecycle，使普通执行依赖 Evolution 并扩大隐私、上下文和故障面。 | repository-wide loader 定性为 `maintainer-full` helper；M11 Runtime Bundle 只接受显式最小闭包并有 import-graph test。 | controlled by M11-001 bounded Core |
| I35-PROJECTION-TRUTH-001 | inference | SkillReleaseProjection 变成可写的第二套 Registry，与 Admission/Lifecycle 真值漂移。 | projection 只能由不可变 Release 确定性派生；exact identity/hash；publisher regression；Runtime 不可回写。 | boundary accepted；publisher deferred |
| I35-AUTHORIZATION-001 | fact | eligibility、Supply Report 或 Snapshot 被误作 permission grant。 | Authority Basis 固定 metadata-only ceiling；Resolved Execution View 只计算并冻结最严交集，不创造 permission grant。 | bounded enforcement controlled by M11-002/003；external permission authority remains separate |
| I35-DIAGNOSTIC-001 | fact | gap/failure 自动升级为 Skill Need，或 Diagnostic 自动上传造成隐私泄露和自批准演化。 | Diagnostic 默认本地、脱敏、consent-gated；不是 Need；具名 Maintainer 必须重新 triage。 | boundary accepted；feedback bridge PARKED |
| I35-NOSKILL-001 | fact | no-Skill/direct Tool 仍被 Skill Assignment、Lifecycle 或 Release Projection 阻塞。 | Runtime Bundle 与 Execution View 验收要求零 Skill/零 Evolution；Skill projection 只约束 Skill-bearing path。 | controlled by M11 Core; optional Skill extension remains PARKED |
| I35-SELECTION-OWNER-001 | fact | Resolver 与 Execution Host 同时拥有 Supply selection/replanning authority，导致 frozen Snapshot 内隐式 rebinding 或 fallback。 | Research Control / Capability Resolver 是唯一 selection owner；Host 只消费 exact frozen View，失败时只能请求 new Resolution/Snapshot/View。 | controlled by M11-002/003 adversarial tests |
| I35-CORE-EXTENSION-001 | fact | SkillReleaseProjection 被设为 Topic 4 Core 全局前置，使可选 Evolution 再次阻塞 no-Skill/direct Tool/Adapter 路径。 | Runtime Bundle/Profile 单独 Gate Core；Projection 只 Gate Skill-bearing extension，缺失时仅 Skill new-binding fail closed。 | Core controlled by M11-001～004；publisher/mapping deferred |
| I35-SNAPSHOT-DRIFT-001 | fact | Release/Registry 更新静默改变运行中供给或权限。 | exact version/hash pin；供给变化必须创建新 Resolution/Snapshot/Bundle/View；active/latest selector 禁止进入 frozen input。 | bounded Core controlled by M11 closure/freshness tests |
| I35-COMPAT-001 | fact | 为解耦重写 v0.1 Method→Need、Lifecycle v2 或 PR #33 fixture，破坏 exact replay。 | Issue #35 docs-only；旧 Schema/Registry/fixture 原字节不变；只增加 consumer-profile 澄清。 | controlled by diff allowlist and full validation |
| I35-OVERCLAIM-001 | fact | docs-only ADR 被误写成 Runtime、Release publisher 或 telemetry 已实现。 | PR #36 与后续 M11 evidence 分开；Core、live Provider、publisher 与 telemetry 的成熟度分别声明。 | controlled by post-integration documentation review |
| I35-OWNER-001 | fact | 任一 owner 单方面把自己的结构资格或实现便利升级为跨域 authority。 | R2 cross-owner acceptance、CODEOWNERS、Authority Basis 与 ADR final-diff reconfirmation。 | architecture accepted and PR #36 closeout complete |
