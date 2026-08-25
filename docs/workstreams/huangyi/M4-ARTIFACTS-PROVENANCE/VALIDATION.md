# M4 验证证据

状态：实现中；本文件在 Stage PR 提交前补齐最终数据。

## 计划验证项

| 项 | 命令 | 结果 |
|---|---|---|
| 基线全量测试（实现前） | `py -3.11 -m unittest discover -s tests` | 432 passed（develop@4ce83bc，2026-08-25） |
| 全量测试（实现后） | `py -3.11 -m unittest discover -s tests` | 待填 |
| 覆盖率 | `py -3.11 -m coverage run -m unittest discover -s tests && coverage report --fail-under=80` | 待填 |
| 仓库校验 | `rwb validate examples registry` | 待填 |
| wheel + 干净安装 smoke | `python -m build --wheel` + venv 安装 + `rwb schema list` / `rwb validate examples registry` | 待填 |
| 远端 CI | governance + Python 3.11/3.13 矩阵 | 待填 |

## 任务级证据（PR body 引用）

### M4-001 source admission 与 provenance

- 待填：Schema、sidecar fixture、`ARTIFACT-INBOX-CITED`/`ARTIFACT-MISSING-PROVENANCE`
  负面测试、CLI 命令输出。

### M4-002 work → object/run promotion

- 待填：promotion-record Schema、`ARTIFACT-PROMOTION-BYPASS`/`ARTIFACT-OVERWRITE`/
  `ARTIFACT-NEGATIVE-DROPPED` 负面测试、CLI 输出。

### M4-003 Claim trace 与 counterevidence

- 待填：一次定位输出样例、引用完整性负面测试（悬空 ref、hash 漂移）。

### M4-004 Run manifest 与复现检查

- 待填：run-manifest Schema、仿真重建 fixture（确定性重跑 hash 比对）、
  `REPRO-GAP` 负面测试。
