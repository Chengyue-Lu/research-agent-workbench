# 2B — Consumer proposal and execution comparison

Owner: 路诚钺 (`Chengyue-Lu`); risk R2; [Issue #87](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87).
This first 2B slice follows the [domain inventory](DOMAIN_MODEL.md). It introduces
an offline behavioral proposal and result comparator. Accepted execution still runs
under the existing planner, witness, workers and aggregate Gates.
The [review boundary](CONSUMER_SHADOW_READINESS.md) separates this diagnostic PR's
completion requirements from later production activation.

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
An optional nonempty `changed_path_patterns` field limits an invocation proposal
to its reviewed input-change scope; a change outside that scope retains the tests.

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

## Paired execution observations

[`ci_shadow_pair.py`](../../../../.github/scripts/ci_shadow_pair.py) extends the
diagnostic with two separately recorded executions. It recomputes the proposal from
the exact plan, matches canonical IDs/order and source receipts, and binds Python,
platform, dependency inventory, runner, coverage configuration, invocation context
and the actual execution-driver source/invocation. It rejects using one execution
as both pair members. A changed selection must use a `shadow-candidate` receipt;
an unchanged candidate may retain its original native runner suite label.
When either behavioral or coverage order changes, invocations must differ only in
the value of one unique `--role` argument from `accepted` to `candidate`. Identical
invocations are allowed only when both complete orders are unchanged. Missing or
ambiguous roles for changed orders keep the pair inconclusive, as do other changes
to options, values or their order. Every smoke observation also binds its member's
run ID and native
execution receipt digest and retains the original smoke artifact digest. A copied
opposite-member smoke is rejected. Aggregate
skip events remain inconclusive even when individual case records omit the skip.

Each raw coverage artifact is explicitly associated with its plan, target, run,
source receipt digest and artifact digest. The existing impact and repository
checkers evaluate each member separately, using the tested target's policy and
matching checker sources. Global 90, critical 95/90, changed 100/100 and required
positive/negative evidence remain their original requirements. Coverage missing,
failed tests, skipped checkpoints or failed/missing smoke stay inconclusive.

A real subprocess regression demonstrates why coverage and execution outcomes are
separate: both runs execute every line and branch, but moving a case into the later
coverage phase restarts its class fixture and makes its behavior fail. The paired
diagnostic reports that failure instead of accepting the complete coverage map.

Two drivers with different code remain a timing confound even on the same target
and environment. The report preserves their observed wall times and quality results
but keeps the pair `inconclusive`. An `observed-matching-pair` result refers to the
supplied inventories/artifacts, not authenticated completeness or activation authority.
One local pair cannot establish hosted critical-path savings.

A historical provider control also exercises real required coverage and both
smokes: two fresh Python 3.11 executions each retain B=81/C=34, with no exclusions,
and pass impact, repository and four package-install probes independently. An
earlier guard-change control passes all behavioral cases but fails its changed
coverage coordinates; that original failure is retained. These provider subjects
are not critical inventory members. This control proves actual protocol handling,
not repository coverage, a new critical threshold result or a speedup.

```text
python .github/scripts/ci_shadow_pair.py --repo . --plan plan.json --proposal proposal.json --inventory inventory.json --accepted accepted-bundle.json --candidate candidate-bundle.json --output pair.json
```

The first complete doc-control observation uses the original plan's 325 tests
across 13 modules, with C empty and both smokes not required. The previously proposed
Kernel pair is already outside this B and saves zero actual work. A separate source
audit identifies 73 PlannerTests that read 19 fixed source/config/fixture inputs and
generate their Markdown inside temporary Git repositories. Their new proposal is
limited to modified existing workstream Markdown; other consumers stay selected.
The independent audit also runs a real planner-source mutation that makes an existing
test fail, and that executable change remains outside the exclusion pilot.

Actual pair data, original setup-error evidence and the hosted #92 baseline are in
[Attempt A-20260920-003](../../../../work/TEST-PERF-002/A-20260920-003/RESULTS.md).
The hosted #92 baseline passed all Gates with B=1418/C=1392 and coverage job 19m51s;
its lone unclassified fallback was the diagnostic `domain-model.json` input. This
is a future declaration-boundary item, not an exemption based on its docs path.
Protocol repairs, the real impact/smoke controls and their independent review are
retained in [Attempt A-20260920-004](../../../../work/TEST-PERF-002/A-20260920-004/RESULTS.md).

## Inherited reviewed-leaf anchor issue

Coverage pilot preparation at base `171d4654f88e926f239cdf25bc8168109b81f391`
found an additional conservative expansion. The production planner chooses the most
recent commit touching the entire impact-policy file as its reviewed fingerprint
anchor. PR #86 and #89 changed diagnostic consumer-record pins only within that
file, preserving the earlier fingerprint, groups and leaf definitions. Their new
file anchors include changed non-leaf inventories and no longer match that digest.
Consequently otherwise eligible leaf changes lose the reviewed opaque-consumer
boundary; both behavioral and impact test selection can expand.

The matching historical anchor is `348d6257ddd28637c9d06abe177fc685ac4368b6`.
Experiments using it are historical controls, not narrow plans available at the
current accepted base. The current-base expanded plans and exact fingerprint record
changes are retained as diagnostic debt. A digest refresh would admit newly changed
consumers into the reviewed inventory and needs its own closure audit.

Repair requires a separately reviewed authority anchor that survives diagnostic-only
record changes while continuing to retain new or changed consumers. The current PR
does not alter that production selection mechanism. An unavailable or mismatched
anchor continues to retain the conservative plan.
