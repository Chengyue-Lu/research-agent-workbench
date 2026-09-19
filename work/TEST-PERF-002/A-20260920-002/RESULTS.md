# Consumer shadow 2B: first diagnostic slice

TEST-PERF-002 / Issue #87; owner Chengyue-Lu; R2; 2026-09-20.
Develop base: `171d4654f88e926f239cdf25bc8168109b81f391`. Stacked dependency: PR #91 `09c6cb1c82680233c369014e0831874b6702d3b7`.
Implementation: `435dfb69646737904660183c13f74a98c0b6782a`.

The offline comparator derives explicit proposed behavioral exclusions and joins
canonical IDs with actual receipt outcomes. Coverage C, its thresholds/subjects/
coordinates/positive-negative evidence, and smoke obligations stay intact. Reports
separate B exclusions, effective execution exclusions, and changes of fixture phase.
Unknown C yields unknown effective membership and no cost claim.

## Validation

- Python 3.11: 45 focused tests PASS, 35.476 s; Python 3.13: 18 PASS, 9.525 s.
- New comparator: 197/197 statements, 78/78 branches; no new exclusions.
- Three real Markdown failures retained: bad link (one parent), missing public
  navigation (one public-surface parent while documentation passes), internal public
  navigation (six parents). One unrelated control: 25/25 PASS.
- Each native observation executes 25 unchanged documentation/public-surface/kernel
  cases with pre-execution inventory. This is an observed subset, not full CI.
- Two in-memory Kernel cases are the only proposed unrelated exclusions. Other
  unknown consumers stay selected. Historical PR #90 B=1425/C=1399 proposes no skip.
- Independent review's three initial P2 findings and one follow-up P2 were repaired
  and rechecked: receipt/checkpoint contradictions, wildcard canonical IDs, empty
  Git deltas, and unknown-coverage effective omission overclaim.
- Trace has no BLOCK. Capture-gap warnings remain explicit for incomplete original
  tool/message streaming and final publication after archival seal.

[Structured validation and raw hashes](checks/validation.json),
[probe and historical summary](checks/replay-summary.json),
[consumer audit](checks/docs-input-audit.md),
[independent recheck](checks/comparator-code-recheck.md),
[raw evidence ZIP](checks/raw-evidence.zip).
The ZIP retains native receipts/inventories, raw first-pass probe evidence, frozen
experiment producers, incremental Git bundle and local logs. Its scripts are audit
artifacts; they are not additional maintained executable coverage subjects.

## Limits and next step

This first 2B slice does not complete independent candidate coverage/smoke execution,
the full consumer/environment closure, a trusted exclusion witness, or paired hosted
speed measurements. No reduction is activated, no merge performed, and no 37-minute
coverage improvement is claimed. Continue with complete accepted-plan observations
and candidate coverage/lifecycle comparisons before requesting 2C. Business/evidence
fixes in PR #90 remain with its owner.
