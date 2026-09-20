# Paired protocol readiness evidence

TEST-PERF-002 / Issue #87 / PR #92; owner Chengyue-Lu; risk R2; 2026-09-20.
Implementation `35b5b28eb070e588f80c92b1ea9371dd0fcf2fd6`; accepted base `171d4654f88e926f239cdf25bc8168109b81f391`.

## Protocol review closure

Independent review reproduced three false matching observations: an unexplained
aggregate skip, equal driver bytes with changed invocation options, and a copied
opposite-member smoke result. All three are repaired and independently rechecked.
Only an identical invocation or its single explicit `--role` value may differ.
Smoke requires member run/receipt association and the original artifact digest.

Related Python 3.11 regression: 52 PASS in 40.761 s. Final targeted Python 3.11:
11 PASS in 10.660 s; Python 3.13: 11 PASS in 8.412 s. Consumer comparator covers
205/205 statements and 84/84 branches; paired comparator 123/123 and 40/40.
No coverage exclusions or production selection policies changed. Independent
recheck: four focused methods and six direct protocol counterexamples passed.

The original 325/252 document execution artifacts were read from the previous Git
archive and re-evaluated with the repaired comparator. The report still matches
and retains 73 proposed exclusions. This is a protocol replay, not fresh execution
or a new timing measurement; the original target and local-only scope remain.

## Real impact and smoke observations

Historical accepted base `348d6257ddd28637c9d06abe177fc685ac4368b6` supplies a bounded
provider control. The isolated positive target is
`51eb115119d3ea7b9639fae86ba94e0f5f0be8ea`, with plan
`f8091e8ca27f552f3c30a9c99bf36a74bf614344999c816098294856a9885736`.
It changes a covered provider assignment; the Markdown-only consumer proposal
retains every source-case obligation.

| Fresh observation | Accepted | Candidate |
| --- | --- | --- |
| Behavioral / coverage inventory | 81 / 34, C minus B = 0 | 81 / 34, C minus B = 0 |
| Native cases | 81 PASS | 81 PASS |
| Native runner wall | 19.179342 s | 18.632539 s |
| Impact checker | PASS | PASS |
| Repository smoke | 186 / 0 / 0 | 186 / 0 / 0 |
| Package smoke | Four fresh install probes PASS | Four fresh install probes PASS |
| Recorded subprocess steps | 98.717210 s | 98.634778 s |

Both fresh processes use the same driver, environment and exact target. Their
raw coverage objects remain unchanged; each smoke is associated with its own
run/receipt and original artifact. The current comparator returns
`observed-matching-pair`, with no blockers. Zero exclusions means no claimed
speedup. Provider subjects are not critical inventory members; this local pair
does not establish critical 95/90 or repository-wide coverage.

Two original failures remain preserved. A guard-change target passes all 81 cases
but fails impact coverage for line 65 / branch 64 to 65. A first run of the positive
target passes behavior, coverage and repository validation, but fails package
build at a deep temporary path. Both roles then rerun the same positive target
using a shared short TEMP setting: observed successful resource paths are 193
characters. The previous failed path length of 260 is inferred from the native
temporary-directory pattern; its deleted random basename was not captured.
All 49 prior evidence files remain byte-identical, and both isolated targets have
verified thin Git bundles against the immutable historical base.

## Inherited production anchor debt

At current accepted base `171d4654...`, the same leaf controls expand conservatively
to B1412/C1386. PR #86/#89 diagnostic consumer pin edits move the planner's
whole-policy-file anchor while keeping the prior fingerprint. The new anchor
inventory no longer matches it, disabling previously reviewed leaf boundaries.
Exact Git record changes and the two policy semantic diffs are retained.

No digest was refreshed and no production authority changed. Historical narrow
plans cannot be presented as current-base savings. A separate reviewed anchor
repair must preserve new/changed consumers and the independent witness.

## Hosted implementation baseline

Remote head `387d18ebac7817b2a7492a60568b4ef194f557e3` completed run
`35497858451` successfully at tested merge
`dc0bc58ef1d8d5fb036d68956c77c4dafe287b47`. Coverage job wall was 27m35s;
Python 3.13 compatibility was 14m43s, with 1424 PASS. Both fixed Python aggregates
passed. This baseline precedes the protocol repair; it is not the later HEAD's
CI result and its timing change is not a controlled performance comparison.
The exact hosted plan executed B1424/C1398 with C minus B empty; all 1424 unique
cases passed. Global coverage was 94.316887%, all 59 critical files met 95/90,
and the three impact modules covered all required lines/branches. The six new
paired-diagnostic cases account for only 2.513 s of the coverage receipt; the
producer's 463.046 s increase over the previous run is recorded largely in
existing modules and cannot be assigned to the new tests or a single cause.
All five original artifact ZIPs match their GitHub API SHA256 and pass CRC checks.

## Scope and remaining merge conditions

The raw ZIP retains original review failures and repairs, focused logs and
coverage, document replay, actual impact/smoke positive and negative evidence,
source bundles, environment/driver bindings, current hosted observations and
fingerprint audit. Hashes are in [validation](checks/validation.json).

[Protocol review](checks/protocol-review.md), [recheck](checks/protocol-recheck.md),
[anchor audit](checks/fingerprint-debt.md), [raw evidence](checks/raw-evidence.zip).

The active goal remains PR92 readiness, under
[the review boundary](../../../../docs/workstreams/chengyue-lu/TEST-PERF-002/CONSUMER_SHADOW_READINESS.md).
Current-head required CI, accepted dependency integration and human cross-owner
review remain separate conditions. Agent audits do not substitute for owner
acceptance. Offline artifact binding does not authenticate external execution.
Production reduction activation, three hosted speed pairs and cross-commit reuse
remain outside this diagnostic PR. No merge occurred.
