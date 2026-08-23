# `develop` → `main` 发布合并规范

状态：Stable release rules  
更新：2026-08-24

本文规定已在 `develop` 集成的项目状态如何进入 `main`。这里的“发布”是仓库稳定线发布，表示
项目接受该提交集为共享真值；它不自动表示公开发行、许可证问题解决、真实 Provider 兼容、科研
有效性或产品成熟度已经获批。

## 1. 唯一允许的拓扑

```text
feature / task-definition branch
        │ squash merge
        ▼
     develop
        │ same-repository release PR + merge commit
        ▼
       main
```

- `main` 只接受同一仓库中以精确 `develop` 分支为 head 的 PR；
- release PR 的 base 必须是 `main`，PR class 必须是 `release`；
- 禁止从 feature、个人、临时汇总、fork 或重新拼装的 release branch 直接进入 `main`；
- 紧急修复仍先进入 `develop`，不得以紧急为由绕过 CI、审查或 authority gate；
- 禁止直接 push、force push 或删除 `develop` / `main`。

该拓扑由 `.github/scripts/check_pr_governance.py` 校验。GitHub ruleset 负责远端阻断；仓库规则与
ruleset 两者都生效后，才能宣称分支受到完整保护。

## 2. 创建 release PR 前

发布负责人必须先确认：

1. `origin/develop` 与 `origin/main` 已重新获取，拟发布 head 确为当前远端 `develop`；
2. 所含 feature/task-definition PR 均已在 `develop` 完成各自要求的 CI 与审查，不在 release PR 中
   偷渡新的实现、Task 定义或 authority 决定；
3. `develop` 的完整 CI 通过，工作树干净，且与 `main` 无未解决冲突；
4. `STATUS.md`、`TASKS.md`、迁移说明、已知限制和必要 History 能准确描述拟发布状态；
5. 涉及治理、架构、共享契约、权限、数据、Method/Claim/Gate 或 Runtime authority 时，原变更的
   具名 owner、跨 owner 审查与证据仍可追溯；
6. 明确本次仓库发布不解除仍存在的许可证、外部发布、真实环境、科学正确性或净收益 Gate。

若 `develop` 在审查期间前进，release PR 会随 exact `develop` 自动扩大范围。负责人必须重新检查
新增提交和 CI；不得把“最初看过旧 head”当成对新 head 的批准。若不能接受新增范围，应暂停发布，
先在 `develop` 完成分段或回退决定，而不是建立替代 release branch 绕开 exact-head 规则。

## 3. PR 元数据与审查

release PR 使用仓库模板，并至少填写：

- `PR 类型: release`；
- `任务 ID`：通常为 `none`，release 不重新定义或完成 Task；若治理器要求正式 Audit ID，则使用
  对应已存在的 release/governance workstream，不临时伪造 Task；
- `风险等级`：不得低于本次 diff 推导出的有效风险；
- `责任人`：对本次发布边界作判断的具名维护者；
- `工作流目录`、authority basis 与 adversarial evidence：按有效风险和仓库治理器要求填写；
- 范围、已纳入提交/PR、验证证据、残余风险和明确未发布内容。

至少一名具备相应 authority 的维护者审查 release PR。若 head 在批准后变化，应重新确认最新 diff；
未解决 conversation、失败/缺失的必需检查、冲突或 Governance `ERROR` 均阻断合并。

## 4. 合并方式

- release PR 使用 **merge commit**，不使用 squash、rebase merge 或手工 cherry-pick；
- merge commit 是一次稳定线发布边界，并保留 `develop` 的集成历史；
- 不在 GitHub 网页或本地额外修改 release 内容；任何修复先通过正常 PR 进入 `develop`，然后由同一
  release PR head 自然纳入；
- 合并后回读 `main` head、release PR 的 `mergedAt`/merge commit、必需检查与 branch protection；
- 若本次发布触发 History、迁移或远端 ruleset rollout，按对应 workstream 完成记录和验证。

## 5. 合并后的边界

- `main` 成为已接受共享真值；`develop` 继续作为下一批变更的唯一集成线；
- feature 分支不得改以 `main` 为日常集成目标；
- 远端分支清理只删除已合并且不再承担审计/恢复用途的分支，不删除 `main`、`develop` 或他人活动分支；
- 仓库稳定线发布与公开制品发布是两件事。缺少 LICENSE、外部数据/模型授权、真实 conformance、
  安全审查或科学证据时，必须继续保持对应 Gate，不得因进入 `main` 而改写为已完成。

日常 feature/task-definition 规则见[开发协作指南](DEVELOPMENT.md)，远端保护部署见相应 Governance
workstream 的 rollout 记录。
