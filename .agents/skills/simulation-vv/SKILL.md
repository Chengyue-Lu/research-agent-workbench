---
name: simulation-vv
description: Audit a bounded computational simulation run for pinned model and input versions, numerical convergence evidence, sensitivity evidence, benchmark comparisons, assumptions, and claim limits. Use for simulation verification and validation planning or run review. Do not use to claim experimental validation, certify real-world fidelity, choose acceptable error bounds, or replace domain-expert judgment.
---

# Simulation V&V

Audit the evidence supporting a simulation run without confusing numerical verification with physical validation.

## Workflow

1. Read the Task Packet, Skill Assignment, run and method references, parameter boundary, input lock, write scope, and claim ceiling. Stop on an unpinned or stale input.
2. Read [vv-contract.md](references/vv-contract.md) before writing the report.
3. Record model, code, environment, input, parameter, seed, and output versions before interpreting results.
4. Check convergence, sensitivity, and benchmark evidence independently. Record `not-run` or `blocked` instead of inferring a pass from a successful program exit.
5. Separate numerical implementation evidence, model-form assumptions, calibration evidence, and external validation evidence.
6. Keep the claim at `simulation_supported` or weaker unless another accepted Research Mode and Human Gate authorize a different ceiling.
7. Run `python scripts/check_vv_report.py <report>` and validate referenced files and the Handoff with `$handoff-integrity`.
8. Return a concise Handoff with failed or absent checks, assumptions, limitations, and human decisions required. Keep raw logs outside the main-agent context.

## Stop conditions

Stop as `blocked` or `incomplete` when the model or inputs are unversioned, evidence references are missing, the requested parameter region exceeds the declared boundary, or a requested conclusion implies experimental or real-world validation not present in the inputs.
