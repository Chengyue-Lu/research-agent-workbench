# GitHub 治理 rollout

状态：执行清单。远端状态以 2026-08-23 只读核对为准；完成每项后记录链接或规则 revision，
不能把仓库内配置文件误写成 GitHub 已启用的保护。

## 1. 当前核对结果

- `main` 与 `develop` 都是 `b1d5a5a5850e0e7541e4c460f15384cd45357ab2`；
- 两个分支均显示 `protected=false`，没有 required checks；
- PR #23 为 open、非 Draft，base `main@b1d5a5a`，head `57b3d24`，无 label/reviewer/review；
- PR #20 与 PR #24 也以 `main@b1d5a5a` 为 base；当前 `main==develop`，但尚未完成 retarget；
- 当前执行客户端没有仓库写入或管理权限，因此本文件不能宣称远端操作已经完成。

## 2. 仓库内门禁

本 workstream 提供：

- `.github/CODEOWNERS`：两位 accountable owner 共同覆盖；
- `.github/pull_request_template.md`：强制 Task、workstream、base、契约、风险和验证字段；
- `.github/scripts/check_pr_governance.py`：验证 `feature → develop → main` 拓扑、最新 base、
  workstream 存在、跨 owner、TASKS 不被 feature 重定义/置 DONE，以及独立 task-definition/closeout；
- CI `governance`、Python 3.11/3.13、Schema/Registry、coverage、wheel 与 clean-install checks。

这些文件先经 `develop`/`main` 正常发布；随后才能把新 `governance` check 设为 required，避免
创建一个默认分支上尚不存在、因而永远无法通过的必需检查。

## 3. PR #23 hard-block

由有写权限的维护者按顺序完成：

1. 将 PR #23 转为 Draft；
2. 复用现有 `blocked`，新增唯一必要标签 `do-not-merge`，不要再造同义 `hard-block`；
3. 请求 `Chengyue-Lu` 审查；
4. 留下固定 base/head 的阻断说明，至少列出 TASKS 越权、数据出口、原始 transcript、未知敏感
   状态、Trace 断链、权限前置、summary→fact、observed model 和伪 recovery；
5. 不 retarget 到 `develop`，不 merge/rebase-merge/批量 cherry-pick；洁净替代实现合并后再关闭，
   保留 PR 历史。

建议标签：`do-not-merge`，颜色 `B60205`，说明：
`Must not merge until a clean replacement satisfies canonical TASKS and architecture review`。

## 4. 分支 ruleset

先让包含治理检查的 release PR 在默认分支通过，再由 Repo Admin 配置：

| 规则 | `develop` | `main` |
|---|---|---|
| Require pull request | 是 | 是 |
| Required approvals | 1、dismiss stale、require Code Owner、require approval after last push | 同左 |
| Required checks | `governance`、`test (3.11)`、`test (3.13)`，strict/up to date | 同左 |
| Conversation resolution | 是 | 是 |
| Block force push/delete/direct push | 是 | 是 |
| Linear history | 是（确保 feature squash） | 否（允许 release merge commit） |

仓库 merge 设置保留 squash merge 与 merge commit，禁用 rebase merge。来源限制由 `governance`
检查实施：`main` 只接受同仓库 exact `develop`。

## 5. 现有黄毅分支

- PR #20 与 PR #24 在去除跨分支依赖、核对 diff 干净后分别 retarget 到 `develop`；二者保持独立，
  不成为 M8-002/M8-003 前置；
- PR #24 的 M6-007 文案不得再写“待 PR #23 合入”；修正后才 retarget；
- `agent/k-api-2-rework` 永不继承到 `develop`；M8-003 合并后从当时最新 `develop` 新建洁净分支。

## 6. 完成证据

远端 rollout 只有在以下证据齐全后才能标为完成：PR #23 Draft 与 labels/comment/reviewer 链接、
本治理 workstream 的 develop/main PR 与 commit、两份 ruleset revision、merge settings 截图或 API
回读，以及 PR #20/#24 的新 base SHA。缺少 Admin 权限是待外部授权动作，不得伪造 PASS。
