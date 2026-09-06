# Independent CI obligations

Owner: Chengyue-Lu; cross-owner: let778750-cpu; Audit ID: TEST-PERF-002; risk: R2.
Accepted base: `97f760c43e95b398c396987f349e2199c567cbc7` (PR #65).

Plan v2 retains exact Git diff and event binding, the base-side impact policy and dependency closure,
consumer fingerprints, additive Agent requests, metadata isolation, obsolete-head cancellation and the
fixed `test (3.11)` / `test (3.13)` gates. It adds four independently checked obligations and reasons:

```yaml
risk: R2
behavioral_scope: full
coverage_scope: none
package_smoke: false
repository_smoke: false
```

`risk` determines governance and review strength. R2 still requires full Python 3.11 and 3.13 behavior.
`change_class` remains a diagnostic FAST/FOCUSED/FULL alias for behavior. Workers and gates use the
individual scopes, and artifacts with contradictory aliases or obligations below the machine minimum fail.

| Surface / boundary | Behavior | Coverage | Package / repository smoke |
|---|---|---|---|
| Allowlisted documentation with R0/R1 | none (documentation lane remains) | none | only if independently requested |
| R2 test code, test fixtures, work archive, reviewed fingerprint refresh | full | none | false / false |
| Accepted bounded Provider closure | focused, or full at R2 | impact | accepted downstream group flags |
| Bounded planner, CI evidence checker or governance validator | full | impact | false / false |
| Schema data | full | none | true / true |
| Registry or example data | full | none | false / true |
| Descriptive package metadata (version, description, authors, etc.) | full | none | true / false |
| Runtime/test dependencies, interpreter, entrypoints or build configuration | full | repository | true / false |
| Coverage policy semantics, coverage checker, coverage runner/workflow authority | full | repository | independently affected surfaces |
| Unknown/high-fanout executable, new imports, incomplete closure, stale base | full | repository | fail-safe true / true |
| develop/main push, release boundary, explicit complete-evidence recovery | full | repository | true / true |

The bounded CI validators must already appear in the base critical inventory with positive and negative
acceptance mappings. Their selected test modules come from those immutable mappings. Newly introduced
executables, dependency changes, source mode changes, deletion-only hunks and unmappable lines retain
complete fail-safe evidence. Coverage policy semantics include source roots, thresholds, critical inventory,
suite selection, exclusions and negative acceptance. Formatting alone in the YAML policy does not change
those facts. In `pyproject.toml`, only descriptive package metadata is exempted; dependency, interpreter,
entrypoint, build and coverage configuration changes still require repository evidence.

Impact evidence has its own `coverage_tests` selection and `--suite impact` execution lane, so full behavior
can coexist with impact coverage. Changed executable statement spans and their outgoing branches require
100/100; each impacted critical module retains whole-file 95/90 and its own positive/negative PASS evidence.
The report sets `repository_coverage_proved: false`. Repository coverage retains global 90% and critical
95/90, the original measurement roots, exclusions and negative acceptance. No behavioral tests are removed.
The workflow supplies both measurement roots as filesystem paths so validator-only impact runs still include
unimported package files and reconcile the complete declared exclusion inventory.

Each fixed aggregate recomputes the machine minimum against the event and exact Git target. Coverage may
skip only when the verified plan says `none`; required impact/repository coverage cannot be missing, skipped,
cancelled or failed. Metadata continuity compares behavior, coverage and both smokes independently. A prior
full-behavior result with no coverage cannot cover a new impact/repository requirement. Version-1 bundled
artifacts cannot satisfy the version-2 obligation contract.

## Acceptance evidence

[The PR #65 fixture](../../../../tests/fixtures/ci/pr65.json) contains its exact 20 Git change records,
base/head text blobs and SHA-256 hashes. The test constructs real Git commits from these records and checks
the resulting exact diff before requiring R2/full behavior, coverage none and both smokes false. It is pinned
to base `690a9f8` and head `09f9619`, so acceptance does not depend on retaining an old remote PR branch.

Additional adversarial tests cover bounded critical impact with 95/90 and distinct passing positive/negative
tests, coverage-authority mutations, unknown executable fallback, candidate fingerprint/group changes,
metadata and artifact scope reductions, and the required-job missing/skip/cancel/failure matrix.

PR #65's successful pre-merge CI and its post-merge integration run are separate evidence. Integration pushes
continue to re-prove repository coverage deterministically; selective PR evidence makes no global claim.
Validation results for this revision are recorded in [VALIDATION.md](VALIDATION.md).
