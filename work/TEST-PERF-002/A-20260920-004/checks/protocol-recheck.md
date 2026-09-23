# Independent protocol repair recheck

Date: 2026-09-20. Owner: Chengyue-Lu. Reviewer: CI integrity reviewer / domain_plan_review. Skills: []. Scope: only the three findings in `final-protocol-review.md` and their repair delta. No production source or frozen evidence changes, no network actions, no full test suite. The original report, reproducer and original false-positive results were preserved.

## Disposition

**All three reported P2 findings are closed in the reviewed source bytes. No new material issue found in this repair slice.** This closes the bounded 2B diagnostic code review; it does not activate 2C or establish hosted performance.

## Closure evidence

1. **Unexplained skip events:** `ci_consumer_shadow.compare_receipt` now includes nonzero `events.skips` in the incomplete/unsuccessful suite check. Independently checked accepted and candidate roles with both coverage-none and required-impact plans: all four remain `inconclusive`. Existing case/checkpoint, missing/order and fixture checks are preserved.
2. **Invocation confound:** `ci_shadow_pair.compare_pair` now permits equal argv, or exactly one value changing `accepted` to `candidate` after the unique `--role` argument, at index >=3. Differing lengths, other options/inputs, executable/script values, positional role substitutions, duplicate role options and other role values remain inconclusive. Same-source, role-only intended controls still match. This is explicit syntax-level invocation equivalence; the larger input/producer authenticity boundary is unchanged.
3. **Smoke association:** each supplied smoke now requires `run_id`, `execution_receipt_sha256`, and a well-formed `artifact_sha256`, alongside exact plan/target/status/source. Direct accepted-to-candidate copies are rejected for both package and repository smokes. The focused regression also rejects changing only the run ID while retaining the stale receipt digest, and rejects invalid artifact digests. Missing/failed/cancelled/skipped required smokes remain inconclusive; both valid required smoke results permit matching.

## Verification

Independently ran four existing focused test methods: **4 PASS in 0.010 s**, recorded in `recheck-focused.log`. They include the new invocation/smoke matrix, aggregate skip checks, unsuccessful coverage/lifecycle/smoke handling, and unchanged positive pair controls. Additionally executed six bounded direct protocol probes; results are in `recheck-counterexamples.json`. No full suite or real historical pair was rerun in this review. Root's broader validation results are not attributed to this reviewer.

The first failed/missing-input smoke format is now rejected, which is the intended protocol tightening. Historical frozen artifacts were not rewritten. The archived successful doc pair has empty smoke obligations and uses the accepted unique `--role` invocation form, so these fixes do not contradict that observed result.

## Remaining scope boundaries

Artifact digests and run/receipt association are checked structurally; the offline tool does not authenticate that the supplied source file actually contains those bytes. Independent collector/input closure, exclusion witness, full candidate coverage/smoke experiments beyond the C-empty control, and repeated hosted pairs retain their existing staged requirements. No new execution authority, exclusions, threshold relaxation or result reuse was introduced.

## Reviewed source SHA-256

- `.github/scripts/ci_consumer_shadow.py`: `b5a7dad41d4c0b77b9bce68396eec9f775dea3e28d0ebae9a8d9545b9a9f53a3`
- `.github/scripts/ci_shadow_pair.py`: `c7282a72742deb5734c596fc49b79a185d49808d0d1802adeac480b4b4636aab`
- `tests/test_ci_consumer_shadow.py`: `24dc8b646e5a33f6a8daf12f779464324f8e289de68813e04a37d124782bfbc0`
- `tests/test_ci_shadow_pair.py`: `f9939d83bb34b1d9660d22c3ffa9f1437bbd495df62758d3efa73f297ec23f4e`
