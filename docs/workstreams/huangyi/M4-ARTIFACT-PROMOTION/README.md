# M4-002 Artifact Promotion Workstream

- Task owner / 必需审查人：路诚钺（GitHub `Chengyue-Lu`）
- 实现责任：黄毅（GitHub `let778750-cpu`）与 Codex
- Task：`M4-002`
- 风险：R1（共享 Schema、CLI、artifact lifecycle contract）
- 基线：`develop@6a032e12c30a88a501258eec8c0b5d6c6082d81d`（已包含 PR #56）
- 分支：`codex/m4-002-promotion`
- 状态：实现与本地验证进行中；等待 PR exact-head CI 和 Task owner 接受，不自行 merge

## 范围

本 PR 只完成 M4-002：`promotion_record`、独立 library validator/executor、trusted validation host 与
`rwb validation run`、`promotion_validation_host_receipt`、`rwb promotion validate|execute`、对抗测试、
Coverage Policy 和实现文档。它提议在合入时将 M4-002 置为 DONE，并因
hard dependency 满足而把 M4-003/004 激活为 READY。

M4-003 Claim Trace 与 M4-004 Run reproduction 不在本分支实现；M5 状态不变。本分支已整合上述
`develop` 基线，保留共享 document kinds、Schema catalog、Coverage Policy 与 M5 Task/navigation
变化；收尾修复推送后仍须通过 exact-head CI 和 Task owner review。

## 契约边界

- pre-Attempt canonical Task → accepted-policy registry → exact policy → validation 三元组 →
  promotion 的 Task/Attempt/revision、checker/runner/host identity/version/source hash 与 subject set 全部
  exact closure；允许稳定目录本身不授予 authority；eligibility 是 validity fact，只在 promotion 验证时
  由确定性重执行 pinned runner/checker 并 byte-exact 复现 PASS report 与记录 transcript 来确立；
  validation run 三元组是 provenance metadata（自声明 operator/时间不可独立验证，
  `validation_execution_fact=false`）；手写的错误 PASS report/transcript 会被重执行阻断；byte-exact
  自报历史可通过有效性检查，但不产生历史 producer/operator/time 权威；
- report、subjects、entries 与 live bytes 全部 exact-pin；subjects/entries 按 exact file-reference 集合相等；
- 只从 exact `work/<task>/<attempt>` 复制到 `objects/`、`runs/`、`deliverables/candidates/`；
- execute 只接受 workspace 内的 file-bound record；staging + commit-time 复验 + exclusive-create 同批发布
  目标和 durable receipt，冲突不覆盖，失败回滚本次可确认创建的目标/receipt；
- 每个受检工件都有 promote/retain disposition，负结果不能被静默丢弃；
- promotion 不产生 Claim acceptance、Human Decision、publication 或 scientific correctness。

验证证据见 [VALIDATION.md](VALIDATION.md)，风险见 [RISK_LEDGER.md](RISK_LEDGER.md)。
