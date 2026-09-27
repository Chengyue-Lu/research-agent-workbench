# Coverage-policy parsing cost

Repeated planner verification reads the base and candidate coverage policies and
parses them again, even when their bytes match earlier requests in the same
process. Profiling two existing adversarial tests found 48 and 52 in-planner
parses. The original verification calls and their assertions remain necessary.

The planner now reuses successful parsing of exact bytes in an eight-entry,
process-local cache. Every caller receives a deep copy. Base/head Git reads,
including their existing read cache, and all identity, policy, selection and
minimum-plan verification remain unchanged. No validation outcome is cached.

## Parser and mutation boundary

The implementation keeps `yaml.safe_load`. It records the parser functions,
SafeLoader class and constructor/resolver configuration at normal CI module
import. Each lookup observes that configuration again. A replacement or in-place
registry change bypasses the cache and invokes the current parser on every call;
restoring the initial configuration permits its original cached values again.
The snapshot also copies implicit-resolver rule lists, so in-place edits are
visible. This supports the controlled CI process with stock PyYAML initialization;
arbitrary preinstalled loader extensions, class-method mutation or concurrent
plugin reconfiguration are outside that contract.

Non-exact-bytes inputs retain the original parser path. Failed parsing is not
cached. Returned objects cannot modify a cached policy or another caller's copy;
YAML aliases and cycles remain intact within each document. Capacity eight limits
entries, not retained bytes. Entries are released on eviction, clearing or process
exit. There is no cache persisted between CI executions.

Four lightweight test methods cover value isolation and aliases, errors and
non-bytes inputs, configuration changes/restoration, and capacity/clearing. They
do not use the planner's Git fixture. All original planner tests and the original
catalog forgery cases remain.

## Bounded observations

The comparison used the verified but unmerged PR103 candidate `725647f` and the
parser candidate SHA-256
`20ae01b14d33a4a37fb20961c95be339c3bfef2295af24be3ecdadf211fd63db`.
Accepted develop was `97d3b3d`. Complete clones retained original tests, fixture
setup, Git operations and cleanup. Each arm ran in a fresh Python 3.11.16 process
with PyYAML 6.0.3. The two original tests retain eight proof-source and 23 catalog
forgery subtests; repeated observations are not additional unique cases.

| Original test | Unprofiled median, three pairs | One separate branch-coverage pair |
| --- | --- | --- |
| Planner proof-source pinning | 19.114 → 17.951 seconds (6.08% lower) | 22.545 → 18.986 seconds |
| Re-signed catalog forgeries | 10.708 → 9.566 seconds (10.67% lower) | 21.136 → 16.989 seconds |

Pairs alternate execution order. Suite timing includes original setup, assertions
and cleanup; whole-process timings separately retain startup and data saving.
The branch pair uses coverage.py 7.16.1 and the identical saved CI source/omit
configuration. Report export runs outside both timers. All 16 measured processes and
their original subtests passed. Machine activity was not exclusively controlled,
and the branch mode has only one pair. These observations support this small
implementation candidate; they do not estimate whole-CI savings or certify the
coverage gate.

The first branch wrapper failed before tests because the coverage data directory
conflicted with an exclusive output-directory check. Its failure was retained;
only the four unexecuted arms resumed with a separate data path. A later Windows
path-separator aggregation correction reused the original data without rerunning
tests. Earlier parser candidates and the rejected diagnostic-demand prototype
keep their own identities and results.

This cost change preserves test selection, all quality thresholds, independent
authority verification and fresh integration requirements. Business selection
reduction remains subject to the [execution-input work](EXECUTION_INPUTS.md).
