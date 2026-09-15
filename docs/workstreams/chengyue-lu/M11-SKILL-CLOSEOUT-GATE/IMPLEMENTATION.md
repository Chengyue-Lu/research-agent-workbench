# M11-007 implementation candidate

- Accepted definition: PR #76, `develop@0bebafd81f0116a8269c63ac97378038a1eb2a5d`.
- User authorization: continue M11-007 implementation in this session.
- Branch: `feature/m11-007-skill-closeout`; target: `develop`; risk: R2.
- Execution acceptance owner: 黄毅 (`let778750-cpu`).
- Proposal / Evaluation consumer owner: 路诚钺 (`Chengyue-Lu`).
- Agent role: bounded implementation; required Skills: []; delegation: false.

## Contract and scope

Add independently versioned Skill execution Host report, typed execution fact and Receipt contracts.
Reuse the existing Host and closeout invariants; retain published Core and legacy schemas and their replay.
The execution producer captures actual Projection / Supply / component bytes and identity at consumption.
The pre-use fact records consumed input identity only. A separate Core post-call fact records the
observed execution binding after Provider/Tool activity. Host preflight checks the already-selected
Skill closure before invoking the Driver. The Host preserves those observations and diagnoses drift. Closeout consumes
frozen Trace and independently reloads all exact references; it never creates missing execution facts.

The [PR81 review repair](REVIEW-REPAIR.md) records the two-stage timing, before-call closure check,
and single-read invariant. The earlier candidate archive remains immutable historical evidence.

Completed execution has exact requested/actual equality. Post-call failure retains corroborated actual
drift. Preflight-blocked execution has no actual facts or calls. Driver exception and incomplete capture
remain ineligible. Completion remains Action/Capability-slice-only, with `task_completion=false`.

Read scope: accepted M11-007 / Gate B definition, repository guidance and architecture, Runtime module,
Core closeout, Host/View/Bundle, Skill mapping, Trace and Schema implementations, M5 consumer contracts,
directly related fixtures/tests, coverage policy, package/resource and governance integration checks.

Write scope: execution closeout/Host exports and directly required Trace producer support; new versioned
schemas; related deterministic tests and coverage registrations; implementation documentation; M11-007
status/evidence, Gate B candidate pins and this workstream; `work/M11-007/` attempt evidence. M6-008 and
other Task definitions remain unchanged. Runtime selection, candidate/Evaluation/oracle access, admission,
Harness, real execution and release authority retain their accepted boundaries.

## Verification and acceptance

Deliver a synthetic Bundle → View → bounded Host → use-boundary Trace → Artifact/Validation → Receipt
→ independent file replay. Cover completed, failed drift and preflight-blocked; independent corruption,
missing-fact and subject-closure negatives; Core and legacy regression; current focused/full/coverage,
repository/package/governance checks. Reuse execution evidence according to the accepted CI plan.

Gate B remains UNSATISFIED while the candidate is implemented and reviewed. Implementation pins and
test/CI evidence are prepared for both named owners; no prior single-PR merge exception carries forward.

## Attempt evidence

The implementation attempt captures observable tool results from the scoped core-read stage onward.
Initial memory/governance reads, worktree creation and early commentary were not captured as original
Trace events. Any delayed export retains that gap; no original timestamps or hidden reasoning are inferred.

Implementation proceeds until the scoped candidate and validation are reviewable. Stop on a required
change to accepted Runtime ownership, published identities, read authority or Task semantics and raise
that concrete boundary for a separate decision.
