# M10 Phase C 验证证据

状态：PR #44 review 整改；基线 `develop@6b16129`。

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
  reopen basis empty/type mismatch、predecessor/reopen 双向独立、duplicate lineage identity、Failure source
  type mismatch、partial profile，以及
  execution failure/negative Evidence/Capability Gap/Skill Need 平行字段拒绝。

- **M3-009** Schema：`method-trace.schema.json`；
- exact Method：正式索引 `resolution_id@revision`，并验证 MR Schema、Task identity 与 Task byte pin；
- ref-only closure：Attempt、Task、Mode ref、Action decision id、State、kernel Decision、typed path basis；
- bounded case：`examples/phase-c/m3-009-case-a`，复用 M10-001/002 exact closure；
- actual-binding：正例固定 unavailable/gap-only；captured 仅预留给 accepted `execution_trace_fact`；
- negative evidence：MR missing/wrong-kind/wrong-task/malformed/bad-pin、Mode drift、Action path missing/
  duplicate/disposition drift、Attempt Task mismatch、from-State mismatch、Question causal splice、Human/Evidence
  wrong type、duplicate Trace、gap overclaim、missing producer 与 selected Snapshot as actual。

## Re-run

| 项 | 结果 |
|---|---|
| `test_research_state_candidate.py` | 15 passed |
| `test_research_attempt_failure.py` | 18 passed |
| `test_method_trace_candidate.py` | 20 passed |
| `test_schemas.py` | 3 passed |
| 两个 explicit-closure CLI checks | PASS（6 / 4 explicit documents） |
| M10-002 explicit-closure CLI check | PASS（M10-001 + M10-002 显式 roots） |
| `rwb validate examples/phase-c --root .` | validated=20, errors=0, warnings=0 |
| `rwb validate examples registry --root .` | validated=174, errors=0, warnings=0 |
| 最终全量 | 485 passed, 3 skipped |

## Owner review remediation matrix

| Review finding | M10-001 head evidence |
|---|---|
| dependency chain mixed four Tasks | PR diff now changes only M10-001 to DONE；all downstream statuses remain BLOCKED |
| duplicate/ambiguous identity | `duplicate_identities` + ambiguous resolver tests |
| pinned ref without target hash | `hash-unverifiable` negative test |
| State role not type-bound | explicit role→semantic-type map + mismatch negative test |
| parallel Human Decision representation | kernel `object_type: decision` fixture; no new Human Decision Schema |
| fresh actor and Method Trace defects | M3-009 以独立 ref-only contract 修复；M10-003 runner 仍未实现 |

## M10-002 acceptance matrix

| Task acceptance | Evidence |
|---|---|
| Attempt 分离 from-State | versioned lineage sidecar 不改 legacy Attempt；state exact ref 独立 |
| optional predecessor + independent reopen justification | 双向独立正例；predecessor distinct/type/exact；reopen ref/type/changed-condition 反例 |
| 多 Attempt 共享 State，State 独立演化 | Case A 两个 lineage 同指 r1；既有 State r2 独立 supersede |
| Failure universal minimum | minimal fixture test 只需 learned/revisit semantic content |
| source/observed/uncertainty 仅 bounded profile | optional all-or-nothing `execution_profile` |
| 与其他 failure/gap/need 分离 | additionalProperties fail-closed 与四项字段拒绝测试 |

## M3-009 acceptance matrix

| Task acceptance | Evidence |
|---|---|
| 独立 ref-only Method Trace | 新 Schema/validator；Execution Trace 与被引用正文不改 |
| applied Method / Mode / Action disposition | exact MR ref、selected mode equality、Action decision 全覆盖与 applied equality |
| Human Decision / State / path | kernel Decision 和 typed basis refs；Attempt from-State 与 Task Question causal closure |
| 无 producer 时显式 gap | unavailable + fixed reason + gap-only positive fixture |
| Snapshot 不等于 actual execution | captured fact kind/file pin 限制 + structural Snapshot wrong-kind 反例 |
| gap-valid 不得 coverage-complete | mutually exclusive Schema branches 与负面测试 |
