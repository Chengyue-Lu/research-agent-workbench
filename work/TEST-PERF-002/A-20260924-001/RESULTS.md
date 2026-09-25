# Per-input propagation diagnostics

Owner Chengyue-Lu; Audit TEST-PERF-002; R2; required Skills [].
Accepted baseline `6cf80610cc2d3b4ebdeb9f47a840cd0ec1870bbf`; implementation `ada2309696ab3a65a7c546ecf30c067f4d56b977`.

The implementation retains the accepted execution plan and every quality obligation.
Input facts and graph observations remain non-authoritative. Both Python versions
passed 35 related cases; the changed script covered 151/151 lines and 44/44 branches.
Working-tree source hashes were compared with the implementation blobs; this does
not make these local checks hosted exact-target evidence.

The [summary](checks/summary.json) binds newly generated diagnostics to their original
Git inputs. Historical PR65/84 are new local replays, while PR90 observes its original
verified official plan. Accepted obligations and smoke/activation fields match before
and after. Isolated closures are not safe minimum sets or timing savings.

Independent review found unverified unclassified reasons and the wrong ancestor
selection for stale histories. Both were corrected with real Git regressions before
the successful test runs. Original findings and the follow-up remain in the
[raw evidence](checks/raw-evidence.zip), pinned by the [manifest](checks/manifest.json).
The initial Python3.13 loader failure, all timing observations and source snapshots
are preserved. Local diagnostic timings are not hosted performance acceptance.

Trace capture is partial: early implementation/tool messages were not recorded as a
complete live event stream. Evidence retention is recorded now; missing transmissions
are disclosed as capture gaps. Publication and future hosted checks occur after this
archive and keep their own identities. No merge or activation is authorized here.
