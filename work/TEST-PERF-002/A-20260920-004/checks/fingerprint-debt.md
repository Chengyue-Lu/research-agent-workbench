# Reviewed leaf fingerprint anchor debt

Date: 2026-09-20. Owner: Chengyue-Lu. Reviewer: CI integrity / cost root-cause audit. Scope: immutable Git refs 348d6257ddd28637c9d06abe177fc685ac4368b6, 51dc3ab477f21f18ac3829bf553b5b779d49a4fe, 171d4654f88e926f239cdf25bc8168109b81f391; current unchanged planner/dependency implementation; supplied fingerprint-anchor audit. No policy/source changes, no Git writes, no network actions, no full test execution.

## Finding

**Confirmed production-selector conservative expansion caused by implicit anchor drift.** It is not merely a diagnostic display/cost issue, and no unsafe reduction is established. A base at PR #86 or #89 disables the existing reviewed leaf opaque-consumer boundary whenever a subsequent change would otherwise qualify for that boundary.

The decisive distinction is that a current tree fingerprint mismatch alone need not disable a historical reviewed boundary. The implementation was designed to retain an older reviewed anchor and invalidate changed consumers individually. Here a diagnostic pin update silently changes which anchor is chosen, defeating that mechanism.

`plan_ci.py:537` selects exactly the latest commit touching the entire `tests/ci_impact_policy.yaml` file at base (`git log -1 ... -- policy`). It does not search for the last matching fingerprint definition or carry an explicit accepted anchor. At 51dc3ab this resolves to 51dc3ab; at 171d465 it resolves to 171d465. Both commits retain the digest from 348d625 while adding/changing non-leaf inventory. The comparison at line 538 fails; lines 552-554 clear all `bounded` candidates and record `reviewed closure fingerprint anchor unavailable; opaque consumers retained`.

`ci_dependencies.py:653,662-669` then uses ordinary dependency/opaque propagation rather than the reviewed boundary. The same bounded/reviewed arguments also feed impact-proof selection (`plan_ci.py:582`), so this can expand behavioral selection and the cases used for impact measurement. It does not by itself prove a FULL or repository-coverage classification, nor quantify runtime; independent fallback/authority rules can also add those obligations. Pure documents and other changes without a qualifying bounded leaf do not enter this anchor branch.

The affected existing leaf inventory is unchanged across all three refs:

- `src/research_workbench/adapters/models/anthropic.py`
- `src/research_workbench/adapters/models/gemini.py`
- `src/research_workbench/adapters/models/openai.py`
- `src/research_workbench/artifacts/claim_trace.py`
- `src/research_workbench/capability/release_projection.py`

The function-body/import and evidence-drift guards still apply independently; restoring an anchor would not entitle every edit to these five files to be narrow.

## Immutable digest evidence

`consumer_fingerprint` (`plan_ci.py:43-51`) hashes sorted `[path, Git mode/type/object metadata]` records under src/, schemas/, registry/, tests/ and pyproject.toml, excluding all policy group coverage leaves and the impact-policy file itself. .github implementation files and docs are outside this particular inventory.

| Anchor | Records | Declared digest | Computed digest | Match |
| --- | ---: | --- | --- | --- |
| 348d625 / PR85 | 397 | 6550918ee9940e29a668a6a2880a8a9fb18873c2d8ebfff22b2e41eebc7382b0 | same | yes |
| 51dc3ab / PR86 | 404 | same | b624c23eda9f9ef5b5cc7778a9e4c6fc9e2f7971f17fdbb0205e0b5519989450 | no |
| 171d465 / PR89 | 409 | same | b35d849291b9d559172365c0260c438d3e931813b44224e9838013794b84f99b | no |

All three were independently recomputed from Git tree records and the current unchanged fingerprint function, matching the supplied audit. `fingerprint-record-deltas.json` records the exact old/new Git metadata for each contributing path. There are 11 changed inventory records in PR86 and 13 in PR89; the fingerprint is global, so these changes contribute collectively.

### 348d625 → 51dc3ab

- `schemas/v0.1.0/evaluation-harness-plan.schema.json` (added)
- `schemas/v0.1.0/evaluation-harness-preflight.schema.json` (added)
- `src/research_workbench/evaluation/harness_plan.py` (added)
- `src/research_workbench/evaluation/harness_preflight.py` (added)
- `src/research_workbench/validation/document_kinds.py` (changed)
- `src/research_workbench/validation/documents.py` (changed)
- `tests/coverage_policy.yaml` (changed)
- `tests/harness_fixtures.py` (added)
- `tests/test_evaluation_harness_plan.py` (added)
- `tests/test_evaluation_harness_preflight.py` (added)
- `tests/test_schemas.py` (changed)

### 51dc3ab → 171d465

- `schemas/v0.1.0/evaluation-harness-execution.schema.json` (added)
- `src/research_workbench/evaluation/harness_execution.py` (added)
- `src/research_workbench/evaluation/harness_runtime.py` (added)
- `src/research_workbench/execution/host.py` (changed)
- `src/research_workbench/observability/trace.py` (changed)
- `src/research_workbench/validation/document_kinds.py` (changed)
- `tests/coverage_policy.yaml` (changed)
- `tests/harness_execution_fixtures.py` (added)
- `tests/harness_fixtures.py` (changed)
- `tests/test_agent_trace.py` (changed)
- `tests/test_evaluation_harness_execution.py` (added)
- `tests/test_execution_host.py` (changed)
- `tests/test_schemas.py` (changed)

## Why the anchor moved without a refresh

The exact impact-policy JSON semantic diff for both ranges changes only `consumer_contracts`. PR86 updates two diagnostic pin fields: validation/documents.py and test_schemas.py. PR89 updates only the test_schemas.py diagnostic pin. `consumer_fingerprint`, groups, surfaces and impact evidence remain unchanged. PR86's squash message explicitly includes “refresh consumer pins after harness registration”; no digest refresh appears in either diff. The planner and dependency code are unchanged across these refs.

These consumer records describe themselves as diagnostic, with `execution_authority=false` in `ci_consumer_contracts.py`. Updating their truthful source pins should not redefine a production exclusion anchor, but their storage in the same file makes that happen. `validate_policy` checks schema/shape and records, not semantic self-matching of the latest Git commit. A mismatch is intentionally a conservative fallback, so green CI does not force maintainers to notice or refresh it.

This explains the technical omission and why it was not blocked. Git evidence does not establish the authors' intent or awareness; it would be inaccurate to claim a deliberate decision to leave the digest stale.

## Safe repair evidence; do not blindly refresh

A fresh digest at 171d465 would reclassify newly introduced non-leaf consumers as reviewed/unchanged for later leaf edits. It is therefore a production selection authority update, not a harmless checksum repair. Newly added execution/resource consumers must not gain exclusion authority merely because CI passed once.

Prefer evaluating a repair that preserves the last accepted authority anchor across diagnostic-only record changes: an explicit exact anchor or semantic-authority history lookup. Evidence must show that the anchor is an ancestor of base, its fingerprint matches its own complete inventory, and its authority-bearing groups/surfaces/impact evidence agree with the accepted base authority. Arbitrary older matching hashes or candidate metadata cannot authorize a boundary. Preserve current base/head/anchor per-consumer byte checks, proof/helper/resource closure drift, imports/mode/function-body guards, unknown/new consumer retention and FULL fail-safe.

Before merging such a production repair, retain these adversarial proofs:

1. Metadata-only consumer-record pin edits with unchanged authority preserve the historical anchor; real Git history reproduces PR86/89 coupling.
2. New and changed opaque consumers since that anchor remain selected; relevant failing controls are retained. New helper, package initializer and fixture-directory membership also invalidate impacted evidence.
3. Group/surface/leaf/acceptance changes and a candidate fingerprint rewrite cannot backdate or approve themselves; mismatched/missing history remains conservative.
4. Compare exact old/new plans for representative provider, claim-trace and release-projection local edits, with real passing and failing cases. Separate identity-count reductions from hosted timing.
5. Re-run selection-authority bootstrap, independent witness, quality floors and review required by the production authority change. A reviewed current-inventory refresh is a separate alternative requiring closure audit of all newly admitted consumers, not just recomputation.

## How current PR92 should describe this

Record an inherited production anchor/cost debt discovered by 2B observations. State that current 171d465-based leaf pilots retain conservative propagation because the last policy-file edit no longer matches the preserved digest; no production policy was refreshed and no resulting reduction was activated. Keep the earlier matching 348d625 probe explicitly historical; it is not the current accepted plan and cannot establish current hosted savings.

This inherited issue does not invalidate the correctly bounded diagnostic tools or their unchanged obligations. It is not, on its own, a reason to merge a production selector repair into diagnostic-only PR92. Repairing an existing accepted leaf boundary is also distinct from activating new 2C consumer exclusions; both require their own clear authority/evidence scope. The current 2B PR can be reviewed with this limitation visible, while the production anchor repair receives a separate scoped change and validation.
