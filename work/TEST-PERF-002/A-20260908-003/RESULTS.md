# Real-module precision acceptance evidence

TEST-PERF-002 revision 15 validation continuation. Owner Chengyue-Lu; cross-owner let778750-cpu; R2.

PR #67 head `439940067c3d60e0d0196fd976e24ccd6e79424a`, base `bdbac11a0c9a17fa221f8cc8bdd522c1bf4f9087`, target `8338a4518e6768159ec6f5af5f2c80b8f9a2c73f`.
[Current-head CI](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34154360036) and both fixed aggregates pass. [Independent pinned witness](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34154474835) passes for the exact binding and plan ID. Cross-owner acceptance remains a separate merge prerequisite.

| Formal suite | Actual tests | Test wall seconds |
|---|---:|---:|
| compatibility-3.11-evidence/full-test-results-3.11.json | 985 | 1049.32 |
| compatibility-3.13-evidence/full-test-results-3.13.json | 985 | 1257.23 |
| coverage-quality-evidence/coverage-test-results.json | 959 | 1995.23 |

Repository global line is **92.27%**; the independent artifact recheck retains all critical 95/90 floors and positive/negative acceptance. The CI impact checker also passed. Focused preflight after the alias repair passed 115 tests with changed statements/outgoing branches 100/100.

The actual M14-based comparison uses isolated proposed future-develop consumer contracts. They require review before becoming authority for ordinary PRs. The final selector/worker bytes match PR #67; the experimental workflow supplies explicit hypothetical bases and emits no required aggregate identities. Formal M14/M4 branches remain unchanged.

[Shared before run](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34152736021) and [final after run](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34154076029) use ubuntu-latest, Python 3.11.16/3.13.15 and the actual candidate runner/collector. Each independent before plan selects the same 72 modules; one combined equivalent-edit run measures their common suite. The edits preserve outputs by adding [0:] to a single function return. The baseline combines the three such edits, and the after cases each change only their own module.

| Case | Behavioral tests | Proof tests | Behavior 3.11 s | Behavior 3.13 s | Coverage suite s | Max worker s | Sum runner s |
|---|---:|---:|---:|---:|---:|---:|---:|
| before | 1027 | 1027 | 968.44 | 1644.57 | 3498.21 | 3522 | 6176 |
| claim | 27 | 15 | 95.69 | 135.17 | 184.45 | 210 | 479 |
| projection | 28 | 16 | 149.48 | 89.55 | 239.12 | 269 | 555 |
| release | 38 | 38 | 8.84 | 10.74 | 17.66 | 45 | 105 |

One sample per case, on separate hosted VMs: these are observed conditional measurements, not a statistical latency guarantee. Worker wall includes setup, checks and upload; dispatch-to-start time and actual matrix spans are retained in [the structured summary](checks/hosted-summary.json). Max worker is the parallel compute critical path, not a measured standalone PR latency. Smokes are not timed by this experiment; their plan flags are retained.

All three local positive controls and six injected source/consumer faults passed their expected outcomes. Faults ran against the frozen positive behavioral suite and failed through real assertions or the injected consumer exception. The release consumer probe targets export within release_surface.py; claim targets CLI _claim_trace, and projection targets registry validation. The original local prototype predates the alias repair; [byte equivalence](checks/integrity.json) establishes unchanged runtime/consumer/test inputs, while final hosted plans establish the repaired selector output.

Initial formal head 9e286e3 and its witness/experimental after receipts are historical inputs, superseded by the final references above. The old content run was automatically cancelled when 4399400 arrived; metadata edits did not replace the new content plan. PR #60 integration coverage paths and archived-oracle classification remain separate work. This evidence does not activate release/tag/main or further M14 milestones.

Trace has an explicit native capture gap and is sealed safe-paused for cross-owner review.
