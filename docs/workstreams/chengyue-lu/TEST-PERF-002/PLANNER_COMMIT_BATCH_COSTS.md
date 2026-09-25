# Planner exact-commit batching: bounded cost slice

Owner Chengyue-Lu; TEST-PERF-002 / Issue87. Candidate implementation on accepted
baseline `6cf80610cc2d3b4ebdeb9f47a840cd0ec1870bbf`; independent R2 review and complete integration checks remain.

## Current native cost evidence

Re-ranked the original successful [develop push run35851960207](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35851960207)
receipts at this exact target. These are historical observations, not a new run or a controlled coverage/plain comparison.
Coverage3.11 producer wall was1516.435344s; compatibility3.13 wall663.473623s.

| Receipt | Rank | Module | Sum of case durations, seconds | Cases |
|---|---:|---|---:|---:|
| coverage-3.11 | 1 | `test_evaluation_harness_execution` | 424.422208 | 25 |
| coverage-3.11 | 2 | `test_ci_plan` | 125.075955 | 80 |
| coverage-3.11 | 3 | `test_evaluation_harness_preflight` | 94.539906 | 13 |
| compatibility-3.13 | 1 | `test_evaluation_harness_execution` | 175.669333 | 25 |
| compatibility-3.13 | 2 | `test_baseline_execution` | 55.592634 | 18 |
| compatibility-3.13 | 3 | `test_ci_plan` | 51.893668 | 80 |

Planner is the highest CI-owned module in both receipts. The two other coverage leaders are business harness modules and stay with their owners.
Planner case durations sum to 8.25% of coverage producer wall;
batching improves only a fraction of that module, so it cannot alone solve full-suite duration.
Original artifact10746748818 execution receipt SHA256 `d3338824dcc040a93347075d3a7b265dbcbea3da96dee2b85554879a49160523`;
artifact10746790816 compatibility receipt SHA256 `bf78537969f8dbcbd1ef75259140adf93ac00533aa45f2308d71628d4142ed15`.

## Change and invariants

One `make_plan` validates base/head/target using one actual Git `rev-parse` process
instead of three. Validate every argument's full lowercase40-character format
before Git; preserve duplicate inputs and compare every output position. The
public singular helper delegates to the same fresh operation. Every `verify_plan`
still invokes Git again; no persistent identity cache is added. Existing
`--no-replace-objects` behavior remains. A request with multiple invalid inputs may
now report a format error before an earlier missing-object error; both fail closed.

No selection, B/C order, runner preflight, coverage policy, thresholds, fixture
isolation, test removal or business code changes. All 80 original planner test
bodies are AST-identical; four new tests cover identity positions, malformed
arguments, real blob/tree/tag/missing objects with replacement refs, and removal
of a previously verified loose commit object before re-verification. Real Git is
wrapped only for call observation; its arguments/results are unchanged.

## Local measured validation

Six focused checks passed: four added regressions plus existing docs-plan replay
and independent-clone isolation checks. Three AB/BA/AB fresh process pairs ran the
original native planner leader
`PlannerTests.test_contract_pins_each_behavioral_proof_and_acceptance_module`.
Each executed the identical canonical case, subtest order, outcomes and 8
subtest checkpoints, under Python3.11.16, Windows, branch coverage, the same
dependencies and fixture inputs. Existing per-case fixture construction/cleanup
remain inside the timed interval. This is one representative case, not the full module.

| Variant | Three seconds | Median seconds | Range seconds |
|---|---|---:|---|
| before | 34.712646, 34.060856, 34.404051 | 34.404051 | 34.060856–34.712646 |
| after | 32.259544, 32.504804, 31.790705 | 32.259544 | 31.790705–32.504804 |

Observed local median reduction: 6.23%.
Paired after-minus-before seconds: -2.453102, -1.556052, -2.613346.
The table measures test loading, fixture setup, case execution and cleanup. Process
startup, planner import and coverage start/stop sit outside that inner timer but
remain in command receipts: external process median
34.732055s→32.580612s.
This does not establish hosted CI, full-suite or aggregate critical-path savings.
Coverage records the baseline planner from its retained source file and the
candidate from its actual source path; both read identical live fixture inputs.
The before module's ROOT is explicitly bound to the same checkout. The initial
attempt omitted that binding and failed locating the governance script; that
failed log is retained and excluded from all valid pairs.
An earlier six-sample series omitted the saved baseline planner from coverage's
source scope and imported the two planners at different measurement stages. That
series is retained as invalid measurement and excluded. The final series imports
both planners symmetrically before the timed interval, includes both source
locations in branch coverage, and asserts nonempty measured planner lines/arcs.

A separate plain cProfile/operation-count run of the same case passed for each
variant; it is excluded from timing gains. Total real subprocess calls were
579→531.
Identity validation occupied 2.971029s
(9.30% of its profiled case) before and
1.026751s (3.40%) after.
This attributes the bounded saving; process reduction alone is not a speed claim.
The operation profile records 24 real `make_plan` invocations: identity subprocesses
decrease from72 single-SHA calls to24 triple-SHA calls, exactly two per invocation.

## Remaining acceptance and evidence

The implementation diff is limited to planner batching and four independent regressions;
the workstream report, navigation and risk entry record this slice. Exact-target hosted
checks and cross-owner review remain the merge boundary. The first failed harness
version was not snapshotted before its path repair; its command and failure log remain.
The archive discloses this capture gap and partial collaboration/tool capture.

Independent static code review found no substantive issue in the two-file implementation
at the recorded source hashes. A separate Python 3.13 run passed the same six focused
checks. This review does not replace cross-owner approval, and those checks do not
replace complete planner-module or integration evidence. The completed Python 3.11
planner-module run passed all 84 cases: 588/589 executable lines (99.8302%) and
222/224 branches (99.1071%). The local diff and coverage facts cover all 9 changed
executable lines and both outgoing branch arcs. These are local module and changed-code
facts, not a native impact receipt or a repository-wide/hosted Gate conclusion.

The [Attempt A-20260924-002](../../../../work/TEST-PERF-002/A-20260924-002/RESULTS.md)
binds the actual complete-module result, both focused runs, independent review,
fair and invalid timing series, original failures and source hashes. Local checks
retain their original execution identity; matching committed source bytes does
not turn them into hosted exact-target evidence.
