# M4-002 Artifact Promotion Workstream

- Task owner / 必需审查人：路诚钺（GitHub `Chengyue-Lu`）
- 实现责任：黄毅（GitHub `let778750-cpu`）与 Codex
- Task：`M4-002`
- 风险：R1（共享 Schema、CLI、artifact lifecycle contract）
- 基线：`develop@97fa2455c983dc65e66a782bac8d272eed32c633`
- 分支：`codex/m4-002-promotion`
- 状态：实现与本地验证进行中；等待 PR exact-head CI 和 Task owner 接受，不自行 merge

## 范围

本 PR 只完成 M4-002：`promotion_record`、独立 library validator/executor、`rwb promotion
validate|execute`、对抗测试、Coverage Policy 和实现文档。它提议在合入时将 M4-002 置为 DONE，并因
hard dependency 满足而把 M4-003/004 激活为 READY。

M4-003 Claim Trace 与 M4-004 Run reproduction 不在本分支实现；M5 状态不变。PR #51 可并行修改
Runtime Bundle、document kinds 和 Coverage Policy，但 M4-002 在最终 owner review 前必须 rebase 到包含
#51 最终状态的最新 `develop`，解决共享文件 delta 后重新跑 exact-head CI。

## 契约边界

- report、checker、subjects、entries 与 live bytes 全部 exact-pin；subjects/entries 按 `(path, sha256)`
  完全集合相等；
- 只从 exact `work/<task>/<attempt>` 复制到 `objects/`、`runs/`、`deliverables/candidates/`；
- staging + 二次复验 + exclusive-create 发布，冲突不覆盖，失败回滚本次可确认创建的目标；
- 每个受检工件都有 promote/retain disposition，负结果不能被静默丢弃；
- promotion 不产生 Claim acceptance、Human Decision、publication 或 scientific correctness。

验证证据见 [VALIDATION.md](VALIDATION.md)，风险见 [RISK_LEDGER.md](RISK_LEDGER.md)。
