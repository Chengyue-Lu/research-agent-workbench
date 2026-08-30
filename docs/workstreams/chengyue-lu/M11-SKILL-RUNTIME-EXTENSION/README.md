# M11 Skill Runtime Extension

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 风险：R2 Capability / Skill Evolution → Runtime publication boundary
- 开发基线：`develop@97fa2455c983dc65e66a782bac8d272eed32c633`
- 分支：`agent/m11-skill-runtime-extension`
- Task：`M11-005`、`M11-006`

## 目标

本 workstream 只补上 ADR-0019 已接受的可选 Skill-bearing seam：

```text
accepted immutable Skill Release
  + externally verified Lifecycle eligibility
  + named Human Admission decision
        ↓ deterministic publisher
SkillReleaseProjection
        ↓ factual mapping
Capability Supply Report
        ↓ existing Capability Resolver
Capability Resolution → Snapshot → Resolved Execution View → Thin Host
```

M11-005 负责发布窄、不可变、hash-pinned 的 `SkillReleaseProjection`。M11-006 只允许该投影成为
统一 Supply/Resolution/Snapshot/View 路径的一种候选来源；它不增加 Skill-specific dispatcher、session、
fallback、Host 分支或新的 selection authority。

当前三个 accepted Skill 都是 historical replay only。本 workstream 不重新准入它们，也不制造真实
科研增量证据；生产 projection index 因而可以合法为空。正向契约由 synthetic bounded Release、外部
evidence resolver 与 Human-decision resolver 证明。

## 实施切片

### M11-005 — SkillReleaseProjection

- 定义 projection 与 integrity index Schema；
- Release 必须 exact-pin Skill ID/version、manifest path/hash、package hash；
- publisher 必须重验 Lifecycle current/new-binding、外部 evidence、named Human decision 与 manifest；
- projection 只保留 capabilities、I/O、依赖/compatibility、permission/data-egress/side-effect ceiling、
  runtime scope 与最小 admission provenance；
- Need、Candidate、Trial/Evaluation 结果、metric、deliberation 与完整 Lifecycle history 不进入 projection；
- published identity append-only；missing/stale/mismatch 一律 fail closed；
- 不发布任何现有 legacy Skill 的可执行 projection。

### M11-006 — unified Skill supply mapping

- Skill Supply Report exact-pin projection identity/path/hash；Runtime qualification 不读取 Lifecycle；
- projection facts 必须等于 Supply identity、capability、I/O 与三类 boundary facts，Report 只能增加
  observation、conformance、availability、limits 和 limitations；
- Capability Resolver 继续是唯一 selector；projection eligibility 不等于 permission 或 execution grant；
- Runtime Bundle 仅在 `skill_extension.enabled: true` 时把 exact projection 加入显式 closure；
- zero-Skill/no-Skill/direct Tool Core 的 manifest、loader 与 View/Host 语义保持不变；
- View、Host、Trace 与 Receipt 继续消费同一个 supply-neutral frozen binding，不增加 Skill 分支。

## 原子边界

本阶段允许在一个 module-level PR 中按 `M11-005 → M11-006` 提交两个独立 implementation slice 和
task-specific evidence，但不改写 Task identity、dependency 或 acceptance。当前实现分支不额外创建
状态解锁 PR；Task 状态的最终 closeout 仍由 merge-boundary governance 与具名 owner 决定。

## 明确非目标

- 准入、升级或恢复任一真实 Skill；
- 设计新的 benchmark、trial runner、Evaluation Record 或 Human Decision system；
- Runtime 自动创建 Need/Candidate/Projection；
- fallback、reselection、model routing、multi-Agent、Topic 5 recovery；
- Provider SDK、API session、credential、live conformance；
- 修改 Method、Claim、Gate、Human authority 或 permission grant 语义。

## 验证计划

- M11-005：publisher/registry positive + missing evidence/decision、legacy/ineligible、hash/path/fact drift、
  forbidden history fields 与 append-only governance negative tests；
- M11-006：projection→Supply deterministic mapping、runtime eligibility、Requirement/Resolution/Snapshot closure、
  missing/stale/mismatch projection candidate fail-closed、zero-Skill regression 与 Runtime import-graph tests；
- 新增 authority-sensitive validator 纳入 Coverage Policy，提供独立 positive/negative evidence；
- focused tests 后运行 full behavioral suites、coverage-quality、repository validation、governance 与 package smoke。
