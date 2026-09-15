# M6-008 takeover evidence

This archive binds the implementation at `b04957223d20d59904309fe9d7de70c7b074ac4c`.
[proof.json](proof.json) records the actual source hashes and the exact envelope/receipt references.
The A1 and A2 cases use a local scripted Provider; A2 executes one file-bound read-only function.
Both cases completed and passed fresh-process file replay with Provider, Tool and process reruns
forbidden. They establish transport behavior, with `task_completion=false`.

The complete original files are stored in [transport-proof.zip](transport-proof.zip).
[bundle-manifest.json](bundle-manifest.json) records its SHA-256 and all 163 member hashes;
the bundle was reopened and every member verified against the original bytes. Python members
are archived case data and local proof helpers, outside the application source tree.
From an installed repository environment, extract into a fresh directory and replay:

```text
python -m zipfile -e work/M6-008/A-20260916-001/transport-proof.zip .rwb/m6-008/replay
python .rwb/m6-008/replay/verify.py
```

The bundled `verify.py` does not generate a new case. To generate fresh synthetic cases and a new
development export, run the bundled `generate.py` with `PYTHONPATH=.` and `--output` pointing to
a fresh directory. Generation also consumes the four retained local logs named in the script;
it does not call a live or paid Provider. The frozen fixture clock is a deterministic test label;
`generated_at` records the actual generation time separately.

[development-trace](development-trace/INDEX.yaml) is a delayed, incomplete export of retained
test outputs. It explicitly declares missing initial reads, edits, command setup, event timing,
partial tool results and original Provider messages. Its lifecycle is `safe-paused` because
capture is incomplete. Local checkout paths in retained output are replaced with `<checkout>`.
The synthetic runtime traces under `cases/` are separate complete execution records.

[trace-validation.json](trace-validation.json) reports no BLOCK and retains the capture-gap warning.
The initial report export encountered a dataclass serialization error after both cases and Trace
sealing had succeeded; only report serialization was repaired, without rerunning those cases.

The red regression log records nine rehashed counterexamples incorrectly accepted by the original
candidate. The subsequent logs record the repairs and 31 passing M6 tests across the final focused
coverage run and two added edge cases. Exact-head full/coverage/package/repository/governance checks
and human acceptance remain bound on PR #75. These files do not close M5 or Skill gates.
