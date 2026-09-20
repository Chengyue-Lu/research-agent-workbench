# Git fixture clone configuration

Owner: Chengyue-Lu; TEST-PERF-002; [Issue #87](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87).
Base: `171d4654f88e926f239cdf25bc8168109b81f391`.

## Change

Each `PlannerTests` case creates a real independent Git clone. Its repository-local
identity and line-ending settings now use three `git clone -c` arguments instead
of three separate `git config` processes. The clone still uses `--no-hardlinks`,
and the existing HEAD lookup and per-case temporary-directory cleanup remain.

This ports the small fixture change from local prototype `132dffe9e5c2cf47b0bf1f5531a89c7381ba3f01`
onto the accepted base. Other experiments on that older branch are not included.
The production planner, policies, worker, coverage checker and witness are unchanged.

The new regression checks actual local configuration, the `develop` branch, LF
checkout bytes, the absence of object alternates, separate seed/clone object files,
and a real clone commit that leaves the seed HEAD and README unchanged. It does not
replace Git commands or filesystem behavior with mocks.

## Verification

The 73 existing test-method ASTs are identical to the accepted base; one regression
is added. Both Python versions use the actual worktree test and planner modules,
with their source paths and file hashes recorded before execution. Full checks run
sequentially to avoid adding a second long test load from this experiment.

The current worktree source passes these fresh checks:

| Scope | Python | Result | External process wall |
| --- | --- | --- | ---: |
| New fixture regression | 3.11.16 | 1 PASS, zero skip/error/failure | 1.536 s |
| New fixture regression | 3.13.15 | 1 PASS, zero skip/error/failure | 1.545 s |
| Complete PlannerTests | 3.11.16 | 74 PASS, zero skip/error/failure | 265.890 s |
| Complete PlannerTests | 3.13.15 | 74 PASS, zero skip/error/failure | 269.860 s |

The tested `tests/test_ci_plan.py` SHA-256 is
`64619dc6fd2bbd939dafc480b7541d926dae5bf30b2934a05a533023fd2ee912`.
These checks ran against the worktree source before committing; they are not
authenticated merge-target CI. Raw native receipts, process commands,
inventories, dependency versions and hashes are retained for the enclosing Task
Attempt. Independent source review found no material issue and did not run tests.

## Cost boundary

The implementation removes three Git process launches from each case's fixture
setup. This is a count of changed operations, not a measured hosted speedup. The
new regression also has its own verification cost.

Earlier prototype timing belongs to its original source and environment. This
port does not reuse those measurements as new evidence. Current suite durations
are execution records on a shared machine, not controlled before/after samples.

All existing behavioral assertions, independent fixture state, negative acceptance,
coverage obligations and integration requirements retain their current authority.
