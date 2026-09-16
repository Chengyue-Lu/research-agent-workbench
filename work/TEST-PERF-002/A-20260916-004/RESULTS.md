# PR83 archive source identity correction

TEST-PERF-002 revision 32; Chengyue-Lu; R2. The user authorized repair of the latest
cross-owner review at `5d989f87abf0a84c57cd87587c526488d09a549a`.

The failure in CI run `35028593655` was independently reproduced using its original
plan, coverage and coverage-execution receipt: `impact module absent:
work/TEST-PERF-002/A-20260916-003/checks/compare_scope.py`.

The comparison producer is a frozen source snapshot, now stored as
`A-20260916-003/checks/compare_scope.py.txt`. Its bytes and SHA-256
`a444af83162de6ff29e206b915c7f95acc86f7825484f58ad73bdcc56fb1a768` are unchanged.
The corresponding INDEX reference is relocated with the same hash; all other
fields and recorded evidence remain unchanged. `checks/before-INDEX.yaml` retains
the prior INDEX. The original scratch-directory ROOT logic remains in the snapshot
as historical source, not a runnable archive entry point.

Validation checks every coverage module in the final candidate's plan, source
identity, changed coverage coordinates, archive integrity and PR governance. Older
coverage is used only to diagnose membership/source identity; its receipt is not
rebound to this candidate. Fresh hosted full behavioral execution, impact coverage,
required aggregate checks and the independent pinned witness are separate evidence.

Correction commit: `fbe3e1836e12f635dc91f2f18f0f78ecc3dd08da`. The local plan has
only `.github/scripts/ci_dependencies.py` and `.github/scripts/plan_ci.py` as impact
coverage modules; neither source changed from the failed candidate. All planned
modules are present in the diagnostic coverage input and have no missing changed
lines/branches. The ten documentation tests, relocated archive integrity and source-
head governance pass. After this correction archive is committed, the complete
candidate plan and every planned module are checked again before the single push.

No production selector/checker, coverage policy, quality floor, required Gate, M6
branch or primary develop checkout is changed. Cross-owner review remains required;
this correction grants no merge or release authority. Native capture gaps are retained.
