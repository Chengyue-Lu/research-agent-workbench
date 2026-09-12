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
required coverage tests. When coverage is required, one instrumented producer:

1. Runs the original B suite with its original hierarchy, order, and class/module fixtures.
2. Completes B's top-level teardown before loading the C suite. This also prevents imports
   of coverage-only modules from changing the state observed by B.
3. Runs C minus B in a subsequent fixture lifecycle on the same unittest result. Each
   canonical case in B union C executes once, and failures recorded by B remain failures.

The raw `coverage-execution` receipt records B followed by C minus B. Its
`ordered-behavioral-v1` contract contains the separately collected ordered B and C inventories.
The compatibility check reloads the inventories and validates schema, plan ID, tested Git
target, coverage obligations, exact Python version, suite, canonical/runtime IDs, counts,
actual order, successful outcomes, checkpoint outcomes and fixture failure/error events.
Legacy split-producer receipts cannot satisfy this contract. Missing, failed, cancelled or
mismatched evidence blocks the unchanged `test (3.11)` aggregate.

Verified projections retain the raw receipt digest. The behavioral receipt contains only B;
the coverage receipt contains the required C evidence. Coverage data records execution of
B union C and is checked against every planned coverage obligation. For an alias overlap,
the original B case executes; the C projection retains its requested identity alongside
`execution_id`, the actual runtime ID. Coverage-only IDs never enter the behavioral receipt.

For coverage=none, the original B executes once without instrumentation and the coverage
producer must be skipped. The aggregate checks that the plan authorizes that skip.
Python 3.13 retains its independently executed behavioral suite.

Artifacts come from the same workflow run. Source-relative file/class/method identities
allow separate checkout locations and canonical import aliases without cross-commit reuse.
No persistent execution-result cache or new selection authority is introduced. Plans still
come from exact Git facts and base-side authority, and the independent witness is required.
Changing the runner/workflow itself requires full bootstrap and repository coverage.

Shared class/module state is part of the behavioral suite's execution semantics. A mutation
in an earlier B case that fails a later B case must still fail this producer. Coverage extras
start only after that complete lifecycle; they cannot heal a failed body or teardown.

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

Receipt schema 1.2 retains portable identity, scenario description and checkpoint records,
and adds ordered execution evidence.
Scenario outcome counts and failure/skip event counts are separate. A failed subtest cannot
be overwritten by a subsequent success. A skipped checkpoint is reported as
`passed_with_skips`, which does not satisfy a mandatory `outcome=passed` acceptance case.
Class/module fixture errors remain visible even when no test body executed. Console and
GitHub summaries show failed scenarios/checkpoints before the slowest-test list.

## Measurement boundary

The green `fee47c0` run had B=1,112 and C=1,074, with C entirely inside B. Their producer
times summed to 3,575.083 seconds. The overlapping B test bodies account for 759.665 seconds;
the remaining 38 account for 198.848 seconds. These are recorded baseline durations.
Sharing one ordered execution of that inventory removes 1,074 duplicate executions and their associated work.
This arithmetic is not a measured workflow wall-time speedup: the long coverage producer
can still dominate elapsed time, and receipt verification adds a short collection/check job.
Coverage selector narrowing and process parallelism need their own measurements and proof.

The `8c09f6c` result reconstructed complete TestCase identity coverage from two producers;
it did not establish historical full fixture/order equivalence. Both a class-state and a
module-state counterexample fail direct full but pass that old split. The repaired unit
and real Git worker regressions require the ordered producer to preserve both failures.
They also cover teardown failure, coverage-only import ordering and behavioral exclusion,
alias deduplication, coverage-none, combined obligations, and receipt tampering.
Exact-head hosted results are recorded in the PR checks; earlier green heads and their
duration measurements are historical evidence only.

The implementation follows the existing [unittest subtest API](https://docs.python.org/3/library/unittest.html#distinguishing-test-iterations-using-subtests)
and [coverage.py execution/report separation](https://coverage.readthedocs.io/en/latest/commands/cmd_report.html).
