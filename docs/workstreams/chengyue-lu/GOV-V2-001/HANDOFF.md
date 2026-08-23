# 下一 AI 窗口接手：Governance v2 与 Action→Resolution 节点

状态：Governance v2 与统一 M8 节点均已实现并本地验证；Governance v2 已提交 Draft PR #27，
PR #26 已撤回且未合并；未发起 review、未合并、未修改远端 ruleset。

本文是跨窗口恢复入口。聊天摘要不作为权威；接手者应先执行只读核对，再按下述顺序工作。

## 1. 共享基线与分支

| 线 | 分支 / 已知提交 | 远端状态 | 合并边界 |
|---|---|---|---|
| shared integration | `develop@5991cafdb7f536cd7b871508de9055d02b558728` | `origin/develop` | PR #25 的 Governance v1 仍是当前有效政策 |
| release | `main@b1d5a5a` | `origin/main` | 只接受同仓库 `develop → main` |
| 统一 M8 节点 | `agent/method-m8-action-resolution-node@d791b4e` | 已推送；暂不建 PR | M8-002 与 M8-003 两个旧 head 均为其祖先；未来作为一个 R2 节点交付 |
| M8 历史引用 | `agent/method-m8-002-mode-action-contract@def0689`、`agent/method-m8-003-method-resolution@1610d87` | 保留但停止开发；PR #26 CLOSED、未合并 | 仅供历史与审计追溯 |
| Governance v2 | `governance/v2-risk-based-merge-boundary@f504bf8` | Draft PR #27 | R2 governance；等待 CI 与跨负责人审查 |

接手先运行：

```powershell
git fetch --all --prune
git worktree list
git branch -vv
gh pr view 26 --json state,isDraft,mergedAt,headRefOid,baseRefName,url
gh pr view 27 --json state,isDraft,headRefOid,baseRefName,reviewRequests,statusCheckRollup,url
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

### 统一 M8 Action→Resolution 节点

- `action_id@version` 明确为 published immutable identity；语义变化必须升版；
- Claim effect 复用 canonical Claim strength，阻断 sides overlap 和 Mode `allows` 越界；
- Human Gate 限为 opaque kebab-case ID；移除任意 Action `metadata` 扩展；
- 16 个 Action YAML 未改变，所以 Registry hash 与下游 Resolution pin 未漂移；
- Method Resolution 已完整建立，并保持 no-Skill、Skill Need、Human Gate、blocked 与 split 为一级结果；
- 原 M8-002 与 M8-003 head 已通过 merge commit 收束到 `agent/method-m8-action-resolution-node`；
- PR #26 已撤回且未合并，旧分支与 CI/讨论只作为历史证据保留；
- 统一 M8 分支在 Governance v2 生效并形成合法 Task snapshot 前不创建 PR。

当前 `M8-003: IN_PROGRESS` 只表示 isolated node branch 工作状态。它从当前 develop 的 PARKED
  直接进入 IN_PROGRESS，不能原样通过 Governance v2 merge-boundary dependency/state checks；
- 正式 PR 前必须先在统一分支形成 M8-002 DONE、M8-003 READY 的合法 merge snapshot；
- 不创建全局 Resolution Registry，不绑定 Tool/Skill/Model/Provider/Runtime。

## 3. 验证证据

| 分支 | 完整 suite | Repository validation | 重点负面证据 |
|---|---|---|---|
| Governance v2 | `273 passed, 3 skipped` | `59 valid, 0 errors, 0 warnings` | 33 governance tests；risk downgrade、R2 evidence、Task/state/dependency、topology、CODEOWNERS、Action identity |
| 统一 M8 节点 | `289 passed, 3 skipped` | `84 valid, 0 errors, 0 warnings` | Action Claim/Gate/identity；Resolution hash/closure；provider/runtime/Assignment rejection |

两个活动分支的 `git diff --check` 均通过。测试使用本地 Python 3.14 与仓库 `src/`，未安装在线依赖；
Python 3.11/3.13、coverage、wheel 与 clean-install 以各 PR 的 GitHub CI 为准。结构 PASS 不证明科学正确。

## 4. 建议的节点级审查与交付顺序

可以按完整节点审查，避免逐小步来回；Git 合并仍必须按依赖顺序执行：

1. 审查 Draft PR #27 的 Governance v2 authority boundary；修改只落到 governance 分支；
2. cross-owner review/CI 通过后，将 Governance v2 squash merge 到 `develop`；
3. 通过 `develop → main` release 发布 Governance v2，确认 check 名可用后再按 [ROLLOUT](ROLLOUT.md)
   配置并回读 develop/main rulesets；不得提前设置不存在的 required checks；
4. 将统一 M8 分支更新到新的 `develop`，用 Governance v2 `feature` 状态机形成
   `M8-002: IN_PROGRESS → DONE` 与
   `M8-003: PARKED → READY`。这只是一次迁移期状态 progression，不使用 retired closeout class；
5. 重跑完整验证并为统一 M8 节点创建一个 R2 PR；M8-003 在该 PR 保持 READY，除非 owner 已有充分
   completion judgment 并能采用治理允许的状态转换；
6. 节点完成后再决定 M8-004/M8-005，不在本轮继续扩张。

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
- 不要合并统一 M8 分支当前的隔离开发 TASKS snapshot；
- 不要修改 Provider/API/Runtime 分工、Resolved Execution View、M8-004/005 或具体 Skill binding；
- 不要把私有治理原文提交。固定来源 `GOV-V2-SPEC-20260823` 的 SHA-256 为
  `6bdcc987236e51af1f7dc01906588d5a5ca987b90e779991e731bfc21ff293bf`。

若外部状态无变化，下一 AI 的第一项实际工作应是：核对 PR #27 的 CI 与 review 状态，准备
Governance v2 R2 审查；不要继续新增 M8 实现或重开 PR #26。
