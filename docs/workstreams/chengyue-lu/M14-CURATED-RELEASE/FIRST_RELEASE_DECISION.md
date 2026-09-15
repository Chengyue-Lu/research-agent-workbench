# M14-005 v0.1.0 准备授权与外部 Gate 回读

- 决定人：路诚钺（`Chengyue-Lu`）。
- 决定日期：2026-09-15；来源：维护者在当前任务中明确回复“确认上述 v0.1.0 范围与准备授权”。
- 关联：[PR #80 review](https://github.com/Chengyue-Lu/research-agent-workbench/pull/80#issuecomment-5680900745)、
  [Issue #57](https://github.com/Chengyue-Lu/research-agent-workbench/issues/57)、[ADR-0021](../../../decisions/0021-CURATED-DEVELOP-TO-MAIN-RELEASE.md)。
- 本次候选的开发基线：`7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba`。

## 具名决定

维护者确认首个 curated release 的版本为 **v0.1.0**，定位为内部技术 alpha。
内容范围为届时冻结 develop 的完整产品源码、全部已发布 Schema、Runtime 必需的公开 Registry、MIT
许可、构建/包元数据、公开用户文档及 curated 离线 no-Skill Quickstart；具体路径和受控生成文件由
版本化 allowlist 确定。开发资料、tests、workstream、Task/评估历史继续留在 develop。

维护者接受当前 **structural / bounded** 成熟度及以下限制：生产 Skill Projection 为空，无 live Provider
保证，无已完成的 M5 系统净收益实证。首发不将这些边界提升为已证明能力，也不新增 Skill 准入。

在下述远端保护回读通过的基础上，维护者授权 **M14-005 BLOCKED → READY**，开展该 Task 的实现与
cutover 准备。PR #80 由此获得当前候选的 Task 授权；原先保持 BLOCKED 的历史提交与冻结 Attempt
保留为当时事实。这一决定不是对历史授权时间的追溯改写。

本决定确定版本、内容类别与准备范围。它不固定最终 source/parent SHA，也不批准 PR #80 自行合并、
最终 release PR 合并或 tag。具体 source、parent、policy、manifest、projection、工件及风险须在发布
候选形成后审查，最终发布动作由维护者另行批准。实际 topology cutover 仍以全部机器门禁及 R2 验收为前提。

## 外部 readiness 回读

2026-09-15 14:41:58 UTC，使用 GitHub 只读 API 同时核对 ruleset 内容、branch protection 标记与
effective rules。四层均 active；配置与 effective rules 一致。本次没有修改远端配置。

| 分支 | 回读 tip（仅观察，不是发布冻结） | hard / review ruleset | 合并方式 |
|---|---|---|---|
| develop | `7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba` | `23305447` / `23192001` | squash |
| main | `b1d5a5a5850e0e7541e4c460f15384cd45357ab2` | `23305460` / `23192054` | merge commit |

- hard 层无 bypass，要求 PR、conversation resolution、禁止删除/force push，并要求最新 base 上的
  `governance`、`test (3.11)`、`test (3.13)`；检查来源绑定 GitHub Actions App `15368`。
- review 层要求 Code Owner review、新提交撤销旧审核；develop 全局 approval 为 0，main 为 1 并要求
  last-push approval。唯一 bypass 是 Chengyue-Lu（User `140945476`）的 `pull_request` 模式，
  仅按既有单次例外制度使用；本决定没有批准任何单次审核例外。
- canonical 依赖 `M0-007`、`M1-009`、`M14-002`、`M14-003`、`M14-004` 在该基线均为 DONE。
  `GITHUB-RELEASE-PROTECTION-GATE` 由上述外部读回证据满足，Task 定义与依赖未改写。

原始回读、SHA-256 清单及决定转录见本轮修复 Attempt；其入口由 PR #80 保留。
远端保护的观察只绑定本次时间，cutover/发布前仍需 fresh readback，漂移时重新核对。

## 接续验收

1. PR #80 的 READY 状态、source-CI 实现与本决定一起接受 R2 review 和最终 head CI。
2. 合入后验证真实 protected develop push，并在相同 source checkout 执行在线 `attest`。
   `source-governance.json` 仅为审计附件；其存在或内容不替代在线信任校验，见 [source CI](SOURCE_CI.md)。
3. 继续 release-only workflow/checks、policy include 与 atomic cutover 准备；全部门禁满足后再形成
   exact source/parent 的发布候选，校验 projection/prospective-tree equality、安装与公开表面。
4. 最终 release PR 和 tag/artifact/hash closure 单独验收并取得发布批准。
