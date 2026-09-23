# Coverage/smoke control pair completed

Owner: Chengyue-Lu. `execution_authority=false`; production activation remains ineligible.

The current `ci_shadow_pair.build_report` returns **`observed-matching-pair`**, with no pair blockers, for the single local Python 3.11 control in `provider-positive/short-temp-pair/paired-report.json`.

| Identity | Value |
| --- | --- |
| Immutable accepted base | `348d6257ddd28637c9d06abe177fc685ac4368b6` (PR85) |
| Isolated tested target | `51eb115119d3ea7b9639fae86ba94e0f5f0be8ea` |
| Plan | `f8091e8ca27f552f3c30a9c99bf36a74bf614344999c816098294856a9885736` |
| Source change | OpenAI provider line 72, `self.timeout_seconds = +timeout_seconds` |
| B / C / C minus B | 81 / 34 / 0 |
| Proposed exclusions | 0 |
| Driver SHA-256 | `5a93e5bc31c5e541c0e8a8e9535fb1e24fb953542ecd5ba58969f1957632da0b` |
| Environment / driver | Equal; full invocation differs only in the `--role` value |
| Pair report SHA-256 | `88758a6c784ee2eebb8713510c5d20849e8c528240d5d943811d8d8bbfc1df78` |

| Fresh execution | Accepted | Candidate |
| --- | ---: | ---: |
| Native B cases | 81 PASS | 81 PASS |
| Native C evidence | 34 PASS | 34 PASS |
| Runner wall | 19.179342 s | 18.632539 s |
| Coverage process wall, including collection | 29.296301 s | 28.596206 s |
| Raw coverage / unchanged impact Gate | PASS | PASS |
| Repository smoke | 186 validated / 0 errors / 0 warnings | 186 validated / 0 errors / 0 warnings |
| Package smoke | Four fresh direct/sdist × isolated/nonisolated installs PASS | Four fresh direct/sdist × isolated/nonisolated installs PASS |
| Package smoke process wall | 62.188630 s | 62.904056 s |
| All recorded subprocess steps | 98.717210 s | 98.634778 s |

No tests were removed, so the small timing difference is noise, not a reduction result. This verifies that the diagnostic protocol can retain and check actual ordered B/C execution, raw impact coverage, existing positive/negative mappings, and independently rerun required smokes on both roles. These provider files are not critical inventory members. The separate Claim critical case remains prepared only; no new critical 95/90 or repository-wide coverage claim is made.

## Preserved controls and setup diagnosis

- `provider-pair/`: original guard-change target `09361362c7d4d8fdf4599f066965ee092c05b939` passes all 81 behavioral cases but the unchanged impact checker rejects missing affected line 65 / branch 64→65. No candidate or smoke is represented as run. This is real fail-closed coverage evidence.
- `provider-positive/provider-pair/`: same positive target as the successful pair passes behavioral, impact and repository checks, but package smoke fails in a deep temporary directory. The inferred build-resource target length is 260 characters; its historical random basename was removed by native cleanup.
- Only TEMP/TMP changed for `short-temp-pair/`, to the separately authorized `D:/lcy/develop/_tmp/ci92-20260920`. Both roles now succeed with independently observed, existing 193-character build resource paths. The old failure remains a setup failure, with no retroactive success relabeling.
- `prior-artifacts-unchanged.json` verifies all 49 frozen files from both earlier attempts remain byte-identical.

## Retained evidence and replay

`PREPARATION.md` explains current baseline fingerprint fallback, historical selection, setup and scope. The first two observations retain their original `accepted-shadow.json`, native receipts, raw coverage, `.coverage` databases, exact commands/exits, producer sources, fallback decisions, and thin Git bundles.

`provider-positive/short-temp-pair/` contains both native receipts, separate raw coverage and SQLite data, native 34-case projections, fresh expected inventories, environmental/context snapshots, identical driver source, smoke reports/logs/bindings, two execution bundles, exact step commands, actual temporary paths, final pair report and `artifact-sha256.json`.

The failed scenario bundle is `provider-pair/failed-scenario.bundle`; the positive bundle is `provider-positive/provider-pair/positive-scenario.bundle`. Both were verified and require the immutable PR85 base. The current isolated snapshots remain clean. Raw Windows coverage keys were preserved unchanged; original and semantic artifact digests are separately retained. No coverage artifact was transformed or re-signed for this report.

`frozen-existing-proposal.json` preserves all 73 audited PlannerTests IDs and 19 pins. Real comparator output retains every test because the proposal baseline differs and executable changes are outside its Markdown pilot. Pin drift is recorded, not refreshed.

## Remaining limits

The accepted develop base is `171d4654f88e926f239cdf25bc8168109b81f391`. The audited PR head snapshot `387d18ebac7817b2a7492a60568b4ef194f557e3` inherits that base's policy anchor; it is not the accepted develop base. The accepted closure fingerprint/anchor mismatch is documented in `fingerprint-anchor-audit.json`, and the local executable controls based on that PR snapshot expanded to B1412/C1386. This historical experiment does not fix or bypass that debt.

This is one local Python 3.11 pair. It does not supply the Python 3.13 matrix, three hosted pairs, a trusted exclusion witness, production activation or demonstrated savings. No primary checkout, production policy, business branch, test body or coverage threshold changed.
