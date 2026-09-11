# M5-006 implementation work log

- Owner: 路诚钺 (`Chengyue-Lu`); Execution interface owner: 黄毅 (`let778750-cpu`).
- Task: M5-006; risk: R2; branch: `feature/m5-evaluation-protocol`.
- Starting base: `11c3b57dfbf8af0dc2587fc421d097e2544941c3`.
- Authorization: user requested implementation of the recorded [entry plan](ENTRY_PLAN.md).
- Input scope: accepted M5 Task/ADR/Gate and workstream, evaluation/Capability/Runtime contracts and their fixtures, repository validation/CI/governance integration.
- Write scope: M5 evaluation modules, new schemas/tests/fixtures, necessary validation/CLI/coverage integration, M5 implementation documentation and this workstream. Other worktrees remain independently owned.
- Execution: one Codex actor; no delegated agents, Provider experiments, release action or Human admission.
- Trace: local capture spool under `.rwb/m5-006/`; archived v0.1 records will disclose delayed capture, setup reads not captured in the spool, and any missing tool results. No hidden reasoning or secrets are retained.

## Progress

2026-09-11: fetched origin; base unchanged; only the prior entry-plan file was untracked. Verified current Snapshot, Bundle and View validators as reuse points. M11 Core requires `no-skill` Method disposition for non-Skill and `skill-need|mixed` for Skill: current executable A3/A4 paths therefore cannot honestly claim an exact Skill-only delta.

Implementation and validation evidence will be added by slice. No new Task is marked DONE by this initial record.

Implementation pass: added S1/S2 protocol and qualification, S3 pairwise comparison, S4 overlap, S5 pre-run overlay and S6 public verifier/CLI/Schema registration. Existing M5-003 and Skill Evaluation schemas remain unchanged. First focused runs: 11 protocol/qualification tests PASS; 13 overlap/comparison tests PASS. Complete synthetic A4 lineage and A3/A4 pairwise probes PASS, with the pairwise result correctly downgraded to `skill-bearing-package`. Broader regression/coverage is in progress; these probes are not live/admission evidence.

Integration audit: the first partial coverage invocation was stopped to tighten independently supplied case pins and View/Manifest binding checks. Its partial output is not acceptance evidence. Added per-invocation Protocol/Manifest/schema-result reuse with content-based keys and reference rechecks; returned cached documents are copied so caller mutation cannot poison subsequent validation. No cross-invocation trust cache is used. Full focused tests and targeted coverage will run after these changes.

First implementation commit: `a3dfed5d9610bd0c60f68a6fb7ed6c56e0f53df2`. Its source passed 52 focused tests under coverage (559.604 s): all seven new modules reached 100% line coverage; six reached 100% branch coverage and overlap reached 95.83%. Two uncaptured-admission branches were identified for additional tests. The complete A4/pairwise integration subset passed 15 tests (102.729 s), including a coherently rebuilt View with a substituted model version. Earlier integrated focused pass: 40/40 (268.611 s).

Repository validation: 186 validated / 0 errors / 0 warnings. Documentation and coverage-policy tests: 30 PASS. Portable package smoke: Python 3.11.16 and 3.13.15, direct wheel and sdist-to-wheel, isolated and normal imports, all eight combinations PASS; Runtime resource manifest hash `03677958839e4ecc77a8aba0bc8036c9bf1f6aec8d369ef09a2edb1d8bbc67d8`.

Final audit adds complete provider-interface I/O comparison and integer-safe count validation. The old-head full run was stopped while still passing observed tests because the implementation was about to change; it is not a completed full-suite result. Final acceptance will use the revised head and a forced full CI plan retaining both impact and repository coverage obligations. The ordinary current plan selected focused + impact with no blocked reasons; no threshold or CI authority was weakened.

Trace export was probed separately: an initial invalid stream/scope encoding was corrected in the local export adapter; the corrected probe has no BLOCK and retains `TRACE-CAPTURE-DELAYED`. The formal archive will preserve actual captured payloads and evidence with their original diagnostic/commit boundaries, not reconstruct missing history.

Final delta checks: all three targeted tests PASS (58.290 s), covering uncaptured admission Task/input, arbitrary-size integral measurements and full interface I/O comparison. The implementation PR proposes M5-006 READY → DONE without changing its definition or dependencies. Acceptance remains gated by exact-head full/coverage/package/repository/governance CI and cross-owner review; M6-008, Gate B, M5-007 and real execution stay separately owned and gated.

[Implementation Attempt Archive](attempts/M5-006-IMPLEMENTATION-001/README.md) preserves the available construction evidence. Hosted CI runs and PR review are subsequent evidence bound to the PR's exact head; their logs/results remain in GitHub Actions. Capture incompleteness is explicit rather than filled with reconstructed events.

Formal Trace validation: no BLOCK; `TRACE-CAPTURE-DELAYED` warning retained. The Trace Attempt is `incomplete` because original capture was gapped; it does not claim a complete transcript or reconstruct unseen results. Contract implementation and the proposed Task status remain separately subject to CI/review acceptance. Final documentation links: 9 tests PASS.

2026-09-12 hosted CI follow-up: run [34618373895](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34618373895), bound to head `173d08e1779912b5454608520ec2eac7c3d59384` and base `11c3b57dfbf8af0dc2587fc421d097e2544941c3`, exposed one full Python 3.13 regression: the existing Schema catalog equality test omitted the eight newly registered M5 record kinds (1148 passed / 1 failed / 0 errors). The repair adds those eight explicit names and preserves strict set equality; production contracts and coverage thresholds are unchanged. This failed run is diagnostic evidence. The revised commit requires fresh exact-head full, impact/repository coverage, package, repository and governance checks before acceptance.
