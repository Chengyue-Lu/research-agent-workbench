# Accepted documentation execution and bounded PlannerTests candidate

Accountable owner Chengyue-Lu; CI execution auditor; required Skills=[]; execution_authority=false.
Exact target `9724a4ee36889b327b33ba1ebb066a6e02521404`; plan `777a8ef84f852fa74b4df4b344876d9d377d62802d7939d70e79746772a15944`.
Inputs: unchanged original plan, separately audited 73-ID PlannerTests proposal and snapshot runner.

## Results

- Full accepted B: 325 cases across 13 modules; C=0; smoke obligations false.
- Candidate B: 252 cases across 12 modules; removed exactly 73 audited PlannerTests IDs.
- Accepted outcomes: {"errors": 0, "expected_failure": 0, "failed": 0, "passed": 325, "passed_with_skips": 0, "skipped": 0, "unexpected_success": 0}.
- Candidate outcomes: {"errors": 0, "expected_failure": 0, "failed": 0, "passed": 252, "passed_with_skips": 0, "skipped": 0, "unexpected_success": 0}.
- Native accepted wall: 323.833 s; process wall: 323.993 s.
- Native candidate wall: 63.072 s; process wall: 63.233 s.
- Both actual orders match their fresh preexecution inventories: accepted=True, candidate=True.
- Frozen environment bindings equal: True. Driver identities differ and remain an explicit timing confounder.

This is one local sequential observation, not a clean common-driver paired speed proof, hosted gain,
coverage validation, or activation authority. The candidate's original TestSuite nesting is retained
recursively; unchanged native result/summary helpers record it as `shadow-candidate`. Acceptance runs
the native CLI as `focused`. Both driver sources and complete argv are preserved separately.

The initial Kernel proposal would remove **zero** cases: neither Kernel case is in the accepted plan.
Its observed-subset exclusion cannot be presented as savings from actual CI. This full-plan check
therefore replaced that no-op experiment with the separately audited PlannerTests boundary, at the
parent's direction. The frozen proposal used here is the original audit proposal; the parent's later
workstream-path-scoped declaration did not alter this run or its 73-ID filter.

## Accepted case-cost attribution

Case seconds omit module/class fixture setup and plan collection; they are not total CPU or job critical path.

| Module | Cases | Summed case seconds |
| --- | ---: | ---: |
| tests/test_ci_plan.py | 73 | 260.057 |
| tests/test_selection_witness.py | 10 | 21.041 |
| tests/test_ci_contract_shadow.py | 15 | 20.091 |
| tests/test_ci_dependencies.py | 52 | 6.051 |
| tests/test_ci_domain_audit.py | 4 | 5.241 |
| tests/test_ci_checks.py | 23 | 3.123 |
| tests/test_m5_trace_export.py | 4 | 1.687 |
| tests/test_documentation.py | 10 | 0.350 |
| tests/test_test_runner.py | 17 | 0.239 |
| tests/test_ci_consumer_contracts.py | 6 | 0.189 |
| tests/test_pr_governance.py | 84 | 0.149 |
| tests/test_ci_input_facts.py | 6 | 0.132 |
| tests/test_coverage_policy.py | 21 | 0.077 |

## Setup gap and retained failed evidence

The initial raw Git checkout lacked generated `_runtime_pin.py`/runtime assets. That first full run
observed 322 PASS + 3 ModuleNotFoundError errors in M5TraceExport; its native receipt and raw logs
remain in the parent directory. These are checkout-setup failures, not candidate regressions or
an accepted green baseline. Its 318.842 s process wall exceeded the original five-minute threshold,
so the pointless identical-candidate repeat was not launched.

The parent extended the task to correct setup and rerun. The resolved generated target was checked
to be inside this isolated snapshot and absent before calling this exact snapshot's `build_backend.generate`.
Generated runtime manifest/pin hashes were captured for both corrected runs, with dependencies,
runner, Git/config digest, safe environment fields, Python/OS/machine and an empty coverage-config
digest because C=0. The read-only venv was not installed into or modified. All 19 proposal pins
matched at base, target and working-file (57 checks). Tracked checkout status remains clean.

## Reproduction and evidence

- `run_pair.py`: original unchanged-runner experiment and failed raw-checkout receipt.
- `run_corrected_pair.py`: generated runtime setup; corrected complete accepted plus filtered candidate.
- `check_inputs.py`, `corrected/proposal-pin-check.json`: base/target/worktree pin checks.
- `capture_drivers.py`, `corrected/drivers/`: exact producer/collector/runner sources and argv.
- `corrected/accepted-inventory.json`: fresh full plan collection; candidate-side full discovery retained separately.
- `corrected/candidate-expected.json`: recursively filtered expected inventory before candidate execution.
- `corrected/accepted-receipt.json`, `candidate-receipt.json`: original native outcomes; no rewritten receipts.
- `corrected/*-environment.json`, `*-driver.json`, `setup.json`: environment, driver and generated-resource bindings.
- `corrected/analysis.json`: actual counts, order checks, costs and artifact hashes.
- Raw stdout/stderr and exact isolated Git checkout remain under this task's assessment directory.

No shared probe snapshot, primary/official branch, selector, production test method, policy or workflow was edited.
GitHub was not mutated. Three fresh same-environment hosted pairs with a common driver and independently
accepted exclusion authority remain future requirements.
