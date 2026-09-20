# CI follow-up inventory — 2026-09-20

Owner: Chengyue-Lu; Audit ID: TEST-PERF-002; [Issue #87](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87).
Accepted baseline for this inventory: `171d4654f88e926f239cdf25bc8168109b81f391`.

The current work covers PR #91 review readiness, PR #92 acceptance, confirmed CI
repairs, and the unfinished cost experiments below. Each executable change uses an
isolated branch with its own evidence. Production acceptance remains separate from
an offline proposal, local experiment, or Draft PR.

## Accepted foundation and current review

PR #85 is already merged. Its planner, typed-input, contract-shadow and consumer-record
implementation blobs match this accepted baseline. Nine older CI worktrees were
checked against actual accepted blobs and patches; their pre-squash ancestor commits
are not new work. None of those nine worktrees was modified by the inventory.

[PR #91](https://github.com/Chengyue-Lu/research-agent-workbench/pull/91) was changed
to Ready for review at `09c6cb1c82680233c369014e0831874b6702d3b7` after all required
checks passed. Cross-owner review remains requested. [PR #92](https://github.com/Chengyue-Lu/research-agent-workbench/pull/92)
at `4119f8b2d8e1e64a0afead138d13061e2d89e996` has complete successful CI, including
both fixed Python aggregates. It retains its dependency acceptance, rebase and
final review requirements. These are snapshots, not approval of future heads.

## Work and acceptance boundaries

| Priority / item | Current evidence and next action | Acceptance boundary |
| --- | --- | --- |
| P0: authority anchor | Implemented on `fix/ci-policy-authority-anchor`; recover an unchanged authority epoch across diagnostic metadata edits. Current-base leaf replays and adversarial histories verify the result. | Preserve new/changed consumers, proof drift, independent FULL witness and all quality floors; separate production review. |
| P0: typed diagnostic inputs | `domain-model.json` and archived metadata have known conservative fallback costs. Start with one named input and its actual readers, schemas, references and membership. | Diagnostic replay first; no suffix-wide or directory-wide exemption. |
| P0: early impact feasibility | Archived executable evidence previously failed impact after a long successful behavioral run. Audit which missing subjects, selectors and measurement inputs can be reported earlier. | Static preflight cannot claim actual coverage success or alter fixture order. |
| P0: 2B acceptance | Continue PR #91/#92 review and exact-head integration evidence. Current #92 B1425/C1399/C−B0 all pass. | Cross-owner acceptance; dependency integration followed by revalidation; no automatic merge. |
| P1: Git fixture setup | Port only the old clone/config optimization onto `perf/ci-fixture-clone-config`; verify real local config, LF, independent objects and all existing scenarios. | Test setup only; retain `--no-hardlinks`, fixture isolation and all behavioral tests. Hosted savings need measurement. |
| P1: fresh-read/Git overhead | Old local candidates have evidence for fresh lstat and batched exact-commit validation. Split them before rebasing and repeating relevant checks. | Resource implementation needs its owner; planner changes retain selection-authority FULL and witness obligations. No mutable-path success cache. |
| P1: workstream document reduction | One local complete pair reduced 325 to 252 cases. Prepare the independent exclusion witness after the 2A/2B dependency is accepted. | Closed inputs/environment, rollback and at least three fresh hosted pairs before any 2C activation. |
| P2: YAML parsing | A local candidate preserved values and failure behavior, but its cold Skill sample regressed 3.37%. Diagnose cold/duplicate load and actual memory cost first. | Fresh bytes on every call; isolated returned values; explain the cold regression before promotion. |
| P2: input diagnostics | Coverage contexts and invocation capsules have local evidence. Select an expensive consumer before extending the experiment. | Observed contexts do not prove absent dependencies; preserve original ordered runner and opaque inputs. |
| P2: fixture boundary | Old local extraction preserved 37 execution/replay cases and one real failing control. Rebase the minimal helper change for owner review. | Fixture/helper changes retain their own broad consumers; extraction itself grants no exclusion. |
| P2: identical CI reuse | A dormant comparator exists, but old hosted runs lack trusted environment attestation. Prepare a producer-only evidence capture experiment. | Authenticated run/job/artifact and full environment/command binding before reuse; required fresh integration stays fresh. |
| P2: full-suite hotspots | Rank current receipt costs and hand off business-specific work to its owner. H3/H4 internal changes remain with the M5 owner. | No complete test has been proved redundant; retain distinct faults, lifecycle and checkpoint evidence. |

The anchor and fixture slices can proceed independently now. Typed-input and early
feasibility work can begin as diagnostic audits. Fresh-read changes, YAML caching,
new exclusion authority and result reuse retain the prerequisites in the table;
old local passing numbers are not current-base or hosted proof.

## Measurement discipline

The current-base provider replay recovers the correct historical anchor while its
new/changed consumer closure still selects 95 modules. This establishes why the
anchor repair alone must not be advertised as a CI speedup. Remaining propagation
requires consumer-specific evidence.

PR #92's current hosted coverage job took 27m41s, with 1425 unique executions. Its
raw receipts distinguish suite execution, quality enforcement, smoke and job wall
time. Local setup process counts and old branch measurements are separate facts.

Global 90%, critical 95/90, changed 100/100, positive/negative evidence, ordered B then
C minus B, independent selection witness and full fresh integration baselines stay
in force. Each follow-up records its exact base/head, actual checks, remaining
uncertainty and human acceptance state in its PR and Issue #87.
