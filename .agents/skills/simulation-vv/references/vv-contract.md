# Simulation V&V report contract

The report is a work artifact, not a certification. Use JSON or YAML with these fields:

- `run_ref`: pinned Run reference.
- `model_version`: non-empty code or model version.
- `input_lock`: one or more `{path, sha256}` records.
- `parameter_boundary`: the reviewed parameter region.
- `checks`: `convergence`, `sensitivity`, and `benchmark_comparison` entries.
- `assumptions`: explicit model, numerical, and boundary assumptions.
- `limitations`: residual gaps and untested conditions.
- `claim_ceiling`: `exploratory`, `simulation_supported`, or `unresolved`.

Each check has `status` (`pass`, `fail`, `not-run`, or `blocked`) and `evidence_refs`. A `pass` without at least one evidence reference is structurally invalid. The checker verifies completeness and hash syntax only; it does not recompute or endorse scientific results.
