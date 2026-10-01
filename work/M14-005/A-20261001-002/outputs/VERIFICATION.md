# Verification and limits

Base: `331809fc7d8fc0a72bb9bc72f59363495e2917c8`.

- Python 3.11.16: 121/121 governance, helper branches, release governance/install
  and checkpoint tests PASS. New real-Git candidate/API fixtures read Task/workstream
  from source and cover ref/repository/Task/authority/dormant/metadata drift rejection.
- Python 3.13.15: 105/105 governance/install tests PASS in a fresh dependency environment.
- Release surface/preflight/governance helper regression: 56/56 PASS. Initial combined
  71-test run failed only its old component-map expectation after adding the new
  real consumer. That expectation was updated; final component map 15/15 PASS.
- Documentation links: final 10/10 PASS. Public/install/documentation/coverage-policy
  group previously passed 53/53; those coverage-policy tests use controlled fixture
  percentages, not a global repository coverage measurement.
- Repository validation: `validated=186 errors=0 warnings=0`.
- Scoped actual coverage: PR governance 677/689 lines (98.258345%) and 302/308 branches
  (98.051948%); release_governance 35/35 lines, 4/4 branches; release_install 53/53
  lines, 6/6 branches. No global/full-suite acceptance is claimed in this slice.
- All five prior policy objects exactly equal origin/develop; 1.5.0 adds only the
  source-owned release governance helper. Diff check PASS; old A-20261001-001 unchanged.

The first 110-test run had a test-assumption failure: declared R0 is automatically
raised to effective R2 by accepted governance. The corrected tests require R2
obligations after escalation and reject missing authority evidence; production risk
semantics were not changed to satisfy the test. Final 3.11/3.13 results above passed.

Source/candidate API fixtures are controlled tests, not actual new-source hosted
observations. The accepted 331809f source CI and ef29d7e hosted run remain historical
cutover readiness input (see CUTOVER.md); this feature has not been merged. Required
PR CI and independent R2 review must precede integration. New actual protected
source CI, candidate/pin regeneration, dual-Python hosted checks and a fresh full
ruleset/readiness audit must precede any remotely authorized one-update cutover.
No remote ruleset, main merge, tag, release publishing or Task DONE was performed.

The visible tool/external-action stream was not captured exhaustively; omissions
are explicit capture gaps, not fabricated telemetry.
