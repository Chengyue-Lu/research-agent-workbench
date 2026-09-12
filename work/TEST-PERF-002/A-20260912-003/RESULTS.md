# Preserve full behavioral fixture and ordering semantics

TEST-PERF-002 revision 26; Chengyue-Lu; R2; source `b99bb7eacf024d40d12191a2a02841339b2b825c`.

PR #70 review 5182240960 identified a real semantic gap at `8c09f6c`: separately
executing C and B minus C can hide shared class/module state failures. Both old-head
counterexamples fail direct full but pass the split producers and their receipt join.
The old result establishes complete behavioral TestCase identity coverage reconstructed
from two producers, not historical single-process full equivalence. Its hosted duration
observations remain historical evidence.

The repaired Python 3.11 producer runs the original ordered B suite to completion, then
loads and runs C minus B. B's suite hierarchy and fixture lifecycle remain intact. The
second phase starts fresh fixture tracking on the same result; a failed B body or teardown
cannot be healed. Each canonical B case executes once. Coverage data measures B union C,
the behavioral projection contains only B, and the coverage projection supplies C.
Coverage none executes B once without instrumentation. Python 3.13 runs independently.

Schema 1.2 receipts bind exact plan/target/Python, inventories, actual order, counts,
outcomes, fixture events and checkpoints. Projections reference the raw digest; alias
overlaps preserve the actual B execution ID. Legacy split receipts, missing/failed evidence,
reordered cases and forged identities are rejected. Fixed aggregate identities and
90/95/90, changed 100/100, exclusions and mandatory negative acceptance are preserved.

Local checks:

- 44 targeted checks PASS, including real Git-bound worker processes for successful
  projection, delayed coverage-only import, coverage-only behavioral exclusion, stale
  target rejection, and both class/module mutation failures matching direct full.
- 155 runner, CI, coverage-policy, documentation and governance checks PASS.
- 17 final runner checks PASS; 201 executable
  lines mapped to this repair and their outgoing branches have local 100/100 coverage.
  This targeted report is not a repository coverage claim.
- Initial harness checks found an outdated workflow step label and a repeated identical
  fixture Git commit. Both were corrected; original failing logs and successful reruns
  are retained.

The frozen source plan verifies full behavior plus impact and repository coverage.
Fresh archived-head hosted dual-Python full, coverage, package/repository smoke, governance,
fixed aggregates and pinned selection witness remain pending at this archive boundary.
The witness proves selection only. Cross-owner acceptance remains required; no merge.

The recorder was created before implementation and restored from its live pickle.
Native event/message export gaps remain explicit; earlier sealed Attempts are unchanged.
Other performance directions recorded on Issue #48 remain unstarted in this repair.
