# 验证 Attempt 索引

| Attempt | 状态 | 最远执行点 | 是否 canonical | 说明 |
|---|---|---|---|---|
| [`A-20260823-CODEX-READONLY`](attempts/A-20260823-CODEX-READONLY/ATTEMPT_MANIFEST.md) | `FAILED_PRE_PROTOCOL` | Schema CLI 参数校验 | 否 | Schema 子命令拒绝 `--strict-config`；未执行协议 |
| [`A-20260823-CODEX-READONLY-02`](attempts/A-20260823-CODEX-READONLY-02/ATTEMPT_MANIFEST.md) | `PARTIAL` | Schema完成、preinit 请求写入 | 否 | PowerShell 空集合绑定错误；进程被终止，无模型/线程行为 |
| [`A-20260823-CODEX-READONLY-03`](attempts/A-20260823-CODEX-READONLY-03/ATTEMPT_MANIFEST.md) | `PARTIAL_SUCCESS` | 基本握手与错误行为 | 否 | Schema 方法提取器只认 `const`，错误记录为 0 方法并跳过实验 Gate |
| [`A-20260823-CODEX-READONLY-04`](attempts/A-20260823-CODEX-READONLY-04/ATTEMPT_MANIFEST.md) | `VALID_SUPERSEDED` | 完整协议验证 | 否 | 结果有效，但 sanitized unknown-method 字段过宽；由 Attempt 05 最小化替代 |
| [`A-20260823-CODEX-READONLY-05`](attempts/A-20260823-CODEX-READONLY-05/ATTEMPT_MANIFEST.md) | `PASS_WITH_CAPTURE_GAPS` | 完整计划范围 | 是 | 181 stable、237 experimental、56 experimental-only；最小 fixture |
| [`A-20260823-REPO-CHECKS`](attempts/A-20260823-REPO-CHECKS/ATTEMPT_MANIFEST.md) | `PASS_LOCAL_WITH_MATRIX_PENDING` | 仓库回归、wheel、clean install | 否 | Python 3.12 本地通过；3.11/3.13 等待目标 PR CI |

Attempt 03/04 的自动 sanitized 文件被各自 `.gitignore` 保留在本地但不提交；其历史结论由
`RESULTS.md` 记录。Attempt 05 是唯一可用于本工作流正式结论和公共 fixture 的运行。
