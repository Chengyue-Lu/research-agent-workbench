# 远端审核例外分层记录

授权人：路诚钺（`Chengyue-Lu`）；2026-09-14 接受 reviewer 不可用时由自己一侧批准单次例外，无默认等待。

部署前：develop ruleset `23192001`、main ruleset `23192054` 均 active，包含 PR/审批/checks/force/delete，bypass 为空。
实施顺序：先创建并回读无 bypass 的 hard layers，再将原两条规则改为 review-only + 指定 User 的 PR-only bypass。
每次配置回读、身份/branch tips、请求原文和负例验证保存到本 Audit 的 Attempt。

## 已执行的配置

| 分支 | 无 bypass 的硬门禁 | 审核层 | 唯一审核 bypass |
|---|---|---|---|
| develop | [23305447](https://github.com/Chengyue-Lu/research-agent-workbench/rules/23305447) | [23192001](https://github.com/Chengyue-Lu/research-agent-workbench/rules/23192001) | User `140945476`，`pull_request` |
| main | [23305460](https://github.com/Chengyue-Lu/research-agent-workbench/rules/23305460) | [23192054](https://github.com/Chengyue-Lu/research-agent-workbench/rules/23192054) | User `140945476`，`pull_request` |

四条 ruleset 均 active，使用 exact branch ref，无 exclude。身份回读将 user ID `140945476` 绑定为
`Chengyue-Lu`；没有向 admin 角色、另一 owner、App 或其他用户授予 bypass。

硬门禁保留 PR、develop squash/main merge、conversation resolution、三个 required checks
（`governance`、`test (3.11)`、`test (3.13)`，GitHub Actions app `15368`）、strict latest-base 与
force/delete 阻断。其审批数为 0、Code Owner/last-push/stale/extra-unattributed approval 关闭，
这些审核条件保留在可单独例外的审核层，避免硬门禁暗含第二人审批要求。

各请求与回读字段一致，effective branch rules 同时包含两层完整规则；迁移期间原保护保持到两个
hard layers 已创建并核对后，才更新审核层。8 个离线配置负例均被拒绝：hard bypass、错误用户、
always/exempt、缺 check、merge method 漂移、审核条件漂移和硬门禁残留额外审批。

main/develop branch API 均保持 protected，配置前后 tips 相同：

- develop：`f7a9715ed35787d3326283c22f834b1514c5c88c`；
- main：`b1d5a5a5850e0e7541e4c460f15384cd45357ab2`。

未执行 merge、直推、force/delete 探测；回读证明配置及组合覆盖，不冒充破坏性操作的实际拒绝结果。
原 M14 readiness 的无 bypass 快照保留为部署历史，当前远端保护以本次分层记录及合并前 fresh readback 为准。
本次启用没有授予任何具体 PR 的例外合并权。

## 验证档案

[Attempt index](../../../../work/GOV-REVIEW-EXCEPTION-001/A-20260914-001/INDEX.yaml) 与
[验证汇总](../../../../work/GOV-REVIEW-EXCEPTION-001/A-20260914-001/outputs/VERIFICATION.json)
绑定实现提交 `7ce9ad6aefaf0f81a244f48a7baf7729bad6ce2f`。103 项 focused checks、repository 186/0/0
及治理检查 PASS；本地计划 coverage execution 为 1213 PASS + 4 skip，impact coverage policy PASS，
治理器 line 98.06% / branch 97.60%。这不是 repository-global coverage 声明。
独立 worktree 首次缺少构建生成的 runtime pin，完成自身 editable install 后 repository 验证通过；失败与恢复均留证。
Trace 无 BLOCK，保留 capture-gap warning；最终提交的 hosted CI 以 PR 当前回执为准。
