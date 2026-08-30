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
- canonical global source root `src/research_workbench` 与 line threshold `>=90%`；checker 拒绝任何缩窄；
- critical file exact paths 与逐文件 line `>=95%` / branch `>=90%`；
- critical allow/block surface 的 positive + negative test IDs；
- 窄范围、具名、可审计的 justified exclusions，并与 `coverage.json` 的实际 excluded lines 双向 exact 对账。

[`check_coverage_policy.py`](../../../../.github/scripts/check_coverage_policy.py) 从 branch-enabled
`coverage.json` 重算完整 `src/research_workbench` 的全局 line coverage，不采用包含外部脚本的 aggregate
total；随后逐文件检查 critical line/branch，并确认声明的 positive/negative tests 在本次
coverage-quality execution 中真实 PASS。正反 test ID 必须分别非空、内部唯一且互不相交。checker 自身也
属于 critical module，必须满足 95/90 并具备独立正反证据。缺文件、缺 branch data、缺 evidence、阈值
下调、source-root 缩窄、wildcard exclusion 或实际/声明 exclusion 不闭合均 fail closed。

当前仅登记 coverage.py 对 Protocol 声明体自动识别的两组 exact exclusions：
`adapters/models/session.py:90-93` 与 `execution/host.py:66-74,76-78`。每组都固定 path、逐行列表、reason
和 owner；新增、删除或行号漂移都会由双向对账阻断。

每次 hosted run 将 `coverage.json` 与 `coverage-test-results.json` 保留为 14 天的具名 artifact，供
R2 reviewer 校核逐行/逐 branch 缺口与 slowest evidence；artifact 是审计输入，不改变 Gate 结果。

## Critical Surface 映射

| Semantic surface | Exact measured implementation |
|---|---|
| Governance-sensitive validator | `.github/scripts/check_pr_governance.py` |
| Coverage quality authority | `.github/scripts/check_coverage_policy.py`；checker 不能豁免自己 |
| Authority Rule Eligibility | `protocol/authority.py` |
| Capability Requirement / Resolution / Snapshot | `capability/requirements.py`, `supply.py`，以及 Runtime Bundle 对 Resolution/Snapshot exact closure 的验证 |
| Runtime Bundle / Resolved Execution View / Thin Host | `execution/runtime_bundle.py`, `execution_view.py`, `host.py` |
| Trace / Generic Receipt closeout | `observability/trace.py`, `execution/generic_closeout.py` |
| exact-ref / hash / provenance | `artifacts/integrity.py`, `validation/relationships.py` |
| Capability Snapshot consumer | `validation/capability.py` |
| Method / Authority / Capability / Phase B document closure | `validation/method_resolution_registry.py`, `authority_registry.py`, `capability_supply_registry.py`, `phase_b_gate.py` |
| Capability Requirement registry closure | `validation/capability_registry.py`, `validation/document_core.py` |
| Research State / Attempt / Failure / Method Trace / Phase C Gate | `kernel/objects.py`, `research_state/closure.py`, `fresh_actor.py`, `gate.py`, `validation/research_state_registry.py`；document-kind dispatch 同受 critical Gate |
| Source Admission producer / raw-reference gate | `artifacts/admission.py`；accepted M4-001 producer 与 ordinary raw-reference sidecar/hash closure 均受独立 95/90 critical Gate 和正反 evidence 约束 |

Coverage percentage 只说明路径被执行。每个可能改变 allow/block/authority/permission/hash/binding/Receipt
closure 的 critical surface 仍必须有显式正反验收；R2/DONE 不能只引用百分比。

`validation/documents.py` 现在负责 SchemaCatalog 调度、通用字段/hash walk、旧 registry/task 校验，以及
Skill Need、Protocol Profile、Skill lifecycle、Mode migration 等尚未拆分的域校验。它不是“纯 dispatch”，
也不被整体机械拉到 95/90；本轮明确影响 Method Resolution、Authority、Capability/Supply/Snapshot 与
Phase B replacement Gate 的实现已迁到上述四个职责模块。后续若剩余域逻辑被提升为 authority-sensitive
surface，必须先拆分并追加 critical inventory，不能借用 `documents.py` 的 global coverage 代替。

`capability/resolver.py` 是历史 Task→Skill Assignment resolver，不是 M9 的 Capability Resolution；首轮
baseline 暴露命名歧义后已从 critical inventory 移除，但仍计入 repository global coverage。该修正不排除
实际 M9 Resolution/Snapshot：它们由 `capability/supply.py` 的 demand/supply assessment 与
`execution/runtime_bundle.py` 的 exact selected closure 共同覆盖。

## Suite 职责

Behavioral suites 在 Python 3.11/3.13 上继续 discovery 全部 `test_*.py`，保留 property、subprocess、
repository fixture replay 与 integration。Coverage-quality suite 只包含 deterministic unit/contract/validator
modules；具名 omitted modules 没有被删除，仍在两套 behavioral suites 中运行。

原生 unittest runner 记录 suite wall time、test count、slowest 20、p50、p95，并生成机器可读 JSON；不引入
pytest、sharding、test selection framework 或 cache。Coverage suite 只组合 deterministic
unit/contract/validator modules；Generic Receipt/Trace replay E2E、长 Host integration、archive/recovery replay、
Handoff replay 与 live Skill evaluation 仍由 3.11/3.13 full discovery 执行，不能因此被删除或视为已被较快
helper test 取代。

共享 Runtime Bundle / View / Host fixture 已迁到不匹配 `test_*.py` 的 `tests/execution_fixtures.py`；测试模块
不再 import 其他测试模块的 `TestCase`。runner 在执行前按“源码文件 + TestCase qualname + method”核对
canonical identity，字符串清单不同但实际测试相同也会 fail closed。最终 hosted run 33254218939 的
coverage selection 为 543/543 unique canonical tests，Python 3.11/3.13 full discovery 均为
604/604 unique canonical tests。

## 前置基线与验收

CI-PERF-001 / PR #47 成功 run `33089933787`：关键路径 28:48；3.11 full coverage 28:20；3.13 plain
full suite 08:37；全局 line 83%，Trace line 92.87%。这证明单靠 suite 拆分不能达到 90/95/90，本轮必须用
高价值 fail-closed tests 补足真实缺口，不能只移动阈值。

最终验收需要：

- 两版本 plain full suite 全部 PASS；
- coverage-quality global line `>=90%`；
- 每个 critical file line `>=95%`、branch `>=90%`；
- coverage-quality 中不存在 duplicate canonical test execution；
- policy checker 的阈值、branch、文件、evidence 与 exclusion 对抗测试 PASS；
- package-smoke、repository validation 与 governance PASS；
- hosted critical path 进入约 12–15 分钟，或用 slowest/p50/p95 给出明确事实原因。

重型 head 的 run 33185024911 曾证明旧 inventory 可达阈值，但 coverage suite 557 tests / 1086.391 秒，
且含 21 个 canonical duplicate，不能作为最终结构验收。最终 run 33254218939 在无 canonical duplicate 的
543 项 dedicated suite 上达到 global line 91.01%，全部 20 个 critical files 满足逐文件 95/90，双 Python
full suite、package-smoke、governance 与 legacy aggregate Gates 均 PASS。
