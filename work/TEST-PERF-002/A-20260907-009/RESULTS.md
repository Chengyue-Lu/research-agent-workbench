# TEST-PERF-002 review repair, revision 11

The two P1 omissions reported by cross-owner review comment 5564944896 are repaired in `8ba54a432ff54afe85b98729e387f74a243a1521`, based on `develop@b8a38a1d0cea4e8422ade8481aec4c277250d6cb`. The incremental repair starts at `def9322d44dd7bd6161d244f81f7b1ee6a7adeb6`.

## Repairs and adversarial evidence

- Changed Markdown enters the immutable base/head dependency graph. The real Git fixture changes only an existing Markdown input: its consumer passes at base, fails at candidate, and is now required by the verified focused plan. Unreferenced documentation in the planner fixture keeps documentation-only obligations.
- A known execution namespace escaping through assignment retains an opaque consumer. The real Git fixture assigns `namespace = importlib`, obtains a reflective loader, and changes only the imported source. The failing reflective consumer is retained alongside the passing direct-import control. Both review counterexamples failed before the repair and pass as regression tests after it.
- A constant ordinary data field such as `getattr(path.lstat(), "st_file_attributes", 0)` does not itself imply dynamic code execution. Actual resource-input edges remain covered. Unknown execution and execution attributes retain conservative behavior.
- M14 isolated commit `7dea133a8e5f5e98dc05af0cfb9a2933a67ba050` adds independent SHA-256 known vectors and checks exported output, policy, generator, generated-input and manifest-receipt hashes. Two positive methods pass. A separate actual constant-zero implementation at local probe `8a50c062a539e5106eb8852483415d6ca83de18f` fails those two methods with three expected assertion failures. No digest mock supplies the expected values.

## Validation

- Focused planner/checker/dependency/witness regression: 101/101 PASS, 250.375 seconds locally.
- Incremental dependency helper: 100% statements / 100% branches; planner: 99.7758% / 98.6842%. Both repaired executable files cover every changed statement and outgoing branch. Existing positive/negative acceptance IDs pass.
- Documentation and coverage-policy checks: 30/30 PASS. Repository validation: 183 validated, zero errors, zero warnings.
- Local coverage above proves the repair increment. It is not repository coverage and does not replace the final hosted plan's complete PR obligations.

## Repeated M14 selection probes

The isolated integration baseline `65b22cb154fc60805946072699573be9d8b5af13` combines the repaired CI and independent M14 hash assertions. Official M4 and M14 PR branches remain unchanged.

| Probe | Head | Obligations | Observed result |
|---|---|---|---|
| New M14 workstream Markdown | `09dca68630d56742b72de5c02e5efa1c97b076af` | focused, coverage none, both smokes false | 215/215 PASS, 219.668 seconds suite / 219.781 seconds process |
| Existing M14 README comment | `751add0a29de10ed8b68af6a94d2624700ad0ad5` | focused, coverage none, both smokes false | Plan verified; behavioral suite not repeated |
| Equivalent digest function | `00b82ea3e66c6a66c568bfee7e599d0825809b36` | focused, impact coverage, both smokes true | 1027/1039 tests selected, only 1.15% excluded; selected suite not rerun |

The earlier 93-test documentation observation is historical. Preserving Markdown dependency edges now exposes conservative transitive paths through documentation tests, runner/planner fixtures and literal references. The function still reaches broad consumers through opaque subprocess execution, for example release_surface -> research_state/gate -> validation/documents -> observability/models -> API session tests. Removing the erroneous stat-access edge alone does not shrink the resulting union.

**The substantial CI time reduction acceptance remains open.** No full-suite elapsed-time comparison was collected for these probes, and no hosted saving is claimed. Correctness fixes do not justify deleting conservative execution edges. Further narrowing needs bounded, auditable resource/execution dependencies or reviewed base-side consumer contracts, with the newly preserved consumers retained.

## Review and integration boundary

The final PR still changes selection authority, so it requires complete dual-Python behavioral regression and the plan's independent coverage/smoke obligations. Cross-owner acceptance and a receipt from the unchanged independent witness root `1b543393ae71b9032359b739170d66ec0be08772` must bind the final candidate. That witness proves the behavioral floor, not consumer-graph completeness; it remains a manual review obligation rather than an automatic required check.

Hosted CI/witness for the final archive commit follows this record. No merge is authorized by this archive. Global 90%, critical 95/90, changed 100/100, exclusions, base-side policy, M4 acceptance entries, integration baseline rules and release boundaries remain intact. Trace capture gaps are retained explicitly.
