# M5-007 H4c implementation attempt

Date: 2026-09-27. Owner: 路诚钺 (`Chengyue-Lu`). Reviewer: 黄毅 (`let778750-cpu`). Risk: R2.
Agent: `codex-m5-h4c`; bounded repository implementation; Skills: [].
User authorization: implement H4c and publish a PR targeting develop; no merge.
Base: `97d3b3d3141419b34ad47e0f42d9f01d0dfbd535`; preparation: `3f90631dfa79dec9eaf5ba9ba937f1dfa079070b`.
Task: [M5-007 H4c packet](../../M5-007_H4C_PACKET.md), M5-007 remains IN_PROGRESS.

Read/write boundaries, budget and stop conditions are retained in TASK.md. No delegation or live execution.
Deliver method/observation/measurement associations and independently rebuilt paired analysis inputs;
retain failed/retry/unstarted Attempts, exact externally selected scope, missing statuses and comparison ceiling.
H5 final acceptance, live/case/admission Gates, research efficacy and release remain separate.

Validation evidence is being captured in this attempt; final source/evidence pins will be retained in verification.json.
Intake, patch operations and native calls before the logger were not a complete contemporaneous Agent Trace.
The capture-gap warning is retained explicitly; logs and delayed exports do not recover omitted events.

All numeric unit observations are manually authored synthetic contract fixtures. The real four-arm closure uses
unavailable/null for all 13 metrics because its integer rubric and archived execution do not establish the fixed
whole-arm measurements. No scientific measurement method or net-benefit claim has been accepted.


## Verification and interpretation

Implementation commit: `3447372`; positive same-process roundtrip hardening: `791f4d5`.
The production source and schemas are identical across these commits; the latter only adds an
independent successful validation assertion to the already tested positive fixture.

- [Focused final](evidence/focused-final.log): 24 PASS in 661.259 s, including real synthetic H3/H4a/H4b,
  cold H4c reconstruction with denied execution ports, and resigned comparison/result attacks.
- [Positive roundtrip](evidence/positive-roundtrip.log): changed test independently recompiled and
  validated in the measured process, 1 PASS in 20.140 s. Combined scoped coverage on the same
  production bytes: [222/222 statements and 52/52 branches](evidence/focused-coverage.json).
- [Changed implementation coverage](evidence/changed-coverage-results.json): no uncovered new
  executable lines/branches; both registration additions are constant members with no new executable statements.
  This is scoped evidence; older validator modules in the registration report are not globally covered by these tests.
- [Registration/contracts](evidence/registration.log): 85 PASS; [registration coverage](evidence/registration-coverage.log): 14 PASS;
  [H4b/Trace regression](evidence/review-regression.log): 20 PASS; [final docs](evidence/docs-final.log): 10 PASS.
- [Repository](evidence/repository.log): 186 checked / 0 errors / 0 warnings.
- [Package](evidence/package-results.json): four clean direct/sdist-wheel isolated/ordinary installs PASS,
  identical 154-resource / 106-schema closure, offline scaffold reconstruction matched; Python 3.11.16.
- [Candidate governance](evidence/governance-candidate.log): PASS, effective R2.
- [Local Git-bound CI plan](evidence/ci-plan-candidate.json): full behavior, impact+repository coverage,
  both smokes, no blocked reasons. This diagnostic plan is not a hosted execution receipt or full/global PASS.
  Full dual-Python behavior/global coverage is left to current hosted CI; no additional run was dispatched locally.

Diagnostic history is retained: first unit fixtures collided with exclusive paths and did not isolate the
already validated comparison schemas; the first real fixture omitted required private transport metadata.
Both were corrected before the final successful tests. First changed coverage missed the successful return
executed only in an unmeasured child; the positive roundtrip closed it. A local plan/results output basename
collided with logger metadata; exact command/exit records and logs survived, and distinct result names were
regenerated. Failed results remain diagnostic and are not counted as acceptance.

[Input pins](INPUTS.json) and verification.json bind source/evidence. Trace replay and explicit capture-gap
warning are retained; omitted original intake/patch/native messages/publication cannot be reconstructed.
H4c is an implementation candidate awaiting exact-head CI and cross-owner review. M5-007 remains
IN_PROGRESS; H5 retained vertical proof/overall acceptance and all live/research/release decisions remain open.

[Trace replay](trace-validation.json): no BLOCK; TRACE-CAPTURE-DELAYED warning retained.
[Source/evidence manifest](verification.json) binds this retained candidate proof.
The scoped .gitattributes LF rule preserves these byte pins on Windows and Unix checkouts.
