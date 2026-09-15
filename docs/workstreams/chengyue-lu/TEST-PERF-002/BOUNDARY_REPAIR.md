# Dependency boundary repair — Draft implementation

TEST-PERF-002; Chengyue-Lu; R2; Issue #48. Implementation starts from
`7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba` after the M11-007 integration.

## Implemented in this Draft

Literal `len("SKILL.md")` computes metadata and does not read every repository file
with that name. The analyzer now recognizes that operation when `len` resolves to
the builtin. Function/class definitions, exception and pattern bindings, imported or
parameter aliases, global mutation, reflection and opaque execution retain conservative
dependencies. Actual file reads with the same literal continue to select their tests.

Workflow comments and formatting now use the same typed YAML comparison for behavioral
and coverage authority. When both YAML semantics and file mode match the base, the
workflow does not seed the global resource-reader fallback. YAML semantics, duplicate
entries/scalar types, file-mode changes and independent job additions keep the existing
full authority bootstrap. The independently pinned selection witness remains unchanged.

Plans now report `selection.selected_edge_kinds` for every selected test's chain and
`selection.scope_summary` with the inventory/selected counts and counts of paths using
opaque-execution or unbounded-resource edges. These explain scope; they do not authorize
exclusions. Existing workers compare the complete selection proof during verification.

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

## Remaining work in this Draft

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
cache is enabled by this Draft. Cross-commit result reuse needs complete input/environment
keys and a separately reviewed evidence contract; overlapping test names are insufficient.

Analysis timings are retained with the comparisons, but cold/warm state and Windows Git
process costs vary between samples. They are diagnostics, not a new analyzer speedup claim.
The Draft is prepared as one initial push containing implementation and its archive, avoiding
an intentional code-push followed immediately by an archive-only replacement CI run.

Evidence and implementation hashes are recorded in the
[Attempt results](../../../../work/TEST-PERF-002/A-20260915-001/RESULTS.md).
