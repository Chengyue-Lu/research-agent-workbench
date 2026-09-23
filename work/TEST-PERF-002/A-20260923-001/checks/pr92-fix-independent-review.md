# PR #92 role-binding fix: independent bounded review

Conclusion: no actionable finding in the reviewed minimal fix. This is a code/test review of the listed working-tree bytes, not a GitHub owner approval, current-head hosted CI result, merge authorization, or production-reduction activation.

## Scope and identity

Reviewed the three-file working-tree diff for review 5287223195, repository AGENTS/README, complete pair comparator and pair tests, CONSUMER_SHADOW protocol, and the retained before-fix reproduction. Source hashes are recorded in `pr92-fix-independent-sourcehash.json` and were checked unchanged after review/testing. The before-fix reproduction preserved a changed behavioral order with identical accepted-role commands incorrectly obtaining `observed-matching-pair`.

## Assessment

- The new condition compares both complete `behavioral_order` and `coverage_order` against inventory. Any changed selection or ordering now requires `role_only`; unchanged execution union alone cannot avoid this guard.
- `role_only` already requires equal argv lengths, exactly one differing value, a preceding unique `--role`, and the ordered value pair `accepted` / `candidate`. Since all other arguments are equal, the candidate cannot add a second literal role, different option/value, driver name, or reorder arguments through this allowance. Identical commands, missing roles, identical wrong roles and duplicate roles cannot satisfy the changed-order guard.
- Complete B/C orders unchanged may still use identical native commands. They remain subject to distinct execution identity/receipt, environment, driver hash, receipt order/outcome, coverage and smoke checks.
- The implementation only adds a blocker. Driver/argv mismatch checks and the downstream incomplete execution, required coverage and required smoke blockers remain intact. The existing actual fixture-phase regression and negative cases remain in the file; none were deleted. The deleted same-command matching assertion was precisely the invalid changed-order expectation; a separate unchanged-orders control replaces it.
- Protocol text now matches this distinction. `execution_authority=false`, `activation.eligible=false`, and `savings_proved=false` are retained unconditionally. There is no 2C/workflow activation or threshold change.

## Independent verification

Python 3.11 targeted unittest execution: 3 methods PASS in 0.009 seconds (see `pr92-fix-independent-tests.log`):

1. `test_changed_behavioral_or_coverage_order_requires_distinct_driver_roles` — changed selection, behavioral order, and coverage-only order (same union); accepts the valid role pair and rejects identical accepted/candidate/missing/other/duplicate-role invocations.
2. `test_identical_complete_orders_allow_same_native_invocation` — unchanged complete B/C native-command control with/without coverage.
3. `test_role_only_invocations_and_smoke_membership_cannot_hide_other_execution` — other argv/role mutations and copied or invalid smoke membership.

No full suite, repository coverage, hosted run, or lifecycle subprocess was independently rerun in this review. Source inspection confirms those existing protection paths are preserved; broader implementation validation belongs to the implementation report/current CI. New source changes after these hashes require revalidation before applying this conclusion.
