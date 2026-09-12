# Parent-path follow-up

TEST-PERF-002 revision 22; source `c60a3ad72eec527e5c8ef7652e12be1866818d08`; Chengyue-Lu; R2.

The final audit adds canonical parent-segment resolution to fixed roots and retains
ambiguity after leaving the repository. This prevents an internal `docs/../tests`
resource from disappearing from the graph. The added regression covers both in-root
resolution and outside-root fallback.

Final targeted tests: 36 PASS. Analyzer: 381/381 statements, 254/254 branches.
The immutable PR #68 replay remains 10 modules / 261 baseline IDs, coverage none,
both smokes false. [Revision 21](../A-20260911-001/RESULTS.md) retains the broader audit,
package, repository and initial controls. The 135-test infrastructure log belongs to
source 0c4572e before this final parent-path adjustment; it is retained as supporting
evidence. The complete final-head dual-Python hosted bootstrap and independent
fixed-root witness remain required before cross-owner merge review.

Native capture gaps remain declared. The previous sealed archive is unchanged.
