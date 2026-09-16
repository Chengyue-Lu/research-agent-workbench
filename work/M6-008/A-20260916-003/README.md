# M6-008 terminal eligibility review evidence

This archive binds implementation `48ba0e6ce9d70ea5f8c659188a722f76a46742b1` and
[review thread 4021866705](https://github.com/Chengyue-Lu/research-agent-workbench/pull/75#discussion_r4021866705).
The branch integrates accepted `develop@2d5af1b` through `07de6e6`; prior evidence commits remain intact.
[proof.json](proof.json) records exact source, envelope and receipt pins.

The five recorded local synthetic sessions cover:

| Case | Observed status | Provider calls |
| --- | --- | --- |
| A1 successful final response | completed | 1 |
| A2 Tool loop and final response | completed | 2 |
| A2 Tool result at the turn limit, without a final Provider response | post-call-failed | 1 |
| A1 reaches the frozen time limit after a response | post-call-failed | 1 |
| A1 preflight binding drift | preflight-blocked | 0 |

Each case passes a fresh-process file replay that forbids transport/Provider/Tool reruns and process launches.
`task_completion=false` throughout. Fixture clocks are deterministic test inputs, not historical external clock authentication.
These are transport engineering checks, not live conformance, scientific acceptance or authority to run M5.

[transport-proof.zip](transport-proof.zip) contains exact case files, checker snapshots, generation/replay helpers,
the review, retained logs and delayed development Trace. [bundle-manifest.json](bundle-manifest.json) pins all ZIP members.
From the installed repository test environment, choose a fresh extraction directory:

```text
python -m zipfile -e work/M6-008/A-20260916-003/transport-proof.zip .rwb/m6-008/terminal-replay
python .rwb/m6-008/terminal-replay/verify.py --schema-root schemas
```

`verify.py` reads existing files and forbids importing recorded case/checker source. `generate.py --output <fresh-directory>`
creates new synthetic cases using the four retained logs named in its local input directory; generation is separate from replay.
Python members are archived case data or local proof helpers, outside application sources.

- `terminal-red.log`: old replay wrongly accepted 10 mutations across three test methods: one unexecuted final Tool,
  elapsed at/above the deadline, and seven non-success finish reasons. The STOP/within-budget control passed.
  All mutants passed generic Trace validation and had every enclosing pin recomputed.
- `end-clock-red.log`: a real session return moved the test clock to the deadline; the old producer still reported completed.
- `terminal-green.log`: seven focused checks passed after repair, including preserving real turn-limit and timeout failures.
- `focused-coverage.log`: all 45 M6 tests passed; the three modules have 100% line/branch coverage (582 statements, 120 branches).

[trace-validation.json](trace-validation.json) reports no BLOCK and preserves `TRACE-CAPTURE-DELAYED`.
The development Trace is an explicitly incomplete export, with missing original reads, edits, command setup/timing and Provider messages.
Its `safe-paused` status describes capture completeness; the five case Traces independently retain their actual runtime outcomes.
Prior `A-20260916-001/002` archive bytes are unchanged. Final-head CI and human review remain bound on PR75.
M11/Gate B acceptance comes from PR82; M6 remains an unaccepted candidate and M5-007 still waits for M6 DONE.
