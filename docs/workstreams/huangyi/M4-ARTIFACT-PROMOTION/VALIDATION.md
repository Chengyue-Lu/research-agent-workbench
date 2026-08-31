# M4-002 验证证据

状态：本地 code-complete 验证已完成；hosted exact-head CI 与 Task owner acceptance 尚未发生。

## 已完成的本地证据

| 项 | 结果 |
|---|---|
| Promotion focused tests | 23 项收集：22 项通过；Windows 因权限跳过 1 项真实 symlink 创建，Linux CI 保留执行 |
| Promotion critical coverage | line 96.77%，branch 91.49%，满足 95% / 90% 门槛 |
| 对抗面 | report/checker/subject/entry drift、额外/遗漏 entry、failed report、prefix/accepted/existing target、duplicate identity、source/staging/target race、partial rollback |
| Coverage Policy v2 | 732 项收集：730 PASS、2 项 Windows symlink 权限跳过；global line 91.58%；全部 critical line/branch 门槛 PASS |
| Full suite | 793 项收集：791 PASS、2 项 Windows symlink 权限跳过 |
| Repository validation | `validated=182 errors=0 warnings=0` |
| Wheel / clean install | Python 3.11 clean venv 可列出 `promotion-record`、加载 `promotion_record` Schema、显示 `rwb promotion` CLI，并完成 repository validation |
| Static checks | `compileall`、documentation/schema/governance tests 与 `git diff --check` PASS |

## 合并前仍需更新

- PR #51 最终状态后的 latest-base rebase；
- exact HEAD Python 3.11/3.13 hosted CI；
- 所有 review conversation resolved，且路诚钺对 exact HEAD 接受。
