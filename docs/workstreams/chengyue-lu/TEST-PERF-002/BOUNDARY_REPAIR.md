# Dependency boundary repair — bounded implementation

TEST-PERF-002; Chengyue-Lu; R2; Issue #48. Implementation starts from
`7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba` after the M11-007 integration.

## Implemented scope

Literal `len("SKILL.md")` computes metadata and does not read every repository file
with that name. The analyzer now recognizes that operation when `len` resolves to
the builtin. Function/class definitions, exception and pattern bindings, imported or
parameter aliases, global mutation, reflection and opaque execution retain conservative
dependencies. Actual file reads with the same literal continue to select their tests.
Call-mediated mutations through `patch`, imported patch aliases, `patch.object`,
`setattr` helpers and `__setattr__` also invalidate this optimization when their
target can be `builtins.len`. Dynamic targets and unknown receivers remain conservative;
fixed unrelated patch targets preserve ordinary literal-length precision.

Workflow comments and formatting now use the same typed YAML comparison for behavioral
and coverage authority. When both YAML semantics and file mode match the base, the
workflow does not seed the global resource-reader fallback. YAML semantics, duplicate
entries/scalar types, file-mode changes and independent job additions keep the existing
full authority bootstrap. The independently pinned selection witness remains unchanged.

Plans now report `selection.selected_edge_kinds` for every selected test's chain and
`selection.scope_summary` with `dependency_selected_test_modules`, the inventory count and counts of paths using
opaque-execution or unbounded-resource edges. These explain scope; they do not authorize
exclusions. Existing workers compare the complete selection proof during verification.
The dependency-selected count precedes policy groups and explicit additions; final
execution scope is given by `plan.tests` and its independent obligations.

## Measured selection changes

The comparisons run the accepted and modified planners over the same immutable Git
candidate snapshots. Their historical base is `0bebafd81f0116a8269c63ac97378038a1eb2a5d`;
the PR #72 replay uses its original base/head. These are planner experiments, not new
hosted execution or merge evidence. Counts refer to test modules, not TestCases.

| Candidate change | Before | After |
|---|---|---|
| New candidate SKILL.md | 85 modules, focused, coverage none | 13 modules, focused, coverage none |
| Workflow comment only | 86 modules, focused, repository coverage | Documentation obligations only, coverage none; 2 documentation modules |
| Ordinary docs/STATUS prose | 10 modules, coverage none | 10 modules, coverage none |
| Ordinary test assertion change | 8 modules, coverage none | 8 modules, coverage none |
| Shared fixture comment | Documentation obligations only | Same |
| Shared fixture semantics | 84 modules, coverage none | Same; unresolved scope recorded below |
| New observer plus its test | 85 modules, impact coverage | Same; unresolved scope recorded below |
| JSON fixture | 86 modules, coverage none | Same; unresolved scope recorded below |
| New Skill YAML | Full, repository coverage | Same |
| Independent develop-only job / new workflow | Full, repository coverage | Same |
| Actual docs PR #72 | 38 modules, coverage none, package smoke | Same |

The introducing PR changes selection authority and must itself run the complete dual-Python
bootstrap. Its CI duration cannot measure the speed of a future Skill/docs PR.

## Follow-up work tracked in Issue #48

PR #83 closes the bounded changes above, their review findings and the fixed-root
subset documented below. The remaining expansion repairs retain their own proof requirements.

1. Scope opaque execution and resource access by proven targets/roots. Unknown calls and
   readers currently create nearly repository-wide dependencies; do not remove them without
   evidence for aliasing, reflection, inventory changes and path escape.
2. Distinguish generated output filenames and ZIP/member/string metadata from repository
   inputs. PR #72's README basename still reaches scaffold and CLI consumers. Literal-length
   handling closes one demonstrated instance, not the complete resource provenance model.
3. Distinguish lazy/conditional imports, re-exports and import-time effects. The ordinary
   static graph contains a 45-file import strongly connected component including local
   imports; it is not evidence of a runtime import failure and cannot simply be cut.
4. Classify independent integration jobs together with the trusted witness. Keep shared
   configuration, plan/coverage producers, artifact dependencies and aggregates protected.
5. Prove excluded-statement identity across source-line relocation before treating an
   unchanged exclusion as local. Threshold/root/executable-exclusion changes remain global.
6. Give new Skill/config surfaces stable input/consumer classification, and derive smoke
   obligations from the corrected graph. Installed schema changes still require smoke.

Each follow-up needs both a precision control and a real failing selected-consumer case.
`focused` or `impact` alone is not success: verify actual inventories, negative evidence,
critical 95/90, changed 100/100 and measured execution time. Integration global 90 and full
behavior, exact-target receipt binding and the ordered B then C-minus-B contract remain.

## Related time-saving work considered

The prior [full-suite cost audit](FULL_SUITE_COST.md) already established successful schema
self-check reuse and retained the necessary behavior/negative cases. Scope reduction is
the immediate opportunity here. Test splitting, shared fixture reuse and process scheduling
must preserve module/class lifecycle and ordered execution; no additional worker or fixture
cache is enabled by this change. Cross-commit result reuse needs complete input/environment
keys and a separately reviewed evidence contract; overlapping test names are insufficient.

Analysis timings are retained with the comparisons, but cold/warm state and Windows Git
process costs vary between samples. They are diagnostics, not a new analyzer speedup claim.
The initial Draft push contained implementation and its archive, avoiding
an intentional code-push followed immediately by an archive-only replacement CI run.

Evidence and implementation hashes are recorded in the
[Attempt results](../../../../work/TEST-PERF-002/A-20260915-001/RESULTS.md).

## Review remediation

The task-owner review of `288489429b412ead2f0f8df34c43655c25089900` identified a
call-mediated builtin mutation gap. Selector-level regressions cover dotted/object
patches, import aliases, helper overloads, keyword arguments and uncertain targets.
Two actual Git repositories exercise unchanged readers with `patch` and `patch.object`:
changing the document from four bytes to three makes execution fail, and the selector
retains the failing consumer. Ordinary metadata and all prior direct/lexical/opaque
controls remain covered. The diagnostic count name also resolves the review's P2 ambiguity.
The [review-remediation Attempt](../../../../work/TEST-PERF-002/A-20260916-001/RESULTS.md)
records 47 dependency, 106 planner/checker/witness and 10 documentation checks, source
hashes and critical/changed coverage. Hosted final-head checks are linked from PR #83.

The subsequent review of `55f20aa4e9887e882c716a53a1d7346bb31ad880` adds the bounded
`patch.multiple` rule: explicit `len` or expanded keywords invalidate metadata when
the target may be builtins. Fixed unrelated targets or fixed unrelated attribute sets
retain precision. The adjacent `patch.dict` namespace form also retains dependencies
when its target may be the builtin dictionary; replacement/clearing can affect the
whole namespace. Imported patch aliases use the same rules. The shared real-Git
failure scenario now covers direct patch, object patch, multiple patch and dictionary
patch without adding separate full test modules.
The [batch-patch Attempt](../../../../work/TEST-PERF-002/A-20260916-002/RESULTS.md)
records the reproduced omissions and the final local source/coverage checks.

## M6-008 expansion audit and fixed repository inputs

PR #75 at `34cc426e9c08d837ffc2e6dc58732c08a659291e`, against
`7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba`, selected 91 of 92 behavioral test
modules. Its impact coverage measured five source files; 108 coverage selectors
represented 89 distinct test modules, including individual acceptance cases. The
coverage job took 11m05s in run `35025376167`. This was a nearly complete execution
set, not repository-wide instrumentation or a risk-driven FULL fallback. Installed
schemas and the generic validation registration independently justify both smoke jobs.

The analyzer now distinguishes exact `__file__`-anchored pathlib reads and directory
scans from unknown resource roots. Directory scans retain the entire inventory below
their root, including new files. Fixed `runpy.run_path` targets retain the archived
script and its transitive imports; unparsed or unknown targets keep opaque execution.
Shadowed bindings, mutation helpers, escaped reader capabilities, path escape and
symlink modes retain conservative fallback. Immutable syntax caching never caches a
resolved inventory or test result, and base/head edges are still combined.

For the same M6 snapshots, nine consumer files no longer acquire an unconditional
resource edge from every new schema: the fallback reader set decreases from 125 to
116. The complete M6 selection remains 91/92 because independent paths still reach
those consumers. Public validation changes reach the CLI and package initializers;
parameter-driven I/O helpers, opaque execution and output-name references remain
conservative. Removing those paths requires additional evidence about callers and
inputs. This repair does not establish an M6 wall-time reduction.

Regression scenarios retain failing unchanged consumers in real Git repositories:
changing a fixed resource or executed script breaks its reader/replay, which stays
selected. Unrelated new-schema probes exclude these fixed consumers. The previous
PR #83 analyzer fails eleven precision assertions in the same scenarios. Controls
cover directory additions, lexical mutation, escaped calls, unknown executables,
symlink inventory changes and old unbounded readers. Evidence is retained in the
[fixed-input Attempt](../../../../work/TEST-PERF-002/A-20260916-003/RESULTS.md).

## Archive source identity correction

Cross-owner review of `5d989f87abf0a84c57cd87587c526488d09a549a` found that the
frozen comparison producer was packaged as `checks/compare_scope.py`. The final
candidate correctly treated that added Python file as executable and required impact
coverage for it. Run `35028593655` failed that gate because coverage had no such
module, despite successful behavioral execution and the selection witness.

The producer is retained as [source evidence](../../../../work/TEST-PERF-002/A-20260916-003/checks/compare_scope.py.txt).
Its original bytes and SHA-256 `a444af83162de6ff29e206b915c7f95acc86f7825484f58ad73bdcc56fb1a768`
are unchanged; only its filename and the matching archive check reference move. It
records a scratch-directory producer, including that producer's original ROOT logic,
and is not an installed or runnable archive tool. The original INDEX is retained in
the [correction Attempt](../../../../work/TEST-PERF-002/A-20260916-004/RESULTS.md).

Preflight now inspects every module required by the final candidate's plan, after
archive files are included. The earlier check inspected only two named critical
modules and therefore missed this new obligation. Production selection rules,
coverage exclusions, floors and witness authority are unchanged; fresh final-head
hosted checks remain required. Historical passing test receipts are not rebound to
the corrected candidate.
