# Component CI candidate: bounded local evidence

Owner Chengyue-Lu; TEST-PERF-002; R2; 2026-09-27.
User requested closing the previous CI work and adopting the latest Issue87 direction.
This candidate uses directory components, a baseline Python and short installed smoke.
Unknown ownership is visible; it does not recursively escalate to FULL.
The old production workflow, protected checks and release/source-CI contract are unchanged.

The source manifest binds the local candidate bytes, not a later hosted run.
The planner and smoke control tests have their own receipts. A fresh wheel and clean
environment were built successfully. The first smoke failed because the new probe
used the wrong SchemaValidationError attribute; its failure is preserved. After the
pointer correction, the same installed wheel passed all eight steps in 9.469 seconds.
Six runner controls, ten documentation checks and seven existing historical behavior
regressions passed: 23 tests, 6.084 seconds of test execution (6.444 seconds process wall).
Independent review closed import-root, mixed empty-module and Schema probe findings.

The smoke keeps timestamp positive/negative controls, real installed CLI/resources
and an offline project. Existing regressions retain deterministic hash, path/integrity,
permission denial, unapproved release, document dispatch and public CLI behavior.
No full suite, hosted speedup or platform/release equivalence is claimed.
Coverage is not collected here; diagnostic coverage and explicit checkpoints belong
to the proposed route. Required-check/source-CI activation remains separately reviewed.

[Summary](checks/summary.json), [manifest](checks/manifest.json), [raw evidence](checks/raw-evidence.zip).
