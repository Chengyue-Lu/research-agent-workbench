# TEST-PERF-002 validation

Base: `6f0caf0b8e8a9b123f1ea399e747d2c0ed33cdce` (`develop`).
Implementation: `ceacf58cca0f82d6016e18ba818acd9b42f2805a`.
Guard verification baseline: `2e083f9c1790458689c94873eb192cd3250648b0`.
Review: [PR #63](https://github.com/Chengyue-Lu/research-agent-workbench/pull/63), R2, target `develop`.

## Local evidence and its commit boundary

All local runs used Windows and Python 3.14. The full runs below belong to the implementation commit;
the final code adds strict policy and execution-input guards and has its own targeted regression evidence.
Archive commit `613f91a` preserves those source and test blobs. Hosted Python 3.11/3.13
FULL checks must pass on the final PR head before acceptance.

| Check | Commit | Result |
| --- | --- | --- |
| Full behavioral suite | `ceacf58` | 887 tests: 884 PASS, 3 Windows symlink-privilege skips; 942.57 s |
| Coverage-quality suite | `ceacf58` | 826 tests: 823 PASS, 3 same skips; 544.92 s |
| Repository coverage policy | `ceacf58` | Global line 91.97%; every critical module meets 95% line / 90% branch |
| Planner/checker/runner regressions | `2e083f9` | 34/34 PASS |
| Planner critical coverage | `2e083f9` | 99.59% line / 96.88% branch, zero exclusions |
| CI checker critical coverage | `2e083f9` | 99.13% line / 95.00% branch, zero exclusions |
| Governance, documentation, coverage-policy regressions | `2e083f9` | 104 PASS |
| Repository validation | `ceacf58` | 183 validated, 0 errors, 0 warnings |
| Wheel clean-install smoke | `ceacf58` | Build, fresh venv install, schema list and 183/0/0 validation PASS |
| Workflow syntax | final workflows | actionlint 1.7.12 PASS; release archive checksum verified |

The initial local wheel install inherited `PYTHONPATH` and did not prove a clean wheel import. The recorded
passing smoke clears that variable and force-installs the built wheel in the fresh venv. Product source,
schemas, registry and packaging are identical between the two code commits and the accepted base.

## Actual selective execution in isolated Git fixtures

Both fixtures start at final code `2e083f9`. They preserve the full accepted consumer inventory and invoke
the real planner and runner. Their synthetic commits exist only in an ignored local clone.

| Fixture | Selected obligations | Result |
| --- | --- | --- |
| Equivalent OpenAI provider-name literal | provider-wire → conformance → session → CLI; impact coverage | 81/81 PASS, impact checker PASS; 26.46 s |
| README-only addition | documentation group; FAST | 76/76 PASS; 1.46 s |

These timings establish local selection and execution behavior, not hosted speed savings. Impact coverage
explicitly reports `repository_coverage_proved: false`. Unknown or changed consumers, policy/runner edits,
new imports, source add/delete/rename/mode changes, source deletion-only hunks, stale bases, R2 and
integration/release work retain FULL. Negative fixtures cover plan weakening, dirty/untracked inputs,
coverage and evidence drift, missing/failed/cancelled required jobs, and stale or weaker metadata reuse.

## Hosted evidence and remaining acceptance

The initial PR opened at `2e083f9`; governance run `34029871790` passed. Content run `34029871793`
started for that head. The archive commit will trigger a replacement FULL run. Current results are
authoritative at the [PR checks](https://github.com/Chengyue-Lu/research-agent-workbench/pull/63/checks).
Old-head cancellation and metadata-only behavior must be observed from actual hosted events; local
workflow and negative fixtures do not by themselves prove those remote outcomes.

The remote settings query returned `rulesets=[]` and `develop.protected=false`. Fixed aggregate check
names and fail-closed propagation are preserved; remote required-check enforcement is not established
by this implementation. Cross-owner review and final-head CI remain merge gates.

## Archive

[Attempt index](../../../../work/TEST-PERF-002/A-20260906-001/INDEX.yaml) pins the task, compact handoff,
source hashes and machine result summaries. Native events, intermediate file revisions and complete
tool output streams have explicit capture gaps. The archive distinguishes observed checks from pending
hosted acceptance; structural Trace validation does not grant a human approval.

## PR review follow-up

Copilot's initial review identified a missing `pull-requests: read` token permission for FULL dispatch and
an unclear failure when a focused run omits `--plan`. The follow-up grants only the required read permission
and rejects missing plan/loader inputs with explicit errors. The existing regression cases now exercise
these paths (34/34 PASS); actionlint and 9 documentation tests pass. This follow-up is recorded in PR #63 and its
own Git commit after the frozen archive; the archive's code manifest remains evidence for `2e083f9`.

Hosted run `34029871793` on `2e083f9` was automatically cancelled after `613f91a` started replacement
run `34030126386`. No manual cancellation was issued. Updating the PR body after that replacement plan
was uploaded triggered governance run `34030228581`, which passed and retained content run `34030126386`
without launching another content run. Final hosted outcomes remain available in the PR checks and body.
