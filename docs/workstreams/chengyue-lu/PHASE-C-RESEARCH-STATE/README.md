# Phase C Research State & Verification

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- 跨负责人执行事实接口审查：黄毅（GitHub `let778750-cpu`）
- Tasks：`M10-001`～`M10-003`、`M3-009`
- 状态：四项 bounded implementation Task 已由 PR #44 合入 `develop@92fcbe5`；machine Gate 已实现，
  Human semantic review 与 R2/Phase C closeout 仍 pending，Topic 5 implementation authority 仍为 false
- 原 planning authority basis：[Issue #38](https://github.com/Chengyue-Lu/research-agent-workbench/issues/38) 的 `R2 architecture review — ACCEPT`；只授权 bounded task drafting/implementation exploration，不接受最终表示
- 规划基线（历史）：`develop@4ce83bcf286feb085f4807df40f110ca98057c0c`
- 目标 base：`develop`
- 阶段分支（历史）：`codex/phase-c-implementation`；实际集成 workstream 见
  [`huangyi/M10-RESEARCH-STATE`](../../huangyi/M10-RESEARCH-STATE/README.md)
- 风险：`R2`；Research State meaning、Human Decision、Failure、Method Trace 与 Topic 5 Gate

## 1. 原子边界

本 workstream 已实现的 bounded candidate 只覆盖跨 Runtime 可复用的最小科研语义：

```text
exact-ref Research State
+ Attempt / Research Failure
+ Method Trace v0.1
+ two bounded continuity cases
```

它不建设知识图谱、数据库、通用 workflow DAG、策略引擎、自动科研、Runtime Bundle、Resolved
Execution View、Provider binding、Skill evolution、multi-Agent recovery 或 Topic 5 实现。

## 2. 已实现、仍待 Human/R2 semantic closeout 的表示假设

- 既有 `v0.1.0` ResearchObject、Attempt、Decision、Execution Trace 保持可重放，不原位改写其 Schema identity；
- Phase C candidate 使用显式新版本契约；当前把需要 durable identity/revision 的 State、Failure 和
  Method Trace 建成独立文档，Human Decision 则复用现有 kernel Decision 的 exact ref，不建立平行
  Decision Schema；这不是预先接受的最终 universal representation；
- 当前候选把 Unknown 与可跨 Attempt 引用的 Assumption 表为 State 内轻量 item、Contradiction 表为
  declared Evidence–Claim relation、Frontier 表为 derived projection。两个 bounded case 与机器反例已经
  合入；它们只证明候选可确定验证，最终进入 accepted universal representation 仍须 Human semantic review
  与 R2 closeout；
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

当前 `develop` 已有 M11 typed、hash-pinned `execution_trace_fact` producer。Method Trace 只有在该事实
exact-link 同一 Attempt、applied path 与 State effect 时才可记录 `captured`；本 Attempt 没有合格事实时仍
必须显式记录 `unavailable` / gap-only，不能把全局 producer 的存在冒充本次捕获。Phase C 始终不从
Resolved Capability Snapshot 推断真实执行，也不把 Topic 4 变成 State/Failure/Trace 的语义所有者。

## 5. Verification

两份 bounded fixture 都必须在 staged 新进程中只读取 runner-owned allowlist，并输出实际 read surface。
private oracle 只能检查 exact outputs、read surface、known-failure fixture behavior 与声明 predicate；它不能
证明 reviewer reconstruction 或科学正确性。独立人类 rubric 评价科研/控制解释，R2 owner 再决定最终表示。
机器 Gate、Human review 与 R2 closeout 分开，任一缺失都不能宣称完整 Phase C closeout。

## 6. Stop condition

Contracts、fixtures、validators、tests 与全套 CI/negative/adversarial evidence 已随 PR #44 进入
`develop`，四项 M Task 因此为 DONE。尚未完成的是 Human semantic review 与 R2/Phase C closeout；在该
具名决定前不得把候选提升为最终 universal representation，也不得允许 Topic 5 重新进入架构设计。
即使未来 Phase C closeout 通过，也绝不自动批准 Topic 5 实现。

## 7. 历史 PR sequencing

以下段落保留原 task-definition / feature 分离要求，解释该 workstream 如何进入实现，不是当前 live queue：

仓库治理要求 task-definition 与 feature 分离：本 workstream 的 Task 草案必须先作为 **docs-only
task-definition PR** 独立接受；Issue #38 本身没有使这些行成为 canonical Task。之后 implementation changes
才能基于已进入 `develop` 的 Task definition 形成 feature PR。不得把 Task 定义调整与实现合并到同一 PR，
也不得在 feature PR 中借机冻结最终 representation。
