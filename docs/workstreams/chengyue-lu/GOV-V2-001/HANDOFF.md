# 下一 AI 窗口接手：Governance v2 与 Action→Resolution 节点

状态：三条分支均已实现并本地验证；未发起新的 review、未合并、未修改远端 ruleset。

本文是跨窗口恢复入口。聊天摘要不作为权威；接手者应先执行只读核对，再按下述顺序工作。

## 1. 共享基线与分支

| 线 | 分支 / 已知提交 | 远端状态 | 合并边界 |
|---|---|---|---|
| shared integration | `develop@5991cafdb7f536cd7b871508de9055d02b558728` | `origin/develop` | PR #25 的 Governance v1 仍是当前有效政策 |
| release | `main@b1d5a5a` | `origin/main` | 只接受同仓库 `develop → main` |
| M8-002 | `agent/method-m8-002-mode-action-contract@def0689` | 已推送；PR #26 Draft | R1 shared contract；未审查、未合并 |
| M8-003 | `agent/method-m8-003-method-resolution@1610d87` | 已推送；无 PR | stacked on M8-002 lineage；R2 Method surface |
| Governance v2 | `governance/v2-risk-based-merge-boundary@9a8953b` | implementation commit | R2 governance；本 handoff 随后追加 |

接手先运行：

```powershell
git fetch --all --prune
git worktree list
git branch -vv
gh pr view 26 --json state,isDraft,headRefOid,baseRefName,reviewRequests,statusCheckRollup,url
gh api repos/Chengyue-Lu/research-agent-workbench/rulesets
```

不得假设上述 hash、CI 或 ruleset 状态仍未变化；按实时回读更新本文或新 Handoff。

## 2. 本轮各分支实际改变

### Governance v2

- `.github/governance-policy.json`：3 PR classes、3 risk tiers、3 finding severities、owner、Task 状态机、
  R1/R2 最低路径；
- governance script：风险自动升级、INFO/WARNING/ERROR、可解释输出、stale-base warning、条件
  workstream/Risk Ledger、Task definition/status/dependency 分离、同 PR completion+activation；
- published Mode Action Registry 的 base/head append-only 检查；
- PR template 删除人工 base SHA、reviewer、独立 closeout 字段；
- CODEOWNERS 删除全局 `*`，保守覆盖 R1/R2 shared/authority paths；
- ADR-0018、Development/AGENTS/workstream/history 与远端 rollout 已同步；PR #25 历史原文只增加
  superseded 提示，不重写当时事实。

### M8-002 / PR #26

- `action_id@version` 明确为 published immutable identity；语义变化必须升版；
- Claim effect 复用 canonical Claim strength，阻断 sides overlap 和 Mode `allows` 越界；
- Human Gate 限为 opaque kebab-case ID；移除任意 Action `metadata` 扩展；
- 16 个 Action YAML 未改变，所以 Registry hash 与下游 Resolution pin 未漂移；
- PR body、workstream、Risk Ledger、Validation 改成不预设旧 `task-closeout`/逐 Task History；
- PR #26 仍是 Draft 且无 review request。

### M8-003

- 已 cherry-pick M8-002 hardening，并更新 Method Resolution workstream 的 Governance v2 R2 要求；
- 当前 `M8-003: IN_PROGRESS` 只表示 isolated stacked branch 工作状态。它从当前 develop 的 PARKED
  直接进入 IN_PROGRESS，不能原样通过 Governance v2 merge-boundary dependency/state checks；
- 正式 PR 前必须等待 M8-002 DONE、M8-003 READY，再 rebase 并采用合法 transition；
- 不创建全局 Resolution Registry，不绑定 Tool/Skill/Model/Provider/Runtime。

## 3. 验证证据

| 分支 | 完整 suite | Repository validation | 重点负面证据 |
|---|---|---|---|
| Governance v2 | `273 passed, 3 skipped` | `59 valid, 0 errors, 0 warnings` | 33 governance tests；risk downgrade、R2 evidence、Task/state/dependency、topology、CODEOWNERS、Action identity |
| M8-002 | `279 passed, 3 skipped` | `76 valid, 0 errors, 0 warnings` | 20 contract/schema focused；Claim/Gate/metadata/identity |
| M8-003 | `289 passed, 3 skipped` | `84 valid, 0 errors, 0 warnings` | Resolution/action hash、Need/Gate/block closure、provider/runtime/Assignment rejection |

三条分支的 `git diff --check` 均通过。测试使用本地 Python 3.14 与仓库 `src/`，未安装在线依赖；
Python 3.11/3.13、coverage、wheel 与 clean-install 以各 PR 的 GitHub CI 为准。结构 PASS 不证明科学正确。

## 4. 建议的节点级审查与交付顺序

可以一次性完成三条线的概念审查，避免逐小步来回；Git 合并仍必须按依赖顺序执行：

1. 审查 Action→Resolution 节点和 Governance v2 authority boundary；修改分别回到所属分支；
2. 先按当前有效 Governance v1 审查并 squash merge PR #26，M8-002 保持 IN_PROGRESS；
3. 为 Governance v2 创建 R2 Draft PR，使用本 workstream、authority basis 和 adversarial evidence；
   cross-owner review/CI 通过后 squash merge 到 `develop`；
4. 通过 `develop → main` release 发布 Governance v2，确认 check 名可用后再按 [ROLLOUT](ROLLOUT.md)
   配置并回读 develop/main rulesets；不得提前设置不存在的 required checks；
5. 用 Governance v2 `feature` 状态机提交 `M8-002: IN_PROGRESS → DONE` 与
   `M8-003: PARKED → READY`。这只是一次迁移期状态 progression，不使用 retired closeout class；
6. 将 M8-003 rebase 到该 develop，解决 TASKS/文档基线，重跑完整验证；创建 R2 PR，并在同一 PR
   采用合法 `M8-003: READY → DONE`（或先 IN_PROGRESS，若 owner 尚不作 completion judgment）；
7. 节点完成后再决定 M8-004/M8-005，不在本轮继续扩张。

## 5. Review 要点

- Governance：R0 是否真的无需 workstream/SHA/reviewer；R1/R2 是否无法通过低报绕开；
- CODEOWNERS：无全局 wildcard，同时 R1 schema/registry/protocol 和 R2 governance/architecture 仍硬审；
- Task：DONE immutable、definition class、状态机、dependency head snapshot 与 combined transition；
- Action：同 `action_id@version` 的 Registry entry 是否 base/head append-only；
- Method：Resolution 是否只表达 Task-specific 决定，没有成为固定 DAG、第二 Router 或 Runtime binding；
- Authority：机器证据只证明结构资格，completion、Method/Claim/Gate 与 release 决定仍属于具名人类。

## 6. 已知限制与禁止动作

- changed-path inference 是确定性下界，不是完备语义分类器；已知 Method/Claim/Gate 文件列入 R2，
  PR declaration 与 cross-owner review 处理剩余语义判断；
- CODEOWNERS 对混合公共文件的内部 refactor 可能产生保守 false positive；当前接受，不要为降摩擦
  删除 shared-contract 保护；
- 远端当前没有已确认启用的 ruleset；不得写成已保护；
- 不要直接 push/force/delete `develop` 或 `main`；
- 不要合并 M8-003 当前 stacked TASKS snapshot；
- 不要修改 Provider/API/Runtime 分工、Resolved Execution View、M8-004/005 或具体 Skill binding；
- 不要把私有治理原文提交。固定来源 `GOV-V2-SPEC-20260823` 的 SHA-256 为
  `6bdcc987236e51af1f7dc01906588d5a5ca987b90e779991e731bfc21ff293bf`。

若外部状态无变化，下一 AI 的第一项实际工作应是：核对三分支远端与 PR #26 CI，然后准备一次
节点级 review package；不要继续新增实现。
