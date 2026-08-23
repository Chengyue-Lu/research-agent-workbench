# M8-002 验证证据

状态：feature 实现与本轮完整验证已通过；已纳入统一节点分支，等待 R2 节点审查。

## 基线与环境

- 当前目标 base：`develop@51c86072c986826f1abc7ca3b17018169b7ca75d`；
- 原实现 base：`develop@5991cafdb7f536cd7b871508de9055d02b558728`；
- 活动分支：`agent/method-m8-action-resolution-node`；
- 历史提交：`def0689`，原 Draft PR #26 已撤回且未合并，原分支已删除；
- Python：本地 Python 3.14，使用仓库 `src/` 作为 `PYTHONPATH`；
- 未安装新的在线依赖；Hypothesis 属性测试按项目既有条件跳过。

## 已执行检查

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m unittest discover -s tests -v
python -c "from research_workbench.cli import main; raise SystemExit(main())" validate examples registry --root .
git diff --check develop...HEAD
```

合入 Governance v2 所在的最新 `develop` 后，本地结果：

- 当前完整 suite：`298` tests passed；
- `3` Hypothesis tests skipped；
- repository validation reports `validated=84 errors=0 warnings=0`；
- contracts、schemas、Mode Action、Method Resolution、routing、documentation 与 PR governance 的
  `79` 个 focused tests passed；
- `git diff --check` passed；
- 以最终 commit、`develop` base、PR body、owner/reviewer 和 workstream 构造的本地 PR event 通过
  `check_pr_governance.py`；
- Action Registry 的 closed-set、missing/orphan、raw-byte hash drift、Mode relation 与 fixture ref
  负面测试通过。

本轮新增 focused checks 覆盖 canonical Claim strength、effect overlap、Mode claim-rule ceiling、
opaque Human Gate ID、metadata rejection 与 published identity/append-only contract 声明。跨 commit
immutability 必须由合并边界比较 base/head Registry；静态 Schema/validator 不冒充历史证明。

完整 suite、focused suite、repository validation 与 `git diff --check develop...HEAD` 均在同一集成
工作树重新执行通过；Governance v2 synthetic PR preflight 推导 R2，并确认 M8-002 READY→DONE、
M8-003 PARKED→READY 均为合法转换，结果为 PASS。

## 统一节点 PR 前仍需执行

- 由更新后的远端 CI 重跑 Python 3.11/3.13、coverage、wheel 和 clean-install checks；
- 核对统一分支同时包含原 M8-002 与 M8-003 历史，并按 R2 边界完成跨负责人审查。

这些结果不证明真实研究方法有效、外部 Provider 兼容或 Skill/Action 具有净收益。
