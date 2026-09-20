# Common-driver local pair

Owner Chengyue-Lu; CI execution auditor; required Skills=[]; execution_authority=false.
Target `9724a4ee36889b327b33ba1ebb066a6e02521404`; plan `777a8ef84f852fa74b4df4b344876d9d377d62802d7939d70e79746772a15944`.

| Role | Cases | Outcomes | Native wall | Process wall |
| --- | ---: | --- | ---: | ---: |
| Accepted | 325 | all PASS | 323.008 s | 323.174 s |
| Candidate | 252 | all PASS | 59.492 s | 59.654 s |

Both fresh processes execute the same `driver.py`, SHA-256 `258b24bd3a3adc34fc0b4cbaee7bf467818d07426ad91aa972ed378a72ebc87a`.
Their full argv differ only in the explicit `--role accepted` / `--role candidate` argument.
Both verify the unchanged plan, collect accepted suite/input inventory, check the same 19 pins,
reconstruct the same TestSuite hierarchy, capture the same environment fields, and start timing
at the same point including collection. The role selects only the exclusion set (empty versus
the audited 73 PlannerTests IDs), role-specific evidence paths and native receipt label.
Original test methods, assertions, runner helpers, fixtures and suite hierarchy are preserved.

Accepted325 and candidate252 actual order each matches its preexecution expected inventory.
Candidate adds no case and removes exactly73. C=0; package/repository smoke are false in the
frozen plan. This does not measure coverage or establish whole-repository quality evidence.

Frozen environment documents match exactly, including Python/OS/machine, dependencies digest,
native runner digest, runtime manifest and pin-source hashes, Git/config digest, safe process
environment fields, and empty coverage-config digest. The native receipt files are unchanged
outputs of the accepted runner's TimedTextResult/_write_summary helpers.

This closes the previous local pair's different-driver confound. It remains **one local sequential
pair**, with ordinary shared-host/system cache and scheduling variation; no hosted repetitions
were performed and no activation or hosted speed claim follows. The earlier failed setup run
and corrected different-driver pair remain byte-preserved in their original directories.

## Evidence

- `driver.py`, `run.py`: exact common wrapper and sequential launcher.
- `*-driver.json`: source hash, full argv, exact plan/proposal hashes and checked pins.
- `*-inventory.json`: complete accepted B collected before each run.
- `*-expected.json`: role-specific inventory before execution.
- `*-receipt.json`: native outcomes, test IDs/order, timings and checkpoints.
- `*-environment.json`: identical environment bindings.
- `*.stdout.txt`, `*.stderr.txt`: raw output.
- `analysis.json`, `summary.json`: counts, equalities, observed timings and artifact hashes.

No primary/official branch, production source, test body, selector, policy, workflow, prior
probe snapshot or prior evidence file was edited. The shared isolated snapshot was read/executed
at its existing target with its already generated runtime resources.
