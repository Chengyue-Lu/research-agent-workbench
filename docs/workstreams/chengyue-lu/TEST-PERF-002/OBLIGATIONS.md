# Independent CI obligations

Owner: Chengyue-Lu; cross-owner: let778750-cpu; Audit ID: TEST-PERF-002; risk: R2.
Accepted base: `97f760c43e95b398c396987f349e2199c567cbc7` (PR #65).

Plan v3 retains exact Git diff and event binding, the base-side impact policy and dependency closure,
consumer fingerprints, additive Agent requests, metadata isolation, obsolete-head cancellation and the
fixed `test (3.11)` / `test (3.13)` gates. It adds four independently checked obligations and reasons:

```yaml
risk: R2
behavioral_scope: full
coverage_scope: none
coverage_obligations: []
package_smoke: false
repository_smoke: false
```

`risk` determines governance and review strength. R2 still requires full Python 3.11 and 3.13 behavior.
`change_class` remains a diagnostic FAST/FOCUSED/FULL alias for behavior. Workers and gates use the
individual obligations, and artifacts with contradictory aliases or obligations below the machine minimum fail.
Coverage is a canonical set: `[]`, `[impact]`, `[repository]`, or `[impact, repository]`. Its diagnostic
`coverage_scope` alias is respectively `none`, `impact`, `repository`, or `impact+repository`.
Repository 90/95/90 and impact 100/100 are independent proofs. Set inclusion governs evidence reuse;
a repository-only artifact cannot cover an impact requirement.

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
| Unknown/high-fanout executable | full | repository, plus any known bounded impact | fail-safe true / true |
| New imports, consumer/mode drift, stale base with bounded executable impact | full | impact + repository | independently affected surfaces |
| develop/main integration push | full | repository | true / true |
| Release target or explicit complete-evidence PR recovery | full | repository, plus any bounded impact | explicit recovery enables both |

The bounded CI validators must already appear in the base critical inventory with positive and negative
acceptance mappings. Their selected test modules come from those immutable mappings. Newly introduced
executables, dependency changes, source mode changes and deletion-only hunks add repository/full evidence
without clearing bounded modules, selected tests, changed statements or base acceptance. Unmapped blank/comment
lines add repository evidence; executable mapping or required acceptance failures block plan consumption.
Decorator expressions retain executable mappings. Coverage policy semantics include source roots, thresholds, critical inventory,
suite selection, exclusions and negative acceptance. Formatting alone in the YAML policy does not change
those facts. In `pyproject.toml`, only descriptive package metadata is exempted; dependency, interpreter,
entrypoint, build and coverage configuration changes still require repository evidence.

Impact evidence has its own `coverage_tests` selection. The workflow's `--suite coverage-plan` runner validates
the plan and executes the union of required repository and impact tests, deduplicated by canonical test identity.
`ci_checks.py coverage` executes each required checker; either checker failing fails the job. The direct
`--suite impact` entry accepts impact-only plans. Full behavior can coexist with either or both coverage proofs.
Changed executable statement spans and their outgoing branches require
100/100; each impacted critical module retains whole-file 95/90 and its own positive/negative PASS evidence.
The report sets `repository_coverage_proved: false`. Repository coverage retains global 90% and critical
95/90, the original measurement roots, exclusions and negative acceptance. No behavioral tests are removed.
The workflow supplies both measurement roots as filesystem paths so validator-only impact runs still include
unimported package files and reconcile the complete declared exclusion inventory.

Each fixed aggregate recomputes the machine minimum against the event and exact Git target. Coverage may
skip only when the verified plan says `none`; required impact/repository coverage cannot be missing, skipped,
cancelled or failed. Metadata continuity compares behavior, coverage and both smokes independently. A prior
full-behavior result with no coverage cannot cover a new impact/repository requirement. A repository-only
artifact cannot replace impact evidence even if all global/critical floors passed. Version-1 bundled and
version-2 ordinal artifacts cannot satisfy the version-3 obligation contract.

## Acceptance evidence

[The PR #65 fixture](../../../../tests/fixtures/ci/pr65.json) contains its exact 20 Git change records,
base/head text blobs and SHA-256 hashes. The test constructs real Git commits from these records and checks
the resulting exact diff before requiring R2/full behavior, coverage none and both smokes false. It is pinned
to base `690a9f8` and head `09f9619`, so acceptance does not depend on retaining an old remote PR branch.

Additional adversarial tests cover bounded critical impact with 95/90 and distinct passing positive/negative
tests, coverage-authority mutations, unknown executable fallback, candidate fingerprint/group changes,
metadata and artifact scope reductions, and the required-job missing/skip/cancel/failure matrix.
The PR #66 blocking review adds repository-only reuse rejection, bounded source plus coverage-authority
retention, new-import guard retention, real union execution without duplicates, and both-checker failure propagation.

PR #65's successful pre-merge CI and its post-merge integration run are separate evidence. Integration pushes
continue to re-prove repository coverage deterministically; selective PR evidence makes no global claim.
Validation results for this revision are recorded in [VALIDATION.md](VALIDATION.md).
