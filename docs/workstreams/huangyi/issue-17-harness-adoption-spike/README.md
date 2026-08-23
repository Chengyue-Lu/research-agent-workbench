# Issue #17：Harness Adoption Spike

- owner：黄毅（GitHub `let778750-cpu`）
- required reviewer：路诚钺（GitHub `Chengyue-Lu`）
- workstream ID：`ISSUE-17-HARNESS-ADOPTION`
- Issue：[GitHub #17](https://github.com/Chengyue-Lu/research-agent-workbench/issues/17)
- PR：[GitHub #20](https://github.com/Chengyue-Lu/research-agent-workbench/pull/20)
- current branch：`agent/issue-17-harness-adoption-spike`
- original base：`main@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- target integration branch：`develop`（治理基线发布后 rebase/retarget）
- 状态：实现候选；不阻断 M8-002/M8-003，不代表外部 Runtime 准入

## 范围

- 用一手来源按机制比较 Codex App Server 与 DeepSeek Harness，形成 Adoption Matrix；
- 实现从已验证 Trace 中重建最后一个 provider-neutral `ModelRequest` 的窄 spike；
- 保持 PR #20 与 Issue #21/PR #24、PR #23、M8 主线相互独立；
- rebase 后按最新治理模板补齐 base SHA、风险和 clean-checkout 证据。

写入范围：`docs/references/HARNESS_ADOPTION_MATRIX.md`、request reconstruction 实现/导出/测试和
本 workstream。没有 TASKS/STATUS/ROADMAP/ADR 变更权限。

## 语义限定

`reconstruct_last_provider_request` 只重建已持久化并通过 hash/envelope 校验的最后一个
provider-neutral `ModelRequest`。它不证明：

- Provider SDK/HTTP 的逐字节请求完全相同；
- 远端模型内部状态、采样或响应可重放；
- 原始本地正文可安全持久化；
- audit replay 等于模型 bitwise replay。

外部项目的机制只能作为设计证据；ADR-0010 的 API-first isolated baseline 不因此重开，任何
native-agent、router、multi-agent 或自动 fallback 接入都需要独立 Task/Gate。

## 非目标

- 不实现或继承 PR #23/K-API-2；
- 不引入 JSON-RPC、常驻 host、后台 Agent、teams/workflow UI 或隐式路由；
- 不改变 Method、Mode、Method Resolution、Registry、权限或 Human Gate；
- 不把外部框架项目名本身作为采用理由。

## 验证与合并

原 PR 记录 238 passed / 3 skipped 及 4 个 reconstruction 正反测试；这些结果必须在最新
`develop` 的干净检出中重跑，并补 Python 3.11/3.13、Registry、wheel 和 cross-owner review。

治理基线发布后，本分支 rebase 到当时最新 `develop`，PR #20 retarget 到 `develop` 并 squash
merge。只有后续 `develop → main` 发布完成后，才在 `docs/history/` 写具名 closeout，记录最终
来源 revision、验证、局限和是否关闭 Issue #17。
