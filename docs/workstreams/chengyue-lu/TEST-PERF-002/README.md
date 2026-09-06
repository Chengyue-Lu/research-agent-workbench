# TEST-PERF-002 — Change-aware CI

- Audit ID: `TEST-PERF-002`; owner: 路诚钺 (`Chengyue-Lu`); cross-owner: 黄毅 (`let778750-cpu`).
- Risk: R2, shared CI selection and quality authority.
- Request: [Issue #48 restart](https://github.com/Chengyue-Lu/research-agent-workbench/issues/48#issuecomment-5558497614).
- Base: `6f0caf0b8e8a9b123f1ea399e747d2c0ed33cdce`; independent implementation branch `feature/test-perf-002-change-aware-ci`.
- Accepted quality foundation: [TEST-QUALITY-001](../TEST-QUALITY-001/README.md).
- Scope: planner, execution/coverage obligations, workflow events and evidence. Product Runtime, Provider code, research authority and Task definitions retain their current contracts.

## Selection authority

[`plan_ci.py`](../../../../.github/scripts/plan_ci.py) reads exact base/head/merge-base Git facts and the
accepted base [`ci_impact_policy.yaml`](../../../../tests/ci_impact_policy.yaml). Governance v2 supplies the risk
floor. Policy/runner/checker changes require FULL, including the bootstrap PR that introduces the planner.
Git replacement objects are disabled for the planner's reads; immutable Git blobs are cached by repository,
exact commit and path. No mutable branch-name result is cached.

The deterministic plan binds repository, base/head, merge-base, tested head/merge candidate, policy digest,
selected surfaces/groups/tests, coverage and smoke obligations. Workers and aggregates revalidate it against
the workflow event and Git facts. Agent requests may add policy groups or request FULL; they cannot remove the
machine minimum. The PR's declared risk can raise the inferred floor and cannot lower it.
The impact policy uses strict JSON (a YAML subset); duplicate keys and ambiguous YAML constructs are rejected.
Consumers reject tracked checkout drift and unexpected source/test/CI files before executing a plan.

| Class | Execution |
|---|---|
| FAST | Allowlisted documentation with acceptable risk: documentation/links, task/governance tests and diff check; governance independently validates the real PR |
| FOCUSED | Closed groups and downstream consumers on Python 3.11/3.13, impact coverage, required package/repository smoke |
| FULL | Complete dual-Python behavioral suites, repository Coverage Policy, documentation, package and repository smoke |

R2, shared Schema/Registry, high-fanout/unclassified source, CI/test infrastructure, new/deleted/renamed source,
stale base, invalid/missing policy or incomplete groups select FULL. If exact commit facts cannot be read,
execution fails instead of inventing a usable plan. All develop/main push and release boundaries remain FULL.
Authority documents are subject to Governance risk even when an allowlist pattern matches them.

## Initial focused closure

The first bounded entry is Provider wire serialization/parsing in `openai.py`, `anthropic.py` and `gemini.py`:

`provider-wire -> provider-conformance -> provider-session -> provider-cli`

The groups include existing normalization/preflight/error tests, conformance construction, API session behavior,
CLI and validation consumers. Product-source, Schema, Registry, packaging metadata and all Python files under
`tests/` outside these leaves are
bound by a consumer-inventory fingerprint. A changed accepted inventory requires a fresh closure review and
policy update before FOCUSED resumes. Changed imports and deletion-only source hunks also fall back to FULL.
This conservative inventory guard prevents a newly merged consumer from silently escaping the old groups.

An initial local shadow measurement executed 81 group tests with no skips in approximately 19 seconds under
coverage. This is selected-suite evidence, not a hosted critical-path or total-compute speedup claim. Exact
final validation and limitations are recorded in [VALIDATION.md](VALIDATION.md).

## Coverage Policy v2.1

[`coverage_policy.yaml`](../../../../tests/coverage_policy.yaml) remains the threshold authority. FULL keeps
canonical package-wide line >=90% and every critical module line >=95% / branch >=90%, with the existing
positive/negative acceptance and exact exclusion reconciliation.

FOCUSED uses the same full measurement roots and preserves its artifact. Each impacted critical file must
still satisfy whole-file 95/90 plus its own positive/negative evidence. For ordinary files, changed executable
lines and outgoing branches require 100% coverage. Git derives physical `changed_lines`; the planner expands
each line to the smallest enclosing AST statement span in `coverage_lines`, preserving multiline statement
and branch origins. A changed compound condition conservatively covers its suite as well. Workers recompute
both sets; unmappable lines require FULL. This may require more evidence than the physical diff alone.
Unchanged ordinary lines do not acquire a new whole-file critical threshold. The impact report explicitly sets
`repository_coverage_proved: false`. Missing files, branch detail, wrong-head results, lowered thresholds,
uncovered changed code, skipped required evidence and undeclared exclusions fail.

The planner and CI evidence checker themselves enter the critical 95/90 inventory with independent positive
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
The work uses the existing Audit ID path, as PR #49 did, and does not modify M-series Task states. Cross-owner
review and exact-head required checks are merge prerequisites. No self-merge or release operation is included.
