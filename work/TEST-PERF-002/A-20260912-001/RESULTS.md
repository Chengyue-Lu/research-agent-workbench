# Scenario execution and coverage evidence reuse

TEST-PERF-002 revision 24; Chengyue-Lu; R2; source `57daffc039f6cc006fa1320819d3eafd50a12789`.

[Design and scenario mapping](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/SCENARIO_EXECUTION.md).
The user clarified that the function call was an example, not a request to replace
line/branch gates with function coverage. Existing quality floors remain unchanged.

Coverage producer C and behavioral producer B minus C execute independently. A verified
join checks complete exact-plan receipts before proving Python 3.11 behavior; Python 3.13
still executes its selected behavior. Final source inventory: 1127 behavior,
1101 coverage, 26 remainder, complete and disjoint.
This is inventory evidence, not a claim that those final suites have already passed.

Two cache tests share one named inventory lifecycle; their assertions are retained.
Reports identify scenario/checkpoint failures, preserve multiple failures and distinguish
skipped checkpoints from a complete pass. Required negative case IDs are unchanged.

Frozen implementation: 100 targeted checks PASS in 52.626 seconds, including real Git-bound
workers in separate Python processes. Changed runner: 231 executable lines and their outgoing
branches 100/100. Runner overall: 292/300 statements and 110/116 branches; no exclusions.
The earlier 174-check infrastructure pass took 510.452 seconds and started before the final
diagnostic-preservation/summary changes; it is separate from the frozen-head targeted proof.
Documentation/governance: 93 PASS. Repository validation: 186/0/0.

The recorded green baseline had 1,074 duplicate executions, accounting for 759.665 seconds
of behavioral test bodies. This is a compute-cost attribution, not a hosted wall-time
speedup. Fresh final-head full suites, impact+repository coverage and other CI gates remain
required. Cross-owner review is pending; no merge or release occurred.

The recorder was created before implementation and restored from its persisted live object.
Native message/event export gaps remain explicit. Earlier sealed Attempts are unchanged.
