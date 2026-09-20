# PR #92 hosted CI observation

Run [35468682117](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/35468682117), attempt 1, pull_request event, completed successfully on 2026-09-19 UTC. This audit downloads existing evidence; it does not rerun CI, change a branch, or modify business code.

## Exact identity and provenance

- Repository: `Chengyue-Lu/research-agent-workbench`.
- PR head: `b8b21b72459236508613e751d68aa02fc86967b1`.
- Base and merge-base: `171d4654f88e926f239cdf25bc8168109b81f391`.
- Tested target: `f786ed5652af0320fb84ebfdecdba3b978da51de`.
- Plan ID: `d9fc68506c372f0a9b67ea6be4e4645a32a473a30cb092213dc3da6f60724746`.
- Producer receipt canonical SHA256: `d397620bbbf46102b063f453cae8cbda21e47e670193c1ae45d0102522d1ea2f`.

The exact merge object was fetched into the shared Git object store without changing any checkout or branch. Its two parents are the base and head above. All execution receipts share the plan ID and target. Both the 3.11 behavioral projection and the coverage projection match the producer's canonical hash. Worker, smoke, and aggregate checkout log lines independently show this target. See `checks.json` and `target-commit.txt`.

All five artifact ZIP SHA256 digests match the GitHub API and pass ZIP CRC validation. Raw ZIPs and extracted contents are retained. The exact target workflow and coverage policy are retained under `tested-source/`. This proves this CI run's observed state, not cross-owner review or merge authorization.

## Actual obligations and timing

Plan: risk R2; behavioral full; coverage impact + repository; package smoke true; repository smoke true.

The sole behavioral full reason is:

```text
unclassified dependency surface: docs/workstreams/chengyue-lu/TEST-PERF-002/domain-model.json
```

The same reason requests repository coverage. Impact covers `.github/scripts/ci_consumer_shadow.py` and `.github/scripts/ci_domain_audit.py`. Smoke reasons also report affected public CLI and repository-validation consumers. These are accepted-plan facts; this observation does not grant an exclusion for the model JSON.

| Measurement | Seconds |
|---|---:|
| Whole workflow created to completed | 1243 (20m43s) |
| Initial created-to-first-job gap | 2 |
| Coverage job API wall | **1191 (19m51s)** |
| Coverage clock printed by workflow | 1187 |
| Ordered behavior + coverage execution step | 1173 |
| Coverage runner receipt wall | **1169.746930** |
| unittest execution interval | 1160.698 |
| Sum of coverage case timings | 1079.557003 |
| Compatibility 3.13 job API wall | **870 (14m30s)** |
| Compatibility 3.13 runner wall | **855.218937** |
| Sum of compatibility case timings | 798.230191 |
| Compatibility 3.11 receipt-verification job | 22 |
| Package smoke 3.11 / 3.13 | 61 / 59 |
| Repository smoke | 14 |
| Sum of all API job walls | 2278 (37m58s) |

Coverage checkout/dependencies/download used approximately ten seconds; export/upload/enforcement used six seconds. The critical path remains execution. The 90.19-second difference between runner wall and case sums includes unseparated fixture/lifecycle/runner costs; it is not a measured per-module fixture profile. Aggregate job-wall is a compute-cost proxy, not billed CPU or pure test time.

## B/C and quality evidence

| Set | Count |
|---|---:|
| Behavioral B | 1418 |
| Coverage C | 1392 |
| Intersection | 1392 |
| C minus B | 0 |
| B minus C | 26 |
| Union / executed / unique IDs | 1418 / 1418 / 1418 |

Ordered B then C minus B is exact. All 1418 cases pass under the 3.11 producer and the separate 3.13 compatibility worker. The 3.11 compatibility job verifies the projected producer receipt rather than executing the suite again.

- Hosted coverage enforcement **PASS**, not merely raw percentages: final log reports impact result and `repository: passed`.
- Canonical source-root line coverage: 15733/16681 = **94.316887%**, meeting global 90%.
- All **59** registered critical modules meet 95% line / 90% branch. Lowest reported line is 95.64%; lowest branch is 90.00%.
- `ci_consumer_shadow.py`: **197/197 statements, 78/78 branches**.
- `ci_domain_audit.py`: **121/121 statements, 38/38 branches**. Both impact subjects therefore preserve changed 100/100.
- Repository smoke: **186 validated, 0 errors, 0 warnings**.
- Both package workers pass direct-wheel and sdist-wheel routes in isolated and non-isolated installs: **8 total install probes**, 142 runtime resources and 94 schemas each. Resource manifest SHA256 agrees across workers: `999d722fcfcd54881ae34003e6d4194205fd53dd7b94acf23afac1f3a50d909f`.
- Fixed `test (3.11)` and `test (3.13)` aggregates pass and print this plan ID plus their required obligation jobs.

## Dominant case costs

| Module | Cases | Coverage seconds | 3.13 seconds |
|---|---:|---:|---:|
| `test_evaluation_harness_execution` | 25 | 318.473 | 238.897 |
| `test_ci_plan` | 73 | 86.691 | 54.405 |
| `test_evaluation_harness_preflight` | 13 | 76.267 | 51.304 |
| `test_baseline_execution` | 18 | 69.129 | 69.751 |
| `test_baseline_replay_integrity` | 19 | 68.506 | 42.829 |
| `test_skill_execution_closeout` | 33 | 49.966 | 33.692 |

H3 execution is 29.50% of summed coverage case time. Slowest cases: transient retry 49.990s, four-arm execution/cold replay 41.269s, slice-gap deadline 35.533s, dispatch-clock replay 23.240s, preflight validator pins 18.190s. Complete module/case lists are in `summary.json`.

## Comparison limits and next measurement

PR #90's 37m43s coverage job and this 19m51s job are **different workloads and different Git targets**. Their case-ID intersection is 1410; PR #90 has 15 additional H4 evidence cases, while PR #92 has eight additional CI diagnostic cases. Their shared-case source bytes and host conditions have not been established equivalent. Compatibility 3.13 is actually slower here than in PR #90. Therefore the cross-PR time difference is not proof that this PR reduced CI cost.

This run is a complete, fresh accepted-plan baseline for later paired shadow replay. Keep its real cost data, exact identities, and unchanged B/C union control. Any predicted shadow reduction must remain diagnostic until paired same-target measurements and failing-consumer/precision evidence support activation. Different Python workers are also not a controlled coverage-overhead comparison.

## Reproducible evidence files

- `run.json`, `run-api.json`, `pr.json`, `artifacts.json`: GitHub observations.
- `workflow.log`, `coverage.log`: exact checkout, thresholds, smoke outputs, and timings.
- `artifacts/`: five extracted evidence bundles; original ZIPs are adjacent.
- `verification.json`: artifact ID, SHA256 and CRC verification.
- `summary.json`: B/C sets, all modules/cases, job/step cost summary.
- `checks.json`: receipt binding/hash, exact checkout evidence, threshold inventory, PR #90 case differences.
- `SHA256SUMS.json`: local-file byte counts and SHA256 hashes, excluding the manifest itself.
