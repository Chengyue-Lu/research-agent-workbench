# M14-005 cutover preparation attempt

PR #108 was cross-owner approved and squash-merged to `develop@318904977c0492322e1bffe3e28532bc712e321b`.
Its reviewed head and merged source have the same Git tree. Protected push CI run
`36662594652` passed; a clean exact-source live source-CI attestation passed.

This R2 slice makes both release preflight matrix jobs run on every main-bound PR so the
first-step guard fails non-release heads. It prepares, but does not apply, a single main
hard-ruleset required-check swap. The preparer checks protected refs, both source-CI
observations, four exact-ref rulesets and their effective rules. It preserves the
separate main review requirement and develop protections. The current remote rulesets,
dormant governance policy and main branch remain unchanged.

The live read-only helper matched the current remote state and produced a cutover payload
hash. This is preparation evidence, not a real first-main hosted run or an activation
decision. The release candidate, hosted observation, fresh cutover readback, actual
ruleset update, final PR merge approval and tag/artifact closure remain separate gates.

The visible tool-call stream was not captured exhaustively. This archive records a
capture gap and retains decisive evidence rather than reconstructing missing events.
The formal Trace Attempt is safe-paused with a `TRACE-CAPTURE-DELAYED` warning; the
implementation proposal and acceptance status are tracked separately by the PR.
