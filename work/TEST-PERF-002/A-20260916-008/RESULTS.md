# Shared input facts and source-witness evidence

TEST-PERF-002; owner Chengyue-Lu; R2; A-20260916-008.
User request: 继续测试更多可能的分支，然后进一步推进整改。

Implementation producer: `c713f999d7e39900966f6e59156377fc0dc3ec93`.
Accepted base observed: `0d4a1d00a4c32ca9b822df6482a95920e7c21b1b`.
The before producer is `980bb99947a52a812fb691334e8ad6106171b9d5` in a clean isolated checkout.
Historical targets equal their original heads; original Git facts and PR metadata are retained.
No original branch or primary develop checkout was modified.

## Results

- Twelve cases (#65/#68/#71/#73/#74/#75/#77/#78/#80/#81/#82/#84) PASS. Every previous selection
  field and 16 execution/binding fields are equal before/after, including exact test selectors,
  impact evidence, changed coordinates, coverage obligations and smokes. The new evidence adds
  one deterministic path per affected source; it does not enumerate alternative paths.
- Unknown input records across the corpus decrease from 112 to 4 (not a unique file count).
  Three transport-proof ZIPs and LICENSE remain unresolved. Largest plan: 443,764 bytes,
  below the existing independent witness 4 MiB input limit.
- Local suites: 72 PASS / 24.268 s for input facts, shadow and dependencies; 137 PASS / 278.204 s
  for existing planner, checker, witness, coverage-policy and documentation regressions.
  The sum is 209 distinct tests, not a full-suite result. Instrumented coverage records the
  72-test run; the other suite is a separate uninstrumented regression run.
- Changed modules all reach 100% lines and branches with zero excluded lines: input facts
  80/80 statements and 46/46 branches; shadow 120/120 and 36/36; selector 503/503 and 322/322.
  These are module results, not repository-wide coverage. Existing quality thresholds are unchanged.
- Exact implementation-head plan verification and governance PASS. Raw Git and checkout source
  hashes match. Full behavioral plus impact/repository coverage remain required for this authority
  change. The evidence-only commit and hosted merge target require separate final-head checks.

The twelve new cases are planner/report comparisons, not twelve behavioral executions or paired
CI timing experiments. The prior actual #65 five-module execution (134 PASS / 63.548 s) remains
in [A-20260916-007](../A-20260916-007/RESULTS.md). No reduction is activated; #84 still selects
91/92 modules. Prior-head green CI does not validate this new head.

## Corrected smoke diagnosis and remaining work

The earlier test-chain explanation did not identify actual smoke predicate source paths.
For #80, package has `release_source_ci.py → cli.py` via opaque execution; repository has
`ci.yml → validation/*` via unbounded resource readers, directly or via shared helpers.
A runner-only contract cannot close both obligations. The original frozen attempt remains as
historical evidence; the new source witnesses refine the next contract work. A static path is
not a proof of safe exclusion. CLI invocation, validation input instances, unknown containers
and alternative paths need reviewed contracts before any scope reduction is activated.

See the [current design](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/SHADOW_V2.md),
[comparison](checks/corpus-comparison.json), [before matrix](checks/corpus-before/matrix.json),
[after matrix](checks/corpus-after/matrix.json), [module coverage](checks/v2-coverage.json),
[implementation preflight](checks/v2-implementation/preflight-summary.json),
[manifest](checks/evidence-manifest.json) and [Trace validation](checks/trace-validation.json).
Raw plans/reports, PR metadata and producer/reproduction snapshots are retained under checks.
Python snapshots have the non-executable `.py.txt` suffix. Evidence bytes are copied exactly.

Trace has an explicit retrospective capture-gap warning for exchanges not streamed during
exploration. Retained outputs are factual; no complete runtime-event capture is claimed.
This archive is not human acceptance, merge authorization or release authority.
