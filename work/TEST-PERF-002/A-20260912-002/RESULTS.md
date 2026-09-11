# Full-suite cost and test necessity audit

TEST-PERF-002 revision 25; Chengyue-Lu; R2; source `518f622b33d57f05240c5ade9e6abc860e20600c`.

[Measured cost and necessity analysis](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/FULL_SUITE_COST.md).

Profiling the real paired Skill evaluation test found 14 catalog constructions and 1,064
repeated schema self-checks. The implemented bounded process-local cache reuses successful
self-checks only for exact schema bytes and checker identity. Reads, pinned resource checks,
fresh mutable schema/registry instances and every document validation remain active.

Three unprofiled trials clear the schema cache before each trial. Median time changes from
16.840 to 6.112 seconds (63.7% reduction).
Schema self-check calls fall from 1,064 to 76, while document validations remain 14.
The separate cProfile measurements are diagnostic; their cumulative rows overlap. Neither
local measurement establishes a hosted full-suite speedup.

Frozen-source verification: 1104 coverage cases completed successfully,
plus 26 behavioral remainder cases. Strict exact-plan receipt join proves
1130 Python 3.11 behavioral cases: {'passed': 1127, 'skipped': 3}.
Global line coverage is 92.66%; all critical 95/90 gates and
all changed executable line/outgoing-branch 100/100 gates pass. Quality thresholds, exclusions
and required negative acceptance identities are preserved.

Targeted schema/runtime: 18 PASS; schema/runtime/validation under coverage: 26 PASS;
documentation/governance: 93 PASS; repository validation: 186/0/0. Adversarial schema cases
cover same-size/timestamp byte changes, invalid retries, checker changes, mutable catalog
isolation, independent roots, rename/removal and malformed JSON/missing IDs.

Actual code reading did not establish a removable whole test. Distinct model/context/checker
drift, Host boundary diagnostics, publication authority, Claim promotion and generated Trace
variants retain their assertions. Long projection tests can be split by fixture and contract
boundaries. Remaining repeated Runtime resource closure validation needs operation-scoped
integrity proof before reuse. Cross-commit test/coverage evidence reuse has an adoption design;
it is not enabled by this change.

The earlier hosted run 34625704088 passed both full suites and coverage at `bf6d079`; its
baseline measurements are separately identified in checks/hosted-before-summary.json. A new
archived HEAD still requires hosted CI and independent witness, followed by cross-owner review.
No merge or release occurred.

The recorder was created before implementation and restored from its persisted live object.
Native message/event export gaps remain explicit; earlier sealed Attempts are unchanged.
