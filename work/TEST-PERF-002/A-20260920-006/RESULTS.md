# CI fixture setup evidence

Implementation `94b7fbd447fe05091653f8f9820ea8105fd63979`; accepted base `171d4654f88e926f239cdf25bc8168109b81f391`.

The raw acquisition report describes its original pre-commit state; source hashes bind it to this implementation. Hosted CI and human acceptance are separate.

Initial post-seal Trace validation required generating the new worktree runtime resources. The sealed raw archive and Trace files were preserved; validation then completed without BLOCK. Capture-gap warnings remain.

# Fixture clone cost handoff

Base `171d4654f88e926f239cdf25bc8168109b81f391`, branch `perf/ci-fixture-clone-config`; source remains uncommitted.

Only `tests/test_ci_plan.py` and `FIXTURE_CLONE_COST.md` changed. Three per-case configuration subprocesses move into the real clone command. `--no-hardlinks`, identity, branch, LF, original fixtures/assertions and cleanup are retained.

73 prior test-method ASTs unchanged; new actual config/object/seed-isolation regression passes both Python versions. Source SHA-256 `64619dc6fd2bbd939dafc480b7541d926dae5bf30b2934a05a533023fd2ee912`.

| Run | Result | Process wall |
| --- | --- | ---: |
| 311-fixture / Python 3.11.16 | 1 PASS, no skips/errors/failures | 1.536 s |
| 313-fixture / Python 3.13.15 | 1 PASS, no skips/errors/failures | 1.545 s |
| 311-full / Python 3.11.16 | 74 PASS, no skips/errors/failures | 265.890 s |
| 313-full / Python 3.13.15 | 74 PASS, no skips/errors/failures | 269.860 s |

Independent source review: no material issue; no tests run by reviewer. No controlled performance comparison was performed while other tasks were active. The historical prototype measurements are not reused as current results.

Raw commands, source snapshots, environment/dependency metadata, inventories, native receipts, logs, review, patch and manifest are retained here. No policy, production code, old branch or frozen evidence was modified; no commit, push or PR operation occurred. Final commit/merge-target CI and named-owner acceptance remain with the root task.
