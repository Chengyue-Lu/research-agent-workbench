# TEST-PERF-002 contract shadow v1 evidence

Owner: Chengyue-Lu. Risk: R2. Attempt: A-20260916-006. User authorized the first implementation, Draft PR and Issue #48 update.

## Retained local results

- Implementation commit: `627487c1d56f8c026bc9d460ecd4dd66279000ae`; base: `0d4a1d00a4c32ca9b822df6482a95920e7c21b1b`.
- New module: 12 PASS; 140/140 statements and 58/58 branches, zero exclusions.
- Existing dependency/planner/checker/witness/coverage-policy/documentation regression: 189 PASS in 260.663 s. Together: 201 PASS; this is focused regression, not a repository full-suite result.
- Exact implementation-head plan, worker recomputation and governance: PASS. Obligations: full behavioral, impact + repository coverage. Actual impact subject: `.github/scripts/ci_contract_shadow.py` only.
- PR84 replay: 15 document, 8 evidence-data, 1 archive-attributes, 9 classification conflicts; retained dependency selection 91/92. Diagnostic analysis: 7.360 s on this local run. CI savings have not yet been established.
- Existing quality thresholds, omitted modules, coverage exclusions and selection implementations remain unchanged; the diagnostic workflow is the declared authority-sensitive change.

The implementation plan predates this archive commit. Final-head plan/governance checks and hosted CI are separate PR evidence; archived source hashes identify the tested bytes. This archive does not attest hosted full execution or human acceptance.

## Scope and navigation

[Implementation and boundaries](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/SHADOW_V1.md), [source and check hashes](checks/evidence-manifest.json), [implementation preflight](checks/implementation-preflight.json), [PR84 report](checks/pr84-shadow.json), [Trace validation](checks/trace-validation.json).

The shadow report preserves all accepted obligations and cannot control skip or impersonate plan v4. Inputs/contracts still require reviewed consumer boundaries and independent witness support before activation.

Trace is retrospective retention of the observed results, with an explicit capture-gap warning. It is not a complete tool-event stream. Historical evidence and the deliberately failing document probe retain their original outcomes.
