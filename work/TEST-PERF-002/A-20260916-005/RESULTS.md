# CI contract replanning evidence

TEST-PERF-002 revision 33；owner Chengyue-Lu；2026-09-16。
状态：规范评审稿完成；实现和效果验收未开始。

## Request and scope

用户要求重新制定一轮 CI 规范，对已有业务模块做深入盘点，以支持后续局部 bugfix 和小型结构调整。
本轮读取 exact base 的业务源码/测试 AST、模块契约、共享入口、CI policy/runner，以及 PR84 的实际执行证据。
没有改动产品代码、执行选择规则、quality thresholds、witness、workflow、Task 状态或其他开发分支。

## Outputs

- [CI contract proposal](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/CI_REPLAN.md)
- [Business module and cost inventory](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/MODULE_AUDIT.md)
- [Migration and acceptance corpus](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/CI_REPLAN_ACCEPTANCE.md)

原始证据按下方清单保留。

## Bindings and retained evidence

- Source inventory base: `b041aeef8c32b74bc4399f90bf3fb49fbbb4fc22`。
- PR84 head: `dfe3165a90ebcef99d107aef8e790bf7abc0c13f`；target: `7bc70fab34f947ff0e506d8a6b9450dba099589d`。
- Plan: `b2a8eb54ba3b2fcc3d2f5028ecf70152d45695f1be726ffdbd8a8295f0896b34`。
- [Host run](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35092826503)：completed / success。
- [Inventory](checks/module-inventory.json)：99 source files、34,294 physical lines、92 test modules。
- [Scope audit](checks/pr84-scope-audit.json)：hosted plan scope/reasons reproduced；分类修正仍91/92；
  去掉通用资源回退89；Markdown-only seeds46。诊断消融不能当作安全exclusion。
- [Raw plan](checks/pr84-ci-plan.json)、[PR snapshot](checks/pr84-snapshot.json)、[run metadata](checks/pr84-hosted-run.json)。
- [3.13 plain receipt](checks/full-test-results-3.13.json)：1331 PASS、496.956315 s suite wall。
- [3.11 measured execution receipt](checks/execution-test-results-3.11.json)：1331 PASS、950.239261 s suite wall。
- [Coverage projection receipt](checks/coverage-test-results.json)：投影不是较少实际执行的证据。
- [Hash manifest](checks/evidence-manifest.json)：保留文件的 exact bytes/sha256/size。
- [Inventory producer](checks/inventory_ci.py.txt)、[scope producer](checks/audit_scope.py.txt)、
  [archive producer](checks/archive_replan.py.txt)：原始源码证据，以 `.py.txt` 保存。

## Validation boundary

数字和诊断来自上述原始 receipts/Git snapshot；模块耗时是 case duration 求和，不含所有 class setup。
跨 Python plain/coverage 结果不能直接测量 instrumentation overhead。尚未执行新模型或证明未来缩时幅度。

本轮 recorder 为回溯留存；capture-gap 如实声明，未伪造完整工具事件流。首次 Trace 验证因新 worktree
尚未生成 `_runtime_pin.py` 终止，随后使用 accepted build backend 在此隔离 worktree 生成 ignored runtime
resources，再重新验证。该环境准备没有改变任何 tracked source。

[最终文档与证据验证](checks/proposal-validation.json)：10 项 documentation tests 通过，208 个 inventory
文件的 Git blob hash 与基线相符，11 份 retained evidence 的 hash/size 相符，3 份执行回执的
target/plan/唯一 case IDs 一致；Trace 无 BLOCK，仅如实保留 delayed-capture warning。

后续实现按 proposed P1–P5 分批，不以此档案或已有绿色 CI 代替规范接受、具名 review 或 merge authority。
