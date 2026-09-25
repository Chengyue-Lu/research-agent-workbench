# Checkout-sensitive Attempt consumer experiment

Owner Chengyue-Lu; TEST-PERF-002; R2; required Skills [].
Accepted base `eb49093d6d89515c3e66bec29ee85e7a95bb9ce7`; implementation `4793e81d4963f291ae956d33464f363b6af68468`.

The existing Trace validator executes on a caller-selected generated Attempt.
Real fresh Git checkouts reproduce valid LF, whitespace-only, CRLF hash failure,
repaired LF, nested/outside controls and missing/renamed references. Unknown
attribute semantics stop before checkout. CRLF produces only the expected ledger
hash BLOCK; repaired data and INDEX preserve the original Git blob and digest.
No original test, production assertion or policy was modified.

Both Python 3.11 and 3.13 passed 10 related tests: 8 new named regressions and
2 existing hash/ref negatives. Initial 10/10 results are retained separately;
independent review then found that final probe status was not asserted by unittest.
The added overall-status assertion and the final 10/10 runs are separately bound.
Review also corrected repair freshness, canonical IDs, Git isolation and CLI
causal checks before the first actual execution. No full CI was run locally.

Three sequential fresh Python 3.11 CLI processes all passed, with total wall times
13.831 / 12.952 / 12.896 seconds. Each includes fixture creation, all scenario
checkouts and observations. With 1 / 10 / 100 additional unrelated Attempt copies,
the same selected reader's median call times were 0.370 / 0.371 / 0.350 seconds;
setup medians were 0.437 / 0.502 / 0.849 seconds. These are warm calls inside each
fresh process, not isolated cold starts. They show results and measured costs
for this invocation only, not absence of reads, safe exclusions or CI speedup.

[Summary](checks/summary.json), [raw archive](checks/raw-evidence.zip) and
[manifest](checks/manifest.json) retain commands, source identities, actual risks,
original failure findings, exact small Git snapshot trees and replay bundles.
Source hashes match the implementation Git blobs. This does not make local
results hosted target receipts. Schema-catalog and directory-membership closure,
historical production call mappings, independent witness and B/C acceptance
remain required before production reduction. Final-head validation and hosted
checks retain their subsequent identities.

Trace capture is partial: this record begins at evidence freeze. Earlier visible
tool/inter-agent messages were not a complete continuously captured event stream;
the written design/review findings are preserved without claiming otherwise.
Publication and subsequent checks occur after this seal and remain separate.
