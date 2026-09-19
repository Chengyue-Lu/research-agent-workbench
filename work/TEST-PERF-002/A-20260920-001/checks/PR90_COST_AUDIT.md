# PR #90 hosted CI cost audit

Observed run: [35449976025](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35449976025), completed 2026-09-19, status **failure**. Audit is read-only. No tests rerun, source changed, CI rerun, or business-owner branch modified.

## Exact evidence identity

- PR head: `d9042fd1611f152573a7d2cae176cb1e1ec70065`.
- Plan base and merge-base: `171d4654f88e926f239cdf25bc8168109b81f391`.
- Executed target: `737fb4198eac1e51f42da2f2204971ef96ec5ace`.
- Plan ID: `8ca44bba92c53e16a9bcf324b191f3abcc9adb68e142f2e2e425ee43e15527ea`.
- Plan policy SHA256: `f7fc9d92ce0271f323e5973751f1e08933d6398fc50faf251cdbda902f33d67a`.
- CPython coverage producer: 3.11.16; coverage.py 7.16.1. Compatibility worker: CPython 3.13.15.

Raw plan, execution/coverage receipts, full coverage JSON, shadow report, run API job/step timings, and coverage log are retained here. `verification.json` records artifact ZIP digests against the GitHub API and source copies against exact Git blobs. `SHA256SUMS.json` enumerates local evidence hashes. Source copies represent the PR head; they are not observations of runtime profiling.

## Where the 37 minutes went

| Measurement | Seconds | Interpretation |
|---|---:|---|
| Workflow created to first job start | 3 | Observed initial scheduling gap; not all per-job queue time |
| Whole workflow created to completed | 2300 | 38m20s |
| Coverage job API start to end | 2263 | **37m43s** |
| Coverage clock reported by workflow | 2260 | Different clock endpoints |
| Coverage checkout/dependencies/plan before execution step | 10 | API start to execution-step start |
| Ordered behavior + coverage execution step | 2244 | **37m24s**; includes configure/runner overhead |
| Runner receipt wall | 2239.890768 | Test producer interval |
| unittest reported execution interval | 2227.070 | Includes fixture lifecycle |
| Sum of individually timed cases | 2015.878845 | Per-case timings exclude some shared fixture/lifecycle overhead |
| Export/check/upload/post-step tail | 9 | Execution-step end to coverage-job end |
| Compatibility 3.13 runner receipt | 564.161839 | Same 1425 tests; 9m24s |
| Compatibility 3.13 whole job | 580 | 9m40s |
| All jobs' API wall summed | 3024 | 50m24s aggregate job-wall proxy; not billed CPU measurement |

The long critical path is real test execution, not queue, pip installation, or artifact upload. The approximately 224-second gap between receipt wall and summed case time cannot be attributed to a specific module from this receipt alone; class setup/teardown and runner work are not independently timed. Per-phase instrumentation is needed before claiming that cost is fixture work.

The 3.11 coverage run is about 3.97 times the 3.13 uninstrumented worker wall. This is observational: Python version and host differ, so it **does not isolate coverage instrumentation overhead**. A paired same-version run is required for that attribution.

## No repeated B/C union execution

| Set | Count |
|---|---:|
| Behavioral B | 1425 |
| Coverage C | 1399 |
| B intersection C | 1399 |
| C minus B | 0 |
| B minus C | 26 |
| B union C | 1425 |
| Executed cases / unique case IDs | 1425 / 1425 |

The receipt preserves ordered B followed by C minus B exactly. All 1425 outcomes passed. There is no duplicate full-suite union execution in this producer. The 3.11 compatibility gate uses the producer receipt and did not launch another behavioral suite. Its failure is downstream of failed coverage enforcement.

## Why this plan expands

Observed obligations are R2, behavioral `full`, coverage `impact+repository`, both smokes true.

1. **All behavioral full reasons are 42 `unclassified dependency surface` paths in the new attempt archive.** Examples are `.gitattributes`, `.log`, `.json`, `.yaml`, `.txt`, and `trace/events.jsonl`. The planner's `non_executable()` recognizes Markdown, `work/`, and selected `tests/` data; a documentation surface match itself does not stop unknown-surface fallback. See exact `plan_ci.py:291` and `:498-521`.
2. These same 42 reasons cause repository coverage. This is not an R2-to-full rule and is not caused by the additive coverage-policy registration: the plan explicitly reports **`monotonic local coverage evidence additions`**. `selection.errors` is empty.
3. Smokes have independent legitimate inputs: the new installed schema triggers package/repository validation obligations, and affected public CLI/repository validation consumers are reported. Removing archive fallback would **not alone justify turning these smokes off**.
4. Existing shadow diagnostic already classified archive data and reported the 42 classification conflicts in about seven seconds. It correctly remains `execution_authority=false`, with activation requiring reviewed contracts, independent witness acceptance, and real failure/precision corpus.

This is a boundary-model gap to close through declared archive consumers and shadow replay. It is not evidence for blindly excluding all files below `docs/`: the same archive also contains an executable one-shot producer.

## Actual failure and ownership

Coverage enforcement failed **after successful test execution**, at exact `ci_checks.py:76`:

```text
ValueError: impact module absent: docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/attempts/M5-007-H4-001/export_capture.py
```

The script is a real one-shot delayed capture exporter importing `AgentTraceRecorder`, reading a local `.rwb` spool, and writing the archive. It is neither ordinary Markdown nor installed production code. The plan includes it among four executable impact modules. The coverage configurator permits planned files but relies on root discovery (`source=.`) for auxiliary subjects; permitting an unexecuted non-package archive script does not guarantee a measured file record. The full suite did not supply its expected coverage evidence.

Therefore the immediately evidenced defect is **CI subject classification/measurement and late viability checking**, not a failed M5 behavior. Decide the script's intended contract explicitly: retained historical producer vs maintained executable consumer. Bind that decision to accepted metadata/witness and referenced-reader tests. If maintained, its independent tests/instrumentation belong to its owner. If retained provenance only, use a reviewed archive contract, not blanket path-based exclusion. A cheap preflight should reject an unsatisfied measurable-subject obligation before expensive execution where that can be established structurally.

The new business module `harness_evidence.py` has 102/102 statements and 32/32 branches in the raw hosted coverage artifact. Source-root global line coverage computes to 15835/16783 = 94.351427%; this is a raw observation, not a completed coverage Gate. The checker stopped before completing all obligations. No M5 business failure is evidenced in this run. Hand off any business-test redesign to task **开发（3）**; this audit makes no business changes.

## Dominant tests and concrete internal-cost direction

| Module | Cases | Coverage case seconds | 3.13 case seconds |
|---|---:|---:|---:|
| `test_evaluation_harness_execution` | 25 | 480.638 | 114.757 |
| `test_evaluation_harness_evidence` | 15 | 456.542 | 112.487 |
| `test_ci_plan` | 73 | 120.045 | 30.090 |
| `test_evaluation_harness_preflight` | 13 | 109.137 | 24.586 |
| `test_baseline_replay_integrity` | 19 | 98.134 | 21.154 |
| `test_baseline_execution` | 18 | 97.296 | 35.775 |
| `test_skill_execution_closeout` | 33 | 73.237 | 17.067 |

H3 execution and H4 evidence together consume 937.179 case seconds: **46.49% of summed case time** and 41.84% of runner wall. They are plausibly relevant to this M5 change, so eliminating unrelated tests alone cannot eliminate this core cost. The new H4 module accounts for 7m37s of individually timed cases; this is not a paired baseline regression estimate.

The two slowest cases are H4 projection/supply/tool/binding tampering (87.547s) and missing failure/slice/case/attempt substitution (86.158s). Exact source inspection finds four mutations in each. Each calls `validate_harness_evidence()`, which rebuilds via `compile_harness_evidence()`, which replays the complete H3 run. Thus each matrix executes four complete replay paths to prove four downstream comparisons. This is a concrete cost multiplier, not proof that any negative assertion is redundant.

The tests already build a completed archive once in `setUpClass` and clone it per case; simply introducing a shared fixture is not a new optimization. Preserve cold replay and real validation obligations. Next profile separately: class construction, filesystem/deepcopy cloning, fresh reads/schema parsing, H3 replay, and H4 comparison. Then propose an owner-reviewed split between full integration proofs and focused comparator proofs with identical positive/negative detection. Do not replace required integration evidence with mocks or silently share trusted execution results across mutations.

## Recommended CI work order

1. Register this exact run as a real corpus item: archive-data conflicts, auxiliary executable subject, installed-schema smoke, M5 semantic consumer, and successful B/C de-duplication control.
2. Implement domain/consumer shadow with explicit predictions and named retained/skip candidates. Compare with accepted execution; preserve unknown fallback and fixed aggregates.
3. Add a cheap structural obligation viability diagnostic for changed auxiliary executables. Surface the exporter issue before a 37-minute run where possible; keep enforcement fail closed.
4. Measure instrumented/uninstrumented same-Python pairs and fixture lifecycle; pursue independent internal-cost improvements without changing selection authority.
5. Activate any archive exclusion only after real failing referenced-consumer and unrelated precision controls, exact target bindings, and candidate-independent witness review. Keep source/schema smokes and fresh integration coverage as required.

No speedup is claimed by this audit. It distinguishes observed cause, implementation hypotheses, and required future evidence.
