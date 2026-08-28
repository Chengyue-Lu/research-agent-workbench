# M10 Phase C 验证证据

状态：PR #44 final-contract review 整改；已语义 rebase 到 `develop@aa4e7ee`（accepted M11 Core）。
latest-base 本地全量测试已通过；双 Python、coverage、wheel clean-install 证据等待当前 HEAD 远端 CI。

## Task-specific evidence

- **M10-001** Schema：`research-state.schema.json`；
- closure：`research_state/closure.py`；
- CLI：`rwb research-state validate ... --closure ...`，只消费显式 closure；
- bounded cases：`examples/phase-c/m10-001-case-a` 与 `m10-001-case-b`；
- Human Decision：Case A 复用 `object_type: decision`；无 `human-decision-record` Schema；
- negative evidence：duplicate/ambiguous identity、missing target hash、pin drift、unversioned ref、
  role/type mismatch、stale current、cross-lineage/non-incremental supersession、closed item without
  provenance，以及 downstream role/field schema rejection。

- **M10-002** Schemas：`research-attempt-lineage.schema.json`、`research-failure.schema.json`；
- legacy boundary：`attempt.schema.json`、archive/recovery/Receipt 均未改写；
- exact execution pin：explicit closure 唯一路径、execution type、attempt_id 与 loaded-byte SHA-256；
- bounded cases：`examples/phase-c/m10-002-case-a` 与 `m10-002-case-b`，并复用 M10-001 State closure；
- independence evidence：两个 Attempt 共享 State r1，而 State r2 由 Evidence/Human Decision 独立演化；
- negative evidence：wrong/missing/drifted execution pin、predecessor self-loop/unversioned/type mismatch、
  reopen basis empty/type mismatch、changed-condition missing/wrong-type provenance、predecessor/reopen 双向独立、
  duplicate lineage identity、execution-origin missing source Attempt、non-execution carrying execution profile、
  Failure source type mismatch、partial profile，以及
  execution failure/negative Evidence/Capability Gap/Skill Need 平行字段拒绝。

- **M3-009** Schema：`method-trace.schema.json`；
- exact Method：正式索引 `resolution_id@revision`，并验证 MR Schema、Task identity 与 Task byte pin；
- ref-only closure：Attempt、Task、Mode ref、Action decision id、State、kernel Decision、typed path basis；
- bounded case：`examples/phase-c/m3-009-case-a`，复用 M10-001/002 exact closure；
- actual-binding：本 Attempt 无 authoritative fact 时固定 unavailable/gap-only 且 path fact 为空；captured
  正例由 M11 `AgentTraceRecorder.record_execution_fact()` 生成，exact fact 必须绑定同一 Attempt、至少一个
  applied disposition 与 State effect，coverage 只声明 `fact-bound-path-effect`；
- negative evidence：MR missing/wrong-kind/wrong-task/malformed/bad-pin、Mode drift、Action path missing/
  duplicate/disposition drift、Attempt Task mismatch、from-State mismatch、Question causal splice、Human/Evidence
  wrong type、duplicate Trace、gap overclaim、fact missing/ref drift/Attempt mismatch/path-effect unbound、
  unavailable-with-fact 与 selected Snapshot as actual。

- **M10-003** Schemas：`phase-c-gate-manifest.schema.json`、`phase-c-gate-report.schema.json`；
- runner-owned source：manifest exact path/hash/kind/identity，保持原 repository-relative path staging；
- fresh actor：两案各用独立 PID，只读生成 manifest、staged allowlist 与 trusted Schema code root；输出
  exact case-data read surface、declared trusted runtime/schema surface 与 input-write surface；private oracle
  在 actor 退出后才首次读取；
- report pins：每案绑定 source-manifest SHA、private-oracle SHA 与 exact input-closure digest；顶层 digest
  绑定两案 pins，Schema 精确固定 trusted runtime/schema 二元组并拒绝 complete-process-read overclaim；
- bounded cases：evidence-synthesis 复用 Case A 全 closure；simulation-negative 增加完整继承 SIM-A3
  Gate/artifact/stop/block 的 Case B Method Resolution/Trace 与 synthetic reviewer Decision；
- oracle minimum：exact State/Trace/Mode/Action/Evidence/Decision/open/invalidated/Failure/candidate/binding/
  authority/read surface，加固定 known-failure predicates；
- negative evidence：source pin drift、duplicate identity/path、oracle-as-input、unlisted read/input write、stale
  trace、duplicate candidate、wrong-kind reopen basis、弱 oracle 与 caller output overwrite；
- authority boundary：machine PASS 时 Human semantic review、R2 closeout、Phase C closeout 仍 pending，
  reviewer reconstruction/scientific correctness/Topic 5 authority 均为 false。

## Re-run

| 项 | 结果 |
|---|---|
| `test_research_state_candidate.py` | 15 passed |
| `test_research_attempt_failure.py` | 20 passed（latest owner-review delta） |
| `test_method_trace_candidate.py` | 24 passed（M11 semantic integration） |
| `test_phase_c_gate.py` | 18 passed（latest owner-review delta） |
| `test_schemas.py` | 3 passed |
| 两个 explicit-closure CLI checks | PASS（6 / 4 explicit documents） |
| M10-002 explicit-closure CLI check | PASS（M10-001 + M10-002 显式 roots） |
| `rwb validate examples/phase-c --root .` | validated=26, errors=0, warnings=0 |
| `rwb validate examples registry --root .` | validated=180, errors=0, warnings=0 |
| latest-base full unittest | 552 passed，3 skipped（本地未安装可选 Hypothesis）；818.723s |
| latest-base coverage/dual-Python/wheel clean-install CI | PENDING（当前 HEAD 推送后由远端 CI 验证） |

## Owner review remediation matrix

| Review finding | Evidence |
|---|---|
| dependency chain mixed four Tasks | PR diff now changes only M10-001 to DONE；all downstream statuses remain BLOCKED |
| duplicate/ambiguous identity | `duplicate_identities` + ambiguous resolver tests |
| pinned ref without target hash | `hash-unverifiable` negative test |
| State role not type-bound | explicit role→semantic-type map + mismatch negative test |
| parallel Human Decision representation | kernel `object_type: decision` fixture; no new Human Decision Schema |
| fresh actor and Method Trace defects | M3-009 以独立 ref-only contract 修复；M10-003 以 runner-owned exact staging、新进程 deny policy、post-exit private oracle 与 stale-trace 反例闭合 |
| reopen changed condition / execution Failure provenance | changed condition 逐项 exact provenance；`origin_kind` 强制 execution source Attempt、分离 minimal non-execution Failure |
| M11 execution facts | per-Attempt gap reason；M11 producer-generated captured 正例；fact exact 绑定 applied path/State effect |
| Gate case/oracle identity | 每案 manifest/oracle/closure pins + 顶层 digest；等价替换仍 hash-distinguishable |
| complete read-surface overclaim | exact case-data 与 declared trusted runtime/schema 分栏；Schema 固定完整进程读面为 false |

## M10-002 acceptance matrix

| Task acceptance | Evidence |
|---|---|
| Attempt 分离 from-State | versioned lineage sidecar 不改 legacy Attempt；state exact ref 独立 |
| optional predecessor + independent reopen justification | 双向独立正例；predecessor distinct/type/exact；changed condition 逐项携带 exact/type-bound provenance |
| 多 Attempt 共享 State，State 独立演化 | Case A 两个 lineage 同指 r1；既有 State r2 独立 supersede |
| Failure universal minimum | minimal fixture test 只需 learned/revisit semantic content |
| source/observed/uncertainty 仅 bounded profile | `origin_kind` 条件化：execution 强制 source Attempt；non-execution 禁止 profile |
| 与其他 failure/gap/need 分离 | additionalProperties fail-closed 与四项字段拒绝测试 |

## M3-009 acceptance matrix

| Task acceptance | Evidence |
|---|---|
| 独立 ref-only Method Trace | 新 Schema/validator；Execution Trace 与被引用正文不改 |
| applied Method / Mode / Action disposition | exact MR ref、selected mode equality、Action decision 全覆盖与 applied equality |
| Human Decision / State / path | kernel Decision 和 typed basis refs；Attempt from-State 与 Task Question causal closure |
| 当前 Attempt 无 fact 时显式 gap | `no-authoritative-execution-fact-for-attempt` + gap-only；path fact 必须为空 |
| M11 captured actual fact | producer-generated 正例；exact loaded-byte pin、同 Attempt、applied path 与 State effect 绑定 |
| Snapshot 不等于 actual execution | captured fact kind/file pin 限制 + structural Snapshot wrong-kind 反例 |
| gap-valid 不得 fact-bound | mutually exclusive Schema branches；captured 只声明 `fact-bound-path-effect` |

## M10-003 acceptance matrix

| Task acceptance | Evidence |
|---|---|
| 两份 bounded continuity case | exactly one evidence-synthesis + one simulation-negative manifest；case/profile identity 固定 |
| staged 新进程 | runner 临时 staging；不同 actor PID；output fresh-only |
| compact State/Method Trace + exact closure | source byte pin/kind/identity/whole closure；actor 不扫描目录；case-data read surface exact |
| runner-owned private oracle | 不传入 args/env/staging；actor 成功退出后首次读取；minimum fields/predicate vocabulary 固定 |
| exact case/oracle 可审计 | manifest/oracle/closure SHA 逐案记录；顶层 digest 独立复算；等价替换输入仍 hash-distinguishable |
| runtime/schema 信任边界 | report 与 Schema 分离 exact case-data surface 和精确声明的 trusted surface；完整进程读面固定 false |
| known-failure behavior | repeat-coarse-grid=`known-failed-avoid`；推荐 inspect-higher-resolution-input 且不重复 Failure |
| Human/R2/Topic 5 独立 | report 固定 pending/false；Schema 与正面/篡改测试均不允许 machine Gate 越权 |
