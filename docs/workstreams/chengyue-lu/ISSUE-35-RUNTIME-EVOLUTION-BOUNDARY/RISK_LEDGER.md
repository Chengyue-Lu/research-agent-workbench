# ISSUE-35 Risk Ledger

| ID | 类型 | 风险 | 控制 | 当前状态 |
|---|---|---|---|---|
| I35-RUNTIME-READ-001 | fact | Runtime 递归读取 Need/Candidate/Evaluation/Lifecycle，使普通执行依赖 Evolution 并扩大隐私、上下文和故障面。 | 当前 loader 明确定性为 `maintainer-full` helper；future `runtime-bundle` 只接受显式最小闭包并有 import-graph test。 | boundary proposed；implementation deferred |
| I35-PROJECTION-TRUTH-001 | inference | SkillReleaseProjection 变成可写的第二套 Registry，与 Admission/Lifecycle 真值漂移。 | projection 只能由不可变 Release 确定性派生；exact identity/hash；publisher regression；Runtime 不可回写。 | boundary proposed；publisher deferred |
| I35-AUTHORIZATION-001 | fact | eligibility、Supply Report 或 Snapshot 被误作 permission grant。 | Authority Basis 固定 metadata-only ceiling；最终权限由 Resolved Execution View 计算收紧交集。 | controlled by R2 review；Runtime enforcement deferred |
| I35-DIAGNOSTIC-001 | fact | gap/failure 自动升级为 Skill Need，或 Diagnostic 自动上传造成隐私泄露和自批准演化。 | Diagnostic 默认本地、脱敏、consent-gated；不是 Need；具名 Maintainer 必须重新 triage。 | boundary proposed；feedback bridge PARKED |
| I35-NOSKILL-001 | fact | no-Skill/direct Tool 仍被 Skill Assignment、Lifecycle 或 Release Projection 阻塞。 | Runtime bundle 与 Execution View 验收要求零 Skill/零 Evolution；Skill projection 只约束 Skill-bearing path。 | implementation deferred to Topic 4 |
| I35-SNAPSHOT-DRIFT-001 | fact | Release/Registry 更新静默改变运行中供给或权限。 | exact version/hash pin；供给变化必须创建新 Resolution/Snapshot/View；active/latest selector 禁止进入 frozen input。 | boundary proposed；tests deferred |
| I35-COMPAT-001 | fact | 为解耦重写 v0.1 Method→Need、Lifecycle v2 或 PR #33 fixture，破坏 exact replay。 | Issue #35 docs-only；旧 Schema/Registry/fixture 原字节不变；只增加 consumer-profile 澄清。 | controlled by diff allowlist and full validation |
| I35-OVERCLAIM-001 | fact | docs-only ADR 被误写成 Runtime、Release publisher 或 telemetry 已实现。 | STATUS/TASKS 不变；workstream 和 implementation docs 显式列出 deferred implementation 与未证明内容。 | controlled by documentation review |
| I35-OWNER-001 | fact | 任一 owner 单方面把自己的结构资格或实现便利升级为跨域 authority。 | R2 cross-owner acceptance、CODEOWNERS、Authority Basis 与 ADR final-diff reconfirmation。 | open until both owners accept |
