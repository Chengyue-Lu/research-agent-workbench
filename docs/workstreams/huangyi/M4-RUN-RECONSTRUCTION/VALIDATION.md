# M4-004 Candidate Validation

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
| Promotion linkage has exact path/hash semantics | Real host-produced promotion fixture is executed; its published target is accepted and a same-byte different path rejected |
| Readers do not execute checkers or simulations | Manifest and report validation tested with `Popen` forbidden |
| Producer to generic validator | Generated report accepted; modifying generated output makes generic validation fail |
| Scope and authority remain constrained | Escape/inbox/alias/wrong Run/duplicate output/Claim authority changes rejected; existing attempt not overwritten |

An initial pre-binding-fix CLI attempt was retained locally under
`work/M4-004/A-20260906-001/reconstruction/`. It ran CPython 3.11.9 with `-I -S` in a fresh staged directory,
returned zero and reported `matched`. Output SHA-256:
`177fa6856055f38f2ce7268a2e47f21f843628f0bfe316813ac1c55efec09369`.
That initial manifest has since changed; its old report is retained as historical debugging material, not current
validation evidence. Current corrected reconstruction and producer-to-generic-validation evidence come from
the actual subprocess tests above. The ignored attempt is not committed evidence or Human acceptance.
