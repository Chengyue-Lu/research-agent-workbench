# M4-004 Run Reconstruction

Task owner: Chengyue Lu. Implementation owner: Huang Yi. Base: develop `6f0caf0`, after PR #54.
Status: accepted and merged into develop via [PR #62](https://github.com/Chengyue-Lu/research-agent-workbench/pull/62)
at `2026-09-10T23:50:24Z`, squash commit `11c3b57dfbf8af0dc2587fc421d097e2544941c3`.
M4-004 is DONE within its original acceptance, owner and dependencies.

The bounded goal is to rebuild one Run from explicit pinned files in a fresh process, without the original Agent
conversation or cwd. This is an M4 synthetic engineering case. It does not establish an M5 research result.

## File Contract

`run_reconstruction_manifest` binds the Run identity plus exact FileRefs for a single Python program, input data,
parameters, environment definition and expected outputs. It adds no new core ObjectRef meaning or Claim authority.
The manifest's `run_ref.revision` must equal the Run revision. `input_bindings` explicitly maps every Run
`input_refs` ObjectRef to exactly the executed input and parameter FileRefs. Each input binding declares
`role: input` or `role: parameters`, exactly once each; its FileRef must equal the corresponding top-level
`input_ref` or `parameters_ref`, including any FileRef revision. Reordering bindings is valid; swapping their
files is not. `environment_binding` maps the
Run environment ObjectRef to the executed environment FileRef. Each `expected_outputs` entry maps a Run
output ObjectRef to its expected artifact FileRef. These object identity/revision sets must match exactly,
without duplicate, missing or additional bindings. Unversioned string ObjectRefs are rejected for reconstruction.
Where an ObjectRef declares `sha256`, the Run and binding must declare the same normalized object hash;
this preserves its existing logical `content_hash` meaning and does not compare it to the FileRef byte hash.
FileRefs independently verify actual bytes. No global object resolver, implicit package imports, workflow
graph or shell command is resolved.

The runner copies captured, hash-checked bytes into a new directory under `work/`, then invokes exactly:

```text
python -I -S program.py inputs.json parameters.json outputs
```

The program must use only the Python standard library and the supplied files and must write output files under
`outputs/`. Expected names are flat; missing, additional or changed output files yield `output-different`.
The core runner does not contain the case equation. This bounded trusted-program contract is not an OS sandbox
and does not provide general dependency installation, filesystem/network confinement or resource quotas.

The pinned environment definition records CPython implementation, exact patch version and platform; all three
must match the current interpreter. Dependency declaration is `stdlib-only`. It does not attest interpreter
binary bytes, OS patch level, CPU, standard-library build or undeclared code behavior. The shipped manifest
targets CPython 3.11.9 on Windows. A different platform/version requires an explicit new environment definition
and repinned manifest, which represents a different reconstruction configuration. Focused tests do that in
temporary fixtures so they can run on supported CI platforms; they do not silently rewrite the shipped pin.

## Shared Synthetic Case

`examples/run-reconstruction/linear-recurrence/` contains the complete portable fixture:

| File | Meaning |
| --- | --- |
| `run.yaml` | `RUN-M4-LINEAR-001`; explicitly synthetic metadata, fixture timestamp |
| `simulate.py` | Integer recurrence `x[n+1] = a*x[n] + u[n]` |
| `inputs.json.txt` | `u = [1, -1, 2, -2]` |
| `parameters.json.txt` | Initial value `x0 = 0`; coefficient `a = 1` |
| `environment.json` | Exact interpreter facts and standard-library-only declaration |
| `trajectory.csv` | `(n,x) = (0,0),(1,1),(2,0),(3,2),(4,0)` |
| `manifest.yaml` | Exact SHA-256 pins for the above files |

The `.json.txt` suffix marks application data rather than a repository contract document; the program receives
the same bytes as `inputs.json` and `parameters.json`. No stochastic parameter or random seed is involved.
Zero net change is marked `negative_result: true` and retained. That label describes this synthetic comparison,
not the falsification of a scientific hypothesis. Real scientific parameter meanings, Claim ceilings or core
contract changes still require named owner acceptance; ordinary bounded fixture implementation is reviewable
branch work, without an additional advance-approval gate.

## Commands And Outcome

From the repository with the pinned Python environment and installed package:

```text
rwb run check examples/run-reconstruction/linear-recurrence/manifest.yaml --root .
rwb run reproduce examples/run-reconstruction/linear-recurrence/manifest.yaml --root . --attempt-dir work/M4-004/A-NEW
rwb validate work/M4-004/A-NEW/reconstruction-report.json --root .
```

Use a new attempt directory on every execution; existing attempts and paths outside `work/` are rejected.
An unreadable/unparseable manifest or invalid destination is rejected before creating an attempt. Once a
manifest is parsed and an attempt is allocated, ordinary preflight and execution failures receive a durable
report, stdout/stderr and any partial outputs. Interrupted parent processes and host crashes are not recovered.

| Status | Meaning |
| --- | --- |
| `manifest-invalid` | Schema, identity, admission or output/receipt binding is invalid |
| `pin-drift` | A required file exists but differs from its declared SHA-256 |
| `prerequisite-missing` | A required file is absent or the current interpreter facts differ |
| `run-failed` | Process start, nonzero exit, timeout or invalid output path |
| `output-different` | The successful process produced a different set of output files or bytes |
| `matched` | The successful process reproduced the complete expected set and exact bytes |

Reports bind the exact manifest, copied code/input/parameter/environment files, actual outputs and diagnostic
streams. `rwb validate` checks report structure and these direct FileRefs without executing any program. It does
not authenticate a report's claimed history or recursively replay the manifest; a retained failed report can
therefore remain structurally valid while documenting missing or drifted original inputs. `matched` is a current
execution result from this runner, not scientific authority or proof that earlier execution metadata is genuine.
`code_ref` pins the executed program's bytes but does not bind that program to `Run.method_ref`; matching bytes
therefore do not prove that the program implements the Run's declared Method.

## Promotion And Claim Boundary

Optional `promotion_receipt_ref` exact-pins an existing M4-002 Promotion Execution Receipt. The manifest reader
checks its schema, requires its original `runs/promotions/<promotion_id>/receipt.json` path without filesystem
aliasing, and requires each expected artifact's path/hash pair to occur as a receipt target. Same bytes
at a different path do not satisfy that binding. It does not re-execute promotion validation, authenticate old
execution metadata or publish reconstructed output. Promotion acceptance remains in M4-002.

M4-003 can consume the same input, parameter and trajectory files and the receipt target refs. Neither Task
depends on the other's new code. Claim evidence/support semantics remain separate from byte reconstruction.

Validation and residual limits: [VALIDATION.md](VALIDATION.md), [RISK_LEDGER.md](RISK_LEDGER.md).
