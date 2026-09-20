# Final independent 2B diagnostic protocol audit

Owner: Chengyue-Lu. Reviewer: CI integrity reviewer, domain_plan_review. Skills: []. Date: 2026-09-20.
Reviewed HEAD: `387d18ebac7817b2a7492a60568b4ef194f557e3`; clean worktree at initial inspection. Scope: PR #92's new comparator/pair protocol, directly used runner/checkers and relevant tests, CONSUMER_SHADOW/RISK_LEDGER. No source or frozen evidence modifications; no network actions or full suite.

## Disposition

Three reproducible P2 protocol gaps remain. The first two should be repaired before treating this diagnostic slice as ready. The third needs an explicit evidence association/shared-job contract before a required-smoke pair can be called matching. None disproves the archived 325/252, same-driver, zero-smoke, zero-skip local pair; these are future-input validation gaps.

### P2: A nonzero unexplained skip event is accepted as complete execution

Location: `.github/scripts/ci_consumer_shadow.py:201-205`.

The parser validates `events.skips` as a nonnegative integer but never blocks a positive value. A candidate with all per-case rows marked passed and `events.skips=1` still produces `observed-matching-pair`, with no blockers. This contradicts the advertised handling of absent/skipped fixture evidence. Native runner `_write_summary` records `len(result.skipped)` in this field; a positive total with no corresponding row/checkpoint must be treated as inconsistent or incomplete evidence, not silently ignored. This is a malformed-receipt counterexample; no claim is made that the unchanged native runner itself generates contradictory records.

Repair: require zero suite skip events for the current all-success diagnostic contract, or explicitly reconcile every skip against case/checkpoint evidence and preserve inconclusive status. Add both accepted and candidate regressions, including the coverage path.

### P2: Same driver bytes can use materially different invocation arguments

Location: `.github/scripts/ci_shadow_pair.py:120-122` (driver shape validation at 31-35 only records argv).

A candidate invocation with extra `--fixtures cached-success` arguments returns `observed-matching-pair` with no blockers when the source SHA and supplied environment match. Source equality does not establish equal execution options; the same program may change fixture preparation, coverage options, or input paths based on argv. Invocation is retained in the report but never compared. This is an already visible difference, independent of offline authentication or wider input closure.

Repair: declare an explicit allowed role argument position/value mapping and compare every remaining argv element, or mark any unreviewed invocation difference as a confounder/inconclusive. Avoid heuristic replacement of every occurrence of the role string. Add role-only allowed and non-role option/interpreter/path difference regressions.

### P2: Required candidate smoke can be satisfied by an accepted-run smoke label

Location: `.github/scripts/ci_shadow_pair.py:53-59,116-129`.

With `package_smoke=true`, copying the accepted `source=accepted-run-A/package.log` success object unchanged into the candidate bundle yields `observed-matching-pair`. Smoke is associated only with common plan/target and a nonempty string, whereas coverage carries an explicit run and receipt association. The output presents candidate smoke as success even though no candidate-associated artifact is supplied.

Repair: either require smoke run identity and source artifact digest bound to the corresponding observation, or introduce a separately reviewed shared-job evidence contract which explicitly identifies one unchanged smoke execution reused by both roles. Until then, ambiguous copied evidence should remain inconclusive. This request concerns structural association, not cryptographic authentication; an offline producer can still lie and that existing limitation remains disclosed.

## Reproduction

The three counterexamples directly exercise the production `compare_pair` using existing focused test fixtures. No test suite or external process is run. The CLI `build_report` path recomputes the proposal but adds no skip-total, argv-equivalence or smoke-run association checks, so these gaps are not repaired there.

Run from any directory:

```powershell
& 'D:/lcy/develop/_assessments/rwb-ci-schema-parse-20260917/venv311/Scripts/python.exe' -B 'D:/lcy/develop/_assessments/rwb-ci-ready-20260920/review/reproduce_protocol.py' 'D:/lcy/develop/_worktrees/RWB/ci-consumer-shadow'
```

Observed all three cases: `status=observed-matching-pair`, `blockers=[]`. Full mutation summaries are retained in `protocol-counterexamples.json`.

## Current 2B acceptance versus 2C prerequisites

Required for this bounded 2B implementation: internally consistent native outcomes/events/counts/IDs/order; original C and coverage subjects/evidence retained; required coverage/smoke missing/failure kept inconclusive; exact plan/target and producer identities; separate candidate outcome observation; explicit invocation/environment confounders; real lifecycle counterexample; honest local-only report wording. Resolve the gaps above and run corresponding focused regressions. Review the independently supplied inventory as evidence of its stated scope; do not silently promote an observed subset to complete execution.

Not required to merge this diagnostic-only slice: activate exclusions, prove all future consumer inputs, build an authenticated exclusion witness, or produce three fresh hosted pairs. Those remain 2C activation/hosted speed-claim prerequisites. The current C-empty, smoke-free local control does not finish generalized 2B candidate-coverage/smoke experiments; keep that larger experimental work visibly open, without blocking a correctly bounded tool from being reviewed.

No additional material coverage-checker finding was established within this bounded pass. Raw JSON/receipt association remains an offline assertion, as disclosed; it is not a signature, a GitHub attestation, or proof that all possible inputs were observed. Current global/critical/changed thresholds and production planner/worker/Gate authority remain untouched.

## Source identities

- `.github/scripts/ci_shadow_pair.py`: `6e94a6a339b80b92fd659dc209c6df12f0ecbeff1ff7993a0998ca661d285a23`
- `.github/scripts/ci_consumer_shadow.py`: `3112832d8d49d9077589d80651ebeca2e365dfc12651e220a9bd070733208f35`
- `tests/test_ci_shadow_pair.py`: `051039bc01b81192a25c44d1e38003534fc68419bf9ac01c78f2d8c7e5b37cf7`
- `tests/test_ci_consumer_shadow.py`: `84212413b765af4df7e8831916e46caafcfe450dda851a2d85af1020d9428dda`
