# M6-008 review repair evidence

This archive binds implementation commit `0877542a10a10900e872055ffb295d578b0a293f`
and [review comment 5685397753](https://github.com/Chengyue-Lu/research-agent-workbench/pull/75#issuecomment-5685397753).
[proof.json](proof.json) pins the producer sources, actual A1/A2 envelopes and receipts.
Both synthetic local sessions completed; A2 invoked its qualified read-only Tool once.
Fresh-process replay passed with transport, Provider and Tool reruns forbidden.
Every fact has an independent hash-pinned creation event; each Validation pins an archived checker source.
`task_completion` remains false. No live API, scientific acceptance or Gate closure is claimed.

[transport-proof.zip](transport-proof.zip) contains the cases, generator, cold replay helper,
raw test outputs and delayed development Trace. [bundle-manifest.json](bundle-manifest.json)
pins every member and the ZIP itself. Python members are archived case/checker data and local proof helpers.
From the repository's installed test environment, choose a fresh extraction directory:

```text
python -m zipfile -e work/M6-008/A-20260916-002/transport-proof.zip .rwb/m6-008/review-replay
python .rwb/m6-008/review-replay/verify.py --schema-root schemas
```

The helper only reads recorded files. It rejects importing any source under the recorded cases,
including Tool implementations and checker snapshots. Generation is a separate command, `generate.py
--output <fresh-directory>`, requiring the six retained logs named by the script in its documented local input directory.
The fixture clock is a deterministic label; `generated_at` records the actual export time.

The retained logs distinguish the evidence:

- `availability-red.log`: the old implementation wrongly allowed all three expiry scenarios.
- `creation-red.log`: a before fact was created after its response; generic Trace passed, but old M6 replay wrongly accepted it.
- `replay-red.log`: checker path/hash mutations were wrongly accepted. Its first creation-fixture attempt failed generic Trace setup and is not the creation-order counterexample; that setup was repaired in `creation-red.log`.
- `regression-green-2.log`: the first 12 repaired regression tests passed.
- `focused-coverage.log`: 37 M6 tests passed; a checker-byte test was subsequently renamed without changing its assertions.
- `creation-pin-green.log`: the added creation path/hash/action mutation test passed, bringing the M6 suite to 38 tests. The same three source modules have cumulative 100% line/branch coverage (572 statements, 116 branches).

[trace-validation.json](trace-validation.json) reports no BLOCK and preserves the delayed-capture warning.
The development Trace declares missing initial reads, edits, setup, original event times and Provider messages;
its `safe-paused` lifecycle describes incomplete capture. The runtime case Traces are separate complete records.
The older `A-20260916-001` archive is unchanged and lacks this candidate's required creation/source evidence.
Final-head CI and human review remain on PR #75; this archive does not authorize merge or M5 execution.
