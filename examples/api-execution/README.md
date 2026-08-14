# Offline API-execution closeout fixtures

These directories are **static offline fixtures** for the K-API-2 Task-to-API
file closure (`M6-003`). Each one is a complete, hash-consistent closeout
chain produced by replaying a scripted offline provider through the real
compiler, `IsolatedApiSessionRunner`, and closeout transaction.

They are contract evidence only:

- No live provider was contacted; the scripted providers report a fixed
  `worker-model`.
- A passing validator proves structure, references, and recoverability —
  never scientific correctness.
- The `stale-input` path writes no files by design; it is proven by
  `tests/test_execution_e2e.py::test_stale_input_blocks_before_session_with_zero_writes`.

## Scenarios

| Directory | Session outcome | Chain |
|---|---|---|
| `completed/` | Tool round, then a schema-conforming structured result | 11 documents incl. the `evidence.yaml` research object and a `contract-satisfied` receipt claim gated on the deterministic check report |
| `tool-failed/` | Client tool rejected an undeclared path, model gave up | 10 documents, `failed` chain with tool failures retained in the handoff and receipt |
| `safe-paused/` | Hard token budget exceeded | 10 documents, `safe-paused` chain with a resumable main state |

Each scenario contains `work/EVID-001/<attempt-id>/` (attempt, handoff,
receipt, evidence or check report, transfer manifest and audit, two context
snapshots, skill assignment) plus `checkpoints/MS-*.yaml`, the recovery
entry point. A fresh main session recovers by running:

```powershell
rwb context resume-check examples/api-execution/completed/checkpoints/MS-*.yaml `
  --protocol examples/project-protocol.yaml --root .
```

## Regeneration

The chains pin real content hashes (source paper, skill package, checker
source `src/research_workbench/execution/checks.py`). When any pinned input
changes, regenerate from the repository root:

```powershell
python examples/api-execution/regenerate.py
```

`tests/test_api_execution_fixtures.py` fails with `REF-HASH-MISMATCH` until
the fixtures are regenerated.
