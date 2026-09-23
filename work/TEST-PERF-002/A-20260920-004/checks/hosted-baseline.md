# PR #92 current-head hosted acceptance evidence

Run [35497858451](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35497858451) completed successfully. This read-only observation downloads existing logs and artifacts; no CI rerun, branch change, or remote comment was performed.

## Binding

- Base and merge-base: `171d4654f88e926f239cdf25bc8168109b81f391`.
- Head: `387d18ebac7817b2a7492a60568b4ef194f557e3`.
- Tested merge target: `dc0bc58ef1d8d5fb036d68956c77c4dafe287b47`.
- Plan ID: `f7497f4b08b74379b8bf5de3d6da94cea3adff7a9a2ad76cc330d542252c2bf7`.
- Producer canonical SHA256: `3aea99aaec6223c7470664c3c1a8ea148b5c34ac275ad6fc3ccd8b15e922c82d`.
- PR observed state: OPEN; draft=true. This is an observation at retrieval time, not merge authorization.

The merge-commit API confirms the exact base/head parents. All execution receipts bind the same plan and target; both projected 3.11 behavioral and coverage receipts match the producer hash. Worker, smoke and aggregate checkout logs show this same merge SHA. All original artifact ZIPs were verified against the GitHub API SHA256 digests and ZIP CRCs.

## Obligations and execution

Plan: behavioral `full`, coverage `impact+repository`, package_smoke=true, repository_smoke=true.

The full/repository fallback still comes from `docs/workstreams/chengyue-lu/TEST-PERF-002/domain-model.json` being unclassified. Changes introduce diagnostic subjects, not activation of reduction. Impact subjects:

- `.github/scripts/ci_consumer_shadow.py`
- `.github/scripts/ci_domain_audit.py`
- `.github/scripts/ci_shadow_pair.py`

B=1424, C=1398, intersection=1398, C-B=0, B-C=26, union=1424. Executed=1424, unique IDs=1424; exact ordered B then C-B=True.

3.11 producer outcomes: `{"errors":0,"expected_failure":0,"failed":0,"passed":1424,"passed_with_skips":0,"skipped":0,"unexpected_success":0}`.
3.13 behavioral outcomes: `{"errors":0,"expected_failure":0,"failed":0,"passed":1424,"passed_with_skips":0,"skipped":0,"unexpected_success":0}`.

## Quality and smoke Gates

Hosted impact and repository coverage enforcement PASS. Canonical source-root line coverage 15733/16681 = 94.316887% (floor 90%). All 59 registered critical modules pass 95% line / 90% branch.

| Impact module | Covered statements | Covered branches |
|---|---:|---:|
| `.github/scripts/ci_consumer_shadow.py` | 205/205 | 84/84 |
| `.github/scripts/ci_domain_audit.py` | 121/121 | 38/38 |
| `.github/scripts/ci_shadow_pair.py` | 118/118 | 38/38 |

Repository validation: 186 validated / 0 errors / 0 warnings. Package smoke: four install routes per Python (direct and sdist-wheel, isolated and non-isolated), eight total probes PASS; each reports 142 resources, 94 schemas and identical runtime resources. Both fixed `test (3.11)` and `test (3.13)` aggregates pass against their required job set.

Separate governance run 35497858893 also PASS on this same head and merge target; its raw log and run metadata are retained. The PR rollup retains an earlier cancelled governance run 35497858467 (completed 07:48:28 UTC) followed by the successful run (completed 07:48:46 UTC). The successful run is the observed current governance evidence; the cancelled historical entry is preserved, not hidden.

## Observed cost

| Measurement | Seconds |
|---|---:|
| Whole workflow elapsed | 1708 |
| Initial created-to-first-job gap | 2 |
| Coverage job API wall | 1655 |
| Coverage producer wall | 1632.793267 |
| Sum of coverage case durations | 1508.590567 |
| Compatibility 3.13 job API wall | 883 |
| Compatibility 3.13 runner wall | 863.577824 |
| Sum of all job API walls | 2743 |

Job-wall sum is an execution-cost proxy, not a billed CPU measurement. Case timers do not independently expose shared class/fixture/runner lifecycle costs. Full step timing is preserved in summary.json.

| Largest coverage modules | Cases | Coverage seconds | 3.13 seconds |
|---|---:|---:|---:|
| `test_evaluation_harness_execution` | 25 | 458.025 | 236.124 |
| `test_ci_plan` | 73 | 117.768 | 55.132 |
| `test_evaluation_harness_preflight` | 13 | 103.768 | 51.302 |
| `test_baseline_execution` | 18 | 96.355 | 70.544 |
| `test_baseline_replay_integrity` | 19 | 96.115 | 43.738 |
| `test_skill_execution_closeout` | 33 | 68.898 | 34.657 |
| `test_evaluation_overlay` | 19 | 41.496 | 19.869 |
| `test_generic_execution_closeout` | 13 | 32.797 | 16.710 |

## Differences and claim limits

Compared with earlier PR #92 run 35468682117 at `b8b21b72459236508613e751d68aa02fc86967b1`, common case IDs=1418, earlier-only=0, current-only=6. Exact differing case IDs are retained in checks.json.

Coverage job time increased from 1191 to 1655 seconds; producer wall increased from 1169.746930 to 1632.793267 seconds. The six added test_ci_shadow_pair cases take only 2.513358 seconds under coverage (1.346470 seconds in 3.13), so their direct measured execution does not account for the additional 463.046337 seconds. Existing modules also run slower: H3 execution 318.473 to 458.025 seconds, CI plan 86.691 to 117.768 seconds. This observation identifies where the increase is recorded, not whether host variance, instrumentation, or other interactions caused it. Same-environment paired evidence is required.

This is fresh validation of a changed Git target and workload. It is not a paired same-target performance experiment, and lower job time cannot be attributed to the diagnostic implementation. Different Python workers also do not isolate coverage instrumentation overhead. Activation, review and any performance claim require their own evidence.

## Preserved raw evidence

- run.json, pr.json and timestamped run snapshots: current head and job/Gate observations.
- governance-run.json and governance.log: successful current governance run, head and merge-target evidence.
- target-commit-api.json: exact tested merge parents and tree.
- workflow.log and coverage.log: full checkout, smoke, threshold, Gate and duration evidence.
- artifacts.json, original ZIPs, artifacts/, verification.json: raw receipts/coverage/plan/shadow and verified API digests.
- summary.json: all job/step times, B/C counts, ordered-union verification and complete module costs.
- checks.json: plan/target/producer binding, threshold inventory, smoke outputs and case differences.
- SHA256SUMS.json: byte lengths and SHA256 hashes, excluding itself.
