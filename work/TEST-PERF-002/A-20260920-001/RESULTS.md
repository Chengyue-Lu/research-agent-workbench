# Domain model 2A and PR90 cost intake

TEST-PERF-002 / Issue #87; owner Chengyue-Lu; R2; 2026-09-20.
Base: `171d4654f88e926f239cdf25bc8168109b81f391`.
Implementation: `896875587efc1a8be3465f1d04660754053d703c`.

Eight declared review domains reuse four existing consumer record IDs. The offline
audit preserves the observed plan and reports overlapping roles, unknown input facts,
old/new Git objects, absent historical records and supplied receipt outcomes/costs.
It binds the diagnostic model and seven local producer hashes. It supplies no worker
outputs, selected/skipped candidate, exclusion authority or successful execution receipt.

The proposed input model routes all 115 base production/CI/build Python files, 98 test
modules and ten helper/runner/initializer files. Seven source and six helper overlaps
are retained. These counts describe the base inventory, not the new candidate discovery.
Path membership does not prove invocation, environment or alternate-consumer closure.

## Validation

- Python 3.11 focused regression: **41 PASS**, 32.763 s at implementation HEAD.
- Python 3.13 focused plus documentation: **14 PASS**; exact final source rerun is retained
  with the final-head verification. Neither set is a repository-wide full suite.
- New diagnostic module: **121/121 statements, 38/38 branches**, zero exclusions.
- Real Git negative/control cases preserve archive executable facts, worktree independence,
  foreign Gitlink unknowns, output/input collision rejection and immutable accepted plans.
- Review found three P2 issues; all repaired and independently rechecked: governance
  producer hash, output/input aliases and absent external Gitlink objects.
- Five exact Git replays (#65/#68/#84/#86/#90) preserve every observed execution field
  and original plan bytes. Old bases without #85 records are explicitly unresolved.
  The first four are historical head-target replays; #90 uses its actual hosted merge target.

[Validation and raw member hashes](checks/validation.json), [matrix](checks/replay-matrix.json),
[independent review](checks/code-review.md), [raw evidence ZIP](checks/raw-evidence.zip).
The ZIP retains original plans/receipts, GitHub artifact digest checks, per-case data,
logs and frozen producer source. Files inside it are historical audit inputs, not installed
executables or a new coverage exclusion policy.

## PR90 diagnosis and ownership

[Full cost audit](checks/PR90_COST_AUDIT.md) and [structured observation](checks/pr90-summary.json)
bind run `35449976025`, head `d9042fd1611f152573a7d2cae176cb1e1ec70065`,
target `737fb4198eac1e51f42da2f2204971ef96ec5ace`.

Coverage job was 37m43s; ordered execution step was 37m24s. B=1425, C=1399,
intersection=1399, C−B=0: 1425 unique tests passed. There was no repeated B/C suite.
Forty-two archive-data/metadata paths caused unclassified FULL/repository fallback.
Smokes still have independent schema/public/repository consumers.

The checker then rejected absent impact data for an archived capture exporter. No M5
behavioral failure was observed; new H4 source had all 102 statements and 32 branches
covered in raw data. The failed Gate remains failed. Evidence/producer disposition was
handed to the task RWB开发 (3), as requested by the user; its branch was not modified.

H3/H4 tests contributed 937.179 case seconds, 46.49% of summed case durations. Those
relevant consumers retain necessary behavioral proof; eliminating unrelated execution
alone cannot remove this internal cost. Business test restructuring belongs to its owner.

## Next CI slice and limits

2B adds exact candidate selected/skipped and real behavioral/coverage/smoke comparisons;
2C separately accepts one proven exclusion through an independent witness. Archive
consumer closure and early measurement viability are recorded CI debt. Quality thresholds,
ordered execution, fixed aggregates and fresh integration baselines remain unchanged.
This Draft does not claim fewer executed tests, actual hosted speedup, merge readiness,
or completion of 2B/2C. Prior local performance candidates remain separate.

[Trace validation](checks/trace-validation.json) has no BLOCK and retains a capture-gap
warning. The initial trace's unsupported stream label was corrected; its original bytes
and rejected validation are preserved in [initial-invalid-trace.zip](checks/initial-invalid-trace.zip).
Export time describes retention, not original event time. Delegation reports are retained;
unstreamed messages/events and final publication remain declared capture gaps.
