# M6-007 / Issue #21：Trace Schema Export

- owner：黄毅（GitHub `let778750-cpu`）
- required reviewer：路诚钺（GitHub `Chengyue-Lu`）
- Task：`M6-007`
- Issue：[GitHub #21](https://github.com/Chengyue-Lu/research-agent-workbench/issues/21)
- PR：[GitHub #24](https://github.com/Chengyue-Lu/research-agent-workbench/pull/24)
- current branch：`agent/issue-21-trace-schema-export`
- original base：`main@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- target integration branch：`develop`（治理基线发布后 rebase/retarget）
- 状态：实现候选；未进入 `develop`/`main`，不能声明 Task DONE

## 范围

- 导出与 Trace baseline/version/hash 绑定的 Schema bundle；
- 固化 Provider capability snapshot 的冻结不变量和离线测试；
- 保持独立于 PR #20、PR #23、M8-002 与 M8-003；
- 在 rebase 后按最新治理模板补齐 base SHA、风险和 clean-checkout 证据。

写入范围：Trace schema export 实现/CLI/测试、Provider conformance 冻结测试、本 workstream 和
[`TASKS.md`](../../../TASKS.md) 中 M6-007 的非完成定义。任何 Task 定义变更在新治理生效后应由
独立 `task-definition` 路径先进入 `develop`，再从本功能 PR 去除重复 diff。

## 非目标

- 不实现或继承 K-API-2；
- 不等待 PR #23，也不把 PR #23 retarget、merge、rebase-merge 或 cherry-pick 到 `develop`；
- 不实现 API session enforceable/advisory 对齐、Execution Boundary Contract 或 M8 Method
  Resolution；
- 不改变现有 Trace 物理格式、Method/Mode/Registry 语义或引入常驻 host。

## 当前验证与未证明内容

原 PR 记录全量测试、bundle hash/tamper 与 CLI e2e；2026-08-23 的 PR #23 解耦提交
`c1efdc0facb81053108d7a1ea57b83d5f00974b3` 另通过文档链接测试和 `git diff --check`。

这些证据仍需在最新 `develop` 的干净检出中重跑。尚未证明 Python 3.11/3.13 在 rebase 后通过，
尚未获得 cross-owner review，也未完成 `develop` 集成。

## 合并与 history

1. 先发布仓库治理基线；
2. 通过独立 task-definition 审查把 M6-007 的最终非 DONE 定义加入 `develop`；
3. 本分支 rebase 到当时最新 `develop`，移除重复 TASKS diff，保持实现范围不变；
4. 更新 PR #24 base/body，跑 required CI 并由路诚钺审查；
5. squash merge 到 `develop`，随后随完整 workstream 的 `develop → main` release 发布；
6. 只有发布后才在 `docs/history/` 写 closeout，记录最终验证、限制和遗留项。
