# Runner preflight

Owner: Chengyue-Lu. Task: TEST-PERF-002. Risk: R2.

The independent branch is based on accepted develop
`171d4654f88e926f239cdf25bc8168109b81f391`. Initial local validation used pending
PR #92 snapshot `4119f8b2d8e1e64a0afead138d13061e2d89e996`; the runner, existing
runner/planner tests, policies, planner and witness inputs are byte-identical
between those bases. Only this repair was moved onto develop. Exact-target
CI and review remain required before merge.

The ordered coverage producer previously rejected an unsupported Python version
only after running the complete suite and writing a raw receipt. Full behavioral
discovery also allowed loader failures or an empty suite to reach execution, and
the repository coverage loader did not propagate its own loader errors to the
outer coverage union.

Loader failures now retain the failing module and original exception traceback;
empty collections explicitly report that no tests were collected.

The runner now rejects unsupported coverage producers before loading behavior,
and rejects missing or empty groups at their original full/repository collection
boundaries. Ordinary Python 3.11 and 3.13 full/focused suites remain supported;
the ordered coverage producer retains its existing Python 3.11 restriction.
An explicitly unrequired behavioral suite remains empty and valid.

Behavior finishes with its original suite tree, order and fixture teardown before
coverage-only modules are loaded. The existing receipt projection and coverage
checks remain responsible for actual execution outcomes, exact identities,
positive/negative evidence, and line/branch thresholds.

## Validation

Dedicated temporary-module regressions verify early rejection before sentinel
fixtures, valid empty behavior, deferred C import, real loader errors and empty
module suites, preserved module/class lifecycle, and ordinary full/focused/impact
execution. Existing exact-Git worker tests retain their Python 3.11 execution and
failure assertions; Python 3.13 now asserts producer rejection without a raw
receipt or sentinel execution, while its ordinary behavioral worker still runs.

Python 3.11 and 3.13 each passed the complete 96-case runner/planner combination.
After adding detailed loader errors and strengthening the same six regressions,
both versions passed all 23 runner cases again. Three isolated guard-removal
controls were each rejected by the regressions. The original 96-case source
hashes and final 23-case source hashes are separately retained with their logs.
Independent source review found no blocking issue. These local checks do not
establish repository coverage, hosted CI success or release authority.

This change reduces time spent on inputs already known to be invalid. It does
not claim a speedup for valid passing suites. A planned auxiliary script outside
package discovery still needs runtime measurement evidence; package layout alone
cannot establish failure or authorize skipping its impact obligation.
