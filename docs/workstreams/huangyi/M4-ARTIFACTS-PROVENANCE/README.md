# M4-001 Source Admission Workstream

- 实现责任人：黄毅（GitHub `let778750-cpu`）
- Task owner / 必需审查人：路诚钺（GitHub `Chengyue-Lu`）
- Task：`M4-001`
- 基线：`develop@6b16129`
- 分支：`agent/m4-artifacts-provenance`
- 风险：R1（共享 Schema/CLI/validator contract）

## 范围

本 PR 按 Issue #41 / PR #42 的规范化治理只承载 M4 第一依赖层：source admission、
provenance sidecar、inbox 引用阻断、CLI 与确定性验证。`docs/TASKS.md` 只将 M4-001 从
READY 置为 DONE。

M4-002 promotion、M4-003 Claim trace、M4-004 Run manifest 均保留 BLOCKED；它们必须在
前置层经 owner 接受后，以各自 feature PR 推进。规范化前同一 PR 原子闭合四个 Task 的口径已经
撤销，旧 head 仅保存在 `archive/pr39-pre-split-20260826` 供追溯，不构成实现状态真值。

## 写入面与非目标

写入面限于 `source-admission` Schema、`artifacts/admission.py`、`rwb source` CLI、仓库引用
检查的 inbox gate、source fixture、专项测试与本 Task 文档。此层不新增 promotion/reproduction
Schema，不修改 Claim 语义，不实现 Runtime，也不声称 validator 能判断来源可信或科学正确。

验证证据见 [VALIDATION.md](VALIDATION.md)，风险见 [RISK_LEDGER.md](RISK_LEDGER.md)。
