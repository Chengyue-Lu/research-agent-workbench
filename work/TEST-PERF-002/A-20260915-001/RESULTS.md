# Dependency boundary Draft evidence

TEST-PERF-002 revision 28; owner Chengyue-Lu; R2.
Baseline: `7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba`.

This Attempt records the initial literal-metadata, workflow-formatting and selection
diagnostic implementation. The [Draft matrix](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/BOUNDARY_REPAIR.md)
separates completed precision changes from unresolved dynamic/resource/import boundaries.

Implementation: `0b8032762dadec4b32f74cc38676d91427ee9433`.
Consumer-fingerprint/source-check head: `acd900bc2d9c16bec6eecff7421efb9a97c8c391`.

- 44 dependency tests, 106 planner/checker/witness tests and 10 documentation tests PASS.
- A separate 73-test planner coverage rerun passed. Combined source measurements: analyzer
  432/432 statements and 280/280 branches; planner 538/539 statements and 204/206 branches.
  All changed executable line/branch coordinates are covered. Global repository coverage
  is not claimed by these local source checks.
- Actual local PR-event governance and plan verification PASS at the source-check head.
  The plan correctly retains full behavior and impact coverage for selection-authority changes.
- Twelve historical candidate comparisons retain the same Git facts: SKILL.md selection
  85 to 13 modules; workflow formatting 86 modules/repository coverage to documentation
  obligations/coverage none. Other audited expansion scenarios remain explicitly pending.
- The first regression caught an unregistered function binding for len; definition,
  exception and pattern bindings plus reflective mutation checks now preserve those readers.

Check logs are normalized to LF for archival; original file hashes and byte sizes are
retained in `checks/capture-manifest.json`. Native event/message capture gaps are explicit.
This archive records a Draft delivery. Exact-head hosted full CI and independent review
remain separate; no merge or release is authorized.
