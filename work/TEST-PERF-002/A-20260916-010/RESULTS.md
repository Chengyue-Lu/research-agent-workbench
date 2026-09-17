# Witnessed consumer-policy authority correction

TEST-PERF-002; owner Chengyue-Lu; R2; A-20260916-010.
Implementation: `23fd135026e223c7ad9c4c17b279c17d31b4dbb7`; base: `0d4a1d00a4c32ca9b822df6482a95920e7c21b1b`.

Strict consumer-policy validation now lives in the existing `plan_ci.py` authority.
The planner and worker do not import the diagnostic consumer module, and the fixed independent
witness inventory/root are unchanged. A fresh isolated process with a malicious diagnostic
import sentinel loads the planner, validates v2 and rejects an execution-authority injection.
The separate candidate-bootstrap deletion attack still fails at the independent witness.
The diagnostic helper imports the planner validator; dependency flows toward existing authority.

Local regression: 216 PASS / 321.865 s. Five changed CI modules meet critical 95/90
with no exclusions. These CI tests are not a full repository behavioral run. The eleven
previously executed business proofs are referenced by hash: their four declarations and all
nine declared file pins remain byte-identical. This does not establish complete input closure.

| Module | Statements | Branches |
| --- | ---: | ---: |
| .github\scripts\ci_consumer_contracts.py | 60/60 | 26/26 |
| .github\scripts\ci_contract_shadow.py | 125/125 | 36/36 |
| .github\scripts\ci_dependencies.py | 503/503 | 322/322 |
| .github\scripts\ci_input_facts.py | 80/80 | 46/46 |
| .github\scripts\plan_ci.py | 562/563 | 212/214 |

All thirteen historical plans remain byte-identical to A-20260916-009 after the authority move.
No selection or execution obligation reduction has been activated. M5-007 H1/H2 intake and its
hosted run remain in that prior archive: 93/94 selected modules and 29 archive-classification
FULL reasons, independently of actual schema/catalog/install requirements.
The hosted M5 coverage job took 1108 s (18 min 28 s), including 1089 s in its ordered
behavior-plus-coverage test step. Python 3.13 compatibility took 586 s, with 572 s in tests.
These are observed job/step durations, not isolated coverage instrumentation overhead or a
paired before/after speedup. Python 3.11 compatibility consumes the shared execution receipt.

The initial 216-test combined run failed because the isolated planner seed lacked the newly
required consumer-proof module. The seed and explicit union assertions were updated; the union
still executes each selected test once. Failed logs and the small repair checks are retained.
The final rerun above uses the committed implementation and stable source files.

Exact implementation head-target plan/minimum and governance pass. This archive commit and the
hosted merge target require separate final checks. Old-head CI cannot stand in for those results.
No merge or release action is authorized here. Earlier attempts remain byte-identical.
Trace records a retrospective capture gap for events that were not streamed as they occurred.

See [design](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/CONSUMER_CONTRACTS_V1.md),
[prior intake](../A-20260916-009/RESULTS.md), [comparison](checks/plan-comparison.json),
[business reuse](checks/business-proof-reuse.json), [coverage](checks/critical-module-metrics.json),
[M5 timing](checks/m5-hosted-timing.json),
[preflight](checks/implementation/preflight-summary.json), [manifest](checks/evidence-manifest.json)
and [Trace](checks/trace-validation.json).
