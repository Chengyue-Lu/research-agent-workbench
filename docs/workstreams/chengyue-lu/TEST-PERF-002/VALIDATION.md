# TEST-PERF-002 validation

Base: `6f0caf0b8e8a9b123f1ea399e747d2c0ed33cdce` (`develop`).
Implementation: `ceacf58cca0f82d6016e18ba818acd9b42f2805a`.
Guard verification baseline: `2e083f9c1790458689c94873eb192cd3250648b0`.
Review: [PR #63](https://github.com/Chengyue-Lu/research-agent-workbench/pull/63), R2, target `develop`.

## Local evidence and its commit boundary

All local runs used Windows and Python 3.14. The full runs below belong to the implementation commit;
the final code adds strict policy and execution-input guards and has its own targeted regression evidence.
Archive commit `613f91a` preserves those source and test blobs. Hosted Python 3.11/3.13
FULL checks must pass on the final PR head before acceptance.

| Check | Commit | Result |
| --- | --- | --- |
| Full behavioral suite | `ceacf58` | 887 tests: 884 PASS, 3 Windows symlink-privilege skips; 942.57 s |
| Coverage-quality suite | `ceacf58` | 826 tests: 823 PASS, 3 same skips; 544.92 s |
| Repository coverage policy | `ceacf58` | Global line 91.97%; every critical module meets 95% line / 90% branch |
| Planner/checker/runner regressions | `2e083f9` | 34/34 PASS |
| Planner critical coverage | `2e083f9` | 99.59% line / 96.88% branch, zero exclusions |
| CI checker critical coverage | `2e083f9` | 99.13% line / 95.00% branch, zero exclusions |
| Governance, documentation, coverage-policy regressions | `2e083f9` | 104 PASS |
| Repository validation | `ceacf58` | 183 validated, 0 errors, 0 warnings |
| Wheel clean-install smoke | `ceacf58` | Build, fresh venv install, schema list and 183/0/0 validation PASS |
| Workflow syntax | final workflows | actionlint 1.7.12 PASS; release archive checksum verified |

The initial local wheel install inherited `PYTHONPATH` and did not prove a clean wheel import. The recorded
passing smoke clears that variable and force-installs the built wheel in the fresh venv. Product source,
schemas, registry and packaging are identical between the two code commits and the accepted base.

## Actual selective execution in isolated Git fixtures

Both fixtures start at final code `2e083f9`. They preserve the full accepted consumer inventory and invoke
the real planner and runner. Their synthetic commits exist only in an ignored local clone.

| Fixture | Selected obligations | Result |
| --- | --- | --- |
| Equivalent OpenAI provider-name literal | provider-wire → conformance → session → CLI; impact coverage | 81/81 PASS, impact checker PASS; 26.46 s |
| README-only addition | documentation group; FAST | 76/76 PASS; 1.46 s |

These timings establish local selection and execution behavior, not hosted speed savings. Impact coverage
explicitly reports `repository_coverage_proved: false`. Unknown or changed consumers, policy/runner edits,
new imports, source add/delete/rename/mode changes, source deletion-only hunks, stale bases, R2 and
integration/release work retain FULL. Negative fixtures cover plan weakening, dirty/untracked inputs,
coverage and evidence drift, missing/failed/cancelled required jobs, and stale or weaker metadata reuse.

## Hosted evidence and remaining acceptance

The initial PR opened at `2e083f9`; governance run `34029871790` passed. Content run `34029871793`
started for that head. The archive commit will trigger a replacement FULL run. Current results are
authoritative at the [PR checks](https://github.com/Chengyue-Lu/research-agent-workbench/pull/63/checks).
Old-head cancellation and metadata-only behavior must be observed from actual hosted events; local
workflow and negative fixtures do not by themselves prove those remote outcomes.

The remote settings query returned `rulesets=[]` and `develop.protected=false`. Fixed aggregate check
names and fail-closed propagation are preserved; remote required-check enforcement is not established
by this implementation. Cross-owner review and final-head CI remain merge gates.

## Archive

[Attempt index](../../../../work/TEST-PERF-002/A-20260906-001/INDEX.yaml) pins the task, compact handoff,
source hashes and machine result summaries. Native events, intermediate file revisions and complete
tool output streams have explicit capture gaps. The archive distinguishes observed checks from pending
hosted acceptance; structural Trace validation does not grant a human approval.

## PR review follow-up

Copilot's initial review identified a missing `pull-requests: read` token permission for FULL dispatch and
an unclear failure when a focused run omits `--plan`. The follow-up grants only the required read permission
and rejects missing plan/loader inputs with explicit errors. The existing regression cases now exercise
these paths (34/34 PASS); actionlint and 9 documentation tests pass. This follow-up is recorded in PR #63 and its
own Git commit after the frozen archive; the archive's code manifest remains evidence for `2e083f9`.

Hosted run `34029871793` on `2e083f9` was automatically cancelled after `613f91a` started replacement
run `34030126386`. No manual cancellation was issued. Updating the PR body after that replacement plan
was uploaded triggered governance run `34030228581`, which passed and retained content run `34030126386`
without launching another content run. Final hosted outcomes remain available in the PR checks and body.

## Bounded cross-owner closeout: P2-1 through P2-3

The [latest cross-owner review](https://github.com/Chengyue-Lu/research-agent-workbench/pull/63#issuecomment-5559639631)
at `2f93bf5` requests three local corrections. The next R2 commit contains:

- P2-1: consumer fingerprint includes every Python file under `tests/`, including content and mode. Real Git
  fixtures add/delete a test module and evolve an unselected module; old closure falls back FULL. The same
  budget assertion passes before the leaf regression and fails afterward. After explicit grouping and
  fingerprint renewal, FOCUSED includes the consumer again. The policy fingerprint is refreshed against
  the reviewed staged tree; it does not include the policy JSON itself.
- P2-2: retain physical Git `changed_lines` and bind recomputed AST statement spans as `coverage_lines`.
  The checker checks those spans, including multiline branch origins. Real coverage reports the missing
  arc `[2, 6]` for a continuation-line edit; rejection occurs until both paths execute. An unmappable line
  falls back FULL, and narrowing the plan's executable mapping is rejected.
- P2-3: require dispatch trigger `GITHUB_SHA` to equal the freshly queried PR head. Wrong, missing and
  stale trigger SHAs reject before a usable plan exists. Current head and exact merge-candidate fixtures
  retain FULL recovery; metadata matching is unchanged.

Local affected regressions: **37/37 PASS** (90.91 seconds under coverage); documentation/coverage-policy:
**30/30 PASS**. Planner coverage is **261/262 lines (99.62%)**, **66/68 branches (97.06%)**. CI checker
coverage is **114/115 lines (99.13%)**, **37/40 branches (92.50%)**. Both have zero exclusions and retain
the 95/90 critical floor. These runs cover the changed code blobs pinned by the
[review attempt](../../../../work/TEST-PERF-002/A-20260906-002/INDEX.yaml), before its archive-only additions.

The accepted-base product tree, full suite inventory and quality thresholds are retained. This closeout
requires one new final-head FULL hosted run and cross-owner acceptance. Parent Issue #48 remains open;
its broader hosted performance and profiling work is outside these three fixes.

## Independent obligations (revision 4)

Base is `develop@97f760c43e95b398c396987f349e2199c567cbc7`. PR #65 was merged after all ten
exact-head checks passed, with the user's explicit authorization and a matching-head squash operation.
Its receipt is pinned in the [revision-4 archive](../../../../work/TEST-PERF-002/A-20260907-002/INDEX.yaml).

- Final Python 3.11.16 planner/checker suite: **48/48 PASS**. The exact 20-file PR #65 Git replay gives
  R2/full behavior, coverage none and both smokes false. A-F, base-policy/fingerprint bypasses, metadata
  reductions and required-job failure matrices are included.
- Final planner: **346/347 lines (99.71%)**, **108/110 branches (98.18%)**; CI evidence checker:
  **115/116 lines (99.14%)**, **34/36 branches (94.44%)**. Both retain zero exclusions and 95/90 floors.
  This focused critical evidence does not establish repository coverage.
- A separate, isolated bounded planner edit executed **33 impact tests PASS** with real coverage and
  positive/negative acceptance evidence. Its checker accepted the plan and reported
  `repository_coverage_proved: false`. Explicit filesystem measurement roots retain unimported package
  files for complete exclusion reconciliation.
- The local full suite before the final package dependency/configuration guard ran **903 tests**:
  **900 PASS + 3 Windows symlink-permission skips**, zero failures/errors. The final guard has fresh
  focused tests; final-head full behavior remains mandatory in hosted CI.
- The local repository-coverage run was cancelled when superseded by that final guard. No final-head
  repository coverage PASS is claimed here. The new PR requires repository coverage because its runner
  and workflow coverage authority changed; package and repository smoke are independently false.
- actionlint PASS; documentation links **9/9 PASS**; repository validation **183/0/0**; staged governance PASS.

The archive pins source hashes, observable result summaries and plans, and declares native capture gaps.
The new PR's exact-head CI and cross-owner review remain independent acceptance inputs. Global 90%,
critical 95/90, exclusions, negative acceptance and existing behavioral tests are unchanged.

## PR #66 blocking review repair (revision 5)

[Task-owner review 5126334844](https://github.com/Chengyue-Lu/research-agent-workbench/pull/66#pullrequestreview-5126334844)
identified invalid ordinal coverage reuse and destructive impact-analysis clearing at `1f9c13b`.
Plan v3 compares coverage sets by inclusion, retains executable/closure guards and base acceptance, executes
the union of required tests once and enforces both checkers for combined obligations.

- Final scoped Python 3.11.16 run: **54/54 PASS**, zero skips/failures/errors. It includes all three requested
  adversarial cases, repository-only reuse rejection, real union deduplication, independent checker failure
  propagation, decorator mapping and Git type-change retention.
- Planner: **381/382 lines (99.74%)**, **122/124 branches (98.39%)**. CI checker: **127/128 lines (99.22%)**,
  **38/40 branches (95.00%)**. Both retain zero exclusions and all base positive/negative PASS evidence.
- The staged PR diff against `97f760c` requires **impact + repository**, retains both critical modules and
  their coverage test selection, records import/deletion/pragma uncertainty, and leaves both smokes false.
  Its mapped executable statement and outgoing-arc preflight has **zero uncovered changes** in the scoped
  report. This preflight does not claim execution of the actual repository test union or repository coverage.
- Documentation / coverage-policy tests **30/30 PASS**; actionlint PASS; repository validation **183/0/0**.
- The [revision-5 archive](../../../../work/TEST-PERF-002/A-20260907-003/INDEX.yaml) pins the review, final source
  hashes, scoped summaries and staged plan. Native capture gaps are explicit; previous archives remain frozen.

Old-head hosted run `34053678091` completed successfully with two plan-exempt smoke skips. It predates this
repair. Final-head dual-Python full behavior, the actual coverage test union and both checkers remain required
in the new PR CI; human cross-owner acceptance and merge remain pending.


## Revision 6: affected behavioral and coverage scope

The accepted re-audit changes the selection contract to plan v4. R2 controls governance/review;
complete affected behavioral tests, coverage and smokes are independent. Base/head imports and actual
file/path references supplement reviewed groups. A base-side fingerprint commit anchors each reviewed
consumer boundary; only changed/new consumers add their downstream closure. Metadata keys and unchanged
processors of test input cannot turn test-only changes into product executable changes.

On implementation `774cdb6`, the Windows/Python 3.11 full oracle ran **938 tests: 935 PASS, 3 SKIP**
with no failures/errors. The three skips are existing symlink privilege limitations. Full wall time was
1361.041 seconds; it overlapped focused validation and is not a hosted performance benchmark.
`01aa4e4` adds one independently passing real runner regression plus its fingerprint refresh; all four
impacted executable files are byte-identical to the oracle implementation. The retained full inventory
plus that addition contains 939 tests. Linux hosted checks must execute the symlink cases.

Focused evidence is **83 PASS + 1 additional runner regression PASS**. The latter executes none,
impact-only, repository-only and combined coverage entries, verifies real result binding and canonical
identity deduplication. The coverage union/checker proof remains a separate hosted obligation.

| Critical module | Line | Branch |
|---|---:|---:|
| plan_ci.py | 99.77% | 98.63% |
| ci_dependencies.py | 100.00% | 100.00% |
| ci_checks.py | 99.23% | 97.50% |

All changed executable statement/outgoing-branch preflights pass at 100/100, including the runner.
Documentation/coverage-policy: 30 PASS; actionlint: PASS; repository validation: 183/0/0;
wheel build and clean installed-package smoke: PASS. Governance remains R2 with cross-owner review.
Global 90, critical 95/90, exclusions, negative acceptance and full behavioral inventory are retained.

Real full-repository, proposed-baseline Git probes give:

| Probe | Behavior | Selected modules/tests | Coverage | Package/repository smoke |
|---|---|---:|---|---|
| R2 ordinary CI test edit | focused | 4 / 105 | none | false / false |
| R2 Provider leaf edit | focused | 8 / 81 | impact | true / true |

These are plan/collection results against exact local Git trees. They are not observed hosted wall-time
savings. The Provider probe preserves the original reviewed 81-test closure; the test-only probe excludes
unrelated product behavior. The current PR also changes shared planner/runner/workflow authority, so its
own closure remains broad and requires repository plus impact evidence. Hosted critical path and total
runner time must be reported separately from these targeted probes.

Revision 6 archive: `work/TEST-PERF-002/A-20260907-004/`. It pins executable hashes, plan/probe summaries,
observable checks and explicit capture gaps. Final-head hosted checks and cross-owner acceptance remain
required after the same-PR push; this archive does not authorize a merge.

## Revision 7: bound execution consumers

A final boundary probe found that assigning `__import__` to a variable could hide its dynamic consumer.
Execution capabilities passed or bound away from a direct call now preserve opaque consumers. Builtins
aliases and loader methods receive the same treatment; direct literal imports retain precise edges.
Eleven adversarial subcases cover assignment, passing, aliases and loader execution.

The updated planner/checker/dependency regressions pass **85/85**, including the real runner cases.
The dependency helper has **100% line / 100% branch** coverage; planner and checker remain above 95/90.
All four changed executable files pass the **100/100** statement/outgoing-branch preflight.
The full inventory is **940** tests and retains all 938 oracle identities plus both subsequent additions.

Refreshed complete-repository Git probes select **106** tests in four modules for the R2 CI-test edit,
with coverage none and both smokes false. The Provider probe retains **81** tests in eight modules,
impact coverage and the original smokes. These counts are selection evidence, not hosted timings.

The revision 6 full oracle remains tied to its recorded commit. The dependency helper changed afterward,
so final-head hosted dual-Python behavior and the actual coverage union/checkers remain required.
Run `34068747020` on superseded head `e39b398` was cancelled to avoid finishing obsolete evidence.
The supplemental archive is `work/TEST-PERF-002/A-20260907-005/`; the prior sealed archive is preserved.

## Revision 8: selection-authority and reflection review

The [task-owner review on 2e23893](https://github.com/Chengyue-Lu/research-agent-workbench/pull/66#pullrequestreview-5127339541)
identified two P1 blockers. Both were reproduced before the fixes: a real defective candidate selector
could authorize focused behavior, and reflected execution capabilities could lose their consumer edges.

Semantic changes to the five selection-authority files now require full dual-Python behavior. Coverage
and smoke remain independent. A real candidate process with an empty selected-test mapping generates
full; its own worker rejects a re-signed focused downgrade. Python/workflow comment controls remain
scoped. Workflow comparison preserves scalar types and duplicate fields while ignoring comments/layout.
Thirteen `getattr`/reflection scenarios retain consumers across assignment, passing, storage, calls,
aliases and loader/spec capabilities; an ordinary data-attribute consumer remains excluded.

Final local focused validation is **88/88 PASS** with no skips, failures or errors. An earlier run exposed
one old runner expectation of focused behavior after a planner edit; that expectation was updated to full
while retaining the independent impact-runner assertion, and the final suite was rerun on the final code.

| Critical module | Line | Branch |
|---|---:|---:|
| plan_ci.py | 99.78% | 98.68% |
| ci_dependencies.py | 100.00% | 100.00% |
| ci_checks.py | 99.23% | 97.50% |

All four impacted executable files pass the 100/100 changed-statement/outgoing-branch preflight.
The current full inventory contains **943** tests and retains every earlier oracle identity.
Documentation and coverage-policy checks pass **30/30**; quality thresholds, exclusions and acceptance
inventory are preserved. Local focused coverage does not claim repository coverage authority.

The complete-repository probes retain R2 test-only **109 tests / coverage none / no smokes** and Provider
**81 tests / impact / original smokes**. This PR itself now explicitly requires **full behavior** because
it changes selection authority, alongside independently derived impact + repository coverage and smokes.
These probes establish selection, not hosted time savings.

The preceding `2e23893` hosted run [34069525321](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34069525321)
completed successfully. It remains evidence for that earlier head. Final-head hosted full behavior,
coverage/checkers and cross-owner acceptance are separate requirements. Revision 8 evidence is sealed in
`work/TEST-PERF-002/A-20260907-006/`; prior archives remain immutable.

## Revision 9: independent selection-authority witness

The remaining review finding is reproduced with two actual candidate subprocesses:
the candidate deletes its planner FULL guard and empties the dependency selector;
both its planner and worker accept focused behavior. The same plan is rejected by a
separately committed witness running in an isolated Python process. Candidate module
shadowing does not enter that process. The previous bootstrap regression remains useful
behavioral evidence but does not by itself establish an independent authority root.

The [execution procedure](SELECTION_WITNESS.md) pins witness commit
`1b543393ae71b9032359b739170d66ec0be08772`. Independent hosted run
[34079220171](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34079220171)
passed in a 9-second job; GitHub API confirmed that exact workflow SHA and dispatch event.
Its receipt is bound to candidate `69b22e8` and content run `34074914208`, not to later
implementation commits. A new-head invocation follows the final push. Cross-owner
acceptance of the fixed root and current receipt remains required; automatic required
check enforcement of this additional witness has not been configured.

Local targeted regression: **98/98 PASS**, 310.640 seconds. The witness has **100% line /
100% branch** coverage; planner 99.78/98.68, dependency helper 100/100 and checker 99.23/97.50
retain whole-file 95/90. All five impacted executable files satisfy the changed-statement
and outgoing-branch **100/100** preflight. Positive/negative mappings and the coverage-quality
suite include the witness. Thresholds and exclusions are unchanged. These local results
are impact preflight evidence, not repository-wide coverage authority.

Inventory: **953 tests**, retaining all 938 earlier oracle identities. Documentation and
coverage-policy checks: **30 PASS**. Proposed-baseline Git probes retain R2 focused behavior:
test-only selects **119 tests**, coverage none, both smokes false; Provider remains **81 tests**,
impact coverage and its original smokes. These are selection counts, not hosted speedup claims.

Revision 9 archive: `work/TEST-PERF-002/A-20260907-007/`. It records the attack receipt,
independent initial hosted receipt, source hashes, local validation and explicit capture gaps.
Final-head CI and independent witness receipts remain separate GitHub evidence after the seal.
