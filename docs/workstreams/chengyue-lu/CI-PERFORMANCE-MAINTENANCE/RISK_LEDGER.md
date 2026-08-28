# CI Performance Maintenance 风险台账

| ID | 类型 | 风险 | 控制 | 状态 |
|---|---|---|---|---|
| CI-PERF-GATE-001 | fact | 新拆出的 package-smoke job 若未被现有 branch ruleset 列为 required check，package 失败可能不阻断合并。 | 两个既有 `test (3.11)` / `test (3.13)` job 显式依赖 package-smoke，并在 `if: always()` 下断言其结果为 success；package 失败会传播到既有 required-check identity。 | controlled by workflow and PR CI |
| CI-PERF-COMPAT-001 | fact | 去掉重复 suite 可能被误解为减少 Python 版本兼容性覆盖。 | 3.11 仍以 coverage 执行完整 unittest discovery；3.13 仍以 plain unittest 执行同一完整 discovery；不使用 test selection、sharding 或 pytest。 | controlled by workflow topology |
| CI-PERF-COVERAGE-001 | fact | 将 coverage 收敛到单一版本可能意外降低阈值或绕过 Trace 子阈值。 | 3.11 保留 repository `--fail-under=80` 与 Trace `>=90%` 两个阻断断言，退出码继续决定既有 test check。 | controlled by unchanged thresholds |
| CI-PERF-PACKAGE-001 | fact | 从 matrix 移出的 wheel / clean-install / schema / repository validation 可能漏跑或重复运行。 | 独立 Python 3.11 package-smoke job 各执行一次，并由拓扑静态校验和 PR run 共同确认。 | controlled by workflow and PR CI |
| CI-PERF-TIMING-001 | inference | 单次 hosted-run wall time 受排队、runner 与网络波动影响，不能证明测试实现本身变快。 | 记录各 job `startedAt -> completedAt`、关键路径和 runner wall-time 合计；只将执行次数减少归因于拓扑，保留运行链接，不在本 PR 优化测试实现。 | accepted measurement limitation |
| CI-PERF-GOV-001 | fact | workflow 重排可能将 governance 串入 package/test 链或改变治理命令。 | governance 保持无 `needs` 的独立 job，继续运行原有 `python .github/scripts/check_pr_governance.py`。 | controlled by workflow and PR CI |
