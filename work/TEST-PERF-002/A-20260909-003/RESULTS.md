# Accepted proof implementation repair

TEST-PERF-002 revision 19; owner Chengyue-Lu; cross-owner let778750-cpu; R2.
Implementation `54f752942f3f0f66afa4b42d1444834f94322547` on base `bdbac11a0c9a17fa221f8cc8bdd522c1bf4f9087`.

PR 67 review PRR_kwDOT2gtDc8AAAABMuNNww identified same-ID assertion weakening:
candidate source remains within a local edit domain while candidate proof stops
testing that source. Both the local contract and deterministic mixed-module
substitution retained their narrower suites. Two Git regressions fail before repair.

The planner now derives evidence modules from behavioral and proof test lists,
group/global positive and negative IDs, and applicable critical acceptance mappings.
Their Git blob/mode identity must match the accepted fingerprint anchor. Drift
restores ordinary behavioral and proof consumer closure and complete contract test
modules. Deterministic substitutions independently require exact-base module identity.
Candidate fingerprint updates cannot accept their own changes; separately accepted
evidence plus refreshed contract/fingerprint permits later bounded source-only use.

Four added regression methods include eight evidence-source cases, comment-only byte
drift, unchanged IDs with actually weakened assertions, unchanged-proof source faults,
base re-admission and deterministic full-module restoration. [Focused results](checks/summary.json)
record 119 passing tests, critical 95/90 and all changed statements/outgoing
branches covered. Documentation: 9 passing tests; local governance PASS.
[Actual-subject plan replays](checks/real-plans.json) retain focused + impact and
only the Claim/Projection contract suite for source-only edits with unchanged proof.
These isolated Git objects measure selection, not new execution or hosted timings.
[Review snapshots](checks/reviews.json)
also retain the cross-owner initialization-result applicability note, now documented.

The implementation leaves independent obligations, global 90%, critical 95/90,
negative acceptance and fixed aggregate identities intact. Fresh final-head hosted
dual-Python CI and pinned witness are required after the archive commit. Old-head
approval and historical performance measurements do not validate this new head.
Current hosted receipts and renewed cross-owner request will be linked on PR 67.
Log line endings are normalized to LF and terminal blank lines removed before evidence hashing. The first local
attempt with raw Windows log endings remains preserved locally and is not published.
