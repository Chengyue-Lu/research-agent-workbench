# M4-002 验证证据

状态：本地 code-complete 验证已完成；hosted exact-head CI 与 Task owner acceptance 尚未发生。

## 已完成的本地证据

| 项 | 结果 |
|---|---|
| Promotion focused tests | 38 项收集：37 项通过；Windows 因权限跳过 1 项真实 symlink 创建，Linux CI 保留执行 |
| Promotion critical coverage | line 96.96%，branch 94.31%，满足 95% / 90% 门槛 |
| 对抗面 | pre-Attempt Task/registry/policy/host closure、允许稳定目录内完整自洽 fake checker/runner/host/policy/execution/PASS 链、work 内自签链、record/report/subject/entry drift、时间倒置、额外/遗漏 entry、failed report/execution、prefix/accepted/existing target、duplicate identity、record/source/staging/target/receipt race、target+receipt rollback、repository receipt target drift |
| Coverage Policy v2 | 按 PR #47/#49 优化路径仅在 Python 3.11 执行一次：770 项收集，768 PASS、2 项 Windows symlink 权限跳过；global line 91.76%；全部 critical line/branch 门槛 PASS |
| Full suite | Python 3.11 plain compatibility 只执行一次：831 项收集，829 PASS、2 项 Windows symlink 权限跳过；本机没有 Python 3.13，不以其他版本冒充，等待 hosted exact-head CI |
| Repository validation | `validated=183 errors=0 warnings=0` |
| Wheel / clean install | Python 3.11 临时 clean venv 成功安装 wheel，列出 `promotion-record`、`promotion-validation-authority-registry`、`promotion-validation-policy`、`promotion-validation-execution`、`promotion-execution-receipt` 五项 Schema，并完成 repository validation |
| Static checks | `compileall`、documentation 9、Schema 3、governance 67、Coverage Policy 21 项测试与 `git diff --check` PASS |

## 合并前仍需更新

- 已完成：rebase 到最新 `develop@dd2454b5595e33a12aa058529358d46d311a08c4`，保留 PR #53 的 M5 Task/navigation 真值；
- exact HEAD Python 3.11/3.13 hosted CI；
- 所有 review conversation resolved，且路诚钺对 exact HEAD 接受。
