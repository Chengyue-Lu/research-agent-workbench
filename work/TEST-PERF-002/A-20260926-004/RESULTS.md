# Bounded diagnostic test contracts

Owner Chengyue-Lu; TEST-PERF-002; R2; Skills []. Base `5bf2227ca9b4d2f63f452e579185e7838028de78`;
implementation `005e942b192b024d4da9582838694fdc6082a57b`. The implementation reuses the existing accepted-base
function-body contract mechanism for consumer shadow, shadow pair and domain
audit. It preserves complete proof suites, authority anchors, fingerprints,
old/new consumers, evidence drift fallback and fixed quality obligations.

The new isolated minimum checker authenticates complete Git objects and exact
planner/helper sources before executing the accepted planner. It compares the
candidate against that minimum using external identities and metadata. Independent
review first found object-chain and graft weaknesses; the fixes and second review
are retained alongside the original findings. The checker is registered as selection
authority and critical95/90. Its new source measured187/187 statements and32/32
branches;17 related tests passed under each Python. Additional in-process path
measurements supplement the original real isolated CLI tests.

Three new planner tests cover27 real Git scenarios. Candidate-only contracts cannot
reduce their own plan; imports, calls, initialization, proof drift, missing anchors
and new consumers restore conservative obligations. The registration, coverage
policy and documentation check ran41 tests successfully under3.11. Existing
thresholds90/95/90, changed100/100 and exclusions are unchanged.

Under explicit **unaccepted synthetic bases**, the same-source old union1510
contracts to20,9,25. All three correct changes passed real ordered3.11 coverage
and impact checks and3.13 behavioral execution. Local producer times were about
34,13,39 seconds. The consumer/pair/domain files measured237/237+86/86,
125/125+42/42 and121/121+38/38. Each correct probe covered1/1 changed line and
0/0 outgoing changed arcs. These are local results, not a hosted speedup ratio.

Consumer union, percentage and route faults were detected. The original domain
count1-to2 mutation was missed by25 tests and impact coverage. That original
failure of detection remains in the raw archive. Explicit domain count assertions
now yield25PASS for the correct version and24PASS+1FAIL for that same Git fault
under both Python versions. Its exact original raw bytes also fail the new assertion
in fresh processes. A failed producer provides no successful impact projection.

The paired hosted harness passed an independent review and one reduced20-case
execution. It prepares identical non-policy source/test trees, authentic native
B/C/order/projections and quality evidence. Three fresh hosted pairs remain to be
executed; their timing scope excludes setup and smokes. Formal new-head CI and
post-acceptance official reduction each retain their own execution identity.

[Summary](checks/summary.json), [manifest](checks/manifest.json) and
[raw evidence](checks/raw-evidence.zip) preserve hashes, exact refs, commands,
failed attempts, faults, repairs and reviews. Older A001/A002/A003 are unchanged.
Trace capture begins at this freeze; gaps in prior tool/inter-agent events are
declared. Candidate checker pins do not establish human acceptance. No production
2C activation, cross-commit reuse, release or merge is claimed by this archive.
