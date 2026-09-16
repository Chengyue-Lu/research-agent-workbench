# M6-008 CI scope audit and PR #83 fixed-input repair

TEST-PERF-002 revision 31; Chengyue-Lu; R2. The user authorized adding unresolved
M6 dependency expansion repairs to PR #83 without changing the M6 branch.

## Scope

M6 PR #75 head `34cc426e9c08d837ffc2e6dc58732c08a659291e` and base
`7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba` produced a focused/impact plan with
91/92 behavioral modules and five instrumented source files. Its 108 coverage
selectors represent 89 modules. The hosted coverage job took 11m05s in successful
run `35025376167`. This is near-full test execution without repository instrumentation.

Exact fixed repository reads/scans and parsed script targets now follow their known
inputs. Unknown, mutated, escaped, symlinked and unparsed targets remain conservative.
The same M6 snapshots have 116 unbounded resource consumers instead of 125; nine
fixed-input consumers lose false direct fallback edges. Other paths still select
91/92 modules, so this repair does not claim an M6 runtime reduction.

## Evidence

- The prior PR #83 analyzer at `3fe8b1d97559465786640381d11754dce9ff4d65` fails
  eleven precision assertions in the new scenarios.
- Fixed-resource and fixed-script probes run against actual Git commits. Corrupting
  each input causes an AssertionError while the unchanged consumer stays selected.
- Further local coverage, exact-source plan and governance results are recorded in
  the checks accompanying this archive. Hosted final merge-target CI and the pinned
  independent witness remain separately required before acceptance.

Implementation commit: `1b642ae`. Local validation comprises 52 dependency tests,
104 planner/coverage/witness tests, 23 CI checker tests and 10 documentation tests.
The final non-regular Git-mode guard was rechecked with the complete 52-test dependency
suite under coverage. The analyzer covers 501/501 statements and 322/322 branches;
the unchanged planner covers 538/539 statements and 204/206 branches. No changed-line
or changed-branch gaps remain. Source-head plan verification and PR-event governance
pass with full behavioral / impact coverage obligations for this authority-changing PR.

`checks/final-critical-files.json` retains the final analyzer's independently collected
coverage and the unchanged planner's broader regression coverage. The broad run's older
dependency record and aggregate totals are not used as final-source evidence. The source
plan is for the implementation head; the archive commit receives its own hosted merge-
target validation. `checks/m6-hosted-plan.json` is the original downloaded M6 plan.

The primary develop checkout and M6 branch remain unchanged. No merge or release
authority is granted. Native event/message export is unavailable; capture-gap warnings
are retained rather than claiming complete capture.
