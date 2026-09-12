# Incremental dependency analysis evidence

TEST-PERF-002 revision 23; Chengyue-Lu; R2; source `4283a0c18b3dfd95362b72d75cdad78702b2121c`.

Research references and adoption rationale are in
[Analysis performance](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/ANALYSIS_PERFORMANCE.md).
The implementation caches immutable per-file syntax facts and rebuilds inventory-dependent
edges. It also reuses AST/scope traversals and indexes directory descendants.

The complete graph outputs match the previous analyzer on three immutable Git snapshots;
the complete original PR #68 plan is identical, including plan ID and obligations.
The committed implementation also has an equal complete graph and PR #70 source-head
plan under both analyzers, and its refreshed consumer fingerprint matches the Git tree.
Three-sample medians: cold graph 3.548 to 1.416 seconds, warm graph 3.575 to 0.017,
complete cold docs plan 7.658 to 2.628. These are local Windows measurements, not
hosted workflow speedup. The benchmark's first plan phase used an incorrect local helper
name and stopped; the corrected plan phase resumed from the completed graph measurements.
Both logs and the corrected standalone-capable script are retained.

Targeted: 41 PASS. Complete CI infrastructure: 141 PASS. Documentation/governance:
93 PASS. Repository validation: 186/0/0. Critical analyzer: 410/410 statements and
266/266 branches; no missing or excluded lines/branches. Existing full test inventory,
negative acceptance, 90/95/90 and changed 100/100 obligations remain unchanged.
Hosted dual-Python full bootstrap, impact coverage and independent witness are required
on the final pushed head. Cross-owner review remains outstanding; no merge was performed.

The recorder was initialized before implementation. Its live Python object was not
persisted across tool processes; finalization restores its state from the existing index
and four ledger events, retaining those events and their original hashes. Native capture
gaps stay explicit. Earlier sealed archives remain unchanged.
