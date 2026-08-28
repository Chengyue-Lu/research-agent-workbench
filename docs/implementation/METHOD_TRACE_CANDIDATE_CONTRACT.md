# Ref-only Method Trace v0.1 Candidate (M3-009)

状态：Bounded implementation candidate；最终表示待 Human/R2 接受

更新：2026-08-28

## 1. 单层范围

本契约在 M3-008 operational Execution Trace 之上实现独立 Method Trace，不修改或嵌入 Execution Trace。
它记录一条 bounded research/control path 使用了哪个 Research Attempt、Task、Method Resolution、Mode、
Action decision、Research State、kernel Human Decision 与 path disposition。所有关系只保存 stable ref，
不复制 Method、State、Evidence、Decision、Failure 或 operational event 正文。

本层不实现 M10-003 fresh-process continuity Gate，不证明 reviewer reconstruction 或科学正确性，也不授予
Runtime、Claim、Human Decision、retry/replan 或 Topic 5 authority。

## 2. Exact method application

Method Trace 以 `method_application.resolution_ref` 精确引用 canonical `method_resolution`：

- `ClosureIndex` 正式索引 `resolution_id@revision`，missing、duplicate、unversioned、wrong-kind 均阻断；
- referenced Method Resolution 必须 schema-valid，且其 Task id/revision/byte SHA-256 与 Trace Task 一致；
- Trace `mode_refs` 必须与 Resolution 的 selected modes 完全一致；
- `path_dispositions` 必须恰好覆盖 Resolution 的每个 Action decision，不能缺失或重复；
- `action_decision_ids` 必须恰好等于 disposition 为 `applied` 的路径。

Mode/Action 的规范语义仍由既有 Method Resolution validator、Mode Action Registry 与 published Action
documents 负责；Method Trace 只引用 Resolution 内已冻结的 Mode ref、Action decision id 和 Action hash，
不建立第二套选择或解析权威。

## 3. Attempt、State 与 Human Decision closure

Trace 的 Research Attempt sidecar 必须解析到 exact execution Attempt，且 execution Attempt、Trace Task 与
Method Resolution Task identity 一致。`from-state` 必须等于 Attempt 开始时的 State exact ref；其他 State
revision 可记录 current/result/superseded，但不会被解释为 Attempt 必然产生的状态迁移。

Task question 与被引用 State 中的 Question 必须至少有一个 identity 交集，避免把各自合法但无关的 Task、
Attempt 和 State 拼成一条 Method path。Human Decision、Evidence、Failure 与 State path basis 分字段做
semantic type 检查；Human Decision 继续复用 kernel `decision` object。

## 4. Actual-binding boundary

当前基线已包含 M11 `execution_trace_fact` producer。Method Trace 必须区分“producer 存在”与“本 Attempt
是否有 authoritative fact”。没有本 Attempt fact 时只能记录：

```yaml
status: unavailable
reason: no-authoritative-execution-fact-for-attempt
coverage: gap-only
```

该结构只证明 per-Attempt 缺口被诚实表达，所有 path 的 `execution_fact_refs` 必须为空。captured 分支只接受
M11 producer 生成、在显式 closure 中以 path+loaded-byte SHA-256 精确绑定、schema-valid 且属于同一
Attempt 的 `execution_trace_fact`。顶层 fact 必须在至少一个 path disposition 中以完全相同的 FileReference
重复绑定；该 path 必须为 `applied` 且携带 State effect ref。coverage 仅为
`fact-bound-path-effect`，不声称整条 Method、科学结论或 reviewer reconstruction 完整。

Resolved Capability Snapshot 无论是 structural-replay 还是未来 runtime-execution，都不是 actual execution
fact；wrong-kind Snapshot fixture 必须阻断。Method Trace 不从 selected Snapshot、Receipt 或 gap-valid 状态
推断实际执行。

## 5. 证据边界

Case A 证明一条 synthetic evidence-synthesis path 的 exact ref/identity/type/byte-pin closure 和 per-Attempt
gap honesty；captured 正例由 M11 `AgentTraceRecorder.record_execution_fact()` 生成正式 fact，并验证其与
同一 Attempt、applied path 和 State effect 的 exact 绑定。
专项反例覆盖 Method Resolution 缺失/错类型/错 Task/坏 Schema/坏 Task pin、Mode drift、Action disposition
缺失/重复、Attempt/Task/State/Question 拼接、Human/Evidence 错类型、duplicate Trace、gap overclaim、
captured fact 缺失/Attempt 错配/path 未绑定/ref 漂移、unavailable 夹带 fact 与 Snapshot-as-actual。最终
Method Trace 表示和语义仍须具名 Human/R2 接受。
