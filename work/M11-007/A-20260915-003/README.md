# M11-007 implementation evidence

This attempt records the PR81 review repair at commit `e1022d408c805aefb81e9177020064fe85e0ebc3`.
It contains four synthetic vertical cases and independent, isolated-process Receipt replay.
`checks/vertical-proof.json` binds source, input, output, checker and replay bytes.
Run `python -I replay.py <receipt-relative-path> <receipt-sha256> <case-project-root>`
using an installed package built from the pinned implementation. Replay does not use Provider/Tool.

Runtime fixture clocks are deterministic labels; generation time is recorded separately.
The development Trace is a delayed, incomplete export of retained tool responses. Its capture-gap
records missing original argv/setup/edits/provider commentary, export-time timestamps and local-path
placeholders. The development Attempt is safe-paused because its original capture is incomplete.
The runtime synthetic traces separately record use-boundary facts during execution.

Review regression and coverage logs bind the repaired implementation. Final exact-head
compatibility/coverage/package/repository/governance CI
and owner reviews are bound on the implementation PR. Gate B remains UNSATISFIED.
