# M10-001 验证证据

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

## Re-run

| 项 | 结果 |
|---|---|
| `test_research_state_candidate.py` | 15 passed |
| `test_schemas.py` | 3 passed |
| 两个 explicit-closure CLI checks | PASS（6 / 4 explicit documents） |
| `rwb validate examples/phase-c --root .` | validated=10, errors=0, warnings=0 |
| `rwb validate examples registry --root .` | validated=164, errors=0, warnings=0 |
| 最终全量 | 447 passed, 3 skipped |
