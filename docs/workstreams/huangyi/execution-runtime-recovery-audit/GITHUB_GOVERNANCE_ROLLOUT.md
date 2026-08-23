# GitHub 治理 rollout

状态：`PARTIAL — PR #23 hard-block complete; rulesets / merge settings / retarget pending`。
远端状态以 2026-08-23 核对为准；完成每项后记录链接或规则 revision，不能把仓库内配置文件
误写成 GitHub 已启用的保护。

## 1. 初始核对结果（操作前快照）

- `main` 与 `develop` 都是 `b1d5a5a5850e0e7541e4c460f15384cd45357ab2`；
- 两个分支均显示 `protected=false`，没有 required checks；
- PR #23 为 open、非 Draft，base `main@b1d5a5a`，head `57b3d24`，无 label/reviewer/review；
- PR #20 与 PR #24 也以 `main@b1d5a5a` 为 base；当前 `main==develop`，但尚未完成 retarget；
- 当时的 API 集成没有仓库写权限；该限制不代表 GitHub 网页中的具名账户没有写权限。

## 2. 2026-08-23 已实施的远端治理

- 黄毅的 GitHub 主名 `let778750-cpu` 与昵称/界面名 `huangyi855` 已由本人确认为同一账户；
- [PR #23](https://github.com/Chengyue-Lu/research-agent-workbench/pull/23) 保持 open、base
  `main@b1d5a5a`、head `57b3d24`，并已转为 Draft；
- PR #23 已添加 `blocked` 与 `do-not-merge`；后者颜色为 `B60205`，说明为
  `Must not merge until a clean replacement satisfies canonical TASKS and architecture review`；
- PR #23 已向 `Chengyue-Lu` 发出 reviewer request；截至
  `2026-08-23T07:51:44Z`，submitted reviews 仍为 `0`。同时已发布固定 base/head 的
  [hard-block 说明](https://github.com/Chengyue-Lu/research-agent-workbench/pull/23#issuecomment-5384190781)；
- [PR #24](https://github.com/Chengyue-Lu/research-agent-workbench/pull/24) 已删除“待 PR #23
  合入”的错误依赖，改为 M8-003 后独立的 Execution Boundary Contract / K-API-2 修复边界；base
  仍为 `main`，尚未 retarget；
- 当前 `main`/`develop` 仍为 `protected=false`，required checks 为空；治理提交尚未进入
  `develop`/`main`，因此不能先把尚不存在于目标分支的 `governance` check 设为 required；
- 治理检查发布后，branch ruleset 与 merge settings 仍需 `Chengyue-Lu` 或 Repo Admin 配置，当前
  不得写成已保护。

## 3. 仓库内门禁

本 workstream 提供：

- `.github/CODEOWNERS`：两位 accountable owner 共同覆盖；
- `.github/pull_request_template.md`：强制 Task、workstream、base、契约、风险和验证字段；
- `.github/scripts/check_pr_governance.py`：验证 `feature → develop → main` 拓扑、最新 base、
  workstream 存在、目录 owner 与责任人一致、跨 owner、TASKS 不被 feature 重定义/置 DONE，
  task-definition 的实际变更 Task ID 与 PR 声明精确一致，以及独立 task-definition/closeout；
- CI `governance`、Python 3.11/3.13、Schema/Registry、coverage、wheel 与 clean-install checks。

这些文件先经 `develop`/`main` 正常发布；随后才能把新 `governance` check 设为 required，避免
创建一个默认分支上尚不存在、因而永远无法通过的必需检查。

## 4. PR #23 hard-block

以下动作已经完成，并继续作为不可回退的治理约束：

1. 将 PR #23 转为 Draft；
2. 复用现有 `blocked`，新增唯一必要标签 `do-not-merge`，不要再造同义 `hard-block`；
3. 请求 `Chengyue-Lu` 审查；
4. 留下固定 base/head 的阻断说明，至少列出 TASKS 越权、数据出口、原始 transcript、未知敏感
   状态、Trace 断链、权限前置、summary→fact、observed model 和伪 recovery；
5. 不 retarget 到 `develop`，不 merge/rebase-merge/批量 cherry-pick；洁净替代实现合并后再关闭，
   保留 PR 历史。

实际标签：`do-not-merge`，颜色 `B60205`，说明：
`Must not merge until a clean replacement satisfies canonical TASKS and architecture review`。

## 5. 分支 ruleset

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

## 6. 现有黄毅分支

- PR #20 与 PR #24 在去除跨分支依赖、核对 diff 干净后分别 retarget 到 `develop`；二者保持独立，
  不成为 M8-002/M8-003 前置；
- PR #24 的 M6-007 文案已解除 PR #23 依赖；仍须在治理发布后核对 diff 与 CI，才可 retarget；
- `agent/k-api-2-rework` 永不继承到 `develop`；M8-003 合并后从当时最新 `develop` 新建洁净分支。

## 7. 完成证据

PR #23 Draft、labels、comment 与 reviewer request 已有可回读证据；实际 review/approval 仍未发生。
远端 rollout 只有在本治理 workstream 的 develop/main PR 与 commit、两份 ruleset revision、merge
settings 截图或 API 回读，以及 PR #20/#24 的新 base SHA 齐全后才能标为完成。缺少 Admin 权限是
待外部授权动作，不得伪造 PASS。
