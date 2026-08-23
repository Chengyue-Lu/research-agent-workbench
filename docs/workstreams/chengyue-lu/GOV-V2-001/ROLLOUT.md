# Governance v2 远端 rollout

状态：pending；仓库 API 回读显示当前没有已启用 ruleset。未合并政策不得先施加到共享分支。

## 合并前

1. Governance v2 以 R2 PR 指向 `develop`；
2. cross-owner 明确审查 authority boundary 与 adversarial evidence；
3. governance、Python 3.11/3.13、Schema/Registry、coverage、wheel/clean-install 全部通过；
4. 确认 workflow check 名实际为 `governance`、`test (3.11)`、`test (3.13)`；
5. squash merge 后用一个 `develop → main` release 发布，之后才设置 required checks。

## develop ruleset

- require PR；global approval count `0`；require Code Owner review；dismiss stale approval；
- require `governance`、`test (3.11)`、`test (3.13)`，strict merge-ref integration；
- require conversation resolution；block direct push、force push、delete；
- linear history；仓库允许 squash merge，禁止 rebase merge。

普通 R0 不匹配 CODEOWNERS，因此无需人工 approval；R1/R2 sensitive paths 触发另一位 owner。

## main ruleset

- require PR 和至少 `1` approval，dismiss stale，require conversation resolution；
- required checks 同上；block direct push、force push、delete；
- 不要求 linear history，以允许 `develop → main` merge commit；
- governance 脚本继续阻断任何非同仓库 exact `develop` 来源。

## 回读证据

配置后记录 ruleset ID/revision、enforcement、bypass actors、required checks、approval/count、
Code Owner、conversation、force/delete 和 merge settings。缺少 Admin 权限或尚未配置时保持 pending，
不得把仓库文件误写成远端已经受保护。
