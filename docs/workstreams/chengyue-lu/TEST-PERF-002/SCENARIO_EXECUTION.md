# Scenario tests and execution reuse

TEST-PERF-002; owner: Chengyue-Lu; R2; Issue #48 / PR #70.

## Evidence from one execution

Behavioral assertions and runtime coverage answer separate questions. A test execution
can provide both its assertion result and its observed line/branch data. Coverage report
generation and threshold enforcement consume that data without executing the tests again.
Entering a function is not a replacement coverage gate. Global 90%, critical 95/90,
changed executable lines/outgoing branches 100/100, and positive/negative acceptance remain
the requirements of the existing policy.

Let B be the exact planned Python 3.11 behavioral inventory and C the exact union of
required coverage tests. The two execution producers run in parallel:

- Coverage producer: execute C with instrumentation and enforce every coverage obligation.
- Behavioral producer: execute B minus C without instrumentation.
- Compatibility check: reload the planned inventories, verify both receipts, and assemble
  behavioral evidence for B. Each canonical case in B union C executes once on Python 3.11.

The join validates plan ID, tested Git target, coverage obligations, Python version, suite,
complete canonical/runtime test IDs, count, successful outcome and checkpoint outcomes.
Both producers must succeed; missing, failed, cancelled or mismatched evidence blocks the
join and the unchanged `test (3.11)` aggregate. Coverage-only tests do not inflate B.
An empty behavioral remainder is legitimate only when the verified C contains all of B.
For coverage=none, all of B executes and the coverage producer must be skipped.
Python 3.13 retains its independently executed behavioral suite.

Artifacts come from the same workflow run. Source-relative file/class/method identities
allow separate checkout locations and canonical import aliases without cross-commit reuse.
No persistent execution-result cache or new selection authority is introduced. Plans still
come from exact Git facts and base-side authority, and the independent witness is required.
Changing the runner/workflow itself requires full bootstrap and repository coverage.

Each producer keeps unittest module/class setup and teardown semantics. Splitting a class
between producers may initialize its fixture once per producer, as independent processes
already did. Tests must remain independently runnable; test methods are not chained through
hidden state. This change deduplicates cases, not all fixture initialization.

## Readable scenarios

Related checks on the same evolving fixture can share one scenario and use named
`subTest(checkpoint=..., case=...)` blocks. A failure remains attached to the module,
scenario and specific checkpoint. Later checkpoints can still run and report their own
failures. Independent contracts and separately selected mandatory negative cases retain
their identities.

The pilot consolidates these two dependency-cache tests into
`DependencyTests.test_cached_consumer_follows_inventory_lifecycle`:

| Previous test | Preserved checks in the scenario |
|---|---|
| `test_cached_facts_resolve_added_and_removed_modules_against_each_inventory` | Missing package, added package initializer/leaf, removed package, restored empty inputs |
| `test_cached_facts_keep_new_basename_and_directory_resource_matches` | Root README, newly added nested README, replaced directory child, unrelated directory exclusion, restored inventory |

The scenario uses one unchanged consumer through six named inventory checkpoints and
compares the complete dependency edge map at each checkpoint. The byte-invalidation
scenario also names its original, changed/dynamic, invalid, and restored source stages.
Different path identity and returned-graph mutation contracts remain separate tests.
The three required dependency positive/negative acceptance IDs remain unchanged.

Receipt schema 1.1 adds portable identity, scenario description and checkpoint records.
Scenario outcome counts and failure/skip event counts are separate. A failed subtest cannot
be overwritten by a subsequent success. A skipped checkpoint is reported as
`passed_with_skips`, which does not satisfy a mandatory `outcome=passed` acceptance case.
Class/module fixture errors remain visible even when no test body executed. Console and
GitHub summaries show failed scenarios/checkpoints before the slowest-test list.

## Measurement boundary

The green `fee47c0` run had B=1,112 and C=1,074, with C entirely inside B. Their producer
times summed to 3,575.083 seconds. The overlapping B test bodies account for 759.665 seconds;
the remaining 38 account for 198.848 seconds. These are recorded baseline durations.
Partitioning that inventory removes 1,074 duplicate executions and their associated work.
This arithmetic is not a measured workflow wall-time speedup: the long coverage producer
can still dominate elapsed time, and the evidence join adds a short collection/check job.
Coverage selector narrowing and process parallelism need their own measurements and proof.

Regressions execute actual Git-bound worker commands in separate Python processes, verify
fixture lifecycle and alias deduplication, exercise coverage-none and combined obligations,
and reject stale targets, missing/duplicated cases, failed producers/checkpoints, wrong
Python versions and unexpected coverage receipts. Exact-head hosted results are recorded
in the PR checks; earlier green heads are baseline evidence only.

The implementation follows the existing [unittest subtest API](https://docs.python.org/3/library/unittest.html#distinguishing-test-iterations-using-subtests)
and [coverage.py execution/report separation](https://coverage.readthedocs.io/en/latest/commands/cmd_report.html).
