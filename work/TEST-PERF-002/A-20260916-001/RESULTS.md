# PR #83 review remediation

TEST-PERF-002 revision 29; owner Chengyue-Lu; R2; native agent; no delegation.

## Scope and source

Review input: task-owner review of `288489429b412ead2f0f8df34c43655c25089900`.
Implementation: `74bf82361bb8b787e8f09350ae80a9e8bd1d2e21`.
Source-check head: `585c63b1b9b76e89e15a76bc67c9106eb5d45068`.
Base: `7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba`.

Known patch and setattr helper calls now invalidate literal-length metadata when the
builtin target is possible or uncertain. Selector regressions preserve ordinary and
unrelated-target precision. The count is named dependency_selected_test_modules to
separate dependency selection from final policy-expanded plan tests.

## Verification

- Before fix: new mutation matrix failed in 9 subcases. This is intentional reproduction.
- After fix: 47 dependency cases PASS, including real Git-bound document failures for
  patch and patch.object. Ten documentation checks PASS.
- 106 planner/checker/witness cases PASS under coverage in 305.871 seconds. BLOCK
  records inside this test log are expected negative witness fixtures, not final gate failures.
- Analyzer: 448/448 statements, 290/290 branches. Planner: 538/539 statements,
  204/206 branches. Both critical floors pass; changed lines/branches have no gaps.
- Actual PR-event governance and recomputed local exact-head plan verification PASS.
  Required behavior remains full. These local checks do not replace hosted full execution.
- The first dependency run used an invalid coverage source argument: its 46 tests passed,
  but no coverage was collected. dependencies.log retains that warning; corrected final
  collection is dependencies-coverage.log and critical-coverage.json.

## Capture and handoff

Capture manifest binds original and archived bytes; log normalization changes CRLF to LF
only. Native complete message/tool export is unavailable and capture gaps remain explicit.
This archive is frozen before push; the enclosing archive commit and hosted merge-target
checks are reported in PR #83, avoiding another evidence-only CI restart.

The user requests moving the repaired bounded PR out of Draft. Merge/release are not
performed. Wider graph precision work remains Issue #48 follow-up scope. Local develop
and other development branches remain unchanged.
