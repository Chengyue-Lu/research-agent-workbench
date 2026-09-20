# Final paired-shadow repair recheck

Profile: CI integrity reviewer; skills=[]; owner Chengyue-Lu. Bounded review of execution-driver provenance repair, invocation context binding, changed-path pilot guard and suite-label adapter. No implementation changes or official-branch/network mutations.

## Disposition

CLOSED: the prior execution-driver identity P2 is resolved. Each bundle now requires a driver SHA256 and concrete nonempty invocation; both are preserved in the output. Different driver hashes add an explicit uncontrolled-code-difference blocker, keeping pair_status inconclusive. Existing accepted receipt bytes need not be rewritten to satisfy this contract. The original tested-target runner pin remains independently checked.

The environment also requires invocation_context_sha256 with strict hash syntax and exact equality between pair members. This records a further supplied boundary; offline metadata remains explicitly unauthenticated and does not establish execution authority.

## Additional bounded checks

- changed_path_patterns is validated when present, cannot be an empty list, and restricts the consumer only when every changed Git path is in the declared pilot scope. A path outside docs/workstreams/** retains the consumer. The original modified-existing-regular-Markdown, executable/mode, empty-diff and pin-drift safeguards remain in force.
- suite_label changes only the expected diagnostic label passed from candidate_observation. Changed candidate runs must still identify shadow-candidate; all actual IDs, aliases, order, failure/events and B-then-C-minus-B contract checks remain active.
- Required coverage absence remains missing/inconclusive. Retained C and passing raw coverage cannot override actual candidate failure.
- The real fixture-phase regression executes both schedules under coverage and observes all source lines/branches covered in each. Moving the second case into the coverage-only phase resets the fixture and makes the actual candidate assertion fail; the pair correctly stays inconclusive.
- Required smoke failures/cancellation/skips, checker policy floors, exact target/plan bindings and input/output alias protections are retained.

## Independent verification

Executed seven focused tests with Python 3.11, bytecode writes disabled:

- all six tests in tests.test_ci_shadow_pair, including real Git CLI/input protection and the real fixture-phase/coverage counterexample;
- ConsumerGitTests.test_real_git_proposal_drift_membership_and_overlapping_consumers, including the workstream scope restriction.

Result: 7 PASS in 8.682 seconds. This is repair verification, not a production CI speed measurement or full repository acceptance.

No remaining material blocker found in this reviewed slice. The disposition does not authorize CI reduction activation or merge; independent exclusion/input closure, authenticated provenance and repeated controlled hosted performance evidence remain separate gates.
Reviewed ci_shadow_pair.py SHA256: 6e94a6a339b80b92fd659dc209c6df12f0ecbeff1ff7993a0998ca661d285a23
Reviewed ci_consumer_shadow.py SHA256: 3112832d8d49d9077589d80651ebeca2e365dfc12651e220a9bd070733208f35
Reviewed test_ci_shadow_pair.py SHA256: 051039bc01b81192a25c44d1e38003534fc68419bf9ac01c78f2d8c7e5b37cf7
