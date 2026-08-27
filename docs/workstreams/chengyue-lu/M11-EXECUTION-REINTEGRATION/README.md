# M11 — Execution Reintegration

- 协调责任人：路诚钺（GitHub `Chengyue-Lu`）
- Runtime 实现责任人：黄毅（GitHub `let778750-cpu`）
- 分支：`agent/m11-execution-reintegration`
- PR：单个 module-level feature PR，按 M11-001→002→003→004 逐层提交与独立验收
- 风险：R2 shared Runtime / Capability boundary
- 基线：`develop@6b16129c496c3a47a7d0d4ac3321cb8c0edd3b2d`

## 目标与顺序

本 workstream 在一个阶段 PR 中逐层实现 M11 Core，但不并行越过 dependency：

```text
M11-001 Runtime Bundle/Profile
→ M11-002 supply-neutral Resolved Execution View
→ M11-003 Thin Execution Host / actual facts
→ M11-004 generic Trace/Receipt linkage and Core Gate
```

每层必须先形成独立 commit、focused tests、负面证据和可复核输出，才进入下一层。PR 最终合并仍是
一个 R2 Stage closure，因此所有 DONE Task 必须有 task-specific evidence，dependency DAG 必须可拓扑证明。

本次单 PR 组织遵守 `DEVELOPMENT.md` 的稳定 module-level PR 规则：M11-001 是 READY 入口，外部 hard
dependency 已在 base 中 DONE，M11-002～004 从入口沿预定义 DAG 可达，四项各有独立 commit、实现切片
和具名证据。它不是人类豁免，只改变 integration/review unit，不修改 Task 定义、依赖、验收或任何
Runtime/Capability authority。

## 分层停止点

### M11-001

- 显式 closure manifest；只读取列出的 exact path/hash；
- 明确 `action-capability-slice`，同时暴露完整 Task capability demand 与当前 closed set；未闭合能力时不得声明 Task completion；
- 拒绝目录输入、root scan、未声明传递引用和 `structural-replay`；
- Runtime import graph 不包含 Skill Need/Candidate/Evaluation/Lifecycle validators；
- zero-Skill、零 Evolution Registry 的 no-Skill/direct Tool Core 可验证；
- 不产生 Resolved Execution View，不选择或替换 Supply。

实现证据（本阶段第一层）：

- Schema：`runtime-bundle-manifest.schema.json`；
- Runtime API：`research_workbench.execution.load_runtime_bundle()`；
- focused tests：`tests.test_runtime_bundle` 与 schema catalog tests；
- 正路径在临时 project root 中不创建 Registry，未声明坏文件不影响结果；
- 负路径覆盖 directory/hash/undeclared import/structural replay/import graph/identity/Supply-fact drift；
- repository validation：`validated=154 errors=0 warnings=0`；
- full unit suite：`Ran 438 tests ... OK (skipped=3)`；三个 skip 均为当前环境未安装 Hypothesis 的既有可选测试；
- 结论：M11-001 验收闭合，状态 `READY→DONE`；只解锁 M11-002 为 `READY`，尚未实现其 View 语义。

### M11-002

- 仅在 M11-001 证据闭合后开始；
- 从 frozen selection 形成 supply-neutral View，并计算最严 policy intersection；
- 不执行、不 fallback、不依赖 SkillReleaseProjection。

实现证据（本阶段第二层）：

- Schema：`execution-binding`、`execution-policy`、`resolved-execution-view`；
- producer：`produce_resolved_execution_view()` 只消费 M11-001 bundle 与四个 explicit pins；
- exact binding：Provider/Adapter/Model/Runtime/Host ref/version/config hash 全部冻结；
- deterministic preflight：external bundle/input pins、Profile identity、Supply selection、availability、typed
  evidence、execution-time freshness 与 policy intersection fail closed；
- final narrowing：Profile 的 Tool capability/output contract/Model class-slot-capability 与 Host policy 的 exact
  Host subject 都必须覆盖最终 Binding；View 冻结三组 freshness windows；
- Profile Tool allowlist 只作用于真实 Tool Supply；final intersection 后必须反证 selected Supply 的
  permission/data-egress/side-effect operating boundary 仍可满足；
- focused negative tests：Supply reselection、Profile/hash drift、tool/output/model/host-subject mismatch、
  stale/unavailable、disjoint write roots、bundle pin drift；source test 禁止 execution/fallback/Skill Evolution imports；
- focused governance/runtime/view/schema tests：`Ran 81 tests ... OK`；
- repository validation：`validated=154 errors=0 warnings=0`；
- full unit suite：`Ran 443 tests ... OK (skipped=3)`；三个 skip 均为当前环境未安装 Hypothesis 的既有可选测试；
- 结论：M11-002 验收闭合，状态 `READY→DONE`；只解锁 M11-003 为 `READY`，尚未执行任何 Provider/Tool。

### M11-003

- 仅消费 exact closure-valid Snapshot/View；
- 报告 actual execution facts 或 bounded failure/re-resolution request；
- 不 reselect/rebind、修改 Method/Claim/Gate 或实现 Topic 5 recovery。

实现证据（本阶段第三层）：

- exact View loader：external pin + Bundle lineage + M11-002 deterministic recomputation，并把同一 validated
  Bundle 绑定进 View consumer；
- single-binding Driver port：preflight/postflight binding equality，最多且恰好一次调用，无候选或 fallback；
- 调用前防线：Host-owned/injected trusted clock 的 actual started-at freshness + exact Bundle
  manifest/document reload；失败时 Driver 零调用，调用方不能 backdate；
- fact report：requested binding/Supply 与 post-call actual binding/Supply 分离，并记录 Tool identity、完整性、调用/预算、egress、side effects、external write、
  artifacts/output contract；preventive 与 detective enforcement 分栏且不信任 Driver 自报；
- bounded failure：Driver exception 不泄露正文、不 retry；capture gap 不伪装 completion；binding drift 只请求
  上游 re-resolution；
- focused negative tests：hash-valid View rewrite、pre/post binding drift、egress/effect/budget/write-scope/output
  violation、exception capture gap、forbidden routing/recovery imports；
- focused Host/View/Bundle/schema tests：`Ran 20 tests ... OK`；
- repository validation：`validated=154 errors=0 warnings=0`；
- full unit suite：`Ran 449 tests ... OK (skipped=3)`；三个 skip 均为当前环境未安装 Hypothesis 的既有可选测试；
- 结论：M11-003 验收闭合，状态 `READY→DONE`；只解锁 M11-004 为 `READY`，尚未生成 generic Receipt。

### M11-004

- no-Skill/direct Tool 路径闭合 Task→View→Host→Trace/Artifact/Validation/generic Receipt；
- execution completion 不等于 Claim/Human acceptance；
- legacy Receipt 仍可解释；不伪造 Skill Assignment。

实现证据（本阶段第四层）：

- `generic_execution_receipt`：exact execution slice/View/Host/Trace/Artifact/validation closed set，completed
  claim 固定为 `action-capability-slice-only`，所有状态均无 Task/Skill Assignment/Claim/Human/Topic 5 effect；
- deterministic replay：Receipt refs 全部重载、View 重算、Trace validation、validation subject exact set，并
  独立闭合 Host actual binding/Supply、Trace provider/tool identity/count 与 selected-Supply component；
- `execution_core_gate`：独立 no-Skill 与 direct-tool bounded vertical fixtures 均从 Bundle→View→Host→
  Trace/Artifact/Validation→Receipt replay 闭合；
- legacy `execution_receipt` schema/model/checked-in fixture 保持不变；
- negative tests：validation/Trace pin drift、Skill/Claim/Human/Recovery 字段注入、rehashed Host actual
  binding/Supply substitution、Host↔Trace Tool fact drift；
- focused M11/governance tests：`Ran 91 tests ... OK`；
- repository validation：`validated=154 errors=0 warnings=0`；
- full unit suite：`Ran 453 tests ... OK (skipped=3)`；三个 skip 均为当前环境未安装 Hypothesis 的既有可选测试；
- 结论：M11-004 验收闭合，状态 `READY→DONE`；M11-001～004 dependency chain 全部完成，M11-005/006 仍 PARKED。

## PR #45 R2 review 整改证据（2026-08-27）

本轮不改变四个 M11 Task 的 identity、dependency 或 acceptance，仅收紧已实现 contract，并把 PR 组织
规则改为稳定、通用的 module-level DAG 治理：

| Review blocker | 修复与对抗证据 |
|---|---|
| full Task capability closure | Core 显式选择 Action/Capability-slice 语义；manifest 公开完整 Task demand 与 singleton closed set，View/Host/Trace/Receipt 全程 pin 同一 slice；unresolved capability + Task completion 负例 |
| multi-candidate Resolution | Runtime 验证完整 candidate/comparison 关系但只导入 selected Supply；`satisfied` 必须唯一 eligible；双 eligible 负例 |
| Profile/Host/binding final narrowing | Profile Tool allowlist 只约束真实 Tool Supply；output/Model/Host subject 闭合；final intersection 低于 Supply permission/egress/effect demand 时 fail closed |
| freshness / Bundle TOCTOU | View 绑定 validated Bundle；Host-owned/injected trusted clock 重验三组 freshness，调用方不能 backdate；Driver 调用前重载 exact manifest/documents |
| prevented / detected | Host report 分列 preventive 与 detective controls，固定 `driver_claims_trusted=false`；文档不把 post-hoc 检测描述为沙箱预防 |
| Host↔Trace actual facts | Attempt/status、Provider/Runtime actor identity、Provider/Tool count、Tool identity 与 selected-Supply Tool component 交叉闭合；缺失 Trace operation、provider request 与 actor substitution 负例 |
| Receipt lifecycle replay | completed 要求 actual==View；post-call failed 保留 drift 并由 diagnostic+Trace actual actors 佐证；preflight blocked 无 actual binding且 Trace 零调用；三态 Host→Trace→Receipt→replay E2E |
| module-level PR governance | 不在 PR #45 内自我授权；稳定规则已拆到独立 PR #46，须先经独立接受/合并，随后 #45 rebase 并按 accepted base 复核 |

最终本地证据：

- focused Runtime Bundle/View/Host/Closeout：`Ran 38 tests ... OK`（其中最终新增的 egress/effect
  satisfiability adversarial test 单独复核通过）；
- Governance focused：`Ran 67 tests ... OK`；
- full suite：`Ran 470 tests ... OK (skipped=3)`；三个 skip 为本机缺少可选 Hypothesis；
- repository validation：`validated=154 errors=0 warnings=0`；
- wheel build、隔离 venv install、installed `rwb schema list` 与 installed repository validation：PASS；
- 本机 Python 环境没有 `coverage` 包，未临时修改系统环境；coverage 由 latest-head CI 的 3.11/3.13 jobs 执行；
- PR #46 独立接受/合并、#45 rebase、latest-head Python 3.11/3.13、coverage、wheel/clean-install、
  governance 与 cross-owner R2 review 仍是合并 Gate。

## 明确非目标

- M11-005/006 Skill Runtime Extension；
- automatic fallback、model auto-routing、multi-Agent orchestration、critic voting；
- Runtime 创建 Skill Need/Candidate、执行 admission/promotion 或读取完整 Lifecycle；
- Topic 5 Handoff/context/safe-pause/recovery/continuation；
- Provider SDK、认证或 live conformance 扩张；
- 改写 Method、Claim、Gate、Human Decision 或 permission grant authority。

## 验证与合并 Gate

每层已执行 focused unit tests、repository validation、`git diff --check`。M11-001～004 已按依赖分别形成
独立 implementation commit 与 task-specific evidence；review 整改以一个额外聚合 commit 收紧共享
contract，不重写四层历史。最终仍须等待 Python 3.11/3.13 CI、coverage、wheel/clean-install，并由两位
具名 owner 完成 cross-owner R2 review 后才可合并。PR #45 还必须先等待独立 governance PR #46 被接受，
再 rebase 到包含该规则的 `develop`；当前分支不把 PR #46 的 head checker 当自我授权证据。
