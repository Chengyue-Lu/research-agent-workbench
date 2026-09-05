# CHK-0006 — Agent Trace v0.1 archive remediation

- tested implementation ref: `e560dbcd6374c5719ba807383ad5578d703177ca`
- scope: `work/M14-001/A-20260905-001/**`
- initial command: `PYTHONPATH=src python -m research_workbench trace validate --attempt work/M14-001/A-20260905-001 --root .`
- initial result: `BLOCK`

The initial Attempt Archive followed the lightweight narrative example in `docs/templates/TASK_WORKLOG.md`, but that example does not satisfy the accepted Agent Trace v0.1 machine Schemas. The first validation therefore reported missing Index identities/status fields, invalid message envelopes and event shapes, non-closed file references, and missing capture projections.

The archive was migrated without changing product code or any Schema:

- `ACTORS.yaml` now binds Task, revision, Attempt, and typed actors;
- every visible transfer uses the v0.1 YAML-envelope plus JSON-body form and is independently hash-pinned;
- the event ledger records lifecycle, one capture event per message, and explicit message/event/tool-result gaps;
- `INDEX.yaml` uses only accepted v0.1 fields and exact file references;
- the Attempt is `safe-paused`, `frozen`, and honestly `gapped`, so retained capture warnings do not masquerade as completion evidence.

The raw output of the initial failing run was not durably archived and is declared by `EVT-0023`; this check preserves the result and remediation basis without claiming the missing stream was captured.
