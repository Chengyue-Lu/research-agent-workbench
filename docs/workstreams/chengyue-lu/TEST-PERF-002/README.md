# TEST-PERF-002 — Change-aware CI

- Audit ID: `TEST-PERF-002`; owner: 路诚钺 (`Chengyue-Lu`); cross-owner: 黄毅 (`let778750-cpu`).
- Risk: R2, shared CI selection and quality authority.
- Request: [Issue #48 restart](https://github.com/Chengyue-Lu/research-agent-workbench/issues/48#issuecomment-5558497614).
- Base: `6f0caf0b8e8a9b123f1ea399e747d2c0ed33cdce`; independent implementation branch `feature/test-perf-002-change-aware-ci`.
- Accepted quality foundation: [TEST-QUALITY-001](../TEST-QUALITY-001/README.md).
- Scope: planner, execution/coverage obligations, workflow events and evidence. Product Runtime, Provider code, research authority and Task definitions retain their current contracts.

The next repair round after merged PR #66 is prepared in [Impact precision](IMPACT_PRECISION.md),
with the real M14 hosted baseline, three reproduced module probes and independent coverage-selection acceptance.

The post-merge PR #68 investigation and bounded parser repair are recorded in
[Resource dependency precision](RESOURCE_DEPENDENCIES.md).

The follow-up [project comparison and analysis performance](ANALYSIS_PERFORMANCE.md)
records immutable syntax-fact reuse, unchanged graph/plan outputs and local timings.

[Scenario tests and execution reuse](SCENARIO_EXECUTION.md) describes named checkpoints
and the parallel coverage / behavioral-remainder producers with a complete evidence join.

## Selection authority

[`plan_ci.py`](../../../../.github/scripts/plan_ci.py) reads exact base/head/merge-base Git facts and the
accepted base [`ci_impact_policy.yaml`](../../../../tests/ci_impact_policy.yaml). Governance v2 supplies the risk
floor. Plan v4 derives behavior from the affected base/head consumer and contract closure.
R2 determines governance and cross-owner review; affected tests run on Python 3.11 and 3.13. Candidate policy changes never authorize their own lighter selection.
Semantic changes to `plan_ci.py`, `ci_dependencies.py`, `ci_checks.py`, `run_unittest_suite.py` or `ci.yml`
require complete behavioral suites to validate selection authority. Their coverage and smoke obligations
remain independently derived. Ordinary R2 product and test changes retain affected-scope selection.
Git replacement objects are disabled for the planner's reads; immutable Git blobs are cached by repository,
exact commit and path. No mutable branch-name result is cached.

The deterministic plan binds repository, base/head, merge-base, tested head/merge candidate, policy digest,
selected surfaces/groups/tests, coverage and smoke obligations. Workers and aggregates revalidate it against
the workflow event and Git facts. Agent requests may add policy groups or request FULL; they cannot remove the
machine minimum. The PR's declared risk can raise the inferred floor and cannot lower it.
The impact policy uses strict JSON (a YAML subset); duplicate keys and ambiguous YAML constructs are rejected.
Consumers reject tracked checkout drift and unexpected source/test/CI files before executing a plan.

| Behavioral class | Behavioral execution |
|---|---|
| FAST | Documentation-only obligations: documentation/links, task/governance tests and diff check; governance independently validates the real PR |
| FOCUSED | Closed groups and downstream consumers on Python 3.11/3.13 |
| FULL | Complete dual-Python behavioral suites |

`change_class` is a diagnostic alias for `behavioral_scope`; jobs consume their own obligation fields.
Source, tests, shared fixtures and resources seed the affected closure independently of risk.
Test/fixture/archive data and selection-policy metadata can have `coverage_scope: none` and no smokes. Bounded executable changes require
impact coverage; coverage-authority changes and uncertain executable closure add repository coverage.
`coverage_obligations` is a set: repository evidence never substitutes for impact 100/100. Combined plans
run the union of selected tests once and enforce both checkers. Failed required impact mapping blocks consumption.
Stale base, invalid/missing policy and unavailable closure retain complete fail-safe evidence. If exact commit
facts cannot be read, execution fails instead of inventing a usable plan. All develop/main push and release
boundaries retain full behavior, repository coverage and both smokes.
Authority documents are subject to Governance risk even when an allowlist pattern matches them.

The detailed obligation matrix, reasons and PR #65 acceptance fixture are in [OBLIGATIONS.md](OBLIGATIONS.md).

## Initial focused closure

The first bounded entry is Provider wire serialization/parsing in `openai.py`, `anthropic.py` and `gemini.py`:

`provider-wire -> provider-conformance -> provider-session -> provider-cli`

The groups include existing normalization/preflight/error tests, conformance construction, API session behavior,
CLI and validation consumers. These base-side groups remain additive contract obligations.
[`ci_dependencies.py`](../../../../.github/scripts/ci_dependencies.py) builds a module-level reverse graph
from exact base/head Python blobs, including imports, package initialization, literal repository references,
resource readers and conservative opaque-execution consumers. Removed edges remain in the union.
Changed tests seed themselves and their consumers. Ordinary comments preserve the executable AST; deleted
source lines select old consumers without inventing candidate coverage coordinates.

The graph inventory digest binds the evidence. Reviewed groups use their immutable base-side fingerprint
commit as an anchor; unchanged consumers retain that boundary, while changed consumers and imports add
new dependency obligations. A change to an unrelated consumer no longer invalidates
all groups. Candidate fingerprint refreshes cannot remove base-side requirements. Unparseable dependencies,
unclassified surfaces and source without a closed test consumer retain explicit complete-evidence fallback.
Opaque execution can select a broad set; its affected consumers and dependency chains appear in the plan.
The analyzer is conservative and does not claim that static import reachability alone proves independence.

An initial local shadow measurement executed 81 group tests with no skips in approximately 19 seconds under
coverage. This is selected-suite evidence, not a hosted critical-path or total-compute speedup claim. Exact
final validation and limitations are recorded in [VALIDATION.md](VALIDATION.md).

## Coverage Policy v2.1

[`coverage_policy.yaml`](../../../../tests/coverage_policy.yaml) remains the threshold authority. Repository coverage keeps
canonical package-wide line >=90% and every critical module line >=95% / branch >=90%, with the existing
positive/negative acceptance and exact exclusion reconciliation.

Impact coverage uses the same full measurement roots and preserves its artifact. Each impacted critical file must
still satisfy whole-file 95/90 plus its own positive/negative evidence. For ordinary files, changed executable
lines and outgoing branches require 100% coverage. Git derives physical `changed_lines`; the planner expands
each line to the smallest enclosing AST statement span in `coverage_lines`, preserving multiline statement
and branch origins. A changed compound condition conservatively covers its suite as well. Workers recompute
both sets; ordinary blank/comment lines have no executable obligation and unmappable executable changes block. This may require more evidence than the physical diff alone.
Unchanged ordinary lines do not acquire a new whole-file critical threshold. The impact report explicitly sets
`repository_coverage_proved: false`. Missing files, branch detail, wrong-head results, lowered thresholds,
uncovered changed code, skipped required evidence and undeclared exclusions fail.

The planner, dependency analyzer and CI evidence checker themselves enter the critical 95/90 inventory with independent positive
and adversarial acceptance tests. Tests are retained in full behavioral discovery.

## Events, cancellation and required checks

`CI` owns content events and fixed `test (3.11)` / `test (3.13)` aggregate identities. A newer PR content run
cancels its obsolete predecessor. Integration push runs are not cancelled by this PR optimization.
`CI governance` alone owns the `governance` identity and also processes body/label edits; it has a separate
concurrency group and cannot cancel a content run.

Metadata recomputes obligations and requires an authenticated same-repository CI plan artifact from the exact
base/head/test target and policy. An in-progress content plan can satisfy continuity while the independently
required content checks remain pending. Failed/cancelled runs, another workflow, a weaker plan, stale base or
head cannot supply continuity. Metadata never publishes a successful compatibility/coverage/package result.

Base retargeting or risk escalation can require new content evidence. Run the FULL recovery entry using the
current PR branch and number, then rerun the failed governance check after its content plan is available:

```sh
gh workflow run ci.yml --ref <current-pr-branch> -f pr=<pr-number>
```

The dispatch fetches current PR metadata and requires its trigger `GITHUB_SHA` to equal that PR's current head
before planning FULL for the exact head/merge candidate. A wrong ref or stale dispatch rerun stops at the plan
stage; start a new dispatch from the current PR branch. Ordinary
metadata edits do not dispatch code tests. A very early metadata run with no uploaded content plan fails
explicitly and can be rerun once the plan exists.

Aggregates use `always()` and recompute obligations. Every required dependency must report success; missing,
cancelled, failed or unexpectedly skipped required jobs block. Only plan-exempt work may be skipped.
Repository settings are separate: the intake query found no rulesets and `develop.protected=false`; preserving
check names does not claim remote protection is enabled. This PR does not change repository settings.

## Delivery and review

The [Risk Ledger](RISK_LEDGER.md), validation record, PR diff and bounded Attempt archive are the review inputs.
Post-merge behavior and the integration fixture repair are recorded in [HOSTED_VERIFICATION.md](HOSTED_VERIFICATION.md).
The work uses the existing Audit ID path, as PR #49 did, and does not modify M-series Task states. PR #65 was
merged at the user's explicit instruction after all ten exact-head checks passed. Its merge is `97f760c`.
The independent-obligation implementation is a new R2 PR for cross-owner review.
