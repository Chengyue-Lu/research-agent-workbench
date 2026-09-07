# Post-merge hosted operational verification

Accepted base: `690a9f8c89c32400bbc57b0781ef9b43205894db`, the squash merge of PR #63.
User request: test whether the merged selective CI takes effect. Evidence uses one controlled
[draft verification PR #64](https://github.com/Chengyue-Lu/research-agent-workbench/pull/64) with sequential
documentation and AST-equivalent Provider literal edits. The probe is closed after capture; its changes
are not release or product work. Natural feature-PR performance observation remains separate.

## Observed behavior

| Scenario | Hosted evidence | Result |
| --- | --- | --- |
| Allowlisted docs-only diff | [FAST 34049735916](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34049735916) | FAST; 76 documentation/governance tests pass; both aggregates pass; compatibility, coverage and smoke jobs skip as the plan requires |
| PR body edit | [34049868007](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34049868007) | Only governance; reuses completed FAST plan 34049735916 |
| Add documentation label | [34049895921](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34049895921) | Only governance; same content plan retained |
| Provider leaf diff | [FOCUSED 34049937742](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34049937742) | provider-wire → conformance → session → CLI; 81/81 pass on each Python; 81/81 coverage suite pass; required package/repository smoke and aggregates pass |
| New HEAD replaces an active run | [34050011774](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34050011774) | Automatically cancelled by the next HEAD; no manual cancellation |
| Replacement HEAD closes normally | [34050042447](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34050042447) | Replacement FOCUSED content run and both aggregates succeed |
| Actual develop integration | [FULL 34043176406](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34043176406) | Correctly selects FULL and propagates a failing unit test to both aggregate gates |

FOCUSED's authenticated log reports `coverage_mode=impact` and `repository_coverage_proved=false` for the
three Provider files. The selected suites' plan IDs and merge targets match the corresponding plan artifacts.
The leaf edits preserve the Python AST and do not contact a live Provider.

## Timing boundary

| Scenario | Content job execution span | Sum of content job durations | Suite time |
| --- | --- | --- | --- |
| FAST | 37 seconds | 38 runner-seconds | 76 tests in 0.215 seconds |
| FOCUSED | 88 seconds | 226 runner-seconds | Python 3.11: 33.146 s; 3.13: 24.367 s; impact coverage: 51.899 s |

Execution span is earliest job start to latest job completion; runner-seconds sum non-skipped jobs. These
figures include job setup but exclude queue time, separate governance and cancelled probes. They establish
hosted operational behavior for controlled changes, not a general speedup factor or natural product-change
benchmark. FULL still runs its existing suites; this task does not change their performance topology.

## Integration failure and bounded repair

The actual post-merge FULL run executes 892 behavioral tests per Python and 831 coverage-suite tests. Each
suite has the same single error: `test_cli_emits_canonical_plan_and_workflow_outputs` passes a synthetic PR
payload but inherits `GITHUB_EVENT_NAME=push`, leading to `ValueError: unsupported PR event`. Package,
repository and documentation jobs pass. The aggregate failures correctly preserve fail-closed behavior.

The same failing test was reproduced locally under `GITHUB_EVENT_NAME=push`. The repair passes
`--event-name pull_request` explicitly with that synthetic PR payload and checks the fixture under all three
ambient events: `pull_request`, `push` and `workflow_dispatch`. Planner event validation remains unchanged.
The reviewed test-content fingerprint is refreshed so this fixture-only repair does not leave the existing
Provider closure disabled after acceptance.

Local repair evidence: 37/37 planner/checker regressions pass under `GITHUB_EVENT_NAME=push`; 30/30
documentation/coverage-policy regressions pass. A separate R2 repair PR carries final-head FULL evidence.
Until that repair is accepted and develop integration is green, post-merge FULL is not an all-pass claim.

## Evidence and remaining scope

[Attempt index](../../../../work/TEST-PERF-002/A-20260907-001/INDEX.yaml) pins compact hosted summaries,
the test-environment failure/repair audit and observable execution facts. Full raw artifacts remain on the
linked hosted runs and in ignored local evidence storage. Native capture gaps are declared.

Issue #48 remains open for its profiling, Phase C coverage-suite boundary work and evidence-based follow-up.
This verification does not change quality thresholds, test inventory, product contracts or release gates.
