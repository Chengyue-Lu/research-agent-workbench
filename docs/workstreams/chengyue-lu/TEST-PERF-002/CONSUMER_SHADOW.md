# 2B — Consumer proposal and execution comparison

Owner: 路诚钺 (`Chengyue-Lu`); risk R2; [Issue #87](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87).
This first 2B slice follows the [domain inventory](DOMAIN_MODEL.md). It introduces
an offline behavioral proposal and result comparator. Accepted execution still runs
under the existing planner, witness, workers and aggregate Gates.

## Protocol

[`ci_consumer_shadow.py`](../../../../.github/scripts/ci_consumer_shadow.py) takes an
exact Git plan, a separately supplied consumer proposal, a collected canonical test
inventory, and optionally a native runner receipt. It does not import or execute a
consumer while deciding exclusions. Every output has `execution_authority=false`
and `activation.eligible=false`; no workflow consumes it as a plan.

The proposal declares a frozen base, named owner and invocation, exact canonical
test IDs, source/helper pins, input discovery patterns, explicit assumptions and
unknowns. Matching pins establish byte agreement only. They do not prove a complete
input closure or authorize a reduction. Pattern matching is case-sensitive and
`*`/`**` can cross `/`, as in the domain diagnostic. Test identities and pins are exact.

The first pilot considers only changes to existing regular Markdown under `docs/`
or the root README. It checks both the PR delta and base-to-tested-target delta,
plus pins at base, merge-base, head and target. Empty deltas, add/delete/rename,
mode boundaries, executable documents, stale proposals, changed pins and unknown
inputs retain accepted behavior. A Gitlink never causes a foreign object read.
Markdown eligibility alone does not exclude any test. Undeclared test consumers
remain selected; overlapping consumers must all propose exclusion before a case
can leave the behavioral set. Future tests absent from a declaration remain selected.

Inventory is explicit about `plan-collection` versus `observed-subset`, exact plan,
target, Python version, ordered canonical IDs and runtime aliases. It is separately
hashed, but offline provenance is not authenticated. A partial observation cannot
establish execution of the complete accepted plan. Reports preserve missing tests,
skips, expected failures, fixture events, failing checkpoints, inconsistent order,
unknown coverage inventory and absent smoke results.

## Behavioral and coverage work

Let B be the accepted behavioral order and C the accepted coverage order. The
candidate only narrows B in this slice; coverage tests, subjects, coordinates,
positive/negative evidence and both smoke obligations remain unchanged.

| Report field | Meaning |
| --- | --- |
| behavioral_skips | B minus proposed B |
| effective_execution_skips | Cases absent from both proposed B and C, within the supplied inventory |
| moved_to_coverage_phase | Former B/C overlap cases now executed during C minus proposed B |
| comparison | Actual outcomes joined to proposed execution, including observed missed failures |
| coverage_comparison | Preserved obligations; candidate measurement still not run |

The resulting order is proposed B followed by C minus proposed B. An accepted
coverage union cannot establish coverage for a different fixture lifecycle. When
a subset observation has incomplete required C, effective skips and their duration
estimate are unknown. With complete supplied inventories, excluded case durations
are an estimate of case cost only, never job critical path, CPU time or proven savings.
Projected receipts cannot substitute for the original ordered execution receipt.

CLI inputs are read-only, including hardlink and resolved-path overwrite guards:

```text
python .github/scripts/ci_consumer_shadow.py --repo . --plan plan.json --proposal proposal.json --inventory inventory.json --receipt execution.json --output shadow.json
```

The output includes semantic input digests (planner canonical JSON, including its
trailing newline) and producer hashes. Original artifact bytes and their hashes are
retained separately in the experiment archive. These are different from the runner's
compact, no-trailing-newline projection digest.

## Real failure probes

The isolated probe starts at `09c6cb1c82680233c369014e0831874b6702d3b7`, the stacked
2A snapshot. Each probe changes one existing document and executes 25 original
tests: documentation, public surface, and two in-memory Kernel cases. No test body,
assertion or resource reader is mocked. The native timed runner is used for the
second observation and captures subtest failures on their parent case.

| Input mutation | Observed failure | Candidate behavior |
| --- | --- | --- |
| Broken link in docs/README | Internal Markdown link check | Failure retained |
| Remove support navigation from root README | Public-surface navigation check; all documentation tests pass | Failure retained |
| Internal navigation in GETTING_STARTED | Six parent cases across documentation and public surface | All failures retained |
| Unrelated workstream note | All 25 cases pass | Kernel pair proposed as unrelated control |

Several public-surface tests that construct fixture dictionaries still retain other
real public documents. They cannot be excluded as isolated fixture tests. Trace
vocabulary also consumes `docs/modules/07-ARTIFACTS_AND_PROVENANCE.md`; governance
tests consume a specific rollout document. Their unknown consumers stay selected.
Only the two audited in-memory Kernel invocations are proposed exclusions here.
This is a small boundary experiment, not evidence for excluding all business tests.

The historical PR #90 source receipt provides a mixed source/schema/archive
control: B=1425, C=1399. This pilot proposes zero exclusions. Its test outcomes do
not repair the historical coverage Gate failure or establish fresh execution.

## Remaining gates

Evidence and exact implementation validation are retained in
[Attempt A-20260920-002](../../../../work/TEST-PERF-002/A-20260920-002/RESULTS.md).
Before completing 2B and requesting 2C activation, expand declared invocation
closure, run the complete accepted plan beside independent candidate execution,
compare candidate coverage and smoke, and retain relevant-failure/irrelevant-control
evidence for each proposed boundary. Independent witness review and at least three
fresh same-environment hosted pairs remain required for activation and a speed claim.

Current quality thresholds and fresh develop/main/release baselines remain in force.
The 37-minute coverage problem is not solved by reducing a behavioral set alone.
Coverage selection and the internal cost of genuinely required cases remain separate
work items; this comparator makes that distinction measurable.
