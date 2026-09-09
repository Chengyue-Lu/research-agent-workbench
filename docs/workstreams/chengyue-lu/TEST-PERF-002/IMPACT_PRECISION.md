# Impact selection precision: next repair round

Status: candidate implementation under validation; contract review and hosted performance acceptance pending.
Owner: Chengyue-Lu; cross-owner: let778750-cpu; Audit ID: TEST-PERF-002; risk: R2.

Request: [Issue #48 comment 5573581053](https://github.com/Chengyue-Lu/research-agent-workbench/issues/48#issuecomment-5573581053).
Accepted implementation: PR #66, merged into `develop@bdbac11a0c9a17fa221f8cc8bdd522c1bf4f9087`.
Next branch: `feature/test-perf-002-impact-precision`, starting at that exact base.
The [revision 13 intake](../../../../work/TEST-PERF-002/A-20260908-001/RESULTS.md)
pins the request, raw selection certificates and hosted artifact hashes.
The [revision 14 implementation record](../../../../work/TEST-PERF-002/A-20260908-002/RESULTS.md)
records the independent proof selector, guarded local contracts and collector repair.

## Reproduced baseline

PR #60 head is `205559b25f7f0bd276094a4ac53db28354b7284d`; its hosted test target is merge candidate
`b9d5d432c0ba9455eca9aedba7823095b83fbc2f` against the accepted develop above.
The dependency analyzer at that head is byte-identical to the accepted develop analyzer.
Read-only calls to `ci_dependencies.select(repo, head, head, {seed})` reproduced:

| Sole hypothetical seed | Selected / inventoried test modules |
|---|---:|
| `src/research_workbench/artifacts/claim_trace.py` | 72 / 75 |
| `.github/scripts/release_surface.py` | 72 / 75 |
| `src/research_workbench/capability/release_projection.py` | 72 / 75 |

These are raw dependency probes on an immutable snapshot, without Git modifications, contract overrides,
test execution or wall-time experiments. A final plan also adds base policy groups and explicit obligations.
The earlier 44/1040 M14 result depended on an extra reviewed-base contract assumption; that contract is
absent from this accepted baseline and is not evidence of a formal M14 speedup.

The downloaded [CI 34131110394](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34131110394)
plan has `behavioral_scope=full`, `coverage_scope=impact+repository`, and identical 74-module
`tests` / `coverage_tests` lists. Its coverage artifact reports 1039 passing tests in 2655.396489 seconds.
Classification of those executed IDs against the exact-head repository coverage policy gives 978 repository
suite members and 61 tests re-added by impact selection. Those 61 tests account for 937.590517 seconds
(15.6 minutes, 35.3% of the combined coverage suite wall time).

| Re-added test module | Cases | Observed instrumented case time (seconds) |
|---|---:|---:|
| `test_generic_execution_closeout` | 10 | 515.574 |
| `test_execution_trace_adapter` | 14 | 144.160 |
| `test_execution_host` | 9 | 137.616 |
| `test_trace_properties` | 3 | 83.447 |
| Other four modules | 25 | 56.794 |

This is cost attribution within one executed union, not a measured 15.6-minute saving. The runner already
deduplicates canonical test IDs inside that union. A smaller impact proof suite may still need some of
these tests. Complete behavior retains its required integration cases.

GitHub job start/completion timestamps provide a distinct timing measure:

| Job | Wall time (seconds) | Result |
|---|---:|---|
| compatibility (3.11) | 1566 | success |
| compatibility (3.13) | 1724 | success |
| coverage-quality (3.11) | 2674 | failure |
| package-smoke (3.11) | 98 | success |
| package-smoke (3.13) | 84 | success |
| repository_smoke | 16 | success |

Test execution passed; impact coverage failed, and both aggregates blocked. The Issue comment separately
records repository global line 93.07% with all critical floors passing. This intake did not rerun that checker.
Initial M14 integration changes build/workflow/packaging surfaces and legitimately has broader obligations
than a later single-module change. The two acceptance questions remain separate.

## Implementation sequence

### 1. Explain and bound dependency expansion

Start with the three frozen probes and classify each path that crosses a module boundary: actual import
and package initialization, fixed dynamic execution target, resource input, source/fixture inspection, or
unresolved execution. Record provenance and exclusion reasons in the selection certificate. Preserve real
shared dependencies; a source reference or subprocess call is not sufficient evidence to delete an edge.

Resolve fixed entrypoints and resource inputs only where immutable base/head syntax or an accepted base
consumer contract establishes the boundary. Keep unresolved execution conservative. Preserve the union
of old/new dependencies, Markdown consumers, assigned/reflected loaders, changed imports and new/changed
consumers. Candidate policy, fingerprints, scan classifications or selector edits cannot approve a smaller
minimum themselves. Review any new consumer boundary before using it as the base of a measurement.

Deliver a consumer inventory for each probe with must-run modules, justified exclusions and unresolved
edges. Freeze that inventory before changing selection, so the selector does not define its own oracle.

### 2. Derive impact proof tests independently

Build `coverage_tests` from accepted proof mappings for impacted subjects and their mandatory positive /
negative evidence, independently of the complete affected behavioral closure. Prefer exact deterministic
test IDs when a module also owns slow behavioral cases. Keep necessary integration tests in behavioral
execution and retain them in impact measurement when they supply indispensable proof.

The plan must expose why each proof test is required, bind this list to the exact Git facts and policy, and
allow only monotonic candidate additions. Workers and aggregates must recompute it. Missing proof mappings,
missing subjects and uncovered statements/branches block or require conservative additional evidence;
repository coverage cannot substitute for missing impact proof. Combined obligations still execute a
canonical union once and run both checkers. Do not subtract repository policy omissions from impact by fiat.

### 3. Close executable collection and integration gaps

Require every planned impact subject to be present in measurement. PR #60 reports a missing
`build_backend.py` subject despite its tests executing, and an archived
`work/M14-002/A-20260906-001/checks/independent_projection_oracle.py` subject. Verify the collector closure
and distinguish sealed evidence from actually executed/imported work files. A blanket `work/**/*.py`
exemption would hide real consumers and is not an acceptable repair.

The portable package smoke passed outside the coverage process; that success does not supply instrumented
statement/branch evidence. Coordinate genuine M14 code-path/test gaps in PR #60 separately from generic
selector changes. Keep executable collection aligned with the existing exclusion reconciliation.

## Acceptance matrix

| Case | Required evidence |
|---|---|
| Each of the three real modules | An isolated committed equivalent/local edit, exact plan, predeclared consumer oracle, selected/excluded rationale, actual selected test IDs/counts and per-job timings |
| Source and downstream faults | Separate real mutants in each module and a relevant downstream consumer, rejected by the same selected suite; establish the positive control first |
| New consumer / removed or changed import | Base/head union retains old consumers and adds new obligations; accepted leaf boundary cannot hide changed imports |
| Markdown input / reflected execution | Retain the already accepted regression failures and ordinary-data narrow-path positive controls |
| Candidate scope reduction | Forged proof list, new contract/fingerprint and modified selector cannot bypass base authority or the independently pinned selection witness |
| Coverage proof | Changed executable statements/outgoing branches 100/100; impacted critical whole-file 95/90 and positive/negative evidence; absent collector subject blocks |
| Aggregate and metadata | Required skip/cancel/missing/failure blocks; metadata cannot cancel or manufacture content evidence; current exact target required |
| Integration and build authority | Full behavioral validation, repository global 90%, all critical 95/90, existing exclusions/negative acceptance and independently required smokes |

Run fixtures on isolated M14-based test branches; M4 is outside this experiment. Use the same Python/runner
configuration for before/after comparisons, identify setup and queue time, report both critical-path time
and summed runner time, and do not equate module counts with test counts or local timings with hosted savings.
An accepted-contract experiment must name the separate reviewed base that authorized its smaller scope.

Completion requires source/downstream fault capture AND a substantial measured reduction for ordinary
local changes in all three modules. If real dependency closure stays broad, report that limit explicitly;
a FOCUSED label alone does not pass. Retain the full/adversarial test inventory and quality thresholds.
Selection-authority implementation itself requires the full dual-Python bootstrap and a fresh witness
receipt for its exact head, followed by cross-owner review and all required CI checks.

This intake changes planning/evidence only. It neither changes M-series Task states nor authorizes release,
tags, main, protection changes or activation of further M14 milestones.
