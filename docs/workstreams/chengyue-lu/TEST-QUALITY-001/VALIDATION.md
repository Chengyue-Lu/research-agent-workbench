# TEST-QUALITY-001 Validation

## Local evidence

```text
python -m py_compile tests/run_unittest_suite.py .github/scripts/check_coverage_policy.py tests/test_coverage_policy.py
python -m unittest tests.test_coverage_policy -v
python tests/run_unittest_suite.py --suite coverage-quality --json-output <temporary> --verbosity 0 --slowest 10
```

- checker adversarial tests：21 PASS；覆盖 canonical source root、正反证据交集、actual/policy exclusion 双向闭合与 CLI fail-closed；
- fixture extraction、Capability consumer/registry validator 与相关 execution contract focused tests：71 PASS；
- dedicated suite 历史基线：518 tests PASS，518/518 canonical unique，local wall 192.768 秒；
- final local selection：543 tests PASS，543/543 canonical unique，wall 217.629 秒；
- final hosted loader：coverage-quality 543/543 canonical unique，Python 3.11/3.13 full discovery 均为 604/604 canonical unique；
- 上述本地分类 run 未启用 coverage instrumentation，仅证明选择与 runner 语义可执行；
- 本机解释器无 coverage module，未安装网络依赖或修改系统环境。

## Required hosted evidence

最终 R2 PR 必须在 Python 3.11 hosted runner 生成 branch-enabled `coverage.json`，并记录：

- global line；
- 每个 critical file 的 line/branch；
- coverage-quality test count/wall/p50/p95/slowest 20；
- Python 3.11/3.13 full suite count/wall/p50/p95/slowest 20；
- governance、package-smoke、repository validation 与 aggregate required Gates；
- 未达到 12–15 分钟时的具名慢测试事实。

在这些证据齐全前，本 workstream 不标记完成。

### Initial hosted baseline — run 33099480345

- governance：7 秒，PASS；package-smoke：17 秒，PASS；
- Python 3.11 full：732 秒，PASS；Python 3.13 full：804 秒，PASS；
- coverage-quality：394 tests，1055 秒，测试本身全部 PASS，policy Gate 按预期 FAIL；
- coverage suite：wall 1036.889 秒，p50 0.013 秒，p95 14.960 秒；
- global line：79.31%；
- 唯一已同时满足 critical line/branch 的首轮文件：`kernel/objects.py`（98.72% / 100%）；
- 两个既有 `test (3.11)` / `test (3.13)` aggregate checks 均因 coverage-quality 失败而失败，证明 Gate
  propagation 生效。

完整逐文件缺口必须从下一 run 保留的 `coverage-quality-evidence` artifact 读取后再补测试；不以降低
90/95/90 阈值或增加宽泛 exclusion 处理。

### Iterative closure baseline — runs 33142576963 / 33143275151 / 33143784530

| Run | Coverage tests | Suite wall | p50 | p95 | Global line | 结果 |
|---|---:|---:|---:|---:|---:|---|
| 33142576963 | 495 | 964.021s | 0.019s | 8.357s | 85.01% | critical gap inventory |
| 33143275151 | 508 | 957.835s | 0.019s | 7.053s | 86.52% | provider / CLI / Skill helper closure |
| 33143784530 | 519 | 1121.152s | 0.019s | 8.160s | 87.12% | eight critical files satisfy policy |

Run 33143784530 的两版本 full suite、governance 与 package-smoke 均 PASS。剩余 critical 缺口是 Runtime
Bundle、Execution View、Trace、Generic Receipt；当前 head 已增加其 manifest/category、constraint
intersection、trace-boundary、Receipt lifecycle/evidence closed-set tests。最终 head run 33179905452 负责
确认这些补测能同时满足 global 与逐文件 90/95/90，并记录精简 coverage selection 后的关键路径。

### Critical closure / performance baseline — run 33179905452

- coverage-quality：546 tests PASS，suite wall 730.009 秒，p50 0.013 秒，p95 5.386 秒；
- coverage job wall：12 分 29 秒，进入 12–15 分钟目标窗口；
- global line：88.52%，唯一 policy failure，距离 90% 还差 157 covered lines；
- 12 个 critical file 全部 PASS，其中最低 line 为 Execution View 95.27%，最低 branch 为 Execution View
  与 relationships 90.00%；
- governance、package-smoke 与 Python 3.11 full suite PASS；
- 当前 head 新增通用文档闭包的 adversarial matrix，覆盖 registry、Mode Action、Capability Requirement、
  Skill Need 与 Protocol Profile 的 duplicate/missing/path/hash/identity/unknown-reference 分支；这些是
  repository-wide validator 行为证据，不改变任何产品 contract。

相对 CI-PERF-001 run 33089933787 的 28:48 关键路径，本轮可比 coverage job 已降到 12:29，同时把
global quality floor 从 83% 目标提升到机器阻断的 90%、critical floor 提升到逐文件 95/90。最终新 head
仍需重新证明 global line 与完整 CI 全绿。

### Global closure baseline / hosted variance — run 33181391418

- coverage-quality：549 tests PASS，suite wall 1063.954 秒，p50 0.017 秒，p95 7.824 秒；
- global line：89.26%，较前一 head 增加 78 covered lines，距离 90% 还差 79 行；
- 全部 12 个 critical file 继续 PASS；Python 3.11/3.13 full suite、governance、package-smoke 与
  repository validation 均 PASS；legacy aggregate Gate 按 global failure 正确阻断；
- 同一 hosted 拓扑在相邻 runs 的 coverage job wall 从 12:29 波动到约 18:05。slowest 仍由三个完整
  Generic Receipt/Trace 文件重放占据（61.22s、57.93s、45.30s），其余长尾使 p95 从 5.386s 波动到
  7.824s；本 PR 不以删除这些 behavioral/replay 证据换取稳定时长；
- 当前 head 再增加 1 秒级的 integrity-index cardinality、Context pressure/raw-material/compaction 与
  Skill Evaluation protocol/case/review/Receipt boundary tests，目标覆盖余下 79 行。

### Final-gap baseline — run 33183258709

- coverage-quality：553 tests PASS，suite wall 949.507 秒，p50 0.016 秒，p95 7.008 秒；
- global line：89.66%，距离 policy floor 还差 36 行；全部 critical files 继续 PASS；
- Python 3.11/3.13 full suite、governance、package-smoke 与 repository validation PASS；
- 当前 head 增加 0.03 秒级的 common contract primitive、Task budget/delegation/lifecycle、Context Snapshot
  late-validation 与 Project Protocol loader 错误分支，覆盖预算为 36 行缺口外另留安全余量。

### Superseded heavy closure — run 33185024911

- coverage-quality：557 tests PASS，suite wall 1086.391 秒，global line 90.16%；
- 原 12 个 critical files 全部越过 95/90，双 Python full suite、governance、package-smoke 与 aggregate
  Gates 全部 PASS；
- 实际 canonical identity 审计发现 21 个测试因 `test_*` / `tests.test_*` 模块别名重复执行；
- slowest 由 Generic Receipt/Trace replay、archive/recovery 与 Host integration 主导，因此该绿灯仅证明旧
  policy 可达阈值，不满足 final remediation 的 suite 结构与时长要求。

### Final remediation candidate — runs 33238653977 / 33244586695

- coverage manifest 移除 Generic closeout E2E、长 Host integration、archive/recovery、Handoff 与 live Skill
  evaluation；上述测试完整保留在双 Python behavioral suite；
- Runtime Bundle / View / Host 共用 fixture 已迁出 discovery，runner 对实际 canonical test identity fail closed；
- 新增 `validation/capability.py` critical inventory，并把 `documents.py` 中 Capability Requirement
  identity/path/hash/Method-reference 闭包拆为 `validation/capability_registry.py`；共用 byte/path primitives
  同步拆为 `validation/document_core.py`，两者都受逐文件 Gate；
- 新模块具备独立 positive closed-set 与 missing/duplicate/kind/identity/path/hash negative evidence；
- run 33238653977：518 tests PASS，suite wall 709.359 秒（11 分 49 秒），global line 87.71%；Host
  97.03% / 92.73%、Generic Receipt 97.95% / 91.14%，新增 capability/document critical validators
  均为 100% / 100%，所有 critical files 已满足逐文件 Gate；
- run 33240592061：527 tests PASS，suite wall 813.756 秒，checker source-root global line 89.99%；
- 当前 head 增加 8 个 archive/recovery 隔离 validator 单元测试与 1 个 Receipt 缺失引用负例；它们 mock
  掉 Trace、协议与完整 replay，只覆盖 fail-closed orchestration，不把重型 replay 放回 coverage；
- 最后一项 publication failure 负例覆盖独占写失败后的半成品清理，不修改产品 contract；
- run 33244586695（commit `b123b91`）：527 tests PASS，job wall 733 秒，global line 90.02%；原有 15 个
  critical modules 全部满足 95/90，双 Python full suite、package-smoke、governance 与 aggregate checks PASS；
- final remediation 新增 checker self-control、canonical source-root、disjoint evidence、exact exclusion reconciliation，
  并把 Method Resolution、Authority、Capability/Supply/Snapshot 与 Phase B Gate validator 从大型
  `documents.py` 拆到独立 critical modules；focused contracts 与 21 个 checker tests PASS；

### Coverage Policy self-control diagnostic — run 33253531031

- 542 coverage tests PASS，suite wall 718.400 秒，job wall 728 秒；global source-root line 90.80%；
- checker 自身 97.24% line / 95.56% branch；Authority registry 100/100；Method registry
  100/93.62；Phase B Gate 96.53/91.86，均满足 critical Gate；
- Capability Supply registry 90.45/81.50，是唯一 policy failure；artifact 显示缺口集中于 malformed
  artifact refs、typed evidence 与 cross-object path/lineage 分支；
- Python 3.11 full 603 PASS（743.712 秒），Python 3.13 full 603 PASS（640.531 秒），package-smoke、
  repository validation 与 governance PASS；aggregate checks 只因 coverage Gate 正确传播失败；
- 后续提交针对上述 artifact 缺口新增 1 个 0.71 秒的 direct validator adversarial matrix，覆盖 reference
  shape、evidence kind/class/hash、candidate/snapshot path 与 Task lineage；不改变产品 contract。

### Final fail-closed closure — run 33254218939

- exact commit：`c7f20f2ce5e983da1e6d847c7a282832c70ae53c`，base `develop@1425141`；
- coverage-quality：543 tests PASS，suite wall 830.067 秒，job wall 842 秒，global source-root line 91.01%；
- 20 个 critical files 全部满足 line >=95% / branch >=90%；checker 自身 97.24/95.56，Capability Supply
  registry 97.01/93.00，Method registry 100/93.62，Phase B Gate 96.53/91.86，Authority registry 100/100；
- Python 3.11 full：604 PASS，suite wall 590.703 秒；Python 3.13 full：604 PASS，suite wall 900.440 秒；
- package-smoke、repository validation、governance 与 `test (3.11)` / `test (3.13)` aggregate checks PASS；
- canonical source root、正反 evidence 互斥、actual/policy exclusions 双向闭合、checker self-control 与拆分后的
  authority-sensitive validator inventory 均由当前精确 HEAD 的 hosted artifact 和对抗测试闭合。
