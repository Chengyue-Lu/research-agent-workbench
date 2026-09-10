# M14 integration on accepted Issue #48 CI

Owner: Chengyue-Lu; R2; H0; no delegation or Skill binding.

The user requested current-develop rebase and adaptation to the accepted CI rules.
Base `3a27f9a052dcb79bd29e56138f9e219385dd1f5f` includes PR #67, following #63/#65/#66.
The clean PR branch at `205559b25f7f0bd276094a4ac53db28354b7284d` was backed up and its 13 commits
rebased without conflicts to `347f264c1624654f909b91542a96724b98c9cad4`. Earlier M14 archives retain
their exact bytes. Implementation: `85ec2d908cd9f543bc6309b591c1aa19ddc18e16`.

The previous hosted run 34131110394 passed behavioral suites but failed impact coverage.
The accepted collector now measures build-backend aliases and the frozen oracle by path.
This repair adds registry/profile/actor negative contracts, distribution orchestration
tests, and an isolated replay of the immutable M14-002 oracle. Resource ancestor loops
are bounded explicitly; already-established path, Task mapping and actor kind checks
are reused. Coverage floors, exclusions and release authority remain unchanged.

The initial 97-case exploratory run found a test-fixture setup error (a directory matched
the schema glob and duplicated a conditional entry). The corrected build tests passed
7/7; the fresh committed focused run at `05906daadd0180a55784a3e4ae161a6e5154054b` passed 257
tests on Python 3.11.16. Coverage inspection then showed that the
mixed-closure fixture needed an explicit scalar to exercise its non-mapping skip.
The fixture was corrected and rechecked (1/1 PASS; line 48 and branch 47 to 48 executed).
That final test-only repair preserves all product bytes from the focused run.
CI/coverage/documentation contracts passed 52/52, repository
validation passed 183/0/0, and R2 governance passed. Both Python versions installed the
direct wheel and sdist-rebuilt wheel outside checkout: all 8 isolated/poisoned probes
passed with identical Runtime resource bytes. See checks/verification.json.

The plan requires FULL, impact plus repository coverage, and package/repository smoke.
Focused coverage is a diagnostic preview, not a successful coverage-plan receipt.
Final-head hosted full/coverage/aggregate checks and fixed-root selection witness remain
independent obligations. The archive is safe-paused for publication and cross-owner
review. PR #60 retains subsequent exact-head GitHub receipts. Capture gaps are explicit.

M14-004 remains PARKED and M14-005 BLOCKED; release/v* to main remains dormant.
No release branch, tag, merge or publication is authorized by these checks.
