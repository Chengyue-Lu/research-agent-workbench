# M5-007 H4b implementation attempt

Date: 2026-09-21. Accountable owner: 路诚钺 (`Chengyue-Lu`).
Execution interface reviewer: 黄毅 (`let778750-cpu`). Risk: R2.
Agent: `codex-m5-h4b`; profile: bounded repository implementation; required Skills: [].

User authorization: implement H4b and publish a separate draft PR; PR90 remains awaiting review.
Dependency candidate: `b9ad97ebf256351dd5e1540d5e688087394d474d` (PR90).
Integration base: `develop@171d4654f88e926f239cdf25bc8168109b81f391`.
Branch: `feature/m5-007-harness-review`. H4a acceptance is not assumed.

Task snapshot: M5-007 remains IN_PROGRESS. Deliver the H4b slice of the
[H4 packet](../../M5-007_H4_PACKET.md): versioned bounded synthetic anonymous
packages, private source/projection mapping, externally named Human Review freeze,
and reveal only after all slots are frozen. Revalidate exact H4a evidence.
H4c/H5, real providers, efficacy, release and Task completion are outside this attempt.

Read set: AGENTS, documentation navigation/development/architecture, M5-007 Task,
H4 packet, H1-H4a evaluation code and directly related M6/M11 replay contracts,
schemas/tests/fixtures, document catalog and existing coverage/CI/governance hooks.
Write set: `evaluation/harness_review.py`, its new schemas/tests/fixtures, necessary
catalog/coverage registrations and candidate consumer pins, implementation/status
documentation and this attempt. Preserve all frozen older archives byte-for-byte.

Output contract: independently replayable H4b records and positive/negative tests,
local coverage/repository/package/governance proof, separate draft PR targeting
develop with PR90 dependency. No merge. Do not wait for hosted CI.
Budget: one H4b implementation slice; local targeted tests plus required checks;
no delegation, network execution or paid model calls.
Stop conditions: a required change to treatment, runtime ownership, Supply selection,
Human authority, Task acceptance or live execution permission must return to the owner.

Capture policy: preserve commands, observable validation outcomes and final artifacts;
do not capture secrets or hidden reasoning. Preparation reads and context recovery
were not captured as a complete Agent Trace. This is an explicit capture gap, never
represented as complete runtime evidence. Persist implementation validation logs and
hashes below; a work log does not substitute for omitted tool/event transcripts.

## Work log

- Verified clean PR90 candidate and current remote develop; created isolated worktree.
- No modification to PR90 or the primary local develop checkout.
- Implemented seven versioned records and independently replayed freeze/reveal APIs.
- H4b focused: 13 PASS in 182.172 s; new module 141/141 statements, 12/12 branches.
- H4a dependency regression: 2 PASS in 105.589 s (all arms/slices/retry and blocked/unstarted).
- Registration/Schema/Trace exporter/docs/coverage contracts: 53 PASS; CI consumer/shadow/docs: 31 PASS.
- Repository: 186 checked, 0 errors, 0 warnings. Package: four clean installation probes PASS;
  direct-wheel and sdist-wheel resources identical, including all seven new schemas.
- Both catalog registration edits have zero uncovered changed lines/branches. This is scoped
  coverage, not a claim of full-suite/global or hosted CI PASS.
- Initial unit fixture dates preceded the frozen case date; corrected synthetic clock constants
  before the final run. A local coverage-summary shell quoting error was rerun via a literal
  script. Neither diagnostic is represented as acceptance evidence.
- Implementation commit: `e700b6fff86565a0fefa927f02bd3b1f1a06959b`.
- [Source pins and verification manifest](verification.json) bind the retained local evidence.
- [H4b focused log](review-focused.log) and [coverage](review-focused-coverage.json);
  [H4a regression](review-dependency.log); [registration contracts](review-registration.log);
  [CI consumer contracts](review-ci-contracts.log); [repository](review-repository.log);
  [package](review-package.json); [governance](review-governance.log).
- An additional [20-test scoped run](review-ci-scoped.log) used the actual candidate CI coverage
  configuration. Its [coverage excerpt](review-ci-coverage-excerpt.json) shows H4b 141/141
  statements and 12/12 branches, plus the inherited frozen exporter 39/39 and 12/12.
  It does not replace the plan's full behavior and repository/global coverage obligations.
- [Trace replay](trace-validation.json): no BLOCK; the explicit `TRACE-CAPTURE-DELAYED`
  warning retains the missing intake/patch/native-message/publication events. Export timestamps
  are not original execution timestamps. No executable exporter was added to the archive.
- PR90 remains unchanged. Publish this candidate as a separate draft to develop, then wait for
  PR90 acceptance before rebasing and advancing review. Hosted CI is asynchronous.
