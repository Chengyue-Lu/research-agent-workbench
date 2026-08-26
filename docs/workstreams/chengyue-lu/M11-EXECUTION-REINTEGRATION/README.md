# M11 — Execution Reintegration

- 协调责任人：路诚钺（GitHub `Chengyue-Lu`）
- Runtime 实现责任人：黄毅（GitHub `let778750-cpu`）
- 分支：`agent/m11-execution-reintegration`
- PR：单个 draft feature PR，按 M11-001→002→003→004 逐层提交
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

本次单 PR 组织是 2026-08-26 具名人类指令对 Issue #41 “一 dependency layer 一 PR”实施节奏的显式
覆盖；它只改变提交/审查组织，不修改 Task 定义、依赖、验收或任何 Runtime/Capability authority。

## 分层停止点

### M11-001

- 显式 closure manifest；只读取列出的 exact path/hash；
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
- focused negative tests：Supply reselection、Profile/hash drift、stale/unavailable、disjoint write roots、bundle
  pin drift；source test 禁止 execution/fallback/Skill Evolution imports；
- focused governance/runtime/view/schema tests：`Ran 81 tests ... OK`；
- repository validation：`validated=154 errors=0 warnings=0`；
- full unit suite：`Ran 443 tests ... OK (skipped=3)`；三个 skip 均为当前环境未安装 Hypothesis 的既有可选测试；
- 结论：M11-002 验收闭合，状态 `READY→DONE`；只解锁 M11-003 为 `READY`，尚未执行任何 Provider/Tool。

### M11-003

- 仅消费 exact closure-valid Snapshot/View；
- 报告 actual execution facts 或 bounded failure/re-resolution request；
- 不 reselect/rebind、修改 Method/Claim/Gate 或实现 Topic 5 recovery。

### M11-004

- no-Skill/direct Tool 路径闭合 Task→View→Host→Trace/Artifact/Validation/generic Receipt；
- execution completion 不等于 Claim/Human acceptance；
- legacy Receipt 仍可解释；不伪造 Skill Assignment。

## 明确非目标

- M11-005/006 Skill Runtime Extension；
- automatic fallback、model auto-routing、multi-Agent orchestration、critic voting；
- Runtime 创建 Skill Need/Candidate、执行 admission/promotion 或读取完整 Lifecycle；
- Topic 5 Handoff/context/safe-pause/recovery/continuation；
- Provider SDK、认证或 live conformance 扩张；
- 改写 Method、Claim、Gate、Human Decision 或 permission grant authority。

## 验证与合并 Gate

每层至少执行 focused unit tests、repository validation、`git diff --check`。最终执行 Python 3.11/3.13 CI、
coverage、wheel/clean-install，并由两位具名 owner 完成 cross-owner R2 review。只有全部四项 Task-specific
evidence 成立后，才在同一 PR 中按 dependency DAG 置 DONE；任一层失败则后继层保持未实现并停止。
