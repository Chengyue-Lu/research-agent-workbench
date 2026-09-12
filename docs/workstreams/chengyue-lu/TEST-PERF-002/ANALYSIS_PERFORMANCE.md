# Incremental CI project comparison and dependency analysis cost

Owner: Chengyue-Lu; cross-owner: let778750-cpu; Audit ID: TEST-PERF-002; R2.
Sources inspected on 2026-09-11. Implementation continues PR #70 on
`develop@11c3b57dfbf8af0dc2587fc421d097e2544941c3`.

## Projects and adoption decision

| Project | Relevant mechanism | Fit and adoption in this repository |
|---|---|---|
| [Pants](https://github.com/pantsbuild/pants) | Explicit dependency modeling, fine-grained invalidation, caching and concurrent execution. Its [changed-target guide](https://www.pantsbuild.org/stable/docs/using-pants/advanced-target-selection) uses merge-base plus transitive dependents. | Keep exact Git facts and old/new closure; apply the fine-grained invalidation idea to immutable per-file syntax facts. Resolve facts against every snapshot's current module/resource inventory. A full build-system migration would require additional target and resource contracts. |
| [pytest-testmon](https://github.com/tarpas/pytest-testmon) | [Runtime coverage dependencies](https://www.testmon.org/) select tests after an initial complete run; the database is updated as tests execute. The documented dependency model does not track static assets or external services. | Useful as a future observation source for overly broad static edges. Its database cannot authorize removing resource, negative-acceptance or base-side obligations here. No runner/database dependency is introduced. |
| [rut](https://github.com/schettino72/rut) | A unittest runner with import-based ordering and transitive changed-test selection; file hashes are recorded after successful runs within configured source directories. | Close to our unittest execution model. Import topology can help explain consumers and order feedback; file-hash freshness alone does not establish this repository's exact-ref, policy and resource proof boundaries. |
| [pytest-xdist](https://github.com/pytest-dev/pytest-xdist) | [Process scheduling](https://pytest-xdist.readthedocs.io/en/stable/distribution.html) supports load, module/class scope and whole-file grouping. | Whole-module groups are a useful model for a later parallel unittest runner. Adoption needs fixture isolation, complete test-ID receipts, worker-failure handling and measured runner capacity. This change leaves execution order and coverage collection intact. |
| [pytest-incremental](https://github.com/pytest-dev/pytest-incremental) | Project-structure analysis for test ordering and deselection. Its README marks it unmaintained and points to rut. | Historical reference; do not introduce an unmaintained pytest plugin into the current unittest runner. |

These are design references, not claims that another project's selector proves our
coverage or governance obligations. No external source implementation was copied.

## Implemented optimization

The existing resource repair fixes false dependency edges. Profiling its source at
`c70aa6c8c27c5eaf7f4fc7af6b289ce3f2a2418a` found a separate cost: repeated AST walks
within each Python file and repeated analysis of the same bytes across Git snapshots.
The measured snapshot has 185 Python files, 1,176 paths and 7,187 dependency edges.

The analyzer now separates file syntax facts from graph resolution:

1. A bounded, process-local LRU stores immutable syntax facts keyed by repository-relative
   path and exact Python bytes. Path is necessary for relative imports and `__file__`.
2. Each file's AST traversal and function-scope load/mutation index are reused during
   analysis. The cache retains immutable fact sets, not mutable ASTs or returned graphs.
3. Every graph rebuild resolves symbolic imports, literal filenames and directory inputs
   against that snapshot's complete current inventory. Directory descendants are indexed
   once instead of scanning all paths for each expression.

Adding/removing a module, package initializer, directory entry or same-named resource
therefore changes graph resolution even when a consumer's bytes are unchanged. A byte
change or path rename invalidates its syntax facts. Invalid Python still produces an
error. Returned graph mutations cannot alter cached facts. Eviction only repeats analysis.

This is analysis reuse inside one Python process. It neither stores test PASS results
nor reuses a previous plan as execution authority. Every worker still validates the
exact plan and Git state, with independent selection witness and fail-closed gates.

## Reproducible local measurements

Windows, Python 3.11.16; three alternating before/after samples, medians shown. Cold
graph samples clear analysis caches while retaining the already-read immutable blobs.
Cold plan samples clear graph, syntax, snapshot and planner blob caches and include
Git reads. Warm samples reuse syntax facts but rebuild all inventory-dependent edges.

| Operation | Before | After | Reduction |
|---|---:|---:|---:|
| Cold dependency graph | 3.548 s | 1.416 s | 60.1% |
| Warm dependency graph | 3.575 s | 0.017 s | 99.5% |
| Complete cold PR #68 plan | 7.658 s | 2.628 s | 65.7% |

The complete graph outputs are identical for base `11c3b57`, original docs head
`0f6da94`, and pre-optimization candidate `c70aa6c`. The PR #68 plan is identical in
all fields, including plan ID, inclusion/exclusion chains, selected tests and obligations:
10 modules, focused behavior, coverage none, both smokes false. This performance change
does not further shrink that test set.

These are local analyzer/plan timings, not hosted workflow wall-time measurements.
The separate [resource repair](RESOURCE_DEPENDENCIES.md) records the earlier reduction
from 35 to 10 selected modules. The introducing selector PR still requires full
dual-Python behavioral bootstrap; its run duration cannot represent a future docs PR.

The new regression cases cover module/resource inventory changes, path-sensitive
facts, byte and syntax-error transitions, and mutation isolation. Existing adversarial
resource/closure tests remain. Final measured targeted evidence is 41 PASS and
410/410 statements, 266/266 branches in the analyzer. Exact-head hosted bootstrap,
impact proof and cross-owner review remain required before merging.

## Next measured opportunity

Execution dominates long full runs after planning. The next candidate is scheduling
complete test modules across isolated workers using recorded durations, while retaining
all expected IDs and complete class/module fixtures. Before enabling it, demonstrate
identical outcomes, failure propagation, setup/teardown handling and coverage union;
compare both wall time and total runner cost. Runtime dependency observations can also
identify uncertain static edges for explicit reviewed contracts. They do not silently
replace missing resource dependencies or repository-wide integration coverage.
