# PR89 H3 dispatch deadline repair

Task: M5-007. Owner: Chengyue-Lu. Execution interface reviewer: let778750-cpu. Risk: R2.
No delegation. On 2026-09-18 the user authorized fixing PR89 review comments and pushing to the
same PR, without waiting for hosted CI. Entry head: `4b3101a7aae10894bbca38facff9f32f68a74b92`;
observed develop: `51dc3ab477f21f18ac3829bf553b5b779d49a4fe`.

## Review and scope

[P2 review](https://github.com/Chengyue-Lu/research-agent-workbench/pull/89#discussion_r4043700923)
demonstrated that time spent between M11 slices could exhaust the whole-arm deadline while a later
Driver still ran. The repair covers Evaluation execution/replay, its tests, the existing Host dispatch
boundary, and the associated workstream records. The read set includes those modules and their
direct fixtures, receipt consumers, repository verification tooling and governance guidance.

The optional trusted Host guard runs after all Host preflight checks. Only an exact True permits
dispatch; false or other values produce a zero-call blocked report, and guard exceptions propagate.
It cannot override Host rejection or select a new binding. This narrow seam is necessary to include
Host preparation time; an Evaluation-only check before calling the Host would leave that gap open.
Runtime ownership, frozen View constraints and Human authority remain with their existing owners.

Harness records per-slice dispatch observations in its pre-acceptance Attempt format and independently
replays them against the Protocol budget and retained Host intervals. Each arm uses its first Host
start, including preparation/replay gaps before later calls. Existing receipt and Host schemas remain
unchanged. Baseline transport retains its existing budget enforcement.

## Evidence

Local verification outputs and candidate source hashes are in [verification.json](verification.json):

- [H3/Host](focused.log): 35 PASS in 578.729 seconds under branch coverage.
- Both Harness modules: 100% line and branch coverage. All three changed source files have no
  uncovered changed lines or branches relative to develop. The Host whole-module statistics are
  from this focused subset; they do not establish repository coverage thresholds.
- [M11 Core/Skill closeout](closeout.log): 56 PASS; [documentation/Schema/policy](contracts.log): 37 PASS.
- [Repository validation](repository.log): 186 checked, zero errors/warnings.
- [Package smoke](package.json): direct wheel and sdist-wheel, four installation probes PASS;
  runtime resources are identical.

Hosted CI is left to run asynchronously under the user's instruction. M5-007 remains IN_PROGRESS;
H4/H5 and the M5-008 live Gate retain their previous scope. The PR is not merged by this repair.

This is a partial review-repair record. Initial tool transcripts and native event timestamps were not
fully captured; that capture gap is retained explicitly. Logs and hashes attest only the recorded
local checks, not complete conversation capture or R2 acceptance. Earlier Attempt archives remain frozen.
