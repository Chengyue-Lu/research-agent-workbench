# TEST-QUALITY-001 — Coverage Policy v2

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- Audit ID：`TEST-QUALITY-001`
- 来源：[Issue #48](https://github.com/Chengyue-Lu/research-agent-workbench/issues/48)
- 分支：`maintenance/test-quality-v2`
- 风险：R2（shared CI / contract-quality policy）
- 前置：CI-PERF-001 / PR #47 独立收口；本分支在 #47 head 上开发，合并前以最新 `develop` 重新建立基线

## 本轮边界

本轮把 correctness、Python compatibility、coverage quality、packaging 与 governance 拆成可区分的 Gate，
并把 coverage threshold、critical file inventory、negative acceptance 与 exclusion policy 收敛到单一机器可读
authority。它不改变 Runtime、Method、Claim、Human Gate 或 scientific semantics，也不提前实施
TEST-PERF-002 的 fixture/subprocess/Hypothesis 优化。

```text
governance                         独立
compatibility (3.11)              plain full unittest + durations
compatibility (3.13)              plain full unittest + durations
coverage-quality (3.11)           deterministic coverage suite + branch coverage + policy checker
package-smoke (3.11)              wheel / clean install / schema / repository validation
       │
       └── existing required identities: test (3.11), test (3.13)
```

五个执行 job 尽量并行。最后两个轻量 aggregate job 保留既有 branch-rules 所识别的 `test (3.11)` 与
`test (3.13)` check 名；任一 compatibility、coverage-quality 或 package-smoke 失败都会传播到既有 required
Gate。在 GitHub ruleset 显式纳入新 check 前，不依赖新增 job “显示为红色”来假定它能够阻断合并。

## 单一 Coverage Authority

[`tests/coverage_policy.yaml`](../../../../tests/coverage_policy.yaml) 唯一声明：

- dedicated coverage-quality suite 的 exact test modules 与具名 omission reason；
- global source root 与 line threshold `>=90%`；
- critical file exact paths 与逐文件 line `>=95%` / branch `>=90%`；
- critical allow/block surface 的 positive + negative test IDs；
- 窄范围、具名、可审计的 justified exclusions（首版为空）。

[`check_coverage_policy.py`](../../../../.github/scripts/check_coverage_policy.py) 从 branch-enabled
`coverage.json` 重算完整 `src/research_workbench` 的全局 line coverage，不采用包含外部脚本的 aggregate
total；随后逐文件检查 critical line/branch，并确认声明的 positive/negative tests 在本次
coverage-quality execution 中真实 PASS。缺文件、缺 branch data、缺 evidence、阈值下调或 wildcard
exclusion 均 fail closed。

## Critical Surface 映射

| Semantic surface | Exact measured implementation |
|---|---|
| Governance-sensitive validator | `.github/scripts/check_pr_governance.py` |
| Authority Rule Eligibility | `protocol/authority.py` |
| Capability Requirement / Resolution / Snapshot | `capability/requirements.py`, `resolver.py`, `supply.py` |
| Runtime Bundle / Resolved Execution View / Thin Host | `execution/runtime_bundle.py`, `execution_view.py`, `host.py` |
| Trace / Generic Receipt closeout | `observability/trace.py`, `execution/generic_closeout.py` |
| exact-ref / hash / provenance | `artifacts/integrity.py`, `validation/relationships.py` |
| 当前最小 Research State object lineage | `kernel/objects.py` |
| Source Admission 边界 | 当前尚无独立 accepted Source Admission producer；先由 artifact integrity + provenance relationship fail-closed surface 承担，未来新增 producer 必须 append 到 policy |

Coverage percentage 只说明路径被执行。每个可能改变 allow/block/authority/permission/hash/binding/Receipt
closure 的 critical surface 仍必须有显式正反验收；R2/DONE 不能只引用百分比。

## Suite 职责

Behavioral suites 在 Python 3.11/3.13 上继续 discovery 全部 `test_*.py`，保留 property、subprocess、
repository fixture replay 与 integration。Coverage-quality suite 只包含 deterministic unit/contract/validator
modules；具名 omitted modules 没有被删除，仍在两套 behavioral suites 中运行。

原生 unittest runner 记录 suite wall time、test count、slowest 20、p50、p95，并生成机器可读 JSON；不引入
pytest、sharding、test selection framework 或 cache。首份本地无 instrumentation 分类验证为 327 tests、
330.515 秒、p50 0.030 秒、p95 4.958 秒；加入快速 governance checker tests 后的 hosted baseline 以 PR
首个最终 head run 为准。

## 前置基线与验收

CI-PERF-001 / PR #47 成功 run `33089933787`：关键路径 28:48；3.11 full coverage 28:20；3.13 plain
full suite 08:37；全局 line 83%，Trace line 92.87%。这证明单靠 suite 拆分不能达到 90/95/90，本轮必须用
高价值 fail-closed tests 补足真实缺口，不能只移动阈值。

最终验收需要：

- 两版本 plain full suite 全部 PASS；
- coverage-quality global line `>=90%`；
- 每个 critical file line `>=95%`、branch `>=90%`；
- policy checker 的阈值、branch、文件、evidence 与 exclusion 对抗测试 PASS；
- package-smoke、repository validation 与 governance PASS；
- hosted critical path 进入约 12–15 分钟，或用 slowest/p50/p95 给出明确事实原因。

本文件在最终 hosted baseline 前不把阈值或性能标为已满足。
