# Consumer records and M5 intake evidence

TEST-PERF-002; owner Chengyue-Lu; R2; A-20260916-009.
Implementation commit: `44abc86acb638b22a6740ee178ab72d730838bc0`; base: `0d4a1d00a4c32ca9b822df6482a95920e7c21b1b`.
User authorized continued CI replanning and testing M5-007 after its separate development/test turn closed.

- Local CI suites: 215 PASS / 325.941 s; declared business proofs: 11 PASS /
  9.680 s. These are 226 distinct local tests, not a full-suite claim.
- Five changed CI modules meet critical 95/90 with zero exclusions. New consumer records: 84/84
  statements and 36/36 branches; shadow: 125/125 and 36/36; selector: 503/503 and 322/322;
  input facts: 80/80 and 46/46; planner: 542/543 and 204/206. Missing planner paths are unchanged
  CLI entry/error paths; the required changed coordinates are independently checked by hosted impact CI.
- Thirteen exact historical before/after plans are byte-identical. Producer before: `45fcd894f6a1eac43663e22fed1a23e5983e5c74`.
  Original Git/metadata bindings are retained. Before plan bytes reuse the same retained after copies;
  original metadata for #65 through #84 remains in A-20260916-008, while #86 metadata is added here.
- Implementation head-target preflight and governance PASS. Full behavioral plus impact/repository
  coverage remain required. This evidence commit and hosted merge target need separate final checks.

## M5-007 H1/H2 intake

The other task completed its development turn and PR #86 passed full CI at
`b53a391ece3a4be7207c00c636dc9e1570e71473`. Hosted run 35107663587 used target
`8e7857369894e934ad6c5277f2a3ea2c68201bb8`; replay target=head. Execution fields and all
original selection fields match; plan IDs remain distinct for those different targets.
This is H1/H2 engineering test closure, not whole M5-007 completion or human acceptance.
The branch was only fetched as immutable Git objects and was not rewritten.

Its accepted plan selects 93/94 modules; all 29 behavioral FULL reasons are archive classification.
Raw graph category diagnostics select archive 93/94, business Python 91/94, test Python 91/94,
schemas 93/94 and ordinary documents 48/94. Raw probes do not apply all planner filters and cannot
serve as execution plans. Real schema/catalog/install obligations remain independently necessary.
Current reference records detect changed validation/documents.py and test_schemas.py pins.

## Boundaries and retained failures

Four records pin nine explicitly declared files and eleven positive/negative test IDs. Matching
those pins is not complete input closure, evidence execution or safe-exclusion authority. Candidate
rewrites are checked against base records; all execution_authority flags remain false. No active
selection, threshold, exclusion, behavioral test or release gate is weakened.

The initial 215-test run exposed non-object policy handling, an obsolete unknown-version fixture,
and a new fixture lacking required policy-check test files. The object guard, unsupported version 3
case and complete isolated Git fixture repair were followed by the successful rerun above. The raw
initial failed log is retained. A good reader actually passes and an intentionally incorrect reader
actually fails in isolated child processes; candidate pin refresh and worktree byte restoration
cannot replace the original base declaration.

Prior full PR85 CI at `45fcd89` is retained as prior-head evidence, not this implementation's result.
No paired hosted performance gain or activated reduction is claimed. Trace declares a retrospective
capture gap for unstreamed exchanges and does not claim complete runtime capture.

See [design](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/CONSUMER_CONTRACTS_V1.md),
[comparison](checks/corpus-comparison.json), [M5 intake](checks/m5-intake.json),
[hosted M5 binding](checks/m5-hosted-comparison.json), [module coverage](checks/coverage.json),
[preflight](checks/implementation/preflight-summary.json), [manifest](checks/evidence-manifest.json),
[identical plan reuse](checks/identical-plan-reuse.json) and [Trace](checks/trace-validation.json).
