# M5-007 H4a latest-develop rebase proof

Date: 2026-09-23. Accountable owner: 路诚钺 (`Chengyue-Lu`). Execution reviewer: 黄毅 (`let778750-cpu`). Risk: R2.

PR: [#90](https://github.com/Chengyue-Lu/research-agent-workbench/pull/90). Original reviewed candidate: `b9ad97ebf256351dd5e1540d5e688087394d474d`. New base: `develop@6cf80610cc2d3b4ebdeb9f47a840cd0ec1870bbf`. Conflict-resolved implementation head before this record: `975d07614e2d670839eb1f7e1e0609d4f7f66151`. Final PR head and hosted CI belong in the PR body/checks and must be read live.

## Review finding and resolution

黄毅在 2026-09-23 对旧 head 提交 `COMMENTED` review：源码无当前分支内缺陷，但要求先处理 `docs/STATUS.md` 与 `tests/coverage_policy.yaml` 的集成冲突，再以新 base/head/merge target 复核完整 CI、证据和审批。该评论不是 formal `APPROVED`；不能用旧 head 的绿灯作为合并证据。

- `docs/STATUS.md` 保留主线 M14-005 READY、source-CI 进度及 release 边界；Phase D 行确认 PR89 H3 已接受，H4a 为待审候选，H4b/H4c/H5 仍后续。
- 覆盖策略保持主线 `2.3.0`，保留 `test_release_source_ci`、`release_source_ci.py`、`protected-release-source-ci` 与全部 41 个既有 negative acceptance surfaces，只增加 H4a suite、critical module 和正反验收；没有改动门槛、exclusions 或 selector。
- 旧 H4a 两个 Attempt 下共 324 个 Git blobs 与 `b9ad97e` 逐项同 object ID，归档证据未改写。
- 本地 dependency check `pip check` 通过；Schema/docs/coverage-policy/CI consumer/exporter 组合 51 PASS；repository validation 186/0/0；重基线后 H4a focused 与 hosted full CI 需绑定最终 head 单独记录。当前 local proof 不构成 Human 接受。

H4a 仍只处理 synthetic actual evidence，M5-007 保持 IN_PROGRESS。PR #96 的 H4b draft 依赖 H4a，但本次不改变 #96 的状态或提出对其合并的决定。

Capture boundary: this addendum preserves deterministic rebase comparison and review decision context. Initial shell/event frames and test timestamps are not complete Agent Trace；旧 H4a archive 的 `TRACE-CAPTURE-DELAYED` warning 继续有效，不以本文件补造历史事件。

## 2026-09-24 H4a source-identity repair

[PR #90 independent review](https://github.com/Chengyue-Lu/research-agent-workbench/pull/90#issuecomment-5814646084) 对 `b1bdba8` 提出一个 P1：A1/A2 cold replay 通过 `baseline_closeout._replay_transport()` 调用 `baseline._request`、`_tool_inputs`、`_plain`，而原 H4a validator identity 未绑定 `execution/baseline.py`；这些函数还将 `adapters.models.port` 的 dataclasses 序列化为请求与 Tool 消息，因此该文件也影响重建结果。

修复只在 H4a `validator_identity()` 增列上述两个直接源码 pin，不改变 M6 producer、历史归档或 H4a 数据 Schema；旧 validator identity 与新版本不相等时，`validate_harness_evidence` 在独立重算前拒绝旧证据。回归测试分别模拟请求 JSON 键顺序和 Tool strict 默认值变化，检验 pin 改变及旧记录拒绝。最终 head、定向测试和 hosted CI 以 PR 的当前提交与 checks 为准；新候选仍须 cross-owner R2 复审。
