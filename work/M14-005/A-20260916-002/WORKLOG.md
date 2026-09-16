# CI fixture follow-up

Repair checkpoint: 81d46bf4893518759da9b1ca3b128acd1c84c4ec; baseline: b041aeef8c32b74bc4399f90bf3fb49fbbb4fc22; owner: Chengyue-Lu.
The hosted coverage job in run 35086048928 executed 1346 tests but failed during two
WitnessTests temporary-directory cleanups with Directory not empty. Python 3.13 passed all 1346.
The failure is consistent with a detached Git writer racing cleanup. A local Git trace showed
three automatic detached maintenance launches before repair and zero after repair in the two
affected cases. The cleanup error itself was not reproduced locally; both cases passed before
and after. The complete witness module passes 10 tests after repair.

The fixture now sets repository-local maintenance.auto=false and gc.auto=0 before its first
commit. Strict cleanup remains active. Production selection_witness.py is unchanged.
Git documents these settings at https://git-scm.com/docs/git-config and https://git-scm.com/docs/git-gc.

Final-head hosted full/coverage/package/governance evidence belongs to PR 80. This checkpoint
does not claim a successful final CI run. Earlier frozen Attempts remain unchanged. The plan
in A-20260916-001 remains: current-candidate R2 acceptance and authorized integration, then
actual protected develop push plus live attest, then release-only checks/policy/cutover preparation.
Final release PR/tag require separate named approval.

Material native test receipts and the failed cleanup excerpt are retained. The diagnosis records
trace hashes and selected maintenance argv; exhaustive native event capture was unavailable.
