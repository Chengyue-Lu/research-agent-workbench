# Curated main 发布合并规范

状态：Stable release rules

`develop` 保存完整工程真相，frozen develop commit 是产品内容与 provenance 来源；exact current
`main` 是生成式 release branch 的 Git 父提交。发布不自动证明真实 Provider、科学有效性、M5 净收益
或 Skill 准入。架构依据见 [ADR-0021](decisions/0021-CURATED-DEVELOP-TO-MAIN-RELEASE.md)。

## 1. 允许的拓扑

```text
feature / task-definition → develop → frozen source Git blobs
                                        │ deterministic complete projection
exact current main ── Git parent ──→ release/vX.Y.Z → main merge commit
```

- 普通实现与语义修复通过 PR、CI 和相应 owner 审查进入 `develop`；
- active curated topology 只接受同仓库 canonical `release/vMAJOR.MINOR.PATCH → main`，拒绝 direct
  `develop → main`、fork、feature head、非 canonical version 和 release branch 回并 develop；
- release branch 由 exporter 完整生成；产品字节只来自 frozen source 或 policy 声明的 deterministic
  generated inputs，不能在该分支修复产品；
- `main` 使用 merge commit，`develop` 使用 squash；两者禁止 direct push、force push 和删除。

仓库 topology 与 GitHub required contexts 共同保护发布。远端 contexts 尚未切换时，旧 hard gate
继续阻断 curated release；source policy 激活不会自动修改远端规则。实际切换遵循
[cutover runbook](workstreams/chengyue-lu/M14-CURATED-RELEASE/CUTOVER.md)，在一次 main hard-ruleset
更新中替换 required contexts，保持 strict、App identity、review、conversation 与 force/delete 保护。

## 2. 来源、候选与在线治理

发布负责人先确认 M14-005 的 hard dependencies、license、scaffold、package/public closure、远端保护与
具名准备决定。随后从接受的 source 执行以下检查：

1. 冻结 exact source SHA、current main parent、policy/release version、source CI run 和独立 manifest
   SHA-256；这些 pins 在候选之外维护，PR body 或 manifest 不能自报信任事实。
2. 从 clean exact-source checkout 在线验证实际 protected develop CI 的 repository/workflow/run/attempt/
   suite/job/check App 身份与成功状态；保存的 receipts 不能代替新的在线观察。
3. 从 Git blobs 重复构建 projection，验证 source/generated provenance、allowlist、closed outputs、
   Git mode/blob 与 manifest；证明 candidate tree、projection tree 与 prospective main merge-result
   tree 完全相同。main parent 前移必须重新生成。
4. `release_install.py --pr-number NUMBER` 在同次 live preflight 后读取当前 PR 的在线元数据，并以
   该次观察的 source CI 事实调用完整 R2 PR governance。Task/workstream 只从 prerequisite-validated
   frozen source 读取；缺失 authority、adversarial evidence、正式 Task 或可信前提都阻断。
5. 从已验证的投影构建 direct wheel 和 sdist-derived wheel；Python 3.11/3.13 分别在独立环境、空目录
   和受污染路径中执行 package resources、no-Skill、Registry/Projection 与 scaffold 重建检查。
6. 安装结束前重新读取 source/main、CI attempt 与 PR 的 body/head/base/state。观察漂移使该检查失败。
   PR body 编辑也触发双 Python release jobs，不能借用编辑前的治理成功。

开发侧 checker、Task 表、完整测试和 workstream 不进入 public candidate。workflow 先检验同仓库
canonical head 与 external pins，再 checkout frozen source；candidate 始终作为 Git data，不能提供
可执行 checker。首发 workflow 来自 PR merge ref，其绿色结果不自证代码来源；独立 reviewer 还需核对
workflow/checker blobs、实际 hosted run 和完整 remote Gate。

source-owned receipts 都保留 `merge_eligible=false`：机器有效性不替代人类审查、远端门禁或最终发布批准。
`develop` 可以在 review 期间前进，但 frozen source 不随其自动扩大；更换 source 必须重新生成候选、pins
和证据。兼容 dormant policy 仍拒绝 curated release，不允许以数据或环境绕过上述检查。

## 3. PR 元数据与审查

release PR 使用 `PR 类型: release`、正式 `M14-005`、`Risk tier: R2`、具名责任人及 source-owned
workstream，说明内容范围、验证、authority basis、adversarial evidence、残余限制与后续动作。release PR
不重定义 Task，不借裁剪删除改变 Runtime/Claim/Human authority，也不将 READY 擅自写为 DONE。

至少一名 cross-owner reviewer 按 exact candidate/base 审查。main review rules 要求 Code Owner、stale
review dismissal 与 last-push approval。新 head、失效证据、冲突、未解决 conversation 和失败或缺失的
required check 均阻断合并。单次维护者审核例外仅按[开发指南第 5.4 节](DEVELOPMENT.md#54-reviewer-不可用时的单次维护者例外)
另行具名授权；它不豁免来源、CI、topology、artifact 或最终发布决定。

## 4. 合并、tag 与后续

1. 维护者在完整候选和 remote Gate 验收后另行批准最终发布合并。
2. exact candidate 以 merge commit 进入 main；合并前后证明 main tree 等于 manifest closed tree，
   回读 PR merge identity、保护、检查与 review 状态。
3. 在批准的 merge commit 上完成 tag、artifact/hash closure；候选检查通过不自动授权 tag 或制品发布。
4. release branch 不合并回 develop；后续修复先进入 develop，再从新 source/current main 重新生成。

远端分支清理保留活动 owner 与审计恢复用途。发布记录留在对应 workstream，实时成熟度、Task 状态和
依赖分别由 `STATUS.md`、`TASKS.md`、`ROADMAP.md` 维护。
