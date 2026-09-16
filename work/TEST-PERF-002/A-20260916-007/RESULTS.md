# Historical branch replay evidence

TEST-PERF-002; owner Chengyue-Lu; R2; A-20260916-007. User authorized tests using old branches.

Current engine commit: `47c09b95cc27fe59e1ebf1240ba3d3d6ef1a3543`. Original base/head pairs and fetched PR metadata are retained. Targets equal historical heads; this is not a rebase or an attestation of historical hosted merge results.

| PR | Dependency modules | Behavioral | Coverage | Package / repository smoke | Replay |
| --- | ---: | --- | --- | --- | --- |
| #65 event isolation | 4/70; final plan has 5 selectors | focused | none | false / false | PASS |
| #77 M14 Quickstart | 86/87 | full | repository | true / true | PASS |
| #80 M14 Source CI | 92/93 | full | impact + repository | true / true | PASS |

The shadow report preserves accepted groups, every selected consumer chain and all obligations. #65 does not change executable production or coverage authority. #77 actually changes pyproject.toml; #80 changes the CI workflow. Those concrete authority reasons retain full baselines independently of R2.

#65 selected execution: the exact five planned modules ran in a clean detached historical checkout, Python 3.11, 134 PASS in 63.548 s. This is fresh local execution of the selected set, without instrumentation or a paired full-suite run. It does not measure hosted savings. M14 branches were used for planner/report replay, not full test execution.

The prototype reports 1/7/22 unknown archive inputs respectively: .log files and historical attributes such as `* text eol=lf`, `** -text`, and scoped whitespace rules. They remain explicit audit gaps. No role exception, selector exclusion or activation rule was added to fit these examples.

The first exploratory invocation supplied incomplete synthetic risk metadata and triggered conservative fallback. The retained final comparisons use the actual PR metadata and assert that this artificial fallback is absent. Earlier tool-stream capture is incomplete and is declared in Trace.

Initial PR85 hosted diagnostic job succeeded at head 47c09b9 and merge target 41de7c4; retained artifact bindings match the official plan and tested engine hash. This proves that diagnostic producer only, not all required CI or a later commit.

See [replay summary](checks/branch-replay-summary.json), [actual #65 execution](checks/pr65-selected-execution.json), [raw log](checks/pr65-selected-execution.log), [hosted diagnostic binding](checks/hosted-shadow-binding.json), [hash manifest](checks/evidence-manifest.json), [Trace validation](checks/trace-validation.json), and [implementation](../../../docs/workstreams/chengyue-lu/TEST-PERF-002/SHADOW_V1.md).
