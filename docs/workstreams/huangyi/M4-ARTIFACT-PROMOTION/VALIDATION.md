# M4-002 验证证据

状态：本地 code-complete 验证已完成；hosted exact-head CI 与 Task owner acceptance 尚未发生。

## 已完成的本地证据

| 项 | 结果 |
|---|---|
| Promotion focused tests | 36 项收集：35 项通过；Windows 因权限跳过 1 项真实 symlink 创建，Linux CI 保留执行 |
| Promotion critical coverage | line 97.07%，branch 94.85%，满足 95% / 90% 门槛 |
| 对抗面 | work 内自签 checker/policy/execution、authority cross-document drift、record/report/checker/runner/subject/entry drift、时间倒置、额外/遗漏 entry、failed report/execution、prefix/accepted/existing target、duplicate identity、record/source/staging/target/receipt race、target+receipt rollback、repository receipt target drift |
| Coverage Policy v2 | 按 PR #47/#49 优化路径仅在 Python 3.11 执行：768 项收集，766 PASS、2 项 Windows symlink 权限跳过；global line 91.73%；全部 critical line/branch 门槛 PASS |
| Full suite | Python 3.11 plain compatibility：829 项收集，827 PASS、2 项 Windows symlink 权限跳过；本机没有 Python 3.13，不以其他版本冒充，等待 hosted exact-head CI |
| Repository validation | `validated=183 errors=0 warnings=0` |
| Wheel / clean install | Python 3.11 临时 clean venv 成功安装 wheel，列出 `promotion-record`、`promotion-validation-policy`、`promotion-validation-execution`、`promotion-execution-receipt` 四项 Schema，显示 `rwb promotion` CLI，并完成 repository validation |
| Static checks | `compileall`、documentation 9、Schema 3、governance 67、Coverage Policy 21 项测试与 `git diff --check` PASS |

## 合并前仍需更新

- 已完成：rebase 到包含 PR #51 的 `develop@100fec5b5ff4e28bc7daa812db4226a85dcd2d26`；
- exact HEAD Python 3.11/3.13 hosted CI；
- 所有 review conversation resolved，且路诚钺对 exact HEAD 接受。
