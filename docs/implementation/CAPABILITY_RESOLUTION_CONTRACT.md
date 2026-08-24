# Capability Resolution and Snapshot Core

M9-005 Snapshot Core 在需求与执行之间固定以下单向关系：

```text
Capability Requirement
        ↓
Capability Supply Report(s)
        ↓ deterministic comparison
Capability Resolution
        ↓ satisfied + exact selected report
Resolved Capability Snapshot
        ↓ frozen execution input
Runtime consumer（本轮不实现）
```

本轮不建立全局供给 Registry，也不实现 Provider discovery、API session、Runtime consumer、自动 fallback
或模型路由。三个对象是 content-addressed 工件；调用方必须显式提供候选 Report。

## Supply Report

Supply Report 只陈述一个实际供给在一个 observation scope 内“报告能够做什么”：

- `no-skill`、direct `tool`、`adapter-provider`，以及为后续扩展保留但尚不可解析的 `skill`；
- exact implementation / component identity、version 与 content hash；
- provided capability、supported inputs / outputs；
- 所需 permission、data-egress behavior 与 side effects；
- deterministic / live conformance evidence、availability facts 与 limitations。

Report 不能选择自己，不能放宽边界，不能拥有 Method、fallback、Claim 或 Human Gate authority。
`available` 只在 Report 声明的 scope 内成立；当前 checked-in 报告全部是 `fixture-only`，不代表真实环境
已经安装 Tool 或 Provider。

## Capability Resolution

Resolver 对一个 Requirement 和零个或多个显式 Report 计算十类检查：capability、inputs、outputs、
required artifacts、permission、data-egress、side-effects、deterministic conformance、availability 与 Skill
runtime eligibility。

- 恰好一个 structurally eligible Report：`satisfied`，成为 Snapshot 候选；
- 没有合格供给且不存在越界尝试：`unsatisfied-gap`；
- 多个合格供给：`requires-decision`，不自动排序或 fallback；
- 没有合格供给且存在 permission / egress / side-effect 越界：`blocked`。

Repository validator 会重新计算 checks、status 与 selection；记录值不能自我声明。Resolution 固定
Method Resolution、Capability Requirement、Supply Report 与 Authority Matrix 的 path/hash，并验证该
Requirement 确实来自被引用的 Method Resolution。`satisfied` 只表示结构匹配，不证明语义正确、真实可用
或获准执行。

## Resolved Capability Snapshot

Snapshot 只能由 `satisfied` Resolution 形成，并原样冻结：

- Method Resolution 与 Requirement lineage；
- selected Supply Report 与 exact implementation/component identity；
- effective permission、data-egress、side-effect；
- conformance evidence refs。

Validator 会阻断 Resolution、Report 或 evidence hash 漂移，也会阻断复制后的 supply facts 与原 Report
不一致。Snapshot 是 Runtime 将来消费的执行输入，但不是 Method decision、permission grant、Claim effect、
Human decision 或 fallback authority。

Snapshot 记录 M8 Matrix 对 `skill-tool-binding / validate / deterministic-resolver` 所需的两个 asserted
facts：`capability-snapshot-frozen` 与 `permission-intersection-satisfied`。这只是后续 Authority Rule
Eligibility 的输入要求；它不证明 facts，不产生 authorization，也不替代 Human decision provenance。

## Skill Supply Extension

Schema 为 `skill` 供给要求 `skill_lifecycle_ref` 与 `runtime_eligibility_ref`。没有 lifecycle v2 检查器时，
resolver 将 eligibility 保持为 `unknown`；repository validator 会要求引用的 lifecycle record 同时满足
evidence-ready evaluation、Human accepted admission、current lifecycle 与 exact runtime eligibility。
不满足时给出 `CAPABILITY-SKILL-SUPPLY-NOT-ELIGIBLE`，且不会阻塞 no-Skill、Tool 和
Adapter/Provider Core。

## Replacement fixture

`examples/capability-resolution/` 包含三条 synthetic bounded chain：

- direct Tool `document-read`；
- Adapter/Provider `document-read`；
- no-Skill `research-contract-check`。

前两条保持 Task、Mode、Action、Method Resolution、Capability Requirement 以及三个 ceiling 全部不变，
只更换 Supply Report 并产生不同 Snapshot。它证明契约允许 provider/tool replacement，不证明真实 Provider
可用或端到端 Runtime 已实现。
