# CI Performance Maintenance

- 责任人：路诚钺（GitHub `Chengyue-Lu`）
- Audit ID：`CI-PERF-001`
- 分支：`maintenance/ci-performance-topology`
- 风险：R2（`.github/workflows/**`）
- 范围：只优化 CI job topology，不改变测试语义、覆盖率阈值或治理 Gate

## 目标拓扑

```text
governance                         独立；规则与命令不变
test (3.11)                        一次 coverage full unittest
  ├─ repository coverage >= 80%
  └─ Trace module coverage >= 90%
test (3.13)                        一次 plain full unittest
package-smoke (3.11)               单次 wheel / clean venv / schema / repository validation
  └─ result 传播到两个既有 test required checks
```

`test (3.11)` 与 `test (3.13)` 的 check 名保持不变，避免破坏既有 required-check identity。两个 Python
版本仍各自完整执行一次 unittest suite；3.11 的 coverage run 本身就是该版本的完整兼容性测试，不再先跑
一遍 plain suite。3.13 不再重复 coverage。package smoke 从 matrix 中移出，只在 Python 3.11 执行一次。

不引入 pytest、sharding、test selection、cache 或并行执行框架，不删除任何测试，也不调整
`coverage report --fail-under=80` 和 Trace `>=90%` 断言。governance 保持独立 job 和原命令。

现有 GitHub ruleset 可能只要求 `test (3.11)` / `test (3.13)`。为避免新增 package job 在管理员更新
ruleset 前成为非阻断性 check，两个 test job 使用 `needs: package_smoke` + `if: always()`，并首先断言
package result 为 success。package 失败会使两个既有 required-check identity 明确失败，而不是变成可忽略的
额外红灯；这不要求修改 GitHub Admin 设置。

## 改造前基线

基线来自同一代码规模下 PR #45 最终成功 run
[`33061177181`](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/33061177181)，
head `25a8da2`，2026-08-27。wall time 按 GitHub job `startedAt → completedAt` 计算：

| Job | Wall time | 旧 job 内主要重复 |
|---|---:|---|
| `governance` | 00:05 | 无 |
| `test (3.11)` | 33:39 | plain full suite 09:11 + coverage full suite 24:06 + package smoke |
| `test (3.13)` | 41:39 | plain full suite 13:04 + coverage full suite 28:10 + package smoke |

- workflow 关键路径：41:43；
- 三个 job runner wall-time 合计：75:23；
- full-suite executions：4 次（3.11 plain + coverage，3.13 plain + coverage）；
- wheel / clean-install / schema-list / repository-validation pipeline：2 次。

## 改造后测量

每个 job 第一条 step 记录 epoch，最后一条 `if: always()` step 将 `job_wall_seconds` 同时写入日志和
`GITHUB_STEP_SUMMARY`。首个 PR-head 成功 run 用同一口径记录实际 after baseline，并在 PR comment 中给出
before/after 对比；不以本地耗时替代 GitHub hosted runner 数据。

预期执行次数固定为：

| Surface | 改造前 | 改造后 |
|---|---:|---:|
| Python 3.11 full suite | 2 | 1（coverage） |
| Python 3.13 full suite | 2 | 1（plain） |
| Coverage Gate | 2 | 1（3.11） |
| Package smoke pipeline | 2 | 1（3.11 独立 job） |
| Governance | 1 | 1（独立） |

## 边界与风险

- coverage run 退出码仍直接决定 `test (3.11)` 成败；coverage report 与 Trace threshold 保持阻断；
- `test (3.13)` 仍执行完整 discovery，不使用选择性过滤；
- package-smoke 的任一步失败会同时使独立 job 和既有 test required checks 失败；本 PR 不修改 GitHub ruleset；
- wall-time step 只观测 job 内 elapsed，不改变任何 Gate；GitHub 排队时间不计入 job wall time；
- 本 PR 不优化慢测试、不改测试实现、不引入 cache，不把 performance 结果解释为测试质量提升。
