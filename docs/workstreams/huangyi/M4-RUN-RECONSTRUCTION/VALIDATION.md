# M4-004 Candidate Validation

## Owner-review corrections (2026-09-10)

The accepted PR66/67 CI policy requires all changed executable lines/outgoing
branches of a new module to be covered. One module-only branch coverage run after
integration passed **19 methods in 109.604 seconds**, with **217/217 lines and
76/76 branches (100/100), zero exclusions**. It closes the actual prior gaps for
non-object pinned documents, distinct Run outputs colliding on names/files, output
link classification and nested extra outputs. The link-classification unit check
injects the filesystem predicate; it does not claim real OS symlink confinement.
Existing tests cover the role/receipt fixes and real producer-to-reconstruction
path in the same suite. No thresholds or policy exclusions changed. This narrow
measurement is distinct from the earlier pre-integration four-method run below;
it is not repository/global coverage. No further local suite is required without
a new change or failure. Evidence: `module-coverage-tests.txt` and
`module-coverage.json` in the local attempt directory.

Repair commit `035d464` is integrated with accepted develop `f78fae6` (including
PR66/67 CI and PR60 M14-001/002/003) by merge commit `eec0f5f`. There were no merge
conflicts. Both Claim/Run consumers, Schema registrations and critical/acceptance
inventories are retained. Schema catalog and internal Markdown links pass
(2 methods, 0.761 seconds). Runtime resources were generated from this merged
checkout for the source-selected local checks; no wheel or installation was run.

The refreshed local combined observation at `eec0f5f` reuses the retained original
promotion target and receipt. Only a new copied manifest receives explicit roles;
historical artifacts are preserved. Claim `complete=true`, Run `matched`, output
bytes and generic map/report checks pass. Exactly one reconstruction subprocess
runs (**0.094 seconds**), with zero promotion/checker executions. The indexed local
result is `work/M4-004/A-20260910-001/README.md`. This fixed-environment synthetic
observation is neither scientific acceptance nor measured research benefit.

Chengyue Lu's review of `5141e6d` identified two remaining P1 closure defects.
Input bindings now require exactly one `input` and one `parameters` role and each
role's FileRef must equal the corresponding executed reference. Promotion receipts
must retain their canonical, unaliased `runs/promotions/<promotion_id>/receipt.json`
location. Report and contract text also explicitly retain the nonblocking limit:
the pinned program is not bound to the Run's declared Method implementation.

Four focused methods passed on Windows CPython 3.11.9 in **15.993 seconds**:
swapped input files reject before execution while binding order remains valid;
duplicate/missing roles and existing invalid bindings reject; the existing real
promotion fixture rejects a re-pinned receipt copy and the original wrong-target
path, then successfully reconstructs the published bytes and validates its report;
the shipped manifest remains generically valid without execution. The receipt test
reuses one producer fixture and only its existing successful reconstruction.
Read-only and rejected cases forbid `Popen`. This is not a new global coverage or
performance measurement. Local evidence: `work/M4-004/A-20260910-001/focused-tests.txt`
and `delta-review.md`. No local full, repository coverage, package or model test was repeated.

The schema and example changes tighten the still-unaccepted manifest candidate;
old local manifests without roles remain historical and are not current acceptance
evidence. Final integrated hosted CI and Chengyue Lu's semantic acceptance are
still required. Earlier measurements below retain their original scope and dates.

## Accepted M4-003 integration (2026-09-07)

PR61 was accepted by Chengyue Lu at `72ba684` and merged into develop as
`b8a38a1`. Integration commit `d3ec4a0` incorporates that accepted Claim consumer
and the accepted PR63/65 CI behavior into this PR62 candidate. Conflict resolution
preserves both consumers, all four Schema registrations, both coverage inventories
and M4-003 DONE; only M4-004's completion remains a candidate Task transition.

The previously tested producer-to-reconstruction extension `cf114c9` is unchanged.
A new combined observation at `d3ec4a0` reuses its retained real promotion target
and receipt, with the now-accepted Claim consumer: Claim `complete=true`, Run
`matched`, exact output bytes and generic manifest/map/report checks all pass.
Readers forbid `Popen`; exactly one necessary reconstruction subprocess ran, with
reported duration **0.141 seconds**, under Windows CPython 3.11.9. No promotion,
checker, installation, model, local full or global coverage run was repeated.

The candidate's ignored `work/M4-004/A-20260907-001/README.md` indexes the manifest,
receipt, Claim trace, reconstruction report and file-hash inventory. The synthetic
Claim intentionally overstates stability; its contrary intermediate states and
limitation remain visible. The observation proves fixed-environment engineering
integration, not scientific truth, cross-platform reproduction or M5 benefit.

The merged Schema catalog inventory and internal Markdown link checks pass
(2 tests, 1.864 seconds), and `git diff --check` passes. No production source
changed after the combined observation; the following commit only records it.

Final hosted CI and Chengyue Lu's semantic acceptance remain required for PR62.
The sections below retain the earlier measurements at their original candidates;
they are not measurements of this integrated candidate.

## Earlier candidate evidence

Validation environment: local Windows, CPython 3.11.9. Source package selected explicitly with `PYTHONPATH`
pointing at this candidate's `src`; the reused closeout venv does not select the older editable source tree.

On 2026-09-06 the corrected candidate's 15 focused tests passed under module-only branch coverage in 57.924
seconds. Initial module results were line 97.16%, branch 88.57%. A real untested source boundary was then added:
exact bytes under `sources/raw` without admission cannot be executed. Only that new test was run and appended
to the same measurement (passed in 1.344 seconds). All 16 focused methods are represented in the final data.

Final `artifacts/run_reconstruction.py` coverage: line **206/211 = 97.63%**, branch **63/70 = 90.00%**,
zero excluded lines. It meets unchanged critical thresholds 95/90. `tests/coverage_policy.yaml` includes the
module, its test suite and distinct actual positive/negative test IDs; global threshold remains 90.
The local JSON and summary are under `work/M4-004/A-20260906-001/coverage-focused.json` and
`COVERAGE_SUMMARY.md`. No repository-wide suite or global coverage run was performed; final hosted validation
owns Python 3.11/3.13 compatibility, global coverage and all other critical modules.

Final documentation/Schema/CLI checks passed after registering the three new Schemas in the existing catalog
inventory test. The other 15 selected tests passed initially; only the inventory method and changed documentation
checks were rerun (10 PASS). A clean wheel installed in a separate environment can check the pinned manifest from
outside the checkout; generic validation of the shipped reconstruction case reports 3 documents, 0 errors and
0 warnings. `git diff --check` passes. No production change followed the focused coverage measurement.

Independent review found that merely re-pinning a Run could previously bypass its logical input/environment/
output refs. Explicit ObjectRef-to-FileRef bindings and `run_ref.revision` now close that gap. The reviewer
repeated all three original mutations and confirmed `manifest-invalid`, `executed=false`, while the positive
control remained `matched`. Equivalent string/mapping ObjectRefs, normalized declared object hashes, and
FileRef revisions are included in focused evidence. No original Task acceptance wording was changed.

| Acceptance observation | Focused evidence |
| --- | --- |
| Code/input/parameters/environment/output pins | Each file drift blocks before process execution; shipped manifest static closure passes |
| Run identity and logical reference closure | Exact input/environment/output ObjectRef sets map to executed FileRefs; merely re-pinning an unrelated Run ref, changing revision/hash or omitting/duplicating a binding blocks |
| Independent process and cwd without original Agent session | Real isolated child asserts environment variable absent; separate CLI process launched from unrelated cwd |
| Replay produces the expected artifact | Actual recurrence trajectory CSV matches byte-for-byte |
| Preconditions and failure are distinct | Missing file, interpreter mismatch, nonzero status, timeout, partial outputs |
| Changed run config reveals a difference | Re-pinned coefficient `a=2` yields `output-different`; missing and extra files are both reported |
| Negative results remain visible | Zero net change is retained with `negative_result: true`; failures retain partial output and stderr |
| Promotion linkage has exact path/hash semantics | One real host-produced promotion fixture supplies the published target and receipt for actual reconstruction; output bytes match, the report retains the receipt ref, and a same-byte different path is rejected |
| Readers do not execute checkers or simulations | Manifest and report validation tested with `Popen` forbidden |
| Producer to generic validator | Generated report accepted; modifying generated output makes generic validation fail |
| Scope and authority remain constrained | Escape/inbox/alias/wrong Run/duplicate output/Claim authority changes rejected; existing attempt not overwritten |

On 2026-09-06 a narrow regression extended only
`test_actual_promotion_receipt_binds_published_target_without_checker_reexecution`. It reuses that method's
existing real promotion target and receipt, saves a valid manifest, then actually reconstructs the trajectory.
Assertions cover `matched`, `executed: true`, zero return code, exact published-target bytes, the unchanged
receipt reference, and generic `rwb validate` acceptance of the emitted report. Both read-only validations keep
`Popen` forbidden; the same-byte wrong-path rejection remains. This one method passed once in **6.639 seconds**
on Windows CPython 3.11.9 with source explicitly selected from this candidate; the capture wrapper took 6.653
seconds including suite loading. No full suite, coverage, package, or model tests were rerun, so the earlier
coverage figures remain historical measurements rather than a new measurement of this test extension.
The local wrapper retained the already-generated producer fixture before normal cleanup under
`work/M4-004/A-20260906-002/agent-regression/producer-case/`, including `promoted-manifest.yaml`, the real
promotion receipt, and the reconstruction report. Its command and raw console evidence are retained beside it
in `WORKLOG.md` and `run-output.txt`. This demonstrates engineering reconstruction and structural report
validation in that environment; it does not establish scientific correctness, historical execution identity,
cross-platform reproduction, or Human acceptance.

The same saved producer case was then consumed by the local-only combined candidate
`e16524631b78985fb2b65f693c9fb1adb4d8a0a3` (PR61 plus this regression). Claim localization and reconstruction
used the same promoted target and receipt: `claim complete=true`, `reconstruction matched`, generic map/report
validation passed, and negative results remained visible. The combination invoked no promotion/checker and
exactly one simulation subprocess, whose reported duration was **0.093 seconds**. This is one engineering
observation, not a performance threshold or research-benefit measurement. The shared trajectory SHA-256 is
`177fa6856055f38f2ce7268a2e47f21f843628f0bfe316813ac1c55efec09369`; the receipt SHA-256 is
`70ba4c543989ffffc00e4a0137431f2bea56c20c4dcba0cffb6f8d7adeafa53c`. The combined checkout's existing
`work/M4-004/A-20260906-002/` archive holds the case, Claim output, reconstruction report and file-hash index.
A single Schema catalog check passed in 0.869 seconds after resolving overlapping registrations; the five
merged documentation files had 66 valid relative links. These observations do not replace hosted checks on
the eventual PR62 candidate or either Task's named-owner acceptance. The draft Claim intentionally overstates
stability so that its contrary intermediate values and limitation remain visible; `complete` does not endorse it.

An initial pre-binding-fix CLI attempt was retained locally under
`work/M4-004/A-20260906-001/reconstruction/`. It ran CPython 3.11.9 with `-I -S` in a fresh staged directory,
returned zero and reported `matched`. Output SHA-256:
`177fa6856055f38f2ce7268a2e47f21f843628f0bfe316813ac1c55efec09369`.
That initial manifest has since changed; its old report is retained as historical debugging material, not current
validation evidence. Current corrected reconstruction and producer-to-generic-validation evidence come from
the actual subprocess tests above. The ignored attempt is not committed evidence or Human acceptance.
