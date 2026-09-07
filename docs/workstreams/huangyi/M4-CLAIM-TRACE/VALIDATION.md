# M4-003 Verification

## Owner-review corrections (2026-09-07)

The two P1 findings in Chengyue Lu's review of `24250cc` are addressed without
changing the input Schema or original Task acceptance. The map now enforces
exact Evidence/source identity sets and validates every declared binding once.
The promotion consumer checks canonical receipt identity, exact work workspace,
record/source membership and allowed target zones using M4-002 path semantics.
Successful and failed provenance lookups share one captured read set.

On the candidate incorporating accepted develop `690a9f8`, Windows CPython
3.11.9 ran `python -m unittest tests.test_claim_trace -v`: **15 tests PASS**
in 122.527 seconds. One existing real producer is reused for all promotion
mutations; the new closure test and those mutations exercise generic validation
with subprocess creation blocked. The original shared-source open-count test
still passes. No local full, global coverage, installation or model suite was
rerun. Earlier coverage and installation figures below belong to `24250cc`.

Independent re-review reused the five preserved inputs from the owner-review
reproduction, without running a producer. The normal control passes; unused
Evidence, an unused binding with missing provenance, a relocated byte-identical
receipt and a record outside its workspace all fail both localization and
generic validation. Each declared binding is checked exactly once, with no
duplicate file opens; the promoted control captures eight files in eight opens.
The local review inputs/results remain in the ignored
`work/REVIEW-PR61/A-20260906-001/` and `A-20260906-002/` archives.

The develop integration preserves PR63's CI planner and all critical/negative
coverage entries from both branches. This R2 candidate uses the accepted FULL
hosted checks. Final hosted results and renewed named-owner acceptance are
required before merge; local re-review does not replace them.

## Historical evidence at 24250cc

The targeted tests exercise actual pinned files, the existing CLI and a real
M4-002 producer. Independent review found and closed duplicate disk reads and
an inaccurate counterevidence fixture locator. Only those changes and new
contract checks triggered focused reruns; PR #60's full/coverage suites were
not repeated during the parallel review.

Local focused evidence: 14 tests PASS, including a real promotion consumer,
retained negative outcome, CLI/generic validation, identity/file drift and
actual open-count checks. The focused branch measurement gives the new
claim_trace.py line 99.32% and branch 98.39%, with no exclusions. Schema and
existing CLI compatibility checks passed during integration. The final
documentation/Schema/CLI selection passed 17 tests; a clean wheel installation
outside the checkout imports the installed package and lists the new Schema.

Full Python 3.11/3.13, global Coverage Policy v2, package and governance must
pass on the final hosted candidate. Local full/coverage suites are not
duplicated solely to repeat those CI jobs. The new module and actual
positive/negative tests are registered in the unchanged 90/95/90 policy.

TASKS DONE is this implementation PR's proposal until the named owner accepts
and merges it. Neither these tests nor the CI establish scientific correctness.
