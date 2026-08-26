# M10 验证证据

状态：Stage PR 提交前记录（分支 `agent/m10-research-state`，基线 `develop@6b16129`）。

## 全局验证

| 项 | 命令 | 结果 |
|---|---|---|
| 基线全量测试（实现前，develop@6b16129） | `py -3.11 -m unittest discover -s tests` | 432 passed |
| 全量测试（实现后） | `py -3.11 -m unittest discover -s tests` | **457 passed, 0 failed**（新增 25 项 Phase C 测试） |
| 仓库校验 | `rwb validate examples registry` | **validated=170 errors=0 warnings=0**（新增 18 个 Phase C fixture 文档全部通过 schema + closure） |
| Behavioral Gate A（evidence synthesis） | `rwb research-state gate --case examples/phase-c/case-a-evidence-synthesis` | **PASS**（RSTATE-PC-A@2） |
| Behavioral Gate B（simulation negative） | `rwb research-state gate --case examples/phase-c/case-b-simulation-negative` | **PASS**（RSTATE-PC-B@2） |

本地 Python 3.11；3.13 矩阵由远端 CI 验证。

## 任务级证据

### M10-001 minimal Research State composition

- Schema：`research-state.schema.json`；closure：`research_state/closure.py`
  （ClosureIndex 按 id+revision 索引，pin 对 content_hash 比对）；
- 行为验证：Case A/B 的 state r1→r2 supersession 通过；fresh actor 从 compact state
  重建 key evidence/limitations/decision effects/open items，read_surface 不含
  original-chat/oracle；
- 对抗：跨 lineage supersession、非递增 supersession、stale current entry、
  invalidated 无 provenance、revisit_refs 非 failure、pin 漂移（6 项负例全阻断）。

### M10-002 Attempt / Research Failure

- Schema：`research-failure.schema.json`（learned_result/revisit_condition 必填，
  schema 负例锁定）；execution_outcome 与研究失败分离：Case B 的 failure 声明
  `execution-succeeded` 同时承载研究否定；
- 对抗：悬空 evidence_refs 阻断；from_state_ref/evidence_refs/invalidated_assumption_refs
  closure 校验。

### M10-003 bounded behavioral Gate

- `fresh_actor.py`：staged 新进程（subprocess）；约定路径读取 + read_surface 全记录 +
  forbidden_reads oracle 断言；pin 漂移 fail-closed（测试锁定）；
- Case A 断言：active_state/key_evidence_refs/invalidated_items/recommended_action 全对；
- Case B 断言：rerun-coarse-grid=known-failed-avoid（回避已知失败路径）、
  refine-resolution=recommendable、ASSUM-PC-B-01 invalidated；
- revisit 翻转测试：condition_met=true 时 rerun 变 reviewable（浮出供审查），
  仍不被推荐——"condition 变化只使路径可复审"的行为锁定；
- CLI gate：oracle 谓词不匹配 → GATE-PREDICATE FAIL（exit 1）。

### M3-009 Method Trace v0.1

- Schema：`method-trace.schema.json`；六族事件闭集 + 必备 ref（execution-fact 缺
  execution_ref 时明确提示 "record an explicit gap instead of inventing the fact"）；
- 对抗：sequence 断裂、悬空 decision_ref、execution-fact 无 ref（3 项负例）；
- Case B trace 含 research-state-changed（state_before/after exact pin）、
  failure-rationale-recorded、reopen-reviewable 三族事件，ref-only 不复制正文。
