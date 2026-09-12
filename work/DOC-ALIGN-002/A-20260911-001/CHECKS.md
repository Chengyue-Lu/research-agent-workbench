# Local verification

- Documentation and governance unit checks: 93 PASS.
- Internal links were initially checked before INDEX.yaml existed: one failure; archive creation resolved it.
- Initial repository validation invocation omitted required paths and exited 2 without validating documents.
- Initial Trace serialization used unsupported message kind `result` for two final handoffs, producing four schema BLOCK findings. Before publication, both envelope/index kinds were corrected to `handoff`; message bodies and event order are unchanged.
- Source, Schema, Registry, tests, governance policy, TASKS, public first-contact surfaces and ADR0020 body are unchanged against the frozen base.
- M4 historical README body and Gate frozen mapping retain exact normalized Git bytes.
- Native capture is retrospective and incomplete. The remaining capture-gap warning is retained.

Exact-head PR CI and cross-owner review remain the delivery checks after commit/push.

Final local preparation: the first explicit-src repository check lacked generated `_runtime_pin` and stopped before validation. `build_backend.generate()` generated the existing Runtime catalog inside the isolated worktree; the corrected `python -m research_workbench validate examples registry --root .` passed: validated=186 errors=0 warnings=0. Trace validation now has zero BLOCK findings and one retained capture-gap warning.
