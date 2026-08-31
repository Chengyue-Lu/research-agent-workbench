# M11 Skill Runtime Extension

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 风险：R2 Capability / Skill Evolution → Runtime publication boundary
- 当前 rebase 基线：`develop@ad038bdd35316718a88a2513886f1831763203bd`
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
- projection facts 必须闭合 Supply identity、required Tool dependencies、capability、I/O 与三类 boundary
  facts；permission roots 与 data-egress forbidden set 不能在粗粒度 policy 相同的情况下被静默放宽，Report 只能增加
  observation、conformance、availability、limits 和 limitations；
- Capability Resolver 继续是唯一 selector；projection eligibility 不等于 permission 或 execution grant；
- Runtime Bundle 仅在 `skill_extension.enabled: true` 时把 exact projection 加入显式 closure；
- zero-Skill/no-Skill/direct Tool Core 的 manifest、loader 与 View/Host 语义保持不变；
- View、Host、Trace 与 Receipt 继续消费同一个 supply-neutral frozen binding，不增加 Skill 分支。

## 原子边界

本阶段允许在一个 module-level PR 中按 `M11-005 → M11-006` 提交两个独立 implementation slice 和
task-specific evidence，但不改写 Task identity、dependency 或 acceptance。当前实现分支不额外创建
状态解锁 PR；本 PR 以 `M11-005 READY → DONE` 为 anchor，并按 dependency DAG 原子完成
`M11-006 PARKED → DONE`。两项 Task 仍分别保留 implementation slice、commit 与验收证据。

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

## 当前实现证据

### M11-005 slice — `3c4b407`（rebase 后）

- projection/index Schema、空生产 index、publisher、runtime-minimal reader、closed validator 与 published
  identity policy 已实现；
- synthetic verified Release 可确定性发布；legacy、缺 evidence/decision/runtime boundaries、index/hash/
  provenance/fact drift 均 fail closed；
- 首轮 focused：projection 5/5、Lifecycle 7/7、catalog 6/6、Schema 3/3、Governance 67/67 PASS；repository
  validation exit 0；首个 hosted coverage artifact 暴露新 producer/validator 分支不足后，projection suite
  已扩展为 8/8，并加入 index/publisher/registry adversarial matrix。

### M11-006 slice — `e8b9dee`（rebase 后）

- Skill Supply identity 支持 exact projection ref；旧 Lifecycle pair 只保留 structural/history 兼容；
- `runtime-execution` 只接受 projection eligibility，Lifecycle callback 不能授权；
- pure projection→Supply checker 闭合 Release identity/component/required Tools、capability/I/O 与
  permission（含 roots）/egress allow+forbid/effect ceiling；
- Runtime Bundle 在 `skill_extension.enabled:true` 时增加唯一 projection 与 `supply-projection` edge；
- synthetic Skill 已通过同一 Resolution→Snapshot→View→Host 单次执行路径；View/Host 源码没有 projection
  或 Skill-specific dispatcher；
- optional Supply roots 进入现有 View permission intersection；未声明 roots 的 Core Report 继续使用 Task
  roots，没有建立 Skill-specific View 字段；
- focused：Skill extension 6/6、Capability Resolution 18/18、Runtime Bundle 12/12、Execution View 9/9、
  Schema 3/3 PASS；Governance 67/67、Coverage Policy self-tests 21/21 与 repository validation PASS；
- 本地 authoritative full behavioral suite：781 tests / 634.437s，PASS（4 个环境特定 skip）；
- 首个 hosted run `33333387290`：Python 3.11/3.13 behavioral、package-smoke、governance PASS，global line
  90.91%；Coverage Policy 正确阻断三个新 critical module 的逐文件不足。补测后 projection + Skill Runtime
  extension 14/14 focused PASS；该 run 属于 rebase 前历史证据，不能替代当前 exact-head Gate。

### R2 review remediation — current PR head

- 唯一 canonical Projection Index 现在只恢复一次 repository root；Accepted Registry、Lifecycle Index/record、
  Projection、Evaluation、Decision、baseline/trial/promotion evidence 与 Manifest 均以该 root 做 portable
  repository-relative exact lookup，不再从 evidence 所在路径反推 root，也不再接受 suffix-first、路径逃逸或
  多个 exact alias；
- aggregate `LoadedDocuments` 负例已覆盖完整 authority closure 移入 `shadow/`、两个同名 shadow closure，
  以及 shadow Index + 真实 Registry 对象 + shadow evidence 的 cross-root stitched closure；三者均 fail closed，
  且不是由 Projection hash/provenance/derivation drift 替代性触发；
- repository publication validator 不再信任 Lifecycle 中的非空引用或仅调用
  `eligible_for_new_binding()`：它会解析真实 `skill_evaluation`，重放 baseline/with-Skill evidence closure，
  并验证与 evaluation/candidate/accept outcome 绑定的 named Human Decision；将全部引用替换为
  `MISSING-*` 且同步重算 Lifecycle/Projection/Index hash 仍会 BLOCK；
- `SkillReleaseProjectionSet.load()` 在返回 Runtime-facing catalog 前完整验证 index/projection Schema；未知
  index 字段、nested `evaluation` / `private_score` / `need_text` 与缺失 boundary 均 fail closed；
- 撤销 Capability Requirement v0.1 中未参与 comparison/View intersection 的 `allowed_roots`；Supply roots
  继续由 Projection ceiling 与 final View intersection 约束；
- focused projection suite：14/14 PASS；shadow/exact-root authority closure focused 4/4 PASS；
  Requirement/Skill Runtime/Schema boundary 20/20 PASS；本地 Python 3.14 full behavioral 788/788 PASS
  （4 skipped，713.611s）；本轮 repository validation 为 183 documents、0 errors、0 warnings，Coverage Policy
  与 Governance focused 88/88 PASS；当前 exact-head Python 3.11/3.13、coverage-quality 90/95/90、
  package-smoke、governance 与 aggregate hosted evidence 在推送后重新生成。
