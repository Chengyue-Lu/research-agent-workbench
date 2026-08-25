# Phase C Research State & Verification

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 跨负责人执行事实接口审查：黄毅（GitHub `let778750-cpu`）
- Tasks：`M10-001`～`M10-003`、`M3-009`
- authority basis：[Issue #38](https://github.com/Chengyue-Lu/research-agent-workbench/issues/38) 的 `R2 architecture review — ACCEPT`
- 基线：`develop@4ce83bcf286feb085f4807df40f110ca98057c0c`
- 目标 base：`develop`
- 阶段分支：`codex/phase-c-implementation`
- 风险：`R2`；Research State meaning、Human Decision、Failure、Method Trace 与 Topic 5 Gate

## 1. 原子边界

本 workstream 只实现跨 Runtime 可复用的最小科研语义：

```text
exact-ref Research State
+ Attempt / Research Failure
+ Method Trace v0.1
+ two bounded continuity cases
```

它不建设知识图谱、数据库、通用 workflow DAG、策略引擎、自动科研、Runtime Bundle、Resolved
Execution View、Provider binding、Skill evolution、multi-Agent recovery 或 Topic 5 实现。

## 2. 表示选择约束

- 既有 `v0.1.0` ResearchObject、Attempt、Decision、Execution Trace 保持可重放，不原位改写其 Schema identity；
- Phase C 新语义使用显式新版本契约；只有需要 durable identity/revision 的 State、Failure、Human Decision
  和 Method Trace 成为独立文档；
- Unknown 与可跨 Attempt 引用的 Assumption 使用 State 内轻量 item；Contradiction 是 declared Evidence–Claim
  relation，Frontier 是 open item、active Failure 与 next Task 的 derived projection；
- exact refs 只验证 identity/revision/path/hash/type closure，不复制被引用正文；
- validator 只验证声明形状和 authority ceiling，不判断 Evidence 科学上是否支持 Claim。

## 3. Attempt 与 State 的三条独立关系

1. `from-State` exact-pin Attempt 开始时读取的 State revision；
2. predecessor Attempt 只在需要执行连续性时单独记录；
3. reopen justification 引用后来出现的 Failure、Decision、Unknown/Evidence 或 changed condition。

多次 Attempt 可以共享同一 State；Attempt 不必产生 State revision；Evidence admission 或 Human Decision
可以在没有一对一 Attempt transition 时改变 State。以上引用都不授权 retry、fallback、rebind、replanning、
Claim promotion 或 Skill Need。

## 4. Actual-binding boundary

当前 `develop` 没有 accepted execution-layer actual-binding fact producer。Method Trace 必须能显式记录
`unavailable` gap；这个结构通过只证明缺口被诚实表达，不证明 actual binding 已捕获。只有未来 accepted
producer/ref 能 exact-link frozen selection 与实际执行时，独立 coverage Gate 才可通过。Phase C 不从
Resolved Capability Snapshot 推断真实执行，也不把 Topic 4 变成 State/Failure/Trace 的语义依赖。

## 5. Verification

两份 bounded case 都必须在新进程中只读取显式 allowlist，并输出实际 read surface。private oracle 检查
exact refs、known Failure、Decision effect、revisit condition 与下一 Frontier/Task；独立人类 rubric 评价
科研/控制解释。机器 Gate 与人类 review 分开，任一缺失都不能宣称完整 Phase C closeout。

## 6. Stop condition

实现分支可以形成可审查的 contracts、fixtures、validators 与 tests；只有 task-definition 进入 `develop`、
全套 CI/negative/adversarial evidence 通过且具名 R2 closeout 接受后，才可在 canonical 状态中标记 Phase C
完成并允许 Topic 5 重新进入架构设计。通过 Phase C 绝不自动批准 Topic 5 实现。
