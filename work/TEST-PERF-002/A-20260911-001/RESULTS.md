# Resource dependency repair evidence

TEST-PERF-002 revision 21; Chengyue-Lu; R2; cross-owner let778750-cpu.
Source `0c4572ede6094a7581e860f43a48f04347aa7d17` on `11c3b57dfbf8af0dc2587fc421d097e2544941c3`.

The repair distinguishes lexical names and pathname predicates from content inputs,
resolves fixed pathlib roots and retains unknown/escaping/shadowed inputs. Four final
acceptance controls fail against the accepted selector; the final targeted set passes
35 tests. The changed critical analyzer covers all 378 statements
and 252 branches. Documentation/governance: 93 PASS;
repository: 186/0/0; portable direct and sdist-wheel package routes: PASS.

The complete immutable PR #68 replay changes 35 modules / 725 baseline IDs to
10 modules / 261 IDs; coverage remains none and both smokes are false. Baseline
case-duration attribution is 773.460 to 74.728 seconds, not a new hosted timing result.
The graph audit removes 432 name/guard edges and adds four fixed relative inputs.
Fixture resources and unbounded executable probes keep their conservative closure.

The 134-test development infrastructure run passed before the last root-scope
hardening was finalized. The earlier instrumented development run was cancelled
as superseded after source changes. Both logs are retained, and neither is claimed
as final-head full acceptance. The separate final-source infrastructure run and
hosted dual-Python bootstrap are reported in the PR when available.

The refreshed consumer fingerprint is proposed for acceptance with this repair;
the introducing PR still uses immutable base policy and requires the complete
selection-authority bootstrap, unchanged quality floors, independent fixed-root
witness and cross-owner review. No M4/M14 implementation branch or release authority
is changed. Logs are normalized to LF before hashing; native capture gaps remain explicit.

See [summary](checks/summary.json), [full replay](checks/real-replays.json), and
[final negative controls](checks/base-regressions.log).
