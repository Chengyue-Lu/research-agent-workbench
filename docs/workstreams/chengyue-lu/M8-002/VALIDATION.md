# M8-002 验证证据

状态：feature 分支本地证据；远端 CI 和 task closeout 尚未完成。

## 基线与环境

- 目标 base：`develop@5991cafdb7f536cd7b871508de9055d02b558728`；
- 分支：`agent/method-m8-002-mode-action-contract`；
- Python：本地 Python 3.14，使用仓库 `src/` 作为 `PYTHONPATH`；
- 未安装新的在线依赖；Hypothesis 属性测试按项目既有条件跳过。

## 已执行检查

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m unittest discover -s tests -v
python -c "from research_workbench.cli import main; raise SystemExit(main())" validate examples registry --root .
git diff --check develop...HEAD
```

合入最新 `develop` 后的本地结果：

- `273` tests passed；
- `3` Hypothesis tests skipped；
- repository validation reports `validated=76 errors=0 warnings=0`；
- documentation、PR governance、Mode Action 与 routing fixture 的 `47` 个 focused tests passed；
- `git diff --check` passed；
- 以最终 commit、`develop` base、PR body、owner/reviewer 和 workstream 构造的本地 PR event 通过
  `check_pr_governance.py`；
- Action Registry 的 closed-set、missing/orphan、raw-byte hash drift、Mode relation 与 fixture ref
  负面测试通过。

## PR 前仍需执行

- 在 clean checkout/CI 中运行 Python 3.11 与 3.13 matrix、coverage、wheel 和 clean-install checks；
- 核对远端分支 ancestry 与 PR 目标确为 `develop`。

这些结果不证明真实研究方法有效、外部 Provider 兼容或 Skill/Action 具有净收益。
