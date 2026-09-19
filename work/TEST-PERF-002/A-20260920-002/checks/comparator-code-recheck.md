# Comparator code recheck

Profile: CI correctness/trust reviewer; skills=[]; owner Chengyue-Lu. Scope limited to repairs in ci_consumer_shadow.py and tests/test_ci_consumer_shadow.py, including observed-subset coverage handling. Read-only source review plus a small direct comparator probe; no source edits or business/full test execution.

## Original findings

- CLOSED: wildcard canonical paths are rejected in identities() at lines 35-37. Direct probes of * and ? both raise ValueError.
- CLOSED: empty Git deltas explicitly retain the existing behavioral inventory through an outside-pilot fallback at lines 115-116. The regression includes different commits with the same tree at test lines 175-180, not only integration base==head.
- CLOSED: failing cases/checkpoints now always add a blocker at lines 220-222, while skipped checkpoints contribute to inconclusive IDs at line 224. Tests cover retained failed checkpoints and skipped checkpoints as well as excluded failures. These changes prevent the prior contradictory supplied envelopes from reaching an unqualified no-missed result.

The B/C union and phase-move accounting remains intact, and source/helper changes still disable the pilot. Coverage/smoke requirements remain the accepted plan's values; activation is always false. The new effective_execution_skips=null and cost=null for observed-subset plus required unknown coverage are directionally correct.

## Remaining P2: unknown C still produces a definite effective missed-failure claim

Location: ci_consumer_shadow.py:211-236, particularly rows at 216 and missed/status at 223-234.

The unknown-C restriction is applied to the top-level effective_execution_skips and cost estimate, but not the case outcome comparison. When scope is observed-subset and coverage is required, an omitted entry from the supplied C does not prove it is absent from the required complete C. Nonetheless an observed failed case omitted from candidate B and missing from that partial C is labeled candidate_execution=skip and yields status=missed-failure / missed_failure_ids=[id]. The complete C may actually retain that case in the later phase.

A direct probe used a correctly failed, bound observed-subset receipt (successful=false, events.failures=1), repository coverage obligation, one behavioral case, supplied coverage_order=[], and empty supplied candidate execution order. Current output:

    status: missed-failure
    missed_failure_ids: [tests/test_a.py::C.test_x]
    excluded_case_seconds_estimate: null
    rows[0].candidate_execution: skip

This is a diagnostic overclaim, not an execution-authority bypass. Keep the observed behavioral exclusion of a failing consumer as a separate useful counterexample. Mark its effective execution membership/omission unknown until complete C is available; the effective missed-failure conclusion must remain inconclusive rather than definitely missed. Cases known to remain in candidate B or known C may still be marked selected. Add a failed observed-subset regression with required but empty/incomplete C; the existing observed-subset tests retain a complete C and do not cover this ambiguity.

## Disposition

Three original P2 findings are closed. One bounded diagnostic-completeness issue remains before final closure of this code review. No activation or merge authorization is supplied by this recheck.

## Final closure after unknown-C repair

CLOSED. Current compare_receipt computes coverage_unknown before joining outcomes, labels omitted cases as candidate_execution=unknown when required C is incomplete, and preserves those observed failures in failure_exclusion_unknown_ids. It no longer emits a definite missed-failure conclusion from that incomplete inventory; status is inconclusive and the cost estimate remains null. The added regression explicitly checks these fields for an observed-subset failed case with empty C.

Independently reran the original one-case reproduction against current source with a valid failed observed-subset receipt. Assertions passed for status=inconclusive, missed_failure_ids=[], failure_exclusion_unknown_ids=[case], candidate_execution=unknown and null excluded-case cost. No source edits or suite reruns were performed.

Final bounded disposition: all original findings and the unknown-C residual are closed. No remaining material blocker identified within this reviewed slice. This is a diagnostic code-review disposition, not activation, merge, coverage-quality or performance acceptance.
Reviewed ci_consumer_shadow.py SHA256: b07f0b63799f1c260ad6877279e059b455330f48ae3a13030d234ed6d517c9d6
Reviewed test_ci_consumer_shadow.py SHA256: 32bf1fcc82a69b80011cee89992bd4cd9be98db911df705829c4f0fe980f6df5
